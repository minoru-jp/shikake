"""Render a canonical source transiently, without persisting canonical Markdown.

Use ``-o`` only when a separate workflow will consume the result (for example,
reviewing the Japanese source before preparing its English public translation).
The caller is responsible for disposing of an explicitly supplied output path.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path

DEV_DOCS = Path(__file__).resolve().parent
ROOT = DEV_DOCS.parent
SOURCES = DEV_DOCS / "canonical_sources"


def _source_module(source: str) -> tuple[str, Path]:
    """Resolve a source relative to canonical_sources (never arbitrary imports)."""
    relative = source.removesuffix(".py").replace("\\", "/")
    parts = relative.split("/")
    if not all(part.isidentifier() for part in parts):
        raise ValueError(f"invalid source name: {source}")

    source_path = SOURCES.joinpath(*parts)
    if source_path.is_dir():
        source_path /= "canonical.py"
        parts.append("canonical")
    else:
        source_path = source_path.with_suffix(".py")
    if not source_path.is_file():
        raise ValueError(f"canonical source not found: {source}")

    return f"devdocs.canonical_sources.{'.'.join(parts)}", Path(*parts[:-1])


def _context_json() -> str:
    context = json.loads((DEV_DOCS / "context.json").read_text(encoding="utf-8"))
    if not isinstance(context, dict):
        raise TypeError("context.json must contain a JSON object")
    project_context = context.setdefault("project", {})
    if not isinstance(project_context, dict):
        raise TypeError("context.json project must be a JSON object")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    # Package metadata is authoritative; context.json holds only extra values.
    project_context.update(
        name=project["name"],
        version=project["version"],
        requires_python=project["requires-python"],
    )
    return json.dumps(context, ensure_ascii=False)


def _render(module: str, output: Path, context_json: str) -> int:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "shikumi_devdoc.cli",
            "render",
            "document",
            module,
            "-o",
            str(output),
            "--context",
            context_json,
        ],
        cwd=ROOT,
        check=False,
    ).returncode


def _explicit_output(path: Path) -> Path:
    output = path.expanduser().resolve()
    forbidden = (DEV_DOCS / "canonical_documents").resolve()
    if output == forbidden or forbidden in output.parents:
        raise ValueError("devdocs/canonical_documents is not a supported output path")
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        help="source under devdocs/canonical_sources, e.g. specification/binding",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="explicit output directory; otherwise render to a temporary directory and discard",
    )
    args = parser.parse_args(argv)

    try:
        module, group = _source_module(args.source)
        context_json = _context_json()
        output = _explicit_output(args.output) if args.output is not None else None
    except (OSError, ValueError, TypeError, KeyError, tomllib.TOMLDecodeError) as exc:
        parser.error(str(exc))

    if output is not None:
        return _render(module, output, context_json)
    with tempfile.TemporaryDirectory(prefix="shikake-canonical-") as temporary:
        return _render(module, Path(temporary) / group, context_json)


if __name__ == "__main__":
    raise SystemExit(main())
