"""Opt-in syntactic import restrictions never resolve or execute import targets."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

import shikake
from shikake.external import ExternalDefinitionsBuilder, ImportedCall


class ImportPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.definitions = (
            ExternalDefinitionsBuilder()
            .add_call("dot:Fn.sin", "test.fn.sin", ("v",))
            .add_call("vendor.geometry:Vector.create", "test.vector.create", ("v",))
            .build()
        )

    def test_default_is_unrestricted_without_regression(self) -> None:
        source = "import math\nfrom dot import Fn\nx = Fn.sin(1)\n"
        strict = shikake.parse_source(source, definitions=self.definitions)
        partial = shikake.inspect_source(source, definitions=self.definitions)
        self.assertTrue(partial.complete)
        self.assertEqual(strict, partial.model)
        self.assertTrue(shikake.inspect_source("import os\n").complete)

    def test_registered_interfaces_accepts_only_explicit_root_imports(self) -> None:
        accepted = (
            "from dot import Fn\nx = Fn.sin(1)\n",
            "from dot import Fn as F\nx = F.sin(1)\n",
            "from vendor.geometry import Vector\nx = Vector.create(1)\n",
            "from dot import Fn\nfrom vendor.geometry import Vector\n",
        )
        for source in accepted:
            with self.subTest(source=source):
                result = shikake.inspect_source(
                    source,
                    definitions=self.definitions,
                    import_policy="registered_interfaces",
                )
                self.assertTrue(result.complete, result.issues)
                self.assertEqual(
                    result.model,
                    shikake.parse_source(
                        source,
                        definitions=self.definitions,
                        import_policy="registered_interfaces",
                    ),
                )

    def test_registered_interfaces_rejects_broad_and_unlisted_imports(self) -> None:
        forbidden = (
            "import dot\n",
            "import dot as d\n",
            "import math\n",
            "from dot import helper\n",
            "from dot import Fn, helper\n",
            "from dot import sin\n",
            "from dot import *\n",
            "from . import Fn\n",
            "from vendor import geometry\n",
            "import vendor.geometry\n",
            "if False:\n    import math\n",
            "def f():\n    import os\n",
        )
        for source in forbidden:
            with self.subTest(source=source):
                with self.assertRaises(shikake.ExternalModelingError) as caught:
                    shikake.parse_source(
                        source,
                        definitions=self.definitions,
                        import_policy="registered_interfaces",
                    )
                self.assertEqual(caught.exception.code, "external.unregistered_import")
                result = shikake.inspect_source(
                    source,
                    definitions=self.definitions,
                    import_policy="registered_interfaces",
                )
                self.assertFalse(result.complete)
                self.assertIsNone(result.model)
                self.assertEqual(len(result.issues), 1)
                self.assertEqual(result.issues[0].code, "external.unregistered_import")
                self.assertEqual(
                    result.issues[0].details["policy"], "registered_interfaces"
                )
                self.assertIsNone(result.issues[0].skipped_span)

    def test_registered_modules_includes_trusted_and_named_modules(self) -> None:
        source = """import dot as d
from dot import helper
from math import no_such_name
import vendor.geometry as geo
import custom_tools
x = d.Fn.sin(1)
y = math.sin(2)
"""
        # The existence of the imported modules and attributes is irrelevant.
        accepted = shikake.inspect_source(
            source,
            definitions=self.definitions,
            import_policy="registered_modules",
            allowed_modules=("math", "custom_tools"),
        )
        self.assertTrue(accepted.complete, accepted.issues)
        strict = shikake.parse_source(
            source,
            definitions=self.definitions,
            import_policy="registered_modules",
            allowed_modules=("math", "custom_tools"),
        )
        self.assertEqual(strict, accepted.model)
        self.assertTrue(any(m.kind.id == "test.fn.sin" for m in strict.walk()))
        # A user-specified module works even without any external definitions.
        self.assertTrue(
            shikake.inspect_source(
                "import custom_tools\n",
                import_policy="registered_modules",
                allowed_modules=("custom_tools",),
            ).complete
        )

    def test_exact_module_name_not_prefix_or_runtime_equivalence(self) -> None:
        allowed = ("my_company.geometry",)
        for source in (
            "import my_company.geometry\n",
            "import my_company.geometry as geo\n",
            "from my_company.geometry import Vector\n",
        ):
            with self.subTest(source=source):
                self.assertTrue(
                    shikake.inspect_source(
                        source,
                        import_policy="registered_modules",
                        allowed_modules=allowed,
                    ).complete
                )
        for source in (
            "import my_company\n",
            "import my_company.geometry.extra\n",
            "from my_company import geometry\n",
            "from my_company.other import Vector\n",
        ):
            with self.subTest(source=source):
                result = shikake.inspect_source(
                    source,
                    import_policy="registered_modules",
                    allowed_modules=allowed,
                )
                self.assertEqual(result.issues[0].code, "external.unregistered_import")
                self.assertIsNone(result.model)

    def test_all_restricted_modes_forbid_relative_and_star_import(self) -> None:
        for policy, allowed_modules in (
            ("registered_interfaces", ()),
            ("registered_modules", ("math",)),
        ):
            for source in (
                "from . import something\n",
                "from ..math import sqrt\n",
                "from math import *\n",
                "from dot import *\n",
            ):
                with self.subTest(policy=policy, source=source):
                    result = shikake.inspect_source(
                        source,
                        definitions=self.definitions,
                        import_policy=cast(Any, policy),
                        allowed_modules=allowed_modules,
                    )
                    self.assertIsNone(result.model)
                    self.assertEqual(
                        result.issues[0].code, "external.unregistered_import"
                    )

    def test_existing_external_structure_protection_remains(self) -> None:
        source = "from dot import Fn\nFn.sin(1)\n"
        # Registered structure roots still may only be imported unconditionally
        # at the top level; a permissive module policy does not override this.
        bad = "if condition:\n    from dot import Fn\n"
        for policy in ("registered_interfaces", "registered_modules"):
            self.assertTrue(
                shikake.inspect_source(
                    source,
                    definitions=self.definitions,
                    import_policy=policy,
                ).complete
            )
            result = shikake.inspect_source(
                bad, definitions=self.definitions, import_policy=policy
            )
            self.assertIsNone(result.model)
            self.assertEqual(result.issues[0].code, "external.import_scope")
            reserved = shikake.inspect_source(
                "from dot import Fn\nFn = 2\n",
                definitions=self.definitions,
                import_policy=policy,
            )
            self.assertIsNone(reserved.model)
            self.assertEqual(reserved.issues[0].code, "external.reserved_name_rebound")

    def test_invalid_options_are_rejected_before_parsing(self) -> None:
        invalid: tuple[tuple[object, object, type[Exception]], ...] = (
            ("unknown", (), ValueError),
            (None, (), TypeError),
            ("unrestricted", ("math",), ValueError),
            ("registered_interfaces", ("math",), ValueError),
            ("registered_modules", ("math", "math"), ValueError),
            ("registered_modules", "math", TypeError),
            ("registered_modules", ("",), ValueError),
            ("registered_modules", (".math",), ValueError),
            ("registered_modules", ("math.",), ValueError),
            ("registered_modules", ("math..extra",), ValueError),
            ("registered_modules", ("for",), ValueError),
            ("registered_modules", (17,), TypeError),
            ("registered_modules", ["math"], TypeError),
        )
        for policy, modules, error in invalid:
            with self.subTest(policy=policy, modules=modules):
                for api in (shikake.parse_source, shikake.inspect_source):
                    with self.assertRaises(error):
                        api(
                            "def bad(:",
                            import_policy=cast(Any, policy),
                            allowed_modules=cast(Any, modules),
                        )

    def test_nested_external_roots_respect_policy_inclusion(self) -> None:
        # The colon fixes the declared module as "pkg", even when the
        # registered structural root is spelled "pkg.mod.Cls".
        definitions = (
            ExternalDefinitionsBuilder()
            .add_call("pkg:mod.Cls.make", "test.nested.make", ("value",))
            .add_call(
                "vendor.geometry:api.Vector.create", "test.nested.vector", ("value",)
            )
            .build()
        )
        roots = (
            "from pkg.mod import Cls as C\nx = C.make(1)\n",
            "from vendor.geometry.api import Vector\nx = Vector.create(1)\n",
        )
        for source in roots:
            for policy in ("registered_interfaces", "registered_modules"):
                with self.subTest(source=source, policy=policy):
                    inspection = shikake.inspect_source(
                        source, definitions=definitions, import_policy=policy
                    )
                    self.assertTrue(inspection.complete, inspection.issues)
                    model = inspection.model
                    assert model is not None
                    self.assertEqual(
                        inspection.model,
                        shikake.parse_source(
                            source, definitions=definitions, import_policy=policy
                        ),
                    )
                    self.assertTrue(
                        any(m.kind.id.startswith("test.nested.") for m in model.walk())
                    )
        # A structural root permission is NOT permission to import its whole
        # parent namespace as a module.
        for source in (
            "from pkg.mod import helper\n",
            "import pkg.mod\n",
            "from vendor.geometry.api import helper\n",
        ):
            with self.subTest(source=source):
                inspection = shikake.inspect_source(
                    source, definitions=definitions, import_policy="registered_modules"
                )
                self.assertFalse(inspection.complete)
                self.assertEqual(
                    inspection.issues[0].code, "external.unregistered_import"
                )

    def test_future_annotations_directive_is_narrow_exception(self) -> None:
        accepted = "from __future__ import annotations\nclass C:\n    pass\n"
        for policy in ("registered_interfaces", "registered_modules"):
            with self.subTest(policy=policy):
                self.assertTrue(
                    shikake.inspect_source(accepted, import_policy=policy).complete
                )
                shikake.parse_source(accepted, import_policy=policy)
                for forbidden in (
                    "import __future__\n",
                    "from __future__ import division\n",
                    "from __future__ import annotations, division\n",
                    "from __future__ import annotations as a\n",
                ):
                    with self.subTest(source=forbidden):
                        inspection = shikake.inspect_source(
                            forbidden, import_policy=policy
                        )
                        self.assertEqual(
                            inspection.issues[0].code, "external.unregistered_import"
                        )
                        self.assertIsNone(inspection.model)

    def test_nfkc_module_name_is_rejected_without_rewriting(self) -> None:
        for module in ("ｍath", "math.Ｆoo", "Kase"):
            with self.subTest(module=module):
                for api in (shikake.parse_source, shikake.inspect_source):
                    with self.assertRaises(ValueError):
                        api(
                            "import math\n",
                            import_policy="registered_modules",
                            allowed_modules=(module,),
                        )
                for target in (f"{module}:Fn.sin", f"math:{module}.sin"):
                    with self.assertRaises(ValueError):
                        ImportedCall(target)
        self.assertTrue(
            shikake.inspect_source(
                "import math\n",
                import_policy="registered_modules",
                allowed_modules=("math",),
            ).complete
        )

    def test_violation_is_still_first_per_source_in_partial(self) -> None:
        inspection = shikake.inspect_source(
            "import os\nimport sys\nimport json\n",
            import_policy="registered_interfaces",
        )
        self.assertFalse(inspection.complete)
        self.assertIsNone(inspection.model)
        self.assertEqual(len(inspection.issues), 1)
        self.assertEqual(inspection.issues[0].details["path"], "os")

    def test_partial_package_violation_only_excludes_bad_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "dialect"
            root.mkdir()
            (root / "good.dot").write_text(
                "import math\nx=math.sqrt(4)\n", encoding="utf-8"
            )
            (root / "bad.dot").write_text("import os\ny=1\n", encoding="utf-8")
            with self.assertRaises(shikake.ExternalModelingError):
                shikake.parse_package(
                    root,
                    extensions=(".dot",),
                    import_policy="registered_modules",
                    allowed_modules=("math",),
                )
            result = shikake.inspect_package(
                root,
                extensions=(".dot",),
                import_policy="registered_modules",
                allowed_modules=("math",),
            )
            self.assertFalse(result.complete)
            self.assertEqual(len(result.issues), 1)
            issue = result.issues[0]
            self.assertEqual(issue.category, "external_definition")
            self.assertEqual(issue.code, "external.unregistered_import")
            self.assertEqual(issue.details["path"], "os")
            self.assertIsNone(issue.skipped_span)
            self.assertEqual(
                [m.get("name") for m in result.model.get_nodes("modules")],
                ["dialect.good"],
            )
            self.assertEqual(result.name_bindings, ())
            self.assertEqual(result.base_references, ())

    def test_include_filters_before_import_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "dialect"
            root.mkdir()
            (root / "good.py").write_text("import math\n", encoding="utf-8")
            (root / "bad.py").write_text("import os\n", encoding="utf-8")
            kwargs = {
                "import_policy": "registered_modules",
                "allowed_modules": ("math",),
                "include": lambda path, is_directory: path.name != "bad.py",
            }
            for api in (shikake.parse_package, shikake.inspect_package):
                result = api(root, **kwargs)
                self.assertEqual(
                    [m.get("name") for m in result.model.get_nodes("modules")],
                    ["dialect.good"],
                )

    def test_invalid_options_on_empty_package_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for api in (shikake.parse_package, shikake.inspect_package):
                with self.assertRaises(ValueError):
                    api(
                        temp,
                        import_policy="registered_interfaces",
                        allowed_modules=("math",),
                    )
                result = api(
                    temp, import_policy="registered_modules", allowed_modules=("math",)
                )
                self.assertEqual(result.model.kind.id, "model.package")


if __name__ == "__main__":
    unittest.main()
