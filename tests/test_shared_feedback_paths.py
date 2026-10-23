"""Regressions for syntax facts shared by binding, candidate and extension paths."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as memory_rules

import shikake


class SharedFeedbackPathsTests(unittest.TestCase):
    def parse(self, files: dict[str, str]) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            for name, code in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(code, encoding="utf-8")
            return shikake.parse_package(root)

    def refs(self, package: shikake.PackageModel) -> dict[str, shikake.BaseReference]:
        return {item.subject.get_name("name"): item for item in package.base_references}

    def test_lambda_defaults_write_into_enclosing_scope_but_body_does_not(self) -> None:
        result = self.parse(
            {
                "case.py": (
                    "class Base: pass\n"
                    "f = lambda a=(Base := 1), *, b=(Base := 2): a\n"
                    "class D(Base): pass\n"
                )
            }
        )
        reference = self.refs(result)["D"]
        self.assertEqual(reference.binding, shikake.BindingState("stable", True, False))
        self.assertEqual(reference.targets[0].get_name("name"), "Base")
        body_only = self.parse(
            {
                "case.py": "class Base: pass\nf = lambda: (Base := 1)\nclass D(Base): pass\n"
            }
        )
        self.assertEqual(
            self.refs(body_only)["D"].binding,
            shikake.BindingState("stable", False, False),
        )
        self.assertEqual(self.refs(body_only)["D"].targets[0].get_name("name"), "Base")

    def test_except_header_walrus_write_into_outer_scope(self) -> None:
        for keyword in ("except", "except*"):
            with self.subTest(keyword=keyword):
                result = self.parse(
                    {
                        "case.py": (
                            "class Base: pass\n"
                            "try: pass\n"
                            f"{keyword} (Base := ValueError): pass\n"
                            "class D(Base): pass\n"
                        )
                    }
                )
                ref = self.refs(result)["D"]
                self.assertEqual(
                    ref.binding, shikake.BindingState("stable", True, False)
                )

    def test_same_method_never_appears_as_own_override_candidate(self) -> None:
        result = self.parse(
            {
                "case.py": (
                    "class A:\n    def m(self): pass\n"
                    "class C(A):\n    def m(self): pass\n"
                    "class A(C):\n    def m(self): pass\n"
                )
            }
        )
        self.assertTrue(result.override_candidates)
        self.assertTrue(
            all(
                candidate.method is not candidate.base_method
                for candidate in result.override_candidates
            )
        )
        self.assertTrue(
            any(
                candidate.derived_class.get_name("name") == "C"
                for candidate in result.override_candidates
            )
        )

    def test_package_attribute_and_star_export_compete_with_child_module(self) -> None:
        for initializer in (
            "from .real import Base as a\n",
            "from .real import *\n",
        ):
            with self.subTest(initializer=initializer):
                result = self.parse(
                    {
                        "__init__.py": initializer
                        if " as a" in initializer
                        else "from .real import *\n",
                        "real.py": "class a: pass\nclass Base: pass\n",
                        "a.py": "class Other: pass\n",
                        "case.py": "from . import a\nclass D(a): pass\n",
                    }
                )
                ref = self.refs(result)["D"]
                self.assertEqual(
                    ref.binding, shikake.BindingState("unstable", False, False)
                )
                self.assertEqual(len(ref.targets), 1)
                self.assertEqual(
                    ref.targets[0].get_name("name"),
                    "Base" if " as a" in initializer else "a",
                )

    def test_direct_package_class_collides_with_named_submodule(self) -> None:
        result = self.parse(
            {
                "__init__.py": "class a: pass\n",
                "a.py": "class Other: pass\n",
                "case.py": "from . import a\nclass D(a): pass\n",
            }
        )
        ref = self.refs(result)["D"]
        self.assertEqual(ref.binding, shikake.BindingState("unstable", False, False))
        self.assertEqual(ref.targets[0].get_name("name"), "a")

    def test_package_without_attribute_can_use_child_module(self) -> None:
        result = self.parse(
            {
                "__init__.py": "pass\n",
                "a.py": "class Base: pass\n",
                "case.py": "from . import a\nclass D(a.Base): pass\n",
            }
        )
        self.assertEqual(self.refs(result)["D"].targets[0].get_name("name"), "Base")

    def test_external_requires_full_written_module_path(self) -> None:
        source = "import framework\nx = framework.memory.Memory.new(1)\n"
        model = shikake.parse_source(source, definitions=memory_rules)
        kinds = {node.kind.id for node in model.walk()}
        self.assertNotIn("ext.memory.allocate", kinds)
        self.assertIn("model.value.call", kinds)

    def test_complementary_dotted_imports_do_not_conflict(self) -> None:
        for source in (
            "import framework.memory\nimport framework.other\n",
            "import framework.other\nimport framework.memory\n",
            "import framework.memory\nimport framework.memory\n",
        ):
            with self.subTest(source=source):
                model = shikake.parse_source(
                    source + "x = framework.memory.Memory.new(1)\n",
                    definitions=memory_rules,
                )
                self.assertEqual(
                    sum(node.kind.id == "ext.memory.allocate" for node in model.walk()),
                    1,
                )

    def test_distinct_external_alias_rebinding_stays_rejected(self) -> None:
        source = (
            "from framework.memory import Memory as M\nfrom other import M\nM.new(1)\n"
        )
        with self.assertRaises(shikake.ExternalModelingError):
            shikake.parse_source(source, definitions=memory_rules)


if __name__ == "__main__":
    unittest.main()
