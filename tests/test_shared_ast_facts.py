"""The AST index is consumed by both external validation and relation output."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as definitions

import shikake
from shikake._mica.ast_facts import collect_syntax_facts


class SharedASTFactsTests(unittest.TestCase):
    def test_one_syntax_index_records_import_writes_and_references(self) -> None:
        tree = ast.parse(
            "from framework.memory import Memory\n"
            "if flag:\n    Memory = other\n"
            "result = Memory.new(1)\n"
        )
        facts = collect_syntax_facts(tree)
        self.assertEqual(
            [(item.name, item.kind) for item in facts.events],
            [("Memory", "import"), ("Memory", "write"), ("result", "write")],
        )
        self.assertTrue(
            any(isinstance(node, ast.Attribute) for node, _ in facts.references)
        )

    def test_conditional_external_import_is_rejected(self) -> None:
        source = (
            "if flag:\n    from framework.memory import Memory\nx = Memory.new(1)\n"
        )
        with self.assertRaises(shikake.ExternalModelingError):
            shikake.parse_source(source, definitions=definitions)

    def test_elif_named_expression_is_tracked_as_written_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "sample"
            folder.mkdir()
            (folder / "case.py").write_text(
                "class Base: pass\n"
                "if a: pass\n"
                "elif (Base := other): pass\n"
                "class Child(Base): pass\n"
            )
            package = shikake.parse_package(folder, analyses={"inheritance"})
        module = next(n for n in package.walk() if n.kind.id == "model.module")
        binding = package.bindings_for(module, "Base")[0]
        self.assertTrue(binding.state.may_rebind)
        reference = package.base_references[-1]
        self.assertTrue(reference.binding.may_rebind)  # type: ignore[union-attr]

    def test_scope_changes_are_module_local_and_external_use_is_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "sample"
            folder.mkdir()
            (folder / "first.py").write_text("class Base: pass\nBase = Other\n")
            (folder / "second.py").write_text(
                "from .first import Base\nclass D(Base): pass\n"
            )
            result = shikake.parse_package(folder, analyses={"inheritance"})
        second = next(
            node
            for node in result.walk()
            if node.kind.id == "model.module"
            and node.get_name("name") == "sample.second"
        )
        self.assertFalse(result.bindings_for(second, "Base")[0].state.may_rebind)
        with self.assertRaises(shikake.ExternalModelingError):
            shikake.parse_source(
                "from framework.memory import Memory\nconsume(Memory.new)\n",
                definitions=definitions,
            )


if __name__ == "__main__":
    unittest.main()
