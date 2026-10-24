"""Annotation scope visibility and distinct public lexical bindings."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake._mica.builtin_names import BUILTIN_NAMES


@unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
class AnnotationVisibilityTests(unittest.TestCase):
    def test_class_body_visible_to_direct_annotation_scopes(self) -> None:
        source = (
            "class Outer:\n"
            "    list = factory\n"
            "    type A[T] = list()\n"
            "    class Inner[T](list()): ...\n"
            "    def m[T](self, x: list()) -> list(): ...\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete, inspected.issues)
        assert inspected.model is not None
        calls = [
            node
            for node in inspected.model.walk()
            if node.kind.id in {"model.value.call", "model.value.collection.sequence"}
        ]
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(node.kind.id == "model.value.call" for node in calls))
        self.assertEqual([node.span.line for node in calls if node.span], [3, 4, 5, 5])

    def test_method_and_nested_class_bodies_do_not_inherit_class_locals(self) -> None:
        source = (
            "class Outer:\n"
            "    list = factory\n"
            "    def m[T](self):\n"
            "        return list()\n"
            "    class Inner[T]:\n"
            "        result = list()\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete, inspected.issues)
        assert inspected.model is not None
        collections = [
            node
            for node in inspected.model.walk()
            if node.kind.id == "model.value.collection.sequence"
        ]
        self.assertEqual(len(collections), 2)
        self.assertEqual([node.span.line for node in collections if node.span], [4, 6])

    def test_annotation_scopes_and_function_body_are_independent_bindings(self) -> None:
        source = "def f[T]():\n    T = 1\n"
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete, inspected.issues)
        assert inspected.model is not None
        function = next(
            node
            for node in inspected.model.walk()
            if node.kind.id == "model.definition.function"
        )
        bindings = inspected.bindings_for(function, "T")
        self.assertEqual(len(bindings), 2)
        self.assertTrue(all(binding.scope is function for binding in bindings))
        self.assertEqual({b.scope_kind for b in bindings}, {"annotation", "function"})
        self.assertTrue(
            all(
                b.state == shikake.BindingState("stable", False, False)
                for b in bindings
            )
        )
        self.assertEqual(
            {b.scope_kind for b in inspected.name_bindings if b.name == "T"},
            {"annotation", "function"},
        )
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "example.py").write_text(source)
            package = shikake.inspect_package(temp)
            self.assertTrue(package.complete, package.issues)
            function_model = next(
                node
                for node in package.model.walk()
                if node.kind.id == "model.definition.function"
            )
            self.assertEqual(
                {
                    b.scope_kind
                    for b in package.package.bindings_for(function_model, "T")
                },
                {"annotation", "function"},
            )

    def test_alias_type_parameters_are_annotation_bindings(self) -> None:
        inspected = shikake.inspect_source("type A[T] = T")
        self.assertTrue(inspected.complete, inspected.issues)
        (type_parameter,) = [b for b in inspected.name_bindings if b.name == "T"]
        self.assertEqual(type_parameter.scope_kind, "annotation")
        (alias,) = [b for b in inspected.name_bindings if b.name == "A"]
        self.assertEqual(alias.scope_kind, "module")


class BuiltinInventoryTests(unittest.TestCase):
    @unittest.skipUnless(
        sys.implementation.name == "cpython", "fixed inventory targets CPython"
    )
    def test_fixed_inventory_matches_isolated_standard_interpreter(self) -> None:
        # Run a clean child interpreter, never the process-mutated builtins.
        script = "import builtins, json; print(json.dumps(sorted(vars(builtins))))"
        completed = subprocess.run(
            [sys.executable, "-S", "-I", "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )
        observed = frozenset(json.loads(completed.stdout))
        self.assertEqual(observed, BUILTIN_NAMES)

    @unittest.skipUnless(sys.version_info >= (3, 15), "requires Python 3.15")
    def test_python315_lazy_import_name_and_exception(self) -> None:
        self.assertIn("__lazy_import__", BUILTIN_NAMES)
        self.assertIn("ImportCycleError", BUILTIN_NAMES)


class ForwardedOwnershipTests(unittest.TestCase):
    def test_nested_nonlocal_owner_is_shared_across_multiple_forwarders(self) -> None:
        source = (
            "def outer():\n"
            "    x = 1\n"
            "    def middle():\n"
            "        nonlocal x\n"
            "        x = 2\n"
            "        def inner():\n"
            "            nonlocal x\n"
            "            x = 3\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete, inspected.issues)
        assert inspected.model is not None
        functions = {
            node.get_name("name"): node
            for node in inspected.model.walk()
            if node.kind.id == "model.definition.function"
        }
        (bound,) = inspected.bindings_for(functions["outer"], "x")
        self.assertEqual(bound.scope_kind, "function")
        self.assertEqual(bound.state, shikake.BindingState("stable", True, False))
        self.assertEqual(inspected.bindings_for(functions["middle"], "x"), ())
        self.assertEqual(inspected.bindings_for(functions["inner"], "x"), ())
