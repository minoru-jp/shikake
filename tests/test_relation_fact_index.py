"""The shared fact collector must not silently lose nested relation subjects."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake._mica.ast_facts import collect_syntax_facts
from shikake._mica.kinds import kind_index
from shikake._mica.model import Model
from shikake._mica.parser import _Builder
from shikake._mica.relation_facts import _collect_facts


class RelationFactIndexTests(unittest.TestCase):
    def analyze(
        self, code: str, *, analyses: set[str] | None = None
    ) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "sample"
            directory.mkdir()
            (directory / "code.py").write_text(code, encoding="utf-8")
            return shikake.parse_package(directory, analyses=analyses)

    def test_plain_dotted_import_preserves_written_path_without_changing_bound_name(
        self,
    ) -> None:
        tree = ast.parse(
            "import pkg.a\nimport pkg.a as a\nfrom pkg import a as renamed\n"
        )
        facts = collect_syntax_facts(tree, include_references=False)
        imports = [event for event in facts.events if event.kind == "import"]
        self.assertEqual([event.name for event in imports], ["pkg", "a", "renamed"])
        self.assertEqual(
            [event.imported for event in imports],
            [("pkg", ""), ("pkg.a", ""), ("pkg", "a")],
        )
        self.assertEqual(
            [event.explicit_module for event in imports], ["pkg.a", None, None]
        )

    def test_nested_class_declarations_all_have_inheritance_results(self) -> None:
        package = self.analyze(
            "class Base: pass\n"
            "if flag:\n    class InIf(Base): pass\n"
            "class Outer:\n    class Inner(Base): pass\n"
            "def factory():\n    class InFunction(Base): pass\n"
            "match value:\n    case 1:\n        class InMatch(Base): pass\n"
            "try:\n    class InTry(Base): pass\n"
            "except Exception:\n    class InExcept(Base): pass\n"
            "with context():\n    class InWith(Base): pass\n",
            analyses={"inheritance"},
        )
        classes = tuple(
            model
            for model in package.walk()
            if model.kind.id == "model.definition.class" and model.get("bases")
        )
        relations = package.base_references
        self.assertEqual(len(relations), len(classes))
        self.assertEqual(
            {relation.subject.get("name") for relation in relations},
            {"InIf", "Inner", "InFunction", "InMatch", "InTry", "InExcept", "InWith"},
        )
        for relation in relations:
            self.assertIs(
                relation.targets[0],
                next(
                    model
                    for model in package.walk()
                    if model.kind.id == "model.definition.class"
                    and model.get("name") == "Base"
                ),
            )

    def test_nested_class_override_uses_same_fact_collection(self) -> None:
        package = self.analyze(
            "class Base:\n    def run(self): pass\n"
            "def create():\n    class Derived(Base):\n        def run(self): pass\n"
        )
        self.assertEqual(len(package.override_candidates), 1)
        self.assertEqual(len(package.base_references), 1)

    def test_written_rebinding_affects_all_base_refs_in_scope(self) -> None:
        result = self.analyze(
            "class Base: pass\n"
            "if condition:\n"
            "    Base = unknown\n"
            "    class Within(Base): pass\n"
            "class Later(Base): pass\n",
            analyses={"inheritance"},
        )
        self.assertEqual(
            {
                r.subject.get("name"): r.binding.may_rebind
                for r in result.base_references
                if r.binding
            },
            {"Within": True, "Later": True},
        )

    def test_conditional_method_binding_invalidates_class_candidate(self) -> None:
        result = self.analyze(
            "class Holder:\n"
            "    class Base: pass\n"
            "    class Before(Base): pass\n"
            "    if condition:\n"
            "        def Base(self): pass\n"
            "    class After(Base): pass\n",
            analyses={"inheritance"},
        )
        self.assertEqual(
            [
                (r.subject.get("name"), r.binding.may_rebind)
                for r in result.base_references
                if r.binding
            ],
            [("Before", True), ("After", True)],
        )
        self.assertEqual(result.base_references[1].targets[0].get("name"), "Base")

    def test_star_import_may_affect_earlier_and_later_base_references(self) -> None:
        result = self.analyze(
            "class Base: pass\n"
            "class Before(Base): pass\n"
            "from unknown import *\n"
            "class After(Base): pass\n",
            analyses={"inheritance"},
        )
        self.assertEqual(
            [r.subject.get("name") for r in result.base_references],
            ["Before", "After"],
        )

    def test_class_namespace_does_not_leak_into_methods(self) -> None:
        result = self.analyze(
            "class Holder:\n"
            "    class Local: pass\n"
            "    def make(self):\n"
            "        class Inner(Local): pass\n",
            analyses={"inheritance"},
        )
        self.assertEqual(len(result.base_references), 1)
        self.assertEqual(result.base_references[0].targets, ())
        self.assertIsNone(result.base_references[0].binding)

    def test_class_local_reference_is_available_to_nested_class(self) -> None:
        result = self.analyze(
            "class Holder:\n    class Local: pass\n    class Inner(Local): pass\n",
            analyses={"inheritance"},
        )
        (relation,) = result.base_references
        self.assertEqual(
            relation.binding, shikake.BindingState("stable", False, False, False)
        )
        self.assertEqual(relation.targets[0].get("name"), "Local")

    def test_condition_header_rebinding_is_visible_to_nested_class(self) -> None:
        result = self.analyze(
            "class Base: pass\n"
            "class Other: pass\n"
            "if (Base := Other):\n    class D(Base): pass\n",
            analyses={"inheritance"},
        )
        (relation,) = result.base_references
        self.assertTrue(relation.binding.may_rebind)  # type: ignore[union-attr]

    def test_loop_target_rebinding_is_visible_to_nested_class(self) -> None:
        result = self.analyze(
            "class Base: pass\nfor Base in values:\n    class D(Base): pass\n",
            analyses={"inheritance"},
        )
        (relation,) = result.base_references
        self.assertTrue(relation.binding.may_rebind)  # type: ignore[union-attr]

    def test_collected_events_preserve_lexical_ownership(self) -> None:
        source = (
            "from demo.kinds import int32\n"
            "count = 0\n"
            "def increment():\n"
            "    global count\n"
            "    count += 1\n"
            "def outer():\n"
            "    local = 1\n"
            "    def inner():\n"
            "        nonlocal local\n"
            "        local += 1\n"
            "        return local\n"
            "    return inner\n"
        )
        result = shikake.inspect_source(source)
        assert result.model is not None
        self.assertTrue(result.complete)
        root = result.model
        count = result.bindings_for(root, "count")[0]
        self.assertEqual(count.state.introduction, "stable")
        self.assertTrue(count.state.may_rebind)
        self.assertEqual(
            result.bindings_for(root, "int32")[0].state.introduction, "stable"
        )
        outer = next(
            node
            for node in root.walk()
            if node.kind.id == "model.definition.function"
            and node.get("name") == "outer"
        )
        local = result.bindings_for(outer, "local")[0]
        self.assertTrue(local.state.may_rebind)
        self.assertTrue(local.state.may_value_use)

    def test_selected_definition_kinds_can_be_extended(self) -> None:
        tree = ast.parse("def run():\n    class Inner: pass\n")
        builder = _Builder(kind_index())
        module = builder.module(tree, name="sample.code")
        facts = _collect_facts(
            {"sample.code": (module, False)},
            {"sample.code": (collect_syntax_facts(tree), builder.statement_models)},
            definitions=frozenset(
                {"model.definition.function", "model.definition.class"}
            ),
        )
        self.assertEqual(
            [site.definition.get("name") for site in facts.definitions],
            ["run", "Inner"],
        )
        self.assertTrue(
            all(isinstance(site.definition, Model) for site in facts.definitions)
        )


if __name__ == "__main__":
    unittest.main()
