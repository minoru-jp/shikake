"""Generator subject: AST-backed early Kind identification, no lowering."""

from __future__ import annotations

import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SAMPLE = Path(__file__).resolve().parents[1] / "tests/fixtures/generator_subject.py"


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    values = model.get(role)
    assert isinstance(values, tuple)
    return cast(tuple[Model, ...], values)


def child(model: Model, role: str) -> Model:
    value = model.get(role)
    assert isinstance(value, Model)
    return value


def definition(root: Model, name: str) -> Model:
    return next(
        n
        for n in nodes(root, "body")
        if n.kind.id.startswith("model.definition.") and n.get("name") == name
    )


class GeneratorSubjectTests(unittest.TestCase):
    def test_generator_is_function_or_method_with_feature(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(len(index.all_kinds()), 142)
        self.assertNotIn(
            "model.definition.generator", {kind.id for kind in index.all_kinds()}
        )
        self.assertTrue(
            index.is_a("model.definition.method", "model.definition.function")
        )
        self.assertIs(
            index.require_structure("model.definition.method"),
            index.require_structure("model.definition.function"),
        )
        index.validate_features("model.definition.function", ("generator",))
        index.validate_features("model.definition.method", ("async", "generator"))
        with self.assertRaises(ValueError):
            index.validate_features("model.value.named", ("generator",))

    def test_sample_generator_kind_and_yield_operands(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        self.assertTrue(shikake.inspect_source(source).complete)
        root = shikake.parse_source(source)
        filtered = definition(root, "filtered_rows")
        self.assertEqual(filtered.kind.id, "model.definition.function")
        self.assertEqual(filtered.features, ("generator",))
        self.assertEqual(filtered.get("name"), "filtered_rows")
        self.assertEqual(len(nodes(filtered, "parameters")), 2)
        self.assertEqual(len(nodes(filtered, "decorators")), 0)
        self.assertEqual(child(filtered, "body").kind.id, "model.statement.block")
        yields = [n for n in filtered.walk() if n.kind.id == "model.value.yield"]
        delegated = [
            n for n in filtered.walk() if n.kind.id == "model.value.yield_from"
        ]
        self.assertEqual(len(yields), 1)
        self.assertEqual(len(delegated), 1)
        self.assertEqual(child(yields[0], "value").get("name"), "row")
        self.assertEqual(
            child(child(delegated[0], "value"), "callee").get("name"), "fallback_rows"
        )
        self.assertEqual(
            definition(root, "fallback_rows").kind.id, "model.definition.function"
        )
        self.assertEqual(
            definition(root, "make_factory").kind.id, "model.definition.function"
        )
        self.assertEqual(
            nodes(child(definition(root, "make_factory"), "body"), "statements")[
                0
            ].kind.id,
            "model.definition.function",
        )
        paused = definition(root, "paused")
        (yield_stmt,) = nodes(child(paused, "body"), "statements")
        self.assertEqual(child(yield_stmt, "value").kind.id, "model.value.yield")
        self.assertIsNone(child(yield_stmt, "value").get("value"))
        self.assertEqual(
            child(
                nodes(child(definition(root, "make_factory"), "body"), "statements")[
                    -1
                ],
                "value",
            ).get("name"),
            "local_generator",
        )
        for item in root.walk():
            self.assertEqual(
                tuple(p.role for p in item.parts()),
                tuple(
                    c.role
                    for c in shikake.kind_index().require_structure(item.kind.id).parts
                ),
            )

    def test_generator_in_class_keeps_composition_without_method_kind(self) -> None:
        klass = definition(shikake.parse_source(SAMPLE.read_text()), "Ledger")
        members = nodes(child(klass, "body"), "statements")
        self.assertEqual([m.get("name") for m in members], ["entries", "count"])
        self.assertEqual(members[0].kind.id, "model.definition.method")
        self.assertEqual(members[0].features, ("generator",))
        self.assertEqual(members[1].kind.id, "model.definition.method")
        self.assertEqual(
            child(nodes(child(members[0], "body"), "statements")[0], "value").kind.id,
            "model.value.yield_from",
        )

    def test_only_owned_yields_classify_generator(self) -> None:
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        yield 1\n"
            "    return inner\n"
            "def unreachable():\n"
            "    if False:\n"
            "        yield 1\n"
            "def only_expression():\n"
            "    return (x for x in xs)\n"
            "def named_generator():\n"
            "    name = (yield 1)\n"
            "    return name\n"
        )
        root = shikake.parse_source(source)
        self.assertEqual(definition(root, "outer").kind.id, "model.definition.function")
        self.assertEqual(
            definition(root, "unreachable").kind.id, "model.definition.function"
        )
        self.assertEqual(
            definition(root, "only_expression").kind.id, "model.definition.function"
        )
        self.assertEqual(
            definition(root, "named_generator").kind.id, "model.definition.function"
        )

    def test_nested_definition_header_and_comprehension_outer_iterable(self) -> None:
        # The default of a nested definition and a comprehension's outermost
        # iterable are evaluated in the enclosing function, not the nested body.
        source = (
            "def outer():\n"
            "    def inner(v=(yield 7)):\n"
            "        return v\n"
            "    return inner\n"
            "def other():\n"
            "    collected = [x for x in (yield range(3))]\n"
            "    return collected\n"
        )
        root = shikake.parse_source(source)
        self.assertEqual(definition(root, "outer").kind.id, "model.definition.function")
        self.assertEqual(definition(root, "other").kind.id, "model.definition.function")
        nested = nodes(child(definition(root, "outer"), "body"), "statements")[0]
        self.assertEqual(nested.kind.id, "model.definition.function")
        (parameter,) = nodes(nested, "parameters")
        self.assertEqual(child(parameter, "default").kind.id, "model.value.yield")

    def test_yield_without_operand_differs_from_explicit_none(self) -> None:
        root = shikake.parse_source("def a():\n    yield\ndef b():\n    yield None\n")
        a = child(nodes(child(definition(root, "a"), "body"), "statements")[0], "value")
        b = child(nodes(child(definition(root, "b"), "body"), "statements")[0], "value")
        self.assertIsNone(a.get("value"))
        self.assertEqual(child(b, "value").kind.id, "model.value.literal.special.none")

    def test_override_candidates_support_generator_class_members(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "work"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "base.py").write_text(
                "class Base:\n    def f(self):\n        yield 1\n", encoding="utf-8"
            )
            (folder / "sub.py").write_text(
                "from .base import Base\nclass Child(Base):\n"
                "    def f(self):\n        yield from (1, 2)\n",
                encoding="utf-8",
            )
            pkg = shikake.parse_package(folder)
            self.assertEqual(len(pkg.override_candidates), 1)
            candidate = pkg.override_candidates[0]
            self.assertEqual(candidate.method.kind.id, "model.definition.method")
            self.assertEqual(candidate.base_method.kind.id, "model.definition.method")
            self.assertEqual(candidate.method.features, ("generator",))
            self.assertEqual(candidate.base_method.features, ("generator",))
            self.assertEqual(pkg.overrides_for(candidate.method), (candidate,))

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_modeling_and_async_remain_bounded(self) -> None:
        src = "def make():\n    yield 1\n    type Item = int\n    yield from xs\n"
        partial = shikake.inspect_source(src)
        self.assertFalse(partial.complete)
        assert partial.model is not None
        fn = nodes(partial.model, "body")[0]
        self.assertEqual(fn.kind.id, "model.definition.function")
        self.assertEqual(fn.features, ("generator",))
        self.assertEqual(
            [n.kind.id for n in nodes(child(fn, "body"), "statements")],
            ["model.statement.expression"] * 2,
        )
        self.assertEqual([issue.node_type for issue in partial.issues], ["TypeAlias"])
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(src)
        async_generator = nodes(
            shikake.parse_source("async def f():\n    yield 1\n"), "body"
        )[0]
        self.assertEqual(async_generator.kind.id, "model.definition.function")
        self.assertEqual(async_generator.features, ("async", "generator"))

    def test_trusted_example_behaves_as_expected_independently(self) -> None:
        scope = runpy.run_path(str(SAMPLE))
        self.assertEqual(list(scope["filtered_rows"]([1, 2, 3])), [2, 3, 99])
        self.assertEqual(list(scope["Ledger"]().entries([4, 5])), [4, 5])
        self.assertEqual(list(scope["make_factory"]()()), [42])


if __name__ == "__main__":
    unittest.main()
