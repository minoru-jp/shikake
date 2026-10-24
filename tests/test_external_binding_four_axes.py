"""v0.0.4: lightweight syntactic binding/use hints, not usage-policy checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake
from shikake.external import ExternalDefinitions, ExternalDefinitionsBuilder

DEFINITIONS = (
    ExternalDefinitionsBuilder()
    .add_call("demo.kinds:int32", "demo.int32", ("value",))
    .build()
)


class ExternalBindingFourAxesTests(unittest.TestCase):
    def state(
        self,
        source: str,
        name: str,
        *,
        definitions: ExternalDefinitions | None = DEFINITIONS,
    ):
        inspected = shikake.inspect_source(source, definitions=definitions)
        self.assertTrue(inspected.complete, inspected.issues)
        assert inspected.model is not None
        (binding,) = inspected.bindings_for(inspected.model, name)
        return binding.state

    def test_registered_direct_import_is_external_and_call_is_not_value(self) -> None:
        self.assertEqual(
            self.state("from demo.kinds import int32\nresult = int32(10)\n", "int32"),
            shikake.BindingState("external", False, False, False),
        )

    def test_annotation_and_generic_annotation_are_not_value_use(self) -> None:
        source = (
            "from demo.kinds import int32\n"
            "v: int32 = 1\n"
            "def f(x: list[int32]) -> int32: return x[0]\n"
        )
        self.assertFalse(self.state(source, "int32").may_value_use)

    def test_value_reference_and_nested_value_reference_are_detected(self) -> None:
        for expr in ("int32", "[int32]", "call(int32)", "(int32,)"):
            with self.subTest(expr=expr):
                state = self.state(
                    f"from demo.kinds import int32\nresult = {expr}\n", "int32"
                )
                self.assertEqual(state.introduction, "external")
                self.assertTrue(state.may_value_use)

    def test_unregistered_call_is_not_an_interface_use(self) -> None:
        source = "from demo.kinds import other\nresult = other(1)\n"
        self.assertEqual(
            self.state(source, "other"),
            shikake.BindingState("stable", False, False, True),
        )

    def test_generic_outside_annotation_needs_registration(self) -> None:
        state = self.state(
            "from demo.kinds import int32\nresult = int32[32]\n", "int32"
        )
        self.assertTrue(state.may_value_use)

    def test_normal_rebinding_and_deletion_are_not_rejected(self) -> None:
        state = self.state(
            "from demo.kinds import int32\nint32 = 1\ndel int32\n", "int32"
        )
        self.assertEqual(state, shikake.BindingState("external", True, True, False))

    def test_alias_import_and_conditional_introduction(self) -> None:
        self.assertEqual(
            self.state("from demo.kinds import int32 as I32\nx = I32(1)\n", "I32"),
            shikake.BindingState("external", False, False, False),
        )
        self.assertEqual(
            self.state("if flag:\n    from demo.kinds import int32\n", "int32"),
            shikake.BindingState("unstable", False, False, False),
        )

    def test_unregistered_definition_does_not_grant_external_introduction(self) -> None:
        self.assertEqual(
            self.state(
                "from demo.kinds import int32\nx = int32(1)\n",
                "int32",
                definitions=None,
            ),
            shikake.BindingState("stable", False, False, True),
        )

    def test_shadowing_does_not_turn_local_binding_into_external(self) -> None:
        inspection = shikake.inspect_source(
            "from demo.kinds import int32\ndef f():\n    int32 = 1\n    return int32\n",
            definitions=DEFINITIONS,
        )
        self.assertTrue(inspection.complete)
        assert inspection.model is not None
        function = next(
            model
            for model in inspection.model.walk()
            if model.kind.id == "model.definition.function"
        )
        self.assertEqual(
            inspection.bindings_for(function, "int32")[0].state,
            shikake.BindingState("stable", False, False, True),
        )
        self.assertEqual(
            inspection.bindings_for(inspection.model, "int32")[0].state,
            shikake.BindingState("external", False, False, False),
        )

    def test_package_and_source_produce_equivalent_facts(self) -> None:
        source = "from demo.kinds import int32\na: int32 = 2\nb = int32\n"
        expected = self.state(source, "int32")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "testpkg"
            root.mkdir()
            (root / "part.py").write_text(source, encoding="utf-8")
            package = shikake.parse_package(
                root, analyses=set(), definitions=DEFINITIONS
            )
            module = package.model.get_nodes("modules")[0]
            self.assertEqual(package.bindings_for(module, "int32")[0].state, expected)

    def test_virtual_builtin_uses_are_on_demand(self) -> None:
        inspection = shikake.inspect_source("v = tuple\n")
        assert inspection.model is not None
        self.assertEqual(
            inspection.bindings_for(inspection.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False, True),
        )
        self.assertNotIn("tuple", {item.name for item in inspection.name_bindings})


if __name__ == "__main__":
    unittest.main()
