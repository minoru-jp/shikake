"""Python 3.15 PEP 798 overlays share the baseline nonrecursive engine."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import shikake
from shikake._mica.parser import _Builder


class Python315ModelingRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = _Builder(shikake.kind_index())

    def test_dict_unpacking_uses_distinct_kind_and_roles(self) -> None:
        base = ast.parse("result = {key: value for key in items}")
        assignment = base.body[0]
        assert isinstance(assignment, ast.Assign)
        comp = assignment.value
        assert isinstance(comp, ast.DictComp)
        comp.key = ast.Name(id="part", ctx=ast.Load())
        comp.value = None  # type: ignore[assignment]  # PEP 798 AST on Python 3.15
        result = self.builder.module(base)
        model = result.get_nodes("body")[0].get_node("value")
        self.assertEqual(model.kind.id, "model.value.collection.mapping")
        self.assertEqual(model.get("construction"), "comprehension")
        (model,) = model.get_nodes("inputs")
        self.assertEqual(model.kind.id, "model.value.comprehension.dict.unpacking")
        self.assertEqual(
            tuple(part.role for part in model.parts()), ("mapping", "clauses")
        )
        self.assertEqual(model.get_node("mapping").get_name("name"), "part")
        self.assertEqual(len(model.get_nodes("clauses")), 1)
        self.assertTrue(
            shikake.kind_index().is_a(model.kind.id, "model.value.comprehension.dict")
        )
        normal = self.builder.expression(
            ast.parse("{x: y for x in items}", mode="eval").body
        )
        self.assertEqual(normal.kind.id, "model.value.collection.mapping")
        (normal,) = normal.get_nodes("inputs")
        self.assertEqual(normal.kind.id, "model.value.comprehension.dict")
        self.assertEqual(
            tuple(part.role for part in normal.parts()), ("key", "value", "clauses")
        )

    def test_starred_comprehensions_use_existing_kind_and_starred_child(self) -> None:
        for kind, node_type in (
            ("list", ast.ListComp),
            ("set", ast.SetComp),
            ("generator", ast.GeneratorExp),
        ):
            with self.subTest(kind=kind):
                node = node_type(
                    elt=ast.Starred(
                        value=ast.Name(id="part", ctx=ast.Load()), ctx=ast.Load()
                    ),
                    generators=[
                        ast.comprehension(
                            target=ast.Name(id="part", ctx=ast.Store()),
                            iter=ast.Name(id="groups", ctx=ast.Load()),
                            ifs=[],
                            is_async=0,
                        )
                    ],
                )
                model = self.builder.expression(node)
                if kind != "generator":
                    category = "sequence" if kind == "list" else "set"
                    self.assertEqual(
                        model.kind.id, f"model.value.collection.{category}"
                    )
                    (model,) = model.get_nodes("inputs")
                self.assertEqual(model.kind.id, f"model.value.comprehension.{kind}")
                self.assertEqual(
                    model.get_node("element").kind.id, "model.value.starred_expansion"
                )
                self.assertEqual(
                    model.get_node("element").get_node("value").get_name("name"), "part"
                )

    def test_nested_starred_collection_is_not_flattening_comprehension(self) -> None:
        model = self.builder.expression(
            ast.parse("[[*xs] for xs in groups]", mode="eval").body
        )
        self.assertEqual(model.kind.id, "model.value.collection.sequence")
        (model,) = model.get_nodes("inputs")
        self.assertEqual(
            model.get_node("element").kind.id, "model.value.collection.sequence"
        )

    def test_lazy_feature_is_restricted_to_import_statements(self) -> None:
        index = shikake.kind_index()
        self.assertEqual(
            index.all_features()[-1].allowed_kind_ids,
            ("model.import.direct", "model.import.from"),
        )
        for kind in ("model.import.direct", "model.import.from"):
            index.validate_features(kind, ("lazy",))
        for kind in ("model.import.alias", "model.value.named"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                index.validate_features(kind, ("lazy",))

    def test_lazy_import_ast_flag_changes_only_statement_feature(self) -> None:
        for source, expected_kind in (
            ("import pkg.module as alias", "model.import.direct"),
            ("from pkg.module import Item as alias", "model.import.from"),
            ("from .module import Item as alias", "model.import.from"),
        ):
            with self.subTest(source=source):
                tree = ast.parse(source)
                statement = tree.body[0]
                assert isinstance(statement, (ast.Import, ast.ImportFrom))
                normal = self.builder.statement(statement)
                statement.is_lazy = 1  # type: ignore[attr-defined]
                lazy = self.builder.statement(statement)
                self.assertEqual(lazy.kind.id, expected_kind)
                self.assertEqual(normal.kind, lazy.kind)
                self.assertEqual(normal.parts(), lazy.parts())
                self.assertEqual(normal.features, ())
                self.assertEqual(lazy.features, ("lazy",))
                self.assertTrue(
                    all(not alias.features for alias in lazy.get_nodes("names"))
                )
                self.assertNotEqual(normal, lazy)
                self.assertEqual(len({normal, lazy}), 2)

    def test_lazy_flag_does_not_change_binding_three_axes(self) -> None:
        source = "import json as j\nfrom pathlib import Path as P\nj = None\n"
        ordinary = shikake.inspect_source(source, syntax_validation="ast")
        self.assertTrue(ordinary.complete, ordinary.issues)
        tree = ast.parse(source)
        for statement in tree.body[:2]:
            assert isinstance(statement, (ast.Import, ast.ImportFrom))
            statement.is_lazy = 1  # type: ignore[attr-defined]
        with patch("shikake._mica.inspection.ast.parse", return_value=tree):
            lazy = shikake.inspect_source(source, syntax_validation="ast")
        self.assertTrue(lazy.complete, lazy.issues)
        self.assertEqual(
            [(item.name, item.state) for item in ordinary.name_bindings],
            [(item.name, item.state) for item in lazy.name_bindings],
        )
        assert ordinary.model is not None and lazy.model is not None
        ordinary_body = ordinary.model.get_nodes("body")
        lazy_body = lazy.model.get_nodes("body")
        self.assertEqual(
            [item.kind for item in ordinary_body],
            [item.kind for item in lazy_body],
        )
        self.assertEqual(
            [item.features for item in lazy_body], [("lazy",), ("lazy",), ()]
        )

    def test_lazy_import_preserves_static_package_reference_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pkg"
            root.mkdir()
            (root / "base.py").write_text("class Base: pass\n", encoding="utf-8")
            (root / "case.py").write_text(
                "from pkg.base import Base\nclass Derived(Base): pass\n",
                encoding="utf-8",
            )
            normal = shikake.parse_package(root)
            original_parse = ast.parse

            def lazy_ast(*args: object, **kwargs: object) -> ast.AST:
                # Python 3.15's extra flag can be simulated on prior versions.
                tree = original_parse(*args, **kwargs)  # type: ignore[arg-type]
                filename = kwargs.get("filename")
                if isinstance(filename, str) and filename.endswith("case.py"):
                    assert isinstance(tree, ast.Module)
                    statement = tree.body[0]
                    assert isinstance(statement, ast.ImportFrom)
                    statement.is_lazy = 1  # type: ignore[attr-defined]
                return tree

            with patch("shikake._mica.package.ast.parse", side_effect=lazy_ast):
                lazy = shikake.parse_package(root)
        self.assertEqual(
            [(b.name, b.state) for b in normal.name_bindings],
            [(b.name, b.state) for b in lazy.name_bindings],
        )
        self.assertEqual(
            [
                tuple(target.get_name("name") for target in ref.targets)
                for ref in normal.base_references
            ],
            [
                tuple(target.get_name("name") for target in ref.targets)
                for ref in lazy.base_references
            ],
        )
        self.assertEqual(len(normal.override_candidates), len(lazy.override_candidates))
        imports = [
            model for model in lazy.model.walk() if model.kind.id == "model.import.from"
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0].features, ("lazy",))

    @unittest.skipUnless(sys.version_info >= (3, 15), "requires Python 3.15+")
    def test_real_lazy_import_strict_and_partial(self) -> None:
        source = "lazy import json as j\nlazy from pathlib import Path as P\n"
        strict = shikake.parse_source(source)
        partial = shikake.inspect_source(source)
        self.assertTrue(partial.complete, partial.issues)
        self.assertEqual(strict, partial.model)
        self.assertEqual(
            [model.features for model in strict.get_nodes("body")],
            [("lazy",), ("lazy",)],
        )
        self.assertEqual({b.name for b in partial.name_bindings}, {"j", "P"})

    def test_large_flattening_ast_stays_nonrecursive(self) -> None:
        node: ast.expr = ast.Name(id="end", ctx=ast.Load())
        for _ in range(1500):
            node = ast.ListComp(
                elt=ast.Starred(value=node, ctx=ast.Load()),
                generators=[
                    ast.comprehension(
                        target=ast.Name(id="x", ctx=ast.Store()),
                        iter=ast.Name(id="groups", ctx=ast.Load()),
                        ifs=[],
                        is_async=0,
                    )
                ],
            )
        result = self.builder.expression(node)
        self.assertEqual(result.kind.id, "model.value.collection.sequence")
        self.assertEqual(
            sum(
                item.kind.id == "model.value.comprehension.list"
                for item in result.walk()
            ),
            1500,
        )

    @unittest.skipUnless(sys.version_info >= (3, 15), "requires Python 3.15+")
    def test_real_pep798_strict_and_partial(self) -> None:
        for source, kind in (
            ("[*xs for xs in groups]", "model.value.collection.sequence"),
            ("{*xs for xs in groups}", "model.value.collection.set"),
            ("(*xs for xs in groups)", "model.value.comprehension.generator"),
            ("{**d for d in groups}", "model.value.collection.mapping"),
        ):
            with self.subTest(source=source):
                model = shikake.parse_source("result = " + source)
                part = model.get_nodes("body")[0].get_node("value")
                self.assertEqual(part.kind.id, kind)
                self.assertTrue(shikake.inspect_source("result = " + source).complete)
