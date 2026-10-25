"""Slice, f-string, conditional value, set and ignored type checker metadata."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SAMPLE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "value_expressions.py"
)


def one(node: Model, role: str) -> Model:
    value = node.get(role)
    assert isinstance(value, Model)
    return value


def many(node: Model, role: str) -> tuple[Model, ...]:
    value = node.get(role)
    assert isinstance(value, tuple)
    assert all(isinstance(item, Model) for item in value)
    return cast(tuple[Model, ...], value)


def value(source: str) -> Model:
    statement = many(shikake.parse_source(f"result = {source}\n"), "body")[0]
    return one(statement, "value")


class ValueExpressionTests(unittest.TestCase):
    def test_slice_is_index_operand_with_omitted_bounds(self) -> None:
        model = value("items[1:9:2]")
        self.assertEqual(model.kind.id, "model.value.access.index")
        interval = one(model, "index")
        self.assertEqual(interval.kind.id, "model.value.slice")
        self.assertEqual(
            [one(interval, key).get("value") for key in ("start", "stop", "step")],
            [1, 9, 2],
        )
        empty = one(value("items[:][:]"), "index")
        self.assertEqual(
            tuple(part.value for part in empty.parts()), (None, None, None)
        )
        mixed = value("items[1:3, :, ...]")
        dimensions = many(one(mixed, "index"), "inputs")
        self.assertEqual(
            [item.kind.id for item in dimensions],
            [
                "model.value.slice",
                "model.value.slice",
                "model.value.literal.special.ellipsis",
            ],
        )
        self.assertEqual(one(dimensions[0], "start").get("value"), 1)
        self.assertIsNone(dimensions[1].get("start"))
        self.assertTrue(
            shikake.definition_index().classified_under(interval.kind.id, "model.value")
        )

    def test_formatted_string_keeps_order_conversion_and_nested_spec(self) -> None:
        model = value('f"Hello {name!r}, total={total:{width}.{precision}f}!"')
        self.assertEqual(model.kind.id, "model.value.interpolated_string")
        parts = many(model, "parts")
        self.assertEqual(
            [p.kind.id for p in parts],
            [
                "model.value.literal",
                "model.structural_part.formatted_field",
                "model.value.literal",
                "model.structural_part.formatted_field",
                "model.value.literal",
            ],
        )
        self.assertEqual(parts[0].get("value"), "Hello ")
        self.assertEqual(one(parts[1], "value").get("name"), "name")
        self.assertEqual(parts[1].get("conversion"), "r")
        self.assertIsNone(parts[1].get("format_spec"))
        self.assertEqual(parts[2].get("value"), ", total=")
        nested = one(parts[3], "format_spec")
        self.assertEqual(nested.kind.id, "model.value.interpolated_string")
        self.assertEqual(
            [p.kind.id for p in many(nested, "parts")],
            [
                "model.structural_part.formatted_field",
                "model.value.literal",
                "model.structural_part.formatted_field",
                "model.value.literal",
            ],
        )
        self.assertEqual(many(nested, "parts")[1].get("value"), ".")
        self.assertEqual(parts[-1].get("value"), "!")
        self.assertEqual(len(tuple(model.walk())), 15)

    def test_f_string_conversion_all_forms_and_escaped_braces(self) -> None:
        model = value('f"{{ {x!s} {y!a} {z} }}"')
        parts = many(model, "parts")
        self.assertEqual(parts[0].get("value"), "{ ")
        fields = [p for p in parts if p.kind.id.endswith("formatted_field")]
        self.assertEqual([p.get("conversion") for p in fields], ["s", "a", None])
        self.assertEqual(parts[-1].get("value"), " }")
        debug = value('f"{x=}"')
        self.assertEqual(many(debug, "parts")[0].get("value"), "x=")
        self.assertEqual(many(debug, "parts")[1].get("conversion"), "r")

    def test_conditional_expression_is_value_not_statement_branch(self) -> None:
        selection = value("0 if amount > 100 else rate")
        self.assertEqual(selection.kind.id, "model.value.selection")
        self.assertEqual(
            one(selection, "condition").kind.id,
            "model.value.operation.comparison.greater",
        )
        self.assertEqual(one(selection, "when_true").get("value"), 0)
        self.assertEqual(one(selection, "when_false").get("name"), "rate")
        self.assertFalse(
            shikake.definition_index().classified_under(
                selection.kind.id, "model.statement.branch"
            )
        )
        nested = value("a if ready else b if alternative else c")
        self.assertEqual(one(nested, "when_false").kind.id, "model.value.selection")

    def test_set_literal_is_collection_with_ordered_elements(self) -> None:
        model = value("{code, 'ready', (1, 2)}")
        self.assertEqual(model.kind.id, "model.value.collection.set")
        self.assertEqual(
            [part.kind.id for part in many(model, "inputs")],
            [
                "model.value.named",
                "model.value.literal",
                "model.value.collection.sequence",
            ],
        )
        self.assertTrue(
            shikake.definition_index().classified_under(
                model.kind.id, "model.value.collection"
            )
        )
        self.assertEqual(value("{}").kind.id, "model.value.collection.mapping")
        self.assertEqual(len(many(value("{1}"), "inputs")), 1)

    def test_type_ignore_metadata_is_not_a_model_or_diagnostic(self) -> None:
        source = (
            "# type: ignore\n"
            "x = 1  # type: ignore[assignment]\n"
            "def get():  # type: ignore[misc]\n"
            "    return x  # type: ignore\n"
        )
        strict = shikake.parse_source(source)
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete)
        self.assertEqual(inspected.issues, ())
        self.assertEqual(inspected.model, strict)
        self.assertEqual(len(many(strict, "body")), 2)
        self.assertEqual(len(shikake.definition_index().all_kinds()), 142)
        # A type comment has no role in Strict or Partial Model generation.
        self.assertTrue(shikake.inspect_source("x = 1  # type: int\n").complete)

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_diagnostics_preserve_other_statements(self) -> None:
        source = "before = x[1:3]\ntype Unsupported = int\nafter = f'{before!r}'\n"
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)
        result = shikake.inspect_source(source)
        self.assertFalse(result.complete)
        self.assertEqual([issue.node_type for issue in result.issues], ["TypeAlias"])
        assert result.model is not None
        body = many(result.model, "body")
        self.assertEqual(len(body), 2)
        self.assertEqual(one(body[0], "value").kind.id, "model.value.access.index")
        self.assertEqual(
            one(body[1], "value").kind.id, "model.value.interpolated_string"
        )

    def test_realistic_source_strict_and_inspection_match(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        strict = shikake.parse_source(source)
        result = shikake.inspect_source(source)
        self.assertTrue(result.complete)
        self.assertEqual(result.model, strict)
        kinds = {node.kind.id for node in strict.walk()}
        self.assertTrue(
            {
                "model.value.slice",
                "model.value.interpolated_string",
                "model.value.selection",
                "model.value.collection.set",
                "model.structural_part.formatted_field",
            }.issubset(kinds)
        )


if __name__ == "__main__":
    unittest.main()
