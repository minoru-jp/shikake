"""Public Partial contracts retained from the legacy specification audit."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as external_rules

import shikake

SPEC = (
    Path(__file__).resolve().parents[1]
    / "devdocs/canonical_sources/specification/parsing.py"
)


class Phase5PartialBoundaryContracts(unittest.TestCase):
    def test_new_partial_rules_have_stable_ids_and_related_contracts(self) -> None:
        tree = ast.parse(SPEC.read_text(encoding="utf-8"))
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        rules = {n.name: n for n in root.body if isinstance(n, ast.ClassDef)}
        for name, terms in {
            "SPEC_017": ("name_bindings", "不完全"),
            "SPEC_018": ("構文エラー", "他の解析可能なモジュール"),
        }.items():
            with self.subTest(rule=name):
                rule = rules[name]
                doc = ast.get_docstring(rule) or ""
                for term in terms:
                    self.assertIn(term, doc)
                fields = {
                    write.target.id
                    for write in rule.body
                    if isinstance(write, ast.AugAssign)
                    and isinstance(write.target, ast.Name)
                    and isinstance(write.op, ast.MatMult)
                }
                self.assertTrue({"title", "level", "related"} <= fields)

    def test_incomplete_syntax_does_not_expose_relations_or_name_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pkg"
            root.mkdir()
            (root / "bad.py").write_text("def broken(:\n", encoding="utf-8")
            (root / "good.py").write_text(
                "class Base: pass\n"
                "class Child(Base): pass\n"
                "def f(parameter):\n    local = parameter\n",
                encoding="utf-8",
            )
            inspected = shikake.inspect_package(root)
            self.assertFalse(inspected.complete)
            self.assertEqual(
                tuple(i.category for i in inspected.issues), ("syntax_error",)
            )
            self.assertEqual(
                tuple(m.get_name("name") for m in inspected.model.get_nodes("modules")),
                ("pkg.good",),
            )
            self.assertEqual(inspected.base_references, ())
            self.assertEqual(inspected.override_candidates, ())
            self.assertEqual(inspected.analyses, frozenset())
            self.assertEqual(inspected.package.name_bindings, ())

            (root / "bad.py").unlink()
            complete = shikake.inspect_package(root)
            strict = shikake.parse_package(root)
            self.assertTrue(complete.complete)

            def binding_values(
                bindings: tuple[shikake.NameBinding, ...],
            ) -> tuple[tuple[object, ...], ...]:
                return tuple(
                    (b.module, b.scope.kind.id, b.scope.span, b.name, b.state)
                    for b in bindings
                )

            self.assertEqual(
                binding_values(complete.package.name_bindings),
                binding_values(strict.name_bindings),
            )
            self.assertTrue(complete.package.name_bindings)

    def test_external_violation_omits_only_bad_module_and_binding_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "pkg"
            root.mkdir()
            (root / "bad.py").write_text(
                "from framework.memory import Memory\nMemory = 1\n",
                encoding="utf-8",
            )
            (root / "good.py").write_text("class Good: pass\n", encoding="utf-8")
            inspected = shikake.inspect_package(root, definitions=external_rules)
            self.assertEqual(
                tuple(issue.category for issue in inspected.issues),
                ("external_definition",),
            )
            self.assertEqual(
                tuple(m.get_name("name") for m in inspected.model.get_nodes("modules")),
                ("pkg.good",),
            )
            self.assertEqual(inspected.package.name_bindings, ())
            self.assertEqual(inspected.base_references, ())
            self.assertEqual(inspected.override_candidates, ())
            self.assertFalse(inspected.analyses)


if __name__ == "__main__":
    unittest.main()
