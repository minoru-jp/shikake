"""Public role accessors preserve existing Model.get semantics."""

from __future__ import annotations

import unittest

import shikake
from shikake import Model


class TypedAccessorTests(unittest.TestCase):
    def test_single_node_sequence_and_name(self) -> None:
        root = shikake.parse_source("total = price + tax")
        (assignment,) = root.get_nodes("body")
        (target,) = assignment.get_nodes("targets")
        self.assertIsInstance(assignment, Model)
        self.assertEqual(target.get_name("name"), "total")

        value = assignment.get_node("value")
        self.assertEqual(value.kind.id, "model.value.operation.addition")
        self.assertEqual(value.get_node("left").get_name("name"), "price")
        self.assertEqual(value.get_node("right").get_name("name"), "tax")
        self.assertIs(assignment.get("value"), value)
        self.assertEqual(root.get_nodes("body"), root.get("body"))

    def test_empty_node_sequences(self) -> None:
        root = shikake.parse_source("")
        self.assertEqual(root.get_nodes("body"), ())

    def test_unknown_role_is_key_error_for_all_accessors(self) -> None:
        root = shikake.parse_source("x = 1")
        for accessor in (root.get_node, root.get_nodes, root.get_name):
            with self.subTest(accessor=accessor.__name__), self.assertRaises(KeyError):
                accessor("nonexistent")

    def test_shape_mismatch_is_type_error_without_coercion(self) -> None:
        root = shikake.parse_source("x = 1")
        (assignment,) = root.get_nodes("body")
        (target,) = assignment.get_nodes("targets")
        with self.assertRaises(TypeError):
            root.get_node("body")
        with self.assertRaises(TypeError):
            target.get_nodes("name")
        with self.assertRaises(TypeError):
            target.get_node("name")
        with self.assertRaises(TypeError):
            assignment.get_name("value")
        self.assertEqual(target.get("name"), "x")

    def test_absent_optional_role_remains_available_via_get(self) -> None:
        root = shikake.parse_source("def f():\n    return\n")
        (function,) = root.get_nodes("body")
        (return_stmt,) = function.get_node("body").get_nodes("statements")
        self.assertIsNone(return_stmt.get("value"))
        with self.assertRaises(TypeError):
            return_stmt.get_node("value")

    def test_text_accessors_do_not_convert_scalars(self) -> None:
        root = shikake.parse_source("x = 123")
        (statement,) = root.get_nodes("body")
        literal = statement.get_node("value")
        self.assertEqual(literal.get("value"), 123)
        with self.assertRaises(TypeError):
            literal.get_name("value")


if __name__ == "__main__":
    unittest.main()
