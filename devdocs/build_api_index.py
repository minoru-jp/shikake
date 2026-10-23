"""Derive the English API index from the two published API translations.

The index is navigation, not a separate canonical document. To change an API
contract, edit its Japanese canonical source and republish its translation first.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DOCS = ROOT / "docs" / "api_reference"
API_HEADING = re.compile(r"^## (API_\d{3}): `([^`]+)`$", re.MULTILINE)


def render_index(directory: Path = API_DOCS) -> str:
    sections = [
        "# API Reference",
        "",
        (
            "Public API documentation translated from Japanese canonical sources. "
            "Specification links in these pages lead directly to the Japanese Python source modules."
        ),
        "",
        (
            "See the [README](../../README.md), [STATUS](../STATUS.md), and "
            "[Documentation Policy](../DOCUMENTATION_POLICY.md)."
        ),
        "",
        (
            "Usage topics: [Relationship analysis selection]"
            "(public.md#relationship-analysis-selection-analyses) and "
            "[minimal external definition example]"
            "(external.md#minimal-working-example)."
        ),
        "",
    ]
    for filename, heading in (
        ("public.md", "Core Python API"),
        ("external.md", "External Definitions API"),
    ):
        content = (directory / filename).read_text(encoding="utf-8")
        names = API_HEADING.findall(content)
        if not names:
            raise ValueError(f"no API entries in {filename}")
        sections.extend((f"## {heading}", ""))
        for identifier, name in names:
            suffix = re.sub(r"[^a-z0-9_-]", "", name.lower())
            anchor = identifier.lower() + "-" + suffix
            sections.append(f"- [{identifier}: `{name}`]({filename}#{anchor})")
        sections.append("")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="verify the current index without writing"
    )
    args = parser.parse_args()
    expected = render_index()
    path = API_DOCS / "INDEX.md"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            parser.error(
                "API index is outdated: regenerate from the published API pages"
            )
    else:
        path.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
