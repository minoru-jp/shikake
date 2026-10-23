# shikake changelog

This changelog summarizes user-facing changes by release. Design decisions and development history remain in Japanese canonical sources: [pre-release history](devdocs/canonical_sources/development_history/pre_release.py) and [performance refactoring history](devdocs/canonical_sources/development_history/performance.py).

## 0.0.1 - 2026-10-23

**Initial Alpha release.** The public API may change incompatibly in subsequent versions.

### Added

- **AST-based modeling:** Kinds, Structures, Features, and role-based Models. Strict `parse_source()` / `parse_package()` and diagnostic Partial `inspect_source()` / `inspect_package()` APIs, plus bounded `format_model_tree()` output.
- **Input selection:** `extensions` and the `include` callback select files and directories for package analysis. Custom suffixes are permitted; their contents must still be parseable as Python AST. Regular `.py` files are the default.
- **Syntax validation:** Non-executing CPython compilation checks by default; `syntax_validation="ast"` skips the additional compilation check.
- **External definitions:** Trusted Shikumi declarations or `ExternalDefinitionsBuilder` can define external Kinds, Structures, and call mappings.
- **Import permissions:** Three `import_policy` modes and arbitrary absolute module names in `allowed_modules`, without runtime import resolution or sandbox guarantees.
- **Static information:** Base-class reference and override candidates, scoped `name_bindings`, and three binding dimensions. Neither definite assignment nor runtime name resolution is guaranteed.

### Python syntax support

- Models Python 3.12 `type` statements and generics, Python 3.13 type-parameter defaults, Python 3.14 t-strings and multiple-exception syntax, and Python 3.15 PEP 798 unpacking comprehensions.
- Dictionary-unpacking comprehensions use `model.value.comprehension.dict.unpacking`.
- Explicit Python 3.15 `lazy import` and `lazy from ... import` use the ordinary import Kinds and Structures with a `lazy` Feature on the import statement. Binding dimensions and static reference rules are unchanged; runtime lazy loading is not modeled.
- Python 3.13-and-earlier baseline rules and 3.14+ overlays are internal. No public model-version selection API is provided.

### Performance improvements

- **Structural Model hashes:** Model instances lazily cache their structural hashes. Hashing a parent also caches computed hashes for its descendants, reducing repeated traversal when those Models are subsequently reused. Structural equality, hash computation rules, and iterative traversal are preserved.
- **Relationship lookups:** `PackageModel.bindings_for()`, `bases_for()`, and `overrides_for()` use internal identity-based indexes rather than scanning every relationship on each call. Result contents, order, and the public API are unchanged.
- These internal optimizations trade some Model initialization, indexing, and hash-caching time and memory for faster repeated operations.

### Diagnostics and developer tooling

- **PackageModel diagnostics:** `repr(package)` provides a bounded summary of the composition Model, selected analyses, and counts of bindings, base references, and override candidates, without expanding each relationship fact. Use attributes and lookup methods for full information.
- **SourceInspection diagnostics:** `repr(inspection)` summarizes the Model and displays a name-binding count rather than expanding every binding. Both inspection result types keep complete `issues` content in their representations.
- **Documentation generator tests:** Expected argparse errors are captured and asserted in invalid-input tests, keeping test output clean. CLI error messages are unchanged.

### Publication and compatibility notes

- The distribution and public import name is **`shikake`**. No compatibility import under the former development name `kangen` is provided.
- The Japanese canonical sources are authoritative. See the [API Reference](docs/api_reference/INDEX.md) and [Status](docs/STATUS.md) for the current contracts, limitations, and separately recorded interpreter test evidence.
- Consult the actual PyPI distribution or GitHub release for downloadable artifacts and publication status.
