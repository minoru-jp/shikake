"""Deep expression families should not depend on Python call-stack depth."""

from __future__ import annotations

import ast
import unittest

from shikake import inspect_source, parse_source
from shikake._mica.kinds import kind_index
from shikake._mica.parser import _Builder


def _lambda_args(*, default: ast.expr) -> ast.arguments:
    return ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg="param")],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[default],
    )


class DeepRemainingExpressionsTests(unittest.TestCase):
    def test_deep_collections_preserve_nested_roles(self) -> None:
        expression: ast.expr = ast.Name(id="leaf", ctx=ast.Load())
        for depth in range(1500):
            if depth % 3 == 0:
                expression = ast.List(elts=[expression], ctx=ast.Load())
            elif depth % 3 == 1:
                expression = ast.Tuple(elts=[expression], ctx=ast.Load())
            else:
                expression = ast.Dict(
                    keys=[ast.Constant(value="key")], values=[expression]
                )
        builder = _Builder(kind_index())
        modeled = builder.expression(expression)
        kinds = [item.kind.id for item in modeled.walk()]
        self.assertEqual(kinds[0], "model.value.collection.mapping")
        self.assertEqual(kinds[-1], "model.value.named")
        self.assertIn("model.structural_part.dictionary_entry", kinds)
        self.assertEqual(modeled, builder.expression(expression))

    def test_deep_comprehensions_mixed_with_collection_values(self) -> None:
        expression: ast.expr = ast.Name(id="leaf", ctx=ast.Load())
        for depth in range(1350):
            generators = [
                ast.comprehension(
                    target=ast.Name(id="item", ctx=ast.Store()),
                    iter=ast.Name(id="items", ctx=ast.Load()),
                    ifs=[ast.Name(id="allowed", ctx=ast.Load())],
                    is_async=0,
                )
            ]
            if depth % 4 == 0:
                expression = ast.ListComp(elt=expression, generators=generators)
            elif depth % 4 == 1:
                expression = ast.SetComp(elt=expression, generators=generators)
            elif depth % 4 == 2:
                expression = ast.GeneratorExp(elt=expression, generators=generators)
            else:
                expression = ast.DictComp(
                    key=ast.Constant(value="key"),
                    value=expression,
                    generators=generators,
                )
        model = _Builder(kind_index()).expression(expression)
        kinds = [item.kind.id for item in model.walk()]
        self.assertEqual(
            kinds.count("model.structural_part.comprehension_clause"), 1350
        )
        self.assertIn("model.value.comprehension.dict", kinds)
        self.assertIn("model.value.comprehension.list", kinds)
        self.assertEqual(model, _Builder(kind_index()).expression(expression))

    def test_deep_format_strings_and_format_specs(self) -> None:
        expression: ast.expr = ast.Constant(value="leaf")
        for _ in range(1400):
            expression = ast.JoinedStr(
                values=[
                    ast.FormattedValue(
                        value=ast.Constant(value=1),
                        conversion=-1,
                        format_spec=expression,
                    )
                ]
            )
        model = _Builder(kind_index()).expression(expression)
        kinds = [item.kind.id for item in model.walk()]
        self.assertEqual(kinds.count("model.value.interpolated_string"), 1400)
        self.assertEqual(kinds.count("model.structural_part.formatted_field"), 1400)
        self.assertEqual(model, _Builder(kind_index()).expression(expression))

    def test_nested_lambda_defaults_do_not_recurse(self) -> None:
        expression: ast.expr = ast.Constant(value=5)
        for _ in range(1250):
            expression = ast.Lambda(
                args=_lambda_args(default=expression),
                body=ast.Name(id="param", ctx=ast.Load()),
            )
        model = _Builder(kind_index()).expression(expression)
        kinds = [part.kind.id for part in model.walk()]
        self.assertEqual(kinds.count("model.value.function_expression"), 1250)
        self.assertEqual(kinds.count("model.definition.parameter"), 1250)

    def test_nested_comparisons_and_named_expressions(self) -> None:
        expression: ast.expr = ast.Constant(value=0)
        for depth in range(1400):
            if depth % 2:
                expression = ast.Compare(
                    left=expression,
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=2)],
                )
            else:
                expression = ast.NamedExpr(
                    target=ast.Name(id="result", ctx=ast.Store()),
                    value=expression,
                )
        model = _Builder(kind_index()).expression(expression)
        kinds = [part.kind.id for part in model.walk()]
        self.assertEqual(kinds.count("model.value.binding"), 700)
        self.assertEqual(kinds.count("model.value.operation.comparison.equal"), 700)

    def test_source_forms_keep_strict_partial_equivalence(self) -> None:
        source = (
            'a = [{"x": x} for x in items if x > 0]\n'
            'b = f"{a!r:>10}"\n'
            "c = (value := (1, 2, 3))\n"
            "d = {n: n * n for n in range(5)}\n"
            "e = (v for v in values)\n"
            "f = {v for v in values}\n"
        )
        strict = parse_source(source)
        partial = inspect_source(source)
        self.assertTrue(partial.complete)
        self.assertEqual(partial.issues, ())
        self.assertEqual(strict, partial.model)


if __name__ == "__main__":
    unittest.main()
