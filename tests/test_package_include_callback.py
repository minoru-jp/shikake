"""Caller-defined source-tree selection shared by Strict and Partial inspection."""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast

import shikake
from shikake._mica.model import Model


def module_names(root: Model) -> list[str]:
    return [cast(str, module.get("name")) for module in root.get_nodes("modules")]


class IncludeCallbackTests(unittest.TestCase):
    def test_default_keeps_hidden_directories_and_invalid_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            (root / ".venv").mkdir(parents=True)
            (root / "main.py").write_text("pass\n", encoding="utf-8")
            (root / ".venv" / "bad.py").write_text("def broken(:\n", encoding="utf-8")
            with self.assertRaises(SyntaxError):
                shikake.parse_package(root)
            self.assertFalse(shikake.inspect_package(root).complete)
            selectors: tuple[Callable[[Path, bool], bool] | None, ...] = (
                None,
                lambda path, is_directory: True,
            )
            for selector in selectors:
                with self.subTest(selector=selector):
                    with self.assertRaises(SyntaxError):
                        shikake.parse_package(root, include=selector)
                    result = shikake.inspect_package(root, include=selector)
                    self.assertFalse(result.complete)
                    self.assertEqual(
                        [issue.category for issue in result.issues], ["syntax_error"]
                    )
                    self.assertEqual(module_names(result.model), ["pkg.main"])

    def test_directory_pruning_precedes_descendant_callbacks_in_both_modes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            (root / ".venv" / "lib").mkdir(parents=True)
            (root / "build").mkdir()
            (root / "nested").mkdir()
            (root / "__init__.py").write_text("pass\n", encoding="utf-8")
            (root / "nested" / "good.py").write_text("x = 1\n", encoding="utf-8")
            (root / ".venv" / "lib" / "bad.py").write_text(
                "def bad(:\n", encoding="utf-8"
            )
            (root / "build" / "bad.py").write_text("def bad(:\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                calls: list[tuple[Path, bool]] = []

                def include(
                    path: Path,
                    is_directory: bool,
                    *,
                    captured: list[tuple[Path, bool]] = calls,
                ) -> bool:
                    captured.append((path, is_directory))
                    self.assertTrue(path.is_absolute())
                    self.assertNotIn("lib", path.parts)
                    self.assertNotIn("bad.py", path.parts)
                    return not (is_directory and path.name in {".venv", "build"})

                result = parse(root, include=include)
                self.assertEqual(module_names(result.model), ["pkg", "pkg.nested.good"])
                self.assertTrue(all(path != root for path, _ in calls))
                self.assertIn((root / ".venv", True), calls)
                self.assertIn((root / "build", True), calls)
                self.assertIn((root / "nested", True), calls)
                self.assertIn((root / "__init__.py", False), calls)
                self.assertIn((root / "nested" / "good.py", False), calls)
                if isinstance(result, shikake.PackageInspection):
                    self.assertTrue(result.complete)

    def test_select_python_files_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            root.mkdir()
            (root / "keep.py").write_text("x = 1\n", encoding="utf-8")
            (root / "bad.py").write_text("def broken(:\n", encoding="utf-8")
            (root / "notes.txt").write_text("not python\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                seen: list[tuple[str, bool]] = []

                def include(
                    path: Path,
                    is_directory: bool,
                    *,
                    captured: list[tuple[str, bool]] = seen,
                ) -> bool:
                    captured.append((path.name, is_directory))
                    return path.name != "bad.py"

                result = parse(root, include=include)
                self.assertEqual(module_names(result.model), ["pkg.keep"])
                self.assertEqual(seen, [("bad.py", False), ("keep.py", False)])
                if isinstance(result, shikake.PackageInspection):
                    self.assertTrue(result.complete)
                    self.assertEqual(result.issues, ())

    def test_selection_precedes_module_collision_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            (root / "sub").mkdir(parents=True)
            (root / "sub.py").write_text("x = 1\n", encoding="utf-8")
            (root / "sub" / "__init__.py").write_text("y = 2\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaisesRegex(ValueError, "ambiguous module name"):
                    parse(root)
                only_file = parse(
                    root, include=lambda path, is_dir: path.name != "sub" or not is_dir
                )
                self.assertEqual(module_names(only_file.model), ["pkg.sub"])
                only_dir = parse(
                    root, include=lambda path, is_dir: path.name != "sub.py"
                )
                self.assertEqual(module_names(only_dir.model), ["pkg.sub"])

    def test_selected_sources_share_relation_and_binding_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            root.mkdir()
            (root / "base.py").write_text(
                "class Base:\n    def f(self): pass\n", encoding="utf-8"
            )
            (root / "derived.py").write_text(
                "from .base import Base\nclass Derived(Base):\n    def f(self): pass\n",
                encoding="utf-8",
            )
            (root / "bad.py").write_text("def bad(:\n", encoding="utf-8")
            include = lambda path, is_dir: path.name != "bad.py"
            strict = shikake.parse_package(root, include=include)
            partial = shikake.inspect_package(root, include=include)
            self.assertTrue(partial.complete)
            self.assertEqual(strict.model, partial.model)
            self.assertEqual(module_names(strict.model), ["pkg.base", "pkg.derived"])
            self.assertEqual(len(strict.override_candidates), 1)
            self.assertEqual(len(partial.override_candidates), 1)
            self.assertEqual(len(strict.base_references), 1)
            self.assertTrue(strict.name_bindings)

            def binding_facts(
                bindings: tuple[shikake.NameBinding, ...],
            ) -> list[tuple[str, str, str, object]]:
                return [
                    (binding.module, binding.scope.kind.id, binding.name, binding.state)
                    for binding in bindings
                ]

            self.assertEqual(
                binding_facts(strict.name_bindings),
                binding_facts(partial.name_bindings),
            )
            # Omitting a dependency changes the selected input set, not the
            # completeness indicator; missing targets cannot be invented.
            only_derived = lambda path, is_dir: path.name == "derived.py"
            result = shikake.inspect_package(root, include=only_derived)
            self.assertTrue(result.complete)
            self.assertEqual(module_names(result.model), ["pkg.derived"])
            self.assertEqual(result.override_candidates, ())

    def test_all_excluded_is_a_complete_empty_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            (root / "child").mkdir(parents=True)
            (root / "main.py").write_text("pass\n", encoding="utf-8")
            for parse in (shikake.parse_package, shikake.inspect_package):
                result = parse(root, include=lambda path, is_dir: False)
                self.assertEqual(module_names(result.model), [])
                self.assertEqual(result.model.get("name"), "pkg")
                if isinstance(result, shikake.PackageInspection):
                    self.assertTrue(result.complete)
                    self.assertEqual(result.issues, ())

    def test_callback_failure_is_not_turned_into_partial_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            (root / "child").mkdir(parents=True)
            (root / "file.py").write_text("pass\n", encoding="utf-8")

            def fail(path: Path, is_directory: bool) -> bool:
                raise RuntimeError(f"selector failed: {path.name}")

            for parse in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaisesRegex(RuntimeError, "selector failed"):
                    parse(root, include=fail)

    def test_root_contract_and_symlinks_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "pkg"
            root.mkdir()
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (outside / "source.py").write_text("pass\n", encoding="utf-8")
            (root / "own.py").write_text("pass\n", encoding="utf-8")
            try:
                (root / "linked").symlink_to(outside, target_is_directory=True)
                (root / "linked.py").symlink_to(outside / "source.py")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            for parse in (shikake.parse_package, shikake.inspect_package):
                seen: list[Path] = []

                def include(
                    path: Path,
                    is_directory: bool,
                    *,
                    captured: list[Path] = seen,
                ) -> bool:
                    captured.append(path)
                    return True

                result = parse(root, include=include)
                self.assertEqual(module_names(result.model), ["pkg.own"])
                self.assertEqual(seen, [root / "own.py"])
                linked_root = Path(temporary) / "linked-root"
                if not linked_root.exists():
                    linked_root.symlink_to(root, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "package symlinks"):
                    parse(linked_root, include=include)


if __name__ == "__main__":
    unittest.main()
