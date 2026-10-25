"""Regression tests for iterative statement/block modeling."""

from __future__ import annotations

import ast
import sys
import unittest
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

from shikake import Model, inspect_source, parse_source
from shikake._mica.kinds import definition_index
from shikake._mica.parser import UnsupportedSyntaxError, _Builder


def _module(statement: ast.stmt) -> Model:
    return _Builder(definition_index()).module(
        ast.Module(body=[statement], type_ignores=[])
    )


class IterativeStatementTests(unittest.TestCase):
    def test_deep_if_and_while_blocks(self) -> None:
        statement: ast.stmt = ast.Pass()
        for index in range(3000):
            statement = (
                ast.If(
                    test=ast.Name(id="condition", ctx=ast.Load()),
                    body=[statement],
                    orelse=[],
                )
                if index % 2 == 0
                else ast.While(
                    test=ast.Name(id="condition", ctx=ast.Load()),
                    body=[statement],
                    orelse=[],
                )
            )
        model = _module(statement)
        self.assertEqual(len(list(model.walk())), 10502)
        self.assertEqual(model, _module(statement))

    def test_deep_functions_classes_and_exception_blocks(self) -> None:
        statement: ast.stmt = ast.Pass()
        args = ast.arguments(
            posonlyargs=[],
            args=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        for index in range(1500):
            if index % 3 == 0:
                statement = ast.FunctionDef(
                    name="nested",
                    args=args,
                    body=[statement],
                    decorator_list=[],
                )
            elif index % 3 == 1:
                statement = ast.ClassDef(
                    name="Nested",
                    bases=[],
                    keywords=[],
                    body=[statement],
                    decorator_list=[],
                )
            else:
                statement = ast.Try(
                    body=[statement], handlers=[], orelse=[], finalbody=[ast.Pass()]
                )
        model = _module(statement)
        self.assertGreater(len(list(model.walk())), 4000)
        self.assertEqual(model, _module(statement))

    def test_deep_elif_chain_does_not_expand_quadratically(self) -> None:
        statement: ast.If = ast.If(
            test=ast.Name(id="flag", ctx=ast.Load()),
            body=[ast.Pass()],
            orelse=[],
            lineno=1,
            col_offset=0,
        )
        for _ in range(1700):
            statement = ast.If(
                test=ast.Name(id="flag", ctx=ast.Load()),
                body=[ast.Pass()],
                orelse=[statement],
                lineno=1,
                col_offset=0,
            )
        model = _module(statement)
        (branch,) = cast(tuple[Model, ...], model.get("body"))
        self.assertEqual(len(cast(tuple[Model, ...], branch.get("paths"))), 1701)

    def test_deep_match_and_with_blocks(self) -> None:
        statement: ast.stmt = ast.Pass()
        for index in range(1200):
            if index % 2:
                statement = ast.With(
                    items=[
                        ast.withitem(
                            context_expr=ast.Name(id="manager", ctx=ast.Load()),
                            optional_vars=None,
                        )
                    ],
                    body=[statement],
                    type_comment=None,
                )
            else:
                statement = ast.Match(
                    subject=ast.Name(id="subject", ctx=ast.Load()),
                    cases=[
                        ast.match_case(
                            pattern=ast.MatchAs(pattern=None, name=None),
                            guard=None,
                            body=[statement],
                        )
                    ],
                )
        model = _module(statement)
        self.assertGreater(len(list(model.walk())), 3000)
        self.assertEqual(model, _module(statement))

    def test_nested_source_is_unchanged_between_strict_and_partial(self) -> None:
        source = (
            "class C:\n"
            "    if flag:\n"
            "        def m(self):\n"
            "            try:\n"
            "                with manager:\n"
            "                    for item in items:\n"
            "                        pass\n"
            "            finally:\n"
            "                pass\n"
        )
        strict = parse_source(source)
        partial = inspect_source(source)
        self.assertTrue(partial.complete)
        self.assertEqual(strict, partial.model)
        self.assertTrue(
            any(node.kind.id == "model.definition.method" for node in strict.walk())
        )

    @unittest.skipUnless(sys.version_info >= (3, 12), "PEP 695 syntax")
    @simulate_unadopted_syntax(generic_class=True)
    def test_unsupported_parent_hides_nested_issues(self) -> None:
        source = "before = 1\nclass C[T]:\n    type Nested = int\nafter = 2\n"
        result = inspect_source(source)
        self.assertFalse(result.complete)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].node_type, "ClassDef")
        self.assertEqual(result.issues[0].skipped_node_type, "ClassDef")
        assert result.model is not None
        self.assertEqual(len(cast(tuple[Model, ...], result.model.get("body"))), 2)
        with self.assertRaises(UnsupportedSyntaxError) as exc:
            parse_source(source)
        self.assertEqual(exc.exception.node_type, "ClassDef")

    @unittest.skipUnless(sys.version_info >= (3, 12), "PEP 695 syntax")
    @simulate_unadopted_syntax()
    def test_partial_retains_supported_nested_siblings(self) -> None:
        source = (
            "if condition:\n"
            "    before = 1\n"
            "    type Omitted = int\n"
            "    after = 2\n"
            "else:\n"
            "    pass\n"
        )
        result = inspect_source(source)
        self.assertFalse(result.complete)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].node_type, "TypeAlias")
        assert result.model is not None
        (branch,) = cast(tuple[Model, ...], result.model.get("body"))
        first = cast(tuple[Model, ...], branch.get("paths"))[0]
        body = cast(Model, first.get("body"))
        self.assertEqual(len(cast(tuple[Model, ...], body.get("statements"))), 2)


if __name__ == "__main__":
    unittest.main()
