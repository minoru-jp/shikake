"""Phase 6: API subjects must reference precise normative contracts."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[1] / "devdocs" / "canonical_sources"


def subjects(path: Path) -> dict[str, ast.ClassDef]:
    root = next(
        node
        for node in ast.parse(path.read_text(encoding="utf-8")).body
        if isinstance(node, ast.ClassDef)
    )
    return {node.name: node for node in root.body if isinstance(node, ast.ClassDef)}


def related(node: ast.ClassDef) -> set[str]:
    field = next(
        item
        for item in node.body
        if isinstance(item, ast.AugAssign)
        and isinstance(item.target, ast.Name)
        and item.target.id == "related"
    )
    assert isinstance(field.value, ast.Tuple)
    return {ast.unparse(item) for item in field.value.elts}


class Phase6ReferenceTests(unittest.TestCase):
    def test_public_api_points_to_the_contract_it_exposes(self) -> None:
        """Avoid linking specific methods only to a topic's general rule."""
        api = subjects(CANONICAL / "api_reference" / "public.py")
        expectations = {
            "API_002": {"PARSING.SPEC_015", "PARSING.SPEC_016"},
            "API_004": {"PARSING.SPEC_017", "PARSING.SPEC_018"},
            "API_015": {"BINDING.SPEC_002", "BINDING.SPEC_003", "BINDING.SPEC_004"},
            "API_016": {"BINDING.SPEC_014"},
            "API_018": {"PARSING.SPEC_017"},
            "API_029": {"MODEL.SPEC_017"},
            "API_031": {"MODEL.SPEC_017"},
            "API_033": {"MODEL.SPEC_017"},
            "API_038": {"BINDING.SPEC_014"},
            "API_041": {"MODEL.SPEC_008"},
            "API_042": {"PARSING.SPEC_013"},
            "API_043": {"PARSING.SPEC_013"},
        }
        for identity, must_include in expectations.items():
            with self.subTest(subject=identity):
                self.assertLessEqual(must_include, related(api[identity]))

    def test_ast_kind_mappings_remain_structured_details(self) -> None:
        """Detailed correspondence is a table of AST/Kind facts, not free prose."""
        for file, identities in (
            (
                "expressions.py",
                ("SPEC_015", "SPEC_016", "SPEC_023", "SPEC_024", "SPEC_026"),
            ),
            (
                "statements.py",
                ("SPEC_022", "SPEC_023", "SPEC_029", "SPEC_030", "SPEC_031"),
            ),
        ):
            rules = subjects(CANONICAL / "specification" / file)
            for identity in identities:
                with self.subTest(file=file, identity=identity):
                    node = rules[identity]
                    self.assertTrue(ast.get_docstring(node))
                    details = [
                        item
                        for item in node.body
                        if isinstance(item, ast.AugAssign)
                        and isinstance(item.target, ast.Name)
                        and item.target.id == "detail"
                    ]
                    self.assertTrue(details)
                    self.assertTrue(
                        all("AST:" in ast.unparse(item.value) for item in details)
                    )
                    self.assertTrue(
                        any(ref.startswith("LAYOUTS.") for ref in related(node))
                    )


if __name__ == "__main__":
    unittest.main()
