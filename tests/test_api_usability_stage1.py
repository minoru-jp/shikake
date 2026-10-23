"""Machine-readable diagnostics and independent, non-coercing helper APIs."""

from __future__ import annotations

import sys
import unittest
from types import MappingProxyType

import external_memory_definitions as definitions
from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake


class DiagnosticCodesTests(unittest.TestCase):
    def test_syntax_error_has_stable_code_and_byte_column(self) -> None:
        source = "文字列 = (\n"
        result = shikake.inspect_source(source)
        self.assertIsNone(result.model)
        (issue,) = result.issues
        self.assertEqual(issue.category, "syntax_error")
        self.assertEqual(issue.code, "syntax.invalid")
        self.assertIsNotNone(issue.column)
        assert issue.column is not None
        self.assertEqual(
            shikake.utf8_byte_column_to_character_column("文字列 = (", issue.column),
            "文字列 = (".index("("),
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires type statement")
    @simulate_unadopted_syntax()
    def test_unsupported_node_has_code(self) -> None:
        result = shikake.inspect_source("type Alias = int\n")
        (issue,) = result.issues
        self.assertEqual(issue.code, "syntax.unsupported")
        self.assertEqual(issue.details["node_type"], "TypeAlias")
        self.assertIsNotNone(issue.skipped_span)

    def test_unregistered_external_call_has_structured_target(self) -> None:
        source = "from framework.memory import Memory\ny = Memory.tan(1)\n"
        result = shikake.inspect_source(source, definitions=definitions)
        self.assertFalse(result.complete)
        self.assertIsNotNone(result.model)  # Local errors omit only the bad statement.
        (issue,) = result.issues
        self.assertEqual(issue.category, "external_definition")
        self.assertEqual(issue.code, "external.unregistered_call")
        self.assertEqual(issue.details, {"target": "Memory.tan"})
        with self.assertRaises(TypeError):
            issue.details["target"] = "modified"  # type: ignore[index]
        with self.assertRaises(shikake.ExternalModelingError) as caught:
            shikake.parse_source(source, definitions=definitions)
        self.assertEqual(caught.exception.code, issue.code)
        self.assertEqual(caught.exception.details, issue.details)

    def test_reserved_name_rebound_has_structured_name(self) -> None:
        source = "from framework.memory import Memory\nMemory = 1\n"
        result = shikake.inspect_source(source, definitions=definitions)
        (issue,) = result.issues
        self.assertEqual(issue.code, "external.reserved_name_rebound")
        self.assertEqual(issue.details["name"], "Memory")

    def test_argument_mismatch_carries_keyword_not_message_parsing(self) -> None:
        source = "from framework.memory import Memory\ny = Memory.new()\n"
        result = shikake.inspect_source(source, definitions=definitions)
        (issue,) = result.issues
        self.assertEqual(issue.code, "external.argument_mismatch")
        self.assertEqual(issue.details["keyword"], "size")

    def test_unknown_keyword_code(self) -> None:
        source = "from framework.memory import Memory\ny = Memory.new(unexpected=1)\n"
        result = shikake.inspect_source(source, definitions=definitions)
        (issue,) = result.issues
        self.assertEqual(issue.code, "external.unknown_keyword")

    def test_manually_created_issue_copies_mutable_details(self) -> None:
        original: dict[str, str | int] = {"target": "sample"}
        issue = shikake.InspectionIssue(
            "syntax_error",
            "sample.py",
            "SyntaxError",
            "error",
            1,
            0,
            details=original,
        )
        original["target"] = "changed"
        self.assertIsInstance(issue.details, MappingProxyType)
        self.assertEqual(issue.details["target"], "sample")
        self.assertEqual(issue.code, "diagnostic.unspecified")


class Utf8ColumnTests(unittest.TestCase):
    def test_character_column_for_japanese_and_emoji(self) -> None:
        line = "日本語🙂 + value"
        self.assertEqual(
            shikake.utf8_byte_column_to_character_column(
                line, len("日本語🙂 ".encode())
            ),
            len("日本語🙂 "),
        )
        self.assertEqual(shikake.utf8_byte_column_to_character_column(line, 0), 0)
        self.assertEqual(
            shikake.utf8_byte_column_to_character_column(line, len(line.encode())),
            len(line),
        )

    def test_invalid_utf8_columns_rejected(self) -> None:
        for column in (-1, 1, 2, 999):
            with self.subTest(column=column), self.assertRaises(ValueError):
                shikake.utf8_byte_column_to_character_column("日", column)
        self.assertEqual(shikake.utf8_byte_column_to_character_column("日", 3), 1)


class ScalarAccessorTests(unittest.TestCase):
    @staticmethod
    def literal(value: str) -> shikake.Model:
        root = shikake.parse_source(f"x = {value}")
        (assignment,) = root.get_nodes("body")
        return assignment.get_node("value")

    def test_noncoercing_scalars(self) -> None:
        for source, expected in (
            ("123", 123),
            ("True", True),
            ("None", None),
            ("...", Ellipsis),
            ("'a'", "a"),
            ("1.25", 1.25),
        ):
            with self.subTest(source=source):
                literal = self.literal(source)
                self.assertEqual(literal.get_scalar("value"), expected)
                self.assertIs(type(literal.get_scalar("value")), type(expected))
                self.assertEqual(literal.get_scalar("value", type(expected)), expected)

    def test_exact_scalar_type_bool_not_int(self) -> None:
        boolean = self.literal("True")
        with self.assertRaises(TypeError):
            boolean.get_scalar("value", int)
        integer = self.literal("1")
        with self.assertRaises(TypeError):
            integer.get_scalar("value", bool)

    def test_role_not_scalar_and_unknown_role(self) -> None:
        root = shikake.parse_source("x = 1")
        with self.assertRaises(TypeError):
            root.get_scalar("body")
        with self.assertRaises(KeyError):
            root.get_scalar("not-a-role")
        (assignment,) = root.get_nodes("body")
        with self.assertRaises(TypeError):
            assignment.get_scalar("value")


if __name__ == "__main__":
    unittest.main()
