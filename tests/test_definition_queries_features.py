"""DefinitionIndex queries and external Feature realization/attachment."""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import external_feature_definitions as fixture

import shikake
from shikake._mica.kinds.regulation import PartContract
from shikake.external import ExternalDefinitionsBuilder, Role, load_external_definitions

SOURCE = (
    "from sample.helpers import do_work, TaggedType, TaggedArray\n"
    "x = do_work(2)\n"
    "def func(value: TaggedType) -> TaggedArray[TaggedType]:\n"
    "    pass\n"
)


class DefinitionQueriesFeaturesTests(unittest.TestCase):
    def test_classification_does_not_inherit_role(self) -> None:
        index = shikake.definition_index()
        self.assertTrue(
            index.classified_under(
                "model.definition.method", "model.definition.function"
            )
        )
        # The definition belongs to the exact concrete Kind, not the ancestor.
        method = index.structure_of("model.definition.method")
        function = index.structure_of("model.definition.function")
        self.assertIsNotNone(method)
        self.assertIsNotNone(function)
        assert method is not None and function is not None
        self.assertEqual(
            index.defines_role("model.definition.method", "body"),
            "body" in {p.role for p in method.parts},
        )
        self.assertFalse(index.defines_role("model", "body"))
        self.assertFalse(index.defines_role("model.value.named", "nonexistent"))
        self.assertTrue(index.defines_role("model.module", "body"))
        self.assertEqual(shikake.parse_source("").get_nodes("body"), ())
        with self.assertRaises(KeyError):
            index.defines_role("not.registered", "body")
        custom = shikake.DefinitionIndex(
            (
                shikake.Kind("model", None),
                shikake.Kind("child", "model", "own"),
                shikake.Kind("grandchild", "child", "other"),
            ),
            (
                shikake.Structure("own", (PartContract("parent_role", "nodes"),)),
                shikake.Structure("other", (PartContract("child_role", "node"),)),
            ),
        )
        self.assertTrue(custom.classified_under("grandchild", "child"))
        self.assertFalse(custom.defines_role("grandchild", "parent_role"))
        self.assertTrue(custom.defines_role("grandchild", "child_role"))

    def test_feature_query_uses_declared_taxonomy_and_not_model_state(self) -> None:
        index = shikake.definition_index()
        self.assertTrue(index.allows_feature("model.definition.method", "async"))
        self.assertFalse(index.allows_feature("model.value.named", "async"))
        with self.assertRaises(KeyError):
            index.allows_feature("model", "missing")
        with self.assertRaises(KeyError):
            index.allows_feature("missing", "async")
        self.assertNotIn("async", shikake.parse_source("def f(): pass").features)

    def test_shikumi_feature_declaration_and_all_mapping_forms(self) -> None:
        definitions = load_external_definitions(fixture)
        index = definitions.index
        self.assertTrue(index.allows_feature("demo.call", "demo.tag"))
        self.assertTrue(index.allows_feature("demo.type", "demo.tag"))
        self.assertTrue(index.defines_role("demo.call", "value"))
        self.assertFalse(index.defines_role("demo.type", "value"))
        root = shikake.parse_source(SOURCE, definitions=definitions)
        tagged = [
            m
            for m in root.walk()
            if m.kind.id in ("demo.call", "demo.type", "demo.generic")
        ]
        self.assertEqual([m.kind.id for m in tagged].count("demo.call"), 1)
        self.assertEqual([m.kind.id for m in tagged].count("demo.type"), 2)
        self.assertEqual([m.kind.id for m in tagged].count("demo.generic"), 1)
        self.assertTrue(all(m.features == ("demo.tag",) for m in tagged))

    def test_external_unicode_ids_are_not_normalized(self) -> None:
        definitions = (
            ExternalDefinitionsBuilder()
            .add_feature("vendor.foo", ("model",))
            .add_feature("vendor.ｆｏｏ", ("model",))
            .build()
        )
        ids = {feature.id for feature in definitions.index.all_features()}
        self.assertIn("vendor.foo", ids)
        self.assertIn("vendor.ｆｏｏ", ids)
        self.assertNotEqual("vendor.foo", "vendor.ｆｏｏ")

    def test_builder_feature_parity_and_feature_only_definition(self) -> None:
        b = ExternalDefinitionsBuilder()
        b.add_kind("demo.parent", "model.value")
        b.add_feature("demo.tag", ("demo.parent",))
        b.add_structure("demo.call.layout", (Role("value", "node"),))
        b.add_kind("demo.call", "demo.parent", "demo.call.layout")
        b.add_mapping(
            "sample.helpers:do_work", "demo.call", ("value",), features=("demo.tag",)
        )
        b.add_type(
            "sample.helpers:TaggedType",
            "demo.type",
            parent_id="demo.parent",
            features=("demo.tag",),
        )
        b.add_generic(
            "sample.helpers:TaggedArray",
            "demo.generic",
            ("element",),
            parent_id="demo.parent",
            features=("demo.tag",),
        )
        definitions = b.build()
        self.assertEqual(
            {f.id for f in definitions.index.all_features()},
            {f.id for f in load_external_definitions(fixture).index.all_features()},
        )
        tagged = [
            m
            for m in shikake.parse_source(SOURCE, definitions=definitions).walk()
            if m.kind.id in ("demo.call", "demo.type", "demo.generic")
        ]
        self.assertEqual(len(tagged), 4)
        self.assertTrue(all(m.features == ("demo.tag",) for m in tagged))
        only = (
            ExternalDefinitionsBuilder().add_feature("demo.extra", ("model",)).build()
        )
        self.assertTrue(only.index.allows_feature("model.value.named", "demo.extra"))

    def test_invalid_external_feature_definitions_and_attachments(self) -> None:
        for builder, message in (
            (
                ExternalDefinitionsBuilder().add_feature("async", ("model",)),
                "external Feature ID",
            ),
            (
                ExternalDefinitionsBuilder().add_feature(
                    "vendor.unknown", ("not.registered",)
                ),
                "unknown allowed Kind",
            ),
            (
                ExternalDefinitionsBuilder().add_feature("vendor.empty", ()),
                "must have allowed Kinds",
            ),
            (
                ExternalDefinitionsBuilder().add_call(
                    "demo:thing", "demo.thing", (), features=("missing",)
                ),
                "unknown Model feature",
            ),
            (
                ExternalDefinitionsBuilder().add_call(
                    "demo:thing", "demo.thing", (), features=("async",)
                ),
                "not applicable",
            ),
            (
                ExternalDefinitionsBuilder().add_call(
                    "demo:thing", "demo.thing", (), features=("async", "async")
                ),
                "duplicate Model features",
            ),
        ):
            with (
                self.subTest(error=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                builder.build()

    def test_all_parse_entry_points_preserve_declared_features(self) -> None:
        definitions = load_external_definitions(fixture)
        single = shikake.inspect_source(SOURCE, definitions=definitions)
        self.assertTrue(single.complete)
        assert single.model is not None
        assert any(m.features == ("demo.tag",) for m in single.model.walk())
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "samplepkg"
            folder.mkdir()
            (folder / "main.py").write_text(SOURCE, encoding="utf-8")
            package = shikake.parse_package(folder, definitions=definitions)
            inspected = shikake.inspect_package(folder, definitions=definitions)
            self.assertTrue(inspected.complete)
            assert inspected.package is not None
            for root in (package.model, inspected.package.model):
                self.assertEqual(
                    len([m for m in root.walk() if m.features == ("demo.tag",)]),
                    4,
                )

    def test_builder_rejects_invalid_feature_sequences(self) -> None:
        with self.assertRaisesRegex(TypeError, "allowed_kind_ids"):
            ExternalDefinitionsBuilder().add_feature("example", "model")
        with self.assertRaisesRegex(TypeError, "allowed_kind_ids"):
            ExternalDefinitionsBuilder().add_feature(
                "example", cast(Sequence[str], (123,))
            )
        with self.assertRaisesRegex(TypeError, "features"):
            ExternalDefinitionsBuilder().add_call(
                "demo:thing", "demo.thing", (), features="demo.tag"
            )
        with self.assertRaisesRegex(TypeError, "features"):
            ExternalDefinitionsBuilder().add_type(
                "demo:Thing", "demo.thing", features=cast(Sequence[str], (123,))
            )

    def test_nonmatching_external_call_does_not_attach_features(self) -> None:
        definitions = load_external_definitions(fixture)
        root = shikake.parse_source(
            "from sample.helpers import do_work\nx = do_work()\n",
            definitions=definitions,
        )
        self.assertFalse(any(m.features for m in root.walk()))


if __name__ == "__main__":
    unittest.main()
