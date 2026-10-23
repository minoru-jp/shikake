"""The README canonical source replaces the two application-specific guides."""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path

import shikake

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "devdocs" / "canonical_sources"


class ReadmeCanonicalTests(unittest.TestCase):
    def test_readme_contains_shared_concepts_and_no_legacy_guides(self) -> None:
        path = CANONICAL / "readme" / "canonical.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        readme = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        sections = {
            node.name: node for node in readme.body if isinstance(node, ast.ClassDef)
        }
        self.assertEqual(
            tuple(sections),
            (
                "ALPHA",
                "CONCEPTS",
                "INSTALL",
                "QUICK_START",
                "EXTERNAL",
                "APPLICATIONS",
                "LIMITATIONS",
                "DOCUMENTS",
                "LICENSE",
            ),
        )
        self.assertIn(
            "予告なく破壊的な変更", ast.get_docstring(sections["ALPHA"]) or ""
        )
        self.assertIn("MIT License", ast.get_docstring(sections["LICENSE"]) or "")
        self.assertIn("外部構造", ast.get_docstring(sections["EXTERNAL"]) or "")
        self.assertIn("Strict解析", source)
        self.assertIn("Partial解析", source)
        self.assertIn("may_rebind", source)
        self.assertIn("may_delete", source)
        self.assertNotIn("docs/guides/", source)
        self.assertFalse((CANONICAL / "guides").exists())

    def test_readme_sample_and_source_are_valid_without_rendering(self) -> None:
        from shikumi_devdoc.context import Context
        from shikumi_devdoc.norms.document import system as document
        from shikumi_devdoc.realizers.document import MarkdownRealizer

        canonical_module = importlib.import_module(
            "devdocs.canonical_sources.readme.canonical"
        )
        validated = document.validate(canonical_module, placement=())
        self.assertTrue(validated.is_valid, validated.diagnostics)
        checked = MarkdownRealizer(
            Context(
                {
                    "project": {
                        "name": "shikake",
                        "import_name": "shikake",
                        "requires_python": ">=3.11",
                    }
                }
            )
        ).check(validated.view)
        self.assertTrue(checked.is_realizable, checked.diagnostics)

        tree = ast.parse((CANONICAL / "readme" / "canonical.py").read_text())
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        quick = next(
            node
            for node in root.body
            if isinstance(node, ast.ClassDef) and node.name == "QUICK_START"
        )
        prose = ast.get_docstring(quick)
        assert prose is not None
        sample = prose.split("```python\n", 1)[1].split("\n```", 1)[0]
        sample = sample.replace("{{project.import_name}}", "shikake")
        sample_tree = ast.parse(sample)
        source_value = next(
            node.value
            for node in sample_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "source"
                for target in node.targets
            )
        )
        assert isinstance(source_value, ast.Constant)
        assert isinstance(source_value.value, str)
        parsed = shikake.parse_source(source_value.value)
        self.assertIsInstance(parsed, shikake.Model)
        self.assertGreater(sum(1 for _ in parsed.walk()), 20)


if __name__ == "__main__":
    unittest.main()
