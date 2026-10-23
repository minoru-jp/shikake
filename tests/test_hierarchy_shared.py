"""Ancestor declarations are possible matches; no hierarchy status exists."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class SharedHierarchyTests(unittest.TestCase):
    def analyze(self, code: str) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "sample"
            folder.mkdir()
            (folder / "case.py").write_text(code, encoding="utf-8")
            return shikake.parse_package(folder)

    def test_diamond_deduplicates_method_declarations(self) -> None:
        package = self.analyze(
            "class Root:\n    def f(self): pass\n    def g(self): pass\n"
            "class Left(Root): pass\nclass Right(Root): pass\n"
            "class Child(Left, Right):\n    def f(self): pass\n    def g(self): pass\n"
        )
        found = [
            c
            for c in package.override_candidates
            if c.derived_class.get_name("name") == "Child"
        ]
        self.assertEqual(len(found), 2)
        self.assertEqual(
            [c.base_class.get_name("name") for c in found], ["Root", "Root"]
        )

    def test_missing_ancestor_does_not_hide_known_one(self) -> None:
        package = self.analyze(
            "class Known:\n    def f(self): pass\n"
            "class Left(Known): pass\nclass Right(Missing): pass\n"
            "class Child(Left, Right):\n    def f(self): pass\n"
        )
        self.assertEqual(len(package.override_candidates), 1)
        right_ref = next(
            r for r in package.base_references if r.subject.get_name("name") == "Right"
        )
        self.assertEqual(right_ref.targets, ())

    def test_member_delete_does_not_erase_written_ancestor_declaration(self) -> None:
        package = self.analyze(
            "class Base:\n    def f(self): pass\n"
            "class Middle(Base):\n    del f\n"
            "class Child(Middle):\n    def f(self): pass\n"
        )
        self.assertEqual(len(package.override_candidates), 1)
        middle = next(
            m
            for m in package.walk()
            if m.kind.id == "model.definition.class" and m.get_name("name") == "Middle"
        )
        self.assertEqual(middle.get_name("name"), "Middle")
        # A deletion without an introduction has no invented BindingState.
        self.assertEqual(package.bindings_for(middle, "f"), ())


if __name__ == "__main__":
    unittest.main()
