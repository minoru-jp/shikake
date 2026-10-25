"""Written assignment structure: multiple targets, unpacking and :=."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SAMPLE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "binding_patterns.py"
)


def nodes(item: Model, role: str) -> tuple[Model, ...]:
    result = item.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(item, Model) for item in result)
    return cast(tuple[Model, ...], result)


def one(item: Model, role: str) -> Model:
    result = item.get(role)
    assert isinstance(result, Model)
    return result


class AssignmentStructureTests(unittest.TestCase):
    def test_ast_information_is_kept_without_normalizing_assignment(self) -> None:
        source = "a = b = produce()\n"
        ast_node = ast.parse(source, type_comments=True).body[0]
        assert isinstance(ast_node, ast.Assign)
        self.assertEqual(len(ast_node.targets), 2)
        (assignment,) = nodes(shikake.parse_source(source), "body")
        self.assertEqual(assignment.kind.id, "model.statement.assignment")
        self.assertEqual(
            [t.get("name") for t in nodes(assignment, "targets")], ["a", "b"]
        )
        self.assertEqual(one(assignment, "value").kind.id, "model.value.call")
        self.assertEqual([p.role for p in assignment.parts()], ["targets", "value"])
        self.assertEqual(len(tuple(assignment.walk())), 5)
        self.assertEqual(assignment.span.line if assignment.span else None, 1)

    def test_single_assignment_also_uses_targets_tuple(self) -> None:
        (stmt,) = nodes(shikake.parse_source("output = value\n"), "body")
        self.assertEqual(len(nodes(stmt, "targets")), 1)
        self.assertEqual(nodes(stmt, "targets")[0].get("name"), "output")
        self.assertEqual(one(stmt, "value").get("name"), "value")
        with self.assertRaises(KeyError):
            stmt.get("target")

    def test_nested_tuple_list_unpacking_and_starred_target(self) -> None:
        source = "(first, [second, *remaining]), last = values\n"
        (stmt,) = nodes(shikake.parse_source(source), "body")
        (target,) = nodes(stmt, "targets")
        self.assertEqual(target.kind.id, "model.structural_part.sequence_target")
        first_tuple, last = nodes(target, "elements")
        self.assertEqual(last.get("name"), "last")
        first, inner_list = nodes(first_tuple, "elements")
        self.assertEqual(first.get("name"), "first")
        self.assertEqual(inner_list.kind.id, "model.structural_part.sequence_target")
        second, starred = nodes(inner_list, "elements")
        self.assertEqual(second.get("name"), "second")
        self.assertEqual(starred.kind.id, "model.structural_part.starred_target")
        self.assertEqual(one(starred, "value").get("name"), "remaining")
        self.assertEqual([p.role for p in starred.parts()], ["value"])
        self.assertTrue(
            shikake.definition_index().classified_under(
                starred.kind.id, "model.structural_part"
            )
        )
        self.assertIsNotNone(starred.span)

    def test_distinct_target_and_value_structures_for_access(self) -> None:
        (assignment,) = nodes(
            shikake.parse_source("obj.code = box[index] = calculate()\n"), "body"
        )
        attribute, index = nodes(assignment, "targets")
        self.assertEqual(attribute.kind.id, "model.value.access.attribute")
        self.assertEqual(index.kind.id, "model.value.access.index")
        self.assertEqual(one(index, "index").get("name"), "index")
        self.assertEqual(one(assignment, "value").kind.id, "model.value.call")
        # Access targets are not a new binding-target Kind.
        self.assertEqual(one(attribute, "target").get("name"), "obj")

    def test_named_expression_is_value_and_preserves_binding(self) -> None:
        source = "result = (count := len(items)) + count\n"
        (assignment,) = nodes(shikake.parse_source(source), "body")
        addition = one(assignment, "value")
        binding = one(addition, "left")
        self.assertEqual(binding.kind.id, "model.value.binding")
        self.assertEqual(one(binding, "target").get("name"), "count")
        self.assertEqual(one(binding, "value").kind.id, "model.value.call")
        self.assertTrue(
            shikake.definition_index().classified_under(binding.kind.id, "model.value")
        )
        self.assertFalse(
            shikake.definition_index().classified_under(
                binding.kind.id, "model.statement.assignment"
            )
        )
        self.assertEqual(one(addition, "right").get("name"), "count")

    def test_nested_named_expressions_follow_ast_structure(self) -> None:
        source = "if (size := len(rows)) and (ready := size > 0):\n    pass\n"
        branch = nodes(shikake.parse_source(source), "body")[0]
        (path,) = nodes(branch, "paths")
        condition = one(path, "condition")
        self.assertEqual(condition.kind.id, "model.value.operation.logical.and")
        bindings = nodes(condition, "values")
        self.assertEqual(
            [one(b, "target").get("name") for b in bindings], ["size", "ready"]
        )
        self.assertEqual(
            one(bindings[1], "value").kind.id,
            "model.value.operation.comparison.greater",
        )

    def test_for_target_reuses_binding_shape_without_new_iteration_kind(self) -> None:
        source = "for first, *remaining in batches:\n    pass\n"
        (iteration,) = nodes(shikake.parse_source(source), "body")
        target = one(iteration, "binding")
        self.assertEqual(target.kind.id, "model.structural_part.sequence_target")
        self.assertEqual(nodes(target, "elements")[0].get("name"), "first")
        starred = nodes(target, "elements")[1]
        self.assertEqual(starred.kind.id, "model.structural_part.starred_target")
        self.assertEqual(one(starred, "value").get("name"), "remaining")

    def test_package_name_resolution_respects_multi_and_starred_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            pkg = Path(temp) / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "base.py").write_text(
                "class Base:\n    def process(self):\n        pass\n", encoding="utf-8"
            )
            child_file = pkg / "derived.py"
            child_body = "class Child(Base):\n    def process(self):\n        pass\n"
            child_file.write_text(
                "from .base import Base\n" + child_body, encoding="utf-8"
            )
            self.assertEqual(len(shikake.parse_package(pkg).override_candidates), 1)

            # Attribute/index assignment leaves the imported name itself intact.
            child_file.write_text(
                "from .base import Base\nBase.attr = 1\nBase[0] = 2\n" + child_body,
                encoding="utf-8",
            )
            self.assertEqual(len(shikake.parse_package(pkg).override_candidates), 1)

            # A later syntactic write makes the name unstable, but the earlier
            # explicit import remains a discoverable class candidate.
            child_file.write_text(
                "from .base import Base\nleft, (right, *Base) = values\n" + child_body,
                encoding="utf-8",
            )
            result = shikake.parse_package(pkg)
            self.assertEqual(len(result.override_candidates), 1)
            child_reference = next(
                ref
                for ref in result.base_references
                if ref.subject.get_name("name") == "Child"
            )
            self.assertEqual(
                child_reference.binding,
                shikake.BindingState("stable", True, False, False),
            )

    def test_augmented_assignment_contract_is_unmodified(self) -> None:
        (stmt,) = nodes(shikake.parse_source("total += count\n"), "body")
        self.assertEqual(stmt.kind.id, "model.statement.assignment.augmented.addition")
        self.assertEqual([p.role for p in stmt.parts()], ["target", "value"])

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_skips_only_unsupported_sibling(self) -> None:
        source = (
            "a = b = 1\n"
            "type Unhandled = int\n"
            "first, *rest = records\n"
            "result = (length := len(rest))\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertFalse(inspected.complete)
        self.assertEqual([issue.node_type for issue in inspected.issues], ["TypeAlias"])
        assert inspected.model is not None
        self.assertEqual(len(nodes(inspected.model, "body")), 3)
        self.assertEqual(
            [len(nodes(stmt, "targets")) for stmt in nodes(inspected.model, "body")],
            [2, 1, 1],
        )
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)

    def test_assignment_type_comments_are_not_modeled(self) -> None:
        (assignment,) = nodes(shikake.parse_source("a = b = 1  # type: int\n"), "body")
        self.assertEqual(len(nodes(assignment, "targets")), 2)
        self.assertEqual(shikake.inspect_source("a = b = 1  # type: int\n").issues, ())

    def test_sample_has_explicit_structure_and_strict_matches_inspection(self) -> None:
        source = SAMPLE.read_text(encoding="utf-8")
        parsed = shikake.parse_source(source)
        inspected = shikake.inspect_source(source)
        self.assertTrue(inspected.complete)
        self.assertEqual(parsed, inspected.model)
        kinds = {node.kind.id for node in parsed.walk()}
        self.assertTrue(
            {"model.value.binding", "model.structural_part.starred_target"}.issubset(
                kinds
            )
        )
        self.assertEqual(len(shikake.definition_index().all_kinds()), 142)


if __name__ == "__main__":
    unittest.main()
