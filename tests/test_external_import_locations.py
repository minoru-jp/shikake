"""External imports are facts, not an AST-level source acceptance policy."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as rules

import shikake


class ExternalImportLocationTests(unittest.TestCase):
    def test_conditional_and_nested_imports_are_accepted(self) -> None:
        imports = (
            "from framework.memory import Memory",
            "import framework.memory as mem",
        )
        contexts = (
            lambda line: f"if flag:\n    {line}\n",
            lambda line: f"try:\n    {line}\nexcept ImportError:\n    pass\n",
            lambda line: f"def f():\n    {line}\n",
            lambda line: f"class Holder:\n    {line}\n",
        )
        for imported in imports:
            for context in contexts:
                with self.subTest(imported=imported, context=context):
                    source = context(imported)
                    result = shikake.inspect_source(source, definitions=rules)
                    self.assertTrue(result.complete, result.issues)

    def test_module_level_explicit_imports_are_recognized(self) -> None:
        for source in (
            "from framework.memory import Memory\nx = Memory.new(1)",
            "import framework.memory\nx = framework.memory.Memory.new(1)",
            "import framework.memory as m\nx = m.Memory.new(1)",
        ):
            with self.subTest(source=source):
                result = shikake.parse_source(source, definitions=rules)
                self.assertIn("ext.memory.allocate", {m.kind.id for m in result.walk()})

    def test_star_import_kept_without_guessing_a_mapping(self) -> None:
        source = "from framework.memory import *\nx = Memory.new(1)"
        result = shikake.inspect_source(source, definitions=rules)
        self.assertTrue(result.complete, result.issues)
        assert result.model is not None
        self.assertIn("model.value.call", {m.kind.id for m in result.model.walk()})

    def test_package_keeps_non_top_level_import(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "example"
            root.mkdir()
            (root / "a.py").write_text(
                "if flag:\n    from framework.memory import Memory\n", encoding="utf-8"
            )
            (root / "b.py").write_text("class Good: pass\n", encoding="utf-8")
            result = shikake.inspect_package(root, definitions=rules)
        self.assertTrue(result.complete, result.issues)
        self.assertEqual(len(result.model.get_nodes("modules")), 2)
