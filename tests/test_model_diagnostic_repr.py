"""Repr must remain useful for debugging deeply nested or wide Model trees."""

from __future__ import annotations

import unittest

from shikake import ModelPart, parse_source


class ModelDiagnosticReprTests(unittest.TestCase):
    def test_small_model_exposes_basic_context(self) -> None:
        root = parse_source("result = 1 + 2\n")
        text = repr(root)
        self.assertIn("Model(kind=", text)
        self.assertIn("span=", text)
        self.assertIn("features=", text)
        self.assertIn("parts=", text)
        self.assertIn("model.", text)
        self.assertLessEqual(len(text), 512)
        self.assertNotIn("ModelPart(", text)

    def test_async_feature_and_source_position_appear(self) -> None:
        root = parse_source("async def compute():\n    return 1\n")
        function = next(model for model in root.walk() if model.features)
        text = repr(function)
        self.assertIn("'async'", text)
        self.assertIn("span=1:0-", text)
        self.assertIn("'name': 'compute'", text)
        self.assertLessEqual(len(text), 512)

    def test_deep_addition_is_not_recursive(self) -> None:
        root = parse_source("result = " + " + ".join(["x"] * 248))
        for model in root.walk():
            text = repr(model)
            self.assertLessEqual(len(text), 512)
            self.assertIn("kind=", text)
        self.assertIn("Model(", repr(root))

    def test_nested_if_is_not_recursive(self) -> None:
        source = "\n".join("    " * level + "if x:" for level in range(90))
        source += "\n" + "    " * 90 + "pass\n"
        root = parse_source(source)
        self.assertLessEqual(len(repr(root)), 512)
        self.assertTrue(all(len(repr(m)) <= 512 for m in root.walk()))

    def test_wide_model_and_model_part_are_bounded(self) -> None:
        source = "items = [" + ",".join(["1234567890"] * 1300) + "]"
        root = parse_source(source)
        text = repr(root)
        self.assertLessEqual(len(text), 512)
        sequence = next(
            m for m in root.walk() if m.kind.id == "model.value.collection.list"
        )
        self.assertIn("1300 items", repr(sequence))
        self.assertLessEqual(len(repr(sequence)), 512)
        for part in sequence.parts():
            self.assertLessEqual(len(repr(part)), 256)
            self.assertNotIn("Model(kind=", repr(part))

    def test_long_scalar_and_role_are_bounded(self) -> None:
        part = ModelPart("r" * 1000, "A\n" * 200_000)
        text = repr(part)
        self.assertLessEqual(len(text), 256)
        self.assertIn("len=", text)
        root = parse_source("value = " + repr("x" * 5000))
        scalar = next(
            m
            for m in root.walk()
            if any(p.role == "value" and isinstance(p.value, str) for p in m.parts())
        )
        self.assertLessEqual(len(repr(scalar)), 512)
        self.assertIn("len=", repr(scalar))

    def test_repr_is_a_summary_not_a_unique_identifier(self) -> None:
        left = parse_source("x = 1")
        right = parse_source("x = 2")
        self.assertNotEqual(left, right)
        # Root parts are counts, not a recursive rendering of scalar leaves.
        self.assertEqual(repr(left), repr(right))

    def test_model_part_with_nested_child_never_recurses(self) -> None:
        root = parse_source("result = " + " + ".join(["x"] * 248))
        part = ModelPart("child", root)
        text = repr(part)
        self.assertIn("Model", text)
        self.assertLessEqual(len(text), 256)

    def test_other_structural_operations_are_unchanged(self) -> None:
        left = parse_source("x = 1")
        right = parse_source("x = 1")
        self.assertEqual(left, right)
        self.assertEqual(hash(left), hash(right))
        self.assertGreater(len(list(left.walk())), 1)


if __name__ == "__main__":
    unittest.main()
