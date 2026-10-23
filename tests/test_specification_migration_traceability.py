"""Structural traceability of the rebuilt normative specification.

Legacy topics are a review checklist, not a claim that every legacy sentence is
normative or that topic-level coverage proves semantic equivalence.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[1] / "devdocs" / "canonical_sources"
SPEC = CANONICAL / "specification"
API = CANONICAL / "api_reference"

# Source names of the 21 former specification documents. Each entry names a
# representative normative contract in the new specification. A topic can be
# covered by further rules; this is deliberately NOT a sentence-by-sentence
# equivalence certificate.
LEGACY_TOPIC_TO_RULE = {
    "assignment_structures.py": "STATEMENTS.SPEC_001",
    "async_modeling.py": "STATEMENTS.SPEC_012",
    "context_comprehensions.py": "EXPRESSIONS.SPEC_008",
    "control_flow_modeling.py": "STATEMENTS.SPEC_004",
    "extensions.py": "MODEL.SPEC_012",
    "function_class_modeling.py": "STATEMENTS.SPEC_009",
    "generator_modeling.py": "STATEMENTS.SPEC_016",
    "kind_index.py": "MODEL.SPEC_016",
    "kind_structure_architecture.py": "MODEL.SPEC_004",
    "model.py": "MODEL.SPEC_001",
    "model_structure.py": "MODEL.SPEC_007",
    "operation_modeling.py": "EXPRESSIONS.SPEC_004",
    "package_modeling.py": "PARSING.SPEC_002",
    "partial_modeling.py": "PARSING.SPEC_007",
    "reference_resolution.py": "RELATIONS.SPEC_001",
    "remaining_statement_forms.py": "STATEMENTS.SPEC_031",
    "scope.py": "BINDING.SPEC_001",
    "source_ingestion.py": "PARSING.SPEC_003",
    "special_statements.py": "STATEMENTS.SPEC_014",
    "structural_placements.py": "STATEMENTS.SPEC_011",
    "value_expressions.py": "EXPRESSIONS.SPEC_002",
}


def read_rules() -> dict[str, tuple[ast.ClassDef, str]]:
    """Extract identities and rule docstrings without running any source."""
    out: dict[str, tuple[ast.ClassDef, str]] = {}
    for path in sorted(SPEC.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        roots = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        if len(roots) != 1:
            raise AssertionError(f"expected exactly one specification root: {path}")
        root = roots[0]
        for node in root.body:
            if not isinstance(node, ast.ClassDef):
                continue
            identity = f"{root.name}.{node.name}"
            if identity in out:
                raise AssertionError(f"duplicate rule identity: {identity}")
            out[identity] = (node, ast.get_docstring(node) or "")
    return out


def references(node: ast.ClassDef) -> tuple[str, ...]:
    """Extract referenced spec identities from the standard related field."""
    targets: list[str] = []
    for field in node.body:
        if not (
            isinstance(field, ast.AugAssign)
            and isinstance(field.target, ast.Name)
            and field.target.id == "related"
        ):
            continue
        if not isinstance(field.value, ast.Tuple):
            raise TypeError("related must be a tuple")
        for item in field.value.elts:
            if isinstance(item, ast.Name):
                # References to independent policy documents are intentional.
                continue
            if not (
                isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name)
            ):
                raise TypeError(f"unexpected related expression: {ast.dump(item)}")
            targets.append(f"{item.value.id}.{item.attr}")
    return tuple(targets)


class SpecificationMigrationTraceability(unittest.TestCase):
    def test_all_21_legacy_topics_have_representative_normative_rules(self) -> None:
        rules = read_rules()
        self.assertEqual(len(LEGACY_TOPIC_TO_RULE), 21)
        self.assertEqual(len(set(LEGACY_TOPIC_TO_RULE)), 21)
        for legacy_filename, rule in LEGACY_TOPIC_TO_RULE.items():
            with self.subTest(legacy=legacy_filename):
                self.assertIn(rule, rules)
                self.assertTrue(rules[rule][1])
                if legacy_filename != "model.py":
                    self.assertFalse((SPEC / legacy_filename).exists())

    def test_specification_rules_are_normative_and_related_graph_is_acyclic(
        self,
    ) -> None:
        rules = read_rules()
        self.assertGreaterEqual(len(rules), 200)
        graph: dict[str, tuple[str, ...]] = {}
        edges = 0
        for identity, (node, docstring) in rules.items():
            self.assertRegex(identity, r"^[A-Z_]+\.SPEC_\d{3}$")
            self.assertTrue(docstring, identity)
            fields = {
                field.target.id: field
                for field in node.body
                if isinstance(field, ast.AugAssign)
                and isinstance(field.target, ast.Name)
            }
            self.assertIn("title", fields, identity)
            self.assertIn("level", fields, identity)
            level = fields["level"].value
            self.assertIsInstance(level, ast.Name)
            assert isinstance(level, ast.Name)
            self.assertIn(
                level.id,
                {"MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY", "INFORMATIVE"},
            )
            links = references(node)
            self.assertEqual(len(links), len(set(links)), identity)
            for target in links:
                self.assertIn(target, rules, f"{identity} -> {target}")
            self.assertNotIn(identity, links)
            graph[identity] = links
            edges += len(links)
        self.assertGreaterEqual(edges, 200)
        visited: set[str] = set()
        active: set[str] = set()

        def visit(identity: str) -> None:
            if identity in active:
                raise AssertionError(
                    f"circular normative reference involving {identity}"
                )
            if identity in visited:
                return
            active.add(identity)
            for child in graph[identity]:
                visit(child)
            active.remove(identity)
            visited.add(identity)

        for identity in sorted(graph):
            visit(identity)

    def test_api_subject_links_point_to_existing_specification_rules(self) -> None:
        rules = read_rules()
        checked = 0
        for path in sorted(API.glob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            roots = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            self.assertEqual(len(roots), 1)
            for subject in roots[0].body:
                if not isinstance(subject, ast.ClassDef):
                    continue
                self.assertTrue(re.fullmatch(r"API_\d{3}", subject.name))
                links = references(subject)
                self.assertTrue(links, f"{path.name}:{subject.name}")
                for ref in links:
                    self.assertIn(ref, rules, f"{path.name}:{subject.name}")
                checked += 1
        self.assertGreaterEqual(checked, 57)


if __name__ == "__main__":
    unittest.main()
