"""Public per-base contract: no inferred whole-relation classification."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class BaseReferenceContractTests(unittest.TestCase):
    def parse(
        self, code: str, analyses: set[str] | None = None
    ) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "sample"
            folder.mkdir()
            (folder / "case.py").write_text(code, encoding="utf-8")
            return shikake.parse_package(folder, analyses=analyses)

    def ref(self, code: str) -> shikake.BaseReference:
        package = self.parse(code, analyses={"inheritance"})
        self.assertEqual(len(package.base_references), 1)
        return package.base_references[0]

    def test_public_api_does_not_publish_relation_results(self) -> None:
        self.assertFalse(hasattr(shikake, "RelationResult"))

    def test_ref_has_no_legacy_status(self) -> None:
        reference = self.ref("class A: pass\nclass D(A): pass\n")
        self.assertFalse(hasattr(reference, "status"))

    def test_ref_has_no_legacy_reasons(self) -> None:
        reference = self.ref("class A: pass\nclass D(A): pass\n")
        self.assertFalse(hasattr(reference, "reasons"))

    def test_single_unconditional_class_introduction(self) -> None:
        reference = self.ref("class A: pass\nclass D(A): pass\n")
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )

    def test_base_reference_reports_implicit_except_deletion(self) -> None:
        reference = self.ref(
            "class Base: pass\n"
            "try:\n    work()\n"
            "except ValueError as Base:\n    pass\n"
            "class D(Base): pass\n"
        )
        self.assertEqual(reference.binding, shikake.BindingState("stable", True, True))

    def test_initial_assignment_is_not_a_rebind(self) -> None:
        reference = self.ref("A = Unknown\nclass D(A): pass\n")
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )

    def test_conditional_class_introduction(self) -> None:
        reference = self.ref("if flag:\n    class A: pass\nclass D(A): pass\n")
        self.assertEqual(
            reference.binding, shikake.BindingState("unstable", False, False)
        )

    def test_repeated_class_introduction(self) -> None:
        reference = self.ref("class A: pass\nclass A: pass\nclass D(A): pass\n")
        self.assertEqual(reference.binding, shikake.BindingState("stable", True, False))
        self.assertEqual(len(reference.targets), 2)

    def test_deletion_after_base_reference(self) -> None:
        reference = self.ref("class A: pass\nclass D(A): pass\ndel A\n")
        self.assertEqual(reference.binding, shikake.BindingState("stable", False, True))

    def test_rebinding_after_base_reference(self) -> None:
        reference = self.ref("class A: pass\nclass D(A): pass\nA = something\n")
        self.assertEqual(reference.binding, shikake.BindingState("stable", True, False))

    def test_global_assignment_is_reported(self) -> None:
        reference = self.ref(
            "class A: pass\ndef f():\n    global A\n    A = Other\nclass D(A): pass\n"
        )
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]

    def test_local_assignment_does_not_change_module_name(self) -> None:
        reference = self.ref(
            "class A: pass\ndef f():\n    A = Other\nclass D(A): pass\n"
        )
        self.assertFalse(reference.binding.may_rebind)  # type: ignore[union-attr]

    def test_import_from_unknown_is_stable_locally(self) -> None:
        reference = self.ref("from unknown import Base\nclass D(Base): pass\n")
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(reference.targets, ())

    def test_unknown_name_has_no_binding(self) -> None:
        reference = self.ref("class D(Missing): pass\n")
        self.assertIsNone(reference.binding)

    def test_computed_expression_has_no_binding(self) -> None:
        reference = self.ref("class D(factory()): pass\n")
        self.assertIsNone(reference.binding)
        self.assertIsNotNone(reference.expression)

    def test_nested_attribute_uses_root_name_state(self) -> None:
        reference = self.ref("class A:\n    class B: pass\nclass D(A.B): pass\n")
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(reference.targets[0].get_name("name"), "B")

    def test_attribute_write_is_not_root_rebinding(self) -> None:
        reference = self.ref("class A: pass\nA.B = Other\nclass D(A.B): pass\n")
        self.assertTrue(reference.attribute_modified)
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )

    def test_attribute_deletion_is_a_separate_fact(self) -> None:
        reference = self.ref("class A: pass\ndel A.B\nclass D(A.B): pass\n")
        self.assertTrue(reference.attribute_modified)
        self.assertFalse(reference.binding.may_delete)  # type: ignore[union-attr]

    def test_unrelated_attribute_write_does_not_match(self) -> None:
        reference = self.ref(
            "class A:\n    class B: pass\nOther.B = x\nclass D(A.B): pass\n"
        )
        self.assertFalse(reference.attribute_modified)

    def test_separate_if_branches_are_not_executed(self) -> None:
        reference = self.ref(
            "if flag:\n    class A: pass\nelse:\n    class A: pass\nclass D(A): pass\n"
        )
        self.assertEqual(
            reference.binding, shikake.BindingState("unstable", True, False)
        )

    def test_try_blocks_do_not_suppress_written_operations(self) -> None:
        reference = self.ref(
            "class A: pass\ntry:\n    A = Other\nexcept Exception:\n    pass\nclass D(A): pass\n"
        )
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]

    def test_loop_blocks_do_not_suppress_written_operations(self) -> None:
        reference = self.ref(
            "class A: pass\nfor i in items:\n    A = Other\nclass D(A): pass\n"
        )
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]

    def test_nested_class_can_see_outer_class_definition(self) -> None:
        reference = self.ref("class Outer:\n    class A: pass\n    class D(A): pass\n")
        self.assertEqual(reference.targets[0].get_name("name"), "A")

    def test_function_does_not_close_over_class_scope(self) -> None:
        reference = self.ref(
            "class Outer:\n    class A: pass\n    def f(self):\n        class D(A): pass\n"
        )
        self.assertEqual(reference.targets, ())
        self.assertIsNone(reference.binding)

    def test_base_reference_order_is_preserved(self) -> None:
        package = self.parse("class A: pass\nclass B: pass\nclass D(A, B): pass\n")
        self.assertEqual(
            [r.expression.get_name("name") for r in package.base_references], ["A", "B"]
        )

    def test_no_inheritance_analysis_still_exposes_name_bindings(self) -> None:
        package = self.parse("class A: pass\nclass D(A): pass\n", analyses=set())
        self.assertEqual(package.base_references, ())
        self.assertTrue(package.name_bindings)

    def test_bases_for_requires_exact_class_identity(self) -> None:
        package = self.parse("class A: pass\nclass B: pass\nclass D(A, B): pass\n")
        d = next(
            m
            for m in package.walk()
            if m.kind.id == "model.definition.class" and m.get_name("name") == "D"
        )
        a = next(
            m
            for m in package.walk()
            if m.kind.id == "model.definition.class" and m.get_name("name") == "A"
        )
        self.assertEqual(len(package.bases_for(d)), 2)
        self.assertEqual(package.bases_for(a), ())

    def test_known_override_candidate_survives_rebinding_flag(self) -> None:
        package = self.parse(
            "class A:\n    def run(self): pass\nclass D(A):\n    def run(self): pass\nA = other\n"
        )
        self.assertEqual(len(package.override_candidates), 1)
        self.assertTrue(package.base_references[0].binding.may_rebind)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
