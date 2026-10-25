"""Regressions for the public result types and their canonical API contracts."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from typing import Literal, get_args, get_type_hints

import shikake
from shikake import external
from shikake._mica.base_references import OverrideCandidate


class ApiFeedbackContractTests(unittest.TestCase):
    def test_feature_is_exported_and_matches_index_results(self) -> None:
        self.assertIn("Feature", shikake.__all__)
        feature = shikake.definition_index().all_features()[0]
        self.assertIsInstance(feature, shikake.Feature)
        self.assertEqual(shikake.Feature.__module__, "shikake._mica.kinds.index")

    def test_call_mapping_is_declared_export(self) -> None:
        self.assertIn("CallMapping", external.__all__)
        mapping = external.CallMapping(
            external.ImportedCall("lib.api:Client.call"), "k", ()
        )
        self.assertIsInstance(mapping, external.CallMapping)
        self.assertEqual(mapping.kind_id, "k")

    def test_inspection_proxies_match_complete_and_incomplete_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "mypkg"
            directory.mkdir()
            (directory / "code.py").write_text(
                "class Base:\n    def f(self): pass\n"
                "class Derived(Base):\n    def f(self): pass\n",
                encoding="utf-8",
            )
            complete = shikake.inspect_package(directory)
            self.assertTrue(complete.complete)
            self.assertTrue(complete.name_bindings)
            for prop in (
                "model",
                "override_candidates",
                "base_references",
                "analyses",
                "name_bindings",
            ):
                self.assertIs(getattr(complete, prop), getattr(complete.package, prop))
            self.assertEqual(len(complete.override_candidates), 1)
            self.assertEqual(len(complete.base_references), 1)
            self.assertEqual(complete.analyses, frozenset({"override", "inheritance"}))

            (directory / "bad.py").write_text("def broken(:\n", encoding="utf-8")
            incomplete = shikake.inspect_package(directory)
            self.assertFalse(incomplete.complete)
            self.assertTrue(incomplete.model.get_nodes("modules"))
            self.assertEqual(incomplete.override_candidates, ())
            self.assertEqual(incomplete.base_references, ())
            self.assertEqual(incomplete.analyses, frozenset())
            self.assertEqual(incomplete.name_bindings, ())
            self.assertIs(incomplete.name_bindings, incomplete.package.name_bindings)

    def test_evidence_literal_matches_generated_categories(self) -> None:
        evidence_type = get_type_hints(OverrideCandidate)["evidence"]
        self.assertEqual(
            set(get_args(evidence_type)),
            {
                "direct_base_and_same_method_name",
                "ancestor_and_same_method_name",
            },
        )
        self.assertEqual(evidence_type.__origin__, Literal)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "mypkg"
            directory.mkdir()
            (directory / "module.py").write_text(
                "class A:\n    def f(self): pass\n"
                "class B(A):\n    pass\n"
                "class C(B):\n    def f(self): pass\n"
                "class D(A):\n    def f(self): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(directory)
            evidence = {candidate.evidence for candidate in result.override_candidates}
            self.assertEqual(evidence, set(get_args(evidence_type)))

    def test_canonical_model_and_api_contracts(self) -> None:
        docs = Path(__file__).resolve().parents[1] / "devdocs" / "canonical_sources"
        api = ast.parse(
            (docs / "api_reference" / "public.py").read_text(encoding="utf-8")
        )
        root = next(node for node in api.body if isinstance(node, ast.ClassDef))
        subjects = {
            node.name: node for node in root.body if isinstance(node, ast.ClassDef)
        }
        model_api = subjects["API_006"]
        self.assertFalse(
            any(
                isinstance(statement, ast.AugAssign)
                and isinstance(statement.target, ast.Name)
                and statement.target.id == "input"
                for statement in model_api.body
            ),
            "Model(...) constructor arguments must not be documented as supported inputs",
        )
        self.assertIn(
            "SPEC_021",
            (docs / "specification" / "model.py").read_text(encoding="utf-8"),
        )
        for member in (
            "PackageInspection.model",
            "PackageInspection.override_candidates",
            "PackageInspection.base_references",
            "PackageInspection.analyses",
            "PackageInspection.name_bindings",
        ):
            self.assertIn(
                f'"shikake.{member}"',
                (docs / "api_reference" / "public.py").read_text(encoding="utf-8"),
            )
        self.assertIn(
            '"shikake.external.CallMapping"',
            (docs / "api_reference" / "external.py").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
