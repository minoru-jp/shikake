"""Class locals are not visible inside lambda/comprehension bodies.

The first comprehension iterable and lambda defaults are evaluated in the
surrounding class scope. The existing expression-frame index distinguishes
these positions without adding name tracking.
"""

from __future__ import annotations

import unittest

import shikake
from shikake.external import ExternalDefinitionsBuilder


def _kind_count(source: str, kind: str, *, definitions=None) -> int:
    model = shikake.parse_source(source, definitions=definitions)
    return sum(node.kind.id == kind for node in model.walk())


class ClassComprehensionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definitions = (
            ExternalDefinitionsBuilder()
            .add_call("demo.ops:clamp", "demo.operation.clamp", ("value",))
            .build()
        )

    def test_class_local_does_not_shadow_builtin_in_comprehension_body(self) -> None:
        for expression in (
            "[list() for v in xs]",
            "{list() for v in xs}",
            "{v: list() for v in xs}",
            "(list() for v in xs)",
        ):
            with self.subTest(expression=expression):
                source = f"class A:\n    list = 1\n    result = {expression}\n"
                self.assertEqual(_kind_count(source, "model.value.call"), 0)
                # The comprehension itself is a collection, as is list().
                self.assertEqual(
                    _kind_count(source, "model.value.collection.sequence"),
                    2 if expression.startswith("[") else 1,
                )

    def test_first_iterable_still_sees_class_local(self) -> None:
        source = "class A:\n    list = 1\n    result = [v for v in list()]\n"
        self.assertEqual(_kind_count(source, "model.value.call"), 1)
        self.assertEqual(_kind_count(source, "model.value.collection.sequence"), 1)

    def test_class_local_does_not_shadow_registered_call_in_body(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "class A:\n"
            "    clamp = 1\n"
            "    result = [clamp(3) for v in xs]\n"
        )
        self.assertEqual(
            _kind_count(source, "demo.operation.clamp", definitions=self.definitions),
            1,
        )

    def test_first_iterable_still_sees_class_local_for_registered_call(self) -> None:
        source = (
            "from demo.ops import clamp\n"
            "class A:\n"
            "    clamp = 1\n"
            "    result = [v for v in clamp(3)]\n"
        )
        self.assertEqual(
            _kind_count(source, "demo.operation.clamp", definitions=self.definitions),
            0,
        )
        self.assertEqual(
            _kind_count(source, "model.value.call", definitions=self.definitions),
            1,
        )

    def test_comprehension_local_still_shadows_builtin(self) -> None:
        source = "class A:\n    list = 1\n    result = [list() for list in xs]\n"
        self.assertEqual(_kind_count(source, "model.value.call"), 1)

    def test_lambda_body_does_not_see_class_local_but_default_does(self) -> None:
        source = "class A:\n    list = 1\n    body = lambda: list()\n    default = lambda arg=list(): arg\n"
        self.assertEqual(_kind_count(source, "model.value.call"), 1)
        self.assertEqual(_kind_count(source, "model.value.collection.sequence"), 1)

    def test_module_level_shadow_is_still_visible_from_comprehension(self) -> None:
        source = (
            "list = custom_constructor\n"
            "class A:\n"
            "    list = 1\n"
            "    result = [list() for v in xs]\n"
        )
        self.assertEqual(_kind_count(source, "model.value.call"), 1)
        self.assertEqual(_kind_count(source, "model.value.collection.sequence"), 1)

    def test_enclosing_class_local_is_not_visible_in_nested_class(self) -> None:
        source = (
            "class Outer:\n"
            "    list = 1\n"
            "    class Inner:\n"
            "        result = [list() for v in xs]\n"
        )
        self.assertEqual(_kind_count(source, "model.value.call"), 0)
        self.assertEqual(_kind_count(source, "model.value.collection.sequence"), 2)


if __name__ == "__main__":
    unittest.main()
