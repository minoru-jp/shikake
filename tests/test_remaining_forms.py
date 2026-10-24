"""AST-faithful lambda, assertion, deletion and declaration Models."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model, ModelFactory


def many(model: Model, role: str) -> tuple[Model, ...]:
    items = model.get(role)
    assert isinstance(items, tuple)
    assert all(isinstance(item, Model) for item in items)
    return cast(tuple[Model, ...], items)


def one(model: Model, role: str) -> Model:
    item = model.get(role)
    assert isinstance(item, Model)
    return item


class RemainingFormsTests(unittest.TestCase):
    def test_kind_and_structure_separation(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(len(index.all_kinds()), 143)
        self.assertEqual(len(index.all_structures()), 62)
        self.assertEqual(len(index.all_features()), 2)
        self.assertTrue(
            index.is_a(
                "model.statement.scope_declaration.global",
                "model.statement.scope_declaration",
            )
        )
        self.assertEqual(
            index.structure_of("model.statement.scope_declaration.global"),
            index.structure_of("model.statement.scope_declaration.nonlocal"),
        )
        self.assertIsNone(index.structure_of("model.statement.scope_declaration"))
        self.assertEqual(
            [
                (p.role, p.shape)
                for p in index.require_structure(
                    "model.statement.scope_declaration.global"
                ).parts
            ],
            [("names", "texts")],
        )
        self.assertFalse(
            index.is_a("model.value.function_expression", "model.definition.function")
        )

    def test_lambda_reuses_parameter_model_without_name_or_block(self) -> None:
        root = shikake.parse_source(
            "fn = lambda first, second=2, /, *args, flag=True, **kw: first + second\n"
        )
        (assignment,) = many(root, "body")
        anonymous = one(assignment, "value")
        self.assertEqual(anonymous.kind.id, "model.value.function_expression")
        self.assertEqual([p.role for p in anonymous.parts()], ["parameters", "body"])
        params = many(anonymous, "parameters")
        self.assertEqual(
            [p.get("name") for p in params], ["first", "second", "args", "flag", "kw"]
        )
        self.assertEqual(
            [p.get("category") for p in params],
            [
                "positional_only",
                "positional_only",
                "var_positional",
                "keyword_only",
                "var_keyword",
            ],
        )
        self.assertIsNone(params[0].get("default"))
        self.assertEqual(one(params[1], "default").get("value"), 2)
        self.assertEqual(one(params[3], "default").get("value"), True)
        self.assertEqual(
            one(anonymous, "body").kind.id, "model.value.operation.addition"
        )
        self.assertIsNotNone(anonymous.span)
        assert anonymous.span is not None
        self.assertEqual(anonymous.span.line, 1)

    def test_lambda_appears_in_both_expression_and_nested_positions(self) -> None:
        source = (
            "def f():\n"
            "    return [((lambda x: x + 1)(v)) for v in values]\n"
            "with ctx(lambda: 1):\n"
            "    pass\n"
        )
        parsed = shikake.parse_source(source)
        self.assertTrue(shikake.inspect_source(source).complete)
        self.assertEqual(
            [m.kind.id for m in parsed.walk()].count("model.value.function_expression"),
            2,
        )

    def test_assert_retains_condition_and_optional_message(self) -> None:
        parsed = shikake.parse_source(
            "assert amount > 0\nassert amount < limit, f'amount={amount}'\n"
        )
        simple, detailed = many(parsed, "body")
        self.assertEqual(simple.kind.id, "model.statement.assertion")
        self.assertIsNone(simple.get("message"))
        self.assertEqual(
            one(simple, "condition").kind.id, "model.value.operation.comparison.greater"
        )
        self.assertEqual(
            one(detailed, "message").kind.id, "model.value.interpolated_string"
        )
        self.assertEqual([p.role for p in detailed.parts()], ["condition", "message"])

    def test_delete_keeps_ordered_recursive_targets(self) -> None:
        parsed = shikake.parse_source("del records[key], owner.attr, (first, second)\n")
        (deletion,) = many(parsed, "body")
        self.assertEqual(deletion.kind.id, "model.statement.deletion")
        targets = many(deletion, "targets")
        self.assertEqual(
            [target.kind.id for target in targets],
            [
                "model.value.access.index",
                "model.value.access.attribute",
                "model.structural_part.sequence_target",
            ],
        )
        self.assertEqual(
            [x.get("name") for x in many(targets[2], "elements")], ["first", "second"]
        )
        self.assertEqual(
            [n.kind.id for n in deletion.walk()].count("model.value.named"), 5
        )

    def test_scope_declarations_store_written_names_not_resolutions(self) -> None:
        source = (
            "counter = 0\n"
            "def outer():\n"
            "    tally = 1\n"
            "    def inner():\n"
            "        global counter, other\n"
            "        nonlocal tally\n"
            "        return tally\n"
        )
        tree = shikake.parse_source(source)
        decls = [
            node
            for node in tree.walk()
            if node.kind.id.startswith("model.statement.scope_declaration.")
        ]
        self.assertEqual(
            [node.kind.id.split(".")[-1] for node in decls], ["global", "nonlocal"]
        )
        self.assertEqual(decls[0].get("names"), ("counter", "other"))
        self.assertEqual(decls[1].get("names"), ("tally",))
        self.assertEqual(len(list(decls[0].walk())), 1)  # texts are not Model children
        self.assertEqual([p.role for p in decls[0].parts()], ["names"])

    def test_texts_shape_rejects_other_values(self) -> None:
        factory = ModelFactory(shikake.kind_index())
        kind = "model.statement.scope_declaration.global"
        for invalid in (["a", "b"], ("a", 42), "a", (1,)):
            with self.subTest(value=invalid), self.assertRaises(TypeError):
                factory.make(kind, names=invalid)  # type: ignore[arg-type]
        correct = factory.make(kind, names=("a", "b"))
        self.assertEqual(correct.get("names"), ("a", "b"))
        self.assertEqual(tuple(correct.walk()), (correct,))

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_keeps_supported_siblings_and_diagnoses_unadopted(self) -> None:
        source = (
            "assert 1\nfactory = lambda n: n + 1\ntype Invalid = int\ndel data[key]\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertFalse(inspected.complete)
        self.assertEqual([issue.node_type for issue in inspected.issues], ["TypeAlias"])
        assert inspected.model is not None
        self.assertEqual(
            [node.kind.id for node in many(inspected.model, "body")],
            [
                "model.statement.assertion",
                "model.statement.assignment",
                "model.statement.deletion",
            ],
        )
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)

    def test_package_parsing_does_not_execute_scope_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "sample_forms"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "logic.py").write_text(
                "def outer():\n    count = 0\n    def inner():\n"
                "        nonlocal count\n        assert count >= 0\n"
                "        del registry['key']\n    return lambda x: x + 1\n",
                encoding="utf-8",
            )
            parsed = shikake.parse_package(package)
            self.assertEqual(parsed.override_candidates, ())
            self.assertTrue(
                any(
                    n.kind.id == "model.statement.deletion" for n in parsed.model.walk()
                )
            )
            self.assertTrue(
                any(
                    n.kind.id == "model.value.function_expression"
                    for n in parsed.model.walk()
                )
            )


if __name__ == "__main__":
    unittest.main()
