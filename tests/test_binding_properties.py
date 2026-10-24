"""Three orthogonal syntactic binding properties, independent of resolution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class BindingPropertiesTests(unittest.TestCase):
    def parse(self, sources: dict[str, str]) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            for name, code in sources.items():
                (root / name).write_text(code, encoding="utf-8")
            return shikake.parse_package(root, analyses=set())

    def module_facts(self, package: shikake.PackageModel, name: str):
        module = next(
            item
            for item in package.walk()
            if item.kind.id == "model.module" and item.get_name("name") == name
        )
        return {
            item.name: item.state
            for item in package.name_bindings
            if item.scope is module
        }

    def test_clean_rebound_and_deleted_are_independent(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class A: pass\nclass B: pass\nB = other\nclass C: pass\ndel C\n"
                )
            }
        )
        flags = self.module_facts(package, "sample.case")
        self.assertEqual(
            flags["A"], shikake.BindingState("stable", False, False, False)
        )
        self.assertEqual(flags["B"], shikake.BindingState("stable", True, False, False))
        self.assertEqual(flags["C"], shikake.BindingState("stable", False, True, False))
        self.assertEqual(package.base_references, ())

    def test_alternative_declarations_and_assignments_are_operations(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "if flag:\n    class A: pass\n"
                    "if flag:\n    class B: pass\nelse:\n    class B: pass\n"
                    "class C: pass\nif flag:\n    C = other\n"
                )
            }
        )
        flags = self.module_facts(package, "sample.case")
        self.assertEqual(
            flags["A"], shikake.BindingState("unstable", False, False, False)
        )
        self.assertEqual(
            flags["B"], shikake.BindingState("unstable", True, False, False)
        )
        self.assertEqual(flags["C"], shikake.BindingState("stable", True, False, False))

    def test_binding_properties_are_module_local_even_for_imports(self) -> None:
        package = self.parse(
            {
                "a.py": "class Base: pass\nBase = other\n",
                "b.py": "from .a import Base\nclass Derived(Base): pass\n",
                "c.py": "from unknown import Base\nclass Derived(Base): pass\n",
            }
        )
        a = self.module_facts(package, "sample.a")
        b = self.module_facts(package, "sample.b")
        c = self.module_facts(package, "sample.c")
        self.assertTrue(a["Base"].may_rebind)
        self.assertEqual(b["Base"], shikake.BindingState("stable", False, False, False))
        self.assertEqual(c["Base"], shikake.BindingState("stable", False, False, False))

    def test_known_star_import_without_name_does_not_rebind_it(self) -> None:
        package = self.parse(
            {
                "exported.py": "class Other: pass\n",
                "case.py": "class Base: pass\nfrom .exported import *\n",
            }
        )
        state = self.module_facts(package, "sample.case")["Base"]
        self.assertEqual(state, shikake.BindingState("stable", False, False, False))

    def test_shadowed_function_local_does_not_change_module(self) -> None:
        package = self.parse(
            {"case.py": ("class X: pass\ndef f():\n    X = 1\n    del X\n")}
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["X"],
            shikake.BindingState("stable", False, False, False),
        )
        function = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.function"
        )
        (local,) = package.bindings_for(function, "X")
        self.assertEqual(
            local.state, shikake.BindingState("stable", False, True, False)
        )

    def test_enclosing_condition_does_not_leak_into_new_scopes(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "if outer_flag:\n"
                    "    def factory(argument):\n"
                    "        class Base: pass\n"
                    "        if inner_flag:\n"
                    "            class Conditional: pass\n"
                    "        class Derived(Base): pass\n"
                    "    class Outer:\n"
                    "        class Member: pass\n"
                    "        if inner_flag:\n"
                    "            class ConditionalMember: pass\n"
                )
            }
        )
        module = self.module_facts(package, "sample.case")
        self.assertEqual(module["factory"].introduction, "unstable")
        self.assertEqual(module["Outer"].introduction, "unstable")
        factory = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.function"
            and model.get_name("name") == "factory"
        )
        factory_bindings = {
            item.name: item.state
            for item in package.name_bindings
            if item.scope is factory
        }
        self.assertEqual(factory_bindings["argument"].introduction, "stable")
        self.assertEqual(factory_bindings["Base"].introduction, "stable")
        self.assertEqual(factory_bindings["Derived"].introduction, "stable")
        self.assertEqual(factory_bindings["Conditional"].introduction, "unstable")
        outer = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.class"
            and model.get_name("name") == "Outer"
        )
        class_bindings = {
            item.name: item.state
            for item in package.name_bindings
            if item.scope is outer
        }
        self.assertEqual(class_bindings["Member"].introduction, "stable")
        self.assertEqual(class_bindings["ConditionalMember"].introduction, "unstable")

    def test_module_global_is_intentionally_unstable_without_binding_itself(
        self,
    ) -> None:
        package = self.parse(
            {
                "case.py": (
                    "global B\n"
                    "global NeverIntroduced\n"
                    "class B: pass\n"
                    "class Derived(B): pass\n"
                    "class Plain: pass\n"
                    "if True:\n    class Conditional: pass\n"
                ),
                "other.py": "class B: pass\n",
            }
        )
        case = self.module_facts(package, "sample.case")
        self.assertEqual(
            case["B"], shikake.BindingState("unstable", False, False, False)
        )
        self.assertEqual(
            case["Derived"], shikake.BindingState("stable", False, False, False)
        )
        self.assertEqual(
            case["Plain"], shikake.BindingState("stable", False, False, False)
        )
        self.assertEqual(
            case["Conditional"], shikake.BindingState("unstable", False, False, False)
        )
        self.assertNotIn("NeverIntroduced", case)
        self.assertEqual(
            self.module_facts(package, "sample.other")["B"],
            shikake.BindingState("stable", False, False, False),
        )

    def test_global_and_nonlocal_operations_retain_their_owners(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class GlobalBase: pass\n"
                    "if flag:\n"
                    "    def change_global():\n"
                    "        global GlobalBase\n"
                    "        GlobalBase = Other\n"
                    "def outer():\n"
                    "    class Local: pass\n"
                    "    if flag:\n"
                    "        def change_nonlocal():\n"
                    "            nonlocal Local\n"
                    "            Local = Other\n"
                )
            }
        )
        self.assertTrue(
            self.module_facts(package, "sample.case")["GlobalBase"].may_rebind
        )
        outer = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.function"
            and model.get_name("name") == "outer"
        )
        (local,) = package.bindings_for(outer, "Local")
        self.assertEqual(
            local.state, shikake.BindingState("stable", True, False, False)
        )

    def test_exception_handler_name_implies_deletion(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "try:\n    work()\nexcept Exception as Error:\n    handle(Error)\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["Error"],
            shikake.BindingState("unstable", False, True, True),
        )

    def test_exception_group_handler_name_implies_deletion(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "try:\n    work()\n"
                    "except* ValueError as Errors:\n    handle(Errors)\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["Errors"],
            shikake.BindingState("unstable", False, True, True),
        )

    def test_exception_deletion_respects_lexical_scope(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Error: pass\n"
                    "def handler():\n"
                    "    try:\n        work()\n"
                    "    except ValueError as Error:\n        pass\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["Error"],
            shikake.BindingState("stable", False, False, False),
        )
        function = next(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.function"
        )
        (binding,) = package.bindings_for(function, "Error")
        self.assertEqual(
            binding.state, shikake.BindingState("unstable", False, True, False)
        )

    def test_unnamed_handler_does_not_introduce_deletion(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Error: pass\n"
                    "try:\n    work()\n"
                    "except ValueError:\n    pass\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["Error"],
            shikake.BindingState("stable", False, False, False),
        )

    def test_exception_cleanup_follows_global_declaration(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class Error: pass\n"
                    "def handler():\n"
                    "    global Error\n"
                    "    try:\n        work()\n"
                    "    except ValueError as Error:\n        pass\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["Error"],
            shikake.BindingState("stable", True, True, False),
        )

    def test_global_write_is_attached_to_module_binding(self) -> None:
        package = self.parse(
            {
                "case.py": (
                    "class X: pass\ndef f():\n    global X\n    X = 3\n    del X\n"
                )
            }
        )
        self.assertEqual(
            self.module_facts(package, "sample.case")["X"],
            shikake.BindingState("stable", True, True, False),
        )


if __name__ == "__main__":
    unittest.main()
