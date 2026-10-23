"""Async modeling: Kind/Structure unchanged, async Feature at written sites."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model, ModelFactory


def models(node: Model, role: str) -> tuple[Model, ...]:
    result = node.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(item, Model) for item in result)
    return cast(tuple[Model, ...], result)


def model(node: Model, role: str) -> Model:
    result = node.get(role)
    assert isinstance(result, Model)
    return result


def definition(root: Model, name: str) -> Model:
    return next(node for node in models(root, "body") if node.get("name") == name)


class AsyncModelingTests(unittest.TestCase):
    def test_kind_structure_feature_independence(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(len(index.all_kinds()), 143)
        self.assertEqual(len(index.all_structures()), 61)
        self.assertEqual(
            [feature.id for feature in index.all_features()], ["async", "lazy"]
        )
        self.assertIs(
            index.require_structure("model.value.await"),
            index.require_structure("model.value.yield_from"),
        )
        feature = index.all_features()[0]
        self.assertIn(
            "model.structural_part.comprehension_clause", feature.allowed_kind_ids
        )
        self.assertNotIn("model.value.comprehension", feature.allowed_kind_ids)
        for kind in (
            "model.definition.function",
            "model.definition.method",
            "model.definition.generator",
            "model.statement.control.iteration",
            "model.statement.control.context_block",
            "model.structural_part.comprehension_clause",
        ):
            index.validate_features(kind, ("async",))
        for kind in (
            "model.value.await",
            "model.value.named",
            "model.value.comprehension.list",
        ):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                index.validate_features(kind, ("async",))
        self.assertFalse(
            index.is_a("model.definition.generator", "model.definition.function")
        )

    def test_function_method_generator_and_header_info(self) -> None:
        source = """
async def plain(x: int = 3) -> int:
    return x

async def stream(xs):
    if False:
        yield None

class Service:
    @staticmethod
    async def fetch(x):
        return await remote(x)

    async def entries(self):
        yield 1

    async def outer(self):
        async def inner():
            yield 2
        return inner
"""
        root = shikake.parse_source(source)
        plain = definition(root, "plain")
        self.assertEqual(plain.kind.id, "model.definition.function")
        self.assertEqual(plain.features, ("async",))
        self.assertEqual(model(plain, "returns").get("name"), "int")
        stream = definition(root, "stream")
        self.assertEqual(stream.kind.id, "model.definition.generator")
        self.assertEqual(stream.features, ("async",))
        service = definition(root, "Service")
        members = models(model(service, "body"), "statements")
        self.assertEqual(
            [member.kind.id for member in members],
            [
                "model.definition.method",
                "model.definition.generator",
                "model.definition.method",
            ],
        )
        self.assertTrue(all(member.features == ("async",) for member in members))
        await_node = next(
            node for node in members[0].walk() if node.kind.id == "model.value.await"
        )
        self.assertEqual(
            model(model(await_node, "value"), "callee").get("name"), "remote"
        )
        nested = models(model(members[-1], "body"), "statements")[0]
        self.assertEqual(nested.kind.id, "model.definition.generator")
        self.assertEqual(nested.features, ("async",))
        self.assertEqual(members[-1].kind.id, "model.definition.method")

    def test_async_for_and_with_keep_written_parts(self) -> None:
        source = """
async def run(stream, cm):
    async with cm() as (a, b), cm():
        async for x, *rest in stream:
            value = await transform(x)
        else:
            pass
    with cm():
        for y in (1, 2):
            pass
"""
        fn = models(shikake.parse_source(source), "body")[0]
        outer = models(model(fn, "body"), "statements")
        context = outer[0]
        self.assertEqual(context.kind.id, "model.statement.control.context_block")
        self.assertEqual(context.features, ("async",))
        entries = models(context, "contexts")
        self.assertEqual(len(entries), 2)
        self.assertEqual(
            model(entries[0], "target").kind.id, "model.value.collection.tuple"
        )
        self.assertIsNone(entries[1].get("target"))
        iteration = models(model(context, "body"), "statements")[0]
        self.assertEqual(iteration.kind.id, "model.statement.control.iteration")
        self.assertEqual(iteration.features, ("async",))
        self.assertEqual(
            model(iteration, "binding").kind.id, "model.value.collection.tuple"
        )
        self.assertIsNotNone(iteration.get("else_block"))
        assignment = models(model(iteration, "body"), "statements")[0]
        self.assertEqual(model(assignment, "value").kind.id, "model.value.await")
        self.assertEqual(outer[1].features, ())
        ordinary = models(model(outer[1], "body"), "statements")[0]
        self.assertEqual(ordinary.features, ())

    def test_comprehensions_have_clause_local_features_and_order(self) -> None:
        source = """
async def collect(groups):
    a = [await f(x) for group in groups async for x in group if x > 0]
    b = {x async for x in groups}
    c = {x: await f(x) async for x in groups}
    d = (x async for x in groups)
    e = [await f(x) for x in groups]
    return a
"""
        fn = models(shikake.parse_source(source), "body")[0]
        assignments = models(model(fn, "body"), "statements")[:5]
        kinds = [model(item, "value").kind.id for item in assignments]
        self.assertEqual(
            kinds,
            [
                "model.value.comprehension.list",
                "model.value.comprehension.set",
                "model.value.comprehension.dict",
                "model.value.comprehension.generator",
                "model.value.comprehension.list",
            ],
        )
        first = model(assignments[0], "value")
        clauses = models(first, "clauses")
        self.assertEqual([clause.features for clause in clauses], [(), ("async",)])
        self.assertEqual([clause.get("is_async") for clause in clauses], [False, True])
        self.assertEqual(len(models(clauses[1], "filters")), 1)
        self.assertEqual(model(first, "element").kind.id, "model.value.await")
        for assignment in assignments[1:4]:
            construction = model(assignment, "value")
            (clause,) = models(construction, "clauses")
            self.assertEqual(clause.features, ("async",))
            self.assertIs(clause.get("is_async"), True)
        only_await = model(assignments[4], "value")
        self.assertEqual(only_await.features, ())
        (ordinary_clause,) = models(only_await, "clauses")
        self.assertEqual(ordinary_clause.features, ())
        self.assertEqual(model(only_await, "element").kind.id, "model.value.await")

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_and_strict_for_nested_unsupported(self) -> None:
        source = """
async def process(stream):
    async for item in stream:
        type ItemAlias = int
        await use(item)
    return 1
"""
        with self.assertRaisesRegex(shikake.UnsupportedSyntaxError, "TypeAlias"):
            shikake.parse_source(source)
        partial = shikake.inspect_source(source)
        self.assertFalse(partial.complete)
        assert partial.model is not None
        fn = models(partial.model, "body")[0]
        self.assertEqual(fn.features, ("async",))
        iteration = models(model(fn, "body"), "statements")[0]
        self.assertEqual(iteration.features, ("async",))
        (statement,) = models(model(iteration, "body"), "statements")
        self.assertEqual(model(statement, "value").kind.id, "model.value.await")
        self.assertEqual([issue.node_type for issue in partial.issues], ["TypeAlias"])

    def test_package_override_candidates_with_async_method_and_generator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "pkg_async"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "base.py").write_text(
                "class Base:\n    async def read(self):\n        return 1\n",
                encoding="utf-8",
            )
            (folder / "child.py").write_text(
                "from .base import Base\n"
                "class Child(Base):\n    async def read(self):\n        yield 1\n",
                encoding="utf-8",
            )
            parsed = shikake.parse_package(folder)
            self.assertEqual(len(parsed.override_candidates), 1)
            candidate = parsed.override_candidates[0]
            self.assertEqual(candidate.method.kind.id, "model.definition.generator")
            self.assertEqual(candidate.base_method.kind.id, "model.definition.method")
            self.assertEqual(candidate.method.features, ("async",))
            self.assertEqual(candidate.base_method.features, ("async",))

    def test_model_factory_still_checks_feature_applicability(self) -> None:
        index = shikake.kind_index()
        factory = ModelFactory(index)
        with self.assertRaisesRegex(ValueError, "not applicable"):
            factory.make(
                "model.value.await",
                value=factory.make("model.value.named", name="x"),
                features=("async",),
            )
        tree = ast.parse("async def f():\n    await use()\n")
        self.assertIsInstance(tree.body[0], ast.AsyncFunctionDef)


if __name__ == "__main__":
    unittest.main()
