"""Written context entries and value-comprehension clauses remain navigable."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SAMPLE = (
    Path(__file__).resolve().parents[1] / "tests/fixtures/context_comprehensions.py"
)


def child(model: Model, role: str) -> Model:
    item = model.get(role)
    assert isinstance(item, Model)
    return item


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    items = model.get(role)
    assert isinstance(items, tuple)
    return cast(tuple[Model, ...], items)


def expression(source: str) -> Model:
    (assignment,) = nodes(shikake.parse_source(f"output = {source}\n"), "body")
    return child(assignment, "value")


class ContextComprehensionTests(unittest.TestCase):
    def test_contexts_preserve_multiple_items_and_optional_targets(self) -> None:
        source = (
            "with manager() as (name, *rest), monitor(), other() as slot:\n"
            "    store(name)\n"
            "    pass\n"
        )
        (context,) = nodes(shikake.parse_source(source), "body")
        self.assertEqual(context.kind.id, "model.statement.control.context_block")
        self.assertEqual([part.role for part in context.parts()], ["contexts", "body"])
        entries = nodes(context, "contexts")
        self.assertEqual(len(entries), 3)
        self.assertEqual(
            [
                child(child(entry, "expression"), "callee").get("name")
                for entry in entries
            ],
            ["manager", "monitor", "other"],
        )
        target = child(entries[0], "target")
        self.assertEqual(target.kind.id, "model.value.collection.tuple")
        self.assertEqual(
            nodes(target, "elements")[1].kind.id, "model.structural_part.starred_target"
        )
        self.assertIsNone(entries[1].get("target"))
        self.assertEqual(child(entries[2], "target").get("name"), "slot")
        self.assertEqual(len(nodes(child(context, "body"), "statements")), 2)
        self.assertTrue(
            shikake.kind_index().is_a(context.kind.id, "model.statement.control")
        )

    def test_each_comprehension_form_has_appropriate_result_roles(self) -> None:
        forms = (
            ("[x + 1 for x in xs]", "list", ("element", "clauses")),
            ("{x + 1 for x in xs}", "set", ("element", "clauses")),
            ("{x: x + 1 for x in xs}", "dict", ("key", "value", "clauses")),
            ("(x + 1 for x in xs)", "generator", ("element", "clauses")),
        )
        for source, suffix, roles in forms:
            with self.subTest(source=source):
                model = expression(source)
                self.assertEqual(model.kind.id, f"model.value.comprehension.{suffix}")
                self.assertTrue(
                    shikake.kind_index().is_a(
                        model.kind.id, "model.value.comprehension"
                    )
                )
                self.assertEqual(tuple(part.role for part in model.parts()), roles)
                (clause,) = nodes(model, "clauses")
                self.assertEqual(child(clause, "target").get("name"), "x")
                self.assertEqual(child(clause, "iterable").get("name"), "xs")
                self.assertEqual(nodes(clause, "filters"), ())
                self.assertIs(clause.get("is_async"), False)
                if suffix == "dict":
                    self.assertEqual(child(model, "key").get("name"), "x")
                    self.assertEqual(
                        child(model, "value").kind.id, "model.value.operation.addition"
                    )
                else:
                    self.assertEqual(
                        child(model, "element").kind.id,
                        "model.value.operation.addition",
                    )

    def test_nested_clauses_filters_binding_and_construction_are_separate(self) -> None:
        source = "[(name, value) for name, items in groups if items for value in items if value > 0 if value < 100]"
        construction = expression(source)
        self.assertEqual(construction.kind.id, "model.value.comprehension.list")
        element = child(construction, "element")
        self.assertEqual(element.kind.id, "model.value.collection.tuple")
        clauses = nodes(construction, "clauses")
        self.assertEqual(len(clauses), 2)
        self.assertEqual(
            [e.get("name") for e in nodes(child(clauses[0], "target"), "elements")],
            ["name", "items"],
        )
        self.assertEqual(child(clauses[0], "iterable").get("name"), "groups")
        self.assertEqual(
            [c.get("name") for c in nodes(clauses[0], "filters")], ["items"]
        )
        self.assertEqual(child(clauses[1], "target").get("name"), "value")
        self.assertEqual(child(clauses[1], "iterable").get("name"), "items")
        self.assertEqual(
            [node.kind.id for node in nodes(clauses[1], "filters")],
            [
                "model.value.operation.comparison.greater",
                "model.value.operation.comparison.less",
            ],
        )
        self.assertNotIn(
            "model.statement.control.iteration",
            {node.kind.id for node in construction.walk()},
        )
        # A converter can select clause order/filters and the terminal value
        # through ordinary roles. Mica does not supply an expansion algorithm.
        plan = [
            (
                child(clause, "target").kind.id,
                len(nodes(clause, "filters")),
            )
            for clause in clauses
        ]
        self.assertEqual(
            plan, [("model.value.collection.tuple", 1), ("model.value.named", 2)]
        )

    def test_nested_constructions_keep_dict_key_value_and_original_order(self) -> None:
        model = expression("{name: [x for x in xs if x] for name, xs in groups if xs}")
        self.assertEqual(child(model, "key").get("name"), "name")
        inner = child(model, "value")
        self.assertEqual(inner.kind.id, "model.value.comprehension.list")
        self.assertEqual(len(nodes(model, "clauses")), 1)
        self.assertEqual(len(nodes(inner, "clauses")), 1)
        self.assertEqual(len(nodes(nodes(model, "clauses")[0], "filters")), 1)
        self.assertEqual(
            [part.role for part in nodes(model, "clauses")[0].parts()],
            ["target", "iterable", "filters", "is_async"],
        )

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_and_strict_do_not_swallow_unsupported_children(self) -> None:
        source = (
            "good = [x for x in xs]\n"
            "type Unmodeled = int\n"
            "type AlsoUnmodeled = str\n"
            "after = {x for x in ys}\n"
        )
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)
        inspected = shikake.inspect_source(source)
        self.assertFalse(inspected.complete)
        self.assertEqual(
            [issue.node_type for issue in inspected.issues], ["TypeAlias", "TypeAlias"]
        )
        self.assertEqual(
            [issue.skipped_node_type for issue in inspected.issues],
            ["TypeAlias", "TypeAlias"],
        )
        assert inspected.model is not None
        self.assertEqual(len(nodes(inspected.model, "body")), 2)
        self.assertEqual(
            [child(node, "value").kind.id for node in nodes(inspected.model, "body")],
            ["model.value.comprehension.list", "model.value.comprehension.set"],
        )

    def test_async_and_ignored_with_type_comment(self) -> None:
        root = shikake.parse_source(
            "async def f(xs):\n"
            "    async with ctx() as resource:\n"
            "        return [x async for x in xs]\n"
        )
        fn = nodes(root, "body")[0]
        self.assertEqual(fn.features, ("async",))
        block = child(fn, "body")
        context = nodes(block, "statements")[0]
        self.assertEqual(context.features, ("async",))
        result = nodes(child(context, "body"), "statements")[0]
        comprehension = child(result, "value")
        clause = nodes(comprehension, "clauses")[0]
        self.assertEqual(clause.features, ("async",))
        self.assertIs(clause.get("is_async"), True)
        (context,) = nodes(
            shikake.parse_source("with ctx():  # type: int\n    pass\n"), "body"
        )
        self.assertEqual(context.kind.id, "model.statement.control.context_block")

    def test_integrated_sample_is_fully_navigable(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        strict = shikake.parse_source(source)
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete)
        self.assertEqual(inspected.model, strict)
        self.assertEqual(len(shikake.kind_index().all_kinds()), 143)
        ids = {node.kind.id for node in strict.walk()}
        for suffix in ("list", "set", "dict", "generator"):
            self.assertIn("model.value.comprehension." + suffix, ids)
        self.assertIn("model.statement.control.context_block", ids)
        self.assertIn("model.structural_part.comprehension_clause", ids)
        self.assertIn("model.structural_part.context_entry", ids)


if __name__ == "__main__":
    unittest.main()
