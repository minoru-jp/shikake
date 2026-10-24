"""Value stars, class headers, annotated targets, and lexical class placement."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model


def one(model: Model, role: str) -> Model:
    result = model.get(role)
    assert isinstance(result, Model)
    return result


def many(model: Model, role: str) -> tuple[Model, ...]:
    result = model.get(role)
    assert isinstance(result, tuple)
    assert all(isinstance(node, Model) for node in result)
    return cast(tuple[Model, ...], result)


def statements(src: str) -> tuple[Model, ...]:
    return many(shikake.parse_source(src), "body")


class StructuralPlacementTests(unittest.TestCase):
    def test_value_stars_are_not_binding_targets_or_call_arguments(self) -> None:
        assignments = statements("a = [*left, *right]\nb = (*left, 3)\nc = {*right}\n")
        self.assertEqual(len(assignments), 3)
        for assignment, type_id, count in zip(
            assignments,
            ("sequence", "sequence", "set"),
            (2, 2, 1),
            strict=True,
        ):
            collection = one(assignment, "value")
            self.assertEqual(collection.kind.id, f"model.value.collection.{type_id}")
            self.assertEqual(len(many(collection, "inputs")), count)
            star = many(collection, "inputs")[0]
            self.assertEqual(star.kind.id, "model.value.starred_expansion")
            self.assertEqual([p.role for p in star.parts()], ["value"])
            self.assertEqual(one(star, "value").kind.id, "model.value.named")
            self.assertIsNotNone(star.span)

        (target_assignment,) = statements("first, *rest = values")
        star_target = many(many(target_assignment, "targets")[0], "elements")[1]
        self.assertEqual(star_target.kind.id, "model.structural_part.starred_target")
        (called,) = statements("f(*values)")
        star_call = many(one(called, "value"), "arguments")[0]
        self.assertEqual(star_call.kind.id, "model.structural_part.starred_argument")
        self.assertFalse(
            shikake.kind_index().is_a(
                "model.value.starred_expansion", "model.structural_part"
            )
        )

    def test_nested_value_expansion_retains_structure(self) -> None:
        (assignment,) = statements("items = [(0, *part) for part in groups if part]")
        comprehension = one(assignment, "value")
        self.assertEqual(comprehension.kind.id, "model.value.collection.sequence")
        (construction,) = many(comprehension, "inputs")
        tup = one(construction, "element")
        star = many(tup, "inputs")[1]
        self.assertEqual(star.kind.id, "model.value.starred_expansion")
        self.assertEqual(len(many(construction, "clauses")), 1)
        # Mapping expansion stays distinct from value-star expansion.
        (mapping,) = statements("items = {**mapping}")
        self.assertIsNone(many(one(mapping, "value"), "inputs")[0].get("key"))

    def test_annotated_assignments_preserve_target_simple_and_absence(self) -> None:
        source = """\nx: int = 1
(x): int = 2
obj.attr: int = 3
items[index]: float
obj.other: str = None
"""
        var, paren, attribute, index, explicit_none = statements(source)
        self.assertEqual(var.kind.id, "model.definition.variable")
        self.assertEqual(var.get("name"), "x")
        self.assertEqual(paren.kind.id, "model.statement.assignment.annotated")
        self.assertEqual(one(paren, "target").get("name"), "x")
        self.assertIs(paren.get("simple"), False)
        self.assertEqual(
            one(attribute, "target").kind.id, "model.value.access.attribute"
        )
        self.assertEqual(one(index, "target").kind.id, "model.value.access.index")
        self.assertIsNone(index.get("value"))
        self.assertEqual(
            one(explicit_none, "value").kind.id,
            "model.value.literal.special.none",
        )
        self.assertEqual(
            [part.role for part in attribute.parts()],
            ["target", "annotation", "value", "simple"],
        )
        self.assertTrue(
            shikake.kind_index().is_a(attribute.kind.id, "model.statement.assignment")
        )

    def test_class_keywords_keep_alias_order_and_star_bases(self) -> None:
        (cls,) = statements(
            "class View(*bases, metaclass=Meta, **options, label='x'):\n    pass\n"
        )
        self.assertEqual(cls.kind.id, "model.definition.class")
        self.assertEqual(many(cls, "bases")[0].kind.id, "model.value.starred_expansion")
        keywords = many(cls, "keywords")
        self.assertEqual(
            [kw.get("name") for kw in keywords], ["metaclass", None, "label"]
        )
        self.assertEqual(
            [one(kw, "value").kind.id for kw in keywords],
            ["model.value.named", "model.value.named", "model.value.literal"],
        )
        self.assertEqual(
            [p.role for p in cls.parts()],
            ["name", "type_parameters", "bases", "keywords", "decorators", "body"],
        )
        self.assertEqual(len(many(one(cls, "body"), "statements")), 1)

    def test_class_methods_traverse_only_control_blocks(self) -> None:
        source = """\nclass Example:
    if guard:
        def branch(self): pass
    else:
        async def alternative(self): pass
    match status:
        case "a":
            def pattern(self): pass
    for item in items:
        def loop(self): pass
    while ready:
        def while_loop(self): pass
    try:
        def attempt(self): pass
    except Exception:
        def recovered(self): pass
    else:
        def succeeded(self): pass
    finally:
        def finished(self): pass
    with context():
        def contextual(self): pass
    async def wrapper(self):
        if guard:
            def local(): pass
    class Nested:
        if guard:
            def nested_method(self): pass
"""
        (cls,) = statements(source)
        members = [
            node for node in cls.walk() if node.kind.id == "model.definition.method"
        ]
        names = [node.get("name") for node in members]
        self.assertEqual(
            names,
            [
                "branch",
                "alternative",
                "pattern",
                "loop",
                "while_loop",
                "attempt",
                "recovered",
                "succeeded",
                "finished",
                "contextual",
                "wrapper",
                "nested_method",
            ],
        )
        self.assertNotIn("local", names)
        nested_function = next(
            node
            for node in cls.walk()
            if node.kind.id == "model.definition.function"
            and node.get("name") == "local"
        )
        self.assertEqual(nested_function.kind.id, "model.definition.function")
        self.assertEqual(
            next(
                node
                for node in cls.walk()
                if node.kind.id == "model.definition.method"
                and node.get("name") == "alternative"
            ).features,
            ("async",),
        )

    def test_conditional_generator_is_generator_without_extra_marker(self) -> None:
        (cls,) = statements(
            "class Example:\n    if flag:\n        def values(self):\n            yield 1\n"
        )
        generator = next(
            node
            for node in cls.walk()
            if node.kind.id == "model.definition.method"
            and "generator" in node.features
        )
        self.assertEqual(generator.get("name"), "values")
        self.assertEqual(generator.features, ("generator",))

    def test_override_candidates_follow_structural_placement_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pkg = Path(directory) / "example_pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "base.py").write_text(
                "class Base:\n    if guard:\n        def value(self): pass\n",
                encoding="utf-8",
            )
            (pkg / "derived.py").write_text(
                "from .base import Base\n"
                "class Derived(Base):\n"
                "    try:\n"
                "        def value(self): pass\n"
                "    finally:\n"
                "        pass\n"
                "    def wrapper(self):\n"
                "        def value(): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(pkg)
            self.assertEqual(len(result.override_candidates), 1)
            (candidate,) = result.override_candidates
            self.assertEqual(candidate.method.get("name"), "value")
            self.assertEqual(candidate.base_method.get("name"), "value")
            self.assertEqual(candidate.derived_class.get("name"), "Derived")
            self.assertEqual(result.overrides_for(candidate.method), (candidate,))
            self.assertEqual(candidate.evidence, "direct_base_and_same_method_name")

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_partial_keeps_new_forms_and_skips_unadopted_sibling(self) -> None:
        source = (
            "a = [*left, *right]\n"
            "type Unadopted = int\n"
            "obj.attr: int = 1\n"
            "class V(metaclass=Meta): pass\n"
        )
        inspected = shikake.inspect_source(source)
        self.assertFalse(inspected.complete)
        self.assertEqual([issue.node_type for issue in inspected.issues], ["TypeAlias"])
        assert inspected.model is not None
        self.assertEqual(len(many(inspected.model, "body")), 3)
        with self.assertRaises(shikake.UnsupportedSyntaxError):
            shikake.parse_source(source)


if __name__ == "__main__":
    unittest.main()
