"""Compiler-level validation is opt-out, and never executes analyzed source."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

import shikake
from shikake._mica.parser import _Builder
from shikake.external import ImportedCall


class CompileSyntaxValidationTests(unittest.TestCase):
    def test_default_rejects_ast_parse_only_source(self) -> None:
        sources = (
            "return 42\n",
            "yield 5\n",
            "break\n",
            "continue\n",
            "def f(a, a): pass\n",
            "def f():\n    from other import *\n",
            "f(a=1, a=2)\n",
            "def f():\n    from __future__ import annotations\n",
            "f(x for x in (z := values))\n",
        )
        for source in sources:
            with self.subTest(source=source):
                ast.parse(source)
                with self.assertRaises(SyntaxError):
                    shikake.parse_source(source)
                partial = shikake.inspect_source(source)
                self.assertIsNone(partial.model)
                self.assertEqual(len(partial.issues), 1)
                self.assertEqual(partial.issues[0].code, "syntax.invalid")

    def test_opt_out_ast_mode_allows_modeling_compiler_invalid_constructs(self) -> None:
        for source in ("return 42\n", "break\n", "f(a=1, a=2)\n"):
            with self.subTest(source=source):
                model = shikake.parse_source(source, syntax_validation="ast")
                inspected = shikake.inspect_source(source, syntax_validation="ast")
                self.assertTrue(inspected.complete, inspected.issues)
                self.assertEqual(model, inspected.model)

    def test_invalid_validation_options_rejected_early(self) -> None:
        for method in (shikake.parse_source, shikake.inspect_source):
            with self.subTest(method=method):
                with self.assertRaises(ValueError):
                    method("", syntax_validation="unknown")  # type: ignore[arg-type]
                with self.assertRaises(TypeError):
                    method("", syntax_validation=cast(Any, None))
        with tempfile.TemporaryDirectory() as folder:
            for method in (shikake.parse_package, shikake.inspect_package):
                with self.subTest(method=method):
                    with self.assertRaises(ValueError):
                        method(folder, syntax_validation="unknown")  # type: ignore[arg-type]
                    with self.assertRaises(TypeError):
                        method(folder, syntax_validation=cast(Any, None))

    def test_utf8_compiler_error_offsets_and_no_source_text(self) -> None:
        source = "f(é=1, é=2)\n"
        error = None
        try:
            compile(ast.parse(source), "unicode.py", "exec", dont_inherit=True)
        except SyntaxError as raised:
            error = raised
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIsNone(error.text)
        inspected = shikake.inspect_source(source, filename="unicode.py")
        (issue,) = inspected.issues
        self.assertEqual(issue.line, 1)
        self.assertEqual(issue.column, len("f(é=1, ".encode()))
        self.assertEqual(issue.filename, "unicode.py")
        self.assertEqual(issue.skipped_span, None)

    def test_compilation_does_not_run_imports_or_expressions(self) -> None:
        source = "import impossible_dependency_for_shikake_test\nraise RuntimeError('not run')\n"
        self.assertTrue(shikake.inspect_source(source).complete)

    def test_package_strict_and_partial_are_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "code"
            folder.mkdir()
            (folder / "valid.py").write_text("x = 1\n", encoding="utf-8")
            (folder / "invalid.py").write_text("return 42\n", encoding="utf-8")
            with self.assertRaises(SyntaxError):
                shikake.parse_package(folder)
            partial = shikake.inspect_package(folder)
            self.assertFalse(partial.complete)
            self.assertEqual(len(partial.issues), 1)
            self.assertEqual(partial.issues[0].filename, str(folder / "invalid.py"))
            self.assertEqual(partial.issues[0].column, 0)
            self.assertEqual(len(partial.package.model.get_nodes("modules")), 1)
            strict_ast = shikake.parse_package(folder, syntax_validation="ast")
            partial_ast = shikake.inspect_package(folder, syntax_validation="ast")
            self.assertTrue(partial_ast.complete)
            self.assertEqual(strict_ast.model, partial_ast.model)

    def test_future_wrong_location_is_compiler_invalid_even_if_policy_allows(
        self,
    ) -> None:
        source = "def f():\n    from __future__ import annotations\n"
        strict_ast = shikake.inspect_source(
            source, import_policy="registered_interfaces", syntax_validation="ast"
        )
        self.assertTrue(strict_ast.complete, strict_ast.issues)
        inspected = shikake.inspect_source(
            source, import_policy="registered_interfaces"
        )
        self.assertEqual(inspected.issues[0].code, "syntax.invalid")

    def test_first_import_policy_violation_follows_source_order(self) -> None:
        source = "def f():\n    import os\n\nimport sys\n"
        inspected = shikake.inspect_source(
            source, import_policy="registered_interfaces", syntax_validation="ast"
        )
        self.assertEqual(inspected.issues[0].code, "external.unregistered_import")
        self.assertEqual(inspected.issues[0].details["path"], "os")
        self.assertEqual(inspected.issues[0].line, 2)

    def test_imported_call_rejects_reserved_word_components(self) -> None:
        for target in (
            "pkg:Cls.class",
            "pkg.class:Cls.make",
            "class:Cls.make",
            "pkg:class.make",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                ImportedCall(target)

    def test_lazy_import_nodes_preserve_explicit_modifier(self) -> None:
        for node_type in (ast.Import, ast.ImportFrom):
            module = ast.parse("import json\n")
            statement = (
                ast.Import(names=[ast.alias(name="json")])
                if node_type is ast.Import
                else ast.ImportFrom(
                    module="json", names=[ast.alias(name="loads")], level=0
                )
            )
            ast.copy_location(statement, module.body[0])
            statement.is_lazy = 1  # type: ignore[attr-defined]  # new on 3.15
            module.body = [statement]
            # Direct builder covers 3.15's AST flag on older interpreters.
            parsed = _Builder(shikake.kind_index()).module(module)
            statement_model = parsed.get_nodes("body")[0]
            self.assertEqual(statement_model.features, ("lazy",))
            self.assertTrue(
                all(not alias.features for alias in statement_model.get_nodes("names"))
            )

    def test_dictcomp_new_shape_is_distinct_pep798_model(self) -> None:
        module = ast.parse("x = {k: v for k in items}")
        assignment = module.body[0]
        assert isinstance(assignment, ast.Assign)
        assert isinstance(assignment.value, ast.DictComp)
        assignment.value.value = cast(Any, None)
        result = _Builder(shikake.kind_index()).module(module)
        expression = result.get_nodes("body")[0].get_node("value")
        self.assertEqual(expression.kind.id, "model.value.collection.mapping")
        (detail,) = expression.get_nodes("inputs")
        self.assertEqual(detail.kind.id, "model.value.comprehension.dict.unpacking")
        self.assertEqual(detail.get_node("mapping").get("name"), "k")
        self.assertEqual(len(detail.get_nodes("clauses")), 1)


if __name__ == "__main__":
    unittest.main()
