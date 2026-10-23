"""Structural hash caching, including descendants and slot initialization."""

from __future__ import annotations

import copy
import dataclasses
import pickle
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from shikake import Model, ModelPart, parse_source
from shikake._mica import model as model_module


class ModelHashCacheTests(unittest.TestCase):
    @staticmethod
    def _chain(depth: int) -> tuple[Model, Model]:
        kind = parse_source("value = 1").kind
        leaf = Model(kind, (ModelPart("scalar", 1),))
        current = leaf
        for _ in range(depth):
            current = Model(kind, (ModelPart("child", current),))
        return current, leaf

    def test_first_hash_caches_root_and_descendants(self) -> None:
        root, leaf = self._chain(80)
        self.assertIsNone(model_module._get_cached_hash(root))
        self.assertIsNone(model_module._get_cached_hash(leaf))
        result = hash(root)
        self.assertEqual(model_module._get_cached_hash(root), result)
        self.assertEqual(model_module._get_cached_hash(leaf), hash(leaf))
        with patch.object(
            model_module,
            "_compute_model_hash",
            side_effect=AssertionError("recomputed"),
        ):
            self.assertEqual(hash(root), result)

    def test_hash_of_parent_reuses_existing_child_cache(self) -> None:
        kind = parse_source("value = 1").kind
        child = Model(kind, (ModelPart("scalar", 123),))
        hash(child)
        parent = Model(kind, (ModelPart("child", child),))
        with patch.object(
            model_module, "_scalar_hash", side_effect=AssertionError("child rehashed")
        ):
            self.assertIsInstance(hash(parent), int)

    def test_shared_child_and_equal_distinct_children_keep_structural_hash(
        self,
    ) -> None:
        kind = parse_source("value = 1").kind
        shared = Model(kind, (ModelPart("scalar", 5),))
        parent = Model(kind, (ModelPart("first", shared), ModelPart("second", shared)))
        separate = Model(
            kind,
            (
                ModelPart("first", Model(kind, (ModelPart("scalar", 5),))),
                ModelPart("second", Model(kind, (ModelPart("scalar", 5),))),
            ),
        )
        self.assertEqual(parent, separate)
        self.assertEqual(hash(parent), hash(separate))
        self.assertEqual(len({parent, separate}), 1)
        self.assertEqual(model_module._get_cached_hash(shared), hash(shared))

    def test_descendant_caching_uses_same_hash_algorithm(self) -> None:
        cached_root, cached_leaf = self._chain(160)
        ordinary_root, _ = self._chain(160)
        expected = hash(ordinary_root)
        self.assertEqual(hash(cached_root), expected)
        self.assertIsNotNone(model_module._get_cached_hash(cached_leaf))
        self.assertEqual(hash(cached_root), expected)
        with patch.object(
            model_module, "_scalar_hash", side_effect=AssertionError("recomputed")
        ):
            self.assertIsInstance(hash(cached_leaf), int)

    def test_new_models_initialize_slot_and_fallback_handles_missing_slot(self) -> None:
        root, leaf = self._chain(25)
        # Direct attribute access must not raise for newly constructed Models.
        self.assertIsNone(root._cached_structural_hash)
        self.assertIsNone(leaf._cached_structural_hash)
        # The default-value fallback remains necessary for old/unpickled Models.
        object.__delattr__(leaf, "_cached_structural_hash")
        with self.assertRaises(AttributeError):
            _ = leaf._cached_structural_hash
        self.assertIsNone(model_module._get_cached_hash(leaf))
        root_hash = hash(root)
        self.assertEqual(hash(root), root_hash)
        self.assertEqual(model_module._get_cached_hash(leaf), hash(leaf))

    def test_hashing_root_makes_hashing_all_children_cache_only(self) -> None:
        kind = parse_source("value = 1").kind
        nodes = [Model(kind, (ModelPart("scalar", 42),))]
        for _ in range(120):
            nodes.append(Model(kind, (ModelPart("child", nodes[-1]),)))
        root_hash = hash(nodes[-1])
        with patch.object(
            model_module,
            "_compute_model_hash",
            side_effect=AssertionError("descendant recomputed"),
        ):
            for node in reversed(nodes):
                self.assertEqual(hash(node), model_module._get_cached_hash(node))
            self.assertEqual(hash(nodes[-1]), root_hash)

    def test_copies_pickle_and_replace_do_not_inherit_process_hash_cache(self) -> None:
        model = parse_source("value = True")
        original_hash = hash(model)
        for copied in (
            copy.copy(model),
            copy.deepcopy(model),
            pickle.loads(pickle.dumps(model)),
        ):
            with self.subTest(copy_type=type(copied)):
                self.assertIsNone(model_module._get_cached_hash(copied))
                self.assertEqual(copied, model)
                self.assertEqual(hash(copied), original_hash)
        replaced = dataclasses.replace(model, features=("replacement",))
        self.assertIsNone(model_module._get_cached_hash(replaced))
        self.assertNotEqual(replaced, model)
        self.assertEqual(model_module._get_cached_hash(model), original_hash)

    def test_cache_is_not_a_dataclass_field(self) -> None:
        model = parse_source("value = 1")
        original = tuple(field.name for field in dataclasses.fields(model))
        representation = repr(model)
        hash(model)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(model)), original
        )
        self.assertEqual(repr(model), representation)
        self.assertNotIn("_cached_structural_hash", repr(model))
        self.assertNotIn("_cached_structural_hash", dataclasses.asdict(model))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            model.features = ()  # type: ignore[misc]

    def test_deep_tree_remains_non_recursive_with_caching(self) -> None:
        root, leaf = self._chain(4000)
        same, _ = self._chain(4000)
        self.assertEqual(root, same)
        self.assertEqual(hash(root), hash(same))
        self.assertEqual(hash(root), hash(same))
        self.assertIsNotNone(model_module._get_cached_hash(leaf))

    def test_repeated_hash_is_stable_under_parallel_access(self) -> None:
        root, _ = self._chain(250)
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: hash(root), range(20)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(hash(root), results[0])


if __name__ == "__main__":
    unittest.main()
