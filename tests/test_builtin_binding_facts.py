"""Built-in names share the three lexical binding dimensions, not value inference."""

from __future__ import annotations

import builtins
import copy
import pickle
import tempfile
import unittest
from pathlib import Path

import shikake


class BuiltinBindingFactsTests(unittest.TestCase):
    def inspect(self, source: str) -> shikake.SourceInspection:
        result = shikake.inspect_source(source)
        self.assertTrue(result.complete, result.issues)
        self.assertIsNotNone(result.model)
        return result

    def test_read_only_builtin_is_virtual_not_eagerly_enumerated(self) -> None:
        inspected = self.inspect("value = tuple([1, 2])")
        assert inspected.model is not None
        self.assertEqual(
            inspected.bindings_for(inspected.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )
        self.assertEqual(
            [binding.name for binding in inspected.name_bindings], ["value"]
        )
        self.assertEqual(inspected.bindings_for(inspected.model, "not_defined"), ())

    def test_module_writes_walrus_deletes_and_conditional_imports(self) -> None:
        examples = (
            ("tuple = list", (True, False)),
            ("tuple = tuple", (True, False)),
            ("(tuple := list)", (True, False)),
            ("if flag:\n    tuple = list", (True, False)),
            ("del tuple", (False, True)),
            ("tuple = list\ndel tuple", (True, True)),
            ("import math as tuple", (True, False)),
            ("from math import sin as tuple", (True, False)),
        )
        for source, (rebound, deleted) in examples:
            with self.subTest(source=source):
                result = self.inspect(source)
                assert result.model is not None
                (binding,) = result.bindings_for(result.model, "tuple")
                self.assertEqual(
                    binding.state, shikake.BindingState("builtin", rebound, deleted)
                )
                self.assertEqual(
                    next(b for b in result.name_bindings if b.name == "tuple"),
                    binding,
                )

    def test_lexical_shadowing_and_global_do_not_conflate_scopes(self) -> None:
        result = self.inspect(
            "def local():\n    tuple = list\n    return tuple([1])\n"
            "def other():\n    return tuple([1])\n"
        )
        assert result.model is not None
        local, other = result.model.get_nodes("body")
        self.assertEqual(
            result.bindings_for(local, "tuple")[0].state,
            shikake.BindingState("stable", False, False),
        )
        self.assertEqual(result.bindings_for(other, "tuple"), ())
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )
        global_result = self.inspect(
            "def mutate():\n    global tuple\n    tuple = list\n"
        )
        assert global_result.model is not None
        self.assertEqual(
            global_result.bindings_for(global_result.model, "tuple")[0].state,
            shikake.BindingState("builtin", True, False),
        )
        self.assertEqual(
            global_result.bindings_for(
                global_result.model.get_nodes("body")[0], "tuple"
            ),
            (),
        )

    def test_annotation_only_local_masks_builtin_without_own_binding(self) -> None:
        result = self.inspect("def f():\n    tuple: int\n    return tuple\n")
        assert result.model is not None
        local = result.model.get_nodes("body")[0]
        self.assertEqual(result.bindings_for(local, "tuple"), ())
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )

    def test_wildcard_import_may_shadow_builtin(self) -> None:
        result = self.inspect("from unknown import *\nvalue = tuple([1])\n")
        assert result.model is not None
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", True, False),
        )

    def test_package_queries_and_reference_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "example"
            folder.mkdir()
            (folder / "__init__.py").write_text("class D(tuple): pass\n")
            package = shikake.parse_package(folder)
        root = package.model.get_nodes("modules")[0]
        (binding,) = package.bindings_for(root, "tuple")
        self.assertEqual(binding.state, shikake.BindingState("builtin", False, False))
        self.assertFalse(any(b.name == "tuple" for b in package.name_bindings))
        (reference,) = package.base_references
        self.assertEqual(reference.binding, binding.state)
        self.assertEqual(reference.targets, ())
        self.assertEqual(package.bindings_for(package.model, "tuple"), ())
        alien = shikake.parse_source("class D(tuple): pass", filename="other")
        self.assertEqual(package.bindings_for(alien, "tuple"), ())
        for cloned in (
            copy.copy(package),
            copy.deepcopy(package),
            pickle.loads(pickle.dumps(package)),
        ):
            cloned_root = cloned.model.get_nodes("modules")[0]
            self.assertEqual(
                cloned.bindings_for(cloned_root, "tuple")[0].state,
                shikake.BindingState("builtin", False, False),
            )

    def test_source_inspection_query_cache_survives_copy_pickle(self) -> None:
        result = self.inspect("value = tuple([1])\nother = value\n")
        assert result.model is not None
        # Warm the identity index before serializing it, so a stale id()-only
        # index would be exposed by deep copies and pickle restoration.
        self.assertEqual(result.bindings_for(result.model, "value")[0].name, "value")
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )
        for clone in (
            copy.copy(result),
            copy.deepcopy(result),
            pickle.loads(pickle.dumps(result)),
        ):
            assert clone.model is not None
            self.assertEqual(clone.bindings_for(clone.model, "value")[0].name, "value")
            self.assertEqual(
                clone.bindings_for(clone.model, "tuple")[0].state,
                shikake.BindingState("builtin", False, False),
            )
            if clone.model is not result.model:
                self.assertEqual(clone.bindings_for(result.model, "other"), ())

    def test_class_body_shadowing_is_not_module_rebinding(self) -> None:
        result = self.inspect(
            "class C:\n    tuple = list\n    class Inner(tuple): pass\n"
        )
        assert result.model is not None
        cls = result.model.get_nodes("body")[0]
        self.assertEqual(
            result.bindings_for(cls, "tuple")[0].state,
            shikake.BindingState("stable", False, False),
        )
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )

    def test_known_star_import_does_not_automatically_shadow_builtin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sample"
            folder.mkdir()
            (folder / "__init__.py").write_text("from .other import *\n")
            (folder / "other.py").write_text("ordinary_name = 1\n")
            package = shikake.parse_package(folder, analyses=set())
        root = package.model.get_nodes("modules")[0]
        self.assertEqual(
            package.bindings_for(root, "tuple")[0].state,
            shikake.BindingState("builtin", False, False),
        )

    @unittest.skipUnless(
        hasattr(builtins, "frozendict"), "requires frozendict built-in"
    )
    def test_runtime_version_builtin_includes_frozendict(self) -> None:
        inspected = self.inspect("item = frozendict()")
        assert inspected.model is not None
        self.assertEqual(
            inspected.bindings_for(inspected.model, "frozendict")[0].state,
            shikake.BindingState("builtin", False, False),
        )

    def test_incomplete_inspection_never_invents_builtin(self) -> None:
        inspected = shikake.inspect_source("return 1")
        self.assertFalse(inspected.complete)
        if inspected.model is not None:
            self.assertEqual(inspected.bindings_for(inspected.model, "tuple"), ())


if __name__ == "__main__":
    unittest.main()
