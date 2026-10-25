"""Integration tests for Kind definitions and AST-to-Model structural traversal."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.kinds import DefinitionIndex, Kind, load_definition_index
from shikake._mica.model import Model, ModelFactory

SAMPLE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "shipping.py"


class DefinitionIndexTests(unittest.TestCase):
    def test_shikumi_description_and_classification(self) -> None:
        index = load_definition_index()
        self.assertEqual(len(index.all_kinds()), 142)
        kind = index.get("model.value.access.index")
        self.assertEqual(kind.parent_id, "model.value.access")
        self.assertEqual(
            [spec.role for spec in index.require_structure(kind.id).parts],
            ["target", "index"],
        )
        self.assertTrue(index.classified_under(kind.id, "model.value"))
        self.assertTrue(index.classified_under(kind.id, kind.id))
        self.assertFalse(
            index.classified_under("model.statement.branch", "model.value")
        )
        self.assertEqual(index.parent("model"), None)
        with self.assertRaises(KeyError):
            index.get("model.not_defined")

    def test_split_description_discovers_modules_and_validates_parents(self) -> None:
        """New files are found without updating a manually maintained registry."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "mica_kind_test_fragments"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "core.py").write_text(
                "from shikake._mica.kinds.regulation import kind_id\n"
                "class Root:\n    kind_id @= 'model'\n",
                encoding="utf-8",
            )
            (package / "access.py").write_text(
                "from shikake._mica.kinds.regulation import kind_id, parent_id\n"
                "class Access:\n"
                "    kind_id @= 'model.access'\n"
                "    parent_id @= 'model'\n",
                encoding="utf-8",
            )
            sys.path.insert(0, str(root))
            try:
                source = importlib.import_module("mica_kind_test_fragments")
                index = load_definition_index(source)
                self.assertTrue(index.classified_under("model.access", "model"))

                # Add another module with no changes to Shikumi regulations/loader.
                (package / "child.py").write_text(
                    "from shikake._mica.kinds.regulation import kind_id, parent_id\n"
                    "class Child:\n"
                    "    kind_id @= 'model.access.child'\n"
                    "    parent_id @= 'model.access'\n",
                    encoding="utf-8",
                )
                importlib.invalidate_caches()
                extended = load_definition_index(source)
                self.assertEqual(len(extended.all_kinds()), 3)
                self.assertTrue(
                    extended.classified_under("model.access.child", "model")
                )

                (package / "invalid.py").write_text(
                    "from shikake._mica.kinds.regulation import kind_id, parent_id\n"
                    "class Invalid:\n"
                    "    kind_id @= 'model.invalid'\n"
                    "    parent_id @= 'model.nonexistent'\n",
                    encoding="utf-8",
                )
                importlib.invalidate_caches()
                with self.assertRaisesRegex(ValueError, "unknown parent"):
                    load_definition_index(source)

                (package / "invalid.py").unlink()
                (package / "duplicate.py").write_text(
                    "from shikake._mica.kinds.regulation import kind_id, parent_id\n"
                    "class Duplicate:\n"
                    "    kind_id @= 'model.access'\n"
                    "    parent_id @= 'model'\n",
                    encoding="utf-8",
                )
                importlib.invalidate_caches()
                with self.assertRaisesRegex(ValueError, "duplicate Kind ID"):
                    load_definition_index(source)
            finally:
                sys.path.remove(str(root))
                for name in tuple(sys.modules):
                    if name == "mica_kind_test_fragments" or name.startswith(
                        "mica_kind_test_fragments."
                    ):
                        del sys.modules[name]

    def test_invalid_definition_index_cannot_be_silent(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate Kind ID"):
            DefinitionIndex((Kind("model", None), Kind("model", None)))
        with self.assertRaisesRegex(ValueError, "missing parent"):
            DefinitionIndex((Kind("model", None), Kind("child", None)))
        with self.assertRaisesRegex(ValueError, "unknown parent"):
            DefinitionIndex((Kind("model", None), Kind("child", "missing")))
        with self.assertRaisesRegex(ValueError, "cyclic Kind ancestry"):
            DefinitionIndex((Kind("model", None), Kind("a", "b"), Kind("b", "a")))

    def test_factory_rejects_missing_or_invalid_roles(self) -> None:
        f = ModelFactory(shikake.definition_index())
        with self.assertRaisesRegex(ValueError, "expected roles"):
            f.make("model.value.named", other="x")
        with self.assertRaisesRegex(TypeError, "shape text"):
            f.make("model.value.named", name=123)


def child(model: Model, role: str) -> Model:
    value = model.get(role)
    if not isinstance(value, Model):
        raise TypeError(f"{model.kind.id}.{role} is not a Model")
    return value


def children(model: Model, role: str) -> tuple[Model, ...]:
    value = model.get(role)
    if not isinstance(value, tuple) or not all(
        isinstance(item, Model) for item in value
    ):
        raise TypeError(f"{model.kind.id}.{role} is not a Model sequence")
    return cast(tuple[Model, ...], value)


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SAMPLE.read_text(encoding="utf-8")
        self.model = shikake.parse_source(self.source)

    def test_module_definition_function_branch_and_return(self) -> None:
        root = self.model
        self.assertIsInstance(root, Model)
        self.assertEqual(root.kind.id, "model.module")
        body = children(root, "body")
        self.assertEqual(len(body), 3)
        for var, name, value in zip(
            body[:2],
            ["FREE_SHIPPING_THRESHOLD", "STANDARD_SHIPPING_FEE"],
            [5000, 600],
            strict=True,
        ):
            self.assertEqual(var.kind.id, "model.definition.variable")
            self.assertEqual(var.get("name"), name)
            self.assertEqual(child(var, "annotation").get("name"), "int")
            self.assertEqual(child(var, "initializer").get("value"), value)

        function = body[2]
        self.assertEqual(function.kind.id, "model.definition.function")
        self.assertEqual(function.get("name"), "calculate_total")
        self.assertEqual(
            [item.get("name") for item in children(function, "parameters")],
            ["prices", "sku", "quantity"],
        )
        self.assertEqual(child(function, "returns").get("name"), "int")
        statements = children(child(function, "body"), "statements")
        self.assertEqual(len(statements), 4)
        self.assertEqual(
            child(statements[0], "value").kind.id, "model.value.access.index"
        )
        self.assertEqual(
            child(statements[1], "value").kind.id,
            "model.value.operation.multiplication",
        )
        branch = statements[2]
        self.assertEqual(branch.kind.id, "model.statement.branch")
        paths = children(branch, "paths")
        self.assertEqual(
            child(paths[0], "condition").kind.id,
            "model.value.operation.comparison.greater_equal",
        )
        self.assertIsNone(paths[1].get("condition"))
        for path, expected_kind, expected_value in (
            (paths[0], "model.value.literal", 0),
            (paths[1], "model.value.named", "STANDARD_SHIPPING_FEE"),
        ):
            block = child(path, "body")
            self.assertEqual(block.kind.id, "model.statement.block")
            (assignment,) = children(block, "statements")
            self.assertEqual(assignment.kind.id, "model.statement.assignment")
            self.assertEqual(
                children(assignment, "targets")[0].get("name"), "shipping_fee"
            )
            value = child(assignment, "value")
            self.assertEqual(value.kind.id, expected_kind)
            self.assertEqual(
                value.get("value" if path is paths[0] else "name"), expected_value
            )
        self.assertEqual(statements[3].kind.id, "model.statement.return")
        self.assertEqual(
            child(statements[3], "value").kind.id, "model.value.operation.addition"
        )

    def test_walk_and_roles_expose_every_model_instance(self) -> None:
        nodes = tuple(self.model.walk())
        self.assertEqual(len(nodes), 48)
        self.assertEqual(nodes[0], self.model)
        self.assertEqual(
            sum(node.kind.id == "model.statement.assignment" for node in nodes), 4
        )
        defined_ids = {kind.id for kind in shikake.definition_index().all_kinds()}
        for node in nodes:
            self.assertEqual(
                tuple(part.role for part in node.parts()),
                tuple(
                    spec.role
                    for spec in shikake.definition_index()
                    .require_structure(node.kind.id)
                    .parts
                ),
            )
            self.assertIn(node.kind.id, defined_ids)

    def test_location_and_index_access_are_preserved(self) -> None:
        function = children(self.model, "body")[2]
        subscript = child(children(child(function, "body"), "statements")[0], "value")
        self.assertEqual(child(subscript, "target").get("name"), "prices")
        self.assertEqual(child(subscript, "index").get("name"), "sku")
        self.assertIsNotNone(subscript.span)

    def test_nested_attribute_as_index(self) -> None:
        source = "def f():\n    x = remaining[line.sku]\n"
        root = shikake.parse_source(source)
        function = children(root, "body")[0]
        subscript = child(children(child(function, "body"), "statements")[0], "value")
        self.assertEqual(subscript.kind.id, "model.value.access.index")
        attribute = child(subscript, "index")
        self.assertEqual(attribute.kind.id, "model.value.access.attribute")
        self.assertEqual(child(attribute, "target").get("name"), "line")
        self.assertEqual(attribute.get("attribute"), "sku")

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_unsupported_syntax_rejected_not_dropped(self) -> None:
        for source, expected in (
            ("type Alias = int\n", "TypeAlias"),
            ("class A:\n    type Alias = int\n", "TypeAlias"),
            ("def f():\n    type Alias = int\n", "TypeAlias"),
        ):
            with self.subTest(source=source):
                with self.assertRaises(shikake.UnsupportedSyntaxError) as caught:
                    shikake.parse_source(source)
                self.assertIn(expected, str(caught.exception))
        with self.assertRaises(SyntaxError):
            shikake.parse_source("if:")

    def test_no_python_execution_during_modeling(self) -> None:
        model = shikake.parse_source("__import__('os').system('echo should-not-run')")
        self.assertEqual(len(tuple(model.walk())), 8)  # only inspects, never executes


if __name__ == "__main__":
    unittest.main()
