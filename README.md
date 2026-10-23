# shikake

**shikake** is an AST-based library that models the static structures and relationships of Python source code according to consumer-defined, domain-specific structural conventions.

It provides building blocks for working with Python code under your own rules, including transpilation and the design or validation of restricted Python dialects. You can also define custom structures and have designated Python constructs modeled using those structures.

Python syntax validation defaults to CPython's non-executing compilation level (`syntax_validation="compile"`). Use `syntax_validation="ast"` to skip compilation checks when modeling AST-parseable restricted dialects; unsupported shikake syntax remains unsupported. This does not execute input code or guarantee runtime correctness.

## Development status (Alpha)

shikake is currently in **Alpha**. Public APIs, specifications, and data structures may change incompatibly without prior notice. See [STATUS](https://github.com/minoru-jp/shikake/blob/HEAD/docs/STATUS.md) for current progress.

## Core concepts

Rather than preserving Python syntax verbatim, shikake represents selected syntactic information in a form that consumers can interpret for their own purposes.

### Model structure

- **Kind** classifies a syntactic element.
- **Structure** specifies the roles and shapes of its constituent parts.
- **Feature** captures orthogonal characteristics, such as `async` or an explicitly written `lazy` import modifier.
- **Model** holds a concrete element according to these definitions.

Trusted external Shikumi declarations or an `ExternalDefinitionsBuilder` using Python data can add Kinds and Structures, and registered calls are represented by dedicated Models during parsing. External Feature declarations are not currently supported.

### Three dimensions of name binding

shikake represents three independent properties of a name's binding:

- `introduction`: whether the introduction is structurally stable (`stable` or `unstable`).
- `may_rebind`: whether a name may be rebound by a later or repeatable write, or by an augmented assignment.
- `may_delete`: whether the syntax indicates possible deletion.

For example, `x = 1` alone has `may_rebind=False`; adding `x = 2` makes it `True`. A lone `n += 1` does not establish a stable introduction. These are **syntactic facts**, not predictions of execution, definite assignment, or judgments about code quality.

### Static relationship candidates

shikake can report candidate targets of base-class references and same-name method override candidates. These are candidates supported by the AST, not guarantees about runtime targets or method resolution order. See the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for the available results and links to their specifications.

## Installation

Python 3.11 or later is required. CI targets Python 3.11–3.15; Python 3.14 t-strings are modeled as distinct Kinds.

```bash
python -m pip install shikake
```

## Quick start

```python
import shikake

source = '''
class Counter:
    def __init__(self, start=0):
        self.value = start

    def increase(self, amount):
        if amount > 0:
            self.value += amount
        return self.value

def calculate(values):
    counter = Counter()
    for value in values:
        counter.increase(value)
    return counter.value
'''

root = shikake.parse_source(source)

for model in root.walk():
    print(model.kind.id)
    print([part.role for part in model.parts()])
```

`parse_source()` builds a Model from one Python source string, and `walk()` traverses its composition tree. Kind, Structure, and Feature let consumers classify elements without depending directly on their original AST nodes.

### Strict and Partial analysis

- **Strict:** `parse_source()` and `parse_package()` require a complete result and raise on unsupported syntax or invalid structures.
- **Partial:** `inspect_source()` and `inspect_package()` return available results together with diagnostics when full analysis is not possible.

Use Strict analysis when completeness is required, and Partial analysis to inspect unsupported or incomplete inputs. **An incomplete Partial result must not be treated as a fully analyzed input.** Consult the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for details.

For package analysis, pass an `include(path, is_directory)` callback to `parse_package()` or `inspect_package()` to choose subdirectories and matching source files. Returning `False` for a directory prunes that entire subtree. The `extensions=(".py",)` parameter selects source suffixes: `(".dot",)` chooses only `.dot` and `(".py", ".dot")` chooses both. These files must contain Python syntax. By default **all** regular `.py` files are included, including those under `.venv`; shikake does not impose exclusion patterns. See [Package input selection](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/public.md#package-input-extensions-extensions-and-selection-include).

### Optional import permissions

Each parsing/inspection API supports `import_policy="unrestricted"` (default), `"registered_interfaces"` (only explicitly imported registered interfaces), and `"registered_modules"` (registered external modules plus caller-specified `allowed_modules=("math", "custom_tools")`). `registered_modules` also permits every explicit registered-interface import. Both restricted modes admit the single directive `from __future__ import annotations`. Relative imports, including within the analyzed package, remain forbidden: change them to absolute imports and explicitly allow the written module names as needed. `allowed_modules` names must be NFKC-normalized. These checks compare written absolute module names without importing them and do not provide a security sandbox. See the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/public.md#caller-selected-import-restrictions-import_policy-allowed_modules).

## External structures

Consumers can define custom Kinds and Structures with trusted Shikumi declarations or `shikake.external.ExternalDefinitionsBuilder` and provide them to the parser. For example, a transpiler may map a Python-facing memory or I/O interface to special operations in its target language.

When their documented conditions are met, explicitly imported calls registered as external operations produce dedicated Models instead of ordinary Python call Models. This is not general-purpose resolution of arbitrary libraries: explicit-import and reserved-name rules constrain recognition. See the [External Definitions API](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/external.md).

## Using analysis results

Transpilation and restricted-Python validation share a basic pattern: inspect Kind, Structure, and Feature information, optionally consult binding facts and static relationship candidates, and then **apply the consumer's own rules** to translate or accept/reject the input.

shikake does not define those downstream rules. Models are intended to be obtained from the official parsing APIs; constructing your own Models is unsupported.

## Limitations

shikake does not execute source code, evaluate values, infer types, or resolve dynamic names. Models do not aim to reproduce the original Python code perfectly or to establish its runtime semantics. Syntactic inspection alone does not provide a secure execution sandbox.

See the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for individual contracts and the [Documentation Policy](https://github.com/minoru-jp/shikake/blob/HEAD/docs/DOCUMENTATION_POLICY.md) for how the sources are managed.

## Documentation

[API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) | [Status](https://github.com/minoru-jp/shikake/blob/HEAD/docs/STATUS.md) | [Changelog](https://github.com/minoru-jp/shikake/blob/HEAD/CHANGELOG.md) | [Documentation Policy](https://github.com/minoru-jp/shikake/blob/HEAD/docs/DOCUMENTATION_POLICY.md)

## License

shikake is distributed under the [MIT License](https://github.com/minoru-jp/shikake/blob/HEAD/LICENSE).
