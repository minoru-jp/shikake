"""File encoding, path identity, and source-tree traversal regressions."""

from __future__ import annotations

import codecs
import os
import tempfile
import unittest
from pathlib import Path
from typing import cast

import shikake
from shikake._mica.model import Model


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    result = model.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(item, Model) for item in result)
    return cast(tuple[Model, ...], result)


class SourceIngestionTests(unittest.TestCase):
    def test_type_comments_never_affect_source_modeling(self) -> None:
        code = (
            "pass  # type: str\n"
            "x = 1  # type: int\n"
            "def f():  # type: () -> str\n"
            "    return x  # type: ignore[return-value]\n"
        )
        strict = shikake.parse_source(code)
        inspection = shikake.inspect_source(code)
        self.assertTrue(inspection.complete)
        self.assertEqual(strict, inspection.model)
        self.assertEqual(
            [node.kind.id for node in nodes(strict, "body")],
            [
                "model.statement.pass",
                "model.statement.assignment",
                "model.definition.function",
            ],
        )

    def test_bom_and_declared_latin1_package_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "written"
            folder.mkdir()
            (folder / "__init__.py").write_bytes(codecs.BOM_UTF8 + b"name = 'ready'\n")
            (folder / "latin.py").write_bytes(
                "# -*- coding: latin-1 -*-\nmessage = 'café'\n".encode("latin-1")
            )
            strict = shikake.parse_package(folder)
            inspection = shikake.inspect_package(folder)
            self.assertTrue(inspection.complete)
            self.assertEqual(strict.model, inspection.model)
            modules = nodes(strict.model, "modules")
            self.assertEqual(
                [model.get("name") for model in modules], ["written", "written.latin"]
            )
            (assignment,) = nodes(modules[1], "body")
            value = assignment.get("value")
            self.assertIsInstance(value, Model)
            assert isinstance(value, Model)
            self.assertEqual(value.get("value"), "café")

    def test_type_comments_in_files_cannot_invalidate_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "package"
            folder.mkdir()
            (folder / "__init__.py").write_text("pass  # type: str\n", encoding="utf-8")
            (folder / "a.py").write_text("value = 1  # type: int\n", encoding="utf-8")
            self.assertEqual(
                len(nodes(shikake.parse_package(folder).model, "modules")), 2
            )
            self.assertTrue(shikake.inspect_package(folder).complete)

    def test_dot_root_and_absolute_path_produce_same_names_and_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "base.py").write_text(
                "class Base:\n    def action(self): pass\n", encoding="utf-8"
            )
            (folder / "derived.py").write_text(
                "from .base import Base\n"
                "class Derived(Base):\n    def action(self): pass\n",
                encoding="utf-8",
            )
            absolute = shikake.parse_package(folder)
            original = Path.cwd()
            try:
                os.chdir(folder)
                relative = shikake.parse_package(".")
                inspected = shikake.inspect_package(".")
            finally:
                os.chdir(original)
            self.assertEqual(relative.model, absolute.model)
            self.assertTrue(inspected.complete)
            self.assertEqual(inspected.model, absolute.model)
            self.assertEqual(len(relative.override_candidates), 1)
            self.assertEqual(len(inspected.override_candidates), 1)
            self.assertEqual(
                [mod.get("name") for mod in nodes(relative.model, "modules")],
                ["pkg", "pkg.base", "pkg.derived"],
            )

    def test_initless_subtrees_are_modeled_in_both_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "model.py").write_text("value = 10\n", encoding="utf-8")
            subpackage = folder / "sub"
            subpackage.mkdir()
            (subpackage / "__init__.py").write_text("", encoding="utf-8")
            (subpackage / "member.py").write_text("value = 20\n", encoding="utf-8")
            scripts = folder / "scripts"
            scripts.mkdir()
            (scripts / "tool.py").write_text("value = 30\n", encoding="utf-8")
            (scripts / "nested").mkdir()
            (scripts / "nested" / "__init__.py").write_text("", encoding="utf-8")
            (scripts / "nested" / "other.py").write_text(
                "value = 40\n", encoding="utf-8"
            )
            strict = shikake.parse_package(folder)
            self.assertEqual(
                [module.get("name") for module in nodes(strict.model, "modules")],
                [
                    "pkg",
                    "pkg.model",
                    "pkg.scripts.nested",
                    "pkg.scripts.nested.other",
                    "pkg.scripts.tool",
                    "pkg.sub",
                    "pkg.sub.member",
                ],
            )
            inspected = shikake.inspect_package(folder)
            self.assertTrue(inspected.complete)
            self.assertEqual(inspected.issues, ())
            self.assertEqual(inspected.model, strict.model)

    def test_root_without_init_is_a_valid_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "namespace"
            (folder / "nested").mkdir(parents=True)
            (folder / "module.py").write_text("x = 1\n", encoding="utf-8")
            (folder / "nested" / "other.py").write_text("y = 2\n", encoding="utf-8")
            strict = shikake.parse_package(folder)
            partial = shikake.inspect_package(folder)
            self.assertEqual(
                [module.get("name") for module in nodes(strict.model, "modules")],
                ["namespace.module", "namespace.nested.other"],
            )
            self.assertEqual(strict.model.get("name"), "namespace")
            self.assertTrue(partial.complete)
            self.assertEqual(partial.model, strict.model)

    def test_initless_source_modules_still_match_local_base(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "namespace"
            (folder / "members").mkdir(parents=True)
            (folder / "base.py").write_text(
                "class Base:\n    def foo(self): pass\n", encoding="utf-8"
            )
            (folder / "members" / "derived.py").write_text(
                "from ..base import Base\n"
                "class Derived(Base):\n    def foo(self): pass\n",
                encoding="utf-8",
            )
            strict = shikake.parse_package(folder)
            partial = shikake.inspect_package(folder)
            self.assertTrue(partial.complete)
            self.assertEqual(len(strict.override_candidates), 1)
            self.assertEqual(len(partial.override_candidates), 1)
            self.assertEqual(
                strict.override_candidates[0].base_module, "namespace.base"
            )
            self.assertEqual(
                strict.override_candidates[0].derived_module,
                "namespace.members.derived",
            )

    def test_initless_subtree_syntax_error_is_not_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            (folder / "nested").mkdir(parents=True)
            (folder / "good.py").write_text("x = 1\n", encoding="utf-8")
            (folder / "nested" / "bad.py").write_text(
                "def broken(:\n", encoding="utf-8"
            )
            with self.assertRaises(SyntaxError):
                shikake.parse_package(folder)
            partial = shikake.inspect_package(folder)
            self.assertFalse(partial.complete)
            self.assertEqual([i.category for i in partial.issues], ["syntax_error"])
            self.assertEqual(
                [m.get("name") for m in nodes(partial.model, "modules")],
                ["pkg.good"],
            )

    def test_colliding_module_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            (folder / "mod").mkdir(parents=True)
            (folder / "mod.py").write_text("x = 1\n", encoding="utf-8")
            (folder / "mod" / "__init__.py").write_text("y = 2\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaisesRegex(ValueError, "ambiguous module name"):
                    parse(folder)

    def test_symlinked_subtrees_and_sources_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            folder.mkdir()
            (folder / "normal.py").write_text("x = 1\n", encoding="utf-8")
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (outside / "hidden.py").write_text("def invalid(:\n", encoding="utf-8")
            try:
                (folder / "linked").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks are not supported")
            (folder / "linked.py").symlink_to(outside / "hidden.py")
            for parse in (shikake.parse_package, shikake.inspect_package):
                result = parse(folder)
                model = result.model
                self.assertEqual(
                    [module.get("name") for module in nodes(model, "modules")],
                    ["pkg.normal"],
                )
            # The input root itself remains an error when supplied as a link.
            linked_root = Path(temporary) / "linked-root"
            linked_root.symlink_to(folder, target_is_directory=True)
            for parse in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaisesRegex(ValueError, "package symlinks"):
                    parse(linked_root)

    def test_dot_py_directory_is_not_treated_as_a_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            (folder / "x.py").mkdir(parents=True)
            (folder / "x.py" / "inner.py").write_text("value = 1\n", encoding="utf-8")
            (folder / "normal.py").write_text("value = 2\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                result = parse(folder)
                self.assertEqual(
                    [m.get("name") for m in nodes(result.model, "modules")],
                    ["pkg.normal", "pkg.x.py.inner"],
                )

    def test_all_regular_py_files_are_in_scope_in_both_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            (folder / ".venv" / "lib").mkdir(parents=True)
            (folder / "build").mkdir()
            (folder / ".venv" / "lib" / "valid.py").write_text(
                "value = 1\n", encoding="utf-8"
            )
            (folder / "build" / "valid.py").write_text("value = 2\n", encoding="utf-8")
            (folder / "normal.py").write_text("value = 3\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                result = parse(folder)
                self.assertEqual(
                    [module.get("name") for module in nodes(result.model, "modules")],
                    ["pkg..venv.lib.valid", "pkg.build.valid", "pkg.normal"],
                )
            (folder / "build" / "invalid.py").write_text(
                "def invalid(:\n", encoding="utf-8"
            )
            self.assertFalse(shikake.inspect_package(folder).complete)
            with self.assertRaises(SyntaxError):
                shikake.parse_package(folder)

    def test_strict_source_filename_is_reported_in_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError) as caught:
            shikake.parse_source("def broken(:\n", filename="example.py")
        self.assertEqual(caught.exception.filename, "example.py")
        with self.assertRaises(SyntaxError) as default:
            shikake.parse_source("def broken(:\n")
        self.assertEqual(default.exception.filename, "<source>")

    def test_source_filename_labels_diagnostics_not_module_identity(self) -> None:
        source = "x = 1\n"
        strict_default = shikake.parse_source(source)
        strict_named = shikake.parse_source(source, filename="src/example.py")
        partial_default = shikake.inspect_source(source)
        partial_named = shikake.inspect_source(source, filename="src/example.py")
        for result in (strict_default, strict_named):
            self.assertEqual(result.get("name"), "<source>")
        for result in (partial_default, partial_named):
            self.assertTrue(result.complete)
            self.assertIsNotNone(result.model)
            assert result.model is not None
            self.assertEqual(result.model.get("name"), "<source>")
            self.assertEqual(result.model, strict_default)
        self.assertEqual(strict_default, strict_named)

        default_issue = shikake.inspect_source("def bad(:\n")
        named_issue = shikake.inspect_source("def bad(:\n", filename="src/example.py")
        self.assertEqual(default_issue.issues[0].filename, "<source>")
        self.assertEqual(named_issue.issues[0].filename, "src/example.py")

    def test_invalid_source_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            file_root = Path(temporary) / "file.py"
            file_root.write_text("x = 1\n", encoding="utf-8")
            for root in (missing, file_root):
                for parse in (shikake.parse_package, shikake.inspect_package):
                    with self.assertRaisesRegex(
                        ValueError, "not a Python source directory"
                    ):
                        parse(root)

    def test_syntax_error_from_encoded_file_uses_utf8_byte_column(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            folder.mkdir()
            (folder / "bad.py").write_bytes(b"# coding: latin-1\nx = '\xe9' +\n")
            result = shikake.inspect_package(folder)
            self.assertFalse(result.complete)
            (issue,) = result.issues
            self.assertEqual(issue.category, "syntax_error")
            self.assertEqual(issue.line, 2)
            self.assertEqual(issue.column, len("x = 'é' +".encode()))

    def test_partial_reports_python_syntax_error_per_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "pkg"
            folder.mkdir()
            (folder / "__init__.py").write_bytes(codecs.BOM_UTF8 + b"x = 1\n")
            (folder / "invalid.py").write_bytes(b"# coding: latin-1\ndef broken(:\n")
            (folder / "good.py").write_bytes(b"# coding: latin-1\nx = 1\n")
            partial = shikake.inspect_package(folder)
            self.assertFalse(partial.complete)
            self.assertEqual(
                [issue.category for issue in partial.issues], ["syntax_error"]
            )
            self.assertEqual(
                [model.get("name") for model in nodes(partial.model, "modules")],
                ["pkg", "pkg.good"],
            )
            with self.assertRaises(SyntaxError):
                shikake.parse_package(folder)


if __name__ == "__main__":
    unittest.main()
