"""Validate published-document layout, links, and distribution metadata."""

from __future__ import annotations

import ast
import re
import tomllib
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PUBLIC = {
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    DOCS / "STATUS.md",
    DOCS / "DOCUMENTATION_POLICY.md",
    DOCS / "api_reference" / "INDEX.md",
    DOCS / "api_reference" / "public.md",
    DOCS / "api_reference" / "external.md",
}


class PublicDocumentationTests(unittest.TestCase):
    def test_only_expected_public_documents_and_no_retained_canonical_render(
        self,
    ) -> None:
        self.assertEqual(
            {ROOT / "README.md", ROOT / "CHANGELOG.md", *DOCS.rglob("*.md")}, PUBLIC
        )
        self.assertFalse((ROOT / "devdocs" / "canonical_documents").exists())
        for doc in PUBLIC:
            text = doc.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# "), doc)
            self.assertIsNone(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text), doc)
        self.assertIn('readme = "README.md"', (ROOT / "pyproject.toml").read_text())
        self.assertIn(
            "Development Status :: 3 - Alpha", (ROOT / "pyproject.toml").read_text()
        )
        manifest = (ROOT / "MANIFEST.in").read_text()
        self.assertIn("graft docs", manifest)
        self.assertIn("graft devdocs", manifest)
        self.assertIn("prune devdocs/canonical_documents", manifest)

    def test_pypi_readme_links_are_absolute_and_point_to_repository_files(
        self,
    ) -> None:
        base = "https://github.com/minoru-jp/shikake/blob/HEAD/"
        urls = re.findall(r"\]\(([^)]+)\)", (ROOT / "README.md").read_text())
        self.assertGreaterEqual(len(urls), 8)
        for url in urls:
            with self.subTest(url=url):
                self.assertTrue(url.startswith(base), url)
                relative = unquote(
                    urlparse(url).path.removeprefix("/minoru-jp/shikake/blob/HEAD/")
                )
                self.assertTrue((ROOT / relative).is_file(), url)

    def test_distribution_metadata_points_to_repository_and_docs(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        self.assertEqual(
            project["urls"]["Homepage"], "https://github.com/minoru-jp/shikake"
        )
        self.assertEqual(
            project["urls"]["Repository"], "https://github.com/minoru-jp/shikake"
        )
        self.assertEqual(
            project["urls"]["Documentation"],
            "https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md",
        )
        self.assertTrue(
            {"python-ast", "static-analysis", "transpilation"}
            <= set(project["keywords"])
        )
        self.assertEqual(project["readme"], "README.md")

    def test_ci_matrix_pull_requests_and_release_gate(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        if not workflows.is_dir():
            self.skipTest("GitHub workflows are not included in the sdist")
        ci = (workflows / "ci.yml").read_text()
        checks = (workflows / "checks.yml").read_text()
        release = (workflows / "release.yml").read_text()
        self.assertIn("  pull_request:", ci)
        self.assertIn("  workflow_dispatch:", ci)
        self.assertIn("uses: ./.github/workflows/checks.yml", ci)
        for version in ("'3.11'", "'3.12'", "'3.13'", "'3.14'", "'3.15'"):
            self.assertIn(version, checks)
        self.assertIn("make check", checks)
        self.assertIn("python -m build --sdist", checks)
        self.assertIn("python -m twine check --strict dist/*.tar.gz", checks)
        self.assertIn("needs: checks", release)
        self.assertIn("needs: build", release)
        # Publishing must not be triggered by a push, tag, or GitHub Release.
        self.assertIn("  workflow_dispatch:", release)
        self.assertNotIn("  release:", release)
        self.assertNotIn("  push:", release)
        self.assertIn(
            "DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}", release
        )
        self.assertIn("cancel-in-progress: false", release)
        self.assertIn("id-token: write", release)
        self.assertIn("needs: [prepare, build, publish]", release)
        self.assertIn("contents: write", release)
        self.assertIn('git push origin "refs/tags/${RELEASE_TAG}"', release)
        self.assertIn('gh release create "$RELEASE_TAG"', release)
        self.assertIn("--verify-tag", release)
        self.assertLess(release.index("  publish:"), release.index("  github_release:"))
        self.assertNotIn("skip-existing", release)

    def test_all_local_document_links_have_targets(self) -> None:
        count = 0
        for document in PUBLIC:
            text = document.read_text(encoding="utf-8")
            for url in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in url:
                    continue
                path, _, fragment = url.partition("#")
                target = document.parent / path if path else document
                self.assertTrue(target.is_file(), (document, url))
                if fragment and target == document:
                    headings = re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE)
                    anchors = {
                        re.sub(r"[^a-z0-9_-]", "", heading.lower().replace(" ", "-"))
                        for heading in headings
                    }
                    self.assertIn(fragment, anchors, (document, url))
                if url.endswith(".md"):
                    self.assertNotIn("/specification/", url)
                count += 1
        self.assertGreater(count, 50)

    def test_api_index_is_derived_from_public_api_pages(self) -> None:
        from devdocs.build_api_index import render_index

        self.assertEqual(
            (DOCS / "api_reference" / "INDEX.md").read_text(encoding="utf-8"),
            render_index(),
        )

    def test_specification_links_have_existing_rule_ids(self) -> None:
        for doc in (
            DOCS / "api_reference" / "public.md",
            DOCS / "api_reference" / "external.md",
        ):
            text = doc.read_text(encoding="utf-8")
            refs = re.findall(
                r"\[([A-Z_]+\.SPEC_\d{3})\]\((\.\./\.\./devdocs/canonical_sources/specification/[^)]+\.py)\)",
                text,
            )
            self.assertGreater(len(refs), 10, doc)
            for identity, relative in refs:
                source = (doc.parent / relative).resolve()
                self.assertTrue(source.is_file(), identity)
                prefix, spec = identity.split(".")
                self.assertEqual(source.stem.upper(), prefix)
                tree = ast.parse(source.read_text(encoding="utf-8"))
                root = next(n for n in tree.body if isinstance(n, ast.ClassDef))
                self.assertTrue(
                    any(
                        isinstance(n, ast.ClassDef) and n.name == spec
                        for n in root.body
                    ),
                    identity,
                )


if __name__ == "__main__":
    unittest.main()
