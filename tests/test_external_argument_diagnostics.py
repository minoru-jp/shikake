"""Nonmatching registered calls retain ordinary Python Call structure."""

from __future__ import annotations

import unittest

import external_memory_definitions as definitions

import shikake


class ExternalArgumentFallbackTests(unittest.TestCase):
    def test_non_matching_argument_forms_fall_back_to_call(self) -> None:
        for expression in (
            "Memory.new(1, 2)",
            "Memory.new()",
            "Memory.new(*args)",
            "Memory.new(**args)",
            "Memory.new(size=1, unexpected=2)",
            "Memory.new(1, size=2)",
            "Memory.new(unexpected=1)",
        ):
            with self.subTest(expression=expression):
                source = f"from framework.memory import Memory\nx = {expression}\n"
                result = shikake.inspect_source(source, definitions=definitions)
                self.assertTrue(result.complete, result.issues)
                assert result.model is not None
                kinds = {m.kind.id for m in result.model.walk()}
                self.assertIn("model.value.call", kinds)
                self.assertNotIn("ext.memory.allocate", kinds)
                self.assertEqual(
                    shikake.parse_source(source, definitions=definitions), result.model
                )

    def test_valid_keyword_and_positional_bind_to_same_structure(self) -> None:
        for call in ("Memory.new(1)", "Memory.new(size=1)"):
            with self.subTest(call=call):
                source = f"from framework.memory import Memory\nx = {call}\n"
                model = shikake.parse_source(source, definitions=definitions)
                self.assertIn("ext.memory.allocate", {m.kind.id for m in model.walk()})

    def test_compile_syntax_errors_remain_python_errors(self) -> None:
        source = "from framework.memory import Memory\nx = Memory.new(size=1, size=2)\n"
        result = shikake.inspect_source(source, definitions=definitions)
        self.assertFalse(result.complete)
        self.assertEqual(result.issues[0].category, "syntax_error")
