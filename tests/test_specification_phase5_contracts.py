"""Phase 5: verify legacy contractual boundaries missing from the first rewrite."""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

import shikake

SPEC = Path(__file__).resolve().parents[1] / "devdocs/canonical_sources/specification"


class SpecificationPhase5ContractTests(unittest.TestCase):
    def test_audited_rules_have_stable_id_and_normative_fields(self) -> None:
        expected = {
            "parsing.py": ("SPEC_015", "SPEC_016"),
            "binding.py": ("SPEC_014", "SPEC_015"),
            "relations.py": ("SPEC_013", "SPEC_014", "SPEC_015", "SPEC_016"),
        }
        for filename, identities in expected.items():
            tree = ast.parse((SPEC / filename).read_text(encoding="utf-8"))
            document = next(n for n in tree.body if isinstance(n, ast.ClassDef))
            nodes = {n.name: n for n in document.body if isinstance(n, ast.ClassDef)}
            for identity in identities:
                with self.subTest(file=filename, rule=identity):
                    node = nodes[identity]
                    self.assertTrue(ast.get_docstring(node))
                    fields = {
                        item.target.id
                        for item in node.body
                        if isinstance(item, ast.AugAssign)
                        and isinstance(item.target, ast.Name)
                    }
                    self.assertTrue({"title", "level", "related"} <= fields)

    def test_module_identity_for_init_and_intermediate_uninitialized_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "mypkg"
            (root / "sub").mkdir(parents=True)
            (root / "plain").mkdir()
            (root / "__init__.py").write_text("ROOT = 1\n")
            (root / "sub" / "__init__.py").write_text("INNER = 1\n")
            (root / "sub" / "mod.py").write_text("X = 1\n")
            (root / "plain" / "leaf.py").write_text("Y = 1\n")
            result = shikake.parse_package(root, analyses=set())
            self.assertEqual(
                tuple(m.get_name("name") for m in result.model.get_nodes("modules")),
                ("mypkg", "mypkg.plain.leaf", "mypkg.sub", "mypkg.sub.mod"),
            )
            (root / "__init__.py").unlink()
            result = shikake.parse_package(root, analyses=set())
            self.assertNotIn(
                "mypkg", (m.get_name("name") for m in result.model.get_nodes("modules"))
            )

    def test_analysis_defaults_dependencies_and_independent_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "mypkg"
            root.mkdir()
            (root / "one.py").write_text(
                "class Base:\n    def m(self): pass\n"
                "class Child(Base):\n    def m(self): pass\n"
                "def f(P):\n    return P\n"
            )
            default = shikake.parse_package(root)
            self.assertEqual(default.analyses, frozenset({"override", "inheritance"}))
            self.assertEqual(len(default.base_references), 1)
            self.assertEqual(len(default.override_candidates), 1)
            only_bases = shikake.parse_package(root, analyses={"inheritance"})
            self.assertEqual(only_bases.analyses, frozenset({"inheritance"}))
            self.assertEqual(len(only_bases.override_candidates), 0)
            empty = shikake.parse_package(root, analyses=set())
            self.assertEqual(empty.analyses, frozenset())
            self.assertEqual(empty.base_references, ())
            self.assertEqual(empty.override_candidates, ())
            module = empty.model.get_nodes("modules")[0]
            function = next(
                node
                for node in module.walk()
                if node.kind.id == "model.definition.function"
            )
            (binding,) = empty.bindings_for(function, "P")
            self.assertEqual(binding.module, "mypkg.one")
            self.assertIs(binding.scope, function)
            self.assertEqual(binding.name, "P")
            self.assertEqual(
                binding.state, shikake.BindingState("stable", False, False)
            )
            self.assertEqual(empty.bindings_for(module, "P"), ())
            with self.assertRaises(ValueError):
                shikake.parse_package(root, analyses={"unsupported"})

    def test_explicit_import_and_star_all_have_distinct_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "mypkg"
            root.mkdir()
            (root / "base.py").write_text('class Base: pass\n__all__ = ["Base"]\n')
            (root / "star.py").write_text(
                "from .base import *\nclass StarChild(Base): pass\n"
            )
            (root / "explicit.py").write_text(
                "from .base import Base\nclass DirectChild(Base): pass\n"
            )
            result = shikake.parse_package(root, analyses={"inheritance"})
            references = {r.subject.get_name("name"): r for r in result.base_references}
            self.assertEqual(references["StarChild"].targets, ())
            self.assertIsNone(references["StarChild"].binding)
            self.assertEqual(
                [m.get_name("name") for m in references["DirectChild"].targets],
                ["Base"],
            )
            self.assertEqual(
                references["DirectChild"].binding,
                shikake.BindingState("stable", False, False),
            )

    @unittest.skipUnless(sys.version_info >= (3, 12), "requires Python 3.12+")
    def test_type_parameter_shadows_outer_class_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "mypkg"
            root.mkdir()
            (root / "generic.py").write_text(
                "class T: pass\nclass Generic[T](T): pass\n"
            )
            result = shikake.parse_package(root, analyses={"inheritance"})
            (reference,) = result.base_references
            self.assertEqual(reference.subject.get_name("name"), "Generic")
            self.assertEqual(reference.targets, ())


if __name__ == "__main__":
    unittest.main()
