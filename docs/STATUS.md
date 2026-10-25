# Development status

**shikake 0.0.5 (released October 25, 2026).**

This page describes the current implementation, its boundaries, and verification evidence. See [CHANGELOG](../CHANGELOG.md) for versioned changes.

## Implemented functionality

- Python 3.11+ syntax is modeled with standard-library `ast` into role-based Models using Kind, Structure, and Feature. Source code and its imports are never executed. The separate `collect_comments()` API uses standard-library `tokenize`. Runtime dependency: `shikumi>=0.2.4,<2.0.0`.
- Strict entry points are `parse_source()` and `parse_package()`; inspection entry points are `inspect_source()` and `inspect_package()`. The default `syntax_validation="compile"` runs non-executing CPython compile checks after parsing; `"ast"` skips only those extra checks. Python warnings follow the host's `warnings` configuration: shikake neither catches them nor turns them into inspection diagnostics. Warnings promoted to syntax errors follow the ordinary syntax-error path.
- Package input uses regular `.py` files by default, with `extensions` and `include(path, is_directory)` controlling selection. Descendant symlinks are not followed. Runtime imports and dynamic name resolution are not performed.
- Consumers may explicitly create a frozen `ModelRef(model, source_path)` for identity-aware dictionary/set keys. It compares the Model by `is` and the normalized `Path` by equality. It does not resolve paths or verify file existence and does not change parsing results or Model structural equality.
- `definition_index()` and an external schema's `definitions.index` separately query Kind classification (`classified_under`), declared roles (`defines_role`), and Feature applicability (`allows_feature`). These queries describe definitions, not values actually held by a Model.
- Models expose `parts()`, `get()`, `get_scalar()`, and `walk()`, with `format_model_tree()` for diagnostic display. Optional analyses produce static base references and override candidates. Relationship queries use Model identity.
- `BindingState` has four fields: `introduction` (`stable`, `unstable`, `builtin`, `external`), `may_rebind`, `may_delete`, and `may_value_use`. These are lightweight observations, not comprehensive static-analysis guarantees. A `False` value does **not** prove that an operation never occurs. Standard built-in names are modeled as virtual introductions at module start.
- Trusted Shikumi declarations or `ExternalDefinitionsBuilder` can register Call, Type, and Generic interfaces and Features. Explicitly imported names matching a registered syntax form become dedicated Models. Mapping-declared Features can be explicitly attached to these Models; merely defining a Feature does not attach it. Unsupported shapes and unregistered uses fall back to ordinary Models. Value references, rebinding, and deletion of external identifiers are not rejected by shikake's own usage rules; definite lexical shadowing prevents specialized recognition.
- An optional `ImportPolicy(default, allow, deny, allow_star_import=False)` delegates AST import checks to shikake. `deny` wins. Module entries match the named module and descendant modules in both allow and deny rules. For `from M import N`, deny also checks `M.N`. A `M:N` member entry matches exactly. Without a policy, imports are not restricted and star-import syntax is modeled.
- Star imports are preserved as syntax Models but their implicit name introductions or possible conflicts are **not** inferred for binding facts, built-in Collection recognition, or inheritance candidates. Explicit named imports keep the existing binding behavior.
- A function or method containing its own `yield`/`yield from` retains the ordinary function/method Kind and Structure, with a `generator` Feature. Built-in Features are `async`, `generator`, and `lazy`; externally defined Features can also be registered.
- Depending on the running Python interpreter, supported newer syntax includes Python 3.12 type parameters, 3.13 type-parameter defaults, 3.14 template strings, and 3.15 PEP 798 unpacking comprehensions and explicit lazy imports. See the [LAYOUTS canonical source](../devdocs/canonical_sources/specification/layouts.py) for the complete Kind/Structure catalog.

## Known limitations

- shikake does not execute source, resolve runtime names, infer types, check definite assignment or type compatibility, or generate target-language code. Binding facts and inheritance candidates are not proofs; the consumer decides how to use and validate them.
- Import targets and `__all__` are not evaluated, and relative import targets are not resolved. ImportPolicy checks written AST imports; it cannot restrict dynamic imports or property access and is **not** a security sandbox.
- External interfaces require compatible registered syntax and explicit imports. Argument mismatches, unregistered operations, and clear local shadowing retain ordinary Models. Dynamic aliases and arbitrary method receivers are not resolved.
- Iterative processing and shared expression context improve handling of deep expressions, but CPython parser/compiler depth and resource limits remain, and arbitrary-depth modeling is not guaranteed.
- A Partial result with `complete=False` is not a complete model; incomplete package results skip relationship analysis. Warning messages are not inspection issues; hosts that need them should use Python's `warnings` facilities.

## Verification

- The updated v0.0.5 suite contains 702 tests. On Python 3.13.5, local checks finished with 689 passed, 13 skipped, no failures; Ruff check/format and BasedPyright passed.
- The stage9 development build on Python 3.13.5 ran 668 tests: 655 passed, 13 skipped, no failures. Ruff check/format and BasedPyright reported no errors.
- An independent reviewer reported that the preceding stage8 passed all 660 tests on Python 3.11–3.15 and free-threaded Python 3.14, with 95% branch coverage. Of 9,892 real-world files, 9,891 were modeled completely and no crashes occurred. Those logs have not been independently reverified in this workspace.
- For the updated v0.0.5 suite, checks are recorded as having completed without failures on Python 3.11, 3.12, 3.13, 3.14, free-threaded 3.14, and 3.15b4 (six environments). Skip counts can vary by interpreter; the cross-version execution logs were not independently inspected in this workspace.

## Distribution

- Version 0.0.5 is documented as released. Public English documents are the root `README.md` and `CHANGELOG.md`, `docs/STATUS.md`, `docs/api_reference/`, and `docs/DOCUMENTATION_POLICY.md`; the authoritative Japanese sources are under `devdocs/canonical_sources/`.
- The CI matrix covers Python 3.11–3.15. PyPI and GitHub Release uploads use separate manually triggered workflows.
