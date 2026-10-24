"""Strict and inspection entry points share syntax and model preparation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake
from shikake.external import ExternalDefinitionsBuilder

_DEFINITIONS = (
    ExternalDefinitionsBuilder()
    .add_type("demo.kinds:Int32", "demo.type.int32")
    .add_generic("demo.kinds:Vector", "demo.type.vector", ("item", "size"))
    .add_call("demo.ops:clamp", "demo.ops.clamp", ("value", "lo", "hi"))
    .build()
)

_SOURCE = """
from demo.kinds import Int32, Vector
from demo.ops import clamp

class Accumulator:
    def convert(self, x: Vector[Int32, 4]) -> Int32:
        if x:
            try:
                return clamp(2, 0, 5)
            except ValueError:
                return 0
        elif x is None:
            return 1
        return 2
"""


class SharedModelingPipelineTests(unittest.TestCase):
    def test_source_strict_and_inspection_share_modeling_rules(self) -> None:
        strict = shikake.parse_source(_SOURCE, definitions=_DEFINITIONS)
        inspected = shikake.inspect_source(_SOURCE, definitions=_DEFINITIONS)
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertEqual(inspected.model, strict)
        self.assertEqual(inspected.issues, ())
        kinds = {item.kind.id for item in strict.walk()}
        self.assertIn("demo.type.int32", kinds)
        self.assertIn("demo.type.vector", kinds)
        self.assertIn("demo.ops.clamp", kinds)

    def test_package_strict_and_inspection_share_modeling_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample_package"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            (root / "operations.py").write_text(_SOURCE, encoding="utf-8")
            strict = shikake.parse_package(root, definitions=_DEFINITIONS)
            inspected = shikake.inspect_package(root, definitions=_DEFINITIONS)
            self.assertTrue(inspected.complete, inspected.issues)
            self.assertEqual(inspected.model, strict.model)
            self.assertEqual(inspected.issues, ())

    def test_compile_validation_precedes_optional_import_policy(self) -> None:
        policy = shikake.ImportPolicy(default="deny")
        source = "import os\nreturn 5\n"
        with self.assertRaises(SyntaxError):
            shikake.parse_source(source, import_policy=policy)
        result = shikake.inspect_source(source, import_policy=policy)
        self.assertFalse(result.complete)
        self.assertEqual([issue.category for issue in result.issues], ["syntax_error"])

        # Opting out of compile validation must still apply the import policy.
        with self.assertRaises(shikake.ImportPolicyError):
            shikake.parse_source(source, import_policy=policy, syntax_validation="ast")
        result = shikake.inspect_source(
            source, import_policy=policy, syntax_validation="ast"
        )
        self.assertEqual([issue.category for issue in result.issues], ["import_policy"])


if __name__ == "__main__":
    unittest.main()
