"""Stage 4: bounded tree diagnostics and single-source lexical binding facts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as memory

import shikake


class SingleSourceBindingsTests(unittest.TestCase):
    def test_module_and_nested_function_scopes(self) -> None:
        result = shikake.inspect_source(
            "x = 1\ndef work(arg):\n    local = arg\n    x = 2\n    return local\n"
        )
        self.assertTrue(result.complete)
        assert result.model is not None
        module = result.model
        function = next(
            m for m in module.walk() if m.kind.id == "model.definition.function"
        )
        recorded = {(v.scope.kind.id, v.name): v for v in result.name_bindings}
        self.assertIs(recorded[("model.module", "x")].scope, module)
        self.assertIs(recorded[("model.module", "work")].scope, module)
        self.assertIs(recorded[("model.definition.function", "arg")].scope, function)
        self.assertEqual(
            recorded[("model.definition.function", "arg")].state.may_rebind, False
        )
        self.assertFalse(recorded[("model.definition.function", "x")].state.may_rebind)
        self.assertEqual({v.module for v in result.name_bindings}, {"<source>"})

    def test_same_binding_states_as_package(self) -> None:
        code = "class Store:\n    value = 1\ndef run(x):\n    x = 2\n    return x\n"
        source = shikake.inspect_source(code)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "sample"
            directory.mkdir()
            (directory / "only.py").write_text(code, encoding="utf-8")
            package = shikake.parse_package(directory, analyses=set())
        normalize = lambda bindings: sorted(
            (
                b.scope.kind.id,
                b.name,
                b.state.introduction,
                b.state.may_rebind,
                b.state.may_delete,
            )
            for b in bindings
        )
        self.assertEqual(
            normalize(source.name_bindings), normalize(package.name_bindings)
        )

    def test_syntax_error_has_no_bindings(self) -> None:
        result = shikake.inspect_source("x =\n")
        self.assertIsNone(result.model)
        self.assertFalse(result.complete)
        self.assertEqual(result.name_bindings, ())

    def test_incomplete_local_external_model_has_no_bindings(self) -> None:
        result = shikake.inspect_source(
            "from framework.memory import Memory\nok = 1\nbad = Memory.unknown(2)\n",
            definitions=memory,
        )
        self.assertIsNotNone(result.model)
        self.assertFalse(result.complete)
        self.assertEqual(result.name_bindings, ())

    def test_file_wide_external_violation_has_no_bindings(self) -> None:
        result = shikake.inspect_source(
            "from framework.memory import Memory\nMemory = 5\n", definitions=memory
        )
        self.assertIsNone(result.model)
        self.assertEqual(result.name_bindings, ())

    def test_existing_source_inspection_positional_construction(self) -> None:
        result = shikake.SourceInspection(None, ())
        self.assertEqual(result.name_bindings, ())


class ModelTreeDisplayTests(unittest.TestCase):
    def test_shows_roles_values_and_source_spans(self) -> None:
        model = shikake.parse_source("total = 2 + 3\n")
        rendered = shikake.format_model_tree(model)
        self.assertIn("model.module", rendered)
        self.assertIn("body[0]:", rendered)
        self.assertIn("model.value.operation.addition", rendered)
        self.assertIn("total", rendered)
        self.assertIn("@1:", rendered)

    def test_shows_features_without_recursive_repr(self) -> None:
        model = shikake.parse_source("async def run():\n    return 1\n")
        shown = shikake.format_model_tree(model)
        self.assertIn("features=", shown)
        self.assertIn("model.definition.function", shown)

    def test_depth_limit_keeps_root_and_marks_elision(self) -> None:
        model = shikake.parse_source("x = 1 + 2\n")
        shown = shikake.format_model_tree(model, max_depth=0)
        self.assertIn("model.module", shown)
        self.assertIn("max_depth reached", shown)
        self.assertNotIn("model.statement.assignment", shown)

    def test_node_limit_and_character_limit(self) -> None:
        model = shikake.parse_source("\n".join(f"n{i} = {i}" for i in range(500)))
        shown = shikake.format_model_tree(model, max_nodes=4, max_chars=400)
        self.assertLessEqual(len(shown), 400)
        self.assertIn("max_nodes reached", shown)
        self.assertLessEqual(len(shikake.format_model_tree(model, max_chars=80)), 80)

    def test_large_scalar_values_remain_bounded(self) -> None:
        model = shikake.parse_source("x = " + repr("a" * 100_000))
        shown = shikake.format_model_tree(model, max_chars=200)
        self.assertLessEqual(len(shown), 200)

    def test_deep_tree_does_not_recurse(self) -> None:
        model = shikake.parse_source("x = " + "+".join("1" for _ in range(250)))
        shown = shikake.format_model_tree(
            model, max_depth=300, max_nodes=500, max_chars=1200
        )
        self.assertLessEqual(len(shown), 1200)
        self.assertIn("model.module", shown)

    def test_invalid_limits_are_rejected(self) -> None:
        model = shikake.parse_source("pass")
        for kwargs in ({"max_depth": -1}, {"max_nodes": 0}, {"max_chars": 3}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                shikake.format_model_tree(model, **kwargs)


if __name__ == "__main__":
    unittest.main()
