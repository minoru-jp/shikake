# shikake: Public Python API

Public top-level functions, Models, indexes, inspection results, and their accessors.

Identifiers, parameter declarations, result types, and exception names below follow the Japanese canonical API source.
The specification links lead to the **Japanese Python canonical source**, not to generated specification Markdown.

## Relationship analysis selection (`analyses`)

The `analyses` parameter of `parse_package()` and `inspect_package()` accepts an **iterable of analysis names**. The supported names are `"inheritance"` (base-reference candidates) and `"override"` (same-name method candidates). Omitting the parameter or passing `None` enables both. Selecting `"override"` also enables its prerequisite, `"inheritance"`.

| `analyses` value | Enabled relationship analyses |
| --- | --- |
| `None` (default) | `inheritance`, `override` |
| `{"inheritance"}` | `inheritance` |
| `{"override"}` | `inheritance`, `override` |
| `{"inheritance", "override"}` | `inheritance`, `override` |
| `set()` | None |

An empty iterable disables **relationship analyses only**; name-binding facts (`name_bindings`) are still collected. A bare string such as `"override"` (including `""`) raises `TypeError`, and an unknown name raises `ValueError`. Incomplete Partial results must not be treated as complete relationship information.

## Compiler-level syntax validation (`syntax_validation`)

All four parsing and inspection APIs default to `syntax_validation="compile"`.
After parsing the source into a Python AST, shikake calls `compile(tree, filename, "exec", dont_inherit=True)` to check the current CPython compiler's syntax and scoping restrictions. **The resulting code object is not executed**, and imported modules are not loaded.
This rejects AST-parseable but uncompilable inputs such as a module-level `return`, `break` outside loops, repeated parameter names and duplicate literal keyword arguments. Strict APIs raise `SyntaxError`; Partial APIs return `syntax.invalid`, omitting the entire affected source while preserving independent modules in a package. Compiler-origin `SyntaxError` locations are reported in zero-based UTF-8 byte columns even if the exception has no source-line text.

Select `syntax_validation="ast"` for restricted dialects that intentionally work with AST-parseable sources even when CPython would not compile them:

```python
import shikake

model = shikake.parse_source("return 42", syntax_validation="ast")
```

This only skips CPython compilation checks; it does **not** disable shikake's unsupported-syntax checks, change import permissions or execute source code. Compilation success does not guarantee successful execution, safety, definite assignment or language-specific validity. Compiler warnings are not silenced and CPython's AST compiler has its own depth/resource limits.

Python 3.15 adds `is_lazy` to `ast.Import` / `ast.ImportFrom`. Explicit `lazy import` and `lazy from ... import` are accepted with the usual import Kind and Structure, plus the `lazy` Feature on the import statement (not on individual aliases). The Feature records the **written modifier**, not whether an import is delayed due to runtime settings such as `__lazy_modules__`. Static name-binding dimensions, import restrictions and reference candidate rules remain the same; the timing of module loading, initialization and side effects is out of scope. Python interpreters older than 3.15 cannot parse this syntax. PEP 798 unpacking comprehensions are supported: a starred element in a list, set, or generator comprehension uses the existing comprehension and `starred_expansion` Models; dictionary unpacking uses `model.value.comprehension.dict.unpacking` with `mapping` and `clauses` roles. The ordinary dictionary comprehension Kind and roles remain unchanged. Interpreter-specific verification history, including reviewer-reported tests on stable Python 3.15.1, is maintained in [STATUS](../STATUS.md); unknown future AST changes cannot all be detected automatically.

## Package input extensions (`extensions`) and selection (`include`)

`parse_package()` and `inspect_package()` accept `extensions: tuple[str, ...] = (".py",)` to select regular source file suffixes. `(".dot",)` selects only `.dot` files; `(".py", ".dot")` selects both. Matching uses the exact, case-sensitive `Path.suffix`. Extensions must be distinct, nonempty, single suffixes starting with a dot (not globs or paths); invalid values raise `ValueError` and a non-tuple or non-string member raises `TypeError`. `__init__.dot` is recognized as a package initializer when `.dot` is selected, and colliding module names across suffixes are rejected. This selects **Python AST input files**, not a new grammar or language parser.

`parse_package()` and `inspect_package()` also accept an optional `include(path: Path, is_directory: bool) -> bool` callback. The `path` is an absolute `pathlib.Path` derived from the resolved input root. The boolean is `True` for a subdirectory and `False` for a candidate regular file matching `extensions`.

```python
from pathlib import Path
import shikake

def include(path: Path, is_directory: bool) -> bool:
    return not (is_directory and path.name in {".venv", "venv", "build"})

result = shikake.inspect_package(
    "my_project", extensions=(".py", ".dot"), include=include
)
```

Returning `False` for a directory **prunes its entire subtree before descent**; descendant files are neither visited nor passed to the callback. Returning `False` for a matching file prevents reading and modeling it. The root directory itself is always accepted and is never passed to the callback. Files with other suffixes and symlinks are never passed to it.

Omitting `include` or passing `None` means **accept everything**: hidden directories such as `.venv` are not skipped by default. The callback decides the policy; shikake does not implement glob matching, path exclusion patterns, or automatic warning suppression. Exceptions raised by the callback propagate in both Strict and Partial modes.

Module-name collision checks, composition, relationships, and name-binding analysis use only the selected files. Excluded files are **not** Partial errors or omission diagnostics; `complete=True` means all *selected* input was modeled, not that all files on disk were included. Missing dependencies cannot be assumed absent merely because they were excluded.

See [PARSING.SPEC_002](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_024](../../devdocs/canonical_sources/specification/parsing.py), and [PARSING.SPEC_025](../../devdocs/canonical_sources/specification/parsing.py) for the Japanese canonical rules.

## Caller-selected import restrictions (`import_policy`, `allowed_modules`)

All four parsing/inspection APIs accept `import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted"` and `allowed_modules: tuple[str, ...] = (), syntax_validation: Literal["compile", "ast"] = "compile"`. These are **opt-in restrictions on written Python import statements**, independent of the `extensions` and `include` source selection options.

| Mode | Allowed import syntax |
| --- | --- |
| `"unrestricted"` (default) | Existing behavior: unrelated imports are permitted; registered external structures retain their separate protections. |
| `"registered_interfaces"` | Only explicit `from module import Interface` statements where the fully written interface root is registered in trusted external CallMappings. `import module` is rejected. |
| `"registered_modules"` | `import module`, `import module as alias`, and `from module import name` for modules named in trusted external CallMappings or the additional `allowed_modules` tuple; **also** all explicit registered-interface imports allowed in `registered_interfaces`. |

For example, if the trusted definitions register `dot:Fn.sin`, `registered_interfaces` allows `from dot import Fn` (also `as F`) but rejects `import dot` and `from dot import helper`. `registered_modules` permits all three because `dot` is registered. For a deeper target `pkg:mod.Cls.make`, the structural root is `pkg.mod.Cls` while the declared module is `pkg`: `from pkg.mod import Cls` is permitted by **both** modes, but `from pkg.mod import helper` and `import pkg.mod` are not thereby permitted in `registered_modules`. The name `pkg.mod` is not inferred to be a real submodule. Specify `allowed_modules=("pkg.mod",)` if that entire module is intentionally permitted. For an arbitrary module not modeled as an external structure:

```python
import shikake

result = shikake.inspect_source(
    "import math\nvalue = math.sqrt(4)\n",
    import_policy="registered_modules",
    allowed_modules=("math", "my_company.geometry"),
)
assert result.complete
```

Neither `math` nor `my_company.geometry` needs to be installed. Imports of those modules are **ordinary Python Models**, and their unregistered calls remain ordinary Call Models. The module name match is **exact and case-sensitive**: `import my_company.geometry` and `from my_company.geometry import Vector` match, but `from my_company import geometry` does not. shikake does not resolve imports, check target existence or individual attribute names, infer that different import spellings refer to the same runtime library, or grant submodules implicitly. The caller is responsible for choosing permitted names and managing the runtime environment.

`allowed_modules` may be nonempty **only** in `registered_modules`. It must be a tuple of distinct, syntactically valid, **NFKC-normalized** absolute dotted module names. Non-normalized names are rejected with `ValueError`, not silently rewritten. External `ImportedCall` target identifiers have the same NFKC requirement and must not be Python reserved keywords. Invalid options raise `TypeError` or `ValueError`, even for an empty source/package. Restricted modes reject relative imports (including imports within the analyzed package) and wildcard `from module import *`. The single directive `from __future__ import annotations` is allowed in both restricted modes, without allowing `import __future__` or other future features. For package-local references, write absolute imports and permit their exact module names as appropriate; listing names does not make relative imports valid. A violation raises `ExternalModelingError` in Strict parsing. Partial inspection reports `external.unregistered_import` (`details.path` and `details.policy`) with `model=None` for that source, or omits the offending module from a package. Only the first import-policy violation in lexical source order is reported; exhaustive collection is not promised. Existing registered-interface import location and reserved-name protections still apply. This feature does **not** prevent dynamic importing and is **not a security sandbox**.

See [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py) and [PARSING.SPEC_020](../../devdocs/canonical_sources/specification/parsing.py).

## Python 3.14 template strings

On Python 3.14+, `t"Hello {name!r}"` produces a `model.value.template_string` Model, distinct from an f-string. Each interpolation uses `model.structural_part.template_interpolation`, preserving the expression Model (`value`), its AST source spelling (`expression_text`, optionally `None`), the optional conversion (`s`, `r`, `a`), and the optional format-spec Model. The fragments remain in source order; expressions and conversions are not evaluated.

See [EXPRESSIONS.SPEC_030](../../devdocs/canonical_sources/specification/expressions.py) and [LAYOUTS.SPEC_061](../../devdocs/canonical_sources/specification/layouts.py) for the Japanese canonical contracts.

## API_001: `shikake.parse_source`

**Operation.** Parse one Python source string into a Model using Strict analysis.

- **Inputs:** `source: str, *, filename: str = "<source>", index: KindIndex | None = None, definitions: ModuleType | ExternalDefinitions | None = None, import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted", allowed_modules: tuple[str, ...] = (), syntax_validation: Literal["compile", "ast"] = "compile"`
- **Result:** `Model`
- **Specifications:** [PARSING.SPEC_001](../../devdocs/canonical_sources/specification/parsing.py), [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py)

Unsupported syntax or invalid external definitions raise an exception.

## API_002: `shikake.parse_package`

**Operation.** Parse selected regular Python-syntax source files under a directory using Strict analysis.

- **Inputs:** `directory: str | Path, *, index: KindIndex | None = None, analyses: Iterable[str] | None = None, definitions: ModuleType | ExternalDefinitions | None = None, include: Callable[[Path, bool], bool] | None = None, extensions: tuple[str, ...] = (".py",), import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted", allowed_modules: tuple[str, ...] = (), syntax_validation: Literal["compile", "ast"] = "compile"`
- **Result:** `PackageModel`
- **Specifications:** [PARSING.SPEC_002](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_015](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_016](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_024](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_025](../../devdocs/canonical_sources/specification/parsing.py), [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py)

`analyses` must be `None` or an iterable of analysis names. A bare string (including the empty string) raises `TypeError`; an unknown name raises `ValueError`. See [relationship analysis selection](#relationship-analysis-selection-analyses) for names and dependencies. The `extensions` tuple selects source suffixes, and `include` selects subdirectories and candidate files; see [package input extensions and selection](#package-input-extensions-extensions-and-selection-include). Duplicate names among selected files (including different extensions), invalid input, and Strict failures raise exceptions.

## API_003: `shikake.inspect_source`

**Operation.** Inspect one source string with Partial analysis, returning a Model and diagnostics.

- **Inputs:** `source: str, *, filename: str = "<source>", index: KindIndex | None = None, definitions: ModuleType | ExternalDefinitions | None = None, import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted", allowed_modules: tuple[str, ...] = (), syntax_validation: Literal["compile", "ast"] = "compile"`
- **Result:** `SourceInspection`
- **Specifications:** [PARSING.SPEC_006](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_013](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_022](../../devdocs/canonical_sources/specification/parsing.py), [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py)

Unsupported syntax is reported with diagnostics identifying omitted units.

Partial external errors are recoverable only when confined to a statement: unregistered interface calls, use of protected interfaces as values, or invalid mapped-call arguments. These statements are omitted while modelable sibling statements may be retained. However, missing statements can affect how later retained models are interpreted, including name-binding or definite-assignment checks. Never infer that an assignment absent from a partial Model was absent from the source. File-wide import and reserved-name violations make the source invalid (`model=None`). Strict parsing continues to reject all external violations.

## API_004: `shikake.inspect_package`

**Operation.** Inspect a package with Partial analysis and report incompleteness and diagnostics.

- **Inputs:** `directory: str | Path, *, index: KindIndex | None = None, analyses: Iterable[str] | None = None, definitions: ModuleType | ExternalDefinitions | None = None, include: Callable[[Path, bool], bool] | None = None, extensions: tuple[str, ...] = (".py",), import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted", allowed_modules: tuple[str, ...] = (), syntax_validation: Literal["compile", "ast"] = "compile"`
- **Result:** `PackageInspection`
- **Specifications:** [PARSING.SPEC_006](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_016](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_017](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_018](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_022](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_024](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_025](../../devdocs/canonical_sources/specification/parsing.py), [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py)

`analyses` must be `None` or an iterable of analysis names. A bare string (including the empty string) raises `TypeError`; unknown names raise `ValueError`. See [relationship analysis selection](#relationship-analysis-selection-analyses) and [package input extensions and selection](#package-input-extensions-extensions-and-selection-include). Only files matching `extensions` and accepted by `include` are inspected; excluded files are not diagnostics. Do not treat relation results from an incomplete selected package as complete.

## API_005: `shikake.kind_index`

**Operation.** Obtain the trusted index of built-in Kind, Structure, and Feature definitions.

- **Result:** `KindIndex`
- **Specifications:** [MODEL.SPEC_020](../../devdocs/canonical_sources/specification/model.py)

Cached within the process.

## API_006: `shikake.Model`

**Type.** A public result type holding a syntax element's classification, role-based parts, location, and Features.

- **Result:** `Model`
- **Specifications:** [MODEL.SPEC_001](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_015](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_021](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_022](../../devdocs/canonical_sources/specification/model.py)

Read Models returned by parsing APIs through `kind`, `span`, `features`, `parts()`, and related accessors. Direct user construction is **unsupported**; the internal constructor parameters are not part of the public contract.

**Equality and hashing.** Models use structural equality based on Kind, ordered roles and values, Features, and SourceSpan. A SourceSpan does not include a filename or module identity. Consequently, distinct Models originating from different files may compare equal and collapse into one key in a dictionary or set. Use `is` to compare individual Model instances, or `id(model)` as a temporary identity key while retaining references to those objects. Each Model instance caches its structural hash after the first calculation. Later calls return the cached value without traversing the tree. The initial calculation remains iterative, reuses cached child hashes when available, and caches newly computed hashes on every visited descendant Model. Cache storage does not change the structural equality or hash algorithm.

`repr(model)` is a short, non-recursive diagnostic summary of the Kind, position, Features, and immediate parts. It does not serialize the full tree; use `parts()` and `walk()` to inspect it.

## API_007: `shikake.ModelPart`

**Type.** An immutable role/value pair for a Model part.

- **Inputs:** `role: str, value: PartValue`
- **Result:** `ModelPart`
- **Specifications:** [MODEL.SPEC_005](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_022](../../devdocs/canonical_sources/specification/model.py)

The value may be a Model, a sequence of Models or strings, or a Scalar. `repr(part)` summarizes its immediate value without recursively expanding child Models. Both repr forms are bounded diagnostic displays, not reconstructible Python expressions.

## API_008: `shikake.SourceSpan`

**Type.** Source positions derived from the Python AST.

- **Inputs:** `line: int, column: int, end_line: int, end_column: int`
- **Result:** `SourceSpan`
- **Specifications:** [MODEL.SPEC_019](../../devdocs/canonical_sources/specification/model.py)

Lines are one-based; columns are zero-based UTF-8 byte offsets.

## API_009: `shikake.Kind`

**Type.** A Kind's ID, immediate classification parent, and directly assigned Structure ID.

- **Inputs:** `id: str, parent_id: str | None, structure_id: str | None = None`
- **Result:** `Kind`
- **Specifications:** [MODEL.SPEC_003](../../devdocs/canonical_sources/specification/model.py)

Kind classification inheritance does **not** imply inheritance of roles or shapes.

## API_010: `shikake.Structure`

**Type.** A Structure ID with ordered role/shape contracts.

- **Inputs:** `id: str, parts: tuple[PartContract, ...]`
- **Result:** `Structure`
- **Specifications:** [MODEL.SPEC_004](../../devdocs/canonical_sources/specification/model.py)

Each part declares a role and shape.

## API_011: `shikake.KindIndex`

**Type.** A validated index offering queries over Kinds, Structures, and Features.

- **Inputs:** `kinds: tuple[Kind, ...], structures: tuple[Structure, ...] = (), features: tuple[Feature, ...] = ()`
- **Result:** `KindIndex`
- **Specifications:** [MODEL.SPEC_016](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

Do not conflate Kind ancestry with Structure roles.

## API_012: `shikake.PackageModel`

**Type.** A package composition tree together with selected static relationship information.

- **Inputs:** `model: Model, override_candidates: tuple[OverrideCandidate, ...] = (), base_references: tuple[BaseReference, ...] = (), analyses: frozenset[str] = frozenset(), name_bindings: tuple[NameBinding, ...] = ()`
- **Result:** `PackageModel`
- **Specifications:** [RELATIONS.SPEC_003](../../devdocs/canonical_sources/specification/relations.py), [RELATIONS.SPEC_019](../../devdocs/canonical_sources/specification/relations.py)

The Model tree and relationship candidates are independent kinds of information. `repr(package)` is a bounded diagnostic overview of the composition Model, selected analyses, and counts of name bindings, base references, and override candidates. It does not expand individual relationship facts or serialize the package; inspect the public attributes and lookup methods for full details.

## API_013: `shikake.BaseReference`

**Type.** One written base-class expression, its static target candidates, and binding facts.

- **Inputs:** `subject: Model, expression: Model, targets: tuple[Model, ...], binding: BindingState | None, attribute_modified: bool = False`
- **Result:** `BaseReference`
- **Specifications:** [RELATIONS.SPEC_002](../../devdocs/canonical_sources/specification/relations.py)

Discovered candidates do not establish runtime inheritance.

## API_014: `shikake.OverrideCandidate`

**Type.** A possible same-name method override relationship with supporting evidence.

- **Inputs:** `method: Model, base_method: Model, derived_class: Model, base_class: Model, derived_module: str, base_module: str, evidence: Literal["direct_base_and_same_method_name", "ancestor_and_same_method_name"] = "direct_base_and_same_method_name"`
- **Result:** `OverrideCandidate`
- **Specifications:** [RELATIONS.SPEC_012](../../devdocs/canonical_sources/specification/relations.py)

Two evidence values distinguish a direct base from an indirect ancestor. Runtime MRO is not computed.

## API_015: `shikake.BindingState`

**Type.** Three independent dimensions of a name's syntactic introduction, possible rebinding, and possible deletion.

- **Inputs:** `introduction: Literal["stable", "unstable"], may_rebind: bool, may_delete: bool`
- **Result:** `BindingState`

A first ordinary assignment such as `x = 1` gives `BindingState("stable", False, False)`. A second `x = 2` makes `may_rebind=True`. A lone `n += 1` gives `BindingState("unstable", True, False)` because augmented assignment reads an existing binding. A single conditional assignment can be `unstable` with `may_rebind=False`, while writes in loops may repeat. These properties do **not** guarantee definite assignment at any read. For details, see [BINDING.SPEC_002](../../devdocs/canonical_sources/specification/binding.py) and [BINDING.SPEC_003](../../devdocs/canonical_sources/specification/binding.py).
- **Specifications:** [BINDING.SPEC_001](../../devdocs/canonical_sources/specification/binding.py), [BINDING.SPEC_002](../../devdocs/canonical_sources/specification/binding.py), [BINDING.SPEC_003](../../devdocs/canonical_sources/specification/binding.py), [BINDING.SPEC_004](../../devdocs/canonical_sources/specification/binding.py)

These fields describe syntactic binding facts, not whether a name is definitely assigned when read. Definite-assignment checks are outside shikake's scope; consumers needing them must implement checks under their own language restrictions or translation rules.

## API_016: `shikake.NameBinding`

**Type.** A name-binding fact for a particular module and lexical scope.

- **Inputs:** `module: str, scope: Model, name: str, state: BindingState`
- **Result:** `NameBinding`
- **Specifications:** [BINDING.SPEC_014](../../devdocs/canonical_sources/specification/binding.py)

The same spelling in different scopes is not conflated. `state` does not establish definite assignment at any read site.

## API_017: `shikake.SourceInspection`

**Type.** A Partial result with a source Model or diagnostics.

- **Inputs:** `model: Model | None, issues: tuple[InspectionIssue, ...], name_bindings: tuple[NameBinding, ...] = ()`
- **Result:** `SourceInspection`
- **Specifications:** [PARSING.SPEC_006](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_022](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_023](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_029](../../devdocs/canonical_sources/specification/parsing.py)

`complete` depends on both Model presence and an empty diagnostics list. Local external-structure errors may leave a partial Model containing valid sibling statements. Syntax errors and file-wide external violations (such as rebinding reserved names) still produce `model=None`. Do not treat an incomplete Model as a validated whole source. An omitted statement can affect interpretation of retained later models (for example, definite-assignment checks). The absence of a statement or binding in a partial model does not prove its absence in the original source. `name_bindings` contains scope-specific `NameBinding` facts only when the inspection is complete; it is empty for all incomplete results, even when a partial Model exists. The module identity is `<source>`. See [PARSING.SPEC_023](../../devdocs/canonical_sources/specification/parsing.py). `repr(inspection)` summarizes the Model and reports the number of name bindings as `<N items>` instead of expanding them. `issues` remains fully displayed to preserve diagnostic detail. The representation is not a serialization, and its overall length is not bounded when many issues are present.

## API_018: `shikake.PackageInspection`

**Type.** A Partial package-analysis result.

- **Inputs:** `package: PackageModel, issues: tuple[InspectionIssue, ...]`
- **Result:** `PackageInspection`
- **Specifications:** [PARSING.SPEC_009](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_017](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_018](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_029](../../devdocs/canonical_sources/specification/parsing.py)

Also exposes properties forwarding results from `package`. On incomplete analysis, candidates, completed analyses, and name bindings are empty. In `repr(inspection)`, the nested PackageModel summarizes relationship counts instead of expanding facts, while `issues` retains full diagnostics.

## API_019: `shikake.InspectionIssue`

**Type.** An issue category, location, and omitted span from Partial analysis.

- **Inputs:** `category: IssueCategory, filename: str, node_type: str, message: str, line: int | None, column: int | None, skipped_node_type: str | None = None, skipped_span: SourceSpan | None = None, code: str = "diagnostic.unspecified", details: Mapping[str, str | int] = {} (read-only)`
- **Result:** `InspectionIssue`
- **Specifications:** [PARSING.SPEC_011](../../devdocs/canonical_sources/specification/parsing.py)

`skipped_node_type` and `skipped_span` identify the omitted syntax unit.

`code` identifies the issue without parsing the English `message`. The immutable `details` mapping contains only known values such as `target` or `keyword`. Code families include `syntax.invalid`, `syntax.unsupported`, and `external.*`. For the complete external-code list, see [PARSING.SPEC_020](../../devdocs/canonical_sources/specification/parsing.py). These codes do not change when a message is translated. Mapped-call argument errors provide the written call `target`. `external.too_many_positional` includes `expected_count` (mapped arguments) and `actual_count` (explicit positional arguments). `external.starred_positional` reports `*` expansion without estimating its size. `external.unknown_keyword` and `external.argument_mismatch` include `keyword`; `external.keyword_arguments` covers `**` expansion or duplicate keywords and includes the keyword if known. An omitted statement may also affect interpretation of retained later models, so missing bindings in a partial model do not establish missing assignments in the original source. For local external errors (unregistered calls, protected interface values, and mapped-call argument errors), `skipped_node_type` and `skipped_span` identify the omitted statement. File-wide external violations still return `model=None` with no invented skipped span.

## API_020: `shikake.UnsupportedSyntaxError`

**Type.** An exception for AST syntax unsupported by Strict analysis.

- **Inputs:** `node: ast.AST, detail: str | None = None`
- **Result:** `UnsupportedSyntaxError`
- **Specifications:** [PARSING.SPEC_005](../../devdocs/canonical_sources/specification/parsing.py)

Partial analysis instead reports such failures as `InspectionIssue` values.

## API_021: `shikake.ExternalModelingError`

**Type.** An exception for an external-structure usage violation in Strict analysis.

- **Inputs:** `message: str, node: ast.AST, *, code: str = "external.definition_error", details: Mapping[str, str | int] | None = None`
- **Result:** `ExternalModelingError`
- **Specifications:** [EXTERNAL.SPEC_008](../../devdocs/canonical_sources/specification/external.py)

Partial analysis reports an `external_definition` diagnostic.

## API_022: `shikake.Model.parts`

**Operation.** Return ordered role/value parts.

- **Result:** `tuple[ModelPart, ...]`
- **Specifications:** [MODEL.SPEC_007](../../devdocs/canonical_sources/specification/model.py)

## API_023: `shikake.Model.get`

**Operation.** Return the value of a role; an undefined role raises `KeyError`.

- **Inputs:** `role: str`
- **Result:** `PartValue`
- **Specifications:** [MODEL.SPEC_007](../../devdocs/canonical_sources/specification/model.py)

## API_024: `shikake.Model.get_node`

**Operation.** Return a node; missing roles or incompatible shapes raise `KeyError` or `TypeError`.

- **Inputs:** `role: str`
- **Result:** `Model`
- **Specifications:** [MODEL.SPEC_014](../../devdocs/canonical_sources/specification/model.py)

## API_025: `shikake.Model.get_nodes`

**Operation.** Return a tuple of nodes; missing roles or incompatible shapes raise `KeyError` or `TypeError`.

- **Inputs:** `role: str`
- **Result:** `tuple[Model, ...]`
- **Specifications:** [MODEL.SPEC_014](../../devdocs/canonical_sources/specification/model.py)

## API_026: `shikake.Model.get_name`

**Operation.** Return a text value; missing roles or incompatible shapes raise `KeyError` or `TypeError`.

- **Inputs:** `role: str`
- **Result:** `str`
- **Specifications:** [MODEL.SPEC_014](../../devdocs/canonical_sources/specification/model.py)

## API_027: `shikake.Model.walk`

**Operation.** Traverse the Model composition tree depth-first, starting at this Model.

- **Result:** `Iterator[Model]`
- **Specifications:** [MODEL.SPEC_008](../../devdocs/canonical_sources/specification/model.py)

## API_028: `shikake.KindIndex.get`

**Operation.** Get a Kind by ID; an unknown ID raises `KeyError`.

- **Inputs:** `kind_id: str`
- **Result:** `Kind`
- **Specifications:** [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

## API_029: `shikake.KindIndex.parent`

**Operation.** Get a Kind's immediate classification parent.

- **Inputs:** `kind_id: str`
- **Result:** `Kind | None`
- **Specifications:** [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

## API_030: `shikake.KindIndex.is_a`

**Operation.** Check classification ancestry, not Structure inheritance.

- **Inputs:** `kind_id: str, ancestor_id: str`
- **Result:** `bool`
- **Specifications:** [MODEL.SPEC_003](../../devdocs/canonical_sources/specification/model.py)

## API_031: `shikake.KindIndex.structure_of`

**Operation.** Get the Structure directly referenced by a Kind; do not infer a parent Kind's Structure.

- **Inputs:** `kind_id: str`
- **Result:** `Structure | None`
- **Specifications:** [MODEL.SPEC_016](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

## API_032: `shikake.KindIndex.require_structure`

**Operation.** Require a Structure; abstract Kinds without one raise `ValueError`.

- **Inputs:** `kind_id: str`
- **Result:** `Structure`
- **Specifications:** [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

## API_033: `shikake.KindIndex.get_structure`

**Operation.** Get a Structure by ID.

- **Inputs:** `structure_id: str`
- **Result:** `Structure`
- **Specifications:** [MODEL.SPEC_017](../../devdocs/canonical_sources/specification/model.py)

## API_034: `shikake.KindIndex.all_kinds`

**Operation.** Return all registered Kinds.

- **Result:** `tuple[Kind, ...]`
- **Specifications:** [MODEL.SPEC_016](../../devdocs/canonical_sources/specification/model.py)

## API_035: `shikake.KindIndex.all_structures`

**Operation.** Return all registered Structures.

- **Result:** `tuple[Structure, ...]`
- **Specifications:** [MODEL.SPEC_016](../../devdocs/canonical_sources/specification/model.py)

## API_036: `shikake.KindIndex.all_features`

**Operation.** Return all registered Features.

- **Result:** `tuple[Feature, ...]`
- **Specifications:** [MODEL.SPEC_016](../../devdocs/canonical_sources/specification/model.py)

## API_037: `shikake.KindIndex.validate_features`

**Operation.** Validate whether Features are applicable to a Kind.

- **Inputs:** `kind_id: str, features: tuple[str, ...]`
- **Result:** `None`
- **Specifications:** [MODEL.SPEC_018](../../devdocs/canonical_sources/specification/model.py)

## API_038: `shikake.PackageModel.bindings_for`

**Operation.** Find name bindings only within the given Model's lexical scope.

- **Inputs:** `scope: Model, name: str`
- **Result:** `tuple[NameBinding, ...]`
- **Specifications:** [BINDING.SPEC_014](../../devdocs/canonical_sources/specification/binding.py)

The scope must be the same Model object as `NameBinding.scope`, not merely structurally equal. Only matching names are included, in their original order; an unmatched query returns `()`.

## API_039: `shikake.PackageModel.bases_for`

**Operation.** Return the written base expressions of a class in their source order.

- **Inputs:** `class_model: Model`
- **Result:** `tuple[BaseReference, ...]`
- **Specifications:** [RELATIONS.SPEC_003](../../devdocs/canonical_sources/specification/relations.py)

Matches `BaseReference.subject` by Model identity, not structural equality. Results preserve the original relationship order; an unmatched query returns `()`.

## API_040: `shikake.PackageModel.overrides_for`

**Operation.** Return override candidates associated with the same method Model.

- **Inputs:** `method: Model`
- **Result:** `tuple[OverrideCandidate, ...]`
- **Specifications:** [RELATIONS.SPEC_003](../../devdocs/canonical_sources/specification/relations.py)

Matches `OverrideCandidate.method` by Model identity, not structural equality. Results preserve the original relationship order; an unmatched query returns `()`.

## API_041: `shikake.PackageModel.walk`

**Operation.** Traverse only the PackageModel composition tree.

- **Result:** `Iterator[Model]`
- **Specifications:** [MODEL.SPEC_008](../../devdocs/canonical_sources/specification/model.py), [RELATIONS.SPEC_003](../../devdocs/canonical_sources/specification/relations.py)

## API_042: `shikake.SourceInspection.complete`

**Value.** True when a Model exists and diagnostics are empty.

- **Result:** `bool`
- **Specifications:** [PARSING.SPEC_013](../../devdocs/canonical_sources/specification/parsing.py)

## API_043: `shikake.PackageInspection.complete`

**Value.** True when diagnostics are empty.

- **Result:** `bool`
- **Specifications:** [PARSING.SPEC_013](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_017](../../devdocs/canonical_sources/specification/parsing.py)

## API_044: `shikake.PackageInspection.walk`

**Operation.** Traverse only the composition tree.

- **Result:** `Iterator[Model]`
- **Specifications:** [PARSING.SPEC_006](../../devdocs/canonical_sources/specification/parsing.py)

## API_045: `shikake.Feature`

**Type.** An orthogonal Feature definition independent of Kind classification.

- **Inputs:** `id: str, allowed_kind_ids: tuple[str, ...]`
- **Result:** `Feature`
- **Specifications:** [MODEL.SPEC_006](../../devdocs/canonical_sources/specification/model.py), [MODEL.SPEC_018](../../devdocs/canonical_sources/specification/model.py)

An immutable definition returned by `KindIndex.all_features()`. Built-in Features are `async` for specified asynchronous forms and `lazy` for explicit Python 3.15 import modifiers on `model.import.direct` / `model.import.from`. `lazy` is not attached to `model.import.alias` and does not represent runtime import timing.

## API_046: `shikake.PackageInspection.model`

**Value.** The composition-tree Model from a Partial package result.

- **Result:** `Model`
- **Specifications:** [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py)

Identical to `package.model`.

## API_047: `shikake.PackageInspection.override_candidates`

**Value.** Same-name method candidates found during Partial package analysis.

- **Result:** `tuple[OverrideCandidate, ...]`
- **Specifications:** [PARSING.SPEC_009](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py)

Identical to `package.override_candidates`; empty when the package is incomplete.

## API_048: `shikake.PackageInspection.base_references`

**Value.** Base references found during Partial package analysis.

- **Result:** `tuple[BaseReference, ...]`
- **Specifications:** [PARSING.SPEC_009](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py)

Identical to `package.base_references`; empty when the package is incomplete.

## API_049: `shikake.PackageInspection.analyses`

**Value.** Types of relationship analysis completed during Partial package analysis.

- **Result:** `frozenset[str]`
- **Specifications:** [PARSING.SPEC_016](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py)

Identical to `package.analyses`; empty when the package is incomplete.

## API_050: `shikake.PackageInspection.name_bindings`

**Value.** Name-binding facts by lexical scope from Partial package analysis.

- **Result:** `tuple[NameBinding, ...]`
- **Specifications:** [PARSING.SPEC_017](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_019](../../devdocs/canonical_sources/specification/parsing.py)

Identical to `package.name_bindings`; empty when the package is incomplete.

## API_051: `shikake.Model.get_scalar`

**Operation.** Retrieve an immediate scalar without conversion.

- **Inputs:** `role: str, expected_type: type[T] | None = None`
- **Result:** `Scalar | T`
- **Specification:** [MODEL.SPEC_023](../../devdocs/canonical_sources/specification/model.py)

An unknown role raises `KeyError`, and a non-scalar role or a mismatched exact type raises `TypeError`. `bool` is not accepted as `int`; `None` and `Ellipsis` are valid scalars. For absent optional parts, use `get(role)` and the declared Structure contract.

## API_052: `shikake.utf8_byte_column_to_character_column`

**Operation.** Convert an AST-style zero-based UTF-8 byte column to a zero-based Unicode character column in a decoded source line.

- **Inputs:** `line: str, column: int`
- **Result:** `int`
- **Specification:** [PARSING.SPEC_021](../../devdocs/canonical_sources/specification/parsing.py)

Negative, out-of-range, or mid-character offsets raise `ValueError`. The conversion does not calculate terminal display width or change positions stored in Models or diagnostics.

## API_053: `shikake.format_model_tree`

**Operation.** Format a Model composition tree for diagnostics without recursion.

- **Inputs:** `model: Model, *, max_depth: int = 8, max_nodes: int = 200, max_chars: int = 12000`
- **Result:** `str`
- **Specifications:** [MODEL.SPEC_024](../../devdocs/canonical_sources/specification/model.py)

The root has depth zero and counts as one node. The display includes Kind IDs, part roles, compact scalar values, available spans, and Features. It elides children beyond configured bounds and never exceeds `max_chars`. Invalid limits raise `ValueError`. This is not a lossless serialization, and it does not alter `repr(model)`.

```python
import shikake

model = shikake.parse_source("value = 1 + 2")
print(shikake.format_model_tree(model, max_depth=4, max_nodes=30))
```

## API_054: `shikake.SourceInspection.name_bindings`

**Value.** Lexical name-binding facts from a completely modeled single source.

- **Result:** `tuple[NameBinding, ...]`
- **Specifications:** [PARSING.SPEC_023](../../devdocs/canonical_sources/specification/parsing.py)

Only a complete `inspect_source()` result exposes the collected facts. Any incomplete inspection returns an empty tuple, including cases with a partially preserved Model. `parse_source()` continues to return only a Model.

```python
import shikake

inspection = shikake.inspect_source("count = 1\ncount = 2\n")
if inspection.complete:
    for binding in inspection.name_bindings:
        print(binding.name, binding.state.may_rebind)
```

## API_055: `shikake.collect_comments`

**Operation.** Extract comment tokens from a Unicode source string, without parsing or modeling type comments.

- **Input:** `source: str`
- **Result:** `SourceComments`
- **Specifications:** [PARSING.SPEC_030](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_032](../../devdocs/canonical_sources/specification/parsing.py)
- Lexically malformed input may raise `tokenize.TokenError` or `IndentationError`. The collected result is guaranteed only for input parseable by the AST parser of the current Python version; invalid inputs have no cross-version guarantee for errors or extracted comments. CR, LF, and CRLF are normalized to AST-compatible line numbering. For a file with an encoding cookie or BOM, use `tokenize.open(path)` to read text, and pass the same decoded text to both APIs. This does not change `parse_source()` or `inspect_source()` behavior.

```python
import tokenize
import shikake

with tokenize.open("example.py") as file:
    source = file.read()
comments = shikake.collect_comments(source)
model = shikake.parse_source(source)
```

```python
import shikake

source = "# note\nvalue = 1  # type: int\n"
comments = shikake.collect_comments(source)
model = shikake.parse_source(source).get_nodes("body")[0]
if model.span is not None:
    print(comments.above_line(model.span.line))
    print(comments.on_right_of_line(model.span.line))
    print(comments.in_lines(model.span.line, model.span.end_line))
```

### Composing line queries with definitions and assignments

A function or class definition contains a `body` block. Querying the first statement's start line can retrieve comments between the header and that statement **only when the same line has no code before that first statement**. For a one-line body, do not use this recipe. When testing this condition, use `io.StringIO(source, newline=None).readlines()`, not `str.splitlines()`: the latter splits at additional Unicode separators and form feeds that are not AST line breaks. A statement's **end line** can be used for trailing comments, including assignment statements:

```python
import io
import shikake

source = (
    "def f():\n    # function note\n    value = 1  # assignment note\n    return value\n"
    "class C:\n    # class note\n    item = 2  # class assignment note\n"
)
comments = shikake.collect_comments(source)
function, cls = shikake.parse_source(source).get_nodes("body")
for definition in (function, cls):
    first = definition.get("body").get_nodes("statements")[0]
    if first.span is not None:
        # SourceSpan columns are UTF-8 byte offsets.
        lines = io.StringIO(source, newline=None).readlines()
        prefix = lines[first.span.line - 1].encode("utf-8")[: first.span.column]
        if not prefix.strip():
            print(comments.above_line(first.span.line))
        print(comments.on_right_of_line(first.span.end_line))
```

For decorators before a function or class, query above the earliest decorator row (rather than `def`/`class`):

```python
import shikake

source = "# definition note\n\n@decorator\ndef decorated():\n    return 1\n"
comments = shikake.collect_comments(source)
function = shikake.parse_source(source).get_nodes("body")[0]
if function.span is not None:
    lines = [function.span.line]
    lines.extend(d.span.line for d in function.get_nodes("decorators") if d.span is not None)
    print(tuple(comment.text for comment in comments.above_line(min(lines))))
    # ('# definition note',)
```

The same approach applies to other statements with a `SourceSpan`. Use `in_lines()` to examine comments within multiline constructs. An intervening code-containing line blocks `above_line()`; empty lines do not. These calls return comments **at the queried lines**, not comments belonging to a particular definition, variable, or assignment. Multiple statements on one line are not distinguished, and `span=None` cannot supply a line. The caller must provide the source matching the Model.

## API_056: `shikake.Comment`

**Type.** Frozen source comment with `text`, `line`, `column`, and `end_column` attributes.

- `text` includes the leading `#`; `line` is one-based. The columns are zero-based **Unicode character indices**, *not* AST/`SourceSpan` UTF-8 byte offsets. For line-based queries, `Model.span.line` and `end_line` need no column conversion.
- **Specifications:** [PARSING.SPEC_030](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_032](../../devdocs/canonical_sources/specification/parsing.py)

## API_057: `shikake.SourceComments`

**Type.** Frozen token-derived comment collection, separate from the Model tree. Its `repr` summarizes the comment count without expanding all entries. Only `collect_comments()` constructs this result; direct construction and `dataclasses.replace()` are unsupported because its private indexes must remain consistent. Copy and pickle round-trips are supported.

- **Specifications:** [PARSING.SPEC_030](../../devdocs/canonical_sources/specification/parsing.py), [PARSING.SPEC_031](../../devdocs/canonical_sources/specification/parsing.py)

## API_058: `shikake.SourceComments.in_lines`

**Operation.** `in_lines(first: int, last: int) -> tuple[Comment, ...]` returns comments in the inclusive one-based line interval, in source order. An available `Model.span` supplies `line` and `end_line` directly; this does not establish ownership.

## API_059: `shikake.SourceComments.on_right_of_line`

**Operation.** `on_right_of_line(line: int) -> tuple[Comment, ...]` returns the comment on that line only when code precedes it. No representative Model is required, even for punctuation-only lines. Using an assignment statement's `Model.span.end_line` queries its last line, but does not imply the comment belongs to that assignment. `Model.span.line` can also be used.

## API_060: `shikake.SourceComments.above_line`

**Operation.** `above_line(line: int) -> tuple[Comment, ...]` returns comments between the queried line (excluded) and the nearest preceding code-containing line (excluded). Blank lines never block the search. For function and class bodies, the first body statement's `Model.span.line` can be used to search above that statement, but only if its source line has no code before the statement. This does not apply when the header and body share a line. For decorated definitions, use the earliest decorator start line to search above the definition; its own `def`/`class` line will be blocked by decorator code. No ownership or semantic relevance is inferred.

## API_061: `shikake.SourceComments.module_header`

**Operation.** `module_header() -> tuple[Comment, ...]` returns comments before the first code-containing line.

## API_062: `shikake.SourceComments.module_footer`

**Operation.** `module_footer() -> tuple[Comment, ...]` returns comments after the last code-containing line.

A file containing comments but no code returns all of its comments for **both** header and footer queries. On lines containing code, trailing comments are obtained through `on_right_of_line` rather than header/footer.

## API_063: `shikake.SourceComments.comments`

**Value.** A `tuple[Comment, ...]` containing all comments in source order. Type-comment text is included without interpretation. A `SourceComments` object is the result of the explicit `collect_comments()` call. There is no separate Model-origin or package-wide comment query. Instead, callers use `Model.span` line numbers with the existing queries and collect comments separately for each source. A module root or other Model can have `span=None`; Models sharing a line give the same line-query results. The library neither checks that the Model and comments came from the same source nor infers comment ownership.

**Input validation:** Line numbers must be non-boolean integers >= 1. Invalid types raise `TypeError`; non-positive lines or reversed ranges raise `ValueError`. `collect_comments()` requires a Unicode `str`, not bytes. The comment query API does not change the behavior of any existing AST-based modeling entry point.
