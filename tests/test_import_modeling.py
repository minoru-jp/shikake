"""Imports remain Models; consumers may explicitly request acceptance checks."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

import shikake
from shikake.external import ExternalDefinitionsBuilder


class ImportModelingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.definitions = (
            ExternalDefinitionsBuilder()
            .add_call("dot:Fn.sin", "test.fn.sin", ("v",))
            .add_type("demo.kinds:int32", "test.int32")
            .build()
        )

    def test_all_parsing_apis_expose_opt_in_import_policy(self) -> None:
        for api in (
            shikake.parse_source,
            shikake.inspect_source,
            shikake.parse_package,
            shikake.inspect_package,
        ):
            with self.subTest(api=api.__name__):
                self.assertIn("import_policy", inspect.signature(api).parameters)
                self.assertNotIn("allowed_modules", inspect.signature(api).parameters)

    def test_unknown_and_unregistered_imports_are_modeled_without_loading(self) -> None:
        source = (
            "import module_that_cannot_exist_in_this_test\n"
            "from dot import Fn, helper\n"
            "from demo.kinds import int32\n"
            "x = Fn.sin(1)\n"
            "y: int32 = 3\n"
        )
        strict = shikake.parse_source(source, definitions=self.definitions)
        partial = shikake.inspect_source(source, definitions=self.definitions)
        self.assertTrue(partial.complete, partial.issues)
        self.assertEqual(strict, partial.model)
        kinds = {model.kind.id for model in strict.walk()}
        self.assertIn("test.fn.sin", kinds)
        self.assertIn("test.int32", kinds)

    def test_relative_and_star_imports_have_no_special_rejection(self) -> None:
        sources = (
            "from . import something\n",
            "from ..math import sqrt\n",
            "from math import *\n",
            "import unknown\n",
        )
        for source in sources:
            with self.subTest(source=source):
                strict = shikake.parse_source(source)
                partial = shikake.inspect_source(source)
                self.assertTrue(partial.complete, partial.issues)
                self.assertEqual(strict, partial.model)

    def test_package_preserves_all_syntactically_valid_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "dialect"
            root.mkdir()
            (root / "registered.py").write_text(
                "from dot import Fn\nx = Fn.sin(1)\n", encoding="utf-8"
            )
            (root / "other.py").write_text(
                "import os\nfrom other import something\n", encoding="utf-8"
            )
            strict = shikake.parse_package(root, definitions=self.definitions)
            partial = shikake.inspect_package(root, definitions=self.definitions)
            self.assertTrue(partial.complete, partial.issues)
            self.assertEqual(strict.model, partial.model)
            self.assertEqual(len(strict.model.get_nodes("modules")), 2)
            self.assertTrue(any(m.kind.id == "test.fn.sin" for m in strict.walk()))

    def test_caller_may_check_import_models_with_own_policy(self) -> None:
        model = shikake.parse_source("import os\nimport math\n")
        imports = [
            part for part in model.walk() if part.kind.id == "model.import.direct"
        ]
        self.assertEqual(len(imports), 2)
        # Policy decisions belong to the caller, not shikake.
        self.assertEqual(len([m for m in imports if m is not None]), 2)


if __name__ == "__main__":
    unittest.main()
