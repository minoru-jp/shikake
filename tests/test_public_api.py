"""Public distribution and import contract, independent of Mica internals."""

import tomllib
import unittest
from pathlib import Path

import shikake
from shikake import _mica


class PublicApiTest(unittest.TestCase):
    def test_public_distribution_name(self) -> None:
        project = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )["project"]
        self.assertEqual(project["name"], "shikake")
        self.assertEqual(shikake.__version__, project["version"])
        self.assertEqual(
            project["urls"]["Repository"], "https://github.com/minoru-jp/shikake"
        )

    def test_only_shikake_owns_top_level_import(self) -> None:
        src = Path(__file__).resolve().parents[1] / "src"
        packages = [
            ".".join(path.parent.relative_to(src).parts)
            for path in src.rglob("__init__.py")
        ]
        self.assertIn("shikake", packages)
        self.assertIn("shikake._mica", packages)
        self.assertNotIn("mica", packages)
        self.assertFalse((src / "kangen").exists())  # No former-name import shim.
        self.assertTrue(
            all(name == "shikake" or name.startswith("shikake.") for name in packages)
        )

    def test_shikumi_supported_version_range(self) -> None:
        project = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )["project"]
        self.assertIn("shikumi>=0.2.4,<2.0.0", project["dependencies"])
        self.assertFalse(
            any(
                "shikumi-contrace" in item
                for item in project["optional-dependencies"]["dev"]
            )
        )

    def test_public_api_is_same_implementation(self) -> None:
        self.assertEqual(set(shikake.__all__), set(_mica.__all__))
        for name in shikake.__all__:
            self.assertIs(getattr(shikake, name), getattr(_mica, name))
        root = shikake.parse_source("answer = 1 + 2")
        self.assertEqual(root.kind.id, "model.module")
        self.assertTrue(shikake.inspect_source("answer = 1 + 2").complete)
        self.assertIs(shikake.kind_index(), _mica.kind_index())


if __name__ == "__main__":
    unittest.main()
