"""Document generator contracts without rendering or writing Markdown."""

import json
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from devdocs import generate


class DocumentGeneratorTest(unittest.TestCase):
    def test_context_uses_pyproject_version_as_single_source(self) -> None:
        project = tomllib.loads(
            (generate.ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        context = json.loads(generate._context_json())
        self.assertEqual(context["project"]["name"], project["name"])
        self.assertEqual(context["project"]["version"], project["version"])
        self.assertEqual(
            context["project"]["requires_python"], project["requires-python"]
        )
        self.assertEqual(context["project"]["import_name"], "shikake")

    def test_default_output_is_temporary_and_removed_after_render(self) -> None:
        output: Path | None = None

        def render(args: list[str], **kwargs: object) -> object:
            nonlocal output
            output = Path(args[7])
            self.assertTrue(output.parent.is_dir())
            self.assertTrue(output.is_relative_to(Path(tempfile.gettempdir())))
            return type("Result", (), {"returncode": 0})()

        with patch.object(generate.subprocess, "run", side_effect=render) as run:
            self.assertEqual(generate.main(["specification/binding"]), 0)
        args = run.call_args.args[0]
        self.assertEqual(
            args[3:6],
            ["render", "document", "devdocs.canonical_sources.specification.binding"],
        )
        self.assertEqual(args[6], "-o")
        self.assertEqual(Path(args[7]), output)
        assert output is not None
        self.assertEqual(output.name, "specification")
        self.assertFalse(output.parent.exists())
        self.assertEqual(args[8], "--context")
        self.assertEqual(json.loads(args[9])["project"]["name"], "shikake")
        self.assertEqual(run.call_args.kwargs["cwd"], generate.ROOT)

    def test_temporary_output_is_removed_on_render_failure(self) -> None:
        output: Path | None = None

        def render(args: list[str], **kwargs: object) -> object:
            nonlocal output
            output = Path(args[7])
            return type("Result", (), {"returncode": 2})()

        with patch.object(generate.subprocess, "run", side_effect=render):
            self.assertEqual(generate.main(["specification/binding"]), 2)
        self.assertIsNotNone(output)
        assert output is not None
        self.assertFalse(output.parent.exists())

    def test_alias_and_explicit_output_directory(self) -> None:
        output = generate.ROOT / "custom-out"
        with patch.object(generate.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(generate.main(["policy", "-o", str(output)]), 0)
        args = run.call_args.args[0]
        self.assertEqual(args[5], "devdocs.canonical_sources.policy.canonical")
        self.assertEqual(args[7], str(output))

    def test_rejects_missing_and_outside_sources_without_rendering(self) -> None:
        with patch.object(generate.subprocess, "run") as run:
            for name in ("../pyproject", "specification/not_here", "../../src/shikake"):
                stderr = StringIO()
                with (
                    self.subTest(name=name),
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as raised,
                ):
                    generate.main([name])
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("usage:", stderr.getvalue())
                self.assertIn(
                    "invalid source name"
                    if ".." in name
                    else "canonical source not found",
                    stderr.getvalue(),
                )
        run.assert_not_called()

    def test_rejects_canonical_documents_as_explicit_output(self) -> None:
        forbidden = generate.DEV_DOCS / "canonical_documents"
        with patch.object(generate.subprocess, "run") as run:
            for output in (forbidden, forbidden / "specification"):
                stderr = StringIO()
                with (
                    self.subTest(output=output),
                    redirect_stderr(stderr),
                    self.assertRaises(SystemExit) as raised,
                ):
                    generate.main(["policy", "--output", str(output)])
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("usage:", stderr.getvalue())
                self.assertIn("not a supported output path", stderr.getvalue())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
