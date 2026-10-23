"""Mapped-call diagnostic details must be stable without interpreting messages."""

from __future__ import annotations

import unittest

import external_memory_definitions as definitions

import shikake


class ExternalArgumentDiagnosticsTests(unittest.TestCase):
    @staticmethod
    def source(expression: str, *, alias: bool = False) -> str:
        imported = (
            "from framework.memory import Memory as M\n"
            if alias
            else "from framework.memory import Memory\n"
        )
        return f"{imported}first = {expression}\nafter = 1\n"

    def assert_diagnostic(
        self,
        expression: str,
        code: str,
        details: dict[str, str | int],
        *,
        alias: bool = False,
    ) -> None:
        source = self.source(expression, alias=alias)
        # Duplicate literal keywords cannot pass CPython's compilation stage.
        mode = "ast" if "size=1, size=2" in expression else "compile"
        partial = shikake.inspect_source(
            source, definitions=definitions, syntax_validation=mode
        )
        self.assertFalse(partial.complete)
        self.assertIsNotNone(partial.model)
        (issue,) = partial.issues
        self.assertEqual(issue.code, code)
        self.assertEqual(dict(issue.details), details)
        self.assertEqual(issue.skipped_node_type, "Assign")
        assert partial.model is not None
        self.assertEqual(
            [node.span.line for node in partial.model.get_nodes("body") if node.span],
            [1, 3],
        )
        with self.assertRaises(shikake.ExternalModelingError) as caught:
            shikake.parse_source(
                source, definitions=definitions, syntax_validation=mode
            )
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(dict(caught.exception.details), details)

    def test_too_many_positionals_gives_known_counts(self) -> None:
        self.assert_diagnostic(
            "Memory.new(1, 2)",
            "external.too_many_positional",
            {"target": "Memory.new", "expected_count": 1, "actual_count": 2},
        )

    def test_starred_positional_never_invents_effective_count(self) -> None:
        self.assert_diagnostic(
            "Memory.new(*values)",
            "external.starred_positional",
            {"target": "Memory.new"},
        )

    def test_starred_has_priority_over_syntactic_excess(self) -> None:
        self.assert_diagnostic(
            "Memory.new(*values, 1)",
            "external.starred_positional",
            {"target": "Memory.new"},
        )

    def test_unknown_keyword_is_reported_with_written_alias(self) -> None:
        self.assert_diagnostic(
            "M.new(w=1)",
            "external.unknown_keyword",
            {"target": "M.new", "keyword": "w"},
            alias=True,
        )

    def test_missing_argument_identifies_target_and_keyword(self) -> None:
        self.assert_diagnostic(
            "Memory.new()",
            "external.argument_mismatch",
            {"target": "Memory.new", "keyword": "size"},
        )

    def test_duplicate_positional_and_named_argument_is_mismatch(self) -> None:
        self.assert_diagnostic(
            "Memory.new(1, size=2)",
            "external.argument_mismatch",
            {"target": "Memory.new", "keyword": "size"},
        )

    def test_expanded_and_duplicate_keywords_do_not_infer_values(self) -> None:
        self.assert_diagnostic(
            "Memory.new(**kwargs)",
            "external.keyword_arguments",
            {"target": "Memory.new"},
        )
        self.assert_diagnostic(
            "Memory.new(size=1, size=2)",
            "external.keyword_arguments",
            {"target": "Memory.new", "keyword": "size"},
        )

    def test_prior_omission_does_not_model_missing_assignment(self) -> None:
        source = "from framework.memory import Memory\na = Memory.tan(1)\nsize = a\n"
        result = shikake.inspect_source(source, definitions=definitions)
        self.assertFalse(result.complete)
        self.assertEqual(result.name_bindings, ())
        assert result.model is not None
        self.assertEqual(
            [model.span.line for model in result.model.get_nodes("body") if model.span],
            [1, 3],
        )
        self.assertEqual(result.issues[0].skipped_node_type, "Assign")


if __name__ == "__main__":
    unittest.main()
