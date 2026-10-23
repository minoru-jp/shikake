"""End-to-end contracts for trusted, separate Shikumi call descriptions."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import external_colliding_definitions as collisions
import external_memory_definitions as rules

import shikake
from shikake.external import load_external_definitions


class ExternalModelingTests(unittest.TestCase):
    def test_import_alias_and_arguments(self) -> None:
        source = (
            "from framework.memory import Memory as M\n"
            "ptr = M.new(1024)\n"
            "M.add(target=ptr)\n"
        )
        model = shikake.parse_source(source, definitions=rules)
        foreign = tuple(m for m in model.walk() if m.kind.id.startswith("ext."))
        self.assertEqual(
            [m.kind.id for m in foreign], ["ext.memory.allocate", "ext.memory.release"]
        )
        self.assertEqual(foreign[0].get_node("size").get("value"), 1024)
        self.assertEqual(foreign[1].get_node("target").get_name("name"), "ptr")
        self.assertEqual(foreign[0].span.line if foreign[0].span else None, 2)

    def test_keyword_and_explicit_import_module_alias(self) -> None:
        for imported, call in (
            ("from framework.memory import Memory", "Memory.new(size=8)"),
            ("import framework.memory as mem", "mem.Memory.new(8)"),
            ("import framework.memory", "framework.memory.Memory.new(8)"),
        ):
            with self.subTest(imported=imported):
                model = shikake.parse_source(
                    f"{imported}\nx = {call}\n", definitions=rules
                )
                (found,) = [
                    m for m in model.walk() if m.kind.id == "ext.memory.allocate"
                ]
                self.assertEqual(found.get_node("size").get("value"), 8)

    def test_unimported_spelling_is_generic(self) -> None:
        model = shikake.parse_source("x = Memory.new(1)\n", definitions=rules)
        self.assertNotIn("ext.memory.allocate", {m.kind.id for m in model.walk()})
        self.assertIn("model.value.call", {m.kind.id for m in model.walk()})

    def test_no_definitions_preserves_generic_call(self) -> None:
        source = "from framework.memory import Memory\nMemory.new(1)\n"
        model = shikake.parse_source(source)
        self.assertIn("model.value.call", {m.kind.id for m in model.walk()})

    def test_rebinding_is_fatal_and_inspection_is_diagnostic(self) -> None:
        variations = (
            "Memory = other",
            "class Memory: pass",
            "def function(Memory): pass",
            "def Memory(): pass",
            "Memory.new = other",
            "del Memory.add",
            "for Memory in xs: pass",
            "with cm() as Memory: pass",
            "from other import Memory",
            "from other import *",
            "def f():\n    Memory = 1",
        )
        for mutation in variations:
            with self.subTest(mutation=mutation):
                source = (
                    f"from framework.memory import Memory\n{mutation}\nMemory.new(1)\n"
                )
                with self.assertRaises(shikake.ExternalModelingError):
                    shikake.parse_source(source, definitions=rules)
                inspected = shikake.inspect_source(source, definitions=rules)
                self.assertIsNone(inspected.model)
                self.assertEqual(inspected.issues[0].category, "external_definition")

    def test_repeated_explicit_import_is_rebinding(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "from framework.memory import Memory\n"
            "Memory.new(10)\n"
        )
        with self.assertRaises(shikake.ExternalModelingError):
            shikake.parse_source(source, definitions=rules)

    def test_incomplete_or_ambiguous_call_rejected(self) -> None:
        for call in (
            "Memory.new()",
            "Memory.new(1, 2)",
            "Memory.new(size=1, other=2)",
            "Memory.new(1, size=2)",
            "Memory.new(*args)",
            "Memory.new(**kwargs)",
        ):
            with (
                self.subTest(call=call),
                self.assertRaises(shikake.ExternalModelingError),
            ):
                shikake.parse_source(
                    f"from framework.memory import Memory\n{call}\n",
                    definitions=rules,
                )

    def test_external_structure_only_direct_calls_are_values(self) -> None:
        # Any directly written value-use of a protected structural chain must
        # fail, irrespective of whether the source branch will be executed.
        invalid = (
            "alias = Memory",
            "alias = Memory.new",
            "alias = Memory.new.child",
            "items = [Memory.new]",
            "consume(Memory)",
            "consume(Memory.new)",
            "def f():\n    return Memory.new",
            "if Memory.new:\n    pass",
            "if False:\n    alias = Memory",
            "alias = (Memory.new,)",
            "value = Memory.new[0]",
            "value = Memory.new.child[0]()",
            "x = Memory.new(Memory.add)",
            "@Memory.new\ndef f(): pass",
            "def f(x: Memory): pass",
            "match x:\n    case Memory.new():\n        pass",
        )
        for statement in invalid:
            with self.subTest(statement=statement):
                source = f"from framework.memory import Memory\n{statement}\n"
                with self.assertRaisesRegex(
                    shikake.ExternalModelingError, "structure used as a value"
                ):
                    shikake.parse_source(source, definitions=rules)
                inspected = shikake.inspect_source(source, definitions=rules)
                self.assertFalse(inspected.complete)
                self.assertEqual(inspected.issues[0].category, "external_definition")

    def test_nested_structure_call_and_normal_results(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "obj = Memory.new(1)\n"
            "value = Memory.new(2)[0]\n"
            "nested = Memory.new(Memory.add(3))\n"
            "consume(Memory.new(4))\n"
            "def f():\n    return Memory.new(5)\n"
        )
        model = shikake.parse_source(source, definitions=rules)
        self.assertEqual(
            sum(node.kind.id == "ext.memory.allocate" for node in model.walk()), 5
        )
        self.assertTrue(shikake.inspect_source(source, definitions=rules).complete)

    def test_unregistered_structure_calls_are_rejected(self) -> None:
        # Registered call paths are the entire allowlist. Other structural
        # chains must not fall back to the generic Call Model.
        for imported, call in (
            ("from framework.memory import Memory", "Memory()"),
            ("from framework.memory import Memory", "Memory.other(1)"),
            ("from framework.memory import Memory", "Memory.extra.deep(1)"),
            ("from framework.memory import Memory", "Memory.new.child(1)"),
            (
                "from framework.memory import Memory",
                'Memory.__getattribute__("new")',
            ),
            (
                "from framework.memory import Memory",
                'Memory.__dict__.get("new")',
            ),
            ("import framework.memory as mem", "mem.Memory.other(1)"),
            ("import framework.memory", "framework.memory.Memory.other(1)"),
            ("from framework.memory import Memory as M", "M.extra.deep(1)"),
        ):
            source = f"{imported}\nobj = {call}\n"
            with self.subTest(source=source):
                with self.assertRaisesRegex(
                    shikake.ExternalModelingError,
                    "unregistered external structure call",
                ):
                    shikake.parse_source(source, definitions=rules)
                inspected = shikake.inspect_source(source, definitions=rules)
                self.assertFalse(inspected.complete)
                self.assertEqual(inspected.issues[0].category, "external_definition")

    def test_import_paths_and_unrelated_names_are_distinct(self) -> None:
        for imported, allowed, rejected in (
            (
                "from framework.memory import Memory as M",
                "M.new(1)",
                "alias = M.extra.deep",
            ),
            (
                "import framework.memory as mem",
                "mem.Memory.new(1)",
                "alias = mem.Memory.extra.deep",
            ),
            (
                "import framework.memory",
                "framework.memory.Memory.new(1)",
                "alias = framework.memory.Memory.extra.deep",
            ),
        ):
            with self.subTest(imported=imported):
                shikake.parse_source(f"{imported}\n{allowed}\n", definitions=rules)
                with self.assertRaises(shikake.ExternalModelingError):
                    shikake.parse_source(f"{imported}\n{rejected}\n", definitions=rules)
        # A same-spelled reference lacking the registered import is ordinary
        # Python syntax; a different path in the imported module is not a
        # declared structural descendant.
        shikake.parse_source("x = Memory.new\n", definitions=rules)
        shikake.parse_source(
            "import framework.memory as mem\nx = mem.unrelated\n",
            definitions=rules,
        )

    def test_namespaces_are_not_structural_call_targets(self) -> None:
        for imported, call in (
            ("import framework.memory as mem", "mem()"),
            ("import framework.memory", "framework.memory()"),
        ):
            with (
                self.subTest(imported=imported),
                self.assertRaises(shikake.ExternalModelingError),
            ):
                shikake.parse_source(f"{imported}\n{call}\n", definitions=rules)

    def test_imported_namespace_cannot_be_passed_as_an_alias(self) -> None:
        for imported, alias in (
            ("import framework.memory as mem", "mem"),
            ("import framework.memory", "framework.memory"),
        ):
            with (
                self.subTest(imported=imported),
                self.assertRaises(shikake.ExternalModelingError),
            ):
                shikake.parse_source(
                    f"{imported}\nother = {alias}\n", definitions=rules
                )

    def test_structural_attribute_and_subscript_mutations(self) -> None:
        for imported, prefix in (
            ("from framework.memory import Memory", "Memory"),
            ("import framework.memory as mem", "mem.Memory"),
        ):
            for statement in (
                f"{prefix}.new = other",
                f"del {prefix}.extra.deep",
                f"{prefix}.new[0] = other",
                f"{prefix}.new += 1",
                f"for {prefix}.new in targets: pass",
                f"with cm() as {prefix}.new: pass",
            ):
                with (
                    self.subTest(imported=imported, statement=statement),
                    self.assertRaises(shikake.ExternalModelingError),
                ):
                    shikake.parse_source(
                        f"{imported}\n{statement}\n", definitions=rules
                    )

    def test_external_declarations_only_export_call_matching(self) -> None:
        from shikake import external

        for name in ("ImportedAttribute", "ImportedSubscript", "SubscriptItem"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(external, name))
        prepared = load_external_definitions(rules)
        self.assertEqual(len(prepared.mappings), 2)
        self.assertTrue(
            all(
                isinstance(item.target, external.ImportedCall)
                for item in prepared.mappings
            )
        )

    def test_validated_index_is_reusable(self) -> None:
        prepared = load_external_definitions(rules)
        model = shikake.parse_source(
            "from framework.memory import Memory\nMemory.add(1)", definitions=prepared
        )
        self.assertIn("ext.memory.release", {m.kind.id for m in model.walk()})
        self.assertEqual(len(prepared.mappings), 2)
        self.assertIsNotNone(prepared.index.get("ext.memory.release"))
        with self.assertRaises(ValueError):
            shikake.parse_source(
                "pass", index=shikake.kind_index(), definitions=prepared
            )

    def test_colliding_canonical_call_targets_are_rejected(self) -> None:
        # Module/attribute boundaries differ, but the matching lookup key is
        # identical. Neither definition may silently overwrite the other.
        with self.assertRaisesRegex(ValueError, "duplicate external target"):
            load_external_definitions(collisions)

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_type_parameters_cannot_shadow_reserved_imports(self) -> None:
        for declaration in (
            "def f[Memory](x: Memory): return Memory.new(1)",
            "class Box[*Memory]:\n    def f(self): return Memory.new(1)",
            "type Alias[**Memory] = list[Memory]",
            "class Box[Memory]: pass",
            "def f[**Memory](): pass",
            "type Alias[*Memory] = tuple[*Memory]",
        ):
            with self.subTest(declaration=declaration):
                source = "from framework.memory import Memory\n" + declaration + "\n"
                with self.assertRaisesRegex(
                    shikake.ExternalModelingError, "reserved external name"
                ):
                    shikake.parse_source(source, definitions=rules)
                inspection = shikake.inspect_source(source, definitions=rules)
                self.assertFalse(inspection.complete)
                self.assertEqual(inspection.issues[0].category, "external_definition")

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_unrelated_type_parameters_preserve_external_call(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "def f[T](x: T): return Memory.new(1)\n"
        )
        model = shikake.parse_source(source, definitions=rules)
        self.assertEqual(
            sum(m.kind.id == "ext.memory.allocate" for m in model.walk()), 1
        )

    def test_mapping_validation_requires_kind_and_roles(self) -> None:
        module = ModuleType("test_bad_external_description")
        module.__dict__["__path__"] = []
        # Shikumi's declaration discovery is exercised on real classes in rules;
        # a root without declarations must fail instead of accepting an empty spec.
        with self.assertRaises(ValueError):
            load_external_definitions(module)

    def test_package_and_inspection_use_same_rules(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.py").write_text(
                "from framework.memory import Memory\nresult = Memory.new(64)\n",
                encoding="utf-8",
            )
            (root / "b.py").write_text("print(1)\n", encoding="utf-8")
            model = shikake.parse_package(root, definitions=rules)
            self.assertIn("ext.memory.allocate", {m.kind.id for m in model.walk()})
            inspected = shikake.inspect_package(root, definitions=rules)
            self.assertTrue(inspected.complete)
            self.assertEqual(inspected.model, model.model)

    def test_package_violation_is_reported_without_hiding_other_modules(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bad.py").write_text(
                "from framework.memory import Memory\nMemory = 1\n", encoding="utf-8"
            )
            (root / "good.py").write_text("x = 1\n", encoding="utf-8")
            with self.assertRaises(shikake.ExternalModelingError):
                shikake.parse_package(root, definitions=rules)
            inspected = shikake.inspect_package(root, definitions=rules)
            self.assertFalse(inspected.complete)
            self.assertEqual(inspected.issues[0].category, "external_definition")
            self.assertEqual(len(inspected.model.get_nodes("modules")), 1)


if __name__ == "__main__":
    unittest.main()
