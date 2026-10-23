"""Local external errors omit statements, global alias violations remain fatal."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as rules

import shikake


class LocalExternalRecoveryTests(unittest.TestCase):
    @staticmethod
    def inspect(source: str) -> shikake.SourceInspection:
        return shikake.inspect_source(source, definitions=rules)

    def test_preserves_good_sibling_statements_and_diagnostic_span(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "speed = 3\n"
            "size = Memory.tan(speed)\n"
            "x = 0\n"
        )
        result = self.inspect(source)
        self.assertIsNotNone(result.model)
        self.assertFalse(result.complete)
        assert result.model is not None
        (issue,) = result.issues
        self.assertEqual(issue.category, "external_definition")
        self.assertEqual(issue.code, "external.unregistered_call")
        self.assertEqual(issue.details["target"], "Memory.tan")
        self.assertEqual(issue.skipped_node_type, "Assign")
        self.assertEqual(issue.skipped_span, shikake.SourceSpan(3, 0, 3, 24))
        kept_lines = [
            node.span.line for node in result.model.get_nodes("body") if node.span
        ]
        self.assertEqual(kept_lines, [1, 2, 4])
        with self.assertRaises(shikake.ExternalModelingError):
            shikake.parse_source(source, definitions=rules)

    def test_multiple_preflight_and_build_errors_in_one_file(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "bad = Memory.nope(1)\n"
            "bad2 = Memory.new()\n"
            "also_bad = Memory.new\n"
            "ok = Memory.new(4)\n"
        )
        result = self.inspect(source)
        self.assertIsNotNone(result.model)
        self.assertEqual(
            [issue.code for issue in result.issues],
            [
                "external.unregistered_call",
                "external.argument_mismatch",
                "external.interface_value",
            ],
        )
        assert result.model is not None
        self.assertEqual(
            [node.span.line for node in result.model.get_nodes("body") if node.span],
            [1, 5],
        )
        self.assertEqual(
            [node.kind.id for node in result.model.walk()].count("ext.memory.allocate"),
            1,
        )

    def test_same_statement_multiple_invalid_references_not_modeled(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "x = (Memory.nope(1), Memory.other(2))\n"
            "y = 3\n"
        )
        result = self.inspect(source)
        self.assertEqual(
            [issue.code for issue in result.issues],
            ["external.unregistered_call", "external.unregistered_call"],
        )
        self.assertTrue(
            all(issue.skipped_node_type == "Assign" for issue in result.issues)
        )
        assert result.model is not None
        self.assertEqual(len(result.model.get_nodes("body")), 2)

    def test_nested_branch_keeps_valid_inner_siblings(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "if ready:\n"
            "    good = 1\n"
            "    failed = Memory.unknown(1)\n"
            "    after = 2\n"
            "end = 3\n"
        )
        result = self.inspect(source)
        self.assertFalse(result.complete)
        assert result.model is not None
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].skipped_span.line, 4)  # type: ignore[union-attr]
        self.assertEqual(len(result.model.get_nodes("body")), 3)
        branch = result.model.get_nodes("body")[1]
        block = branch.get_nodes("paths")[0].get_node("body")
        self.assertEqual(len(block.get_nodes("statements")), 2)

    def test_error_in_elif_condition_omits_whole_branch(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "if x:\n"
            "    a = 1\n"
            "elif Memory.nope(1):\n"
            "    a = 2\n"
            "b = 3\n"
        )
        result = self.inspect(source)
        assert result.model is not None
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].skipped_node_type, "If")
        self.assertEqual(result.issues[0].skipped_span.line, 2)  # type: ignore[union-attr]
        self.assertEqual(len(result.model.get_nodes("body")), 2)

    def test_file_wide_reserved_name_errors_take_precedence(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "a = Memory.nope(1)\n"
            "Memory = 42\n"
            "b = 1\n"
        )
        result = self.inspect(source)
        self.assertIsNone(result.model)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].code, "external.reserved_name_rebound")
        self.assertIsNone(result.issues[0].skipped_span)

    def test_wildcard_import_is_global_even_when_unrelated(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "a = Memory.nope(1)\n"
            "from math import *\n"
        )
        result = self.inspect(source)
        self.assertIsNone(result.model)
        self.assertEqual(result.issues[0].code, "external.wildcard_shadow")

    def test_invalid_module_kept_but_package_relations_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pkg = Path(directory) / "pkg"
            pkg.mkdir()
            (pkg / "a.py").write_text(
                "from framework.memory import Memory\n"
                "class Base: pass\n"
                "invalid = Memory.nope(1)\n"
                "class Child(Base): pass\n",
                encoding="utf-8",
            )
            (pkg / "b.py").write_text("value = 1\n", encoding="utf-8")
            result = shikake.inspect_package(pkg, definitions=rules)
            self.assertFalse(result.complete)
            self.assertEqual(
                [m.get_name("name") for m in result.model.get_nodes("modules")],
                ["pkg.a", "pkg.b"],
            )
            self.assertEqual(result.issues[0].code, "external.unregistered_call")
            self.assertEqual(result.issues[0].skipped_node_type, "Assign")
            self.assertEqual(result.base_references, ())
            self.assertEqual(result.override_candidates, ())
            self.assertEqual(result.name_bindings, ())
            self.assertEqual(result.analyses, frozenset())

    def test_no_definitions_behaves_as_before(self) -> None:
        source = "x = Unknown.method(1)\n"
        result = shikake.inspect_source(source)
        self.assertTrue(result.complete)
        self.assertEqual(result.model, shikake.parse_source(source))


if __name__ == "__main__":
    unittest.main()
