"""Inspection repr limits binding expansion without hiding diagnostics."""

from __future__ import annotations

import unittest

import shikake


class InspectionDiagnosticReprTests(unittest.TestCase):
    def test_large_source_binding_facts_are_summarized(self) -> None:
        source = "".join(f"field_{index} = {index}\n" for index in range(500))
        inspection = shikake.inspect_source(source)
        self.assertTrue(inspection.complete)
        self.assertEqual(len(inspection.name_bindings), 500)

        text = repr(inspection)
        self.assertIn("SourceInspection(model=Model(", text)
        self.assertIn("issues=()", text)
        self.assertIn("name_bindings=<500 items>", text)
        self.assertNotIn("NameBinding(", text)
        self.assertLessEqual(len(text), 600)
        self.assertEqual(len(inspection.name_bindings), 500)

    def test_diagnostics_are_not_suppressed(self) -> None:
        invalid = shikake.inspect_source("def invalid(:\n", filename="broken.py")
        self.assertFalse(invalid.complete)
        self.assertEqual(len(invalid.issues), 1)
        text = repr(invalid)
        self.assertIn("SourceInspection(model=None, issues=(InspectionIssue(", text)
        self.assertIn("broken.py", text)
        self.assertIn("name_bindings=<0 items>", text)
        self.assertIn(repr(invalid.issues), text)

        second = shikake.InspectionIssue(
            "syntax_error", "second.py", "SyntaxError", "another error", 2, 0
        )
        with_two = shikake.SourceInspection(None, (*invalid.issues, second))
        self.assertIn(repr(with_two.issues), repr(with_two))

    def test_package_inspection_still_includes_diagnostics(self) -> None:
        root = shikake.parse_source("value = 1\n")
        package = shikake.PackageModel(root)
        issue = shikake.InspectionIssue(
            "syntax_error", "broken.py", "SyntaxError", "bad syntax", 1, 0
        )
        inspection = shikake.PackageInspection(package, (issue,))
        text = repr(inspection)
        self.assertIn("name_bindings=<0 items>", text)
        self.assertIn(repr(inspection.issues), text)
        self.assertEqual(inspection.issues, (issue,))


if __name__ == "__main__":
    unittest.main()
