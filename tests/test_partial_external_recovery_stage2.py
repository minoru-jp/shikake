"""Inspection preserves mismatched and unregistered external uses."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as rules

import shikake


class ExternalInspectionTests(unittest.TestCase):
    def test_invalid_interface_uses_are_not_partial_issues(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "a = Memory.nope(1)\nb = Memory.new()\n"
            "c = Memory.new\nd = Memory.new(4)\n"
        )
        inspected = shikake.inspect_source(source, definitions=rules)
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertEqual(
            shikake.parse_source(source, definitions=rules), inspected.model
        )
        assert inspected.model is not None
        self.assertEqual(len(inspected.model.get_nodes("body")), 5)
        kinds = [m.kind.id for m in inspected.model.walk()]
        self.assertEqual(kinds.count("ext.memory.allocate"), 1)
        self.assertEqual(kinds.count("model.value.call"), 2)

    def test_nested_bad_call_preserves_its_statement(self) -> None:
        source = (
            "from framework.memory import Memory\n"
            "if ready:\n    good = 1\n    bad = Memory.unknown(1)\n    after = 2\n"
        )
        inspected = shikake.inspect_source(source, definitions=rules)
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertIn("model.value.call", {m.kind.id for m in inspected.model.walk()})  # type: ignore[union-attr]

    def test_package_relations_remain_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pkg"
            root.mkdir()
            (root / "a.py").write_text(
                "from framework.memory import Memory\n"
                "class Base: pass\nx = Memory.nope(1)\nclass Child(Base): pass\n"
            )
            (root / "b.py").write_text("value = 1\n")
            inspected = shikake.inspect_package(
                root, definitions=rules, analyses={"inheritance"}
            )
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertTrue(inspected.name_bindings)
        self.assertTrue(inspected.analyses)

    def test_no_definitions_preserves_call(self) -> None:
        result = shikake.inspect_source("x = Unknown.method(1)")
        self.assertTrue(result.complete)
        self.assertEqual(result.model, shikake.parse_source("x = Unknown.method(1)"))
