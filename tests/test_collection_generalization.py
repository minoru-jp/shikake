"""Generalized Collection construction without runtime type inference."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake._mica.model import Model


def expression(text: str) -> Model:
    result = shikake.parse_source(f"result = {text}\n")
    return result.get_nodes("body")[0].get_node("value")


class GeneralizedCollectionTests(unittest.TestCase):
    def test_kind_catalog_has_three_concrete_collection_kinds(self) -> None:
        index = shikake.kind_index()
        descendants = {
            item.id
            for item in index.all_kinds()
            if item.parent_id == "model.value.collection"
        }
        self.assertEqual(
            descendants,
            {
                "model.value.collection.sequence",
                "model.value.collection.mapping",
                "model.value.collection.set",
            },
        )
        for kind in descendants:
            self.assertEqual(
                tuple((p.role, p.shape) for p in index.require_structure(kind).parts),
                (
                    ("construction", "scalar"),
                    ("immutable", "scalar"),
                    ("inputs", "nodes"),
                ),
            )

    def test_literal_and_builtin_types(self) -> None:
        cases = (
            ("[1, 2]", "sequence", "literal", False, 2),
            ("(1, 2)", "sequence", "literal", True, 2),
            ("[]", "sequence", "literal", False, 0),
            ("()", "sequence", "literal", True, 0),
            ("{}", "mapping", "literal", False, 0),
            ("{'a': 1, **rest}", "mapping", "literal", False, 2),
            ("{1, 2}", "set", "literal", False, 2),
            ("list(xs)", "sequence", "builtin", False, 1),
            ("tuple(xs)", "sequence", "builtin", True, 1),
            ("dict(a=1)", "mapping", "builtin", False, 1),
            ("set(xs)", "set", "builtin", False, 1),
            ("frozenset(xs)", "set", "builtin", True, 1),
            ("list()", "sequence", "builtin", False, 0),
            ("tuple()", "sequence", "builtin", True, 0),
        )
        for source, kind, construction, immutable, count in cases:
            with self.subTest(source=source):
                value = expression(source)
                self.assertEqual(value.kind.id, f"model.value.collection.{kind}")
                self.assertEqual(value.get_scalar("construction"), construction)
                self.assertIs(value.get_scalar("immutable"), immutable)
                self.assertEqual(len(value.get_nodes("inputs")), count)
                self.assertFalse(value.features)

    def test_constructor_inputs_preserve_call_argument_shapes(self) -> None:
        value = expression("dict(source, **other)")
        first, second = value.get_nodes("inputs")
        self.assertEqual(first.get_name("name"), "source")
        self.assertEqual(second.kind.id, "model.structural_part.keyword_argument")
        self.assertIsNone(second.get("name"))
        self.assertEqual(second.get_node("value").get_name("name"), "other")
        starred = expression("list(*values)")
        self.assertEqual(starred.kind.id, "model.value.call")
        literal = expression("[*values]").get_nodes("inputs")[0]
        self.assertEqual(literal.kind.id, "model.value.starred_expansion")
        entry = expression("{'k': 1, **rest}").get_nodes("inputs")[1]
        self.assertEqual(entry.kind.id, "model.structural_part.dictionary_entry")
        self.assertIsNone(entry.get("key"))

    def test_comprehension_wrapper_preserves_clause_structure(self) -> None:
        for source, category, inner_kind in (
            ("[x for x in xs if x]", "sequence", "list"),
            ("{x for x in xs}", "set", "set"),
            ("{x: x * 2 for x in xs}", "mapping", "dict"),
        ):
            with self.subTest(source=source):
                value = expression(source)
                self.assertEqual(value.kind.id, f"model.value.collection.{category}")
                self.assertEqual(value.get_scalar("construction"), "comprehension")
                (inner,) = value.get_nodes("inputs")
                self.assertEqual(
                    inner.kind.id, f"model.value.comprehension.{inner_kind}"
                )
                (clause,) = inner.get_nodes("clauses")
                self.assertEqual(clause.get_node("target").get_name("name"), "x")
        self.assertEqual(
            expression("(x for x in xs)").kind.id, "model.value.comprehension.generator"
        )

    def test_equalities_keep_construction_and_immutability(self) -> None:
        values = [expression(text) for text in ("[1, 2]", "(1, 2)", "list([1, 2])")]
        self.assertEqual(len(set(values)), 3)
        self.assertEqual(values[0], expression("[1, 2]"))
        self.assertEqual(hash(values[0]), hash(expression("[1, 2]")))

    def test_shadows_and_unknown_calls_are_never_inferred(self) -> None:
        samples = (
            "list = fn\nresult = list(xs)",
            "result = tuple(xs)\ntuple = fn",
            "del dict\nresult = dict(xs)",
            "def f(list):\n return list(xs)",
            "def f():\n list = fn\n return list(xs)",
            "def f():\n list: int\n return list(xs)",
            "def f():\n global tuple\n tuple = fn\n return tuple(xs)",
            "class C:\n list = fn\n result = list(xs)",
            "result = (lambda list: list(xs))(fn)",
            "result = [list(xs) for list in fs]",
            "result = (lambda: (list := fn)(xs))()",
        )
        for source in samples:
            with self.subTest(source=source):
                model = shikake.parse_source(source)
                calls = [m for m in model.walk() if m.kind.id == "model.value.call"]
                self.assertTrue(calls, source)

    def test_module_global_declaration_is_not_an_infinite_lookup(self) -> None:
        model = shikake.parse_source("global tuple\nresult = tuple(xs)\n")
        value = model.get_nodes("body")[-1].get_node("value")
        self.assertEqual(value.kind.id, "model.value.collection.sequence")
        self.assertEqual(value.get_scalar("construction"), "builtin")

    def test_separate_function_local_does_not_poison_other_scope(self) -> None:
        model = shikake.parse_source(
            "def shadow():\n list = f\n return list(xs)\n"
            "def clean():\n return list(xs)\n"
        )
        functions = model.get_nodes("body")
        shadow_call = (
            functions[0].get_node("body").get_nodes("statements")[-1].get_node("value")
        )
        clean_collection = (
            functions[1].get_node("body").get_nodes("statements")[-1].get_node("value")
        )
        self.assertEqual(shadow_call.kind.id, "model.value.call")
        self.assertEqual(clean_collection.kind.id, "model.value.collection.sequence")

    def test_class_scope_is_skipped_for_nested_method(self) -> None:
        root = shikake.parse_source(
            "class Holder:\n list = other\n def method(self):\n  return list(xs)\n"
        )
        collections = [
            item
            for item in root.walk()
            if item.kind.id == "model.value.collection.sequence"
        ]
        self.assertEqual(len(collections), 1)
        self.assertEqual(collections[0].get_scalar("construction"), "builtin")

    def test_binding_facts_unaffected_by_collection_normalization(self) -> None:
        analyzed = shikake.inspect_source("result = tuple(xs)\n")
        self.assertTrue(analyzed.complete)
        assert analyzed.model is not None
        (binding,) = analyzed.bindings_for(analyzed.model, "tuple")
        self.assertEqual(binding.state.introduction, "builtin")
        self.assertFalse(binding.state.may_rebind)
        value = analyzed.model.get_nodes("body")[0].get_node("value")
        self.assertEqual(value.kind.id, "model.value.collection.sequence")
        unstable = shikake.inspect_source("tuple = fn\nresult = tuple(xs)\n")
        assert unstable.model is not None
        (binding,) = unstable.bindings_for(unstable.model, "tuple")
        self.assertTrue(binding.state.may_rebind)
        self.assertEqual(
            unstable.model.get_nodes("body")[1].get_node("value").kind.id,
            "model.value.call",
        )

    def test_package_and_inspection_share_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pkg.py").write_text("result = tuple(xs)\n")
            package = shikake.parse_package(directory)
            inspected = shikake.inspect_package(directory)
            self.assertTrue(inspected.complete)
            self.assertEqual(package.model, inspected.model)
            self.assertTrue(
                any(
                    item.kind.id == "model.value.collection.sequence"
                    and item.get_scalar("construction") == "builtin"
                    for item in package.model.walk()
                )
            )

    @unittest.skipUnless(sys.version_info >= (3, 15), "requires Python 3.15 frozendict")
    def test_frozendict_is_immutable_mapping(self) -> None:
        value = expression("frozendict({'a': 1})")
        self.assertEqual(value.kind.id, "model.value.collection.mapping")
        self.assertIs(value.get_scalar("immutable"), True)
        self.assertEqual(value.get_scalar("construction"), "builtin")


if __name__ == "__main__":
    unittest.main()
