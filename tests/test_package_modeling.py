"""Package AST modeling: composition, cross-file relations and boundaries."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from test_type_alias_unsupported import simulate_unadopted_syntax

import shikake
from shikake._mica.model import Model

SHOP = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "shop"


def nodes(model: Model, role: str) -> tuple[Model, ...]:
    value = model.get(role)
    assert isinstance(value, tuple)
    assert all(isinstance(item, Model) for item in value)
    return cast(tuple[Model, ...], value)


def node(model: Model, role: str) -> Model:
    value = model.get(role)
    assert isinstance(value, Model)
    return value


class PackageModelTests(unittest.TestCase):
    def test_kind_contract_and_hierarchy(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(len(index.all_kinds()), 143)
        self.assertTrue(
            index.is_a("model.definition.method", "model.definition.function")
        )
        self.assertTrue(index.is_a("model.value.call", "model.value"))
        self.assertTrue(index.is_a("model.package", "model"))
        self.assertEqual(
            tuple(
                c.role for c in index.require_structure("model.definition.class").parts
            ),
            ("name", "type_parameters", "bases", "keywords", "decorators", "body"),
        )

    def test_full_package_and_override_candidate_link(self) -> None:
        result = shikake.parse_package(SHOP)
        root = result.model
        self.assertEqual(root.kind.id, "model.package")
        self.assertEqual(root.get("name"), "shop")
        modules = {m.get("name"): m for m in nodes(root, "modules")}
        self.assertEqual(
            set(modules),
            {"shop", "shop.checkout", "shop.member_shipping", "shop.shipping"},
        )
        self.assertEqual(len(tuple(result.walk())), 95)
        self.assertEqual(len(result.override_candidates), 1)
        (candidate,) = result.override_candidates
        self.assertEqual(candidate.evidence, "direct_base_and_same_method_name")
        self.assertEqual(candidate.base_module, "shop.shipping")
        self.assertEqual(candidate.derived_module, "shop.member_shipping")
        self.assertEqual(candidate.base_class.get("name"), "ShippingPolicy")
        self.assertEqual(candidate.derived_class.get("name"), "MemberShippingPolicy")
        self.assertEqual(candidate.method.get("name"), "calculate_fee")
        self.assertEqual(candidate.base_method.get("name"), "calculate_fee")
        self.assertTrue(any(candidate.method is n for n in result.walk()))
        self.assertTrue(any(candidate.base_method is n for n in result.walk()))
        self.assertEqual(result.overrides_for(candidate.method), (candidate,))
        self.assertEqual(result.overrides_for(candidate.base_method), ())

        subclass = nodes(modules["shop.member_shipping"], "body")[1]
        self.assertEqual(subclass.get("name"), "MemberShippingPolicy")
        self.assertEqual(nodes(subclass, "bases")[0].get("name"), "ShippingPolicy")
        methods = nodes(node(subclass, "body"), "statements")
        self.assertEqual(
            [m.get("name") for m in methods], ["calculate_fee", "calculate_points"]
        )
        self.assertEqual(result.overrides_for(methods[1]), ())
        base = nodes(modules["shop.shipping"], "body")[0]
        self.assertEqual(
            [m.get("name") for m in nodes(node(base, "body"), "statements")],
            ["calculate_fee", "description"],
        )
        self.assertEqual(
            sum(1 for m in result.walk() if m.kind.id == "model.definition.method"), 4
        )

    def test_checkout_branch_and_calls_have_complete_roles(self) -> None:
        result = shikake.parse_package(SHOP)
        checkout = next(
            m
            for m in nodes(result.model, "modules")
            if m.get("name") == "shop.checkout"
        )
        items = nodes(checkout, "body")
        self.assertEqual([i.kind.id for i in items[:2]], ["model.import.from"] * 2)
        function = items[2]
        statements = nodes(node(function, "body"), "statements")
        branch = statements[0]
        self.assertEqual(branch.kind.id, "model.statement.branch")
        self.assertEqual(
            node(nodes(branch, "paths")[0], "condition").get("name"), "is_member"
        )
        for path, policy in zip(
            nodes(branch, "paths"),
            ("MemberShippingPolicy", "ShippingPolicy"),
            strict=True,
        ):
            (assignment,) = nodes(node(path, "body"), "statements")
            self.assertEqual(nodes(assignment, "targets")[0].get("name"), "policy")
            call = node(assignment, "value")
            self.assertEqual(call.kind.id, "model.value.call")
            self.assertEqual(node(call, "callee").get("name"), policy)
            self.assertEqual(nodes(call, "arguments"), ())
        call = node(statements[1], "value")
        self.assertEqual(node(call, "callee").get("attribute"), "calculate_fee")
        self.assertEqual(nodes(call, "arguments")[0].get("name"), "subtotal")
        self.assertEqual(
            node(statements[2], "value").kind.id, "model.value.operation.addition"
        )
        for model in result.walk():
            self.assertEqual(
                [p.role for p in model.parts()],
                [
                    role.role
                    for role in shikake.kind_index()
                    .require_structure(model.kind.id)
                    .parts
                ],
            )

    def test_external_definition_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            (root / "child.py").write_text(
                "from pathlib import Path\n"
                "class MyPath(Path):\n"
                "    def open(self):\n"
                "        return 1\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root)
            self.assertEqual(result.override_candidates, ())
            child = next(
                m
                for m in nodes(result.model, "modules")
                if m.get("name") == "work.child"
            )
            klass = nodes(child, "body")[1]
            self.assertEqual(nodes(klass, "bases")[0].get("name"), "Path")
            self.assertEqual(klass.kind.id, "model.definition.class")

    def test_input_source_is_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "inert"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            target = Path(directory) / "should-not-exist"
            (root / "danger.py").write_text(
                f"from pathlib import Path\nPath({str(target)!r}).write_text('oops')\n",
                encoding="utf-8",
            )
            model = shikake.parse_package(root)
            self.assertTrue(
                any(n.kind.id == "model.statement.expression" for n in model.walk())
            )
            self.assertFalse(target.exists())

    @unittest.skipUnless(
        sys.version_info >= (3, 12), "requires Python 3.12 type statement"
    )
    @simulate_unadopted_syntax()
    def test_unsupported_construct_is_error_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            (root / "impl.py").write_text(
                "class C:\n    type Alias = int\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(shikake.UnsupportedSyntaxError, "TypeAlias"):
                shikake.parse_package(root)

    def test_simple_alias_import_is_resolved_only_in_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "lib"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            (root / "base.py").write_text(
                "class A:\n    def foo(self):\n        return 1\n", encoding="utf-8"
            )
            (root / "child.py").write_text(
                "from .base import A as Renamed\n"
                "class B(Renamed):\n    def foo(self):\n        return 2\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root)
            self.assertEqual(len(result.override_candidates), 1)
            self.assertEqual(result.override_candidates[0].base_class.get("name"), "A")


if __name__ == "__main__":
    unittest.main()
