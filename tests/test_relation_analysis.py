"""Written bases have independent binding states, never relation statuses."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake

BASE = "class Base:\n    def action(self): pass\n"
DERIVED = "class Derived(Base):\n    def action(self): pass\n"


class RelationAnalysisTests(unittest.TestCase):
    def analyze(
        self, code: str, *, analyses: set[str] | None = None
    ) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "sample"
            directory.mkdir()
            (directory / "case.py").write_text(code, encoding="utf-8")
            return shikake.parse_package(directory, analyses=analyses)

    def test_written_base_and_override_candidate_are_independent(self) -> None:
        package = self.analyze(BASE + DERIVED)
        (base,) = package.base_references
        self.assertEqual(base.subject.get_name("name"), "Derived")
        self.assertIs(base.expression, package.bases_for(base.subject)[0].expression)
        self.assertEqual(base.targets[0].get_name("name"), "Base")
        self.assertEqual(base.binding, shikake.BindingState("stable", False, False))
        (candidate,) = package.override_candidates
        self.assertEqual(candidate.base_module, "sample.case")
        self.assertEqual(package.overrides_for(candidate.method), (candidate,))
        self.assertFalse(hasattr(package, "relations"))
        self.assertFalse(hasattr(base, "status"))
        self.assertFalse(hasattr(base, "reasons"))

    def test_each_base_has_its_own_binding_state(self) -> None:
        package = self.analyze(
            "class A: pass\n"
            "class B: pass\nB = Other\n"
            "class C: pass\ndel C\n"
            "class X(A, B, C, Missing, factory()): pass\n",
            analyses={"inheritance"},
        )
        x = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.class"
            and model.get_name("name") == "X"
        )
        refs = package.bases_for(x)
        self.assertEqual(len(refs), 5)
        self.assertEqual(
            [r.binding for r in refs],
            [
                shikake.BindingState("stable", False, False),
                shikake.BindingState("stable", True, False),
                shikake.BindingState("stable", False, True),
                None,
                None,
            ],
        )
        self.assertEqual(
            [[t.get_name("name") for t in r.targets] for r in refs],
            [["A"], ["B"], ["C"], [], []],
        )

    def test_branch_definitions_remain_multiple_candidates(self) -> None:
        package = self.analyze(
            "if flag:\n    class Base: pass\n"
            "else:\n    class Base: pass\n"
            "class D(Base): pass\n",
            analyses={"inheritance"},
        )
        (ref,) = package.base_references
        self.assertEqual(ref.binding, shikake.BindingState("unstable", True, False))
        self.assertEqual(len(ref.targets), 2)

    def test_written_changes_are_independent_of_location(self) -> None:
        for middle, expected in (
            ("Base = other\n", shikake.BindingState("stable", True, False)),
            ("del Base\n", shikake.BindingState("stable", False, True)),
            (
                "if flag:\n    Base = other\n",
                shikake.BindingState("stable", True, False),
            ),
        ):
            for before in (True, False):
                with self.subTest(middle=middle, before=before):
                    code = BASE + (middle + DERIVED if before else DERIVED + middle)
                    package = self.analyze(code)
                    self.assertEqual(package.base_references[0].binding, expected)
                    self.assertEqual(len(package.base_references[0].targets), 1)
                    self.assertEqual(len(package.override_candidates), 1)

    def test_root_binding_is_local_to_importing_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "sample"
            folder.mkdir()
            (folder / "a.py").write_text(BASE + "Base = other\n")
            (folder / "b.py").write_text("from .a import Base\n" + DERIVED)
            result = shikake.parse_package(folder)
        (reference,) = result.base_references
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual([t.get_name("name") for t in reference.targets], ["Base"])
        # A change in an imported module is not part of the local binding state.

    def test_attribute_change_is_a_separate_written_fact(self) -> None:
        for code, expected in (
            ("Base.run = None\n", False),
            ("Base.X = None\n", False),
            ("Base = other\n", False),
        ):
            with self.subTest(code=code):
                package = self.analyze(BASE + DERIVED + code)
                self.assertEqual(
                    package.base_references[0].attribute_modified, expected
                )
        result = self.analyze(BASE + "Base.attr = other\nclass D(Base.attr): pass\n")
        self.assertTrue(result.base_references[0].attribute_modified)

    def test_override_candidates_are_possible_matches_not_admissibility(self) -> None:
        package = self.analyze(BASE + DERIVED + "Base = Other\n")
        self.assertEqual(len(package.override_candidates), 1)
        self.assertTrue(package.base_references[0].binding.may_rebind)  # type: ignore[union-attr]

    def test_multiple_bases_and_diamond_are_deduplicated(self) -> None:
        package = self.analyze(
            "class Root:\n    def run(self): pass\n"
            "class Left(Root): pass\n"
            "class Right(Root): pass\n"
            "class Child(Left, Right):\n    def run(self): pass\n"
        )
        matches = [
            c
            for c in package.override_candidates
            if c.derived_class.get_name("name") == "Child"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].base_class.get_name("name"), "Root")
        self.assertEqual(
            len(
                [
                    r
                    for r in package.base_references
                    if r.subject.get_name("name") == "Child"
                ]
            ),
            2,
        )

    def test_known_unknown_ancestors_do_not_suppress_known_matches(self) -> None:
        package = self.analyze(
            "class Known:\n    def run(self): pass\n"
            "class Left(Known): pass\n"
            "class Right(Missing): pass\n"
            "class Child(Left, Right):\n    def run(self): pass\n"
        )
        self.assertEqual(len(package.override_candidates), 1)
        refs = [
            r for r in package.base_references if r.subject.get_name("name") == "Right"
        ]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].targets, ())
        self.assertIsNone(refs[0].binding)

    def test_deep_chain_iterative(self) -> None:
        lines = ["class A0:\n    def run(self): pass\n"]
        lines.extend(f"class A{i}(A{i - 1}): pass\n" for i in range(1, 110))
        lines.append("class End(A109):\n    def run(self): pass\n")
        result = self.analyze("".join(lines))
        self.assertEqual(
            result.override_candidates[0].base_class.get_name("name"), "A0"
        )

    def test_computed_base_keeps_expression_without_invented_binding(self) -> None:
        package = self.analyze("class D(factory()): pass\n")
        (reference,) = package.base_references
        self.assertIsNone(reference.binding)
        self.assertEqual(reference.targets, ())

    def test_selected_analyses_and_partial_handling(self) -> None:
        unexamined = self.analyze(BASE + DERIVED, analyses=set())
        self.assertEqual(unexamined.base_references, ())
        self.assertEqual(unexamined.override_candidates, ())
        self.assertTrue(unexamined.name_bindings)
        bases_only = self.analyze(BASE + DERIVED, analyses={"inheritance"})
        self.assertEqual(len(bases_only.base_references), 1)
        self.assertEqual(bases_only.override_candidates, ())
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "sample"
            directory.mkdir()
            (directory / "a.py").write_text(BASE + DERIVED)
            (directory / "bad.py").write_text("def broken(: pass")
            inspected = shikake.inspect_package(directory)
            self.assertFalse(inspected.complete)
            self.assertEqual(inspected.base_references, ())
            self.assertEqual(inspected.override_candidates, ())
            self.assertEqual(inspected.analyses, frozenset())


if __name__ == "__main__":
    unittest.main()
