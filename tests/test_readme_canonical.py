"""Validate the example-led README canonical source and its executable samples."""

from __future__ import annotations

import ast
import contextlib
import importlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "devdocs" / "canonical_sources" / "readme" / "canonical.py"


class ReadmeCanonicalTests(unittest.TestCase):
    def test_readme_is_example_led_and_links_to_detailed_documents(self) -> None:
        text = CANONICAL.read_text(encoding="utf-8")
        tree = ast.parse(text)
        readme = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        sections = {
            node.name: node for node in readme.body if isinstance(node, ast.ClassDef)
        }
        self.assertEqual(
            tuple(sections),
            (
                "INSTALL",
                "EXAMPLE",
                "DESIGN",
                "EXTERNAL",
                "FURTHER",
                "DOCUMENTS",
                "LICENSE",
            ),
        )
        example = sections["EXAMPLE"]
        self.assertEqual(
            tuple(node.name for node in example.body if isinstance(node, ast.ClassDef)),
            ("SOURCE", "MODELING", "BINDINGS"),
        )
        for expected in (
            "`ast`",
            "`tokenize`",
            "Shikumi",
            "アルファ版",
            "破壊的変更",
            "match_generic @=",
            "load_external_definitions",
            "外部インターフェース",
            "ExternalDefinitionsBuilder",
            "may_value_use",
            "設計：構造を共有し、解釈は利用側へ",
            "型推論や識別子の詳細な追跡はしません",
            "利用側が決める",
            "docs/STATUS.md",
            "CHANGELOG.md",
            "docs/api_reference/INDEX.md",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("docs/guides/", text)
        self.assertNotIn("v0.0.3", text)
        self.assertFalse((CANONICAL.parent.parent / "guides").exists())

    def test_public_readme_keeps_design_boundary(self) -> None:
        published = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "## Design: structure without prescribed semantics",
            "No type inference or detailed identifier tracking.",
            "**Consumers decide:**",
            "**`False` does not prove absence.**",
            "Consumers needing stronger guarantees must perform additional validation.",
        ):
            self.assertIn(expected, published)

    def test_readme_source_is_valid_and_examples_run(self) -> None:
        from shikumi_devdoc.context import Context
        from shikumi_devdoc.norms.document import system as document
        from shikumi_devdoc.realizers.document import MarkdownRealizer

        canonical_module = importlib.import_module(
            "devdocs.canonical_sources.readme.canonical"
        )
        validated = document.validate(canonical_module, placement=())
        self.assertTrue(validated.is_valid, validated.diagnostics)
        checked = MarkdownRealizer(
            Context({"project": {"name": "shikake", "import_name": "shikake"}})
        ).check(validated.view)
        self.assertTrue(checked.is_realizable, checked.diagnostics)

        tree = ast.parse(CANONICAL.read_text(encoding="utf-8"))
        readme = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        example = next(
            node
            for node in readme.body
            if isinstance(node, ast.ClassDef) and node.name == "EXAMPLE"
        )
        blocks: list[str] = []
        for section in example.body:
            if not isinstance(section, ast.ClassDef):
                continue
            body = ast.get_docstring(section)
            assert body is not None
            blocks.extend(re.findall(r"```python\n(.*?)\n```", body, re.DOTALL))
        self.assertEqual(len(blocks), 3)

        namespace: dict[str, object] = {}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            for block in blocks:
                exec(compile(block, "<readme-example>", "exec"), namespace)  # noqa: S102
        assert isinstance(namespace["source"], str)
        self.assertIn("class Accumulator", namespace["source"])
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "model.definition.class: 1",
                "model.definition.function: 1",
                "demo.type.int32: 6",
                "demo.type.vector: 2",
                "demo.operation.clamp: 1",
                "Int32 BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)",
                "clamp BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)",
                "total BindingState(introduction='stable', may_rebind=True, may_delete=False, may_value_use=True)",
            ],
        )

    def test_shikumi_declaration_example_models_same_source(self) -> None:
        tree = ast.parse(CANONICAL.read_text(encoding="utf-8"))
        readme = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        example = next(
            node
            for node in readme.body
            if isinstance(node, ast.ClassDef) and node.name == "EXAMPLE"
        )
        external = next(
            node
            for node in readme.body
            if isinstance(node, ast.ClassDef) and node.name == "EXTERNAL"
        )
        source_node = next(
            node
            for node in example.body
            if isinstance(node, ast.ClassDef) and node.name == "SOURCE"
        )
        declarations_node = next(
            node
            for node in external.body
            if isinstance(node, ast.ClassDef) and node.name == "DECLARATIONS"
        )
        loading_node = next(
            node
            for node in external.body
            if isinstance(node, ast.ClassDef) and node.name == "LOADING"
        )

        def snippet(node: ast.ClassDef) -> str:
            body = ast.get_docstring(node)
            assert body is not None
            snippets = re.findall(r"```python\n(.*?)\n```", body, re.DOTALL)
            self.assertEqual(len(snippets), 1)
            return snippets[0]

        with tempfile.TemporaryDirectory(prefix="shikake-readme-") as directory:
            Path(directory, "trusted_definitions.py").write_text(
                snippet(declarations_node), encoding="utf-8"
            )
            sys.path.insert(0, directory)
            namespace: dict[str, object] = {}
            try:
                exec(  # noqa: S102
                    compile(snippet(source_node), "<readme-source>", "exec"), namespace
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exec(  # noqa: S102
                        compile(snippet(loading_node), "<readme-loading>", "exec"),
                        namespace,
                    )
                self.assertEqual(output.getvalue().splitlines(), ["1"])
                definitions = namespace["definitions"]
                self.assertEqual(len(definitions.type_mappings), 1)  # type: ignore[attr-defined]
                self.assertEqual(len(definitions.generic_mappings), 1)  # type: ignore[attr-defined]
                self.assertEqual(len(definitions.mappings), 1)  # type: ignore[attr-defined]
            finally:
                sys.path.remove(directory)
                sys.modules.pop("trusted_definitions", None)


if __name__ == "__main__":
    unittest.main()
