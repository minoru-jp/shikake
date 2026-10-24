"""Optional expression evaluation must not be mistaken for a stable introduction."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake._mica.ast_facts import collect_syntax_facts


class ConditionalExpressionBindingTests(unittest.TestCase):
    def _binding(self, source: str) -> shikake.BindingState:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "sample"
            directory.mkdir()
            (directory / "case.py").write_text(source + "\n", encoding="utf-8")
            package = shikake.parse_package(directory, analyses={"inheritance"})
        module = next(node for node in package.walk() if node.kind.id == "model.module")
        (binding,) = package.bindings_for(module, "B")
        return binding.state

    def test_optional_expression_writes_are_unstable(self) -> None:
        samples = (
            "flag and (B := object)",
            "flag or (B := object)",
            "(B := object) if flag else None",
            "None if flag else (B := object)",
            "[(B := k) for k in ks]",
            "{(B := k) for k in ks}",
            "{k: (B := k) for k in ks}",
            "((B := k) for k in ks)",
            "assert (B := object)",
            "first < second < (B := object)",
        )
        for source in samples:
            with self.subTest(source=source):
                self.assertEqual(
                    self._binding(source),
                    shikake.BindingState(
                        "unstable", source.startswith(("[", "{", "((")), False, False
                    ),
                )

    def test_required_expression_positions_remain_stable(self) -> None:
        samples = (
            "(B := object) and flag",
            "(B := object) or flag",
            "value if (B := flag) else other",
            "first < (B := object)",
            "f = lambda a=(B := object): a",
        )
        for source in samples:
            with self.subTest(source=source):
                self.assertEqual(
                    self._binding(source),
                    shikake.BindingState("stable", False, False, False),
                )

    def test_conditions_flow_through_lambda_defaults_but_not_lambda_body(self) -> None:
        self.assertEqual(
            self._binding("flag and (lambda a=(B := object): a)"),
            shikake.BindingState("unstable", False, False, False),
        )
        self.assertEqual(
            self._binding("g = lambda: (B := object)\nB = object"),
            shikake.BindingState("stable", False, False, False),
        )

    def test_expression_conditionality_is_shared_with_base_binding(self) -> None:
        source = "flag and (B := object)\nclass D(B): pass"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "sample"
            directory.mkdir()
            (directory / "case.py").write_text(source, encoding="utf-8")
            package = shikake.parse_package(directory, analyses={"inheritance"})
        (reference,) = package.base_references
        self.assertEqual(
            reference.binding, shikake.BindingState("unstable", False, False, False)
        )

    def test_shared_syntax_events_mark_optional_operations(self) -> None:
        source = "(B := 1) and (B := 2)\nassert (B := 3)"
        facts = collect_syntax_facts(ast.parse(source), include_references=False)
        self.assertEqual(
            [
                event.conditional
                for event in sorted(
                    (event for event in facts.events if event.name == "B"),
                    key=lambda event: (
                        getattr(event.node, "lineno", 0),
                        getattr(event.node, "col_offset", 0),
                    ),
                )
            ],
            [False, True, True],
        )


if __name__ == "__main__":
    unittest.main()
