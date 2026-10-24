"""One AST-only collection of lexical operations and expression occurrences.

The parsed source is the sole source of syntactic facts. The index does not
import or execute source, infer values, or depend on the composition Model.
Consumers may attach their own meaning to the same recorded operations.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Literal


@dataclass(slots=True, eq=False)
class SyntaxScope:
    kind: Literal["module", "class", "function", "annotation"]
    node: ast.AST
    parent: SyntaxScope | None
    globals: set[str] = field(default_factory=set)
    nonlocals: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class SyntaxEvent:
    name: str
    kind: Literal[
        "import",
        "star",
        "definition",
        "parameter",
        "write",
        "augmented_write",
        "delete",
        "attribute_write",
        "attribute_delete",
        "annotation",
    ]
    node: ast.AST
    statement: ast.stmt
    scope: SyntaxScope
    sequence: int
    conditional: bool
    imported: tuple[str | None, str] | None = None
    explicit_module: str | None = None
    repeatable: bool = False


@dataclass(frozen=True, slots=True)
class SyntaxDefinition:
    statement: ast.stmt
    scope: SyntaxScope
    sequence: int


@dataclass(slots=True)
class SyntaxFacts:
    root: SyntaxScope
    scopes: tuple[SyntaxScope, ...]
    events: tuple[SyntaxEvent, ...]
    definitions: tuple[SyntaxDefinition, ...]
    # A maximal Name/Attribute and its direct parent, not every prefix in a
    # written attribute chain. Also includes Store and Del occurrences.
    references: tuple[tuple[ast.Name | ast.Attribute, ast.AST | None], ...]
    special_bindings: tuple[tuple[str, ast.AST], ...]
    # A generic declaration has two nested lexical scopes: type parameters
    # are visible across its body and headers, but ordinary class locals are
    # not inherited by methods. A type alias has only the annotation scope.
    annotation_scopes: dict[ast.AST, SyntaxScope] = field(default_factory=dict)

    def expression_scopes(
        self, tree: ast.Module
    ) -> tuple[dict[ast.AST, SyntaxScope], dict[ast.AST, ast.AST]]:
        """Map expression nodes to the lexically visible scope, once.

        Definition decorators/default values remain in the enclosing scope;
        generic bases, type-alias values and annotations see type parameters.
        This table is shared by all AST-based expression consumers.
        """
        scopes = {
            item.node: item
            for item in self.scopes
            if item.kind in {"class", "function"}
        }
        result: dict[ast.AST, SyntaxScope] = {}
        parents: dict[ast.AST, ast.AST] = {}
        pending: list[tuple[ast.AST, SyntaxScope, SyntaxScope | None]] = [
            (tree, self.root, None)
        ]
        while pending:
            node, scope, header_annotation = pending.pop()
            result[node] = scope
            body_scope = scopes.get(node)
            own_annotation = self.annotation_scopes.get(node)
            for name, value in ast.iter_fields(node):
                children = (
                    (value,)
                    if isinstance(value, ast.AST)
                    else value
                    if isinstance(value, list)
                    else ()
                )
                for child in children:
                    if not isinstance(child, ast.AST):
                        continue
                    parents[child] = node
                    child_scope = scope
                    next_annotation = header_annotation
                    if body_scope is not None:
                        next_annotation = own_annotation
                        if name == "body":
                            child_scope = body_scope
                            next_annotation = None
                        elif own_annotation is not None and (
                            name == "type_params"
                            or (
                                isinstance(node, ast.ClassDef)
                                and name in {"bases", "keywords"}
                            )
                            or (
                                isinstance(
                                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                                )
                                and name == "returns"
                            )
                        ):
                            child_scope = own_annotation
                    elif own_annotation is not None:
                        next_annotation = own_annotation
                        if name in {"value", "type_params"}:
                            child_scope = own_annotation
                    elif (
                        isinstance(node, ast.arg)
                        and name == "annotation"
                        and header_annotation is not None
                    ):
                        child_scope = header_annotation
                    pending.append((child, child_scope, next_annotation))
        return result, parents

    # All bound parameter / pattern / type parameter names are operations,
    # including syntactic constructs without an ast.Name(Store) child.


def explicit_import_path(event: SyntaxEvent) -> str | None:
    """The absolute path literally imported by this AST event, if known.

    `import pkg.child` binds `pkg` while importing the longer written path;
    `from pkg import child` binds `child` and names `pkg.child` explicitly.
    Relative imports have no absolute path until a module context is known.
    """
    if event.kind != "import" or event.imported is None:
        return None
    module, imported = event.imported
    if module is None or module.startswith("."):
        return None
    if event.explicit_module is not None:
        return event.explicit_module
    return f"{module}.{imported}" if imported else module


def _target_names(node: ast.AST) -> tuple[tuple[str, ast.AST], ...]:
    names: list[tuple[str, ast.AST]] = []
    pending = [node]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.Name):
            names.append((current.id, current))
        elif isinstance(current, (ast.Tuple, ast.List)):
            pending.extend(reversed(current.elts))
        elif isinstance(current, ast.Starred):
            pending.append(current.value)
    return tuple(names)


def _target_attributes(node: ast.AST) -> tuple[tuple[str, ast.Attribute], ...]:
    """Extract only explicit dotted attribute targets (no value propagation)."""
    found: list[tuple[str, ast.Attribute]] = []
    pending = [node]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.Attribute):
            path: list[str] = []
            end = current
            while isinstance(end, ast.Attribute):
                path.append(end.attr)
                end = end.value
            if isinstance(end, ast.Name):
                path.append(end.id)
                found.append((".".join(reversed(path)), current))
        elif isinstance(current, (ast.Tuple, ast.List)):
            pending.extend(reversed(current.elts))
        elif isinstance(current, ast.Starred):
            pending.append(current.value)
    return tuple(found)


_HeaderKind = Literal[
    "definition",
    "write",
    "augmented_write",
    "delete",
    "attribute_write",
    "attribute_delete",
    "annotation",
]
_HeaderWrite = tuple[str, ast.AST, _HeaderKind, bool, bool]


def _header_writes(statement: ast.stmt) -> tuple[_HeaderWrite, ...]:
    """Operations in a statement header, with expression-local conditionality.

    A compound statement is handled by the frame collector. Here we also
    retain places within expressions where evaluation may be skipped, without
    evaluating any values or execution paths.
    """
    found: list[_HeaderWrite] = []
    if isinstance(statement, ast.AnnAssign) and statement.value is None:
        # A bare annotation has no binding/write effect. In a function it
        # nevertheless declares a lexical local, blocking outer-name lookup.
        if isinstance(statement.target, ast.Name):
            found.append(
                (statement.target.id, statement.target, "annotation", False, False)
            )
    elif isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = (
            statement.targets
            if isinstance(statement, ast.Assign)
            else [statement.target]
        )
        for target in targets:
            found.extend(
                (
                    name,
                    origin,
                    "augmented_write"
                    if isinstance(statement, ast.AugAssign)
                    else "write",
                    False,
                    False,
                )
                for name, origin in _target_names(target)
            )
            found.extend(
                (name, origin, "attribute_write", False, False)
                for name, origin in _target_attributes(target)
            )
    elif isinstance(statement, ast.Delete):
        for target in statement.targets:
            found.extend(
                (name, origin, "delete", False, False)
                for name, origin in _target_names(target)
            )
            found.extend(
                (name, origin, "attribute_delete", False, False)
                for name, origin in _target_attributes(target)
            )
    elif isinstance(statement, (ast.For, ast.AsyncFor)):
        found.extend(
            (name, origin, "write", False, False)
            for name, origin in _target_names(statement.target)
        )
        found.extend(
            (name, origin, "attribute_write", False, False)
            for name, origin in _target_attributes(statement.target)
        )
    elif isinstance(statement, (ast.With, ast.AsyncWith)):
        for item in statement.items:
            if item.optional_vars is not None:
                found.extend(
                    (name, origin, "write", False, False)
                    for name, origin in _target_names(item.optional_vars)
                )
                found.extend(
                    (name, origin, "attribute_write", False, False)
                    for name, origin in _target_attributes(item.optional_vars)
                )
    elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        found.append((statement.name, statement, "definition", False, False))
    elif type(statement).__name__ == "TypeAlias":
        written = getattr(statement, "name", None)
        if isinstance(written, ast.Name):
            found.append((written.id, statement, "definition", False, False))

    # Named expressions in evaluated headers and other expressions. Nested
    # function/class bodies and statement blocks are separate frames. The
    # boolean records optional evaluation within the expression itself.
    expression_roots: list[tuple[ast.AST, bool, bool]] = []
    for field_name, value in ast.iter_fields(statement):
        if field_name in {
            "body",
            "orelse",
            "finalbody",
            "handlers",
            "cases",
            "type_params",
        }:
            continue
        # Header children such as ast.keyword, ast.arguments and ast.withitem
        # are not expressions themselves, but can contain NamedExpr writes.
        optional = isinstance(statement, ast.Assert)
        if isinstance(value, ast.AST) and not isinstance(value, ast.stmt):
            expression_roots.append((value, optional, False))
        elif isinstance(value, list):
            expression_roots.extend(
                (child, optional, False)
                for child in value
                if isinstance(child, ast.AST) and not isinstance(child, ast.stmt)
            )
    if isinstance(statement, (ast.Try, ast.TryStar)):
        # Handler type expressions run in the enclosing lexical scope; handler
        # bodies are traversed as separate conditional statement frames.
        expression_roots.extend(
            (handler.type, True, False)
            for handler in statement.handlers
            if handler.type is not None
        )
    if isinstance(statement, ast.Match):
        expression_roots.extend(
            (case.guard, True, False)
            for case in statement.cases
            if case.guard is not None
        )

    pending = expression_roots
    while pending:
        current, conditional, repeatable = pending.pop()
        if isinstance(current, ast.Lambda):
            # Defaults are evaluated in the containing lexical scope; the
            # lambda body belongs to the function's own scope.
            pending.extend(
                (default, conditional, repeatable) for default in current.args.defaults
            )
            pending.extend(
                (default, conditional, repeatable)
                for default in current.args.kw_defaults
                if default is not None
            )
            continue
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(current, ast.NamedExpr):
            found.extend(
                (name, origin, "write", conditional, repeatable)
                for name, origin in _target_names(current.target)
            )
        if isinstance(current, ast.BoolOp):
            # Only the first operand is necessarily evaluated. Neither the
            # operator nor its values are evaluated by the modeler.
            pending.extend(
                (value, conditional or index > 0, repeatable)
                for index, value in enumerate(current.values)
            )
            continue
        if isinstance(current, ast.IfExp):
            pending.extend(
                (
                    (current.test, conditional, repeatable),
                    (current.body, True, repeatable),
                    (current.orelse, True, repeatable),
                )
            )
            continue
        if isinstance(current, ast.Compare):
            # Chained comparisons may skip later comparators.
            pending.append((current.left, conditional, repeatable))
            pending.extend(
                (value, conditional or index > 0, repeatable)
                for index, value in enumerate(current.comparators)
            )
            continue
        if isinstance(
            current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            # The result expression and all comprehension clauses are subject
            # to iteration (and generator evaluation may be deferred).
            pending.extend(
                (child, True, True) for child in ast.iter_child_nodes(current)
            )
            continue
        pending.extend(
            (child, conditional, repeatable) for child in ast.iter_child_nodes(current)
        )
    return tuple(found)


def _child_blocks(
    statement: ast.stmt,
) -> tuple[tuple[list[ast.stmt], tuple[tuple[str, ast.AST], ...]], ...]:
    if isinstance(statement, ast.If):
        branches: list[tuple[list[ast.stmt], tuple[tuple[str, ast.AST], ...]]] = []
        current = statement
        while True:
            elif_captures = (
                tuple(
                    (name, origin) for name, origin, _, _, _ in _header_writes(current)
                )
                if current is not statement
                else ()
            )
            branches.append((current.body, elif_captures))
            if (
                len(current.orelse) == 1
                and isinstance(current.orelse[0], ast.If)
                and current.orelse[0].col_offset == current.col_offset
            ):
                current = current.orelse[0]
                continue
            if current.orelse:
                branches.append((current.orelse, ()))
            return tuple(branches)
    if isinstance(statement, ast.Match):
        branches = []
        for case in statement.cases:
            captures: list[tuple[str, ast.AST]] = []
            for node in ast.walk(case.pattern):
                if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
                    captures.append((node.name, node))
                elif isinstance(node, ast.MatchMapping) and node.rest:
                    captures.append((node.rest, node))
            branches.append((case.body, tuple(captures)))
        return tuple(branches)
    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        return ((statement.body, ()), (statement.orelse, ()))
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        return ((statement.body, ()),)
    if isinstance(statement, (ast.Try, ast.TryStar)):
        return (
            (statement.body, ()),
            *((h.body, ((h.name, h),) if h.name else ()) for h in statement.handlers),
            (statement.orelse, ()),
            (statement.finalbody, ()),
        )
    if isinstance(statement, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return ((statement.body, ()),)
    return ()


@dataclass(slots=True)
class _Frame:
    statements: list[ast.stmt]
    scope: SyntaxScope
    conditional: bool = False
    position: int = 0
    # Pattern / handler captures are emitted at the first entry to a block.
    captures: tuple[tuple[str, ast.AST], ...] = ()
    header: ast.stmt | None = None
    added_captures: bool = False
    captures_conditional: bool = True
    repeatable: bool = False


def collect_syntax_facts(
    tree: ast.Module, *, include_references: bool = True
) -> SyntaxFacts:
    """Collect lexical events and optional reference uses without executing input."""
    root = SyntaxScope("module", tree, None)
    scopes = [root]
    events: list[SyntaxEvent] = []
    definitions: list[SyntaxDefinition] = []
    references: list[tuple[ast.Name | ast.Attribute, ast.AST | None]] = []
    special_bindings: list[tuple[str, ast.AST]] = []
    annotation_scopes: dict[ast.AST, SyntaxScope] = {}

    # The occurrence table is needed by external-structure validation only.
    # Relationship analysis does not construct this unused table.
    pending: list[tuple[ast.AST, ast.AST | None]] = (
        [(tree, None)] if include_references else []
    )
    while pending:
        node, parent = pending.pop()
        if isinstance(node, (ast.Name, ast.Attribute)) and not (
            isinstance(parent, ast.Attribute) and parent.value is node
        ):
            references.append((node, parent))
        if isinstance(node, ast.arg):
            special_bindings.append((node.arg, node))
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            special_bindings.append((node.name, node))
        elif isinstance(node, ast.MatchMapping) and node.rest:
            special_bindings.append((node.rest, node))
        elif isinstance(node, ast.ExceptHandler) and node.name:
            special_bindings.append((node.name, node))
        elif type(node).__name__ in {"TypeVar", "TypeVarTuple", "ParamSpec"}:
            parameter_name = getattr(node, "name", None)
            if isinstance(parameter_name, str):
                special_bindings.append((parameter_name, node))
        pending.extend(
            (child, node) for child in reversed(tuple(ast.iter_child_nodes(node)))
        )

    frames = [_Frame(tree.body, root)]
    sequence = 0
    while frames:
        frame = frames[-1]
        if not frame.added_captures:
            frame.added_captures = True
            for name, node in frame.captures:
                if frame.header is not None:
                    events.append(
                        SyntaxEvent(
                            name,
                            (
                                "parameter"
                                if isinstance(node, ast.arg)
                                or type(node).__name__
                                in {"TypeVar", "TypeVarTuple", "ParamSpec"}
                                else "write"
                            ),
                            node,
                            frame.header,
                            frame.scope,
                            sequence,
                            frame.captures_conditional,
                            repeatable=frame.repeatable,
                        )
                    )
                    if isinstance(node, ast.ExceptHandler):
                        # `except E as name` also mandates an implicit deletion
                        # of `name` when the handler exits (likewise `except*`).
                        # Record the syntactic effect, not execution timing.
                        events.append(
                            SyntaxEvent(
                                name,
                                "delete",
                                node,
                                frame.header,
                                frame.scope,
                                sequence,
                                True,
                                repeatable=frame.repeatable,
                            )
                        )
        if frame.position == len(frame.statements):
            frames.pop()
            continue
        stmt = frame.statements[frame.position]
        frame.position += 1
        sequence += 1
        if isinstance(stmt, ast.Global):
            frame.scope.globals.update(stmt.names)
            continue
        if isinstance(stmt, ast.Nonlocal):
            frame.scope.nonlocals.update(stmt.names)
            continue
        if isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(SyntaxDefinition(stmt, frame.scope, sequence))
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for alias in stmt.names:
                is_star = alias.name == "*" and isinstance(stmt, ast.ImportFrom)
                name = (
                    "*"
                    if is_star
                    else alias.asname
                    or (
                        alias.name.split(".")[0]
                        if isinstance(stmt, ast.Import)
                        else alias.name
                    )
                )
                origin = (
                    (("." * stmt.level) + (stmt.module or ""), alias.name)
                    if isinstance(stmt, ast.ImportFrom)
                    else (
                        (alias.name if alias.asname else alias.name.split(".")[0]),
                        "",
                    )
                )
                events.append(
                    SyntaxEvent(
                        name,
                        "star" if is_star else "import",
                        alias,
                        stmt,
                        frame.scope,
                        sequence,
                        frame.conditional,
                        origin,
                        (
                            alias.name
                            if isinstance(stmt, ast.Import)
                            and alias.asname is None
                            and "." in alias.name
                            else None
                        ),
                        frame.repeatable,
                    )
                )
        else:
            for (
                name,
                node,
                kind,
                expression_conditional,
                expression_repeatable,
            ) in _header_writes(stmt):
                is_conditional = (
                    expression_conditional
                    or frame.conditional
                    or isinstance(
                        stmt,
                        (
                            ast.If,
                            ast.For,
                            ast.AsyncFor,
                            ast.While,
                            ast.Try,
                            ast.TryStar,
                            ast.With,
                            ast.AsyncWith,
                            ast.Match,
                        ),
                    )
                )
                events.append(
                    SyntaxEvent(
                        name,
                        kind,
                        node,
                        stmt,
                        frame.scope,
                        sequence,
                        is_conditional,
                        repeatable=frame.repeatable
                        or expression_repeatable
                        or isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)),
                    )
                )
        is_declaration = isinstance(
            stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        # Annotation scopes are a lexical overlay enclosing the *body* scope.
        # The type-alias expression also evaluates in its own annotation scope.
        parameters = tuple(
            (name, parameter)
            for parameter in getattr(stmt, "type_params", ())
            if isinstance(name := getattr(parameter, "name", None), str)
        )
        annotation_scope = None
        if parameters:
            annotation_scope = SyntaxScope("annotation", stmt, frame.scope)
            scopes.append(annotation_scope)
            annotation_scopes[stmt] = annotation_scope
            for name, parameter in parameters:
                events.append(
                    SyntaxEvent(
                        name,
                        "parameter",
                        parameter,
                        stmt,
                        annotation_scope,
                        sequence,
                        False,
                    )
                )
        if is_declaration:
            child_scope = SyntaxScope(
                "class" if isinstance(stmt, ast.ClassDef) else "function",
                stmt,
                annotation_scope or frame.scope,
            )
            scopes.append(child_scope)
            branch_scope = child_scope
            branch_conditional = False
        else:
            branch_scope = frame.scope
            branch_conditional = True
        blocks = _child_blocks(stmt)
        for body, captures in reversed(blocks):
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = stmt.args
                captures = (
                    *captures,
                    *((arg.arg, arg) for arg in args.posonlyargs),
                    *((arg.arg, arg) for arg in args.args),
                    *((arg.arg, arg) for arg in args.kwonlyargs),
                    *((arg.arg, arg) for arg in (args.vararg, args.kwarg) if arg),
                )
            frames.append(
                _Frame(
                    body,
                    branch_scope,
                    # The declaration itself inherits outer conditionality,
                    # but statements in a new lexical scope do not.
                    (
                        False
                        if branch_scope is not frame.scope
                        else frame.conditional or branch_conditional
                    ),
                    captures=captures,
                    header=stmt,
                    captures_conditional=not isinstance(
                        stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ),
                    repeatable=(
                        False
                        if branch_scope is not frame.scope
                        else frame.repeatable
                        or (
                            isinstance(stmt, (ast.For, ast.AsyncFor, ast.While))
                            and body is stmt.body
                        )
                    ),
                )
            )
    return SyntaxFacts(
        root,
        tuple(scopes),
        tuple(events),
        tuple(definitions),
        tuple(references),
        tuple(special_bindings),
        annotation_scopes,
    )
