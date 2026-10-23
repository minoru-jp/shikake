"""PEP 695/696 TypeAlias and type parameter modeling contracts."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

import shikake
from shikake._mica.model import Model


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    value = model.get(role)
    assert isinstance(value, tuple)
    return cast(tuple[Model, ...], value)


def child(model: Model, role: str) -> Model:
    result = model.get(role)
    assert isinstance(result, Model)
    return result


class TypeDeclarationContracts(unittest.TestCase):
    def test_kind_structure_feature_contracts(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(
            (len(index.all_kinds()), len(index.all_structures())), (143, 61)
        )
        self.assertEqual(len(index.all_features()), 2)
        self.assertIsNone(index.structure_of("model.definition.type_parameter"))
        self.assertTrue(
            index.is_a(
                "model.definition.type_parameter.type_variable_tuple",
                "model.definition",
            )
        )
        self.assertEqual(
            [
                part.role
                for part in index.require_structure("model.definition.type_alias").parts
            ],
            ["name", "type_parameters", "value"],
        )
        self.assertEqual(
            [
                part.role
                for part in index.require_structure("model.definition.function").parts
            ],
            ["name", "parameters", "type_parameters", "decorators", "returns", "body"],
        )
        self.assertEqual(
            [
                part.role
                for part in index.require_structure("model.definition.class").parts
            ],
            ["name", "type_parameters", "bases", "keywords", "decorators", "body"],
        )

    def test_old_function_and_class_have_empty_parameters(self) -> None:
        root = shikake.parse_source("def f(x): return x\nclass C: pass\n")
        fn, cls = nodes(root, "body")
        self.assertEqual(nodes(fn, "type_parameters"), ())
        self.assertEqual(nodes(cls, "type_parameters"), ())

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_simple_alias_and_annotated_alias_are_distinct(self) -> None:
        root = shikake.parse_source("type A = int\nA2: TypeAlias = int\n")
        alias, annotation = nodes(root, "body")
        self.assertEqual(alias.kind.id, "model.definition.type_alias")
        self.assertEqual(alias.get("name"), "A")
        self.assertEqual(nodes(alias, "type_parameters"), ())
        self.assertEqual(child(alias, "value").kind.id, "model.value.named")
        self.assertEqual(annotation.kind.id, "model.definition.variable")
        self.assertEqual(alias.span.line if alias.span is not None else None, 1)
        inspected = shikake.inspect_source("type A = int\n")
        self.assertTrue(inspected.complete)
        self.assertEqual(inspected.issues, ())
        self.assertEqual(inspected.model, shikake.parse_source("type A = int\n"))

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_bound_and_constraint_use_expression_models(self) -> None:
        root = shikake.parse_source(
            "type Simple[T: int] = list[T]\ntype Choices[T: (int, str)] = list[T]\n"
        )
        simple, choices = nodes(root, "body")
        t1 = nodes(simple, "type_parameters")[0]
        t2 = nodes(choices, "type_parameters")[0]
        self.assertEqual(t1.kind.id, "model.definition.type_parameter.type_variable")
        self.assertEqual(t1.get("name"), "T")
        self.assertEqual(child(t1, "restriction").kind.id, "model.value.named")
        self.assertEqual(
            child(t2, "restriction").kind.id, "model.value.collection.tuple"
        )
        self.assertIsNone(t1.get("default"))
        self.assertEqual(t1.span.line if t1.span is not None else None, 1)

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_generic_function_class_and_type_parameter_categories(self) -> None:
        root = shikake.parse_source(
            "class Container[T, *Ts, **P]:\n"
            "    def get[U](self, value: U) -> U: return value\n"
            "async def fetch[V](v: V) -> V: return v\n"
            "def produce[T](): yield None\n"
        )
        cls, async_fn, generator = nodes(root, "body")
        self.assertEqual(
            [p.kind.id.rsplit(".", 1)[-1] for p in nodes(cls, "type_parameters")],
            ["type_variable", "type_variable_tuple", "parameter_specification"],
        )
        self.assertEqual(
            [p.get("name") for p in nodes(cls, "type_parameters")], ["T", "Ts", "P"]
        )
        method = nodes(child(cls, "body"), "statements")[0]
        self.assertEqual(method.kind.id, "model.definition.method")
        self.assertEqual(nodes(method, "type_parameters")[0].get("name"), "U")
        self.assertEqual(async_fn.features, ("async",))
        self.assertEqual(nodes(async_fn, "type_parameters")[0].get("name"), "V")
        self.assertEqual(generator.kind.id, "model.definition.generator")
        self.assertEqual(len(nodes(generator, "type_parameters")), 1)
        result = shikake.inspect_source("class C[T]: pass\n")
        self.assertTrue(result.complete)
        self.assertEqual(result.issues, ())

    @unittest.skipUnless(sys.version_info >= (3, 13), "requires Python 3.13 defaults")
    def test_default_values_for_every_parameter_category(self) -> None:
        root = shikake.parse_source(
            "type Items[T: int = str, *Ts = *tuple[int, ...], **P = ...] = tuple[T, *Ts]\n"
        )
        alias = nodes(root, "body")[0]
        normal, variadic, paramspec = nodes(alias, "type_parameters")
        self.assertEqual(child(normal, "default").kind.id, "model.value.named")
        self.assertEqual(
            child(variadic, "default").kind.id, "model.value.starred_expansion"
        )
        self.assertEqual(
            child(paramspec, "default").kind.id,
            "model.value.literal.special.ellipsis",
        )
        self.assertEqual(child(normal, "restriction").kind.id, "model.value.named")

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_package_analysis_and_shadowed_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sample"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "mod.py").write_text(
                "class Base[T]:\n    def f(self): pass\n"
                "class Before(Base):\n    def f(self): pass\n"
                "type Base = int\n"
                "class After(Base):\n    def f(self): pass\n",
                encoding="utf-8",
            )
            parsed = shikake.parse_package(folder)
            self.assertEqual(len(parsed.override_candidates), 2)
            refs = [
                ref
                for ref in parsed.base_references
                if ref.subject.get_name("name") in {"Before", "After"}
            ]
            self.assertTrue(all(ref.binding.may_rebind for ref in refs if ref.binding))
            self.assertTrue(shikake.inspect_package(folder).complete)

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_nested_type_alias_and_type_var_are_visible_in_walk(self) -> None:
        result = shikake.parse_source(
            "class C[T]:\n    type A[U] = tuple[T, U]\n"
            "    def method[V](self, x: V) -> V: return x\n"
        )
        ids = [model.kind.id for model in result.walk()]
        self.assertIn("model.definition.type_alias", ids)
        self.assertEqual(ids.count("model.definition.type_parameter.type_variable"), 3)
        self.assertEqual(
            result,
            shikake.inspect_source(
                "class C[T]:\n    type A[U] = tuple[T, U]\n"
                "    def method[V](self, x: V) -> V: return x\n"
            ).model,
        )


if __name__ == "__main__":
    unittest.main()
