"""Check supported API behavior and run usage examples from either language."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import shikake

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "api_reference"
CANONICAL = ROOT / "devdocs" / "canonical_sources"


def _code_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)


class PublicApiUsageExampleTests(unittest.TestCase):
    def test_analysis_selection_contract_is_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "example"
            package.mkdir()
            (package / "module.py").write_text(
                "class Base:\n    def action(self): pass\n"
                "class Child(Base):\n    def action(self): pass\n",
                encoding="utf-8",
            )
            cases = (
                (None, {"inheritance", "override"}),
                ({"inheritance"}, {"inheritance"}),
                ({"override"}, {"inheritance", "override"}),
                ({"inheritance", "override"}, {"inheritance", "override"}),
                (set(), set()),
            )
            for analyses, expected in cases:
                for inspect in (False, True):
                    with self.subTest(analyses=analyses, partial=inspect):
                        result = (
                            shikake.inspect_package(package, analyses=analyses)
                            if inspect
                            else shikake.parse_package(package, analyses=analyses)
                        )
                        self.assertEqual(result.analyses, frozenset(expected))
                        self.assertTrue(result.name_bindings)
            for parser in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaises(TypeError):
                    parser(package, analyses="override")
                with self.assertRaises(TypeError):
                    parser(package, analyses="")
                with self.assertRaises(ValueError):
                    parser(package, analyses={"unknown"})

    def test_external_working_examples_are_runnable(self) -> None:
        published = (DOCS / "external.md").read_text(encoding="utf-8")
        tree = ast.parse(
            (CANONICAL / "api_reference" / "external.py").read_text(encoding="utf-8")
        )
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        loader = next(
            node
            for node in root.body
            if isinstance(node, ast.ClassDef) and node.name == "API_004"
        )
        example = next(
            node
            for node in loader.body
            if isinstance(node, ast.ClassDef) and node.name == "EXAMPLE"
        )
        japanese = ast.get_docstring(example)
        self.assertIsNotNone(japanese)
        if japanese is None:
            return
        published_code = _code_blocks(published)
        canonical_code = _code_blocks(japanese)
        self.assertEqual(len(published_code), 3)
        self.assertEqual(len(canonical_code), 2)
        for code in (*canonical_code, *published_code):
            ast.parse(code)
        for language, snippets in (("ja", canonical_code), ("en", published_code[:2])):
            with (
                self.subTest(language=language),
                tempfile.TemporaryDirectory() as temp,
            ):
                work = Path(temp)
                for filename, code in zip(
                    ("memory_definitions.py", "example.py"), snippets
                ):
                    (work / filename).write_text(code + "\n", encoding="utf-8")
                env = os.environ.copy()
                env["PYTHONPATH"] = os.pathsep.join(
                    (str(ROOT / "src"), env.get("PYTHONPATH", ""))
                )
                result = subprocess.run(
                    [sys.executable, "example.py"],
                    cwd=work,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "64\n")

    def test_programmatic_builder_example_is_published_and_runnable(self) -> None:
        published = (DOCS / "external.md").read_text(encoding="utf-8")
        source = (CANONICAL / "api_reference" / "external.py").read_text(
            encoding="utf-8"
        )
        english = _code_blocks(published)[2]
        tree = ast.parse(source)
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        builder = next(
            node
            for node in root.body
            if isinstance(node, ast.ClassDef) and node.name == "API_015"
        )
        example = next(
            node
            for node in builder.body
            if isinstance(node, ast.ClassDef) and node.name == "EXAMPLE"
        )
        japanese = ast.get_docstring(example)
        self.assertIsNotNone(japanese)
        if japanese is None:
            return
        japanese_match = re.search(r"```python\n(.*?)\n\s*```", japanese, re.DOTALL)
        self.assertIsNotNone(japanese_match)
        if japanese_match is None:
            return
        japanese_code = textwrap.dedent(japanese_match.group(1))
        for language, code in (("ja", japanese_code), ("en", english)):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as temp:
                ast.parse(code)
                file = Path(temp) / "builder_example.py"
                file.write_text(code + "\n", encoding="utf-8")
                env = os.environ.copy()
                env["PYTHONPATH"] = os.pathsep.join(
                    (str(ROOT / "src"), env.get("PYTHONPATH", ""))
                )
                result = subprocess.run(
                    [sys.executable, str(file)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "64\n")


if __name__ == "__main__":
    unittest.main()
