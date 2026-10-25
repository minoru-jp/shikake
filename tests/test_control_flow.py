"""Control-flow generalization without losing original selectors and blocks."""

from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

EXAMPLE = Path(__file__).resolve().parents[1] / "tests/fixtures/stock_workflow.py"


def one(model: Model, role: str) -> Model:
    result = model.get(role)
    assert isinstance(result, Model)
    return result


def many(model: Model, role: str) -> tuple[Model, ...]:
    result = model.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(item, Model) for item in result)
    return cast(tuple[Model, ...], result)


class ControlFlowModelTests(unittest.TestCase):
    def test_single_kind_for_if_and_match_with_different_selectors(self) -> None:
        root = shikake.parse_source(
            "if flag:\n    x = 1\nelse:\n    x = 2\n"
            'match command:\n    case "ok":\n        x = 3\n    case _:\n        x = 4\n'
        )
        condition_branch, pattern_branch = many(root, "body")
        self.assertEqual(condition_branch.kind.id, "model.statement.branch")
        self.assertEqual(pattern_branch.kind.id, "model.statement.branch")
        self.assertIsNone(condition_branch.get("subject"))
        self.assertEqual(one(pattern_branch, "subject").get("name"), "command")
        conditions = many(condition_branch, "paths")
        self.assertEqual(one(conditions[0], "condition").get("name"), "flag")
        self.assertIsNone(conditions[0].get("pattern"))
        self.assertIsNone(conditions[1].get("condition"))
        self.assertIsNone(conditions[1].get("pattern"))  # explicit else
        patterns = many(pattern_branch, "paths")
        self.assertIsNone(patterns[0].get("condition"))
        self.assertEqual(one(patterns[0], "pattern").kind.id, "model.pattern.value")
        self.assertEqual(one(patterns[1], "pattern").kind.id, "model.pattern.wildcard")
        for branch in (condition_branch, pattern_branch):
            for path in many(branch, "paths"):
                self.assertEqual(len(many(one(path, "body"), "statements")), 1)

    def test_elif_flattens_but_nested_else_if_does_not(self) -> None:
        parsed = shikake.parse_source(
            "if x == 1:\n    pass\nelif x == 2:\n    pass\nelse:\n    pass\n"
        )
        (branch,) = many(parsed, "body")
        paths = many(branch, "paths")
        self.assertEqual(len(paths), 3)
        self.assertIsNone(paths[-1].get("condition"))
        nested = shikake.parse_source(
            "if x == 1:\n    pass\nelse:\n    if x == 2:\n        pass\n"
        )
        (outer,) = many(nested, "body")
        last = many(outer, "paths")[-1]
        self.assertEqual(
            many(one(last, "body"), "statements")[0].kind.id,
            "model.statement.branch",
        )

    def test_both_loop_forms_share_kind_preserve_else_and_transfer(self) -> None:
        root = shikake.parse_source(
            "for key, value in entries:\n"
            "    if value:\n        continue\n"
            "    break\n"
            "else:\n    pass\n"
            "while ready:\n    ready = False\nelse:\n    pass\n"
        )
        by_items, by_condition = many(root, "body")
        self.assertEqual(by_items.kind.id, by_condition.kind.id)
        self.assertEqual(by_items.kind.id, "model.statement.control.iteration")
        self.assertIsNone(by_items.get("condition"))
        self.assertIsNotNone(by_items.get("source"))
        self.assertEqual(
            one(by_items, "binding").kind.id, "model.structural_part.sequence_target"
        )
        self.assertIsNone(by_condition.get("binding"))
        self.assertIsNone(by_condition.get("source"))
        self.assertEqual(one(by_condition, "condition").get("name"), "ready")
        self.assertEqual(
            [m.kind.id for m in many(one(by_items, "body"), "statements")],
            ["model.statement.branch", "model.statement.break"],
        )
        for loop in (by_items, by_condition):
            self.assertEqual(
                many(one(loop, "else_block"), "statements")[0].kind.id,
                "model.statement.pass",
            )

    def test_try_handlers_else_finally_and_exception_star(self) -> None:
        source = (
            "try:\n    work()\n"
            "except ValueError as error:\n    pass\n"
            "except Exception:\n    pass\n"
            "else:\n    done()\nfinally:\n    cleanup()\n"
        )
        (guarded,) = many(shikake.parse_source(source), "body")
        self.assertEqual(guarded.kind.id, "model.statement.control.exception_handling")
        self.assertIs(guarded.get("grouped"), False)
        handlers = many(guarded, "handlers")
        self.assertEqual(len(handlers), 2)
        self.assertEqual(handlers[0].get("name"), "error")
        self.assertEqual(one(handlers[0], "exception").get("name"), "ValueError")
        self.assertEqual(len(many(one(guarded, "body"), "statements")), 1)
        self.assertEqual(len(many(one(guarded, "else_block"), "statements")), 1)
        self.assertEqual(len(many(one(guarded, "finally_block"), "statements")), 1)
        group = shikake.parse_source("try:\n    pass\nexcept* ValueError:\n    pass\n")
        (star,) = many(group, "body")
        self.assertEqual(star.kind.id, guarded.kind.id)
        self.assertIs(star.get("grouped"), True)

    def test_all_pattern_categories_maintain_structural_roles(self) -> None:
        root = shikake.parse_source(
            "match item:\n"
            "    case [first, *rest]:\n        pass\n"
            '    case {"name": label, **extra}:\n        pass\n'
            "    case Thing(value, name=name) as matched:\n        pass\n"
            "    case 1 | 2:\n        pass\n"
            "    case None:\n        pass\n"
        )
        (branch,) = many(root, "body")
        paths = many(branch, "paths")
        expected = (
            "model.pattern.sequence",
            "model.pattern.mapping",
            "model.pattern.alias",
            "model.pattern.alternative",
            "model.pattern.singleton",
        )
        self.assertEqual(
            tuple(one(path, "pattern").kind.id for path in paths), expected
        )
        mapping = one(paths[1], "pattern")
        self.assertEqual(mapping.get("rest"), "extra")
        self.assertEqual(
            many(mapping, "entries")[0].kind.id,
            "model.structural_part.mapping_pattern_entry",
        )
        alias = one(paths[2], "pattern")
        self.assertEqual(alias.get("name"), "matched")
        cls = one(alias, "pattern")
        self.assertEqual(cls.kind.id, "model.pattern.class")
        self.assertEqual(many(cls, "keywords")[0].get("name"), "name")
        index = shikake.definition_index()
        for node in branch.walk():
            self.assertEqual(
                tuple(p.role for p in node.parts()),
                tuple(p.role for p in index.require_structure(node.kind.id).parts),
            )

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_unsupported_children_never_hoisted_and_strict_unchanged(self) -> None:
        source = (
            "for item in values:\n"
            "    total += 1\n"
            "    type Hidden = tuple[item]\n"
            "    total += 2\n"
        )
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)
        partial = shikake.inspect_source(source)
        self.assertFalse(partial.complete)
        self.assertEqual([i.node_type for i in partial.issues], ["TypeAlias"])
        assert partial.model is not None
        (loop,) = many(partial.model, "body")
        self.assertEqual(len(many(one(loop, "body"), "statements")), 2)

    def test_sample_strict_and_concrete_operational_example(self) -> None:
        source = EXAMPLE.read_text(encoding="utf-8")
        root = shikake.parse_source(source)
        self.assertTrue(shikake.inspect_source(source).complete)
        self.assertEqual(root.kind.id, "model.module")
        self.assertTrue(
            all(
                node.kind.id in {k.id for k in shikake.definition_index().all_kinds()}
                for node in root.walk()
            )
        )
        kinds = {n.kind.id for n in root.walk()}
        self.assertTrue(
            {
                "model.statement.branch",
                "model.statement.control.iteration",
                "model.statement.control.exception_handling",
                "model.pattern.sequence",
                "model.statement.break",
                "model.statement.continue",
            }.issubset(kinds)
        )
        # Execute only the trusted example, never user's input supplied to Mica.
        functions = runpy.run_path(str(EXAMPLE))
        self.assertEqual(functions["stock_state"](2, 5), "low")
        self.assertEqual(
            functions["rebalance_stock"](
                [("receive", 3), ("invalid", 2), ("ship", 1)], 5, 2
            ),
            (6, 2, 3, True),
        )


if __name__ == "__main__":
    unittest.main()
