"""Review regressions: context facts and host-controlled syntax warnings."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import shikake
from shikake._mica.ast_facts import collect_syntax_facts


class ExpressionContextIndexTests(unittest.TestCase):
    def test_nested_type_positions_are_marked_without_ancestor_queries(self) -> None:
        source = (
            "class Derived(Base):\n"
            "    field: list[tuple[int, str]]\n"
            "    def method(self, x: list[int]) -> dict[str, int]:\n"
            "        return call(int, x)\n"
        )
        tree = ast.parse(source)
        facts = collect_syntax_facts(tree, include_references=True)
        scopes, parents, positions = facts.expression_scopes(tree)
        self.assertIs(facts.expression_scopes(tree)[0], scopes)
        self.assertTrue(scopes)
        self.assertTrue(parents)
        classified = {
            (node.id, node.lineno): node in positions
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        self.assertTrue(classified[("Base", 1)])
        self.assertTrue(classified[("int", 2)])
        self.assertTrue(classified[("int", 3)])
        self.assertTrue(classified[("int", 4)] is False)
        self.assertFalse(classified[("x", 4)])

    @unittest.skipIf(sys.version_info < (3, 12), "PEP 695 requires Python 3.12")
    def test_type_alias_value_is_type_context(self) -> None:
        tree = ast.parse("type Alias = list[int]\n")
        facts = collect_syntax_facts(tree, include_references=True)
        _, _, positions = facts.expression_scopes(tree)
        int_name = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id == "int"
        )
        self.assertIn(int_name, positions)


class SyntaxWarningInspectionTests(unittest.TestCase):
    source = 'value = "\\q"\n'
    warning_class = SyntaxWarning if sys.version_info >= (3, 12) else DeprecationWarning

    def test_host_receives_warnings_from_strict_and_inspection(self) -> None:
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always", self.warning_class)
            result = shikake.inspect_source(self.source, filename="warning.py")
            strict = shikake.parse_source(self.source, filename="warning.py")
        self.assertTrue(result.complete)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.model, strict)
        self.assertTrue(result.name_bindings)
        self.assertGreaterEqual(len(emitted), 2)
        self.assertTrue(all(item.filename == "warning.py" for item in emitted))
        self.assertTrue(
            all(issubclass(item.category, self.warning_class) for item in emitted)
        )

    def test_package_warnings_go_to_host_not_issues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            (root / "base.py").write_text("class Base: pass\n", encoding="utf-8")
            (root / "derived.py").write_text(
                'from .base import Base\nclass Derived(Base): pass\nx = "\\q"\n',
                encoding="utf-8",
            )
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter("always", self.warning_class)
                result = shikake.inspect_package(root)
                strict = shikake.parse_package(root)
        self.assertTrue(result.complete)
        self.assertTrue(result.name_bindings)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.model, strict.model)
        self.assertEqual(result.override_candidates, strict.override_candidates)
        self.assertGreaterEqual(len(emitted), 2)

    def test_shikake_does_not_change_host_warning_filters(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always", self.warning_class)
            original_filters = tuple(warnings.filters)
            shikake.parse_source(self.source, filename="warning.py")
            shikake.inspect_source(self.source, filename="warning.py")
            self.assertEqual(tuple(warnings.filters), original_filters)

    def test_host_suppression_is_respected(self) -> None:
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("ignore", self.warning_class)
            result = shikake.inspect_source(self.source, syntax_validation="ast")
        self.assertTrue(result.complete)
        self.assertEqual(result.issues, ())
        self.assertEqual(emitted, [])

    def test_warning_as_error_follows_python_syntax_behavior(self) -> None:
        # Versions differ in warning categories and parser diagnostics; test
        # against the active Python parser rather than a hard-coded category.
        with warnings.catch_warnings():
            warnings.simplefilter("error", self.warning_class)
            try:
                ast.parse(self.source, filename="warning.py")
            except SyntaxError:
                with self.assertRaises(SyntaxError):
                    shikake.parse_source(self.source, filename="warning.py")
                result = shikake.inspect_source(self.source, filename="warning.py")
                self.assertFalse(result.complete)
                self.assertIsNone(result.model)
                self.assertEqual(len(result.issues), 1)
                self.assertEqual(result.issues[0].category, "syntax_error")
                self.assertEqual(result.issues[0].code, "syntax.invalid")
            except Warning as warning:
                # A warning promoted directly to an exception propagates;
                # shikake does not attempt to turn it into a syntax issue.
                with self.assertRaises(type(warning)):
                    shikake.parse_source(self.source, filename="warning.py")
                with self.assertRaises(type(warning)):
                    shikake.inspect_source(self.source, filename="warning.py")
            else:
                self.skipTest("this interpreter does not warn on this source")


if __name__ == "__main__":
    unittest.main()
