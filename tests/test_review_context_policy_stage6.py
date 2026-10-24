"""Shared AST context, wildcard boundaries, and delegated import checks."""

from __future__ import annotations

import unittest

import shikake
from shikake.external import ExternalDefinitionsBuilder


class ReviewContextPolicyTests(unittest.TestCase):
    def test_long_external_call_chain_retains_registered_kind(self) -> None:
        definitions = (
            ExternalDefinitionsBuilder()
            .add_call("demo.ops:f", "demo.operation.f", ("value",))
            .build()
        )
        n = 240
        source = "from demo.ops import f\nresult = " + "+".join(["f(a)"] * n)
        result = shikake.inspect_source(source, definitions=definitions)
        self.assertTrue(result.complete, result.issues)
        assert result.model is not None
        self.assertEqual(
            sum(node.kind.id == "demo.operation.f" for node in result.model.walk()),
            n,
        )

    def test_registered_generic_slice_is_not_a_value_use(self) -> None:
        definitions = (
            ExternalDefinitionsBuilder()
            .add_type("demo.kinds:Integer", "demo.integer")
            .add_generic("demo.kinds:Array", "demo.array", ("item",))
            .build()
        )
        source = "from demo.kinds import Array, Integer\nresult = " + "+".join(
            ["Array[Integer]"] * 240
        )
        result = shikake.inspect_source(source, definitions=definitions)
        self.assertTrue(result.complete, result.issues)
        assert result.model is not None
        for name in ("Array", "Integer"):
            (binding,) = result.bindings_for(result.model, name)
            self.assertFalse(binding.state.may_value_use, name)
        self.assertEqual(
            sum(node.kind.id == "demo.array" for node in result.model.walk()),
            240,
        )

    def test_nested_expression_shadows_remain_lexical(self) -> None:
        for source in (
            "result = [list(x) for list in items]",
            "result = (lambda list: list(x))(fn)",
            "result = (lambda: (list := fn)(x))()",
        ):
            with self.subTest(source=source):
                modeled = shikake.parse_source(source)
                self.assertTrue(
                    any(n.kind.id == "model.value.call" for n in modeled.walk())
                )
        modeled = shikake.parse_source("result = list(x) + list(y)")
        self.assertEqual(
            sum(n.kind.id == "model.value.collection.sequence" for n in modeled.walk()),
            2,
        )

    def test_deny_module_member_path_does_not_widen_allow(self) -> None:
        policy = shikake.ImportPolicy(default="deny", allow=("os",), deny=("os.path",))
        for source in (
            "import os.path",
            "from os.path import join",
            "from os import path",
        ):
            with self.subTest(source=source):
                result = shikake.inspect_source(source, import_policy=policy)
                self.assertFalse(result.complete)
                self.assertEqual(result.issues[0].category, "import_policy")
        for source in ("import os", "from os import environ", "from os import pathish"):
            with self.subTest(source=source):
                self.assertTrue(
                    shikake.inspect_source(source, import_policy=policy).complete
                )

    def test_no_external_mapping_mismatch_exception_is_exported(self) -> None:
        self.assertNotIn("ExternalModelingError", shikake.__all__)
        self.assertFalse(hasattr(shikake, "ExternalModelingError"))
        definitions = (
            ExternalDefinitionsBuilder()
            .add_call("demo.ops:f", "demo.operation.f", ("left", "right"))
            .build()
        )
        modeled = shikake.parse_source(
            "from demo.ops import f\nvalue = f(1)", definitions=definitions
        )
        self.assertIn("model.value.call", {n.kind.id for n in modeled.walk()})


if __name__ == "__main__":
    unittest.main()
