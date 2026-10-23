"""Regression tests for non-raising, explicitly incomplete AST inspection."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    value = model.get(role)
    assert isinstance(value, tuple)
    assert all(isinstance(item, Model) for item in value)
    return cast(tuple[Model, ...], value)


def child(model: Model, role: str) -> Model:
    value = model.get(role)
    assert isinstance(value, Model)
    return value


class InspectSourceTests(unittest.TestCase):
    def test_complete_source_matches_strict_model(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "tests/fixtures/shipping.py"
        ).read_text()
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete)
        self.assertEqual(inspected.issues, ())
        self.assertEqual(inspected.model, shikake.parse_source(source))
        self.assertIsNotNone(inspected.model)

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_skip_unsupported_siblings_but_keep_statement_order(self) -> None:
        source = (
            "def f():\n"
            "    first = 1\n"
            "    type Unmodeled = tuple[first, hidden]\n"
            "    second = first + 2\n"
            "    return second\n"
        )
        result = shikake.inspect_source(source, filename="example.py")
        self.assertFalse(result.complete)
        assert result.model is not None
        (fn,) = nodes(result.model, "body")
        statements = nodes(child(fn, "body"), "statements")
        self.assertEqual(
            [node.kind.id for node in statements],
            [
                "model.statement.assignment",
                "model.statement.assignment",
                "model.statement.return",
            ],
        )
        (issue,) = result.issues
        self.assertEqual(issue.category, "unsupported_syntax")
        self.assertEqual(issue.filename, "example.py")
        self.assertEqual(issue.node_type, "TypeAlias")
        self.assertEqual(issue.line, 3)
        self.assertEqual(issue.skipped_node_type, "TypeAlias")
        self.assertEqual(issue.skipped_span.line if issue.skipped_span else None, 3)
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_unsupported_expression_omits_whole_statement_and_reports_both(
        self,
    ) -> None:
        source = "a = 1\ntype B = int\nc = 3\n"
        result = shikake.inspect_source(source)
        assert result.model is not None
        assignments = nodes(result.model, "body")
        self.assertEqual(
            [nodes(m, "targets")[0].get("name") for m in assignments], ["a", "c"]
        )
        (issue,) = result.issues
        self.assertEqual(issue.node_type, "TypeAlias")
        self.assertEqual(issue.skipped_node_type, "TypeAlias")
        self.assertEqual(issue.line, 2)
        self.assertEqual(issue.skipped_span.line if issue.skipped_span else None, 2)

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_does_not_hoist_children_from_unsupported_parent(self) -> None:
        source = (
            "def f():\n"
            "    before = 1\n"
            "    type Unmodeled = tuple[hidden, int]\n"
            "    after = 2\n"
        )
        result = shikake.inspect_source(source)
        assert result.model is not None
        (function,) = nodes(result.model, "body")
        statements = nodes(child(function, "body"), "statements")
        self.assertEqual(len(statements), 2)
        self.assertEqual(
            [nodes(stmt, "targets")[0].get("name") for stmt in statements],
            ["before", "after"],
        )
        self.assertEqual(result.issues[0].node_type, "TypeAlias")
        self.assertEqual(result.issues[0].skipped_node_type, "TypeAlias")

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_nested_branch_keeps_both_blocks_with_partial_content(self) -> None:
        source = (
            "def f(x):\n"
            "    if x >= 1:\n"
            "        a = 1\n"
            "        type Unmodeled = tuple[missing, int]\n"
            "        b = 2\n"
            "    else:\n"
            "        c = 3\n"
        )
        result = shikake.inspect_source(source)
        assert result.model is not None
        (function,) = nodes(result.model, "body")
        (branch,) = nodes(child(function, "body"), "statements")
        paths = nodes(branch, "paths")
        self.assertEqual(len(nodes(child(paths[0], "body"), "statements")), 2)
        self.assertEqual(len(nodes(child(paths[1], "body"), "statements")), 1)
        self.assertEqual(len(result.issues), 1)

    def test_syntax_error_does_not_pretend_model_exists(self) -> None:
        source = "def broken(:\n    pass\n"
        result = shikake.inspect_source(source, filename="broken.py")
        self.assertIsNone(result.model)
        self.assertFalse(result.complete)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].category, "syntax_error")
        self.assertEqual(result.issues[0].filename, "broken.py")
        with self.assertRaises(SyntaxError):
            shikake.parse_source(source)

    def test_syntax_error_columns_are_utf8_byte_offsets(self) -> None:
        cases = (
            ("x = 1 +", 1, "x = 1 +"),
            ("x = 'ああああ' +", 1, "x = 'ああああ' +"),
            ("x = '🙂🙂' +", 1, "x = '🙂🙂' +"),
            ("ok = '日本語'\nvalue = 'é' +", 2, "value = 'é' +"),
        )
        for source, line, prefix in cases:
            with self.subTest(source=source):
                inspected = shikake.inspect_source(source, filename="unicode.py")
                self.assertIsNone(inspected.model)
                (issue,) = inspected.issues
                self.assertEqual(issue.category, "syntax_error")
                self.assertEqual(issue.filename, "unicode.py")
                self.assertEqual(issue.line, line)
                self.assertEqual(issue.column, len(prefix.encode("utf-8")))

    def test_syntax_error_column_is_unknown_when_error_has_no_text(self) -> None:
        from shikake._mica.inspection import _syntax_issue

        error = SyntaxError("no line text", ("missing.py", 1, 4, None))
        issue = _syntax_issue(error, "missing.py")
        self.assertIsNone(issue.column)

    def test_type_ignore_is_ignored_metadata_in_both_modes(self) -> None:
        source = "x = 1  # type: ignore\ny = 2\n"
        result = shikake.inspect_source(source)
        assert result.model is not None
        self.assertEqual(len(nodes(result.model, "body")), 2)
        self.assertEqual(result.issues, ())
        self.assertTrue(result.complete)
        self.assertEqual(result.model, shikake.parse_source(source))


class InspectPackageTests(unittest.TestCase):
    def test_clean_package_matches_strict_output(self) -> None:
        sample = Path(__file__).resolve().parents[1] / "tests/fixtures/shop"
        inspected = shikake.inspect_package(sample)
        strict = shikake.parse_package(sample)
        self.assertTrue(inspected.complete)
        self.assertEqual(len(tuple(inspected.walk())), 95)
        self.assertEqual(inspected.model, strict.model)
        self.assertEqual(len(inspected.override_candidates), 1)
        self.assertEqual(
            inspected.override_candidates[0].method.get("name"), "calculate_fee"
        )

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_continue_when_module_has_syntax_error_and_unsupported_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "shop"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "a.py").write_text("def broken(:\n", encoding="utf-8")
            (pkg / "b.py").write_text(
                "x = 1\ntype Unmodeled = int\ny = 2\n",
                encoding="utf-8",
            )
            (pkg / "c.py").write_text("z = 3\n", encoding="utf-8")
            result = shikake.inspect_package(pkg)
            self.assertFalse(result.complete)
            self.assertEqual(
                [i.category for i in result.issues],
                ["syntax_error", "unsupported_syntax"],
            )
            self.assertEqual(result.override_candidates, ())
            modules = nodes(result.model, "modules")
            self.assertEqual(
                [m.get("name") for m in modules], ["shop", "shop.b", "shop.c"]
            )
            self.assertEqual(len(nodes(modules[1], "body")), 2)
            with self.assertRaises(SyntaxError):
                shikake.parse_package(pkg)

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_package_suppresses_unverifiable_relations(self) -> None:
        sample = Path(__file__).resolve().parents[1] / "tests/fixtures/shop"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "shop"
            shutil.copytree(sample, target)
            (target / "extra.py").write_text("type Unmodeled = int\n", encoding="utf-8")
            result = shikake.inspect_package(target)
            self.assertFalse(result.complete)
            self.assertEqual(result.override_candidates, ())
            self.assertEqual(len(result.issues), 1)
            self.assertTrue(
                any(node.kind.id == "model.definition.method" for node in result.walk())
            )
            self.assertEqual(len(shikake.parse_package(sample).override_candidates), 1)


if __name__ == "__main__":
    unittest.main()
