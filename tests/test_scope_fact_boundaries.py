"""Scope/namespace boundaries and AST header facts used by base references."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import shikake


class SyntaxBoundaryTests(unittest.TestCase):
    def parse(self, sources: dict[str, str]) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / "sample"
            package.mkdir()
            for filename, code in sources.items():
                (package / filename).write_text(code, encoding="utf-8")
            return shikake.parse_package(package)

    def ref(self, package: shikake.PackageModel, name: str) -> shikake.BaseReference:
        matches = [
            ref
            for ref in package.base_references
            if ref.subject.get_name("name") == name
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_nested_class_does_not_inherit_enclosing_class_namespace(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Outer:\n"
                    "    class Base:\n"
                    "        def run(self): pass\n"
                    "    class Inner:\n"
                    "        class Derived(Base):\n"
                    "            def run(self): pass\n"
                )
            }
        )
        derived = self.ref(package, "Derived")
        self.assertEqual(derived.targets, ())
        self.assertIsNone(derived.binding)
        self.assertEqual(package.override_candidates, ())

    def test_direct_sibling_class_and_enclosing_function_remain_visible(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Outer:\n"
                    "    class Base: pass\n"
                    "    class Direct(Base): pass\n"
                    "def build():\n"
                    "    class Local: pass\n"
                    "    class Container:\n"
                    "        class Nested(Local): pass\n"
                )
            }
        )
        self.assertEqual(
            [m.get_name("name") for m in self.ref(package, "Direct").targets], ["Base"]
        )
        self.assertEqual(
            [m.get_name("name") for m in self.ref(package, "Nested").targets], ["Local"]
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_function_type_parameter_shadows_module_class(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class T:\n    def run(self): pass\n"
                    "def factory[T]():\n"
                    "    class Derived(T):\n"
                    "        def run(self): pass\n"
                )
            }
        )
        derived = self.ref(package, "Derived")
        self.assertEqual(derived.targets, ())
        self.assertEqual(
            derived.binding, shikake.BindingState("stable", False, False, False)
        )
        self.assertEqual(package.override_candidates, ())

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_class_type_parameter_shadows_module_class_in_header(self) -> None:
        package = self.parse({"case.py": "class T: pass\nclass Derived[T](T): pass\n"})
        derived = self.ref(package, "Derived")
        self.assertEqual(derived.targets, ())
        self.assertEqual(
            derived.binding, shikake.BindingState("stable", False, False, False)
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_class_type_parameter_is_stable_within_class_body(self) -> None:
        package = self.parse(
            {"case.py": "class T: pass\nclass Owner[T]:\n    class Derived(T): pass\n"}
        )
        derived = self.ref(package, "Derived")
        self.assertEqual(derived.targets, ())
        self.assertEqual(
            derived.binding, shikake.BindingState("stable", False, False, False)
        )
        owner = next(
            node
            for node in package.walk()
            if node.kind.id == "model.definition.class"
            and node.get_name("name") == "Owner"
        )
        (parameter,) = package.bindings_for(owner, "T")
        self.assertEqual(
            parameter.state, shikake.BindingState("stable", False, False, False)
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_function_type_parameter_shadows_class_in_method(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class T: pass\n"
                    "class Container:\n"
                    "    def factory[T](self):\n"
                    "        class Derived(T): pass\n"
                )
            }
        )
        derived = self.ref(package, "Derived")
        self.assertEqual(derived.targets, ())
        self.assertEqual(
            derived.binding, shikake.BindingState("stable", False, False, False)
        )

    def test_star_import_does_not_assume_member_of_explicit_all(self) -> None:
        package = self.parse(
            {
                "base.py": "__all__ = ['Other']\nclass Other: pass\nclass Base:\n    def run(self): pass\n",
                "case.py": "from .base import *\nclass Derived(Base):\n    def run(self): pass\n",
            }
        )
        self.assertEqual(self.ref(package, "Derived").targets, ())
        self.assertEqual(package.override_candidates, ())

    def test_dynamic_all_does_not_guess_star_export(self) -> None:
        package = self.parse(
            {
                "base.py": "__all__ = get_exports()\nclass Base: pass\n",
                "case.py": "from .base import *\nclass Derived(Base): pass\n",
            }
        )
        self.assertEqual(self.ref(package, "Derived").targets, ())

    def test_explicit_import_ignores_star_export_restriction(self) -> None:
        package = self.parse(
            {
                "base.py": "__all__ = ['Other']\nclass Base: pass\n",
                "case.py": "from .base import Base\nclass Derived(Base): pass\n",
            }
        )
        self.assertEqual(
            [m.get_name("name") for m in self.ref(package, "Derived").targets], ["Base"]
        )

    def test_definition_cannot_be_its_own_base_but_import_can(self) -> None:
        package = self.parse(
            {
                "a.py": "class Base:\n    def f(self): pass\n",
                "b.py": "from .a import Base\nclass Base(Base):\n    def f(self): pass\n",
            }
        )
        new_class = self.ref(package, "Base")
        (target,) = new_class.targets
        self.assertIsNot(target, new_class.subject)
        self.assertEqual(len(package.override_candidates), 1)
        candidate = package.override_candidates[0]
        self.assertIs(candidate.derived_class, new_class.subject)
        self.assertIs(candidate.base_class, target)
        self.assertIsNot(candidate.method, candidate.base_method)
        self.assertTrue(new_class.binding.may_rebind)  # type: ignore[union-attr]

    def test_earlier_same_name_class_remains_base_candidate(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Base:\n"
                    "    def run(self): pass\n"
                    "class Base(Base):\n"
                    "    def run(self): pass\n"
                )
            }
        )
        (reference,) = package.base_references
        (target,) = reference.targets
        self.assertIsNot(target, reference.subject)
        self.assertEqual(len(package.override_candidates), 1)
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", True, False, False)
        )

    def test_only_self_declaration_does_not_create_self_candidate(self) -> None:
        package = self.parse({"case.py": "class Base(Base):\n    def f(self): pass\n"})
        self.assertEqual(self.ref(package, "Base").targets, ())
        self.assertEqual(package.override_candidates, ())

    def test_self_definition_does_not_fall_back_to_enclosing_scope(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Base:\n    def f(self): pass\n"
                    "def factory():\n"
                    "    class Base(Base):\n        def f(self): pass\n"
                )
            }
        )
        (reference,) = package.base_references
        self.assertEqual(reference.targets, ())
        self.assertEqual(package.override_candidates, ())

    def test_class_keyword_named_expression_is_a_write(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class A: pass\n"
                    "class M(type): pass\n"
                    "class Derived(A, metaclass=(A := M)): pass\n"
                )
            }
        )
        derived = self.ref(package, "Derived")
        self.assertEqual(
            derived.binding, shikake.BindingState("stable", True, False, False)
        )


if __name__ == "__main__":
    unittest.main()
