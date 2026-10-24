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

- `introduction`: whether a written introduction is structurally stable (`stable` or `unstable`), or an implicit interpreter built-in introduction (`builtin`).
- `may_rebind`: whether a name may be rebound by a later or repeatable write, or by an augmented assignment.
- `may_delete`: whether the syntax indicates possible deletion.

For example, `x = 1` alone has `may_rebind=False`; adding `x = 2` makes it `True`. A lone `n += 1` does not establish a stable introduction. Built-in names such as `tuple` are treated as virtually introduced at module entry. A written module-level assignment to such a name is reported as a *possible rebind*, while a same-named local binding remains separate. Query them through `PackageModel.bindings_for(module, name)` or `SourceInspection.bindings_for(module, name)` after complete inspection. Read-only built-in names are not eagerly enumerated in `name_bindings`. Generic type-parameter annotation scopes and function/class bodies may share an owner Model; `NameBinding.scope_kind` distinguishes their otherwise identical records. These are **syntactic facts**, not predictions of execution, definite assignment, or judgments about code quality. The standard built-in name set is fixed for the Python minor version used for analysis; it does not depend on the current process’s `builtins` namespace. Runtime rebinding and object identity are not inferred.

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

### Generalized collection construction (v0.0.3)

Collection value Models use the three concrete Kinds `model.value.collection.sequence`, `.mapping`, and `.set`. All share `construction` (`literal`, `builtin`, or `comprehension`), `immutable` (a boolean), and `inputs` (ordered construction expressions). For example, `[1, 2]` and `list(xs)` are both Sequence Models, but have different `construction` values and different input Models. `(1, 2)` and `tuple(xs)` additionally have `immutable=True`.

The standard built-in name inventory is fixed per Python minor version, independent of `site` conveniences or process changes to `builtins`. Constructor calls are normalized only for supported written argument shapes: `list`/`tuple`/`set`/`frozenset` accept 0–1 positional arguments and no keywords or starred arguments; `dict`/`frozendict` accept 0–1 positional arguments and keyword arguments including `**`, but no `*` argument. Invalid or uncertain forms remain Calls without runtime argument validation. Generic PEP 695 type parameters shadow built-ins in the scopes where Python makes them visible. Annotation scopes directly inside a class can also see that class's names; ordinary nested method/class bodies cannot. Calls to built-in collection constructors are normalized **only if** the name is available as an unmodified implicit built-in in its visible lexical scopes. Shadowed or possibly overwritten names remain ordinary calls. This is a static and conservative classification, not evaluation or runtime type inference. Mapping covers `dict` and Python 3.15+ `frozendict`; Set covers `set` and `frozenset`. With `construction="literal"`, `inputs` are direct elements/entries; with `"builtin"`, they are written argument Models; with `"comprehension"`, one nested comprehension Model is stored, so a `walk()` can contain two value Models with the same source span. List, set, and dict comprehensions carry their clause-bearing Models inside `inputs`; generator expressions are unchanged. Tuple/list destructuring targets are represented separately from values. This changes the public Model Kind and Structure contracts relative to v0.0.2. [Details](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/public.md#collection-construction-models-v003-breaking-change).

### Strict and Partial analysis

- **Strict:** `parse_source()` and `parse_package()` require a complete result and raise on unsupported syntax or invalid structures.
- **Partial:** `inspect_source()` and `inspect_package()` return available results together with diagnostics when full analysis is not possible.

Use Strict analysis when completeness is required, and Partial analysis to inspect unsupported or incomplete inputs. **An incomplete Partial result must not be treated as a fully analyzed input.** Consult the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for details.

For package analysis, pass an `include(path, is_directory)` callback to `parse_package()` or `inspect_package()` to choose subdirectories and matching source files. Returning `False` for a directory prunes that entire subtree. The `extensions=(".py",)` parameter selects source suffixes: `(".dot",)` chooses only `.dot` and `(".py", ".dot")` chooses both. These files must contain Python syntax. By default **all** regular `.py` files are included, including those under `.venv`; shikake does not impose exclusion patterns. See [Package input selection](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/public.md#package-input-extensions-extensions-and-selection-include).

### Optional import permissions

Each parsing/inspection API supports `import_policy="unrestricted"` (default), `"registered_interfaces"` (only explicitly imported registered interfaces), and `"registered_modules"` (registered external modules plus caller-specified `allowed_modules=("math", "custom_tools")`). `registered_modules` also permits every explicit registered-interface import. Both restricted modes admit the single directive `from __future__ import annotations`. Relative imports, including within the analyzed package, remain forbidden: change them to absolute imports and explicitly allow the written module names as needed. `allowed_modules` names must be NFKC-normalized. These checks compare written absolute module names without importing them and do not provide a security sandbox. See the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/public.md#caller-selected-import-restrictions-import_policy-allowed_modules).

## Source comments (v0.0.2)

The explicit `collect_comments(source)` API returns `SourceComments` with immutable `Comment` records, independently of the AST Model tree:

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

For a function or class, the first statement of its `body` block supplies a line for querying comments immediately above that statement **only if no code appears before the statement on that same line**. For a one-line body such as `def f(): return 1`, this recipe does not apply. For an assignment statement, `span.end_line` supplies a line for querying its trailing comment. For example:

```python
import shikake

source = "def f():\n    # body note\n    value = 1  # value note\n    return value\n"
comments = shikake.collect_comments(source)
function = shikake.parse_source(source).get_nodes("body")[0]
first = function.get("body").get_nodes("statements")[0]
if first.span is not None:
    print(comments.above_line(first.span.line))
    print(comments.on_right_of_line(first.span.end_line))
```

The same `body` lookup works for class definitions. To verify the same-line precondition, use the same universal-newline behavior as comment collection (CR, LF, CRLF); **do not use `str.splitlines()`**, which also splits on form feeds and other characters not considered line breaks by the AST:

```python
import io

lines = io.StringIO(source, newline=None).readlines()
prefix = lines[first.span.line - 1].encode("utf-8")[: first.span.column]
if not prefix.strip():
    print(comments.above_line(first.span.line))
```

AST columns use UTF-8 byte offsets, so the prefix is measured in encoded bytes.

For a decorated function or class, search above its **earliest decorator** rather than its `def`/`class` line:

```python
import shikake

source = "# definition note\n\n@decorator\ndef decorated():\n    return 1\n"
comments = shikake.collect_comments(source)
function = shikake.parse_source(source).get_nodes("body")[0]
if function.span is not None:
    start = min(
        [function.span.line, *(d.span.line for d in function.get_nodes("decorators") if d.span is not None)]
    )
    print(tuple(comment.text for comment in comments.above_line(start)))
    # ('# definition note',)
```

Here `function.span` must be present. These are **line-position queries**, not attachments of comments to declarations or assignments. For comments within multiline constructs, use `in_lines(first, last)`.

It also supports `in_lines(first, last)`, `module_header()`, and `module_footer()`. Blank lines do not interrupt upward search; code lines do. CR, LF, and CRLF all use AST-compatible line numbers. For files with encoding declarations or a UTF-8 BOM, read with `tokenize.open(path)` and pass the **same decoded text** to both `collect_comments()` and `parse_source()`. A `SourceComments` result must be obtained from `collect_comments()`; direct construction and `dataclasses.replace()` are unsupported. Results for syntactically invalid Python input are not guaranteed across Python versions. Comments are not assigned to particular Models and type comments are not interpreted. Python AST parsing continues with `type_comments=False`. There is no separate Model-based comment lookup: callers can supply the line numbers from an available `Model.span` to the existing line queries. The module root and other Models may have `span=None`. A line query does not establish ownership, distinguish Models sharing a line, or verify that a Model and comments came from the same source. See the [API Reference](https://github.com/minoru-jp/shikake/blob/HEAD/docs/api_reference/INDEX.md) for details.

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
