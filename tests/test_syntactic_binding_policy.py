"""Binding facts report syntax, independently of discovered class edges."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class SyntacticBindingPolicyTests(unittest.TestCase):
    def analyze(self, code: str) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "sample"
            folder.mkdir()
            (folder / "case.py").write_text(code, encoding="utf-8")
            return shikake.parse_package(folder)

    def binding(self, package: shikake.PackageModel, name: str) -> shikake.BindingState:
        root = next(m for m in package.walk() if m.kind.id == "model.module")
        return package.bindings_for(root, name)[0].state

    def test_first_assignment_and_subsequent_writes_are_distinct(self) -> None:
        self.assertFalse(self.binding(self.analyze("X = 1\n"), "X").may_rebind)
        for src in (
            "X = 1\nX = 2\n",
            "if flag:\n    X = 1\nelse:\n    X = 2\n",
            "try:\n    X = 1\nexcept Exception:\n    X = 2\n",
            "for v in values:\n    X = 1\nelse:\n    X = 2\n",
            "for v in values:\n    X = 1\n",
        ):
            with self.subTest(src=src):
                self.assertTrue(self.binding(self.analyze(src), "X").may_rebind)

    def test_later_write_does_not_rewrite_base_reference(self) -> None:
        package = self.analyze(
            "class Base:\n    def run(self): pass\n"
            "class D(Base):\n    def run(self): pass\nBase = Other\n"
        )
        (ref,) = package.base_references
        self.assertTrue(ref.binding.may_rebind)  # type: ignore[union-attr]
        self.assertEqual(ref.targets[0].get_name("name"), "Base")
        self.assertEqual(len(package.override_candidates), 1)

    def test_try_and_loop_written_changes(self) -> None:
        prefix = "class Base:\n    def run(self): pass\n"
        snippets = (
            "try:\n    Base = Other\nexcept Exception:\n    class D(Base):\n        def run(self): pass\n",
            "try:\n    Base = Other\nexcept Exception:\n    pass\nelse:\n    class D(Base):\n        def run(self): pass\n",
            "try:\n    Base = Other\nfinally:\n    class D(Base):\n        def run(self): pass\n",
            "for x in xs:\n    Base = Other\nelse:\n    class D(Base):\n        def run(self): pass\n",
            "for x in xs:\n    class D(Base):\n        def run(self): pass\n    Base = Other\n",
        )
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                package = self.analyze(prefix + snippet)
                self.assertEqual(len(package.base_references), 1)
                self.assertTrue(package.base_references[0].binding.may_rebind)  # type: ignore[union-attr]

    def test_function_parameter_shadows_module_class(self) -> None:
        package = self.analyze(
            "class Base:\n    def run(self): pass\n"
            "def factory(Base):\n    class D(Base):\n        def run(self): pass\n"
        )
        (ref,) = package.base_references
        self.assertEqual(ref.targets, ())
        self.assertEqual(
            ref.binding, shikake.BindingState("stable", False, False, False)
        )
        self.assertFalse(self.binding(package, "Base").may_rebind)

    def test_default_and_match_guard_writes(self) -> None:
        prefix = "class Base:\n    def run(self): pass\n"
        for snippet in (
            "def f(x=(Base := Other)): pass\n",
            "match value:\n    case _ if (Base := Other): pass\n",
        ):
            with self.subTest(snippet=snippet):
                package = self.analyze(prefix + snippet + "class D(Base): pass\n")
                self.assertTrue(package.base_references[0].binding.may_rebind)  # type: ignore[union-attr]

    def test_same_module_attribute_write_is_a_separate_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "sample"
            folder.mkdir()
            (folder / "a.py").write_text("class Base: pass\n")
            (folder / "b.py").write_text(
                "import sample.a as a\na.Base = Other\nclass D(a.Base): pass\n"
            )
            package = shikake.parse_package(folder)
        (ref,) = package.base_references
        self.assertTrue(ref.attribute_modified)
        self.assertEqual(
            ref.binding, shikake.BindingState("stable", False, False, True)
        )

    def test_member_writes_do_not_delete_the_method_definition_fact(self) -> None:
        for changed in ("Base.run = None", "del Base.run"):
            with self.subTest(changed=changed):
                package = self.analyze(
                    "class Base:\n    def run(self): pass\n"
                    + changed
                    + "\nclass D(Base):\n    def run(self): pass\n"
                )
                self.assertEqual(len(package.override_candidates), 1)

    def test_decorator_walrus_is_not_a_method_declaration(self) -> None:
        package = self.analyze(
            "class Base:\n    def run(self): pass\n"
            "class D(Base):\n    @(run := decorator)\n    def helper(self): pass\n"
        )
        self.assertEqual(package.override_candidates, ())


if __name__ == "__main__":
    unittest.main()
