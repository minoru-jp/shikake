"""Public-documentation source layout and reference policy, before translation."""

from __future__ import annotations

import ast
import importlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "devdocs" / "canonical_sources"
EXPECTED_PUBLIC = {
    "README.md",
    "CHANGELOG.md",
    "docs/STATUS.md",
    "docs/DOCUMENTATION_POLICY.md",
    "docs/api_reference/INDEX.md",
    "docs/api_reference/public.md",
    "docs/api_reference/external.md",
}


def _canonical_text(relative_path: str) -> str:
    return (SOURCES / relative_path).read_text(encoding="utf-8")


class DocumentationPolicyCanonicalTests(unittest.TestCase):
    def test_policy_source_is_valid_and_renderable_without_writing_markdown(
        self,
    ) -> None:
        from shikumi_devdoc.context import Context
        from shikumi_devdoc.norms.document import system as document
        from shikumi_devdoc.realizers.document import MarkdownRealizer

        module = importlib.import_module(
            "devdocs.canonical_sources.documentation_policy.canonical"
        )
        validated = document.validate(module, placement=())
        self.assertTrue(validated.is_valid, validated.diagnostics)
        checked = MarkdownRealizer(Context({"project": {"name": "shikake"}})).check(
            validated.view
        )
        self.assertTrue(checked.is_realizable, checked.diagnostics)
        text = _canonical_text("documentation_policy/canonical.py")
        for expected in (
            "devdocs/canonical_sources/",
            "docs/STATUS.md",
            "docs/api_reference/",
            "docs/DOCUMENTATION_POLICY.md",
            "devdocs/canonical_documents/",
            "sdist",
            "PyPI",
        ):
            self.assertIn(expected, text)

    def test_public_sources_do_not_link_to_withdrawn_markdown(self) -> None:
        readme = _canonical_text("readme/canonical.py")
        status = _canonical_text("status/canonical.py")
        self.assertFalse((SOURCES / "guides").exists())
        self.assertNotIn("docs/specification/", readme + status)
        self.assertNotIn("MODELING_POLICY.md)", readme + status)
        self.assertNotIn("(STATUS.md)", readme)

        # The Japanese sources describe GitHub-relative destinations; the
        # published root README will require verified absolute URLs for PyPI.
        readme_links = set(re.findall(r"\]\(([^)]+)\)", readme))
        self.assertEqual(
            readme_links,
            {
                "docs/STATUS.md",
                "CHANGELOG.md",
                "docs/api_reference/INDEX.md",
                "docs/api_reference/external.md",
                "docs/DOCUMENTATION_POLICY.md",
                "LICENSE",
            },
        )
        self.assertTrue({"README.md", *readme_links} <= EXPECTED_PUBLIC | {"LICENSE"})
        status_links = set(re.findall(r"\]\(([^)]+)\)", status))
        self.assertEqual(
            status_links, {"../devdocs/canonical_sources/specification/layouts.py"}
        )
        for link in status_links:
            self.assertTrue((ROOT / "docs" / link).resolve().is_file(), link)

    def test_public_document_paths_and_single_source_labels(self) -> None:
        paths = {
            "readme/canonical.py": ("README.md", "README"),
            "changelog/canonical.py": ("CHANGELOG.md", "CHANGELOG"),
            "status/canonical.py": ("STATUS.md", "STATUS"),
            "documentation_policy/canonical.py": (
                "DOCUMENTATION_POLICY.md",
                "DOCUMENTATION_POLICY",
            ),
            "api_reference/public.py": ("public.md", "PUBLIC_API"),
            "api_reference/external.py": ("external.md", "EXTERNAL_API"),
        }
        for path, (filename, name) in paths.items():
            with self.subTest(path=path):
                tree = ast.parse(_canonical_text(path))
                root = next(n for n in tree.body if isinstance(n, ast.ClassDef))
                self.assertEqual(root.name, name)
                decorator = next(
                    n
                    for n in root.decorator_list
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "canonical_source"
                )
                field = next(
                    kw.value for kw in decorator.keywords if kw.arg == "filename"
                )
                assert isinstance(field, ast.Constant)
                self.assertEqual(field.value, filename)


if __name__ == "__main__":
    unittest.main()
