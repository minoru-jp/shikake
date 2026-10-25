"""External declaration provenance, composition and stable Feature identity."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from typing import cast

import shikake
from shikake.external import ExternalDefinitions, ExternalDefinitionsBuilder


def _call(source: str, definitions: ExternalDefinitions, kind: str) -> shikake.Model:
    root = shikake.parse_source(source, definitions=definitions)
    return next(model for model in root.walk() if model.kind.id == kind)


class ExternalReviewFixTests(unittest.TestCase):
    def test_base_preserves_original_mapping_and_feature_provenance(self) -> None:
        first = (
            ExternalDefinitionsBuilder()
            .add_feature("vendor.shared", ("model.value",))
            .add_call(
                "lib1:alpha",
                "vendor.alpha",
                ("value",),
                features=("vendor.shared",),
            )
            .build()
        )
        second = (
            ExternalDefinitionsBuilder(base=first)
            .add_call(
                "lib2:beta",
                "vendor.beta",
                ("value",),
                features=("vendor.shared",),
            )
            .build()
        )
        self.assertEqual(len(second.mappings), 2)
        self.assertEqual(second.external_feature_ids, frozenset({"vendor.shared"}))
        self.assertEqual(
            _call(
                "from lib1 import alpha\nx = alpha(1)\n", second, "vendor.alpha"
            ).features,
            ("vendor.shared",),
        )
        self.assertEqual(
            _call(
                "from lib2 import beta\nx = beta(2)\n", second, "vendor.beta"
            ).features,
            ("vendor.shared",),
        )
        # Original compiled definitions must not mutate in the next build.
        self.assertEqual(len(first.mappings), 1)

    def test_base_preserves_all_mapping_kinds_and_detects_cross_base_collision(
        self,
    ) -> None:
        first = (
            ExternalDefinitionsBuilder()
            .add_type("lib:Type", "vendor.type")
            .add_generic("lib:Array", "vendor.array", ("element",))
            .build()
        )
        second = (
            ExternalDefinitionsBuilder(base=first)
            .add_call("lib:call", "vendor.call", ("value",))
            .build()
        )
        self.assertEqual(len(second.type_mappings), 1)
        self.assertEqual(len(second.generic_mappings), 1)
        self.assertEqual(len(second.mappings), 1)
        with self.assertRaisesRegex(ValueError, "duplicate external target"):
            (
                ExternalDefinitionsBuilder(base=first)
                .add_type("lib:Type", "vendor.other_type")
                .build()
            )

    def test_standard_feature_is_not_assignable_even_when_kind_allows_it(self) -> None:
        # DefinitionIndex query and external assignment authorization are distinct.
        builder = (
            ExternalDefinitionsBuilder()
            .add_kind("vendor.fn", "model.definition.function")
            .add_call(
                "lib:go",
                "vendor.fn.go",
                ("value",),
                parent_id="vendor.fn",
                features=("async",),
            )
        )
        with self.assertRaisesRegex(ValueError, "non-external Feature: async"):
            builder.build()
        index = shikake.definition_index()
        self.assertTrue(index.allows_feature("model.definition.function", "async"))

    def test_raw_index_is_not_extension_provenance(self) -> None:
        first = (
            ExternalDefinitionsBuilder()
            .add_feature("vendor.shared", ("model.value",))
            .build()
        )
        # A bare index has no mapping or external-declaration origin information.
        with self.assertRaisesRegex(
            ValueError, "custom or extended DefinitionIndex cannot be combined"
        ):
            (
                ExternalDefinitionsBuilder(base=first.index)
                .add_call("lib:fn", "vendor.fn", (), features=("vendor.shared",))
                .build()
            )

    def test_builtin_definition_index_is_a_valid_base(self) -> None:
        builtins = shikake.definition_index()
        defined = (
            ExternalDefinitionsBuilder(base=builtins)
            .add_call("lib:run", "vendor.run", ())
            .build()
        )
        self.assertTrue(defined.index.classified_under("vendor.run", "model.value"))
        self.assertEqual(len(defined.mappings), 1)
        self.assertEqual(
            len(defined.index.all_features()), len(builtins.all_features())
        )
        self.assertEqual(
            _call("from lib import run\nrun()", defined, "vendor.run").kind.id,
            "vendor.run",
        )

    def test_custom_index_error_does_not_suggest_a_wrong_argument_type(self) -> None:
        custom = shikake.DefinitionIndex(
            (
                *shikake.definition_index().all_kinds(),
                shikake.Kind("vendor.root", "model.value"),
            ),
            shikake.definition_index().all_structures(),
            shikake.definition_index().all_features(),
        )
        with self.assertRaisesRegex(
            ValueError, "custom or extended DefinitionIndex"
        ) as issue:
            ExternalDefinitionsBuilder(base=custom).add_kind(
                "vendor.other", "model.value"
            ).build()
        self.assertIn("base=previous", str(issue.exception))
        # index= accepts DefinitionIndex only. The message must not invite passing
        # ExternalDefinitions to that parameter.
        import external_feature_definitions as fixture

        with self.assertRaisesRegex(ValueError, "custom or extended DefinitionIndex"):
            shikake.parse_source("x = 1", index=custom, definitions=fixture)

    def test_python_keywords_are_valid_segments_of_external_ids(self) -> None:
        for identifier in (
            "dsl.stmt.return",
            "vendor.op.and",
            "gpu.async",
            "dsl.import",
            "dsl.lit.None",
        ):
            with self.subTest(identifier=identifier):
                self.assertEqual(
                    ExternalDefinitionsBuilder()
                    .add_kind(identifier, "model.value")
                    .build()
                    .index.get(identifier)
                    .id,
                    identifier,
                )
        self.assertEqual(
            ExternalDefinitionsBuilder()
            .add_structure("dsl.layout.return", ())
            .add_feature("dsl.flag.None", ("model.value",))
            .build()
            .external_feature_ids,
            frozenset({"dsl.flag.None"}),
        )

    def test_shikumi_loader_accepts_keyword_segments(self) -> None:
        import external_keyword_ids as fixture

        from shikake.external import load_external_definitions

        defined = load_external_definitions(fixture)
        self.assertEqual(defined.index.get("dsl.stmt.return").id, "dsl.stmt.return")
        self.assertTrue(defined.index.allows_feature("dsl.stmt.return", "gpu.async"))
        self.assertEqual(defined.external_feature_ids, frozenset({"gpu.async"}))

    def test_external_id_validation_reports_actual_reason(self) -> None:
        cases = (
            ("plain", "must be dotted"),
            ("model.example", "reserved 'model.*'"),
            ("vendor.", "non-identifier segment"),
            ("vendor..x", "non-identifier segment"),
            ("vendor.2bad", "non-identifier segment"),
            ("vendor.a-b", "non-identifier segment"),
        )
        for identifier, reason in cases:
            with (
                self.subTest(identifier=identifier),
                self.assertRaisesRegex(ValueError, reason),
            ):
                ExternalDefinitionsBuilder().add_kind(identifier, "model.value").build()

    def test_qualified_external_ids_are_enforced_in_all_three_definitions(self) -> None:
        cases = (
            (lambda b: b.add_kind("model.custom", "model.value"), "Kind"),
            (lambda b: b.add_structure("unqualified", ()), "Structure"),
            (lambda b: b.add_feature("plain", ("model.value",)), "Feature"),
        )
        for add, category in cases:
            with (
                self.subTest(category=category),
                self.assertRaisesRegex(ValueError, f"external {category} ID"),
            ):
                add(ExternalDefinitionsBuilder()).build()
        with self.assertRaisesRegex(TypeError, "Feature ID must be a string"):
            ExternalDefinitionsBuilder().add_feature(123, ("model.value",))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "Kind ID must be a string"):
            (
                ExternalDefinitionsBuilder()
                .add_kind(cast(str, 123), "model.value")
                .build()
            )

    def test_feature_order_is_canonical_for_model_equality(self) -> None:
        def definitions(feature_ids: Sequence[str]) -> ExternalDefinitions:
            return (
                ExternalDefinitionsBuilder()
                .add_feature("vendor.alpha", ("model.value",))
                .add_feature("vendor.zeta", ("model.value",))
                .add_call("lib:go", "vendor.go", ("value",), features=feature_ids)
                .build()
            )

        source = "from lib import go\nx = go(1)\n"
        left = shikake.parse_source(
            source, definitions=definitions(("vendor.zeta", "vendor.alpha"))
        )
        right = shikake.parse_source(
            source, definitions=definitions(("vendor.alpha", "vendor.zeta"))
        )
        self.assertEqual(left, right)
        self.assertEqual(hash(left), hash(right))
        self.assertEqual(
            next(
                model.features for model in left.walk() if model.kind.id == "vendor.go"
            ),
            ("vendor.alpha", "vendor.zeta"),
        )

    def test_model_ref_rejects_non_models(self) -> None:
        for obj in (None, "not a model", 42):
            with (
                self.subTest(obj=obj),
                self.assertRaisesRegex(TypeError, "Model instance"),
            ):
                shikake.ModelRef(cast(shikake.Model, obj), "example.py")


if __name__ == "__main__":
    unittest.main()
