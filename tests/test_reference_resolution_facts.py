"""AST references expose root binding facts separately from known candidates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class ReferenceResolutionFactsTests(unittest.TestCase):
    def parse(self, sources: dict[str, str]) -> shikake.PackageModel:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            for name, code in sources.items():
                (root / name).write_text(code, encoding="utf-8")
            return shikake.parse_package(root, analyses={"inheritance"})

    def refs(self, package: shikake.PackageModel) -> dict[str, shikake.BaseReference]:
        return {ref.subject.get_name("name"): ref for ref in package.base_references}

    def test_bare_annotations_do_not_introduce_bindings(self) -> None:
        parsed = self.parse(
            {
                "case.py": (
                    "B: type\n"
                    "class C(B): pass\n"
                    "class Bound: pass\n"
                    "Bound: type\n"
                    "class D(Bound): pass\n"
                    "Value: type = Bound\n"
                    "class E(Value): pass\n"
                )
            }
        )
        refs = self.refs(parsed)
        self.assertIsNone(refs["C"].binding)
        self.assertEqual(refs["C"].targets, ())
        self.assertEqual(
            refs["D"].binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(refs["D"].targets[0].get_name("name"), "Bound")
        self.assertEqual(
            refs["E"].binding, shikake.BindingState("stable", False, False)
        )
        names = {binding.name for binding in parsed.name_bindings}
        self.assertNotIn("B", names)
        self.assertIn("Bound", names)
        self.assertIn("Value", names)

    def test_bare_function_annotation_masks_outer_binding(self) -> None:
        parsed = self.parse(
            {
                "case.py": (
                    "class B: pass\n"
                    "def factory():\n"
                    "    B: int\n"
                    "    class Local(B): pass\n"
                    "class Container:\n"
                    "    B: int\n"
                    "    class Nested(B): pass\n"
                )
            }
        )
        refs = self.refs(parsed)
        self.assertIsNone(refs["Local"].binding)
        self.assertEqual(refs["Local"].targets, ())
        self.assertEqual(
            refs["Nested"].binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(refs["Nested"].targets[0].get_name("name"), "B")
        self.assertFalse(
            any(
                binding.name == "B"
                and binding.scope.kind.id == "model.definition.function"
                for binding in parsed.name_bindings
            )
        )

    def test_dotted_import_uses_only_the_explicit_written_module_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pkg"
            root.mkdir()
            (root / "a.py").write_text(
                "class Base:\n    def run(self): pass\n", encoding="utf-8"
            )
            (root / "case.py").write_text(
                "import pkg.a\n"
                "class Derived(pkg.a.Base):\n    def run(self): pass\n"
                "class Unknown(pkg.other.Base): pass\n"
                "class Missing(pkg.a.Missing): pass\n",
                encoding="utf-8",
            )
            (root / "alias.py").write_text(
                "import pkg.a as a\nclass Aliased(a.Base): pass\n",
                encoding="utf-8",
            )
            (root / "root_only.py").write_text(
                "import pkg\nclass NotImported(pkg.a.Base): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root)
        refs = self.refs(result)
        self.assertEqual(
            [candidate.get_name("name") for candidate in refs["Derived"].targets],
            ["Base"],
        )
        self.assertEqual(
            refs["Derived"].binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(
            len(
                [
                    candidate
                    for candidate in result.override_candidates
                    if candidate.derived_class is refs["Derived"].subject
                ]
            ),
            1,
        )
        self.assertEqual(
            [candidate.get_name("name") for candidate in refs["Aliased"].targets],
            ["Base"],
        )
        for name in ("Unknown", "Missing", "NotImported"):
            with self.subTest(name=name):
                self.assertEqual(refs[name].targets, ())

    def test_explicit_child_imports_without_init_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "app"
            (root / "sub").mkdir(parents=True)
            (root / "base.py").write_text(
                "class Base:\n    def run(self): pass\n", encoding="utf-8"
            )
            (root / "sub" / "base.py").write_text(
                "class SubBase: pass\n", encoding="utf-8"
            )
            # Reproduce the original spelling as well as aliased forms.
            (root / "relative_case.py").write_text(
                "from . import base\nclass RootRelative(base.Base): pass\n",
                encoding="utf-8",
            )
            (root / "absolute_case.py").write_text(
                "from app import base\nclass RootAbsolute(base.Base): pass\n",
                encoding="utf-8",
            )
            (root / "sub" / "sub_case.py").write_text(
                "from app.sub import base\nclass SubAbsolute(base.SubBase): pass\n",
                encoding="utf-8",
            )
            (root / "sub" / "child.py").write_text(
                "from . import base as relative\n"
                "from app import base as absolute\n"
                "from app.sub import base as named\n"
                "from .base import SubBase as direct\n"
                "import app.base as dotted\n"
                "import app\n"
                "from app import missing\n"
                "class Relative(relative.SubBase): pass\n"
                "class Absolute(absolute.Base):\n    def run(self): pass\n"
                "class Named(named.SubBase): pass\n"
                "class Direct(direct): pass\n"
                "class Dotted(dotted.Base): pass\n"
                "class NotImported(app.sub.base.SubBase): pass\n"
                "class Missing(missing.Base): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root)
        refs = self.refs(result)
        expected = {
            "Relative": "SubBase",
            "Absolute": "Base",
            "Named": "SubBase",
            "Direct": "SubBase",
            "Dotted": "Base",
            "RootRelative": "Base",
            "RootAbsolute": "Base",
            "SubAbsolute": "SubBase",
        }
        for derived, base in expected.items():
            with self.subTest(derived=derived):
                self.assertEqual(
                    [item.get_name("name") for item in refs[derived].targets],
                    [base],
                )
                self.assertEqual(
                    refs[derived].binding,
                    shikake.BindingState("stable", False, False),
                )
        self.assertEqual(refs["NotImported"].targets, ())
        self.assertEqual(refs["Missing"].targets, ())
        self.assertEqual(
            len(
                [
                    candidate
                    for candidate in result.override_candidates
                    if candidate.derived_class is refs["Absolute"].subject
                ]
            ),
            1,
        )

    def test_namespace_parent_with_importable_init_child(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "app"
            (root / "sub").mkdir(parents=True)
            (root / "sub" / "__init__.py").write_text(
                "class Base: pass\n", encoding="utf-8"
            )
            (root / "use.py").write_text(
                "from app import sub\nclass D(sub.Base): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root, analyses={"inheritance"})
        self.assertEqual(
            [item.get_name("name") for item in self.refs(result)["D"].targets],
            ["Base"],
        )

    def test_multiple_dotted_segments_and_outside_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pkg"
            (root / "a").mkdir(parents=True)
            (root / "a" / "b.py").write_text("class Base: pass\n", encoding="utf-8")
            (root / "case.py").write_text(
                "import pkg.a.b\nclass D(pkg.a.b.Base): pass\n"
                "import external_pkg.a\nclass External(external_pkg.a.Base): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root, analyses={"inheritance"})
        refs = self.refs(result)
        self.assertEqual(
            [target.get_name("name") for target in refs["D"].targets], ["Base"]
        )
        self.assertEqual(refs["External"].targets, ())
        self.assertEqual(
            refs["External"].binding, shikake.BindingState("stable", False, False)
        )

    def test_module_and_class_attributes(self) -> None:
        package = self.parse(
            {
                "base.py": "class Base: pass\n",
                "case.py": "import sample.base as source\nclass Outer:\n    class Local: pass\nclass A(source.Base): pass\nclass B(Outer.Local): pass\n",
            }
        )
        refs = self.refs(package)
        self.assertEqual(refs["A"].targets[0].get_name("name"), "Base")
        self.assertEqual(refs["B"].targets[0].get_name("name"), "Local")
        for name in ("A", "B"):
            self.assertEqual(
                refs[name].binding, shikake.BindingState("stable", False, False)
            )

    def test_missing_class_member_does_not_fall_back_to_module_name(self) -> None:
        parsed = self.parse(
            {
                "case.py": (
                    "class Inner:\n    def run(self): pass\n"
                    "class Outer: pass\n"
                    "class Derived(Outer.Inner):\n    def run(self): pass\n"
                )
            }
        )
        reference = self.refs(parsed)["Derived"]
        self.assertEqual(reference.targets, ())
        self.assertEqual(
            reference.binding, shikake.BindingState("stable", False, False)
        )
        self.assertEqual(parsed.override_candidates, ())

    def test_class_attribute_prefers_own_declaration_over_outer_same_name(self) -> None:
        parsed = self.parse(
            {
                "case.py": (
                    "class Inner: pass\n"
                    "class Outer:\n    class Inner: pass\n"
                    "class Derived(Outer.Inner): pass\n"
                )
            }
        )
        (target,) = self.refs(parsed)["Derived"].targets
        outer = next(
            model
            for model in parsed.walk()
            if model.kind.id == "model.definition.class"
            and model.get_name("name") == "Outer"
        )
        self.assertIn(target, tuple(outer.walk()))

    def test_class_member_lookup_does_not_use_class_global_declaration(self) -> None:
        parsed = self.parse(
            {
                "case.py": (
                    "class Inner: pass\n"
                    "class Outer:\n    global Inner\n"
                    "class Derived(Outer.Inner): pass\n"
                )
            }
        )
        self.assertEqual(self.refs(parsed)["Derived"].targets, ())

    def test_multihop_import_and_cycle(self) -> None:
        parsed = self.parse(
            {
                "a.py": "class Base: pass\n",
                "b.py": "from .a import Base as Alias\n",
                "c.py": "from .b import Alias as Again\nclass D(Again): pass\n",
            }
        )
        self.assertEqual(self.refs(parsed)["D"].targets[0].get_name("name"), "Base")
        parsed = self.parse(
            {
                "a.py": "from .b import Other as Base\n",
                "b.py": "from .a import Base as Other\n",
                "c.py": "from .a import Base\nclass D(Base): pass\n",
            }
        )
        self.assertEqual(self.refs(parsed)["D"].targets, ())
        self.assertEqual(
            self.refs(parsed)["D"].binding, shikake.BindingState("stable", False, False)
        )

    def test_conditional_imports_keep_all_explicit_base_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            (root / "base.py").write_text(
                "class Base:\n    def run(self): pass\n", encoding="utf-8"
            )
            (root / "alt.py").write_text(
                "class Base:\n    def run(self): pass\n", encoding="utf-8"
            )
            (root / "case.py").write_text(
                "try:\n"
                "    from .base import Base\n"
                "except ImportError:\n"
                "    from .alt import Base\n"
                "class D(Base):\n    def run(self): pass\n",
                encoding="utf-8",
            )
            result = shikake.parse_package(root)
        ref = self.refs(result)["D"]
        self.assertEqual(len(ref.targets), 2)
        self.assertEqual(ref.binding, shikake.BindingState("unstable", True, False))
        self.assertEqual(
            {candidate.base_module for candidate in result.override_candidates},
            {"sample.base", "sample.alt"},
        )
        self.assertEqual(len(result.override_candidates), 2)

    def test_conditional_imports_and_class_definitions_share_candidates(self) -> None:
        parsed = self.parse(
            {
                "base.py": "class Base: pass\n",
                "case.py": (
                    "if choice:\n"
                    "    class B: pass\n"
                    "elif alternative:\n"
                    "    from .base import Base as B\n"
                    "else:\n"
                    "    from .missing import B\n"
                    "class D(B): pass\n"
                ),
            }
        )
        ref = self.refs(parsed)["D"]
        self.assertEqual(len(ref.targets), 2)
        self.assertEqual(ref.binding, shikake.BindingState("unstable", True, False))

    def test_conditional_module_imports_follow_written_attributes(self) -> None:
        parsed = self.parse(
            {
                "one.py": "class Base: pass\n",
                "two.py": "class Base: pass\n",
                "case.py": (
                    "if flag:\n"
                    "    from . import one as selected\n"
                    "else:\n"
                    "    from . import two as selected\n"
                    "class D(selected.Base): pass\n"
                    "class NoGuess(selected.Missing): pass\n"
                ),
            }
        )
        refs = self.refs(parsed)
        self.assertEqual(len(refs["D"].targets), 2)
        self.assertEqual(
            refs["D"].binding, shikake.BindingState("unstable", True, False)
        )
        self.assertEqual(refs["NoGuess"].targets, ())

    def test_conditional_imports_respect_written_position_and_scope(self) -> None:
        parsed = self.parse(
            {
                "base.py": "class Base: pass\n",
                "case.py": (
                    "class Early(B): pass\n"
                    "if flag:\n"
                    "    from .base import Base as B\n"
                    "class Late(B): pass\n"
                    "class B: pass\n"
                    "class Later(B): pass\n"
                ),
            }
        )
        refs = self.refs(parsed)
        self.assertEqual(refs["Early"].targets, ())
        self.assertEqual(len(refs["Late"].targets), 1)
        self.assertEqual(len(refs["Later"].targets), 2)
        self.assertEqual(
            refs["Late"].binding, shikake.BindingState("unstable", True, False)
        )

    def test_repeated_import_to_same_class_is_not_duplicate_candidate(self) -> None:
        parsed = self.parse(
            {
                "base.py": "class Base: pass\n",
                "case.py": (
                    "if flag:\n"
                    "    from .base import Base\n"
                    "else:\n"
                    "    from .base import Base\n"
                    "del Base\n"
                    "class D(Base): pass\n"
                ),
            }
        )
        ref = self.refs(parsed)["D"]
        self.assertEqual(len(ref.targets), 1)
        self.assertEqual(ref.binding, shikake.BindingState("unstable", True, True))

    def test_conditional_circular_imports_do_not_invent_candidates(self) -> None:
        parsed = self.parse(
            {
                "a.py": "if condition:\n    from .b import Base\n",
                "b.py": "if condition:\n    from .a import Base\n",
                "case.py": "from .a import Base\nclass D(Base): pass\n",
            }
        )
        self.assertEqual(self.refs(parsed)["D"].targets, ())

    def test_alternative_class_definitions_keep_candidates(self) -> None:
        parsed = self.parse(
            {
                "case.py": "try:\n    class A: pass\nexcept Exception:\n    class A: pass\nclass D(A): pass\n"
            }
        )
        ref = self.refs(parsed)["D"]
        self.assertEqual(len(ref.targets), 2)
        self.assertEqual(ref.binding, shikake.BindingState("unstable", True, False))

    def test_package_attribute_import_is_not_guessed(self) -> None:
        parsed = self.parse(
            {
                "__init__.py": "from .real import Base as a\n",
                "real.py": "class Base: pass\n",
                "a.py": "class Base: pass\n",
                "case.py": "from . import a\nclass D(a): pass\nclass E(a.Base): pass\n",
            }
        )
        refs = self.refs(parsed)
        self.assertEqual(
            refs["D"].binding, shikake.BindingState("unstable", False, False)
        )
        # Attribute candidates survive the package/submodule collision even
        # though the independent binding property remains unstable.
        self.assertEqual(refs["D"].targets[0].get_name("name"), "Base")
        self.assertEqual(refs["D"].binding.introduction, "unstable")  # type: ignore[union-attr]
        self.assertEqual(refs["E"].targets, ())

    def test_function_scope_skips_class_namespace(self) -> None:
        parsed = self.parse(
            {
                "case.py": "class Holder:\n    class Base: pass\n    def f(self):\n        class Derived(Base): pass\n"
            }
        )
        ref = self.refs(parsed)["Derived"]
        self.assertIsNone(ref.binding)
        self.assertEqual(ref.targets, ())

    def test_statically_known_star_exports(self) -> None:
        parsed = self.parse(
            {
                "base.py": "class Base: pass\n",
                "case.py": "from .base import *\nclass D(Base): pass\n",
            }
        )
        self.assertEqual(self.refs(parsed)["D"].targets[0].get_name("name"), "Base")


if __name__ == "__main__":
    unittest.main()
