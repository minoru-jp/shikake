"""Candidates are structural, independent of timing and admissibility."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake

BASE = "class Base:\n    def action(self): pass\n"
DERIVED = "class Derived(Base):\n    def action(self): pass\n"


class OverrideBindingOrderTests(unittest.TestCase):
    def analyze(self, sources: dict[str, str]) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            for filename, source in sources.items():
                (root / filename).write_text(source, encoding="utf-8")
            result = shikake.parse_package(root)
            inspected = shikake.inspect_package(root)
            self.assertTrue(inspected.complete)
            self.assertEqual(
                len(result.override_candidates), len(inspected.override_candidates)
            )
            return result

    def test_direct_import_alias_keeps_possible_definition(self) -> None:
        result = self.analyze({"case.py": BASE + "import other as Base\n" + DERIVED})
        (reference,) = result.base_references
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]
        self.assertEqual(len(result.override_candidates), 1)

    def test_later_definition_is_not_invented_as_prior_binding(self) -> None:
        result = self.analyze({"case.py": DERIVED + BASE})
        (reference,) = result.base_references
        self.assertEqual(reference.targets, ())
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(result.override_candidates, ())

    def test_multiple_written_definitions_remain_possible(self) -> None:
        result = self.analyze({"case.py": BASE + DERIVED + BASE})
        (reference,) = result.base_references
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]
        # The later same-scope definition still affects the name's three
        # properties, but cannot become a candidate at an earlier base site.
        self.assertEqual(len(reference.targets), 1)
        first_base = next(
            model
            for model in result.walk()
            if model.kind.id == "model.definition.class"
            and model.get_name("name") == "Base"
        )
        self.assertIs(reference.targets[0], first_base)

    def test_later_imports_do_not_introduce_earlier_targets(self) -> None:
        for suffix, expression in (
            ("from .base import Base\n", "Base"),
            ("import sample.base as imported\n", "imported.Base"),
            ("from .base import *\n", "Base"),
        ):
            with self.subTest(suffix=suffix):
                result = self.analyze(
                    {
                        "base.py": BASE,
                        "case.py": f"class D({expression}):\n    def action(self): pass\n"
                        + suffix,
                    }
                )
                (reference,) = result.base_references
                self.assertEqual(reference.targets, ())
                self.assertEqual(result.override_candidates, ())
                if not suffix.startswith("from .base import *"):
                    self.assertEqual(
                        reference.binding,
                        shikake.BindingState("stable", False, False),
                    )

    def test_later_function_local_masks_outer_class(self) -> None:
        result = self.analyze(
            {
                "case.py": (
                    BASE + "def factory():\n"
                    "    class D(Base):\n        def action(self): pass\n"
                    "    class Base: pass\n"
                )
            }
        )
        (reference,) = result.base_references
        self.assertEqual(reference.targets, ())
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )

    def test_later_enclosing_module_class_is_not_ordered_across_scopes(self) -> None:
        result = self.analyze(
            {
                "case.py": (
                    "def factory():\n"
                    "    class D(Base):\n        def action(self): pass\n" + BASE
                )
            }
        )
        (reference,) = result.base_references
        self.assertEqual([m.get_name("name") for m in reference.targets], ["Base"])
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(len(result.override_candidates), 1)

    def test_later_class_body_definition_is_not_earlier_base(self) -> None:
        result = self.analyze(
            {
                "case.py": (
                    BASE + "class Outer:\n"
                    "    class D(Base):\n        def action(self): pass\n"
                    "    class Base: pass\n"
                )
            }
        )
        (reference,) = result.base_references
        self.assertEqual(reference.targets, ())
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )

    def test_conditional_write_and_deletion_are_independent(self) -> None:
        for statement in (
            "if flag:\n    Base = other\n",
            "with manager() as Base: pass\n",
            "for Base in choices: pass\n",
            "del Base\n",
        ):
            with self.subTest(statement=statement):
                result = self.analyze({"case.py": BASE + statement + DERIVED})
                reference = result.base_references[0]
                binding = reference.binding
                self.assertIsNotNone(binding)
                assert binding is not None
                self.assertTrue(binding.may_rebind or binding.may_delete)
                self.assertEqual(len(result.override_candidates), 1)

    def test_importing_module_keeps_own_local_state(self) -> None:
        result = self.analyze(
            {
                "base.py": BASE + "Base = something_else\n",
                "case.py": "from .base import Base\n" + DERIVED,
            }
        )
        (reference,) = result.base_references
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual([t.get_name("name") for t in reference.targets], ["Base"])

    def test_known_imported_candidate(self) -> None:
        result = self.analyze(
            {"base.py": BASE, "case.py": "from .base import Base\n" + DERIVED}
        )
        self.assertEqual(len(result.override_candidates), 1)
        self.assertEqual(result.override_candidates[0].base_module, "sample.base")


if __name__ == "__main__":
    unittest.main()
