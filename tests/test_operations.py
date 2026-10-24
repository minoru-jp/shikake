"""Tests for written operation Kinds and the nested Model contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SAMPLE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "quote_rules.py"


def child(node: Model, role: str) -> Model:
    result = node.get(role)
    assert isinstance(result, Model)
    return result


def children(node: Model, role: str) -> tuple[Model, ...]:
    result = node.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(item, Model) for item in result)
    return cast(tuple[Model, ...], result)


def value_expr(source: str) -> Model:
    root = shikake.parse_source(f"result = {source}\n")
    (statement,) = children(root, "body")
    return child(statement, "value")


class OperationKindTests(unittest.TestCase):
    def test_every_comparison_operator_has_one_kind(self) -> None:
        cases = (
            ("==", "equal"),
            ("!=", "not_equal"),
            ("<", "less"),
            ("<=", "less_equal"),
            (">", "greater"),
            (">=", "greater_equal"),
            ("is", "is"),
            ("is not", "is_not"),
            ("in", "in"),
            ("not in", "not_in"),
        )
        index = shikake.kind_index()
        for symbol, name in cases:
            with self.subTest(operator=symbol):
                model = value_expr(f"a {symbol} b")
                self.assertEqual(
                    model.kind.id, f"model.value.operation.comparison.{name}"
                )
                self.assertEqual(child(model, "left").get("name"), "a")
                self.assertEqual(child(model, "right").get("name"), "b")
                self.assertTrue(
                    index.is_a(model.kind.id, "model.value.operation.comparison")
                )
                self.assertEqual(
                    tuple(p.role for p in model.parts()), ("left", "right")
                )

    def test_chain_is_not_rewritten_to_and_or_binary_comparisons(self) -> None:
        expression = value_expr("low < mid <= high is not None")
        self.assertEqual(expression.kind.id, "model.value.operation.comparison.chained")
        self.assertEqual(child(expression, "left").get("name"), "low")
        steps = children(expression, "comparisons")
        self.assertEqual(
            [item.kind.id for item in steps],
            ["model.structural_part.comparison_step"] * 3,
        )
        self.assertEqual(
            [item.get("operator") for item in steps], ["<", "<=", "is not"]
        )
        self.assertEqual(
            [child(item, "right").get("name") for item in steps[:2]], ["mid", "high"]
        )
        self.assertIsNone(child(steps[2], "right").get("value"))
        self.assertTrue(all(step.span is not None for step in steps))
        self.assertEqual(len(tuple(expression.walk())), 8)
        self.assertTrue(
            shikake.kind_index().is_a(steps[0].kind.id, "model.structural_part")
        )
        self.assertFalse(shikake.kind_index().is_a(steps[0].kind.id, "model.value"))

    def test_boolean_operator_uses_ordered_values_not_binary_expansion(self) -> None:
        model = value_expr("a and b and c")
        self.assertEqual(model.kind.id, "model.value.operation.logical.and")
        self.assertEqual(
            [child.get("name") for child in children(model, "values")], ["a", "b", "c"]
        )
        outer = value_expr("a and b or c")
        self.assertEqual(outer.kind.id, "model.value.operation.logical.or")
        values = children(outer, "values")
        self.assertEqual(values[0].kind.id, "model.value.operation.logical.and")
        self.assertEqual(values[1].get("name"), "c")
        self.assertTrue(
            shikake.kind_index().is_a(outer.kind.id, "model.value.operation.logical")
        )

    def test_binary_operators_are_all_covered_without_conversion(self) -> None:
        cases = {
            "+": "addition",
            "-": "subtraction",
            "*": "multiplication",
            "@": "matrix_multiplication",
            "/": "division",
            "//": "floor_division",
            "%": "modulo",
            "**": "power",
            "<<": "left_shift",
            ">>": "right_shift",
            "&": "bitwise_and",
            "|": "bitwise_or",
            "^": "bitwise_xor",
        }
        for operator, name in cases.items():
            with self.subTest(operator=operator):
                model = value_expr(f"a {operator} b")
                self.assertEqual(model.kind.id, f"model.value.operation.{name}")
                self.assertEqual(child(model, "left").get("name"), "a")
                self.assertEqual(child(model, "right").get("name"), "b")
        union_annotation = shikake.parse_source("value: int | None\n")
        (definition,) = children(union_annotation, "body")
        self.assertEqual(
            child(definition, "annotation").kind.id, "model.value.operation.bitwise_or"
        )

    def test_unary_operators_keep_distinct_kinds_and_operands(self) -> None:
        for token, name in (
            ("not", "not"),
            ("+", "positive"),
            ("-", "negative"),
            ("~", "bitwise_invert"),
        ):
            with self.subTest(operator=token):
                model = value_expr(f"{token} a")
                self.assertEqual(model.kind.id, f"model.value.operation.{name}")
                self.assertEqual(child(model, "operand").get("name"), "a")
                self.assertTrue(
                    shikake.kind_index().is_a(
                        model.kind.id, "model.value.operation.unary"
                    )
                )

    def test_kind_index_has_unique_ids_and_valid_contracts(self) -> None:
        kinds = shikake.kind_index().all_kinds()
        self.assertEqual(len(kinds), 142)
        self.assertEqual(len({kind.id for kind in kinds}), len(kinds))
        for kind in kinds:
            structure = shikake.kind_index().structure_of(kind.id)
            if structure is None:
                continue
            self.assertEqual(
                len({part.role for part in structure.parts}),
                len(structure.parts),
            )

    def test_realistic_sample_keeps_nested_values_and_blocks(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        root = shikake.parse_source(source)
        self.assertTrue(shikake.inspect_source(source).complete)
        function = children(root, "body")[-1]
        self.assertEqual(function.get("name"), "quote_total")
        block = child(function, "body")
        (first_branch, _subtotal, second_branch, _return) = children(
            block, "statements"
        )
        condition = child(children(first_branch, "paths")[0], "condition")
        self.assertEqual(condition.kind.id, "model.value.operation.logical.or")
        left = children(condition, "values")[0]
        self.assertEqual(left.kind.id, "model.value.operation.not")
        chain = child(left, "operand")
        self.assertEqual(chain.kind.id, "model.value.operation.comparison.chained")
        self.assertEqual(
            [c.get("operator") for c in children(chain, "comparisons")], ["<=", "<="]
        )
        self.assertEqual(
            child(children(second_branch, "paths")[0], "condition").kind.id,
            "model.value.operation.logical.and",
        )
        nodes = tuple(root.walk())
        self.assertTrue(
            all(
                node.kind.id in {k.id for k in shikake.kind_index().all_kinds()}
                for node in nodes
            )
        )

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_unsupported_syntax_is_still_reported(self) -> None:
        source = "x = 1\ntype Unmodeled = int\ny = -2\n"
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)
        inspected = shikake.inspect_source(source)
        self.assertFalse(inspected.complete)
        self.assertEqual(len(inspected.issues), 1)
        self.assertEqual(inspected.issues[0].node_type, "TypeAlias")
        assert inspected.model is not None
        self.assertEqual(len(children(inspected.model, "body")), 2)


if __name__ == "__main__":
    unittest.main()
