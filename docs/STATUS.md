# shikake development status

shikake `0.0.1` is the initial Alpha release. This status describes implemented functionality, limitations, and test evidence. See the [Changelog](../CHANGELOG.md) for the v0.0.1 changes.

## Implemented functionality

- The distribution and public import name are `shikake`. Internal code resides in `shikake._mica`; no top-level `mica` package is distributed. The runtime Shikumi dependency is `>=0.2.4,<2.0.0`.
- Source strings and local Python source trees, including directories without `__init__.py`, are read using the AST to produce Kinds, Structures, Features, and role-based Models. By default all regular `.py` files in a designated tree are considered; `extensions` selects other or additional suffixes, while `include(path, is_directory)` prunes subdirectories and filters matching files. No directories are excluded by default; child symlinks are not followed. Module-name conflicts are checked after selection, and Partial completeness applies to selected inputs. All selected files are parsed as Python AST regardless of suffix. The `filename` argument of `parse_source()` can identify syntax errors.
- All four analysis APIs default to `syntax_validation="compile"` for AST parsing plus non-executing CPython compilation checks, and accept `"ast"` to skip the compilation check for restricted dialects. Compilation does not guarantee runtime validity. Python 3.15 PEP 798 unpacking comprehensions are modeled, including a distinct dictionary-unpacking Kind and Structure; explicit lazy imports use the usual import Kinds and Structures with the `lazy` Feature on the statement. Runtime import timing is not modeled.
- Strict APIs: `parse_source()` and `parse_package()`. Partial APIs with diagnostics: `inspect_source()` and `inspect_package()`. All four accept an optional `import_policy`: `unrestricted` (default), `registered_interfaces` (explicit registered interface imports only), or `registered_modules` (registered external modules plus caller-specified absolute `allowed_modules` names). Restricted modes reject relative and star imports, but allow the single `from __future__ import annotations` directive. Explicit registered-interface imports are valid in both restricted modes. Import targets are never resolved or executed, and this is not a security sandbox.
- Models expose `parts()`, `get(role)`, `get_scalar()`, and `walk()`; `format_model_tree()` provides a bounded diagnostic tree display. The `analyses` option selects inheritance and override candidate analyses. Known single- and multiple-inheritance graphs can yield same-name method candidates without ranking them, and each written base expression has a `BaseReference`. A shared AST fact index collects declarations and binding events per scope, including nested classes.
- Trusted Shikumi definitions or an `ExternalDefinitions` object built with `ExternalDefinitionsBuilder`, supplied through `definitions=`, can register custom Kinds and Structures for explicitly imported external interface calls. Registered external structures and their child attributes cannot be used as values outside permitted direct-call forms; indexing or similar operations on a **call result** retain ordinary Models. `shikake.external` exposes both the Shikumi declaration API and a programmatic builder. No dynamic resolution or execution is performed.
- Internally, Python 3.13-and-earlier baseline modeling rules are refined by Python 3.14 and 3.15 rules, without user-selectable model-version modes or version labels in Models. The parser models Python 3.12 `type` statements and generic declarations, Python 3.13 type-parameter defaults, and Python 3.14 t-strings (`TemplateStr` / `Interpolation`). Python 3.14 unparenthesized multiple-exception handlers reuse the existing exception-handling Model. Interpreter-specific test results are recorded in the verification section below. CI targets Python 3.11–3.15. The built-in catalog has 143 Kinds, 61 Structures, and 2 Features. See the [LAYOUTS specification source](../devdocs/canonical_sources/specification/layouts.py) for the catalog.

## Base references and three binding dimensions

- `PackageModel.base_references` and `bases_for(class_model)` provide a `BaseReference(subject, expression, targets, binding, attribute_modified)` for each written base expression. `targets` are discovered class candidates; `binding` is the root name's `BindingState(introduction, may_rebind, may_delete)` or `None`; `attribute_modified` indicates explicit attribute modification within the same module.
- `PackageModel.name_bindings` and `bindings_for(scope, name)` expose name-binding facts per lexical scope, even when `analyses=set()`. Complete single-source `inspect_source()` results also expose `SourceInspection.name_bindings`; incomplete Partial results expose no binding facts. These are not Features; explicit `lazy` does not change their evaluation rules or static reference candidates. They distinguish initial syntactic introduction, subsequent or repeatable writes, and deletions without deciding execution order, branch outcomes, or definite assignment at a read.
- There is no global certainty status for an inheritance graph. Base-reference facts and override candidates are reported separately; consumers decide what to do with candidates. The AST fact collector is shared with external-structure validation.

## Internal performance behavior

- Each Model instance lazily caches its structural hash. Hashing a parent Model also caches the hashes calculated for its descendants, avoiding repeated traversal when those descendants are queried later. Structural equality, hash computation rules, and iterative traversal are unchanged.
- `PackageModel.bindings_for()`, `bases_for()`, and `overrides_for()` use internal indexes built when the PackageModel is created. Keys rely on Model object identity, not structural hashes; result contents, order, and the empty-tuple behavior are preserved.
- These optimizations introduce no public API. They incur some Model initialization and first-hash caching costs, and PackageModel indexing requires additional construction time and memory.
- `repr(package)` provides a bounded diagnostic summary of the composition Model, selected analyses, and relationship counts without expanding the relationship facts. Full information remains available through attributes and lookup methods.
- `repr(source_inspection)` displays the Model summary and name-binding count without expanding each binding. Both inspection result types retain full `issues` in their representations, so a large collection of diagnostics can still produce a long string.

## Python version verification

- **Python 3.13.5, development environment:** 539 passed and 9 skipped out of 548 tests.
- **Python 3.14.6, reviewer environment:** successful 548-test suite reported.
- **Python 3.15.0b4, reviewer environment:** successful 548-test suite reported.
- **Python 3.15.1, reviewer environment:** successful 548-test suite reported (the stable Python 3.15.1 release is dated October 21, 2026).
- **Post-refactor Python 3.13.5, development environment:** 552 passed and 9 skipped out of 561 tests.
- **v0.0.1 diagnostic and test-output refinements, Python 3.13.5:** 554 passed and 9 skipped out of 563 tests, verified in the development environment. That earlier change was not independently retested on other Python versions here.
- **v0.0.1 SourceInspection repr refinement, Python 3.13.5:** 557 passed and 9 skipped out of 566 tests, verified in the development environment. Cross-version verification of this additional change is not recorded here.
- **v0.0.1 explicit lazy Feature, Python 3.13.5:** 570 tests run, 560 passed, 10 skipped, including AST-flag simulation tests. Native Python 3.15 lazy syntax integration tests could not run in this Python 3.13.5 environment; the separate reviewer result is recorded below.
- **v0.0.1 explicit lazy Feature, Python 3.15.0b4, reviewer environment:** all 570 tests passed, with 0 skipped, including native Python 3.15 lazy import syntax tests. This result was reported by the reviewer; execution logs were not independently reviewed here.
- **Post-performance-refactor, other target Python versions:** the developer reports that tests passed separately across the target Python versions. Counts and skip totals for those earlier cross-version runs remain unspecified, and logs have not been independently reviewed here.

The earlier 548-test results predate the performance refactor. Skip counts were not provided for the earlier reviewer-run 548-test suites; the latest reported Python 3.15.0b4 570-test run had 0 skips. External reports are separate from GitHub Actions CI results. The CI matrix targets Python 3.11–3.15; earlier verification also covered Python 3.11–3.13.

## Release automation

- Ordinary pushes and pull requests run checks through `.github/workflows/ci.yml`; they do **not** publish to PyPI. Start `.github/workflows/release.yml` manually using **Actions → Release to PyPI → Run workflow** on the default branch.
- The release workflow checks Python 3.11–3.15 and the extracted sdist, builds and verifies the distributions, then publishes to PyPI using Trusted Publishing with the `pypi` GitHub Environment. **Only after successful PyPI publication** does it create a `v<project.version>` Git tag (initially `v0.0.1`) on the published commit and a GitHub Release with the built distributions.
- A new release run refuses to republish an already tagged version. If tagging or GitHub Release creation fails after publication, select **Re-run failed jobs** on the *same workflow run*, not **Re-run all jobs**, to avoid uploading the same version to PyPI again. If the PyPI upload outcome is uncertain, check PyPI before retrying.
- Configure a matching PyPI Trusted Publisher for this GitHub repository, workflow file `release.yml`, and GitHub Environment `pypi` (a pending publisher may be used for the first publication). This describes the configured workflow, **not** proof that an actual release has completed.

## Known limitations and issues

- `shikake.Model` is a public **result type**, intended to be read from supported parsing APIs. Direct `Model(...)` construction is unsupported; validity of user-created Models and the behavior of other APIs receiving them are not guaranteed. Kind/Structure/Feature consistency guarantees apply to Models produced through the library's normal parsing paths.
- Strict analysis rejects unsupported syntax with `UnsupportedSyntaxError`. Partial analysis can report available results, but `complete=False` means the result is incomplete. Local external-call errors may omit a statement while retaining later Models, so the omission may also affect how those later Models can be interpreted. On an incomplete package, Partial analysis does not produce base references, override candidates, or name-binding relations.
- The standard Python AST parser imposes depth limits. Several Model construction, traversal, equality, hashing, binding, and method-search paths are iterative, but arbitrarily deep or unbounded analysis is not promised. Partial analysis does not convert `RecursionError` into a diagnostic.
- No automatic discovery of external packages or `.pyi` files is provided. Registered external-call matching requires explicit top-level imports and does not support directly imported free functions. It rejects ambiguous rebinding or unsupported argument forms. Instance-level type inference is not performed. Static base-class candidates are not runtime identity proofs and may not cover runtime-dependent targets. Multiple written bases and candidates can be represented, but runtime MRO, precedence, and generic-base resolution are not computed. The absence of a static candidate does not prove its runtime absence.
- Source code is never executed. Value evaluation, type inference, dynamic name resolution, and code translation are out of scope.

## Planned development

- Continue evaluating which additional syntax to support based on consumer needs.
- Consider reference matching using explicitly supplied external `.py` / `.pyi` files and improved Partial diagnostics.
- Continue reviewing public API contracts, verifying examples, and checking release procedures.
