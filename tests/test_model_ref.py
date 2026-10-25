"""ModelRef is an opt-in identity key with a Path-based source label."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from shikake import Model, ModelRef, parse_source


class ModelRefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = parse_source("value = 1\n")

    def test_public_reference_and_explicit_model_access(self) -> None:
        ref = ModelRef(self.model, "source.py")
        self.assertIs(ref.model, self.model)
        self.assertEqual(ref.source_path, Path("source.py"))
        self.assertIsNot(ref, self.model)
        self.assertNotIsInstance(ref, Model)
        self.assertEqual(ref.model.kind.id, "model.module")
        with self.assertRaises(AttributeError):
            _ = ref.kind  # type: ignore[attr-defined]

    def test_equal_when_model_identity_and_path_match(self) -> None:
        left = ModelRef(self.model, "src/example.py")
        right = ModelRef(self.model, Path("src") / "example.py")
        self.assertIsNot(left, right)
        self.assertEqual(left, right)
        self.assertEqual(hash(left), hash(right))
        self.assertEqual({left: "first"}[right], "first")
        self.assertEqual(len({left, right}), 1)

    def test_same_model_different_source_paths_are_unequal(self) -> None:
        first = ModelRef(self.model, "a.py")
        second = ModelRef(self.model, "b.py")
        self.assertNotEqual(first, second)
        self.assertEqual(len({first, second}), 2)

    def test_distinct_structurally_equal_models_are_unequal(self) -> None:
        another = parse_source("value = 1\n")
        self.assertIsNot(self.model, another)
        self.assertEqual(self.model, another)
        first = ModelRef(self.model, "same.py")
        second = ModelRef(another, "same.py")
        self.assertNotEqual(first, second)
        self.assertEqual(len({first, second}), 2)

    def test_path_comparison_uses_pathlib_not_filesystem(self) -> None:
        self.assertEqual(
            ModelRef(self.model, "./src/example.py"),
            ModelRef(self.model, Path("src/example.py")),
        )
        # Path does not collapse a '..' segment or resolve symlinks.
        self.assertNotEqual(
            ModelRef(self.model, "src/../src/example.py"),
            ModelRef(self.model, "src/example.py"),
        )
        self.assertEqual(
            ModelRef(self.model, "<virtual>").source_path,
            Path("<virtual>"),
        )

    def test_ref_equality_and_hash_skip_model_structural_methods(self) -> None:
        left = ModelRef(self.model, "test.py")
        right = ModelRef(self.model, "test.py")
        with (
            patch.object(Model, "__eq__", side_effect=AssertionError),
            patch.object(Model, "__hash__", side_effect=AssertionError),
        ):
            self.assertTrue(left == right)
            self.assertEqual(hash(left), hash(right))

    def test_immutable_and_slotted(self) -> None:
        ref = ModelRef(self.model, "x.py")
        with self.assertRaises(FrozenInstanceError):
            ref.source_path = Path("y.py")  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            ref.model = parse_source("x = 2")  # type: ignore[misc]
        self.assertFalse(hasattr(ref, "__dict__"))

    def test_unrelated_objects_are_not_equal(self) -> None:
        ref = ModelRef(self.model, "x.py")
        self.assertNotEqual(ref, self.model)
        self.assertNotEqual(ref, object())


if __name__ == "__main__":
    unittest.main()
