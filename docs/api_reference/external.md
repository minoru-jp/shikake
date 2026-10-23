# shikake: External Definitions API

Declarations and call-mapping APIs provided by `shikake.external`. External descriptions must be trusted.

Identifiers, parameter declarations, result types, and exception names below follow the Japanese canonical API source.
The specification links lead to the **Japanese Python canonical source**, not to generated specification Markdown.

## Import permissions for restricted source dialects

An external CallMapping enables dedicated modeling for a specific call, but does not by itself prohibit unrelated imports. All four parsing/inspection APIs accept `import_policy`: `"unrestricted"` (default), `"registered_interfaces"` (only explicit imports of mapped structural roots), or `"registered_modules"` (all imports from modules named in trusted mappings, plus optional caller-defined `allowed_modules=("math", "custom_tools")`, **and** all explicit registered-interface imports). Names are compared literally, not resolved against the runtime environment. Permitting a module does not register every function in it as an external call. For a nested mapping `pkg:mod.Cls.make`, the declared module is `pkg` and the registered structural root is `pkg.mod.Cls`. Thus `from pkg.mod import Cls` is accepted in both restrictive modes without granting all imports from `pkg.mod`. The isolated directive `from __future__ import annotations` is also accepted. `allowed_modules` must contain NFKC-normalized module names, and `ImportedCall` target identifiers must likewise be normalized. Restricted modes reject relative and wildcard imports; existing registered-interface protections still apply. This is not a security sandbox. See [the import-policy API contract](public.md#caller-selected-import-restrictions-import_policy-allowed_modules) and [EXTERNAL.SPEC_013](../../devdocs/canonical_sources/specification/external.py).

## Minimal working example

A trusted Python declaration module defines a Structure, a Kind, and a mapping from an explicitly imported call to that Kind. Save the following two files in the same directory.

**`memory_definitions.py`** (trusted external declarations):

```python
from shikake.external import (
    Argument, ImportedCall, Role,
    bind, emit, kind_id, match, parent_id,
    part, structure_id, structure_ref,
)

class AllocationStructure:
    structure_id @= "demo.memory.allocation"
    part @= Role("size", "node")

class AllocationKind:
    kind_id @= "demo.memory.allocate"
    parent_id @= "model.value"
    structure_ref @= "demo.memory.allocation"

class AllocationCall:
    match @= ImportedCall("sample.memory:Memory.allocate")
    emit @= "demo.memory.allocate"
    bind @= Argument("size", 0, "size")
```

**`example.py`** (run with `python example.py`):

```python
import shikake
import memory_definitions
from shikake.external import load_external_definitions

definitions = load_external_definitions(memory_definitions)

source = (
    "from sample.memory import Memory\n"
    "item = Memory.allocate(64)\n"
)

root = shikake.parse_source(source, definitions=definitions)
for model in root.walk():
    if model.kind.id == "demo.memory.allocate":
        print(model.get_node("size").get("value"))
```

Output:

```text
64
```

The `sample.memory` interface module does **not** need to exist. The source under analysis and its import targets are never executed or imported; the **trusted declaration module** is ordinary Python code and must be safe to import. The registered call yields a Model with Kind `demo.memory.allocate` instead of an ordinary call Model. This is not dynamic resolution of arbitrary library calls.

**Current limitation:** External Shikumi declarations support adding **Kinds and Structures**, but **not Features**. External Feature declarations are rejected.

## Programmatic builder example

For trusted definitions built from Python data, `ExternalDefinitionsBuilder` avoids writing a separate Shikumi class for each Kind and call mapping:

```python
import shikake
from shikake.external import ExternalDefinitionsBuilder

definitions = (
    ExternalDefinitionsBuilder()
    .add_call("sample.memory:Memory.allocate", "demo.memory.allocate", ("size",))
    .build()
)

root = shikake.parse_source(
    "from sample.memory import Memory\nitem = Memory.allocate(64)\n",
    definitions=definitions,
)
for model in root.walk():
    if model.kind.id == "demo.memory.allocate":
        print(model.get_node("size").get("value"))
```

Output: `64`. The builder generates a concrete Kind and a node-only Structure for the declared call. Argument names are both role names and accepted keyword names; provide explicit `Argument(role, position, keyword)` objects when these differ. You can also declare and reuse a Structure (`add_structure`), define a parent Kind (`add_kind`), or map an additional target onto an existing Kind (`add_mapping`). `build()` runs the **same semantic validations** as Shikumi loading. Import targets in the analyzed source are not imported or executed. Directly imported free functions such as `from dot import sin` are **not** supported as external registered calls.

## API_001: `shikake.external.ImportedCall`

**Type.** Declaration of an externally modeled operation called through explicit import.

- **Inputs:** `path: str e.g. "framework.memory:Memory.new"`
- **Result:** `ImportedCall`
- **Specifications:** [EXTERNAL.SPEC_003](../../devdocs/canonical_sources/specification/external.py)

The path must identify a module and an attribute chain of at least `Class.method`.

## API_002: `shikake.external.Argument`

**Type.** Map an external call argument to a Model node role.

- **Inputs:** `role: str, position: int, keyword: str`
- **Result:** `Argument`
- **Specifications:** [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

Positions are contiguous, starting at zero.

## API_003: `shikake.external.ExternalDefinitions`

**Type.** Hold a validated external KindIndex and registered call mappings.

- **Inputs:** `index: KindIndex, mappings: tuple[CallMapping, ...]`
- **Result:** `ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

Supply the result to the parser using `definitions=`.

## API_004: `shikake.external.load_external_definitions`

**Operation.** Validate a trusted Python description module with Shikumi and load its external definitions.

- **Inputs:** `source: ModuleType, *, base: KindIndex | None = None`
- **Result:** `ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

The source being analyzed is never executed.

## API_005: `shikake.external.Role`

**Type.** A public alias for the PartContract defining a role and shape of an external Structure.

- **Inputs:** `role: str, shape: PartShape`
- **Result:** `Role`
- **Specifications:** [MODEL.SPEC_005](../../devdocs/canonical_sources/specification/model.py)

Declare both the role name and its shape.

## API_006: `shikake.external.match`

**Value.** A Shikumi field used to register an `ImportedCall`.

- **Inputs:** `ImportedCall`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_003](../../devdocs/canonical_sources/specification/external.py)

Register an external call by its complete path.

## API_007: `shikake.external.emit`

**Value.** A field specifying the output Kind ID of a registered call.

- **Inputs:** `kind_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

The output must be a registered concrete Kind.

## API_008: `shikake.external.bind`

**Value.** A field binding an `Argument` to an external Shikumi call.

- **Inputs:** `Argument`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

The mapping must match the output Structure's node roles.

## API_009: `shikake.external.kind_id`

**Value.** A field specifying an external Kind's ID.

- **Inputs:** `id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

Used together with fields defining its parent, Structure reference, and other attributes.

## API_010: `shikake.external.parent_id`

**Value.** A field specifying an external Kind's immediate classification parent.

- **Inputs:** `parent_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

Only Kind classification is affected.

## API_011: `shikake.external.structure_ref`

**Value.** A field referencing the Structure directly used by an external Kind.

- **Inputs:** `structure_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [MODEL.SPEC_004](../../devdocs/canonical_sources/specification/model.py)

A parent Kind's Structure is not inherited.

## API_012: `shikake.external.structure_id`

**Value.** A field declaring the ID of an external Structure.

- **Inputs:** `id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

Duplicate IDs are rejected.

## API_013: `shikake.external.part`

**Value.** A field listing role/shape definitions for an external Structure.

- **Inputs:** `Role`
- **Result:** `Shikumi field assignment`
- **Specifications:** [MODEL.SPEC_005](../../devdocs/canonical_sources/specification/model.py)

Declaration order is preserved.

## API_014: `shikake.external.CallMapping`

**Type.** An immutable mapping from a registered call target to its output Kind and arguments.

- **Inputs:** `target: ImportedCall, kind_id: str, arguments: tuple[Argument, ...]`
- **Result:** `CallMapping`
- **Specifications:** [EXTERNAL.SPEC_003](../../devdocs/canonical_sources/specification/external.py), [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

Stored in `ExternalDefinitions.mappings`.

## API_015: `shikake.external.ExternalDefinitionsBuilder`

**Type.** Build validated external Kinds, Structures, and call mappings from trusted Python data.

- **Inputs:** `__init__(*, base: KindIndex | None = None)`; `add_kind(kind_id: str, parent_id: str, structure_id: str | None = None)`; `add_structure(structure_id: str, parts: Sequence[Role])`; `add_mapping(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument])`; `add_call(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, parent_id: str = 'model.value', structure_id: str | None = None)`
- **Result:** `build() -> ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_012](../../devdocs/canonical_sources/specification/external.py)

`add_call` creates a Kind and a mapping together. If `structure_id` is omitted, it also creates a dedicated node-role Structure. For an already-declared Kind, use `add_mapping`. `arguments` accepts a sequence of names (each used for both the role and keyword) or a sequence of `Argument` objects. Mix neither, and do not pass a single string. The same KindIndex and call-mapping constraints apply as for `load_external_definitions`. This is a convenience API, not a relaxation of the protected-import rules or support for new external Features.
