# shikake: Documentation policy

This policy defines how canonical sources, temporary renders, and published documents are managed. Individual API and modeling contracts remain governed by their canonical specification and API sources, not by this policy.

## Sources of authority

The **Japanese canonical sources** under `devdocs/canonical_sources/` are the sole editable sources for managed documentation.

Published English Markdown is a translated, reviewed deliverable derived from temporary Japanese renders. It is not a separate normative source and must not be edited independently to change a contract.

## Publication scope and locations

Five kinds of documents are published in English:

- `README.md`: purpose, concepts, installation, and introductory usage, at the repository root.
- `CHANGELOG.md`: dated, versioned user-facing release history, at the repository root.
- `docs/STATUS.md`: development status and known limitations.
- `docs/api_reference/`: public API contracts and index.
- `docs/DOCUMENTATION_POLICY.md`: this policy.

`LICENSE` remains at the repository root. Detailed specifications, the modeling policy, and development history remain as Japanese canonical source files. The Japanese `changelog/canonical.py` is normative for the English root `CHANGELOG.md`. The v0.0.1 entry records the initial release under the date October 23, 2026. Essential API guarantees and limitations must still be stated concisely in the public English API Reference.

## Temporary rendering of Japanese documents

Use `devdocs/generate.py` to render Japanese canonical documents only when necessary, then discard them after review and translation. Do not create or retain `devdocs/canonical_documents/`.

When a downstream workflow needs temporary output, use `-o` with a **temporary directory outside the repository**. The calling workflow must delete that directory when finished, including on failure. Generated Japanese documents are not version-controlled.

## Changes, translation, and verification

Edit the relevant Japanese canonical source first, then verify source references and tests. Translate only the documents in the publication scope, manually reviewing technical meaning, API identifiers, values, exceptions, and constraints against the source. Do not attempt to guarantee agreement between the canonical source and English translations using automated content-matching tests. Correct discrepancies against the canonical source as they are discovered. Canonical-source validation, temporary rendering, published link checks, and runnable usage-example checks remain separate.

Requested changes to public English text must also be made at the canonical source, then translated again. Preserve historical entries and append new development decisions instead of rewriting history. Source validation and publication updates are separate steps; do not publish an outdated translation.

## Links between published documents and specifications

Keep README concise and point primarily to `docs/api_reference/` for contract details. API Reference pages should link applicable rule IDs, such as `MODEL.SPEC_005`, **directly to their Python canonical source modules** under `devdocs/canonical_sources/specification/`.

Use repository-relative links between documents when viewed on GitHub. Avoid hard-coded source line numbers because they drift. For the root README shown on PyPI, use absolute links rooted at `https://github.com/minoru-jp/shikake/blob/HEAD/` so they follow the repository default branch. Verify that the repository and linked files are reachable before publishing.

Do not link to nonexistent English specification Markdown; link directly to the Japanese Python sources when details are needed.

## Distribution and release checks

The source distribution (sdist) includes `devdocs/`, with canonical sources and generation scripts, while excluding `devdocs/canonical_documents/`. Public English Markdown is located in the root README and CHANGELOG and under `docs/`; these files should be included in the source distribution.

Before release, verify document layout, link targets, correspondence with canonical sources through manual review (not automated translation-matching tests), and both inclusion and exclusion rules in the sdist.
