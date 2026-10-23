"""External declaration imports must not lose their protection in nested scopes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import external_memory_definitions as rules

import shikake


class ExternalImportLocationTests(unittest.TestCase):
    def test_registered_import_in_unsupported_location_is_rejected(self) -> None:
        imports = (
            "from framework.memory import Memory",
            "from framework.memory import Memory as M",
            "import framework.memory",
            "import framework.memory as mem",
            "from framework import memory",
        )
        contexts = (
            lambda line: f"if True:\n    {line}\n",
            lambda line: f"if False:\n    {line}\n",
            lambda line: f"try:\n    {line}\nexcept ImportError:\n    pass\n",
            lambda line: f"try:\n    pass\nexcept ImportError:\n    {line}\n",
            lambda line: f"def f():\n    {line}\n",
            lambda line: f"class Holder:\n    {line}\n",
            lambda line: f"for item in items:\n    {line}\n",
        )
        for imported in imports:
            for context in contexts:
                source = context(imported)
                with self.subTest(source=source):
                    with self.assertRaisesRegex(
                        shikake.ExternalModelingError,
                        "registered external import must be unconditional at module level",
                    ):
                        shikake.parse_source(source, definitions=rules)
                    inspected = shikake.inspect_source(source, definitions=rules)
                    self.assertFalse(inspected.complete)
                    self.assertEqual(
                        inspected.issues[0].category, "external_definition"
                    )

    def test_import_itself_is_rejected_without_any_external_use(self) -> None:
        source = "def f():\n    from framework.memory import Memory\n"
        with self.assertRaises(shikake.ExternalModelingError) as raised:
            shikake.parse_source(source, definitions=rules)
        self.assertEqual(raised.exception.line, 2)
        for body in ("alias = Memory.new", "return Memory.new(1)"):
            with (
                self.subTest(body=body),
                self.assertRaises(shikake.ExternalModelingError),
            ):
                shikake.parse_source(source + f"    {body}\n", definitions=rules)

    def test_module_level_direct_import_still_activates_protection(self) -> None:
        cases = (
            "from framework.memory import Memory\nx = Memory.new(1)\n",
            "import framework.memory\nx = framework.memory.Memory.new(1)\n",
            "import framework.memory as mem\nx = mem.Memory.new(1)\n",
        )
        for source in cases:
            with self.subTest(source=source):
                result = shikake.parse_source(source, definitions=rules)
                self.assertIn(
                    "ext.memory.allocate", {node.kind.id for node in result.walk()}
                )

    def test_non_registered_imports_are_not_restricted(self) -> None:
        for imported in (
            "from framework.memory import helper",
            "import framework.memory.unrelated",
            "import framework",
            "from another.module import Memory",
            "from another.module import *",
        ):
            with self.subTest(imported=imported):
                result = shikake.inspect_source(
                    f"def f():\n    {imported}\n",
                    definitions=rules,
                    syntax_validation="ast"
                    if imported.endswith("import *")
                    else "compile",
                )
                self.assertTrue(result.complete, result.issues)

    def test_registered_module_wildcard_import_is_rejected(self) -> None:
        for source in (
            "from framework.memory import *\n",
            "if False:\n    from framework.memory import *\n",
        ):
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(
                    shikake.ExternalModelingError, "wildcard import"
                ),
            ):
                shikake.parse_source(source, definitions=rules)
        self.assertTrue(
            shikake.inspect_source(
                "from other_package import *\n", definitions=rules
            ).complete
        )

    def test_partial_package_keeps_unaffected_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "example"
            folder.mkdir()
            (folder / "bad.py").write_text(
                "try:\n    from framework.memory import Memory\n"
                "except ImportError:\n    pass\n",
                encoding="utf-8",
            )
            (folder / "good.py").write_text("class Good: pass\n", encoding="utf-8")
            result = shikake.inspect_package(folder, definitions=rules)
        self.assertFalse(result.complete)
        self.assertEqual(result.issues[0].category, "external_definition")
        self.assertIn(
            "Good",
            {
                node.get_name("name")
                for node in result.package.walk()
                if node.kind.id == "model.definition.class"
            },
        )


if __name__ == "__main__":
    unittest.main()
