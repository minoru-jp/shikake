"""PackageModel repr is compact without losing public relationship data."""

from __future__ import annotations

import unittest

import shikake


class PackageDiagnosticReprTests(unittest.TestCase):
    def test_relationship_counts_without_expanding_facts(self) -> None:
        root = shikake.parse_source("class A: pass\n")
        state = shikake.BindingState("stable", False, False)
        binding = shikake.NameBinding("example", root, "name", state)
        base = shikake.BaseReference(root, root, (), None)
        candidate = shikake.OverrideCandidate(
            root, root, root, root, "example", "example"
        )
        package = shikake.PackageModel(
            root,
            override_candidates=(candidate,) * 400,
            base_references=(base,) * 300,
            analyses=frozenset({"inheritance"}),
            name_bindings=(binding,) * 3000,
        )
        text = repr(package)
        self.assertLessEqual(len(text), 512)
        self.assertIn("PackageModel(model=Model(kind=", text)
        self.assertIn("override_candidates=<400 items>", text)
        self.assertIn("base_references=<300 items>", text)
        self.assertIn("analyses=frozenset({'inheritance'})", text)
        self.assertIn("name_bindings=<3000 items>", text)
        self.assertNotIn("NameBinding(", text)
        self.assertNotIn("BaseReference(", text)
        self.assertNotIn("OverrideCandidate(", text)
        self.assertNotIn("_binding_index", text)
        self.assertEqual(len(package.name_bindings), 3000)
        self.assertIs(package.bases_for(root)[0], base)
        self.assertIs(package.bindings_for(root, "name")[0], binding)
        self.assertIs(package.overrides_for(root)[0], candidate)
        inspection = shikake.PackageInspection(package, ())
        self.assertLessEqual(len(repr(inspection)), 560)

    def test_empty_and_unusually_large_metadata_are_bounded(self) -> None:
        root = shikake.parse_source("value = 1\n")
        package = shikake.PackageModel(root)
        self.assertIn("analyses=frozenset()", repr(package))
        self.assertIn("name_bindings=<0 items>", repr(package))
        self.assertLessEqual(len(repr(package)), 512)

        unusual = shikake.PackageModel(root, analyses=frozenset({"x" * 1000}))
        self.assertLessEqual(len(repr(unusual)), 512)
        self.assertIn("name_bindings=<0 items>", repr(unusual))


if __name__ == "__main__":
    unittest.main()
