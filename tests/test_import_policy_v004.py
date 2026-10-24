"""Opt-in syntax-only import rules and wildcard independence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import shikake


class ImportPolicyTests(unittest.TestCase):
    def test_policy_free_imports_remain_unrestricted(self) -> None:
        source = "from strange import *\nfrom . import value\nimport os\n"
        self.assertTrue(shikake.inspect_source(source).complete)
        self.assertEqual(shikake.parse_source(source).kind.id, "model.module")

    def test_star_default_is_disabled_when_policy_is_given(self) -> None:
        with self.assertRaises(shikake.ImportPolicyError) as failure:
            shikake.parse_source(
                "from math import *", import_policy=shikake.ImportPolicy()
            )
        self.assertEqual(failure.exception.code, "import.policy_denied")
        inspected = shikake.inspect_source(
            "from math import *", import_policy=shikake.ImportPolicy()
        )
        self.assertFalse(inspected.complete)
        self.assertEqual(inspected.issues[0].category, "import_policy")
        self.assertIsNone(inspected.model)

    def test_explicit_star_permission_still_checks_module(self) -> None:
        denied = shikake.ImportPolicy(
            default="deny", allow=("math",), allow_star_import=True
        )
        self.assertTrue(
            shikake.inspect_source("from math import *", import_policy=denied).complete
        )
        issue = shikake.inspect_source("from os import *", import_policy=denied)
        self.assertEqual(issue.issues[0].code, "import.policy_denied")

    def test_allow_and_deny_with_module_and_member_paths(self) -> None:
        policy = shikake.ImportPolicy(
            default="deny", allow=("math", "demo.kinds:int32"), deny=("math:prod",)
        )
        self.assertTrue(
            shikake.inspect_source(
                "from math import sin\nfrom demo.kinds import int32",
                import_policy=policy,
            ).complete
        )
        for source in (
            "from math import prod",
            "from demo.kinds import float32",
            "import demo.kinds",
        ):
            with self.subTest(source=source):
                self.assertEqual(
                    shikake.inspect_source(source, import_policy=policy)
                    .issues[0]
                    .category,
                    "import_policy",
                )
        for code in ("import math", "import math.extra", "from math.extra import sin"):
            self.assertTrue(shikake.inspect_source(code, import_policy=policy).complete)

    def test_blacklist_and_conditional_import(self) -> None:
        policy = shikake.ImportPolicy(default="allow", deny=("os",))
        for code in (
            "import os",
            "from os import path",
            "if flag:\n    import os",
            "import os.path",
            "from os.path import join",
        ):
            with self.subTest(code=code):
                self.assertFalse(
                    shikake.inspect_source(code, import_policy=policy).complete
                )
        for code in ("import sys", "import oscar", "from oscar.path import test"):
            self.assertTrue(shikake.inspect_source(code, import_policy=policy).complete)

    def test_relative_import_uses_default_without_resolution(self) -> None:
        self.assertTrue(
            shikake.inspect_source(
                "from .local import thing", import_policy=shikake.ImportPolicy()
            ).complete
        )
        self.assertFalse(
            shikake.inspect_source(
                "from .local import thing",
                import_policy=shikake.ImportPolicy(default="deny"),
            ).complete
        )

    def test_binding_and_collection_ignore_star_but_keep_explicit_imports(self) -> None:
        source = "from unknown import *\nresult = tuple([1])\n"
        result = shikake.inspect_source(
            source, import_policy=shikake.ImportPolicy(allow_star_import=True)
        )
        self.assertTrue(result.complete)
        assert result.model is not None
        self.assertEqual(
            result.bindings_for(result.model, "tuple")[0].state,
            shikake.BindingState("builtin", False, False, False),
        )
        self.assertIn(
            "model.value.collection.sequence", {n.kind.id for n in result.model.walk()}
        )
        regular = shikake.inspect_source(
            "from x import name\nfrom other import name",
            import_policy=shikake.ImportPolicy(),
        )
        assert regular.model is not None
        self.assertTrue(regular.bindings_for(regular.model, "name")[0].state.may_rebind)

    def test_package_policy_strict_and_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pkg"
            root.mkdir()
            (root / "ok.py").write_text("import math\n")
            (root / "bad.py").write_text("from math import *\n")
            policy = shikake.ImportPolicy(default="deny", allow=("math",))
            with self.assertRaises(shikake.ImportPolicyError):
                shikake.parse_package(root, import_policy=policy)
            inspected = shikake.inspect_package(root, import_policy=policy)
            self.assertFalse(inspected.complete)
            self.assertEqual([i.category for i in inspected.issues], ["import_policy"])
            self.assertTrue(
                shikake.inspect_package(
                    root,
                    import_policy=shikake.ImportPolicy(
                        default="deny", allow=("math",), allow_star_import=True
                    ),
                ).complete
            )

    def test_invalid_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            shikake.ImportPolicy(default="invalid")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            shikake.ImportPolicy(allow=("math:*",))
        with self.assertRaises(ValueError):
            shikake.ImportPolicy(allow=(".foo",))
        with self.assertRaises(ValueError):
            shikake.ImportPolicy(deny=("os", "os"))


if __name__ == "__main__":
    unittest.main()
