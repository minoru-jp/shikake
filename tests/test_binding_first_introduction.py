"""Initial introductions, augmented writes, and repeatability are distinct facts."""

from __future__ import annotations

import unittest

import shikake


class BindingFirstIntroductionTests(unittest.TestCase):
    def state(self, source: str, name: str) -> shikake.BindingState:
        # One legacy AST-shape test intentionally uses a comprehension walrus
        # rejected by CPython's compiler; keep that test at the AST level.
        mode = "ast" if "seen := item" in source else "compile"
        result = shikake.inspect_source(source, syntax_validation=mode)
        self.assertTrue(result.complete, result.issues)
        states = [
            binding.state
            for binding in result.name_bindings
            if binding.scope is result.model and binding.name == name
        ]
        self.assertEqual(len(states), 1)
        return states[0]

    def test_first_independent_introduction_does_not_count_as_rebind(self) -> None:
        for source, name in (
            ("x = 1", "x"),
            ("x: int = 1", "x"),
            ("import math as x", "x"),
            ("from math import sin as x", "x"),
            ("class X: pass", "X"),
            ("def x(): pass", "x"),
            ("(x := 1)", "x"),
            ("with manager() as x:\n    pass", "x"),
        ):
            with self.subTest(source=source):
                self.assertEqual(
                    self.state(source, name),
                    shikake.BindingState(
                        "stable" if not source.startswith("with") else "unstable",
                        False,
                        False,
                        False,
                    ),
                )

    def test_second_introduction_is_a_possible_rebind(self) -> None:
        for source in (
            "x = 1\nx = 2",
            "import math as x\nx = 2",
            "class x: pass\nx = 2",
            "if flag:\n    x = 1\nelse:\n    x = 2",
        ):
            with self.subTest(source=source):
                self.assertTrue(self.state(source, "x").may_rebind)

    def test_conditional_single_write_is_not_automatically_a_rebind(self) -> None:
        self.assertEqual(
            self.state("if flag:\n    x = 1", "x"),
            shikake.BindingState("unstable", False, False, False),
        )

    def test_augmented_assignment_cannot_stably_introduce(self) -> None:
        self.assertEqual(
            self.state("n += 1", "n"),
            shikake.BindingState("unstable", True, False, False),
        )
        self.assertEqual(
            self.state("n = 0\nn += 1", "n"),
            shikake.BindingState("stable", True, False, False),
        )
        self.assertEqual(
            self.state("n += 1\nn = 0", "n"),
            shikake.BindingState("unstable", True, False, False),
        )

    def test_repeatable_writes(self) -> None:
        for source, name in (
            ("for x in values:\n    pass", "x"),
            ("for item in values:\n    x = item", "x"),
            ("while flag:\n    x = 1", "x"),
            ("[x for x in ((seen := item) for item in xs)]", "seen"),
        ):
            with self.subTest(source=source):
                result = self.state(source, name)
                self.assertEqual(result.introduction, "unstable")
                self.assertTrue(result.may_rebind)

    def test_nested_function_scope_does_not_inherit_loop_repeatability(self) -> None:
        result = shikake.inspect_source(
            "for _ in items:\n    def f():\n        x = 1\n"
        )
        self.assertTrue(result.complete)
        (local,) = [binding for binding in result.name_bindings if binding.name == "x"]
        self.assertEqual(
            local.state, shikake.BindingState("stable", False, False, False)
        )

    def test_class_candidates_survive_rebindings_and_conditional_imports(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "sample"
            root.mkdir()
            (root / "base.py").write_text("class Base:\n    def run(self): pass\n")
            (root / "alt.py").write_text("class Base:\n    def run(self): pass\n")
            (root / "child.py").write_text(
                "try:\n    from .base import Base\n"
                "except ImportError:\n    from .alt import Base\n"
                "class Child(Base):\n    def run(self): pass\n"
            )
            result = shikake.parse_package(root)
        reference = next(
            ref
            for ref in result.base_references
            if ref.subject.get_name("name") == "Child"
        )
        self.assertEqual(len(reference.targets), 2)
        self.assertEqual(
            reference.binding, shikake.BindingState("unstable", True, False, False)
        )
        self.assertEqual(len(result.override_candidates), 2)


if __name__ == "__main__":
    unittest.main()
