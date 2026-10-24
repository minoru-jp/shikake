"""Programmatic external definitions must share Shikumi's semantic contract."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from typing import cast

import external_memory_definitions as memory

import shikake
from shikake.external import (
    Argument,
    ExternalDefinitionsBuilder,
    ImportedCall,
    Role,
    load_external_definitions,
)


class ExternalBuilderStage3Tests(unittest.TestCase):
    def test_minimal_call_creates_concrete_kind_and_structure(self) -> None:
        definitions = (
            ExternalDefinitionsBuilder()
            .add_call(
                "sample.memory:Memory.allocate", "demo.memory.allocate", ("size",)
            )
            .build()
        )
        self.assertEqual(
            definitions.index.require_structure("demo.memory.allocate").parts,
            (Role("size", "node"),),
        )
        self.assertEqual(
            definitions.mappings[0].arguments, (Argument("size", 0, "size"),)
        )
        root = shikake.parse_source(
            "from sample.memory import Memory\nitem = Memory.allocate(size=64)\n",
            definitions=definitions,
        )
        self.assertEqual(
            [
                m.get_node("size").get("value")
                for m in root.walk()
                if m.kind.id == "demo.memory.allocate"
            ],
            [64],
        )

    def test_shikumi_and_builder_produce_equivalent_schema(self) -> None:
        reference = load_external_definitions(memory)
        builder = ExternalDefinitionsBuilder()
        builder.add_structure("test.memory.allocation", (Role("size", "node"),))
        builder.add_structure("test.memory.release", (Role("target", "node"),))
        builder.add_call(
            "framework.memory:Memory.new",
            "ext.memory.allocate",
            (Argument("size", 0, "size"),),
            structure_id="test.memory.allocation",
        )
        builder.add_call(
            ImportedCall("framework.memory:Memory.add"),
            "ext.memory.release",
            (Argument("target", 0, "target"),),
            structure_id="test.memory.release",
        )
        built = builder.build()
        self.assertEqual(built.index.all_kinds(), reference.index.all_kinds())
        self.assertEqual(built.index.all_structures(), reference.index.all_structures())
        self.assertEqual(built.index.all_features(), reference.index.all_features())
        self.assertEqual(built.mappings, reference.mappings)
        source = (
            "from framework.memory import Memory\n"
            "x = Memory.new(5)\nMemory.add(target=x)\n"
        )
        first = shikake.parse_source(source, definitions=reference)
        second = shikake.parse_source(source, definitions=built)
        self.assertEqual(first, second)
        built_again = builder.build()
        self.assertEqual(built.index.all_kinds(), built_again.index.all_kinds())
        self.assertEqual(
            built.index.all_structures(), built_again.index.all_structures()
        )
        self.assertEqual(built.mappings, built_again.mappings)

    def test_existing_kind_mapping_and_explicit_parent(self) -> None:
        builder = ExternalDefinitionsBuilder()
        builder.add_kind("demo.func", "model.value")
        builder.add_structure("demo.args", (Role("argument", "node"),))
        builder.add_kind("demo.sin", "demo.func", "demo.args")
        builder.add_mapping("demo:Fn.sin", "demo.sin", (Argument("argument", 0, "v"),))
        definitions = builder.build()
        self.assertTrue(definitions.index.is_a("demo.sin", "demo.func"))
        model = shikake.parse_source(
            "from demo import Fn\nx = Fn.sin(v=2)\n", definitions=definitions
        )
        (call,) = (m for m in model.walk() if m.kind.id == "demo.sin")
        self.assertEqual(call.get_node("argument").get("value"), 2)

    def test_dotlang_eleven_functions_as_short_declarations(self) -> None:
        # Equivalent to the 11 call signatures from dotlang's 22 Shikumi
        # Kind/Mapping classes, with three shared argument Structures.
        builder = ExternalDefinitionsBuilder()
        for count in (1, 2, 3):
            builder.add_structure(
                f"dot.args{count}",
                tuple(Role(name, "node") for name in ("a", "b", "c")[:count]),
            )
        builder.add_kind("dot.fn", "model.value")
        signatures = {
            "sin": ("v",),
            "cos": ("v",),
            "abs": ("v",),
            "sqrt": ("v",),
            "floor": ("v",),
            "min": ("p", "q"),
            "max": ("p", "q"),
            "hypot": ("dx", "dy"),
            "angle": ("dx", "dy"),
            "noise": ("p", "q"),
            "clamp": ("v", "lo", "hi"),
        }
        for name, keywords in signatures.items():
            builder.add_call(
                f"dot:Fn.{name}",
                f"dot.fn.{name}",
                tuple(
                    Argument(role, position, keyword)
                    for position, (role, keyword) in enumerate(
                        zip(("a", "b", "c"), keywords)
                    )
                ),
                parent_id="dot.fn",
                structure_id=f"dot.args{len(keywords)}",
            )
        definitions = builder.build()
        self.assertEqual(len(definitions.mappings), 11)
        self.assertEqual(
            len(definitions.index.all_structures()),
            len(shikake.kind_index().all_structures()) + 3,
        )
        statements = ["from dot import Fn"]
        for name, keywords in signatures.items():
            values = ", ".join(
                f"{keyword}={position + 1}" for position, keyword in enumerate(keywords)
            )
            statements.append(f"x_{name} = Fn.{name}({values})")
        root = shikake.parse_source(
            "\n".join(statements) + "\n", definitions=definitions
        )
        self.assertEqual(
            [m.kind.id for m in root.walk() if m.kind.id.startswith("dot.fn.")],
            [f"dot.fn.{name}" for name in signatures],
        )

    def test_invalid_declarations_are_rejected_by_shared_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "no declarations"):
            ExternalDefinitionsBuilder().build()
        with self.assertRaisesRegex(ValueError, "duplicate Kind ID"):
            (
                ExternalDefinitionsBuilder()
                .add_call("demo:Fn.sin", "model.value.named", ("x",))
                .build()
            )
        with self.assertRaisesRegex(ValueError, "roles do not match"):
            (
                ExternalDefinitionsBuilder()
                .add_structure("demo.args", (Role("a", "node"),))
                .add_call("demo:Fn.sin", "demo.sin", ("b",), structure_id="demo.args")
                .build()
            )
        with self.assertRaisesRegex(ValueError, "duplicate external target"):
            (
                ExternalDefinitionsBuilder()
                .add_call("demo:Fn.sin", "demo.first", ("x",))
                .add_call("demo:Fn.sin", "demo.second", ("x",))
                .build()
            )
        with self.assertRaisesRegex(ValueError, "requires node roles"):
            (
                ExternalDefinitionsBuilder()
                .add_structure("demo.args", (Role("x", "text"),))
                .add_call("demo:Fn.sin", "demo.sin", ("x",), structure_id="demo.args")
                .build()
            )
        with self.assertRaisesRegex(ValueError, "contiguous"):
            (
                ExternalDefinitionsBuilder()
                .add_call("demo:Fn.sin", "demo.sin", (Argument("x", 3, "x"),))
                .build()
            )
        with self.assertRaisesRegex(ValueError, "abstract Kind"):
            (
                ExternalDefinitionsBuilder()
                .add_kind("demo.abstract", "model.value")
                .add_mapping("demo:Fn.sin", "demo.abstract", ())
                .build()
            )

    def test_invalid_arguments_do_not_create_partial_mapping(self) -> None:
        builder = ExternalDefinitionsBuilder()
        with self.assertRaises(TypeError):
            builder.add_call("demo:Fn.sin", "demo.sin", "value")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.add_call(
                "demo:Fn.sin",
                "demo.sin",
                cast(Sequence[str], ("value", Argument("x", 1, "x"))),
            )
        with self.assertRaisesRegex(ValueError, "no declarations"):
            builder.build()
        builder.add_call("demo:sin", "demo.sin", ("value",))
        self.assertEqual(builder.build().mappings[0].target.path, "demo:sin")


if __name__ == "__main__":
    unittest.main()
