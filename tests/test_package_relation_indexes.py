"""Identity-based relation lookups preserve the original ordered facts."""

from __future__ import annotations

import copy
import pickle
import unittest
from collections.abc import Iterator
from dataclasses import asdict, replace
from unittest.mock import patch

import shikake
from shikake._mica.model import Model


class _CountingBindings(tuple[shikake.NameBinding, ...]):
    """A tuple-compatible source that records iteration after package creation."""

    scans: int

    def __init__(self, values: tuple[shikake.NameBinding, ...]) -> None:
        self.scans = 0

    def __iter__(self) -> Iterator[shikake.NameBinding]:
        self.scans += 1
        return super().__iter__()


class PackageRelationIndexTests(unittest.TestCase):
    def test_identity_order_duplicates_and_missing_keys(self) -> None:
        source = "class Owner:\n    def task(self): pass\n"
        root = shikake.parse_source(source)
        equivalent = shikake.parse_source(source)
        owner = next(m for m in root.walk() if m.kind.id == "model.definition.class")
        method = next(m for m in root.walk() if m.kind.id == "model.definition.method")
        other_owner = next(
            m for m in equivalent.walk() if m.kind.id == "model.definition.class"
        )
        other_method = next(
            m for m in equivalent.walk() if m.kind.id == "model.definition.method"
        )
        self.assertIsNot(owner, other_owner)
        self.assertEqual(owner, other_owner)
        self.assertIsNot(method, other_method)
        self.assertEqual(method, other_method)

        stable = shikake.BindingState("stable", False, False, False)
        first = shikake.NameBinding("sample", owner, "x", stable)
        unrelated = shikake.NameBinding("sample", owner, "y", stable)
        second = shikake.NameBinding("sample", owner, "x", stable)
        base1 = shikake.BaseReference(owner, root, (), None)
        base2 = shikake.BaseReference(owner, equivalent, (), None)
        override1 = shikake.OverrideCandidate(
            method, method, owner, owner, "sample", "sample"
        )
        override2 = shikake.OverrideCandidate(
            method, other_method, owner, other_owner, "sample", "sample"
        )

        # A structural Model hash must never be consulted for these lookups.
        with patch.object(Model, "__hash__", side_effect=AssertionError("hashed")):
            package = shikake.PackageModel(
                root,
                override_candidates=(override1, override2),
                base_references=(base1, base2),
                name_bindings=(first, unrelated, second),
            )
            self.assertEqual(package.bindings_for(owner, "x"), (first, second))
            self.assertEqual(package.bindings_for(owner, "y"), (unrelated,))
            self.assertEqual(package.bases_for(owner), (base1, base2))
            self.assertEqual(package.overrides_for(method), (override1, override2))
            self.assertEqual(package.bindings_for(other_owner, "x"), ())
            self.assertEqual(package.bases_for(other_owner), ())
            self.assertEqual(package.overrides_for(other_method), ())
            self.assertEqual(package.bindings_for(owner, "absent"), ())

        self.assertIs(package.bindings_for(owner, "x")[0], first)
        self.assertIs(package.bases_for(owner)[0], base1)
        self.assertIs(package.overrides_for(method)[1], override2)
        self.assertIs(package.model, root)
        self.assertEqual(package.name_bindings, (first, unrelated, second))
        self.assertEqual(package.base_references, (base1, base2))
        self.assertEqual(package.override_candidates, (override1, override2))

    def test_lookup_does_not_rescan_fact_tuples(self) -> None:
        root = shikake.parse_source("answer = 1")
        binding = shikake.NameBinding(
            "sample",
            root,
            "answer",
            shikake.BindingState("stable", False, False, False),
        )
        source = _CountingBindings((binding,))
        package = shikake.PackageModel(root, name_bindings=source)
        self.assertEqual(source.scans, 1)
        for _ in range(100):
            self.assertEqual(package.bindings_for(root, "answer"), (binding,))
            self.assertEqual(package.bindings_for(root, "not_found"), ())
        self.assertEqual(source.scans, 1)

    def test_copies_pickle_and_replace_keep_identity_lookup_valid(self) -> None:
        root = shikake.parse_source("answer = 1")
        first = shikake.NameBinding(
            "sample",
            root,
            "answer",
            shikake.BindingState("stable", False, False, False),
        )
        base = shikake.BaseReference(root, root, (), None)
        override = shikake.OverrideCandidate(root, root, root, root, "sample", "sample")
        package = shikake.PackageModel(
            root, (override,), (base,), name_bindings=(first,)
        )
        for restored in (
            copy.copy(package),
            copy.deepcopy(package),
            pickle.loads(pickle.dumps(package)),
        ):
            with self.subTest(kind=type(restored).__name__):
                self.assertIs(
                    restored.bindings_for(restored.model, "answer")[0],
                    restored.name_bindings[0],
                )
                self.assertIs(
                    restored.bases_for(restored.model)[0], restored.base_references[0]
                )
                self.assertIs(
                    restored.overrides_for(restored.model)[0],
                    restored.override_candidates[0],
                )

        cleared = replace(
            package, name_bindings=(), base_references=(), override_candidates=()
        )
        self.assertEqual(cleared.bindings_for(root, "answer"), ())
        self.assertEqual(cleared.bases_for(root), ())
        self.assertEqual(cleared.overrides_for(root), ())
        self.assertEqual(package.bindings_for(root, "answer"), (first,))
        self.assertIsInstance(asdict(package), dict)


if __name__ == "__main__":
    unittest.main()
