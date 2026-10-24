"""Review regressions: source-only name facts guard collection normalization."""

from __future__ import annotations

import builtins
import symtable
import sys
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake._mica.builtin_names import BUILTIN_NAMES


def values(source: str) -> list[shikake.Model]:
    return [
        node
        for node in shikake.parse_source(source).walk()
        if node.kind.id
        in {
            "model.value.call",
            "model.value.collection.sequence",
            "model.value.collection.mapping",
            "model.value.collection.set",
        }
    ]


class ReviewCollectionGuards(unittest.TestCase):
    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_generic_scopes_hide_builtin_without_inference(self) -> None:
        cases = (
            "class C[list]:\n    def m(self):\n        return list(1)",
            "def f[list](x: list()): ...",
            "type A[list] = list()",
            "class D[list](list()): ...",
            "class C[list]:\n    class Inner:\n        def m(self):\n            return list(1)",
            "class C[list]:\n    def m(self):\n        return (lambda: list(1))()",
        )
        for code in cases:
            with self.subTest(code=code):
                self.assertTrue(shikake.inspect_source(code).complete)
                self.assertTrue(
                    any(node.kind.id == "model.value.call" for node in values(code))
                )
                self.assertFalse(
                    any(
                        node.kind.id == "model.value.collection.sequence"
                        for node in values(code)
                    )
                )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_type_parameters_are_lexically_visible_only_where_expected(self) -> None:
        # Defaults/decorators are outside the annotation scope; annotations,
        # class bases, and type-alias values are inside it.
        source = "def f[list](x=list(), y: list() = None) -> list(): ..."
        nodes = [n for n in values(source) if n.span is not None]
        self.assertEqual(
            sum(n.kind.id == "model.value.collection.sequence" for n in nodes), 1
        )
        self.assertEqual(sum(n.kind.id == "model.value.call" for n in nodes), 2)
        generic = "@decorator(list())\nclass C[list](list()): ..."
        nodes = values(generic)
        self.assertEqual(
            sum(n.kind.id == "model.value.collection.sequence" for n in nodes), 1
        )
        self.assertEqual(sum(n.kind.id == "model.value.call" for n in nodes), 2)

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_compiler_scope_agrees_on_generic_method_free_name(self) -> None:
        source = "class C[list]:\n    def m(self):\n        return list(1)"
        table = symtable.symtable(source, "<scope-regression>", "exec")

        def children(block):
            yield block
            for nested in block.get_children():
                yield from children(nested)

        method = next(block for block in children(table) if block.get_name() == "m")
        self.assertTrue(method.lookup("list").is_free())
        self.assertFalse(
            any(n.kind.id == "model.value.collection.sequence" for n in values(source))
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires PEP 695")
    def test_base_binding_does_not_fall_through_type_parameters(self) -> None:
        source = "class C[tuple]:\n    def m(self):\n        class Inner(tuple): pass\n"
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "sample.py").write_text(source)
            inspected = shikake.inspect_package(folder)
            self.assertTrue(inspected.complete, inspected.issues)
            (base,) = inspected.base_references
            self.assertEqual(base.binding, shikake.BindingState("stable", False, False))

    def test_partial_package_never_invents_implicit_builtin_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "a.py").write_text("list = 1\n")
            (folder / "bad.py").write_text("def (\n")
            partial = shikake.inspect_package(folder)
            self.assertFalse(partial.complete)
            (module,) = partial.model.get_nodes("modules")
            self.assertEqual(partial.package.bindings_for(module, "list"), ())
            self.assertEqual(partial.package.bindings_for(module, "tuple"), ())

    def test_fixed_builtin_inventory_is_independent_of_process_mutations(self) -> None:
        self.assertNotIn("exit", BUILTIN_NAMES)
        self.assertNotIn("quit", BUILTIN_NAMES)
        self.assertNotIn("help", BUILTIN_NAMES)
        self.assertNotIn("_", BUILTIN_NAMES)
        key = "shikake_review_injected_name"
        self.assertNotIn(key, BUILTIN_NAMES)
        setattr(builtins, key, object())
        try:
            result = shikake.inspect_source("a = shikake_review_injected_name()")
            assert result.model is not None
            self.assertEqual(result.bindings_for(result.model, key), ())
        finally:
            delattr(builtins, key)

    def test_standard_builtins_follow_version_contract(self) -> None:
        self.assertEqual("frozendict" in BUILTIN_NAMES, sys.version_info >= (3, 15))
        self.assertEqual("sentinel" in BUILTIN_NAMES, sys.version_info >= (3, 15))

    def test_constructor_call_arity_and_unpacking_are_syntax_guards(self) -> None:
        invalid = (
            "list(a, b)",
            "tuple(a, b)",
            "set(a, b)",
            "frozenset(a, b)",
            "list(x=1)",
            "set(x=1)",
            "tuple(**kwargs)",
            "set(*items)",
            "dict(a, b)",
            "dict(*items)",
            "dict(a, *items)",
            "dict(a, b=1, c=2, *items)",
        )
        for text in invalid:
            with self.subTest(text=text):
                (value,) = values("result = " + text)
                self.assertEqual(value.kind.id, "model.value.call")
        valid = (
            ("list()", "sequence"),
            ("tuple(xs)", "sequence"),
            ("set(xs)", "set"),
            ("frozenset()", "set"),
            ("dict()", "mapping"),
            ("dict(**kwargs)", "mapping"),
            ("dict(xs, **kwargs)", "mapping"),
        )
        for text, category in valid:
            with self.subTest(text=text):
                (value,) = values("result = " + text)
                self.assertEqual(value.kind.id, "model.value.collection." + category)

    def test_unknown_star_import_withholds_model_normalization(self) -> None:
        source = "from unknown import *\nresult = tuple(xs)"
        self.assertEqual(values(source)[0].kind.id, "model.value.call")
        inspected = shikake.inspect_source(source)
        assert inspected.model is not None
        (binding,) = inspected.bindings_for(inspected.model, "tuple")
        self.assertTrue(binding.state.may_rebind)


if __name__ == "__main__":
    unittest.main()
