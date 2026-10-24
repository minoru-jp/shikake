"""Regression tests for atomic external recognition and lexical shadowing."""

from __future__ import annotations

import unittest

import shikake
from shikake.external import ExternalDefinitionsBuilder


class ExternalRecognitionRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.definitions = (
            ExternalDefinitionsBuilder()
            .add_call("demo.ops:clamp", "demo.call", ("value", "lower", "upper"))
            .add_type("demo.ops:clamp", "demo.type")
            .add_generic("demo.ops:Vector", "demo.generic", ("item", "length"))
            .build()
        )

    def kinds(self, source: str) -> list[str]:
        model = shikake.parse_source(source, definitions=self.definitions)
        inspected = shikake.inspect_source(source, definitions=self.definitions)
        self.assertTrue(inspected.complete, inspected.issues)
        self.assertEqual(model, inspected.model)
        return [node.kind.id for node in model.walk()]

    def test_missing_late_argument_falls_back_without_consuming_children(self) -> None:
        for call in ("clamp(1, 2)", "clamp(1, lower=2)", "clamp(value=1, lower=2)"):
            with self.subTest(call=call):
                ids = self.kinds(f"from demo.ops import clamp\nx = {call}\n")
                self.assertNotIn("demo.call", ids)
                self.assertIn("model.value.call", ids)
                self.assertEqual(ids.count("model.value.literal"), 2)

    def test_valid_external_call_still_specializes(self) -> None:
        ids = self.kinds("from demo.ops import clamp\nx = clamp(1, 2, 3)\n")
        self.assertIn("demo.call", ids)
        self.assertNotIn("model.value.call", ids)

    def test_shadowed_direct_call_keeps_ordinary_call(self) -> None:
        samples = (
            "def f(clamp):\n    return clamp(1, 2, 3)",
            "def f():\n    clamp = other\n    return clamp(1, 2, 3)",
            "def f():\n    return clamp(1, 2, 3)\n    clamp = other",
            "x = lambda clamp: clamp(1, 2, 3)",
            "x = [clamp(1, 2, 3) for clamp in funcs]",
            "clamp = other\nx = clamp(1, 2, 3)",
        )
        for body in samples:
            with self.subTest(body=body):
                ids = self.kinds("from demo.ops import clamp\n" + body + "\n")
                self.assertNotIn("demo.call", ids)
                self.assertIn("model.value.call", ids)

    def test_shadowed_type_and_generic_keep_ordinary_models(self) -> None:
        samples = (
            (
                "from demo.ops import clamp\ndef f(clamp):\n    x: clamp = 1",
                "demo.type",
            ),
            (
                "from demo.ops import Vector\ndef f(Vector):\n    x: Vector[int, 4]",
                "demo.generic",
            ),
            (
                "from demo.ops import Vector\ndef f():\n    Vector = other\n    x: Vector[int, 4]",
                "demo.generic",
            ),
        )
        for source, specialized in samples:
            with self.subTest(source=source):
                ids = self.kinds(source + "\n")
                self.assertNotIn(specialized, ids)

    def test_unshadowed_nested_interfaces_still_specialize(self) -> None:
        source = (
            "from demo.ops import clamp, Vector\n"
            "def f():\n"
            "    x: Vector[clamp, 4]\n"
            "    return clamp(1, 2, 3)\n"
        )
        ids = self.kinds(source)
        for kind in ("demo.generic", "demo.type", "demo.call"):
            self.assertIn(kind, ids)

    def test_star_import_does_not_shadow_explicit_import(self) -> None:
        ids = self.kinds(
            "from demo.ops import clamp\nfrom other import *\nx = clamp(1, 2, 3)\n"
        )
        self.assertIn("demo.call", ids)


if __name__ == "__main__":
    unittest.main()
