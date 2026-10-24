"""Function-first modeling and class decorator integration test."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path
from typing import cast

import shikake
from shikake._mica.model import Model

SAMPLE = Path(__file__).resolve().parents[1] / "tests/fixtures/order_calculation.py"


def items(node: Model, role: str) -> tuple[Model, ...]:
    value = node.get(role)
    assert isinstance(value, tuple)
    assert all(isinstance(item, Model) for item in value)
    return cast(tuple[Model, ...], value)


def item(node: Model, role: str) -> Model:
    value = node.get(role)
    assert isinstance(value, Model)
    return value


def named_definition(root: Model, name: str) -> Model:
    return next(
        model
        for model in items(root, "body")
        if model.kind.id in {"model.definition.function", "model.definition.class"}
        and model.get("name") == name
    )


class FunctionClassModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SAMPLE.read_text(encoding="utf-8")
        self.root = shikake.parse_source(self.source)

    def test_sample_complete_and_contract_index_consistent(self) -> None:
        self.assertTrue(shikake.inspect_source(self.source).complete)
        index = shikake.kind_index()
        kinds = index.all_kinds()
        self.assertEqual(len(kinds), 142)
        self.assertEqual(len({kind.id for kind in kinds}), len(kinds))
        nodes = tuple(self.root.walk())
        self.assertEqual(len(nodes), 170)
        for node in nodes:
            self.assertIs(node.kind, index.get(node.kind.id))
            self.assertEqual(
                tuple(part.role for part in node.parts()),
                tuple(
                    contract.role
                    for contract in shikake.kind_index()
                    .require_structure(node.kind.id)
                    .parts
                ),
            )
        self.assertTrue(
            index.is_a("model.definition.method", "model.definition.function")
        )
        self.assertTrue(
            index.is_a(
                "model.structural_part.keyword_argument", "model.structural_part"
            )
        )
        self.assertFalse(
            index.is_a("model.structural_part.keyword_argument", "model.value.call")
        )
        self.assertFalse(
            index.is_a(
                "model.structural_part.dictionary_entry",
                "model.value.collection.mapping",
            )
        )

    def test_function_parameters_distinguish_forms_and_default_expressions(
        self,
    ) -> None:
        line_amount = named_definition(self.root, "line_amount")
        params = items(line_amount, "parameters")
        self.assertEqual([p.get("name") for p in params], ["price", "quantity"])
        self.assertEqual([p.get("category") for p in params], ["positional_only"] * 2)
        self.assertIsNone(params[0].get("default"))
        self.assertEqual(item(params[1], "default").get("value"), 1)
        subtotal = named_definition(self.root, "subtotal")
        subtotal_params = items(subtotal, "parameters")
        self.assertEqual(
            [p.get("category") for p in subtotal_params],
            ["var_positional", "keyword_only"],
        )
        self.assertEqual(item(subtotal_params[1], "default").get("value"), 0)
        checkout = named_definition(self.root, "checkout")
        checkout_params = items(checkout, "parameters")
        self.assertEqual(
            [p.get("category") for p in checkout_params],
            ["positional_or_keyword", "keyword_only", "keyword_only"],
        )
        self.assertEqual(
            item(checkout_params[0], "annotation").kind.id, "model.value.access.index"
        )

    def test_decorated_abc_and_dataclass_are_not_reclassified(self) -> None:
        abc = named_definition(self.root, "ShippingPolicy")
        self.assertEqual(abc.kind.id, "model.definition.class")
        self.assertEqual(item(abc, "body").kind.id, "model.statement.block")
        self.assertEqual(items(abc, "bases")[0].get("name"), "ABC")
        fee = next(
            n
            for n in items(item(abc, "body"), "statements")
            if n.kind.id == "model.definition.method"
        )
        self.assertEqual(items(fee, "decorators")[0].get("name"), "abstractmethod")
        self.assertEqual(
            items(item(fee, "body"), "statements")[0].kind.id, "model.statement.raise"
        )
        std = named_definition(self.root, "StandardShipping")
        self.assertEqual(std.kind.id, "model.definition.class")
        (decorator,) = items(std, "decorators")
        self.assertEqual(decorator.kind.id, "model.value.call")
        self.assertEqual(item(decorator, "callee").get("name"), "dataclass")
        (option,) = items(decorator, "arguments")
        self.assertEqual(option.kind.id, "model.structural_part.keyword_argument")
        self.assertEqual(option.get("name"), "frozen")
        self.assertIs(item(option, "value").get("value"), True)
        methods = [
            n
            for n in items(item(std, "body"), "statements")
            if n.kind.id == "model.definition.method"
        ]
        self.assertEqual(
            [m.get("name") for m in methods], ["fee", "for_members", "valid_amount"]
        )
        self.assertEqual(items(methods[1], "decorators")[0].get("name"), "classmethod")
        self.assertEqual(items(methods[2], "decorators")[0].get("name"), "staticmethod")

    def test_call_argument_kinds_and_order_preserved(self) -> None:
        sample = named_definition(self.root, "sample_order")
        return_node = items(item(sample, "body"), "statements")[-1]
        call = item(return_node, "value")
        self.assertEqual(call.kind.id, "model.value.call")
        args = items(call, "arguments")
        self.assertEqual(
            [arg.kind.id for arg in args],
            [
                "model.value.named",
                "model.structural_part.keyword_argument",
                "model.structural_part.keyword_argument",
            ],
        )
        self.assertEqual(args[1].get("name"), "policy")
        self.assertIsNone(args[2].get("name"))  # **options
        self.assertEqual(item(args[2], "value").get("name"), "options")
        source = "def f():\n    return target(flag=True, *xs, **opts)\n"
        root = shikake.parse_source(source)
        function = items(root, "body")[0]
        call = item(items(item(function, "body"), "statements")[0], "value")
        self.assertEqual(
            [arg.kind.id for arg in items(call, "arguments")],
            [
                "model.structural_part.keyword_argument",
                "model.structural_part.starred_argument",
                "model.structural_part.keyword_argument",
            ],
        )

    def test_keyword_only_defaults_and_double_star_parameter(self) -> None:
        source = "def f(a, /, b=2, *xs: int, flag=True, **opts):\n    return a\n"
        function = items(shikake.parse_source(source), "body")[0]
        params = items(function, "parameters")
        self.assertEqual(
            [p.get("category") for p in params],
            [
                "positional_only",
                "positional_or_keyword",
                "var_positional",
                "keyword_only",
                "var_keyword",
            ],
        )
        self.assertEqual(
            [p.get("default") is None for p in params], [True, False, True, False, True]
        )

    def test_function_type_comments_do_not_prevent_method_modeling(self) -> None:
        source = "class C:\n    def f(self):  # type: () -> int\n        return 1\n"
        root = shikake.parse_source(source)
        (cls,) = items(root, "body")
        (method,) = items(item(cls, "body"), "statements")
        self.assertEqual(method.kind.id, "model.definition.method")
        self.assertTrue(shikake.inspect_source(source).complete)

    def test_sample_program_is_a_coherent_example(self) -> None:
        # This executes only the trusted sample, not input passed to Mica.
        namespace = runpy.run_path(str(SAMPLE))
        self.assertEqual(namespace["sample_order"](), 3100)


if __name__ == "__main__":
    unittest.main()
