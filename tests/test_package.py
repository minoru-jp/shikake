"""Bootstrap checks; replace and extend when Model contracts are defined."""

import tomllib
import unittest
from pathlib import Path

import shikake


class PackageSmokeTest(unittest.TestCase):
    def test_current_version(self) -> None:
        project = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )["project"]
        self.assertEqual(shikake.__version__, project["version"])
        self.assertEqual(shikake.__version__, "0.0.5")


if __name__ == "__main__":
    unittest.main()
