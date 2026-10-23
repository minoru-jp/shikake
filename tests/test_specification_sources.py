"""Structural regression tests for the normative canonical specification."""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path

SPEC_DIR = (
    Path(__file__).resolve().parents[1]
    / "devdocs"
    / "canonical_sources"
    / "specification"
)
EXPECTED = {
    "model.py",
    "layouts.py",
    "parsing.py",
    "expressions.py",
    "statements.py",
    "binding.py",
    "relations.py",
    "external.py",
}


class SpecificationStructureTests(unittest.TestCase):
    def test_specs_are_identity_based_normative_nodes(self) -> None:
        actual = {p.name for p in SPEC_DIR.glob("*.py")} - {"__init__.py"}
        self.assertEqual(actual, EXPECTED)
        found = 0
        for path in sorted(SPEC_DIR.glob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            roots = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            self.assertEqual(len(roots), 1, path)
            root = roots[0]
            self.assertTrue(ast.get_docstring(root), path)
            calls = [d for d in root.decorator_list if isinstance(d, ast.Call)]
            canonical = next(
                d
                for d in calls
                if isinstance(d.func, ast.Name) and d.func.id == "canonical_source"
            )
            heading = next(kw.value for kw in canonical.keywords if kw.arg == "heading")
            assert isinstance(heading, ast.Constant)
            self.assertEqual(heading.value, "identity")
            rules = [n for n in root.body if isinstance(n, ast.ClassDef)]
            self.assertGreaterEqual(len(rules), 5, path)
            found += len(rules)
            for node in rules:
                self.assertRegex(node.name, r"^SPEC_[0-9]{3}$")
                self.assertTrue(ast.get_docstring(node), (path, node.name))
                fields = {
                    write.target.id
                    for write in node.body
                    if isinstance(write, ast.AugAssign)
                    and isinstance(write.target, ast.Name)
                    and isinstance(write.op, ast.MatMult)
                }
                self.assertTrue({"level", "title"} <= fields, (path, node.name))
        self.assertGreaterEqual(found, 186)

    def test_layouts_cover_exact_trusted_kind_and_structure_contracts(self) -> None:
        """The canonical shape catalog must not drift from trusted descriptions."""
        from shikake import kind_index

        tree = ast.parse((SPEC_DIR / "layouts.py").read_text(encoding="utf-8"))
        root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        documented: dict[str, tuple[str, str]] = {}
        abstract: str | None = None
        for node in root.body:
            if not isinstance(node, ast.ClassDef):
                continue
            values: dict[str, list[str]] = {}
            for item in node.body:
                if not isinstance(item, ast.AugAssign) or not isinstance(
                    item.target, ast.Name
                ):
                    continue
                if not isinstance(item.value, ast.Constant):
                    continue
                if not isinstance(item.value.value, str):
                    continue
                values.setdefault(item.target.id, []).append(item.value.value)
            if node.name == "SPEC_060":
                self.assertEqual(values["title"], ["抽象Kindの一覧"])
                abstract = next(
                    x.removeprefix("kinds: ")
                    for x in values["detail"]
                    if x.startswith("kinds: ")
                )
                continue
            structure_id = values["title"][0].removeprefix("Structure: ")
            self.assertNotIn(structure_id, documented)
            roles = next(
                x.removeprefix("roles: ")
                for x in values["detail"]
                if x.startswith("roles: ")
            )
            kinds = next(
                x.removeprefix("kinds: ")
                for x in values["detail"]
                if x.startswith("kinds: ")
            )
            documented[structure_id] = (roles, kinds)

        index = kind_index()
        self.assertEqual(set(documented), {s.id for s in index.all_structures()})
        for structure in index.all_structures():
            roles = (
                ", ".join(f"{p.role}:{p.shape}" for p in structure.parts) or "(none)"
            )
            kinds = (
                ", ".join(
                    kind.id
                    for kind in index.all_kinds()
                    if kind.structure_id == structure.id
                )
                or "(none)"
            )
            with self.subTest(structure=structure.id):
                self.assertEqual(documented[structure.id], (roles, kinds))
        self.assertEqual(
            abstract,
            ", ".join(
                kind.id for kind in index.all_kinds() if kind.structure_id is None
            ),
        )

    def test_api_reference_subjects_match_public_exports(self) -> None:
        """Public names are separate subjects, not buried in prose."""
        from shikake import __all__ as core_exports
        from shikake.external import __all__ as external_exports

        api_dir = SPEC_DIR.parent / "api_reference"
        for filename, module_name, exports in (
            ("public.py", "shikake", core_exports),
            ("external.py", "shikake.external", external_exports),
        ):
            tree = ast.parse((api_dir / filename).read_text(encoding="utf-8"))
            root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
            subjects: set[str] = set()
            for node in root.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                self.assertRegex(node.name, r"^API_[0-9]{3}$")
                self.assertTrue(ast.get_docstring(node))
                fields = {
                    item.target.id: item.value
                    for item in node.body
                    if isinstance(item, ast.AugAssign)
                    and isinstance(item.target, ast.Name)
                }
                self.assertTrue({"name", "kind", "related"} <= fields.keys())
                api_name = fields["name"]
                assert isinstance(api_name, ast.Constant)
                value = api_name.value
                assert isinstance(value, str)
                self.assertNotIn(value, subjects)
                subjects.add(value)
                target = importlib.import_module(module_name)
                suffix = value.removeprefix(module_name + ".")
                for part in suffix.split("."):
                    self.assertTrue(hasattr(target, part), value)
                    target = getattr(target, part)
            self.assertTrue(
                {f"{module_name}.{name}" for name in exports} <= subjects,
                (module_name, subjects),
            )
        # Accessors are first-class API subjects, not a paragraph in Model's node.
        public = (api_dir / "public.py").read_text(encoding="utf-8")
        for method in (
            "Model.get_node",
            "KindIndex.require_structure",
            "PackageModel.bases_for",
        ):
            self.assertIn(f"shikake.{method}", public)

    def test_new_canonical_documents_are_valid_and_cross_references_resolve(
        self,
    ) -> None:
        """Check Shikumi references without generating Markdown files."""
        from shikumi_devdoc.context import Context
        from shikumi_devdoc.norms.document import system as document
        from shikumi_devdoc.realizers.document import MarkdownRealizer

        realizer = MarkdownRealizer(Context({"project": {"name": "shikake"}}))
        canonical_modules = [
            f"devdocs.canonical_sources.specification.{path.stem}"
            for path in sorted(SPEC_DIR.glob("*.py"))
            if path.name != "__init__.py"
        ]
        api_dir = SPEC_DIR.parent / "api_reference"
        canonical_modules.extend(
            f"devdocs.canonical_sources.api_reference.{path.stem}"
            for path in sorted(api_dir.glob("*.py"))
            if path.name != "__init__.py"
        )
        # The independent modeling policy is also a canonical document.
        canonical_modules.append("devdocs.canonical_sources.policy.canonical")
        for dotted in canonical_modules:
            with self.subTest(module=dotted):
                source = importlib.import_module(dotted)
                result = document.validate(source, placement=())
                self.assertTrue(result.is_valid, result.diagnostics)
                check = realizer.check(result.view)
                self.assertTrue(check.is_realizable, check.diagnostics)

    def test_migrated_rule_identities_and_contracts_are_preserved(self) -> None:
        """Protect reviewed contracts from disappearing in a later rewrite."""
        migrated = {
            "model.py": {
                "SPEC_010": ("抽象Kind",),
                "SPEC_013": ("ID重複", "Feature"),
                "SPEC_014": ("KeyError", "TypeError"),
                "SPEC_015": ("SourceSpan", "ハッシュ"),
                "SPEC_016": ("all_kinds", "all_structures"),
            },
            "parsing.py": {
                "SPEC_011": ("UTF-8", "syntax_error"),
                "SPEC_012": ("skipped_span", "node_type"),
                "SPEC_013": ("complete=False", "ファイルI/O"),
                "SPEC_014": ("type: ignore", "注釈構文"),
            },
            "expressions.py": {
                "SPEC_012": ("yield from", "optional_node"),
                "SPEC_013": ("is_async", "Feature"),
                "SPEC_014": ("callee", "arguments"),
            },
            "statements.py": {
                "SPEC_016": ("model.definition.generator", "Method"),
                "SPEC_017": ("内包表記", "yield"),
                "SPEC_018": ("subject", "paths"),
                "SPEC_019": ("optional_node", "None"),
            },
            "binding.py": {"SPEC_013": ("global", "nonlocal")},
            "relations.py": {"SPEC_012": ("evidence", "Generator")},
        }
        for filename, expected_rules in migrated.items():
            tree = ast.parse((SPEC_DIR / filename).read_text(encoding="utf-8"))
            root = next(node for node in tree.body if isinstance(node, ast.ClassDef))
            rules = {
                node.name: ast.get_docstring(node) or ""
                for node in root.body
                if isinstance(node, ast.ClassDef)
            }
            for identity, terms in expected_rules.items():
                with self.subTest(filename=filename, rule=identity):
                    self.assertIn(identity, rules)
                    for term in terms:
                        self.assertIn(term, rules[identity])

    def test_cross_document_related_are_python_object_references(self) -> None:
        links = 0
        for path in SPEC_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.AugAssign):
                    continue
                if not isinstance(node.target, ast.Name) or node.target.id != "related":
                    continue
                assert isinstance(node.value, ast.Tuple)
                for value in node.value.elts:
                    if isinstance(value, ast.Name):
                        # A root document is a valid cross-document related target.
                        self.assertTrue(value.id.isupper())
                    else:
                        assert isinstance(value, ast.Attribute)
                        self.assertRegex(value.attr, r"^SPEC_[0-9]{3}$")
                        assert isinstance(value.value, ast.Name)
                        self.assertTrue(value.value.id.isupper())
                    links += 1
        self.assertGreaterEqual(links, 15)


if __name__ == "__main__":
    unittest.main()
