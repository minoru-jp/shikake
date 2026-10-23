"""Review regressions: closed normative lists and analysis-name input types."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

import shikake

SPECS = (
    Path(__file__).resolve().parents[1]
    / "devdocs"
    / "canonical_sources"
    / "specification"
)


def _rule(filename: str, name: str) -> str:
    tree = ast.parse((SPECS / filename).read_text(encoding="utf-8"))
    root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    rule = next(
        node
        for node in root.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )
    result = ast.get_docstring(rule)
    assert result is not None
    return result


class ClosedNormativeListsTests(unittest.TestCase):
    def test_closed_shape_and_pattern_catalogs(self) -> None:
        shape_rule = _rule("model.py", "SPEC_005")
        self.assertIn("7種類に限り", shape_rule)
        self.assertIn("未知のshapeは拒否", shape_rule)
        for shape in (
            "node",
            "optional_node",
            "nodes",
            "text",
            "optional_text",
            "texts",
            "scalar",
        ):
            self.assertIn(f"`{shape}`", shape_rule)

        pattern_rule = _rule("statements.py", "SPEC_005")
        self.assertIn("10種類", pattern_rule)
        for suffix in (
            "value",
            "singleton",
            "capture",
            "wildcard",
            "sequence",
            "mapping",
            "class",
            "star",
            "alias",
            "alternative",
        ):
            self.assertIn(f"`{suffix}`", pattern_rule)
            self.assertEqual(
                shikake.kind_index().get(f"model.pattern.{suffix}").id,
                f"model.pattern.{suffix}",
            )

    def test_conditional_statement_list_matches_collector(self) -> None:
        binding_rule = _rule("binding.py", "SPEC_005")
        for statement in (
            "if",
            "while",
            "for",
            "async for",
            "try",
            "try*",
            "except*",
            "with",
            "async with",
            "match",
        ):
            self.assertIn(f"`{statement}`", binding_rule)
        self.assertIn("SPEC_006", binding_rule)
        self.assertNotIn("など", binding_rule)


class AnalysesInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "sample"
        self.root.mkdir()
        (self.root / "module.py").write_text(
            "class Base: pass\nclass Child(Base): pass\n", encoding="utf-8"
        )

    def test_string_and_empty_string_rejected_by_both_apis(self) -> None:
        for analyze in (shikake.parse_package, shikake.inspect_package):
            for selected in ("override", "inheritance", "", " "):
                with (
                    self.subTest(api=analyze.__name__, analyses=selected),
                    self.assertRaisesRegex(TypeError, "analyses.*not a string"),
                ):
                    analyze(self.root, analyses=selected)

    def test_supported_iterable_and_default_inputs_are_unchanged(self) -> None:
        for analyze in (shikake.parse_package, shikake.inspect_package):
            for selection, expected in (
                (None, frozenset({"override", "inheritance"})),
                ({"inheritance"}, frozenset({"inheritance"})),
                ({"override"}, frozenset({"override", "inheritance"})),
                ([], frozenset()),
            ):
                with self.subTest(api=analyze.__name__, analyses=selection):
                    self.assertEqual(
                        analyze(self.root, analyses=selection).analyses, expected
                    )
            self.assertEqual(
                analyze(self.root, analyses=iter(["inheritance"])).analyses,
                frozenset({"inheritance"}),
            )

    def test_unknown_analysis_keeps_value_error(self) -> None:
        for analyze in (shikake.parse_package, shikake.inspect_package):
            with (
                self.subTest(api=analyze.__name__),
                self.assertRaisesRegex(ValueError, "unknown relation analyses"),
            ):
                analyze(self.root, analyses={"unexpected"})


if __name__ == "__main__":
    unittest.main()
