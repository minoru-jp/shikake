"""Regression coverage for iterative package relation and binding analysis."""

from __future__ import annotations

import ast
import unittest

from shikake import inspect_source, parse_source
from shikake._mica.ast_facts import _target_names, collect_syntax_facts
from shikake._mica.kinds import definition_index
from shikake._mica.parser import _Builder
from shikake._mica.relation_analysis import _analyze_package_facts


def _method(name: str = "action") -> ast.FunctionDef:
    return ast.FunctionDef(
        name=name,
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        ),
        body=[ast.Pass()],
        decorator_list=[],
    )


def _class(
    name: str, *, base: str | None = None, body: list[ast.stmt] | None = None
) -> ast.ClassDef:
    return ast.ClassDef(
        name=name,
        bases=[ast.Name(id=base, ctx=ast.Load())] if base else [],
        keywords=[],
        decorator_list=[],
        body=body if body is not None else [_method()],
    )


def _candidates_for(statements: list[ast.stmt]):
    tree = ast.Module(body=statements, type_ignores=[])
    syntax = collect_syntax_facts(tree)
    builder = _Builder(definition_index())
    module = builder.module(tree, name="sample.mod")
    return _analyze_package_facts(
        {"sample.mod": (module, False)},
        frozenset({"inheritance", "override"}),
        {"sample.mod": (syntax, builder.statement_models)},
    )


class DeepPackageRelationsTests(unittest.TestCase):
    def test_deep_boolean_alternation_source_strict_and_partial(self) -> None:
        source = "flag = value" + " and item or value" * 2200 + "\n"
        strict = parse_source(source)
        partial = inspect_source(source)
        self.assertTrue(partial.complete)
        self.assertEqual(strict, partial.model)
        self.assertEqual(len(list(strict.walk())), 6605)

    def test_deep_control_block_invalidates_base_binding(self) -> None:
        rebound: ast.stmt = ast.Assign(
            targets=[ast.Name(id="Base", ctx=ast.Store())],
            value=ast.Name(id="unknown", ctx=ast.Load()),
        )
        for i in range(2200):
            if i % 2:
                rebound = ast.If(
                    test=ast.Name(id="flag", ctx=ast.Load()), body=[rebound], orelse=[]
                )
            else:
                rebound = ast.While(
                    test=ast.Name(id="flag", ctx=ast.Load()), body=[rebound], orelse=[]
                )
        candidates, bases, _ = _candidates_for(
            [_class("Base"), rebound, _class("Child", base="Base")]
        )
        self.assertEqual(len(candidates), 1)
        self.assertTrue(bases[-1].binding.may_rebind)  # type: ignore[union-attr]

    def test_deep_class_method_discovery_preserves_candidate(self) -> None:
        method: ast.stmt = _method()
        for i in range(2200):
            method = (
                ast.If(
                    test=ast.Name(id="flag", ctx=ast.Load()), body=[method], orelse=[]
                )
                if i % 2
                else ast.With(
                    items=[
                        ast.withitem(
                            context_expr=ast.Name(id="context", ctx=ast.Load())
                        )
                    ],
                    body=[method],
                )
            )
        result, _bases, _ = _candidates_for(
            [_class("Base", body=[method]), _class("Child", base="Base")]
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].base_method.get("name"), "action")
        self.assertEqual(result[0].method.get("name"), "action")

    def test_deep_nested_assignment_target_invalidates_base(self) -> None:
        target: ast.expr = ast.Name(id="Base", ctx=ast.Store())
        for i in range(1900):
            target = (
                ast.Tuple(elts=[target], ctx=ast.Store())
                if i % 2
                else ast.List(elts=[target], ctx=ast.Store())
            )
        self.assertEqual(tuple(name for name, _ in _target_names(target)), ("Base",))
        result, bases, _ = _candidates_for(
            [
                _class("Base"),
                ast.Assign(
                    targets=[target], value=ast.Name(id="other", ctx=ast.Load())
                ),
                _class("Child", base="Base"),
            ]
        )
        self.assertEqual(len(result), 1)
        self.assertTrue(bases[-1].binding.may_rebind)  # type: ignore[union-attr]

    def test_deep_pattern_capture_invalidates_base(self) -> None:
        pattern: ast.pattern = ast.MatchAs(name="Base")
        for i in range(1900):
            pattern = (
                ast.MatchAs(pattern=pattern, name=None)
                if i % 2
                else ast.MatchSequence(patterns=[pattern])
            )
        result, bases, _ = _candidates_for(
            [
                _class("Base"),
                ast.Match(
                    subject=ast.Name(id="subject", ctx=ast.Load()),
                    cases=[
                        ast.match_case(pattern=pattern, guard=None, body=[ast.Pass()])
                    ],
                ),
                _class("Child", base="Base"),
            ]
        )
        self.assertEqual(len(result), 1)
        self.assertTrue(bases[-1].binding.may_rebind)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
