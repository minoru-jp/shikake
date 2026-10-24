"""Bounded AST-to-Model conversion; input code is never imported or run."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from types import ModuleType
from typing import Literal, cast

from shikake.external import ExternalDefinitions, load_external_definitions

from .ast_facts import collect_syntax_facts
from .builtin_collections import BuiltinCollectionRecognition
from .external_structures import (
    _LOCAL_EXTERNAL_ERROR_CODES,
    ExternalModelingError,
    _ExternalStructures,
)
from .import_policy import (
    ImportPolicy,
    _assert_import_policy,
    _validated_import_options,
)
from .kinds import KindIndex, kind_index
from .model import Model, ModelFactory, SourceSpan

SyntaxValidation = Literal["compile", "ast"]


def _validated_syntax_validation(mode: SyntaxValidation) -> None:
    """Check the caller option, including for empty package selections."""
    if not isinstance(mode, str):
        raise TypeError("syntax_validation must be a string")
    if mode not in ("compile", "ast"):
        raise ValueError(f"unknown syntax_validation: {mode!r}")


def _compile_check(tree: ast.Module, filename: str, mode: SyntaxValidation) -> None:
    """Validate CPython compilation without executing or importing the source."""
    if mode == "compile":
        compile(tree, filename, "exec", dont_inherit=True)


from .modeling.base313 import build_expression, build_statement
from .modeling.common import UnsupportedSyntaxError, _span


class _OwnYieldFinder:
    """Find function-owned yield without walking nested function bodies.

    Function/class headers and the first iterable of a comprehension belong
    to the outer evaluation context. Visit all other children iteratively.
    """

    def __init__(self) -> None:
        self.found = False

    def visit(self, node: ast.AST) -> None:
        pending = [node]
        while pending and not self.found:
            current = pending.pop()
            if isinstance(current, (ast.Yield, ast.YieldFrom)):
                self.found = True
                return
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                children: tuple[ast.AST, ...] = (
                    *current.decorator_list,
                    current.args,
                    *((current.returns,) if current.returns is not None else ()),
                    *getattr(current, "type_params", ()),
                )
            elif isinstance(current, ast.ClassDef):
                children = (
                    *current.decorator_list,
                    *current.bases,
                    *current.keywords,
                    *getattr(current, "type_params", ()),
                )
            elif isinstance(current, ast.Lambda):
                children = (current.args,)
            elif isinstance(
                current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                children = (current.generators[0].iter,) if current.generators else ()
            else:
                children = tuple(ast.iter_child_nodes(current))
            pending.extend(reversed(children))


def _has_own_yield(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    visitor = _OwnYieldFinder()
    for statement in node.body:
        visitor.visit(statement)
        if visitor.found:
            return True
    return False


class _Builder:
    def __init__(
        self,
        index: KindIndex,
        *,
        on_unsupported: Callable[[UnsupportedSyntaxError, ast.AST], None] | None = None,
        on_external: Callable[[ExternalModelingError, ast.AST], None] | None = None,
        local_external_errors: Mapping[int, tuple[ExternalModelingError, ...]]
        | None = None,
        external: _ExternalStructures | None = None,
        collections: BuiltinCollectionRecognition | None = None,
    ) -> None:
        self.factory = ModelFactory(index)
        # Minimal AST-to-Model bridge for successfully modeled statements.
        self.statement_models: dict[int, Model] = {}
        self.external = external
        self.collections = collections
        self.on_unsupported = on_unsupported
        self.on_external = on_external
        self.local_external_errors = local_external_errors or {}
        self._prebuilt_blocks: dict[int, Model] | None = None
        self._current_block_reads: list[int] | None = None

    @staticmethod
    def _child_blocks(
        node: ast.stmt, *, class_body: bool
    ) -> tuple[tuple[list[ast.stmt], bool], ...]:
        """Enumerate the blocks read when this statement is modeled.

        An `elif` chain is one branch Model, not recursively nested branch
        Models. Its intermediate `orelse` lists therefore need no Model.
        """
        if isinstance(node, ast.If):
            blocks: list[tuple[list[ast.stmt], bool]] = []
            current = node
            while True:
                blocks.append((current.body, class_body))
                if (
                    len(current.orelse) == 1
                    and isinstance(current.orelse[0], ast.If)
                    and current.orelse[0].col_offset == current.col_offset
                ):
                    current = current.orelse[0]
                    continue
                if current.orelse:
                    blocks.append((current.orelse, class_body))
                return tuple(blocks)
        if isinstance(node, ast.Match):
            return tuple((case.body, class_body) for case in node.cases)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return ((node.body, class_body), (node.orelse, class_body))
        if isinstance(node, (ast.Try, ast.TryStar)):
            return (
                (node.body, class_body),
                *((handler.body, class_body) for handler in node.handlers),
                (node.orelse, class_body),
                (node.finalbody, class_body),
            )
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return ((node.body, class_body),)
        if isinstance(node, ast.ClassDef):
            return ((node.body, True),)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return ((node.body, False),)
        return ()

    def _statements(
        self, nodes: list[ast.stmt], *, class_body: bool = False
    ) -> tuple[Model, ...]:
        """Build statement blocks bottom-up without Python-stack recursion.

        Keep unsupported diagnostics pending until the enclosing statement has
        succeeded. This preserves the contract that an unsupported parent
        hides its entire subtree, while valid parents retain supported siblings.
        """
        blocks: dict[int, Model] = {}
        issues: dict[
            int, list[tuple[UnsupportedSyntaxError | ExternalModelingError, ast.AST]]
        ] = {}
        self._prebuilt_blocks = blocks
        try:
            pending: list[tuple[list[ast.stmt], bool, bool]] = [
                (nodes, class_body, False)
            ]
            while pending:
                group, in_class, ready = pending.pop()
                if not ready:
                    pending.append((group, in_class, True))
                    for statement in reversed(group):
                        children = self._child_blocks(statement, class_body=in_class)
                        pending.extend(
                            (child, child_class, False)
                            for child, child_class in reversed(children)
                        )
                    continue
                models: list[Model] = []
                block_issues: list[
                    tuple[UnsupportedSyntaxError | ExternalModelingError, ast.AST]
                ] = []
                for statement in group:
                    preflight = self.local_external_errors.get(id(statement), ())
                    if preflight:
                        block_issues.extend((error, statement) for error in preflight)
                        continue
                    accessed: list[int] = []
                    self._current_block_reads = accessed
                    try:
                        model = self.statement(statement, class_body=in_class)
                    except (UnsupportedSyntaxError, ExternalModelingError) as error:
                        if isinstance(error, ExternalModelingError) and (
                            self.on_external is None
                            or error.code not in _LOCAL_EXTERNAL_ERROR_CODES
                        ):
                            raise
                        block_issues.append((error, statement))
                    else:
                        models.append(model)
                        self.statement_models[id(statement)] = model
                        for child_id in accessed:
                            block_issues.extend(issues[child_id])
                    finally:
                        self._current_block_reads = None
                blocks[id(group)] = self.factory.make(
                    "model.statement.block", statements=tuple(models)
                )
                issues[id(group)] = block_issues
            root_issues = issues[id(nodes)]
            if root_issues:
                for error, statement in root_issues:
                    if isinstance(error, UnsupportedSyntaxError):
                        if self.on_unsupported is None:
                            raise error
                        self.on_unsupported(error, statement)
                    elif self.on_external is not None:
                        self.on_external(error, statement)
                    else:
                        raise error
            statements = blocks[id(nodes)].get("statements")
            return cast(tuple[Model, ...], statements)
        finally:
            self._prebuilt_blocks = None
            self._current_block_reads = None

    def module(self, tree: ast.Module, *, name: str = "<source>") -> Model:
        # Type comments are intentionally excluded when parsing the source;
        # annotations written as Python syntax are still modeled.
        return self.factory.make(
            "model.module", name=name, body=self._statements(tree.body)
        )

    def block(self, nodes: list[ast.stmt], *, class_body: bool = False) -> Model:
        if self._prebuilt_blocks is not None:
            cached = self._prebuilt_blocks[id(nodes)]
            if self._current_block_reads is not None:
                self._current_block_reads.append(id(nodes))
            return cached
        return self.factory.make(
            "model.statement.block",
            statements=self._statements(nodes, class_body=class_body),
        )

    def _function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, method: bool
    ) -> Model:
        if node.type_comment is not None:
            raise UnsupportedSyntaxError(node, "function type comment")

        if _has_own_yield(node):
            definition_kind = "model.definition.generator"
        elif method:
            definition_kind = "model.definition.method"
        else:
            definition_kind = "model.definition.function"
        return self.factory.make(
            definition_kind,
            span=_span(node),
            features=("async",) if isinstance(node, ast.AsyncFunctionDef) else (),
            name=node.name,
            parameters=self._parameters(node.args),
            type_parameters=self._type_parameters(getattr(node, "type_params", ())),
            decorators=tuple(self.expression(item) for item in node.decorator_list),
            returns=self.expression(node.returns) if node.returns is not None else None,
            body=self.block(node.body),
        )

    def _type_parameters(
        self, params: tuple[ast.AST, ...] | list[ast.AST]
    ) -> tuple[Model, ...]:
        """Preserve declared type parameter kinds, bounds and defaults as AST facts.

        Python 3.11 has no type-param nodes; 3.12 has no `default_value`.
        Neither a type parameter scope nor type evaluation is simulated.
        """
        f = self.factory
        models = []
        for param in params:
            name = getattr(param, "name", None)
            if not isinstance(name, str):
                raise UnsupportedSyntaxError(param, "invalid type parameter name")
            default = getattr(param, "default_value", None)
            value = self.expression(default) if default is not None else None
            kind = type(param).__name__
            if kind == "TypeVar":
                bound = getattr(param, "bound", None)
                models.append(
                    f.make(
                        "model.definition.type_parameter.type_variable",
                        span=_span(param),
                        name=name,
                        restriction=self.expression(bound)
                        if bound is not None
                        else None,
                        default=value,
                    )
                )
            elif kind in {"TypeVarTuple", "ParamSpec"}:
                models.append(
                    f.make(
                        "model.definition.type_parameter.type_variable_tuple"
                        if kind == "TypeVarTuple"
                        else "model.definition.type_parameter.parameter_specification",
                        span=_span(param),
                        name=name,
                        default=value,
                    )
                )
            else:
                raise UnsupportedSyntaxError(param)
        return tuple(models)

    @staticmethod
    def _parameter_expressions(args: ast.arguments) -> tuple[ast.expr, ...]:
        """List parameter annotations and defaults in modeling order."""
        positional = [*args.posonlyargs, *args.args]
        defaults: list[ast.expr | None] = [
            *([None] * (len(positional) - len(args.defaults))),
            *args.defaults,
        ]
        expressions: list[ast.expr] = []
        for arg, default in zip(positional, defaults, strict=True):
            if arg.annotation is not None:
                expressions.append(arg.annotation)
            if default is not None:
                expressions.append(default)
        if args.vararg is not None and args.vararg.annotation is not None:
            expressions.append(args.vararg.annotation)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            if arg.annotation is not None:
                expressions.append(arg.annotation)
            if default is not None:
                expressions.append(default)
        if args.kwarg is not None and args.kwarg.annotation is not None:
            expressions.append(args.kwarg.annotation)
        return tuple(expressions)

    def _parameters(
        self, args: ast.arguments, *, prebuilt: dict[ast.expr, Model] | None = None
    ) -> tuple[Model, ...]:
        """Share parameter shapes between definitions and iterative lambdas."""

        def modeled(expression: ast.expr) -> Model:
            return (
                self.expression(expression)
                if prebuilt is None
                else prebuilt.pop(expression)
            )

        def parameter(arg: ast.arg, category: str, default: ast.expr | None) -> Model:
            if arg.type_comment is not None:
                raise UnsupportedSyntaxError(arg, "parameter type comment")
            return self.factory.make(
                "model.definition.parameter",
                span=_span(arg),
                name=arg.arg,
                annotation=modeled(arg.annotation)
                if arg.annotation is not None
                else None,
                category=category,
                default=modeled(default) if default is not None else None,
            )

        positional = [*args.posonlyargs, *args.args]
        aligned_defaults: list[ast.expr | None] = [
            *([None] * (len(positional) - len(args.defaults))),
            *args.defaults,
        ]
        parameters = [
            parameter(
                arg,
                "positional_only"
                if i < len(args.posonlyargs)
                else "positional_or_keyword",
                aligned_defaults[i],
            )
            for i, arg in enumerate(positional)
        ]
        if args.vararg is not None:
            parameters.append(parameter(args.vararg, "var_positional", None))
        parameters.extend(
            parameter(arg, "keyword_only", default)
            for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
        )
        if args.kwarg is not None:
            parameters.append(parameter(args.kwarg, "var_keyword", None))
        return tuple(parameters)

    def pattern(self, node: ast.pattern) -> Model:
        """Model patterns in postorder without Python-stack recursion.

        A pattern nested in an alias, sequence, mapping, class or alternative
        is built only after its children. Expression-valued keys and class
        references still go through the expression builder.
        """
        f = self.factory
        pending: list[tuple[ast.pattern, bool]] = [(node, False)]
        built: dict[ast.pattern, Model] = {}
        while pending:
            current, ready = pending.pop()
            if not ready:
                if isinstance(current, ast.MatchAs):
                    children = (current.pattern,) if current.pattern is not None else ()
                elif isinstance(
                    current, (ast.MatchSequence, ast.MatchOr, ast.MatchMapping)
                ):
                    children = current.patterns
                elif isinstance(current, ast.MatchClass):
                    children = (*current.patterns, *current.kwd_patterns)
                elif isinstance(
                    current, (ast.MatchSingleton, ast.MatchValue, ast.MatchStar)
                ):
                    children = ()
                else:
                    raise UnsupportedSyntaxError(current)
                pending.append((current, True))
                pending.extend((child, False) for child in reversed(children))
                continue

            span = _span(current)
            if isinstance(current, ast.MatchValue):
                model = f.make(
                    "model.pattern.value",
                    span=span,
                    value=self.expression(current.value),
                )
            elif isinstance(current, ast.MatchSingleton):
                literal_kind = (
                    "model.value.literal.special.none"
                    if current.value is None
                    else "model.value.literal"
                )
                model = f.make(
                    "model.pattern.singleton",
                    span=span,
                    value=f.make(literal_kind, span=span, value=current.value),
                )
            elif isinstance(current, ast.MatchAs):
                if current.pattern is None:
                    model = (
                        f.make("model.pattern.wildcard", span=span)
                        if current.name is None
                        else f.make(
                            "model.pattern.capture", span=span, name=current.name
                        )
                    )
                else:
                    model = f.make(
                        "model.pattern.alias",
                        span=span,
                        pattern=built.pop(current.pattern),
                        name=current.name,
                    )
            elif isinstance(current, ast.MatchStar):
                model = f.make("model.pattern.star", span=span, name=current.name)
            elif isinstance(current, ast.MatchSequence):
                model = f.make(
                    "model.pattern.sequence",
                    span=span,
                    elements=tuple(built.pop(item) for item in current.patterns),
                )
            elif isinstance(current, ast.MatchMapping):
                model = f.make(
                    "model.pattern.mapping",
                    span=span,
                    entries=tuple(
                        f.make(
                            "model.structural_part.mapping_pattern_entry",
                            span=_span(key),
                            key=self.expression(key),
                            pattern=built.pop(pattern),
                        )
                        for key, pattern in zip(
                            current.keys, current.patterns, strict=True
                        )
                    ),
                    rest=current.rest,
                )
            elif isinstance(current, ast.MatchClass):
                model = f.make(
                    "model.pattern.class",
                    span=span,
                    type=self.expression(current.cls),
                    positional=tuple(built.pop(item) for item in current.patterns),
                    keywords=tuple(
                        f.make(
                            "model.structural_part.named_pattern",
                            name=name,
                            pattern=built.pop(item),
                        )
                        for name, item in zip(
                            current.kwd_attrs, current.kwd_patterns, strict=True
                        )
                    ),
                )
            elif isinstance(current, ast.MatchOr):
                model = f.make(
                    "model.pattern.alternative",
                    span=span,
                    alternatives=tuple(built.pop(item) for item in current.patterns),
                )
            else:
                raise UnsupportedSyntaxError(current)
            built[current] = model
        return built.pop(node)

    def _branch_path(
        self,
        *,
        condition: ast.expr | None = None,
        pattern: ast.pattern | None = None,
        guard: ast.expr | None = None,
        statements: list[ast.stmt],
        span: SourceSpan | None = None,
        class_body: bool = False,
    ) -> Model:
        return self.factory.make(
            "model.structural_part.branch_path",
            span=span,
            condition=self.expression(condition) if condition is not None else None,
            pattern=self.pattern(pattern) if pattern is not None else None,
            guard=self.expression(guard) if guard is not None else None,
            body=self.block(statements, class_body=class_body),
        )

    def _conditional_branch(self, node: ast.If, *, class_body: bool) -> Model:
        paths: list[Model] = []
        current = node
        while True:
            paths.append(
                self._branch_path(
                    condition=current.test,
                    statements=current.body,
                    span=_span(current),
                    class_body=class_body,
                )
            )
            # A same-indentation ast.If in orelse is written as `elif`;
            # a nested `else: if` remains a distinct Branch in the else path.
            if (
                len(current.orelse) == 1
                and isinstance(current.orelse[0], ast.If)
                and current.orelse[0].col_offset == current.col_offset
            ):
                current = current.orelse[0]
                continue
            if current.orelse:
                paths.append(
                    self._branch_path(statements=current.orelse, class_body=class_body)
                )
            break
        return self.factory.make(
            "model.statement.branch",
            span=_span(node),
            subject=None,
            paths=tuple(paths),
        )

    def _pattern_branch(self, node: ast.Match, *, class_body: bool) -> Model:
        return self.factory.make(
            "model.statement.branch",
            span=_span(node),
            subject=self.expression(node.subject),
            paths=tuple(
                self._branch_path(
                    pattern=item.pattern,
                    guard=item.guard,
                    statements=item.body,
                    span=_span(item),
                    class_body=class_body,
                )
                for item in node.cases
            ),
        )

    def _iteration(
        self, node: ast.For | ast.AsyncFor | ast.While, *, class_body: bool
    ) -> Model:
        if isinstance(node, (ast.For, ast.AsyncFor)):
            if node.type_comment is not None:
                raise UnsupportedSyntaxError(node, "loop type comment")
            binding = self.target(node.target)
            source = self.expression(node.iter)
            condition = None
        else:
            binding = None
            source = None
            condition = self.expression(node.test)
        return self.factory.make(
            "model.statement.control.iteration",
            span=_span(node),
            features=("async",) if isinstance(node, ast.AsyncFor) else (),
            binding=binding,
            source=source,
            condition=condition,
            body=self.block(node.body, class_body=class_body),
            else_block=self.block(node.orelse, class_body=class_body)
            if node.orelse
            else None,
        )

    def _exception_handling(
        self, node: ast.Try | ast.TryStar, *, class_body: bool
    ) -> Model:
        f = self.factory
        return f.make(
            "model.statement.control.exception_handling",
            span=_span(node),
            body=self.block(node.body, class_body=class_body),
            handlers=tuple(
                f.make(
                    "model.structural_part.exception_handler",
                    span=_span(handler),
                    exception=self.expression(handler.type)
                    if handler.type is not None
                    else None,
                    name=handler.name,
                    body=self.block(handler.body, class_body=class_body),
                )
                for handler in node.handlers
            ),
            else_block=self.block(node.orelse, class_body=class_body)
            if node.orelse
            else None,
            finally_block=self.block(node.finalbody, class_body=class_body)
            if node.finalbody
            else None,
            grouped=isinstance(node, ast.TryStar),
        )

    def target(self, node: ast.expr) -> Model:
        """Preserve target shapes with an iterative postorder traversal.

        Binding-role Tuple/List/Starred are distinct from value-role forms;
        Attribute and Subscript retain the expression builder's structure.
        """
        f = self.factory
        nested = (ast.Tuple, ast.List, ast.Starred)
        pending: list[tuple[ast.expr, bool]] = [(node, False)]
        built: dict[ast.expr, Model] = {}
        while pending:
            current, ready = pending.pop()
            if not isinstance(current, nested):
                built[current] = self.expression(current)
                continue
            if not ready:
                children = (
                    (current.value,)
                    if isinstance(current, ast.Starred)
                    else current.elts
                )
                pending.append((current, True))
                pending.extend((child, False) for child in reversed(children))
                continue
            if isinstance(current, ast.Starred):
                model = f.make(
                    "model.structural_part.starred_target",
                    span=_span(current),
                    value=built.pop(current.value),
                )
            else:
                model = f.make(
                    "model.structural_part.sequence_target",
                    span=_span(current),
                    spelling="tuple" if isinstance(current, ast.Tuple) else "list",
                    elements=tuple(built.pop(item) for item in current.elts),
                )
            built[current] = model
        return built.pop(node)

    def _context_block(
        self, node: ast.With | ast.AsyncWith, *, class_body: bool
    ) -> Model:
        """Keep each manager expression and optional binding in written order."""
        if node.type_comment is not None:
            raise UnsupportedSyntaxError(node, "with type comment")
        f = self.factory
        return f.make(
            "model.statement.control.context_block",
            span=_span(node),
            features=("async",) if isinstance(node, ast.AsyncWith) else (),
            contexts=tuple(
                f.make(
                    "model.structural_part.context_entry",
                    span=_span(item.context_expr),
                    expression=self.expression(item.context_expr),
                    target=self.target(item.optional_vars)
                    if item.optional_vars is not None
                    else None,
                )
                for item in node.items
            ),
            body=self.block(node.body, class_body=class_body),
        )

    def statement(self, node: ast.stmt, *, class_body: bool = False) -> Model:
        """Model a statement through baseline rules and internal AST refinements."""
        return build_statement(self, node, class_body=class_body)

    def expression(self, node: ast.expr) -> Model:
        """Build with the shared iterative engine and internal version refinements."""
        return build_expression(self, node)


def _external_settings(
    definitions: ModuleType | ExternalDefinitions | None,
    index: KindIndex | None,
) -> tuple[KindIndex, ExternalDefinitions | None]:
    if definitions is None:
        return index if index is not None else kind_index(), None
    if isinstance(definitions, ExternalDefinitions):
        if index is not None and index is not definitions.index:
            raise ValueError("index must be omitted when using compiled definitions")
        return definitions.index, definitions
    prepared = load_external_definitions(definitions, base=index)
    return prepared.index, prepared


def parse_source(
    source: str,
    *,
    filename: str = "<source>",
    index: KindIndex | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    import_policy: ImportPolicy = "unrestricted",
    allowed_modules: tuple[str, ...] = (),
    syntax_validation: SyntaxValidation = "compile",
) -> Model:
    """Model one source without execution; apply optional trusted descriptions."""
    selected_modules = _validated_import_options(import_policy, allowed_modules)
    _validated_syntax_validation(syntax_validation)
    resolved_index, prepared = _external_settings(definitions, index)
    tree = ast.parse(source, filename=filename, type_comments=False)
    _compile_check(tree, filename, syntax_validation)
    _assert_import_policy(
        tree, prepared, import_policy=import_policy, allowed_modules=selected_modules
    )
    syntax = collect_syntax_facts(tree, include_references=prepared is not None)
    matcher = _ExternalStructures.for_facts(syntax, prepared) if prepared else None
    return _Builder(
        resolved_index,
        external=matcher,
        collections=BuiltinCollectionRecognition(tree, syntax),
    ).module(tree)
