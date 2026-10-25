"""External calls are an optional transformation, not a source allowlist."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import external_colliding_definitions as collisions
import external_memory_definitions as rules

import shikake
from shikake.external import ExternalDefinitionsBuilder, load_external_definitions


class ExternalModelingTests(unittest.TestCase):
    @staticmethod
    def kinds(source: str) -> list[str]:
        root = shikake.parse_source(source, definitions=rules)
        inspected = shikake.inspect_source(source, definitions=rules)
        assert inspected.complete, inspected.issues
        assert inspected.model == root
        return [node.kind.id for node in root.walk()]

    def test_import_spelling_and_argument_binding(self) -> None:
        for imported, call in (
            ("from framework.memory import Memory as M", "M.new(8)"),
            ("from framework.memory import Memory", "Memory.new(size=8)"),
            ("import framework.memory as mem", "mem.Memory.new(8)"),
            ("import framework.memory", "framework.memory.Memory.new(8)"),
            ("from framework import memory", "memory.Memory.new(8)"),
        ):
            with self.subTest(imported=imported):
                source = f"{imported}\nx = {call}\n"
                self.assertIn("ext.memory.allocate", self.kinds(source))

    def test_matching_requires_explicit_written_import_path(self) -> None:
        for source in (
            "x = Memory.new(1)",
            "import framework\nx = framework.memory.Memory.new(1)",
            "from unrelated import Memory\nx = Memory.new(1)",
        ):
            with self.subTest(source=source):
                kinds = self.kinds(source)
                self.assertIn("model.value.call", kinds)
                self.assertNotIn("ext.memory.allocate", kinds)

    def test_unregistered_calls_remain_generic(self) -> None:
        for call in (
            "Memory()",
            "Memory.unknown(1)",
            "Memory.new.child(1)",
            "Memory.__getattribute__('new')",
            "Memory.new(1, 2)",
            "Memory.new()",
            "Memory.new(other=2)",
            "Memory.new(*xs)",
            "Memory.new(**xs)",
            "Memory.new(1, size=2)",
        ):
            with self.subTest(call=call):
                kinds = self.kinds(f"from framework.memory import Memory\nx = {call}\n")
                self.assertIn("model.value.call", kinds)
                self.assertNotIn("ext.memory.allocate", kinds)

    def test_values_annotations_and_mutations_are_not_rejected(self) -> None:
        for statement in (
            "alias = Memory",
            "alias = Memory.new",
            "items = [Memory.new]",
            "consume(Memory)",
            "def f(v: Memory): pass",
            "x: Memory = 1",
            "x = Memory.new[0]",
            "Memory.new = func",
            "del Memory.new",
            "Memory = 1",
            "for Memory in xs: pass",
            "def f(Memory): return Memory",
            "from other import Memory",
        ):
            with self.subTest(statement=statement):
                self.kinds(f"from framework.memory import Memory\n{statement}\n")

    def test_external_namespace_and_star_are_not_protected(self) -> None:
        for source in (
            "import framework.memory as m\nx = m\n",
            "import framework.memory as m\nx = m()\n",
            "from framework.memory import *\nx = unknown\n",
            "from framework.memory import Memory\nfrom math import *\n",
        ):
            with self.subTest(source=source):
                self.kinds(source)

    def test_repeated_import_is_written_fact_not_an_error(self) -> None:
        source = "from framework.memory import Memory\nfrom framework.memory import Memory\nx = Memory.new(1)\n"
        kinds = self.kinds(source)
        self.assertIn("ext.memory.allocate", kinds)
        inspected = shikake.inspect_source(source, definitions=rules)
        assert inspected.model is not None
        (binding,) = inspected.bindings_for(inspected.model, "Memory")
        self.assertTrue(binding.state.may_rebind)

    def test_colliding_relevant_imports_degrade_to_generic(self) -> None:
        source = "from framework.memory import Memory as M\nfrom unrelated import M\nx = M.new(1)\n"
        # The unrelated import's conflicting binding is checked by the
        # consumer; shikake still keeps the written Call and all statements.
        self.assertIn("model.value.call", self.kinds(source))

    def test_nested_registered_calls(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "a = Memory.new(1)\n"
            "b = Memory.new(Memory.add(2))\n"
            "def f(): return Memory.new(3)\n"
        )
        kinds = self.kinds(source)
        self.assertEqual(kinds.count("ext.memory.allocate"), 3)
        self.assertEqual(kinds.count("ext.memory.release"), 1)

    def test_direct_imported_call(self) -> None:
        definitions = (
            ExternalDefinitionsBuilder()
            .add_call("pyinto.kinds:int32", "test.int32", ("value",))
            .build()
        )
        for imported, call in (
            ("from pyinto.kinds import int32", "int32(10)"),
            ("from pyinto.kinds import int32 as i32", "i32(10)"),
            ("import pyinto.kinds as kinds", "kinds.int32(10)"),
            ("import pyinto.kinds", "pyinto.kinds.int32(10)"),
        ):
            with self.subTest(imported=imported):
                result = shikake.parse_source(
                    f"{imported}\nx = {call}\n", definitions=definitions
                )
                self.assertIn("test.int32", {m.kind.id for m in result.walk()})
        result = shikake.parse_source(
            "from pyinto.kinds import int32\na: int32 = 10\nb = int32\nc = int32(1, 2)",
            definitions=definitions,
        )
        self.assertNotIn("test.int32", {m.kind.id for m in result.walk()})
        self.assertIn("model.value.call", {m.kind.id for m in result.walk()})

    def test_unrelated_imports_and_differing_paths(self) -> None:
        source = "import framework\nvalue = framework.memory.Memory.new(1)\n"
        self.assertNotIn("ext.memory.allocate", self.kinds(source))

    def test_validation_and_prepared_definitions(self) -> None:
        definition = load_external_definitions(rules)
        self.assertEqual(len(definition.mappings), 2)
        self.assertIn(
            "ext.memory.release",
            {
                m.kind.id
                for m in shikake.parse_source(
                    "from framework.memory import Memory\nx = Memory.add(1)",
                    definitions=definition,
                ).walk()
            },
        )
        with self.assertRaisesRegex(ValueError, "duplicate external target"):
            load_external_definitions(collisions)
        with self.assertRaises(ValueError):
            shikake.parse_source(
                "pass", index=shikake.definition_index(), definitions=definition
            )
        empty = ModuleType("empty_external_description")
        with self.assertRaises(ValueError):
            load_external_definitions(empty)

    def test_package_keeps_modified_external_names(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.py").write_text(
                "from framework.memory import Memory\nMemory = 1\n"
            )
            (root / "b.py").write_text(
                "from framework.memory import Memory\nx = Memory.new(1)\n"
            )
            parsed = shikake.parse_package(root, definitions=rules)
            inspected = shikake.inspect_package(root, definitions=rules)
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertEqual(parsed.model, inspected.model)
        self.assertEqual(len(inspected.model.get_nodes("modules")), 2)

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_type_parameters_can_shadow_imports(self) -> None:
        for declaration in (
            "def f[Memory](x: Memory): return Memory.new(1)",
            "class Box[Memory]: pass",
            "type Alias[*Memory] = tuple[*Memory]",
        ):
            with self.subTest(declaration=declaration):
                self.kinds("from framework.memory import Memory\n" + declaration + "\n")


if __name__ == "__main__":
    unittest.main()
