"""Expression-scope boundaries for lambda defaults and comprehensions.

Registered interfaces and built-in Collection recognition use the same
syntax-only expression frames. No new lexical/name resolver is required.
"""

from __future__ import annotations

import ast
import unittest

import shikake
from shikake._mica.ast_facts import collect_syntax_facts
from shikake.external import ExternalDefinitions, ExternalDefinitionsBuilder


def _kinds(source: str, definitions: ExternalDefinitions | None = None) -> list[str]:
    if definitions is None:
        model = shikake.parse_source(source)
    else:
        model = shikake.parse_source(source, definitions=definitions)
    return [node.kind.id for node in model.walk()]


class ExpressionFrameReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definitions = (
            ExternalDefinitionsBuilder()
            .add_call("demo.ops:clamp", "demo.operation.clamp", ("x", "y", "z"))
            .add_generic("demo.ops:Array", "demo.generic.array", ("item",))
            .build()
        )

    def test_expression_frame_can_be_called_before_expression_scopes(self) -> None:
        tree = ast.parse("value = (lambda item: item + other)(1)\nx = free(1)")
        facts = collect_syntax_facts(tree, include_references=True)
        self.assertIsNone(facts._expression_index)
        item = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id == "item"
            and isinstance(node.ctx, ast.Load)
        )
        frame = facts.expression_frame(item)
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertIn("item", frame.names)
        self.assertIsNotNone(facts._expression_index)
        first_index = facts._expression_index
        outside_call = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "free"
        )
        self.assertIsNone(facts.expression_frame(outside_call))
        self.assertIs(facts._expression_index, first_index)

    def test_lambda_defaults_evaluate_outside_lambda_frame(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "fn = lambda clamp=clamp(1, 2, 3), *, "
            "other=clamp(4, 5, 6): clamp(7, 8, 9)\n"
        )
        kinds = _kinds(source, self.definitions)
        self.assertEqual(kinds.count("demo.operation.clamp"), 2)
        self.assertEqual(kinds.count("model.value.call"), 1)

    def test_lambda_default_still_sees_enclosing_lambda_parameter(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "fn = lambda clamp: (lambda inner=clamp(1, 2, 3): "
            "clamp(4, 5, 6))\n"
        )
        kinds = _kinds(source, self.definitions)
        self.assertNotIn("demo.operation.clamp", kinds)
        self.assertEqual(kinds.count("model.value.call"), 2)

    def test_first_comprehension_iterable_uses_outer_frame(self) -> None:
        examples = (
            "[item for clamp in clamp(1, 2, 3) if clamp(4, 5, 6)]",
            "{item for clamp in clamp(1, 2, 3) if clamp(4, 5, 6)}",
            "{item: item for clamp in clamp(1, 2, 3) if clamp(4, 5, 6)}",
            "(item for clamp in clamp(1, 2, 3) if clamp(4, 5, 6))",
        )
        for example in examples:
            with self.subTest(example=example):
                kinds = _kinds(
                    "from demo.ops import clamp\nresult = " + example,
                    self.definitions,
                )
                self.assertEqual(kinds.count("demo.operation.clamp"), 1)
                self.assertEqual(kinds.count("model.value.call"), 1)

    def test_subsequent_comprehension_iterables_use_inner_frame(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "result = [x for x in clamp(1, 2, 3) "
            "for clamp in clamp(4, 5, 6) if clamp(7, 8, 9)]"
        )
        kinds = _kinds(source, self.definitions)
        self.assertEqual(kinds.count("demo.operation.clamp"), 1)
        self.assertEqual(kinds.count("model.value.call"), 2)

    def test_enclosing_lambda_shadows_first_comprehension_iterable(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "fn = lambda clamp: [item for item in clamp(1, 2, 3) "
            "if clamp(4, 5, 6)]"
        )
        kinds = _kinds(source, self.definitions)
        self.assertEqual(kinds.count("demo.operation.clamp"), 0)
        self.assertEqual(kinds.count("model.value.call"), 2)

    def test_builtin_collection_first_iterable_evaluates_outside(self) -> None:
        kinds = _kinds("result = [item for list in list() if list()]")
        self.assertEqual(kinds.count("model.value.collection.sequence"), 2)
        self.assertEqual(kinds.count("model.value.call"), 1)

    def test_registered_generic_in_first_iterable_evaluates_outside(self) -> None:
        source = "from demo.ops import Array\nresult = [v for Array in Array[int]]"
        kinds = _kinds(source, self.definitions)
        self.assertEqual(kinds.count("demo.generic.array"), 1)


if __name__ == "__main__":
    unittest.main()
