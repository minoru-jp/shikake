"""Scalar payload types are part of structural Model identity."""

from __future__ import annotations

import unittest

from shikake import ModelPart, parse_source


class ScalarModelIdentityTests(unittest.TestCase):
    def test_equal_python_numbers_with_distinct_ast_types_are_not_equal(self) -> None:
        # Equal-length spellings keep SourceSpan equal, exposing the previous bug.
        for a, b in (
            ("True", "0x01"),
            ("0x1", "1.0"),
        ):
            with self.subTest(left=a, right=b):
                left = parse_source(f"x = {a}")
                right = parse_source(f"x = {b}")
                self.assertNotEqual(left, right)
                self.assertNotEqual(hash(left), hash(right))
                self.assertEqual(len({left, right}), 2)
                self.assertEqual(len({left: "left", right: "right"}), 2)

    def test_equal_models_keep_equal_hashes(self) -> None:
        for literal in (
            "True",
            "False",
            "1",
            "1.0",
            "1j",
            "'text'",
            "b'text'",
            "None",
            "...",
        ):
            with self.subTest(literal=literal):
                left = parse_source(f"x = {literal}")
                right = parse_source(f"x = {literal}")
                self.assertEqual(left, right)
                self.assertEqual(hash(left), hash(right))

    def test_model_part_scalar_values_follow_same_contract(self) -> None:
        for a, b in ((True, 1), (1, 1.0), (1.0, 1 + 0j)):
            with self.subTest(left=a, right=b):
                left = ModelPart("value", a)
                right = ModelPart("value", b)
                self.assertNotEqual(left, right)
                self.assertNotEqual(hash(left), hash(right))
        self.assertEqual(ModelPart("value", 1), ModelPart("value", 1))
        self.assertEqual(hash(ModelPart("value", 1)), hash(ModelPart("value", 1)))
        self.assertNotEqual(ModelPart("left", 1), ModelPart("right", 1))

    def test_model_part_with_model_children(self) -> None:
        left = ModelPart("nodes", (parse_source("x = True"),))
        right = ModelPart("nodes", (parse_source("x = 0x01"),))
        self.assertNotEqual(left, right)
        self.assertNotEqual(hash(left), hash(right))
        self.assertEqual(left, ModelPart("nodes", (parse_source("x = True"),)))


if __name__ == "__main__":
    unittest.main()
