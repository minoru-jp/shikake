"""Regression coverage for Model depth independent of Python recursion limits."""

from __future__ import annotations

import ast
import unittest
from typing import cast

from shikake import Model, inspect_source, parse_source
from shikake._mica.kinds import definition_index
from shikake._mica.parser import _Builder


class DeepModelTests(unittest.TestCase):
    @staticmethod
    def _addition_expression(terms: int, *, last_value: float = 1) -> ast.expr:
        """Build a deep AST without depending on CPython's source parser."""
        expression: ast.expr = ast.Constant(value=1)
        for index in range(1, terms):
            expression = ast.BinOp(
                left=expression,
                op=ast.Add(),
                right=ast.Constant(value=last_value if index == terms - 1 else 1),
            )
        return expression

    @classmethod
    def _addition_module(cls, terms: int, *, last_value: float = 1) -> ast.Module:
        return ast.Module(
            body=[
                ast.Assign(
                    targets=[ast.Name(id="total", ctx=ast.Store())],
                    value=cls._addition_expression(terms, last_value=last_value),
                ),
                ast.Assign(
                    targets=[ast.Name(id="after", ctx=ast.Store())],
                    value=ast.Constant(value=2),
                ),
            ],
            type_ignores=[],
        )

    def test_source_addition_strict_and_partial(self) -> None:
        # Keep the public API test below Python 3.11's ast.parse depth limit.
        # The 3,000-term Builder regression is tested independently below.
        terms = 250
        source = "total = " + " + ".join(["1"] * terms) + "\nafter = 2\n"
        strict = parse_source(source)
        partial = inspect_source(source)
        self.assertTrue(partial.complete)
        self.assertEqual(partial.issues, ())
        self.assertIsNotNone(partial.model)
        self.assertEqual(strict, partial.model)
        self.assertEqual(len(list(strict.walk())), 2 * terms + 5)
        self.assertEqual(strict, parse_source(source))
        self.assertEqual(hash(strict), hash(parse_source(source)))

    def test_three_thousand_term_addition_builder_and_model_operations(self) -> None:
        # The 3,000-term depth exercises shikake, not ast.parse, on every Python.
        tree = self._addition_module(3000)
        model = _Builder(definition_index()).module(tree)
        self.assertEqual(len(list(model.walk())), 6005)
        again = _Builder(definition_index()).module(tree)
        self.assertEqual(model, again)
        self.assertEqual(hash(model), hash(again))

    def test_source_expression_inside_function_and_generator(self) -> None:
        chain = " + ".join(["1"] * 250)
        function_source = "def func():\n    return " + chain + "\n"
        function = parse_source(function_source)
        generator = parse_source("def gen():\n    yield " + chain + "\n")
        body = cast(tuple[Model, ...], function.get("body"))
        self.assertEqual(body[0].kind.id, "model.definition.function")
        gen_body = cast(tuple[Model, ...], generator.get("body"))
        self.assertEqual(gen_body[0].kind.id, "model.definition.function")
        self.assertGreater(len(list(generator.walk())), 500)
        self.assertTrue(inspect_source(function_source).complete)

    def test_deep_expression_inside_function_and_generator_builder(self) -> None:
        # Generator detection and nested expression modeling must both be
        # independent of the depth of an already parsed AST.
        function = ast.FunctionDef(
            name="func",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[ast.Return(value=self._addition_expression(3000))],
            decorator_list=[],
        )
        generator = ast.FunctionDef(
            name="gen",
            args=ast.arguments(
                posonlyargs=[],
                args=[],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[ast.Expr(value=ast.Yield(value=self._addition_expression(3000)))],
            decorator_list=[],
        )
        model = _Builder(definition_index()).module(
            ast.Module(body=[function, generator], type_ignores=[])
        )
        functions = cast(tuple[Model, ...], model.get("body"))
        self.assertEqual(functions[0].kind.id, "model.definition.function")
        self.assertEqual(functions[1].kind.id, "model.definition.function")
        self.assertGreater(len(list(model.walk())), 12000)

    def test_deep_mixed_access_chain(self) -> None:
        # Keep a source-level check, but exercise extreme nesting through an
        # already constructed AST: ast.parse can recurse on Python 3.11.
        source = "value = root" + ".field[0]" * 80
        self.assertEqual(parse_source(source), inspect_source(source).model)

        expression: ast.expr = ast.Name(id="root", ctx=ast.Load())
        for _ in range(1500):
            expression = ast.Attribute(value=expression, attr="field", ctx=ast.Load())
            expression = ast.Subscript(
                value=expression, slice=ast.Constant(value=0), ctx=ast.Load()
            )
        tree = ast.Module(
            body=[
                ast.Assign(
                    targets=[ast.Name(id="value", ctx=ast.Store())],
                    value=expression,
                )
            ],
            type_ignores=[],
        )
        model = _Builder(definition_index()).module(tree)
        nodes = list(model.walk())
        self.assertEqual(len(nodes), 4504)
        self.assertEqual(nodes[0].kind.id, "model.module")
        self.assertEqual(nodes[3].kind.id, "model.value.access.index")
        self.assertEqual(nodes[-1].kind.id, "model.value.literal")
        again = _Builder(definition_index()).module(tree)
        self.assertEqual(model, again)
        self.assertEqual(hash(model), hash(again))

    def test_walk_keeps_role_and_tuple_declaration_order(self) -> None:
        source = "result = f(3, key=2) + obj.member"
        kinds = [item.kind.id for item in parse_source(source).walk()]
        self.assertEqual(
            kinds,
            [
                "model.module",
                "model.statement.assignment",
                "model.value.named",
                "model.value.operation.addition",
                "model.value.call",
                "model.value.named",
                "model.value.literal",
                "model.structural_part.keyword_argument",
                "model.value.literal",
                "model.value.access.attribute",
                "model.value.named",
            ],
        )

    def test_deep_conditional_expression_strict_and_partial(self) -> None:
        # Parser depth/complexity limits vary across CPython versions. Exercise
        # the public APIs on source and the Builder on a deeper valid AST.
        source = "value = " + "1 if flag else " * 80 + "0\nafter = 1\n"
        self.assertTrue(inspect_source(source).complete)
        self.assertEqual(inspect_source(source).model, parse_source(source))
        expression: ast.expr = ast.Constant(value=0)
        for _ in range(3000):
            expression = ast.IfExp(
                test=ast.Name(id="flag", ctx=ast.Load()),
                body=ast.Constant(value=1),
                orelse=expression,
            )
        tree = ast.Module(
            body=[
                ast.Assign(
                    targets=[ast.Name(id="value", ctx=ast.Store())], value=expression
                ),
                ast.Assign(
                    targets=[ast.Name(id="after", ctx=ast.Store())],
                    value=ast.Constant(value=1),
                ),
            ],
            type_ignores=[],
        )
        model = _Builder(definition_index()).module(tree)
        self.assertEqual(len(list(model.walk())), 9007)
        self.assertEqual(model, _Builder(definition_index()).module(tree))

    def test_deep_call_and_lambda_chains(self) -> None:
        self.assertTrue(inspect_source("value = make()()()").complete)
        call: ast.expr = ast.Call(
            func=ast.Name(id="make", ctx=ast.Load()), args=[], keywords=[]
        )
        for _ in range(1800):
            call = ast.Call(func=call, args=[], keywords=[])
        tree = ast.Module(
            body=[
                ast.Assign(targets=[ast.Name(id="value", ctx=ast.Store())], value=call)
            ],
            type_ignores=[],
        )
        calls = _Builder(definition_index()).module(tree)
        self.assertEqual(len(list(calls.walk())), 1805)
        self.assertTrue(inspect_source("value = " + "lambda: " * 15 + "3").complete)
        lambda_body: ast.expr = ast.Constant(value=3)
        for _ in range(1700):
            lambda_body = ast.Lambda(
                args=ast.arguments(
                    posonlyargs=[],
                    args=[],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=lambda_body,
            )
        tree = ast.Module(
            body=[
                ast.Assign(
                    targets=[ast.Name(id="value", ctx=ast.Store())],
                    value=lambda_body,
                )
            ],
            type_ignores=[],
        )
        lambdas = _Builder(definition_index()).module(tree)
        self.assertEqual(len(list(lambdas.walk())), 1704)
        self.assertEqual(lambdas, _Builder(definition_index()).module(tree))

    def test_deep_targets_without_recursion(self) -> None:
        # Construct AST directly: CPython imposes a separate nesting limit on
        # source parentheses, which is deliberately out of scope for shikake.
        target: ast.expr = ast.Name(id="value", ctx=ast.Store())
        for depth in range(1500):
            if depth % 3 == 0:
                target = ast.Starred(value=target, ctx=ast.Store())
            elif depth % 3 == 1:
                target = ast.Tuple(elts=[target], ctx=ast.Store())
            else:
                target = ast.List(elts=[target], ctx=ast.Store())
        model = _Builder(definition_index()).target(target)
        self.assertEqual(len(list(model.walk())), 1501)
        self.assertEqual(model, _Builder(definition_index()).target(target))

    def test_deep_patterns_and_mixed_patterns_without_recursion(self) -> None:
        pattern: ast.pattern = ast.MatchAs(name="item")
        for depth in range(1500):
            if depth % 3 == 0:
                pattern = ast.MatchSequence(patterns=[pattern])
            elif depth % 3 == 1:
                pattern = ast.MatchAs(pattern=pattern, name="alias")
            else:
                pattern = ast.MatchOr(patterns=[pattern])
        model = _Builder(definition_index()).pattern(pattern)
        self.assertEqual(len(list(model.walk())), 1501)
        self.assertEqual(model, _Builder(definition_index()).pattern(pattern))
        complex_pattern = ast.MatchClass(
            cls=ast.Name(id="Example", ctx=ast.Load()),
            patterns=[ast.MatchAs(name="positional")],
            kwd_attrs=["field"],
            kwd_patterns=[
                ast.MatchMapping(
                    keys=[ast.Constant(value="key")],
                    patterns=[ast.MatchAs(name="value")],
                )
            ],
        )
        kinds = [
            item.kind.id
            for item in _Builder(definition_index()).pattern(complex_pattern).walk()
        ]
        self.assertIn("model.pattern.class", kinds)
        self.assertIn("model.pattern.mapping", kinds)
        self.assertIn("model.pattern.capture", kinds)

    def test_call_argument_order_and_starred_role(self) -> None:
        source = "value = f(1, key=2, *more, **options)"
        model = parse_source(source)
        call_kinds = [part.kind.id for part in model.walk()]
        self.assertEqual(
            call_kinds,
            [
                "model.module",
                "model.statement.assignment",
                "model.value.named",
                "model.value.call",
                "model.value.named",
                "model.value.literal",
                "model.structural_part.keyword_argument",
                "model.value.literal",
                "model.structural_part.starred_argument",
                "model.value.named",
                "model.structural_part.keyword_argument",
                "model.value.named",
            ],
        )

    def test_deep_equality_detects_differing_scalar_type(self) -> None:
        # The leaf value is numerically equal but its AST scalar type differs.
        first = _Builder(definition_index()).module(
            self._addition_module(3000, last_value=1)
        )
        second = _Builder(definition_index()).module(
            self._addition_module(3000, last_value=1.0)
        )
        self.assertNotEqual(first, second)
        self.assertNotEqual(hash(first), hash(second))

    def test_deep_equality_detects_differing_leaf(self) -> None:
        # Source parsing is tested above; compare deep Builder results here.
        first = _Builder(definition_index()).module(
            self._addition_module(2301, last_value=2)
        )
        second = _Builder(definition_index()).module(
            self._addition_module(2301, last_value=3)
        )
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
