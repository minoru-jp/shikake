# shikake: External Definitions API

Declarations and Call, Type, and Generic mapping APIs provided by `shikake.external`. External descriptions must be trusted.

Identifiers, parameter declarations, result types, and exception names below follow the Japanese canonical API source.
The specification links lead to the **Japanese Python canonical source**, not to generated specification Markdown.

## Import modeling and caller-owned acceptance

External mappings enable dedicated modeling for registered Call, Type, and Generic syntax, not Source acceptance checks. All import statements supported by Python syntax and shikake modeling are retained, whether or not an interface is registered. The caller is responsible for import policies, and shikake never imports or executes targets.

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

The `sample.memory` interface module does **not** need to exist. The source under analysis and its import targets are never executed or imported; the **trusted declaration module** is ordinary Python code and must be safe to import. The registered call yields a Model with Kind `demo.memory.allocate` instead of an ordinary call Model. This is not dynamic resolution of arbitrary library calls. A specialized Call is created only after its complete argument mapping has matched; missing or extra arguments retain an ordinary Call Model. Definite lexical shadowing by function parameters, local bindings, or comprehension targets also prevents specialized recognition. Lambda defaults and the first comprehension iterable are evaluated in their enclosing scope; comprehension bodies within classes do not treat class locals as visible. Star imports are not expanded or resolved.

**Supported declarations:** Trusted Shikumi declarations can add **Kinds, Structures and Features**. Call, Type, and Generic mappings can explicitly attach externally declared Features, but never built-in Features such as `async`, `generator`, or `lazy`.

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

Output: `64`. The builder generates a concrete Kind and a node-only Structure for the declared call. Argument names are both role names and accepted keyword names; provide explicit `Argument(role, position, keyword)` objects when these differ. You can also declare and reuse a Structure (`add_structure`), define a parent Kind (`add_kind`), or map an additional target onto an existing Kind (`add_mapping`). `build()` runs the **same semantic validations** as Shikumi loading. Import targets in the analyzed source are not imported or executed. Directly imported free functions such as `from dot import sin` are supported using a mapping target such as `dot:sin`.

## API_001: `shikake.external.ImportedCall`

**Type.** Declaration of an externally modeled operation called through explicit import.

- **Inputs:** `path: str e.g. "framework.memory:Memory.new"`
- **Result:** `ImportedCall`
- **Specifications:** [EXTERNAL.SPEC_003](../../devdocs/canonical_sources/specification/external.py)

The path must identify a module and at least one attribute. Both `module:function` and `module:Class.method` are supported.

## API_002: `shikake.external.Argument`

**Type.** Map an external call argument to a Model node role.

- **Inputs:** `role: str, position: int, keyword: str`
- **Result:** `Argument`
- **Specifications:** [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

Positions are contiguous, starting at zero.

## API_003: `shikake.external.ExternalDefinitions`

**Type.** Hold a DefinitionIndex, registered interface mappings, and provenance of declared external Features.

- **Inputs:** `index: DefinitionIndex, mappings: tuple[CallMapping, ...], type_mappings: tuple[TypeMapping, ...], generic_mappings: tuple[GenericMapping, ...], external_feature_ids: frozenset[str] = frozenset()`
- **Result:** `ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py), [EXTERNAL.SPEC_018](../../devdocs/canonical_sources/specification/external.py)

Supply the result to the parser using `definitions=`. `external_feature_ids` records externally declared Feature IDs available to mappings. **Only the builder and Shikumi loader validate declarations and provenance.** Constructing `ExternalDefinitions(...)` directly is a low-level, trusted operation: callers are responsible for the consistency of all fields, including `external_feature_ids`. This is not a tamper-proof security boundary for untrusted inputs.

## API_004: `shikake.external.load_external_definitions`

**Operation.** Validate a trusted Python description module with Shikumi and load its external definitions.

- **Inputs:** `source: ModuleType, *, base: DefinitionIndex | ExternalDefinitions | None = None`
- **Result:** `ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_001](../../devdocs/canonical_sources/specification/external.py)

The source being analyzed is never executed. For composition use `base=ExternalDefinitions`: this preserves previous mappings and external Feature provenance. The built-in `DefinitionIndex` is accepted as `base`, but a custom or previously extended index is rejected: it cannot preserve mappings or external Feature provenance. To compose extensions use `load_external_definitions(module, base=previous)` (with `previous` an `ExternalDefinitions`) or `ExternalDefinitionsBuilder(base=previous)`. Do not pass an `ExternalDefinitions` to a parser's `index=` parameter.

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

- **Inputs:** `target: ImportedCall, kind_id: str, arguments: tuple[Argument, ...], features: tuple[str, ...] = ()`
- **Result:** `CallMapping`
- **Specifications:** [EXTERNAL.SPEC_003](../../devdocs/canonical_sources/specification/external.py), [EXTERNAL.SPEC_007](../../devdocs/canonical_sources/specification/external.py)

Stored in `ExternalDefinitions.mappings`.

## API_015: `shikake.external.ExternalDefinitionsBuilder`

**Type.** Build validated external Kinds, Structures, Features, and interface mappings from trusted Python data.

- **Inputs:** `__init__(*, base: DefinitionIndex | ExternalDefinitions | None = None)`; `add_kind(kind_id: str, parent_id: str, structure_id: str | None = None)`; `add_structure(structure_id: str, parts: Sequence[Role])`; `add_feature(feature_id: str, allowed_kind_ids: Sequence[str])`; `add_mapping(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, features: Sequence[str] = ())`; `add_call(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, parent_id: str = 'model.value', structure_id: str | None = None, features: Sequence[str] = ())`; `add_type(target: str | ImportedType, kind_id: str, *, parent_id: str = 'model.value', features: Sequence[str] = ())`; `add_generic(target: str | ImportedGeneric, kind_id: str, roles: Sequence[str], *, parent_id: str = 'model.value', features: Sequence[str] = ())`
- **Result:** `build() -> ExternalDefinitions`
- **Specifications:** [EXTERNAL.SPEC_012](../../devdocs/canonical_sources/specification/external.py)

`add_call` creates a Kind and a mapping together. If `structure_id` is omitted, it also creates a dedicated node-role Structure. For an already-declared Kind, use `add_mapping`. `arguments` accepts a sequence of names (each used for both the role and keyword) or a sequence of `Argument` objects. Mix neither, and do not pass a single string. The same DefinitionIndex and call-mapping constraints apply as for `load_external_definitions`. External Features can be registered with `add_feature`. The `features=` argument explicitly attaches IDs to a matching Call, Type or Generic Model. Definitions and mapping attachments receive the same validation as Shikumi declarations. External Kind, Structure, and Feature IDs require at least two nonempty dot-separated segments, each satisfying `str.isidentifier()`. Python keywords and Unicode identifiers are valid segments (for example `dsl.stmt.return`, `gpu.async`, and `vendor.ｆｏｏ`); the leading `model` namespace is reserved. External IDs are **not** Unicode-normalized (including NFKC); identity and duplicate detection use the original strings, so visually similar IDs may be different. Use `base=ExternalDefinitions` to compose registrations; an extended `DefinitionIndex` alone is rejected because it cannot preserve mappings or external Feature provenance. Models built by the standard parsing/ModelFactory path normalize Features into ascending ID order, independent of mapping declaration order. Directly constructing `Model(...)` does not perform that normalization; tuple order then affects structural equality and hashing, and direct construction is unsupported. This is not a new import-resolution mechanism.

## Type and Generic interface modeling (v0.0.4)

When a trusted definition declares a Type name, shikake recognizes its written use in a **type position** such as a variable annotation, function parameter or result annotation, class base, type alias, or a registered Generic argument. That occurrence becomes a Model of the registered Kind; the same name used as an ordinary Python value remains a standard Name/Attribute Model. No type semantics, compatibility rules, or runtime evaluation are implied.

Generic interfaces recognize `Name[T]` or qualified forms and map a fixed number of positional `[...]` arguments to declared node roles. A registered generic application also works outside a type annotation. Unregistered or shape-mismatched subscripts remain standard `model.value.access.index` Models. A registered Generic target and its type arguments are **not** considered value references by the lightweight `may_value_use` observation. This information is not exhaustive.

```python
from shikake.external import ExternalDefinitionsBuilder
import shikake

definitions = (
    ExternalDefinitionsBuilder()
    .add_type("pyinto.kinds:int32", "example.int32")
    .add_generic("pyinto.kinds:Array", "example.array", ("item", "size"))
    .add_call("pyinto.kinds:int32", "example.make_int32", ("value",))
    .build()
)
root = shikake.parse_source(
    "from pyinto.kinds import int32, Array\n"
    "a: Array[int32, 4]\n"
    "b: int32 = int32(10)\n",
    definitions=definitions,
)
```

The corresponding Shikumi declaration uses `match_type @= ImportedType("pyinto.kinds:int32")`, or `match_generic @= ImportedGeneric("pyinto.kinds:Array")` with `slot @= "item"` and `slot @= "size"`. `emit` supplies the registered Kind ID, while the Type Kind requires an empty Structure and the Generic Kind requires node-only roles in slot order. A target may independently register Call, Type, and Generic modes.

## API_016: `shikake.external.ImportedType`

**Type.** Target path for the Type name interface. Validated like ImportedCall, and used only in written type contexts. See [EXTERNAL.SPEC_014](../../devdocs/canonical_sources/specification/external.py).

## API_017: `shikake.external.ImportedGeneric`

**Type.** Target path for an application with brackets. See [EXTERNAL.SPEC_014](../../devdocs/canonical_sources/specification/external.py).

## API_018: `shikake.external.TypeMapping`

**Type.** Immutable `target: ImportedType`, `kind_id: str` pair, stored in `ExternalDefinitions.type_mappings`.

## API_019: `shikake.external.GenericMapping`

**Type.** Immutable `target: ImportedGeneric`, `kind_id: str`, and ordered `roles: tuple[str, ...]`, stored in `ExternalDefinitions.generic_mappings`.

## API_020: `shikake.external.match_type`

**Value.** Shikumi assignment for the Type target; use with `emit`.

## API_021: `shikake.external.match_generic`

**Value.** Shikumi assignment for the Generic target; use with `emit`.

## API_022: `shikake.external.slot`

**Value.** Shikumi assignment of each Generic node role in positional order.

## API_023: `shikake.external.feature_id`

**Value.** Declare the ID of an external Feature with Shikumi.

- **Inputs:** `feature_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_016](../../devdocs/canonical_sources/specification/external.py)

## API_024: `shikake.external.feature_allowed`

**Value.** Declare a Kind classification on which an external Feature is allowed.

- **Inputs:** `kind_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_016](../../devdocs/canonical_sources/specification/external.py)

One or more allowed Kinds are required. Applicability extends to their descendants.

## API_025: `shikake.external.apply_feature`

**Value.** Explicitly attach a declared Feature to a matching Call, Type or Generic Model.

- **Inputs:** `feature_id: str`
- **Result:** `Shikumi field assignment`
- **Specifications:** [EXTERNAL.SPEC_017](../../devdocs/canonical_sources/specification/external.py)

A declaration alone does not attach a Feature. The registered interface must match before its declared Features are applied. The merged DefinitionIndex validates unknown, duplicate, and disallowed Feature IDs at registration time. An external mapping cannot assign built-in Features, even to a Kind where those Features are applicable. Models produced by the standard parsing path store Feature IDs in sorted order; direct `Model(...)` construction does not normalize them.

### External Feature example

The builder and trusted Shikumi declarations support the same behavior. For example:

```python
from shikake import parse_source
from shikake.external import ExternalDefinitionsBuilder

definitions = (
    ExternalDefinitionsBuilder()
    .add_feature("demo.checked", ("demo.operation",))
    .add_kind("demo.operation", "model.value")
    .add_call(
        "sample.ops:checked", "demo.operation.call", ("value",),
        parent_id="demo.operation", features=("demo.checked",),
    )
    .build()
)
root = parse_source(
    "from sample.ops import checked\nx = checked(5)\n",
    definitions=definitions,
)
assert [m.features for m in root.walk() if m.kind.id == "demo.operation.call"] == [("demo.checked",)]
assert definitions.index.allows_feature("demo.operation.call", "demo.checked")
```

The equivalent trusted Shikumi declaration uses `feature_id @= "demo.checked"` and `feature_allowed @= "demo.operation"` in a Feature entity; on a Call, Type or Generic mapping entity it uses `apply_feature @= "demo.checked"`.
