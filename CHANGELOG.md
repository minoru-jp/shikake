# shikake changelog

This changelog summarizes user-facing changes by release. The 0.0.3 entry is prepared for publication; it does not itself confirm a PyPI upload or GitHub Release. Design decisions and development history remain in Japanese canonical sources: [pre-release history](devdocs/canonical_sources/development_history/pre_release.py), [performance refactoring history](devdocs/canonical_sources/development_history/performance.py), [comment-position history](devdocs/canonical_sources/development_history/comments.py), and [built-in binding history](devdocs/canonical_sources/development_history/builtins.py).

## 0.0.3 - 2026-10-24

### Added

- **Implicit built-in bindings:** Standard built-in names, fixed for each Python minor version, are evaluated with the existing three binding dimensions as virtual module-level initial introductions: `BindingState(introduction="builtin", may_rebind=False, may_delete=False)`. Module-level writes and deletions, and possible wildcard-import conflicts, affect `may_rebind` and `may_delete` as usual; same-named local bindings remain separate. The inventory does not depend on `site` additions or on changes to `builtins` in the running process.
- **On-demand binding queries:** `PackageModel.bindings_for(module, name)` and a complete `SourceInspection.bindings_for(module, name)` also return the implicit introduction of a built-in name that has no explicit write. Read-only built-in names are not eagerly expanded into `name_bindings`, and no implicit facts are produced for incomplete Partial results, including queries through `PackageInspection.package`. Runtime referents and types are not determined.
- **Lexical scope discriminator:** Library-generated `NameBinding` values carry `scope_kind` (`module`, `class`, `function`, or `annotation`). Manually constructed records may omit it, in which case it is `None`.

### Changed (including breaking Model and binding-fact changes)

- **Generalized Collection Kinds:** Value collections now have three concrete Kinds (`model.value.collection.sequence`, `.mapping`, and `.set`) sharing the `collection_construction` Structure (`construction`, `immutable`, and `inputs`). The former `.list`, `.tuple`, and `.dict` Kinds and their collection-specific roles are no longer emitted. `inputs` holds direct elements or dictionary entries for `literal`, the written argument Models for `builtin`, and exactly one original comprehension Model for `comprehension`. No Features are added.
- **Conservative built-in constructor recognition:** Calls to `list`, `tuple`, `dict`, `set`, `frozenset`, and, on Python 3.15 and later, `frozendict` become Collection Models only when no same-named write, deletion, or wildcard import appears in a visible scope and the written argument shape is supported. `list`/`tuple`/`set`/`frozenset` accept 0–1 positional arguments with no keyword or `*` arguments; `dict`/`frozendict` accept 0–1 positional arguments plus keyword arguments (including `**`) with no `*` argument. Visibility of PEP 695 type parameters and of annotation scopes directly inside a class follows Python's lexical rules. Other calls remain ordinary `model.value.call` Models; runtime referents and element contents are never inferred.
- **Comprehensions and targets:** List, set, and dict comprehensions become Collection Models whose sole `inputs` child is the original comprehension Model; generator expressions are unchanged. List/tuple destructuring targets are represented by `model.structural_part.sequence_target` with `spelling` and `elements` roles instead of collection value Kinds. The `async` and `lazy` Features are unchanged.
- **Effects on existing binding facts:** A module-level write or definition that reuses a built-in name (for example `def open(...)`) changes from `BindingState("stable", False, False)` in 0.0.2 to `BindingState("builtin", True, False)`. `BaseReference.binding` for a base written as a built-in name (for example `class AppError(Exception)`) changes from `None` to `BindingState("builtin", False, False)`. `BindingState.introduction` gains the value `"builtin"`.
- **Type-parameter bindings:** PEP 695 type parameters are now bindings of an annotation scope separate from the definition body. A generic definition's type parameter and a same-named body binding are no longer merged into one record; the same definition Model returns two records with different `scope_kind` values. Type-alias type parameters are also reported as bindings.

## 0.0.2 - 2026-10-24

### Added

- **Independent comment facts:** `collect_comments(source)` uses `tokenize` to return immutable `Comment` records in a `SourceComments` result, without adding comments to structural Models.
- **Line queries:** `in_lines(first, last)`, `on_right_of_line(line)`, `above_line(line)`, `module_header()`, and `module_footer()` locate comments by written position. Empty lines do not block upward searches, but code-containing lines do.
- **Type comments remain uninterpreted:** `# type: ...` and `# type: ignore` are collected as raw comments. Existing AST parsing continues with `type_comments=False`.
- **Composition with Model locations:** Callers can pass the existing `Model.span` start/end line numbers to the line-query APIs. The first body statement's start line supports querying comments beneath a function/class header; an assignment statement's end line supports querying a trailing comment. No dedicated Model-to-comment lookup or semantic association is introduced. Package-wide comment collection is not provided.

### Fixed

- Normalize CR, LF, and CRLF for comment line positions consistent with AST parsing.
- Keep `SourceComments` internal indexes consistent by restricting construction to `collect_comments()`; document decorator, same-line body, malformed input, and BOM edge cases.

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
