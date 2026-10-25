"""Contracts for singletons, imports, explicit pass and augmented assignments."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model, ModelFactory, PartValue

SAMPLE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "fee_adjustments.py"
)


def child(node: Model, role: str) -> Model:
    value = node.get(role)
    assert isinstance(value, Model)
    return value


def children(node: Model, role: str) -> tuple[Model, ...]:
    value = node.get(role)
    assert isinstance(value, tuple)
    assert all(isinstance(item, Model) for item in value)
    return cast(tuple[Model, ...], value)


class SpecialStatementTests(unittest.TestCase):
    def test_imports_keep_aliases_and_written_order(self) -> None:
        source = "import os.path as p, sys\nfrom .other import Thing as T, Item\n"
        root = shikake.parse_source(source)
        normal, from_import = children(root, "body")
        self.assertEqual(normal.kind.id, "model.import.direct")
        self.assertEqual(normal.kind.parent_id, "model.import")
        self.assertEqual(
            [
                (item.get("name"), item.get("asname"))
                for item in children(normal, "names")
            ],
            [("os.path", "p"), ("sys", None)],
        )
        self.assertEqual(from_import.kind.id, "model.import.from")
        self.assertEqual(from_import.get("module"), "other")
        self.assertEqual(from_import.get("level"), 1)
        self.assertEqual(
            [
                (item.get("name"), item.get("asname"))
                for item in children(from_import, "names")
            ],
            [("Thing", "T"), ("Item", None)],
        )
        self.assertEqual(tuple(p.role for p in normal.parts()), ("names",))

    def test_pass_is_present_even_when_it_has_no_children(self) -> None:
        root = shikake.parse_source("if flag:\n    pass\nelse:\n    pass\n")
        (branch,) = children(root, "body")
        paths = children(branch, "paths")
        true_pass = children(child(paths[0], "body"), "statements")[0]
        false_pass = children(child(paths[1], "body"), "statements")[0]
        self.assertEqual(true_pass.kind.id, "model.statement.pass")
        self.assertEqual(false_pass.kind.id, "model.statement.pass")
        self.assertEqual(true_pass.parts(), ())
        self.assertIsNotNone(true_pass.span)
        self.assertEqual(len(tuple(root.walk())), 9)

    def test_special_literals_keep_identity_and_absence_is_not_none_literal(
        self,
    ) -> None:
        source = "x = ...\ny = None\ndef f():\n    return\ndef g():\n    return None\n"
        root = shikake.parse_source(source)
        assignment_ellipsis, assignment_none, f, g = children(root, "body")
        ellipsis_model = child(assignment_ellipsis, "value")
        none_model = child(assignment_none, "value")
        self.assertEqual(ellipsis_model.kind.id, "model.value.literal.special.ellipsis")
        self.assertIs(ellipsis_model.get("value"), Ellipsis)
        self.assertEqual(none_model.kind.id, "model.value.literal.special.none")
        self.assertIsNone(none_model.get("value"))
        self.assertTrue(
            shikake.definition_index().classified_under(
                none_model.kind.id, "model.value.literal"
            )
        )
        self.assertTrue(
            shikake.definition_index().classified_under(
                ellipsis_model.kind.id, "model.value.literal"
            )
        )
        (empty_return,) = children(child(f, "body"), "statements")
        (explicit_return,) = children(child(g, "body"), "statements")
        self.assertIsNone(empty_return.get("value"))
        self.assertEqual(
            child(explicit_return, "value").kind.id, "model.value.literal.special.none"
        )
        (indexed_assignment,) = children(shikake.parse_source("x = data[...]"), "body")
        indexed_access = child(indexed_assignment, "value")
        self.assertEqual(indexed_access.kind.id, "model.value.access.index")
        self.assertIs(child(indexed_access, "index").get("value"), Ellipsis)
        with self.assertRaises(TypeError):
            ModelFactory(shikake.definition_index()).make(
                "model.value.literal", value=cast(PartValue, object())
            )

    def test_all_augmented_operators_are_distinct_without_expansion(self) -> None:
        operators = {
            "+=": "addition",
            "-=": "subtraction",
            "*=": "multiplication",
            "@=": "matrix_multiplication",
            "/=": "division",
            "//=": "floor_division",
            "%=": "modulo",
            "**=": "power",
            "<<=": "left_shift",
            ">>=": "right_shift",
            "&=": "bitwise_and",
            "|=": "bitwise_or",
            "^=": "bitwise_xor",
        }
        index = shikake.definition_index()
        for token, slug in operators.items():
            with self.subTest(operator=token):
                root = shikake.parse_source(f"target {token} value\n")
                (statement,) = children(root, "body")
                self.assertEqual(
                    statement.kind.id, f"model.statement.assignment.augmented.{slug}"
                )
                self.assertEqual(
                    tuple(part.role for part in statement.parts()), ("target", "value")
                )
                self.assertTrue(
                    index.classified_under(
                        statement.kind.id, "model.statement.assignment.augmented"
                    )
                )
                self.assertEqual(len(tuple(statement.walk())), 3)
                self.assertEqual(child(statement, "target").get("name"), "target")
                self.assertEqual(child(statement, "value").get("name"), "value")
        indexed = shikake.parse_source("items[key] += count\n")
        (augmented,) = children(indexed, "body")
        target = child(augmented, "target")
        self.assertEqual(target.kind.id, "model.value.access.index")
        self.assertEqual(child(target, "index").get("name"), "key")
        self.assertEqual(child(augmented, "value").get("name"), "count")

    def test_realistic_sample_is_fully_modeled_but_not_interpreted(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        root = shikake.parse_source(source)
        self.assertTrue(shikake.inspect_source(source).complete)
        ids = [model.kind.id for model in root.walk()]
        for expected in (
            "model.import.direct",
            "model.import.from",
            "model.value.literal.special.none",
            "model.value.literal.special.ellipsis",
            "model.statement.pass",
            "model.statement.assignment.augmented.addition",
            "model.statement.assignment.augmented.subtraction",
        ):
            self.assertIn(expected, ids)
        kinds = shikake.definition_index().all_kinds()
        self.assertEqual(len(kinds), 142)
        self.assertEqual(len(kinds), len({kind.id for kind in kinds}))
        inspected = shikake.inspect_source(source)
        assert inspected.model is not None
        self.assertEqual(tuple(root.walk()), tuple(inspected.model.walk()))

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_mode_still_reports_unadopted_syntax(self) -> None:
        source = "import math\nx += 1\ntype Unmodeled = int\ny = ...\n"
        result = shikake.inspect_source(source)
        self.assertFalse(result.complete)
        self.assertEqual([i.node_type for i in result.issues], ["TypeAlias"])
        assert result.model is not None
        self.assertEqual(len(children(result.model, "body")), 3)
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)


if __name__ == "__main__":
    unittest.main()
