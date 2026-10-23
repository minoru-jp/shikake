"""Explicit package source suffixes do not change Python AST modeling rules."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


def module_names(model: shikake.Model) -> list[str]:
    return [str(module.get("name")) for module in model.get_nodes("modules")]


class PackageExtensionTests(unittest.TestCase):
    def test_default_remains_exactly_py(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            (root / "ignored.dot").write_text("def invalid(:\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                result = api(root)
                self.assertEqual(module_names(result.model), ["pkg.main"])
                result = api(root, extensions=(".py",))
                self.assertEqual(module_names(result.model), ["pkg.main"])
                if isinstance(result, shikake.PackageInspection):
                    self.assertTrue(result.complete)

    def test_custom_extension_only_and_multiple_in_both_modes(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            (root / "sub").mkdir(parents=True)
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            (root / "other.dot").write_text("y = 2\n", encoding="utf-8")
            (root / "sub" / "nested.dot").write_text("z = 3\n", encoding="utf-8")
            (root / "note.txt").write_text("def invalid(:\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                self.assertEqual(
                    module_names(api(root, extensions=(".dot",)).model),
                    ["pkg.other", "pkg.sub.nested"],
                )
                self.assertEqual(
                    module_names(api(root, extensions=(".py", ".dot")).model),
                    ["pkg.main", "pkg.other", "pkg.sub.nested"],
                )
                self.assertEqual(
                    module_names(api(root, extensions=(".dot", ".py")).model),
                    ["pkg.main", "pkg.other", "pkg.sub.nested"],
                )

    def test_custom_initializer_contributes_to_module_identity(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            (root / "sub").mkdir(parents=True)
            (root / "__init__.dot").write_text("value = 1\n", encoding="utf-8")
            (root / "sub" / "__init__.dot").write_text("value = 2\n", encoding="utf-8")
            (root / "sub" / "main.dot").write_text("value = 3\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                result = api(root, extensions=(".dot",))
                self.assertEqual(
                    module_names(result.model), ["pkg", "pkg.sub", "pkg.sub.main"]
                )
                self.assertTrue(result.name_bindings)

    def test_same_module_name_across_extensions_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            (root / "main.py").write_text("x = 1\n", encoding="utf-8")
            (root / "main.dot").write_text("x = 2\n", encoding="utf-8")
            (root / "__init__.py").write_text("pass\n", encoding="utf-8")
            (root / "__init__.dot").write_text("pass\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaisesRegex(ValueError, "ambiguous module name"):
                    api(root, extensions=(".py", ".dot"))
                self.assertEqual(
                    module_names(api(root, extensions=(".dot",)).model),
                    ["pkg", "pkg.main"],
                )

    def test_include_sees_only_matching_files_and_prunes_directories(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            (root / ".venv").mkdir(parents=True)
            (root / "sub").mkdir()
            (root / "run.dot").write_text("x = 1\n", encoding="utf-8")
            (root / "run.py").write_text("def invalid(:\n", encoding="utf-8")
            (root / ".venv" / "bad.dot").write_text("def invalid(:\n", encoding="utf-8")
            (root / "sub" / "ok.dot").write_text("pass\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                seen: list[tuple[str, bool]] = []

                def include(
                    path: Path,
                    is_directory: bool,
                    *,
                    captured: list[tuple[str, bool]] = seen,
                ) -> bool:
                    captured.append((path.name, is_directory))
                    return not (is_directory and path.name == ".venv")

                result = api(root, extensions=(".dot",), include=include)
                self.assertEqual(module_names(result.model), ["pkg.run", "pkg.sub.ok"])
                self.assertEqual(
                    set(seen),
                    {
                        (".venv", True),
                        ("sub", True),
                        ("run.dot", False),
                        ("ok.dot", False),
                    },
                )
                if isinstance(result, shikake.PackageInspection):
                    self.assertTrue(result.complete)

    def test_extension_matching_is_case_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            (root / "upper.DOT").write_text("pass\n", encoding="utf-8")
            (root / "lower.dot").write_text("pass\n", encoding="utf-8")
            for api in (shikake.parse_package, shikake.inspect_package):
                self.assertEqual(
                    module_names(api(root, extensions=(".dot",)).model),
                    ["pkg.lower"],
                )
                self.assertEqual(
                    module_names(api(root, extensions=(".DOT",)).model),
                    ["pkg.upper"],
                )

    def test_invalid_extension_parameters_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            for api in (shikake.parse_package, shikake.inspect_package):
                for invalid in [None, ".py", [".py"], (".py", 5)]:
                    with (
                        self.subTest(api=api.__name__, value=invalid),
                        self.assertRaises(TypeError),
                    ):
                        api(root, extensions=invalid)  # type: ignore[arg-type]
                for invalid in [
                    (),
                    ("py",),
                    (".",),
                    (".py", ".py"),
                    ("*.py",),
                    (".p*y",),
                    (".tar.gz",),
                    (".x/y",),
                    (".x\\y",),
                    (".dot ",),
                ]:
                    with (
                        self.subTest(api=api.__name__, value=invalid),
                        self.assertRaises(ValueError),
                    ):
                        api(root, extensions=invalid)

    def test_partial_syntax_diagnostics_use_custom_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            (root / "good.dot").write_text("x = 1\n", encoding="utf-8")
            invalid = root / "bad.dot"
            invalid.write_text("def invalid(:\n", encoding="utf-8")
            with self.assertRaises(SyntaxError):
                shikake.parse_package(root, extensions=(".dot",))
            result = shikake.inspect_package(root, extensions=(".dot",))
            self.assertFalse(result.complete)
            self.assertEqual(module_names(result.model), ["pkg.good"])
            self.assertEqual(len(result.issues), 1)
            self.assertEqual(result.issues[0].filename, str(invalid))

    def test_custom_extension_cross_module_relations_remain_available(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            root = Path(location) / "pkg"
            root.mkdir()
            (root / "base.dot").write_text(
                "class Base:\n    def f(self): pass\n", encoding="utf-8"
            )
            (root / "sub.dot").write_text(
                "from .base import Base\nclass Sub(Base):\n    def f(self): pass\n",
                encoding="utf-8",
            )
            for api in (shikake.parse_package, shikake.inspect_package):
                result = api(root, extensions=(".dot",))
                self.assertEqual(len(result.override_candidates), 1)
                self.assertEqual(len(result.base_references), 1)
                self.assertTrue(result.name_bindings)


if __name__ == "__main__":
    unittest.main()
