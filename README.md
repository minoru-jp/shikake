# shikake

**Alpha warning:** This library is experimental. Breaking changes to APIs and Model contracts may occur.

**shikake** turns Python source code into structured Models. **It provides structure; consumers decide what the code means and whether to accept it.**

- **Building blocks:** **Kind** (classification), **Structure** (roles and shapes of parts), and **Feature** (independent syntactic characteristics).
- **Foundation:** Python's standard-library `ast` and `tokenize` modules, plus the external **Shikumi** library.
- **Extensibility:** Consumers can register external Call, Type, and Generic interfaces.

## Installation

Requires Python 3.11 or later.

```bash
python -m pip install shikake
```

For development progress and support coverage, see [STATUS](https://github.com/minoru-jp/shikake/blob/HEAD/docs/STATUS.md).

## Example

This example models both Python syntax and registered external interfaces:

- **Python structure:** a class, methods, a loop, and type annotations.
- **Registered structure:** external Call, Type, and Generic interfaces.

The `demo` modules are illustrative. shikake neither executes the analyzed source nor imports them.

### 1. Python source

```python
source = '''from demo.kinds import Int32, Vector
from demo.ops import clamp

class Accumulator:
    def __init__(self, start: Int32):
        self.value = start

    def accumulate(self, numbers: Vector[Int32, 4]) -> Int32:
        total: Int32 = 0
        for number in numbers:
            total += number
        self.value += total
        return clamp(self.value, 0, 100)

def summarize(values: Vector[Int32, 4]) -> Int32:
    accumulator = Accumulator(0)
    return accumulator.accumulate(values)
'''
```

### 2. Register external interfaces and model the source

`ExternalDefinitionsBuilder` registers imported names and the syntactic forms in which they are used:

- **Type:** `Int32` → `demo.type.int32`
- **Generic:** `Vector[...]` → `demo.type.vector`
- **Call:** `clamp(...)` → `demo.operation.clamp`

Matching forms become dedicated Models instead of ordinary type references, subscripts, or calls.

```python
from collections import Counter

import shikake
from shikake.external import ExternalDefinitionsBuilder

definitions = (
    ExternalDefinitionsBuilder()
    .add_type("demo.kinds:Int32", "demo.type.int32")
    .add_generic(
        "demo.kinds:Vector",
        "demo.type.vector",
        ("element", "length"),
    )
    .add_call(
        "demo.ops:clamp",
        "demo.operation.clamp",
        ("value", "lower", "upper"),
    )
    .build()
)

inspection = shikake.inspect_source(source, definitions=definitions)
assert inspection.complete and inspection.model is not None
root = inspection.model
counts = Counter(node.kind.id for node in root.walk())

for kind in (
    "model.definition.class",
    "model.definition.function",
    "demo.type.int32",
    "demo.type.vector",
    "demo.operation.clamp",
):
    print(f"{kind}: {counts[kind]}")
```

Output:

```text
model.definition.class: 1
model.definition.function: 1
demo.type.int32: 6
demo.type.vector: 2
demo.operation.clamp: 1
```

Examples of the resulting structure:

- **`Vector[Int32, 4]`:** `element` holds `demo.type.int32`; `length` holds the literal value `4`.
- **`clamp(...)`:** becomes `demo.operation.clamp`.

**Kind names describe structure.** shikake does not interpret the semantics of `Int32` or other runtime types.

### 3. Inspect name bindings

shikake also exposes observations about name introduction and use. This code continues from the previous example:

```python
method = next(
    node for node in root.walk()
    if node.kind.id == "model.definition.method"
    and node.get_scalar("name") == "accumulate"
)

for scope, name in (
    (root, "Int32"),
    (root, "clamp"),
    (method, "total"),
):
    state = inspection.bindings_for(scope, name)[0].state
    print(name, state)
```

Output:

```text
Int32 BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)
clamp BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)
total BindingState(introduction='stable', may_rebind=True, may_delete=False, may_value_use=True)
```

The four `BindingState` properties are **lightweight observations**:

- **`introduction`:** how a name was introduced (`Int32` and `clamp` are `external`).
- **`may_rebind` / `may_delete`:** whether rebinding or deletion was observed.
- **`may_value_use`:** whether use as a value was observed. Registered Type and Call uses do not count.

For `total`, shikake observes augmented assignment and value use. These properties are not exhaustive name tracking: **`False` does not prove absence.**

## Design: structure without prescribed semantics

shikake deliberately stops at structural modeling rather than fully interpreting Python programs.

- **Describes structure:** Kinds, Structures, Features, source positions, and candidate static relationships.
- **Observes coarse facts:** name introduction, rebinding, deletion, and value use. No type inference or detailed identifier tracking.
- **Does not decide semantics:** Python runtime behavior, whether modeled code is acceptable, or what it means in a target language.
- **Consumers decide:** for example, reject code where rebinding is observed, or define target-language meanings for registered interfaces.

**Boundary:** shikake uses Python syntax and selected scope rules, but does not reproduce full runtime semantics. An unobserved use may still exist. Consumers needing stronger guarantees must perform additional validation.

## Declaring external interfaces with Shikumi

You can declare the same external interfaces using **Shikumi**, which shikake also uses for its own Kinds and Structures.

- **`@=`:** Python's augmented matrix-multiplication syntax used for Shikumi declarations. It is **not interchangeable with `=`**.
- **Analyzed source:** modeled, but not executed or imported.
- **Trusted declarations:** imported by the consumer from a separate definition module.

### 1. How shikake declares its own Models

Here is an abbreviated excerpt of shikake's internal declarations. It illustrates the notation, rather than recommending internal imports for applications.

```python
# Excerpt from shikake's internal declarations
from shikake._mica.kinds.regulation import (
    PartContract as Role, kind_id, parent_id,
    part, structure_id, structure_ref,
)

class ModuleDefinition:
    structure_id @= "module_definition"
    part @= Role("name", "text")
    part @= Role("body", "nodes")

class Module:
    kind_id @= "model.module"
    parent_id @= "model"
    structure_ref @= "module_definition"
```

- **`structure_id` / `part`:** declare a Structure and its parts.
- **`kind_id` / `parent_id` / `structure_ref`:** connect a Kind to a Structure.

External definitions use the public `shikake.external` API, not shikake's internal module.

### 2. Define Type, Generic, and Call interfaces

Save this as **`trusted_definitions.py`**. It describes the same `Int32`, `Vector`, and `clamp` interfaces as the preceding example.

```python
# trusted_definitions.py (a trusted declaration module)
from shikake.external import (
    Argument, ImportedCall, ImportedGeneric, ImportedType, Role,
    bind, emit, kind_id, match, match_generic, match_type,
    parent_id, part, slot, structure_id, structure_ref,
)

class Int32Structure:
    structure_id @= "demo.type.int32.type"

class Int32Kind:
    kind_id @= "demo.type.int32"
    parent_id @= "model.value"
    structure_ref @= "demo.type.int32.type"

class Int32Use:
    match_type @= ImportedType("demo.kinds:Int32")
    emit @= "demo.type.int32"

class VectorStructure:
    structure_id @= "demo.type.vector.generic"
    part @= Role("element", "node")
    part @= Role("length", "node")

class VectorKind:
    kind_id @= "demo.type.vector"
    parent_id @= "model.value"
    structure_ref @= "demo.type.vector.generic"

class VectorUse:
    match_generic @= ImportedGeneric("demo.kinds:Vector")
    emit @= "demo.type.vector"
    slot @= "element"
    slot @= "length"

class ClampStructure:
    structure_id @= "demo.operation.clamp.arguments"
    part @= Role("value", "node")
    part @= Role("lower", "node")
    part @= Role("upper", "node")

class ClampKind:
    kind_id @= "demo.operation.clamp"
    parent_id @= "model.value"
    structure_ref @= "demo.operation.clamp.arguments"

class ClampUse:
    match @= ImportedCall("demo.ops:clamp")
    emit @= "demo.operation.clamp"
    bind @= Argument("value", 0, "value")
    bind @= Argument("lower", 1, "lower")
    bind @= Argument("upper", 2, "upper")
```

- **Type:** `match_type` selects the name; the Structure has no parts.
- **Generic:** `match_generic` and `slot` describe the `[...]` arguments.
- **Call:** `match` and `bind` map the `(...)` arguments.
- **Shared:** `emit` names the Kind; imported targets use `module:name`.

### 3. Load the declarations

Shikumi validates the trusted declarations, which can then be supplied to shikake using the same `source` from the earlier example.

```python
import shikake
import trusted_definitions
from shikake.external import load_external_definitions

definitions = load_external_definitions(trusted_definitions)
root = shikake.parse_source(source, definitions=definitions)
print([node.kind.id for node in root.walk()].count("demo.operation.clamp"))
# 1
```

These declarations specify **how to model** a form, not its runtime meaning or whether a consumer should accept it. See the [External Definitions API](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/external.md) for details.

## Working with Models

- **Model traversal:** explore `walk()`, Kinds, Structures, Features, and source positions.
- **Structural relationships:** inspect candidate base-class references and same-name method overrides.
- **External definitions:** register Call, Type, and Generic interfaces through the Python API or trusted Shikumi declarations.
- **Analysis modes:** use `parse_source()` / `parse_package()` for complete results and `inspect_source()` / `inspect_package()` for results with diagnostics.
- **Import checks:** consumers may delegate allow/deny checks through `ImportPolicy`. Star imports are represented, but their implicit name introductions and binding effects are not inferred.

For exact contracts and limitations, see the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for exact contracts and limitations.

## Documentation

- [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md): public APIs and detailed contracts
- [STATUS](https://github.com/minoru-jp/shikake/blob/HEAD/docs/STATUS.md): current development status and known limitations
- [CHANGELOG](https://github.com/minoru-jp/shikake/blob/HEAD/CHANGELOG.md): changes by release
- [Documentation Policy](https://github.com/minoru-jp/shikake/blob/HEAD/docs/DOCUMENTATION_POLICY.md): canonical sources and publication workflow

## License

[MIT License](https://github.com/minoru-jp/shikake/blob/HEAD/LICENSE)
