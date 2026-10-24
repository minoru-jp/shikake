"""v0.0.4 external Type and Generic interfaces: syntax, not runtime types."""

from __future__ import annotations

import unittest

import external_type_generic_definitions as trusted

import shikake
from shikake.external import (
    ExternalDefinitionsBuilder,
    load_external_definitions,
)


def build_definitions():
    return (
        ExternalDefinitionsBuilder()
        .add_type("demo.kinds:int32", "demo.int32")
        .add_generic("demo.kinds:Array", "demo.array", ("element", "size"))
        .add_call("demo.kinds:int32", "demo.int32.call", ("value",))
        .build()
    )


class TypeGenericInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.definitions = build_definitions()

    def parse(self, text):
        inspection = shikake.inspect_source(
            "from demo.kinds import int32, Array\n" + text + "\n",
            definitions=self.definitions,
        )
        self.assertTrue(inspection.complete, inspection.issues)
        assert inspection.model is not None
        return inspection

    def kinds(self, inspection):
        assert inspection.model is not None
        return [m.kind.id for m in inspection.model.walk()]

    def state(self, inspection, name):
        assert inspection.model is not None
        return inspection.bindings_for(inspection.model, name)[0].state

    def test_type_ref_in_annotations_parameters_returns_and_class_bases(self):
        result = self.parse(
            "v: int32 = 1\n"
            "def f(x: int32) -> int32:\n    return x\n"
            "class User(int32):\n    pass"
        )
        self.assertEqual(self.kinds(result).count("demo.int32"), 4)
        self.assertEqual(
            self.state(result, "int32"),
            shikake.BindingState("external", False, False, False),
        )

    def test_generic_with_type_argument(self):
        result = self.parse("v: Array[int32, 4]\n")
        assert result.model is not None
        models = [m for m in result.model.walk() if m.kind.id == "demo.array"]
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].get_node("element").kind.id, "demo.int32")
        self.assertEqual(models[0].get_node("size").get("value"), 4)
        self.assertFalse(self.state(result, "Array").may_value_use)
        self.assertFalse(self.state(result, "int32").may_value_use)

    def test_registered_generic_outside_annotation_not_value_use(self):
        result = self.parse("v = Array[int32, 4]\n")
        self.assertIn("demo.array", self.kinds(result))
        self.assertFalse(self.state(result, "Array").may_value_use)
        self.assertFalse(self.state(result, "int32").may_value_use)

    def test_value_reference_is_still_ordinary_name(self):
        result = self.parse("v = int32\n")
        self.assertNotIn("demo.int32", self.kinds(result))
        self.assertTrue(self.state(result, "int32").may_value_use)

    def test_type_and_call_are_independent(self):
        result = self.parse("v: int32 = int32(5)\n")
        self.assertEqual(self.kinds(result).count("demo.int32"), 1)
        self.assertEqual(self.kinds(result).count("demo.int32.call"), 1)
        self.assertFalse(self.state(result, "int32").may_value_use)

    def test_generic_arity_mismatch_falls_back(self):
        result = self.parse("v = Array[int32]\n")
        self.assertNotIn("demo.array", self.kinds(result))
        self.assertIn("model.value.access.index", self.kinds(result))

    def test_unregistered_generic_is_ordinary_index(self):
        result = shikake.inspect_source(
            "from demo.kinds import Other\nv = Other[int]\n",
            definitions=self.definitions,
        )
        self.assertTrue(result.complete, result.issues)
        assert result.model is not None
        self.assertEqual(
            result.bindings_for(result.model, "Other")[0].state.introduction, "stable"
        )
        self.assertTrue(
            result.bindings_for(result.model, "Other")[0].state.may_value_use
        )
        self.assertIn(
            "model.value.access.index", [m.kind.id for m in result.model.walk()]
        )

    def test_alias_and_module_qualified_type(self):
        from_alias = shikake.parse_source(
            "from demo.kinds import int32 as I32\nv: I32 = 1\n",
            definitions=self.definitions,
        )
        self.assertIn("demo.int32", [m.kind.id for m in from_alias.walk()])
        qualified = shikake.parse_source(
            "import demo.kinds as kinds\nv: kinds.int32 = 1\n",
            definitions=self.definitions,
        )
        self.assertIn("demo.int32", [m.kind.id for m in qualified.walk()])

    def test_conditional_import_and_competing_alias_do_not_specialize(self):
        conditional = shikake.parse_source(
            "if flag:\n    from demo.kinds import int32\nv: int32 = 1\n",
            definitions=self.definitions,
        )
        self.assertNotIn("demo.int32", [m.kind.id for m in conditional.walk()])
        competing = shikake.parse_source(
            "from demo.kinds import int32\nfrom other import int32\nv: int32\n",
            definitions=self.definitions,
        )
        self.assertNotIn("demo.int32", [m.kind.id for m in competing.walk()])

    def test_direct_type_and_generic_coexist_with_imports(self):
        result = shikake.parse_source(
            "from demo.kinds import int32, Array\nv: Array[int32, 4]\n",
            definitions=self.definitions,
        )
        self.assertIn("demo.array", [m.kind.id for m in result.walk()])

    def test_validation_rejects_bad_generic_roles(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            ExternalDefinitionsBuilder().add_generic(
                "demo:Array", "demo.empty", ()
            ).build()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ExternalDefinitionsBuilder().add_generic(
                "demo:Array", "demo.duplicate", ("x", "x")
            ).build()
        with self.assertRaisesRegex(ValueError, "duplicate external"):
            (
                ExternalDefinitionsBuilder()
                .add_type("demo:int32", "demo.first")
                .add_type("demo:int32", "demo.second")
                .build()
            )

    def test_shikumi_definitions_equivalent_to_builder(self):
        built = load_external_definitions(trusted)
        self.assertEqual(len(built.type_mappings), 1)
        self.assertEqual(len(built.generic_mappings), 1)
        output = shikake.parse_source(
            "from demo.kinds import int32, Array\nv: Array[int32, 4]\n",
            definitions=built,
        )
        self.assertIn("demo.array", [m.kind.id for m in output.walk()])
        self.assertIn("demo.type", [m.kind.id for m in output.walk()])


if __name__ == "__main__":
    unittest.main()
