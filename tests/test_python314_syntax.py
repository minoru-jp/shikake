"""Python 3.14 t-string/PEP 758 contracts, including cross-version AST simulation."""

from __future__ import annotations

import ast
import sys
import unittest
from typing import cast
from unittest.mock import patch

import shikake
from shikake._mica import parser
from shikake._mica.model import Model
from shikake._mica.modeling import python314


class _TemplateStr(ast.expr):
    """Synthetic 3.14 AST node for testing on Python 3.11--3.13."""

    _fields = ("values",)

    def __init__(self, values: list[ast.expr]) -> None:
        self.values = values


class _Interpolation(ast.expr):
    _fields = ("value", "str", "conversion", "format_spec")

    def __init__(
        self,
        value: ast.expr,
        expression_text: str | None,
        conversion: int = -1,
        format_spec: ast.JoinedStr | None = None,
    ) -> None:
        self.value = value
        self.str = expression_text
        self.conversion = conversion
        self.format_spec = format_spec


def _name(name: str) -> ast.Name:
    return ast.Name(id=name, ctx=ast.Load())


class Python314SyntaxTests(unittest.TestCase):
    def _simulated(self, node: ast.expr) -> Model:
        with (
            patch.object(python314, "_TEMPLATE_STR", _TemplateStr),
            patch.object(python314, "_INTERPOLATION", _Interpolation),
        ):
            return parser._Builder(shikake.kind_index()).expression(node)

    def test_template_ast_preserves_order_conversion_and_nested_format(self) -> None:
        spec = ast.JoinedStr(
            values=[
                ast.Constant(value=">"),
                ast.FormattedValue(value=_name("width"), conversion=-1),
            ]
        )
        node = _TemplateStr(
            [
                ast.Constant(value="Hello "),
                _Interpolation(_name("name"), " name ", ord("r"), spec),
                ast.Constant(value="!"),
            ]
        )
        result = self._simulated(node)
        self.assertEqual(result.kind.id, "model.value.template_string")
        left, interpolation, right = result.get_nodes("parts")
        self.assertEqual((left.get("value"), right.get("value")), ("Hello ", "!"))
        self.assertEqual(
            interpolation.kind.id, "model.structural_part.template_interpolation"
        )
        self.assertEqual(interpolation.get_node("value").get("name"), "name")
        self.assertEqual(interpolation.get("expression_text"), " name ")
        self.assertEqual(interpolation.get("conversion"), "r")
        format_model = interpolation.get_node("format_spec")
        self.assertEqual(format_model.kind.id, "model.value.interpolated_string")
        self.assertEqual(
            format_model.get_nodes("parts")[1].kind.id,
            "model.structural_part.formatted_field",
        )

    def test_template_interpolation_allows_missing_expression_text(self) -> None:
        result = self._simulated(_TemplateStr([_Interpolation(_name("x"), None)]))
        interp = result.get_nodes("parts")[0]
        self.assertIsNone(interp.get("expression_text"))
        self.assertIsNone(interp.get("conversion"))
        self.assertIsNone(interp.get("format_spec"))

    def test_unknown_conversion_fails_conservatively(self) -> None:
        node = _TemplateStr([_Interpolation(_name("x"), "x", ord("z"))])
        with self.assertRaisesRegex(parser.UnsupportedSyntaxError, "conversion"):
            self._simulated(node)

    def test_deep_template_chain_does_not_use_python_recursion(self) -> None:
        node: ast.expr = _name("leaf")
        for _ in range(1200):
            node = _TemplateStr([_Interpolation(node, "leaf")])
        result = self._simulated(node)
        kinds = [part.kind.id for part in result.walk()]
        self.assertEqual(kinds.count("model.value.template_string"), 1200)
        self.assertEqual(
            kinds.count("model.structural_part.template_interpolation"), 1200
        )

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_real_tstring_strict_and_partial(self) -> None:
        source = 'result = t"Hello {name!r:>{width}}!"'
        model = shikake.parse_source(source)
        template = model.get_nodes("body")[0].get_node("value")
        self.assertEqual(template.kind.id, "model.value.template_string")
        self.assertEqual(len(template.get_nodes("parts")), 3)
        interpolation = template.get_nodes("parts")[1]
        self.assertEqual(interpolation.get("expression_text"), "name")
        self.assertEqual(interpolation.get("conversion"), "r")
        self.assertEqual(
            interpolation.get_node("format_spec").kind.id,
            "model.value.interpolated_string",
        )
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete)
        self.assertEqual(inspected.model, model)

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_tstring_fragments_and_escaped_braces(self) -> None:
        template = (
            shikake.parse_source('x = t"{{prefix}}{a}{b!s}"')
            .get_nodes("body")[0]
            .get_node("value")
        )
        fragments = template.get_nodes("parts")
        self.assertEqual(fragments[0].get("value"), "{prefix}")
        self.assertEqual(
            [item.get("expression_text") for item in fragments[1:]], ["a", "b"]
        )
        self.assertEqual(fragments[-1].get("conversion"), "s")

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_unparenthesized_except_and_except_star_use_existing_model(self) -> None:
        for marker, grouped in (("except", False), ("except*", True)):
            with self.subTest(marker=marker):
                source = (
                    f"try:\n    run()\n{marker} ValueError, TypeError:\n    recover()\n"
                )
                root = shikake.parse_source(source)
                statement = root.get_nodes("body")[0]
                self.assertEqual(
                    statement.kind.id, "model.statement.control.exception_handling"
                )
                self.assertIs(statement.get("grouped"), grouped)
                handler = statement.get_nodes("handlers")[0]
                caught = handler.get_node("exception")
                self.assertEqual(caught.kind.id, "model.value.collection.tuple")
                self.assertEqual(
                    [item.get("name") for item in caught.get_nodes("elements")],
                    ["ValueError", "TypeError"],
                )
                bracketed = source.replace(
                    "ValueError, TypeError:", "(ValueError, TypeError):"
                )
                other = shikake.parse_source(bracketed).get_nodes("body")[0]
                self.assertEqual(
                    [item.kind.id for item in other.walk()],
                    [item.kind.id for item in statement.walk()],
                )

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_tstring_debug_interpolation_implicit_repr(self) -> None:
        template = (
            shikake.parse_source('result = t"{x=}"')
            .get_nodes("body")[0]
            .get_node("value")
        )
        literal, interpolation = template.get_nodes("parts")
        self.assertEqual(literal.get("value"), "x=")
        self.assertEqual(interpolation.get("expression_text"), "x")
        self.assertEqual(interpolation.get("conversion"), "r")
        self.assertIsNone(interpolation.get("format_spec"))

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_tstring_debug_interpolation_with_format_spec(self) -> None:
        source = 'result = t"{x = :>10}"'
        template = shikake.parse_source(source).get_nodes("body")[0].get_node("value")
        parts = template.get_nodes("parts")
        interpolation = parts[-1]
        self.assertEqual(
            interpolation.kind.id, "model.structural_part.template_interpolation"
        )
        self.assertEqual(interpolation.get_node("value").get("name"), "x")
        self.assertIsNone(interpolation.get("conversion"))
        format_spec = interpolation.get_node("format_spec")
        self.assertEqual(format_spec.kind.id, "model.value.interpolated_string")
        self.assertEqual(format_spec.get_nodes("parts")[0].get("value"), ">10")

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_adjacent_tstrings_form_one_template_model(self) -> None:
        source = 'result = t"hello " t"{x}"'
        root = shikake.parse_source(source)
        templates = [
            item
            for item in root.walk()
            if item.kind.id == "model.value.template_string"
        ]
        self.assertEqual(len(templates), 1)
        parts = templates[0].get_nodes("parts")
        self.assertEqual(parts[0].get("value"), "hello ")
        self.assertEqual(parts[-1].get("expression_text"), "x")

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_mixed_literal_prefixes_are_syntax_errors(self) -> None:
        for text in ('t"" ""', 't"" f""', 'bt""'):
            with self.subTest(text=text):
                source = f"result = {text}"
                with self.assertRaises(SyntaxError):
                    shikake.parse_source(source)
                inspected = shikake.inspect_source(source)
                self.assertFalse(inspected.complete)
                self.assertTrue(
                    any(issue.category == "syntax_error" for issue in inspected.issues)
                )

    @unittest.skipUnless(sys.version_info >= (3, 14), "requires Python 3.14+")
    def test_tstring_debug_spans_preserve_overlapping_ast_locations(self) -> None:
        source = 'result = t"{value=}"'
        parsed = ast.parse(source)
        assignment = parsed.body[0]
        assert isinstance(assignment, ast.Assign)
        template_ast = cast(ast.JoinedStr, assignment.value)
        ast_parts = template_ast.values
        model = shikake.parse_source(source).get_nodes("body")[0].get_node("value")
        model_parts = model.get_nodes("parts")
        self.assertEqual(len(ast_parts), len(model_parts))
        self.assertEqual(len(model_parts), 2)
        for ast_part, model_part in zip(ast_parts, model_parts, strict=True):
            with self.subTest(kind=model_part.kind.id):
                span = model_part.span
                self.assertIsNotNone(span)
                assert span is not None
                self.assertEqual(
                    (span.line, span.column, span.end_line, span.end_column),
                    (
                        ast_part.lineno,
                        ast_part.col_offset,
                        ast_part.end_lineno,
                        ast_part.end_col_offset,
                    ),
                )

        literal = model_parts[0].span
        interpolation = model_parts[1].span
        assert literal is not None and interpolation is not None
        # The debug-label literal can overlap the following Interpolation.
        self.assertLess(
            (literal.line, literal.column),
            (interpolation.end_line, interpolation.end_column),
        )
        self.assertLess(
            (interpolation.line, interpolation.column),
            (literal.end_line, literal.end_column),
        )
