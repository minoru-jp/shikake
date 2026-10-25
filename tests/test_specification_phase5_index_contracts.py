"""Executable contracts retained in the phase-5 legacy specification audit."""

from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

import shikake

SPEC = Path(__file__).resolve().parents[1] / "devdocs/canonical_sources/specification"


class SpecificationPhase5IndexContractsTests(unittest.TestCase):
    def test_new_rules_have_stable_identity(self) -> None:
        tree = ast.parse((SPEC / "model.py").read_text(encoding="utf-8"))
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        rules = {
            node.name: node for node in root.body if isinstance(node, ast.ClassDef)
        }
        for identity, required in {
            "SPEC_017": ("KeyError", "ValueError", "require_structure"),
            "SPEC_018": ("重複", "validate_features"),
            "SPEC_019": ("UTF-8", "SourceSpan"),
            "SPEC_020": ("definition_index()", "Index"),
        }.items():
            with self.subTest(rule=identity):
                node = rules[identity]
                body = ast.get_docstring(node) or ""
                for token in required:
                    self.assertIn(token, body)
                fields = {
                    field.target.id
                    for field in node.body
                    if isinstance(field, ast.AugAssign)
                    and isinstance(field.target, ast.Name)
                    and isinstance(field.op, ast.MatMult)
                }
                self.assertTrue({"title", "level"} <= fields)

    def test_definition_index_lookups_have_distinct_absence_semantics(self) -> None:
        index = shikake.definition_index()
        self.assertIsNone(index.parent("model"))
        self.assertTrue(index.classified_under("model", "model"))
        self.assertIsNone(index.structure_of("model"))
        with self.assertRaises(ValueError):
            index.require_structure("model")
        with self.assertRaises(KeyError):
            index.get("not.registered")
        with self.assertRaises(KeyError):
            index.get_structure("not.registered")
        with self.assertRaises(KeyError):
            index.classified_under("model", "not.registered")
        self.assertEqual(
            index.require_structure("model.value.named"),
            index.structure_of("model.value.named"),
        )

    def test_feature_validation_rejects_unknown_duplicate_and_inapplicable(
        self,
    ) -> None:
        index = shikake.definition_index()
        index.validate_features("model.definition.function", ("async",))
        with self.assertRaises(ValueError):
            index.validate_features("model.definition.function", ("async", "async"))
        with self.assertRaises(ValueError):
            index.validate_features("model.definition.function", ("not.registered",))
        with self.assertRaises(ValueError):
            index.validate_features("model.value.named", ("async",))

    def test_ast_source_span_uses_utf8_byte_columns(self) -> None:
        module = shikake.parse_source("あ = 1\n")
        assignment = module.get_nodes("body")[0]
        name = assignment.get_nodes("targets")[0]
        self.assertEqual(name.span, shikake.SourceSpan(1, 0, 1, 3))
        self.assertEqual(assignment.span, shikake.SourceSpan(1, 0, 1, 7))
        self.assertIsNone(module.span)

    def test_validated_index_reuse_and_public_value_immutability(self) -> None:
        first = shikake.definition_index()
        self.assertIs(first, shikake.definition_index())
        kind = first.get("model")
        with self.assertRaises(FrozenInstanceError):
            kind.id = "changed"  # type: ignore[misc]
        structure = first.require_structure("model.value.named")
        with self.assertRaises(FrozenInstanceError):
            structure.id = "changed"  # type: ignore[misc]
        feature = first.all_features()[0]
        with self.assertRaises(FrozenInstanceError):
            feature.id = "changed"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
