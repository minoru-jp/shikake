"""Source and package inspection results with diagnostics and completeness.

Strict parse_* functions remain fail-fast. Inspection does not execute supplied
sources and never reports an omitted subtree as complete.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Literal

from shikake.external import ExternalDefinitions

from .ast_facts import SyntaxFacts, collect_syntax_facts
from .base_references import BaseReference
from .external_structures import ExternalModelingError, _ExternalStructures
from .import_policy import (
    ImportPolicy,
    _assert_import_policy,
    _validated_import_options,
)
from .kinds import KindIndex
from .model import Model, ModelFactory, SourceSpan
from .package import (
    OverrideCandidate,
    PackageModel,
    _analyze_package_facts,
    _module_identity,
    _package_paths,
    _selected_analyses,
)
from .parser import (
    SyntaxValidation,
    UnsupportedSyntaxError,
    _Builder,
    _compile_check,
    _external_settings,
    _span,
    _validated_syntax_validation,
)
from .relation_facts import NameBinding, _collect_facts

IssueCategory = Literal["unsupported_syntax", "syntax_error", "external_definition"]


@dataclass(frozen=True, slots=True)
class InspectionIssue:
    """What could not be modeled and which enclosing subtree was omitted.

    Line and column use the Python AST convention (one-based line, zero-based
    UTF-8 byte column). An unsupported expression may cause an entire containing
    statement to be omitted; skipped_span describes that statement.
    """

    category: IssueCategory
    filename: str
    node_type: str
    message: str
    line: int | None
    column: int | None
    skipped_node_type: str | None = None
    skipped_span: SourceSpan | None = None
    code: str = "diagnostic.unspecified"
    details: Mapping[str, str | int] = field(
        default_factory=lambda: MappingProxyType({}), hash=False
    )

    def __post_init__(self) -> None:
        # A frozen result must not retain a mutable caller-owned dict.
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))


@dataclass(frozen=True, slots=True)
class SourceInspection:
    """Model is None for syntax errors or file-wide external violations."""

    model: Model | None
    issues: tuple[InspectionIssue, ...]
    name_bindings: tuple[NameBinding, ...] = ()

    def __repr__(self) -> str:
        """Summarize binding counts, but retain full diagnostic details."""
        return (
            f"SourceInspection(model={self.model!r}, issues={self.issues!r}, "
            f"name_bindings=<{len(self.name_bindings)} items>)"
        )

    @property
    def complete(self) -> bool:
        return self.model is not None and not self.issues


@dataclass(frozen=True, slots=True)
class PackageInspection:
    """Incomplete packages have no asserted cross-module override candidates."""

    package: PackageModel
    issues: tuple[InspectionIssue, ...]

    @property
    def model(self) -> Model:
        return self.package.model

    @property
    def complete(self) -> bool:
        return not self.issues

    @property
    def override_candidates(self) -> tuple[OverrideCandidate, ...]:
        return self.package.override_candidates

    @property
    def base_references(self) -> tuple[BaseReference, ...]:
        """Written base references (empty for incomplete inspections)."""
        return self.package.base_references

    @property
    def analyses(self) -> frozenset[str]:
        """Actually completed analyses; empty when inspection is incomplete."""
        return self.package.analyses

    @property
    def name_bindings(self) -> tuple[NameBinding, ...]:
        """Name binding facts; empty when inspection is incomplete."""
        return self.package.name_bindings

    def walk(self) -> Iterator[Model]:
        return self.package.walk()


def _syntax_issue(
    error: SyntaxError, filename: str, *, compiler_error: bool = False
) -> InspectionIssue:
    # SyntaxError.offset is a 1-based character position, whereas AST columns
    # are 0-based UTF-8 byte offsets. Use the line provided by Python, which
    # also reflects the source encoding of files passed to ast.parse as bytes.
    column: int | None = None
    if error.offset is not None and error.offset > 0:
        if compiler_error:
            # CPython's AST compiler reports a 1-based UTF-8 byte offset,
            # often without SyntaxError.text. It is NOT a character index.
            column = error.offset - 1
        elif error.text is not None:
            column = len(error.text[: error.offset - 1].encode("utf-8"))
    return InspectionIssue(
        category="syntax_error",
        filename=filename,
        node_type=type(error).__name__,
        message=error.msg,
        line=error.lineno,
        column=column,
        code="syntax.invalid",
    )


def _local_external_errors(
    tree: ast.Module,
) -> tuple[
    dict[int, list[ExternalModelingError]],
    Callable[[ExternalModelingError, ast.AST], None],
]:
    """Prepare a source-ordered sink for errors scoped to one statement.

    Descend iteratively so deep ASTs do not exhaust Python's call stack.
    Structural errors without an enclosing statement must remain fatal.
    """
    enclosing: dict[int, ast.stmt] = {}
    pending: list[tuple[ast.AST, ast.stmt | None, ast.AST | None]] = [
        (tree, None, None)
    ]
    while pending:
        node, statement, parent = pending.pop()
        # An elif has no separate statement Model: its enclosing ast.If
        # is flattened into one branch Model. Skip that outer statement.
        is_elif = (
            isinstance(node, ast.If)
            and isinstance(parent, ast.If)
            and len(parent.orelse) == 1
            and parent.orelse[0] is node
            and parent.col_offset == node.col_offset
        )
        if isinstance(node, ast.stmt) and not is_elif:
            statement = node
        if statement is not None:
            enclosing[id(node)] = statement
        pending.extend((child, statement, node) for child in ast.iter_child_nodes(node))

    errors: dict[int, list[ExternalModelingError]] = {}

    def record(error: ExternalModelingError, node: ast.AST) -> None:
        statement = enclosing.get(id(node))
        if statement is None:
            raise error
        errors.setdefault(id(statement), []).append(error)

    return errors, record


def _inspect_tree(
    tree: ast.Module,
    *,
    index: KindIndex,
    filename: str,
    name: str,
    external: _ExternalStructures | None = None,
    statement_models: dict[int, Model] | None = None,
    local_external_errors: dict[int, list[ExternalModelingError]] | None = None,
) -> SourceInspection:
    issues: list[InspectionIssue] = []

    def record(error: UnsupportedSyntaxError, skipped: ast.AST) -> None:
        issues.append(
            InspectionIssue(
                category="unsupported_syntax",
                filename=filename,
                node_type=error.node_type,
                message=str(error),
                line=error.line,
                column=error.column,
                skipped_node_type=type(skipped).__name__,
                skipped_span=_span(skipped),
                code="syntax.unsupported",
                details=MappingProxyType({"node_type": error.node_type}),
            )
        )

    def record_external(error: ExternalModelingError, skipped: ast.AST) -> None:
        issues.append(
            InspectionIssue(
                category="external_definition",
                filename=filename,
                node_type=error.node_type,
                message=str(error),
                line=error.line,
                column=error.column,
                skipped_node_type=type(skipped).__name__,
                skipped_span=_span(skipped),
                code=error.code,
                details=error.details,
            )
        )

    builder = _Builder(
        index,
        on_unsupported=record,
        on_external=record_external,
        local_external_errors={
            key: tuple(value) for key, value in (local_external_errors or {}).items()
        },
        external=external,
    )
    model = builder.module(tree, name=name)
    if statement_models is not None:
        statement_models.update(builder.statement_models)
    return SourceInspection(model, tuple(issues))


def _external_issue(error: ExternalModelingError, filename: str) -> InspectionIssue:
    return InspectionIssue(
        "external_definition",
        filename,
        error.node_type,
        str(error),
        error.line,
        error.column,
        code=error.code,
        details=error.details,
    )


def inspect_source(
    source: str,
    *,
    filename: str = "<source>",
    index: KindIndex | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    import_policy: ImportPolicy = "unrestricted",
    allowed_modules: tuple[str, ...] = (),
    syntax_validation: SyntaxValidation = "compile",
) -> SourceInspection:
    """Return the modelable portions of one source plus omission diagnostics.

    Unsupported statements are skipped atomically, never hoisted from an
    unsupported enclosing construct. Other statements at the same level are
    visited. A syntax error prevents modeling this source, but is returned as
    a diagnostic instead of raising SyntaxError.
    """
    selected_modules = _validated_import_options(import_policy, allowed_modules)
    _validated_syntax_validation(syntax_validation)
    resolved_index, prepared = _external_settings(definitions, index)
    try:
        tree = ast.parse(source, filename=filename, type_comments=False)
    except SyntaxError as error:
        return SourceInspection(None, (_syntax_issue(error, filename),))
    try:
        _compile_check(tree, filename, syntax_validation)
    except SyntaxError as error:
        return SourceInspection(
            None, (_syntax_issue(error, filename, compiler_error=True),)
        )
    try:
        _assert_import_policy(
            tree,
            prepared,
            import_policy=import_policy,
            allowed_modules=selected_modules,
        )
        local_errors: dict[int, list[ExternalModelingError]] = {}
        matcher = None
        syntax = collect_syntax_facts(tree, include_references=prepared is not None)
        if prepared is not None:
            local_errors, record_local = _local_external_errors(tree)
            matcher = _ExternalStructures.for_facts(
                syntax, prepared, on_local_error=record_local
            )
        statement_models: dict[int, Model] = {}
        result = _inspect_tree(
            tree,
            index=resolved_index,
            filename=filename,
            name="<source>",
            external=matcher,
            statement_models=statement_models,
            local_external_errors=local_errors,
        )
        # Do not expose a partial binding index as if it were complete. Reuse
        # the same lexical fact index as package analysis, with no relation pass.
        if not result.complete or result.model is None:
            return result
        facts = _collect_facts(
            {"<source>": (result.model, False)},
            {"<source>": (syntax, statement_models)},
            definitions=frozenset(),
        )
        return SourceInspection(result.model, result.issues, facts.bindings())
    except ExternalModelingError as error:
        return SourceInspection(None, (_external_issue(error, filename),))


def inspect_package(
    directory: str | Path,
    *,
    index: KindIndex | None = None,
    analyses: Iterable[str] | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    include: Callable[[Path, bool], bool] | None = None,
    extensions: tuple[str, ...] = (".py",),
    import_policy: ImportPolicy = "unrestricted",
    allowed_modules: tuple[str, ...] = (),
    syntax_validation: SyntaxValidation = "compile",
) -> PackageInspection:
    """Inspect each module independently; keep other modules on syntax errors.

    Selected regular files with requested suffixes are inspected, regardless
    of __init__ files. Symlinks are not followed; include selects matching
    files and prunes subdirectories. Invalid roots, I/O errors, and Model
    contract bugs remain fatal. Incomplete packages have no override candidates, because
    omitted definitions may otherwise produce misleading matches.
    """
    selected = _selected_analyses(analyses)
    selected_modules = _validated_import_options(import_policy, allowed_modules)
    _validated_syntax_validation(syntax_validation)
    folder, paths = _package_paths(directory, include=include, extensions=extensions)
    resolved_index, prepared = _external_settings(definitions, index)
    modules: dict[str, tuple[Model, bool]] = {}
    source_facts: dict[str, tuple[SyntaxFacts, dict[int, Model]]] = {}
    issues: list[InspectionIssue] = []
    for path in paths:
        module_name, is_init = _module_identity(folder, path)
        try:
            tree = ast.parse(path.read_bytes(), filename=str(path), type_comments=False)
        except SyntaxError as error:
            issues.append(_syntax_issue(error, str(path)))
            continue
        try:
            _compile_check(tree, str(path), syntax_validation)
        except SyntaxError as error:
            issues.append(_syntax_issue(error, str(path), compiler_error=True))
            continue
        try:
            _assert_import_policy(
                tree,
                prepared,
                import_policy=import_policy,
                allowed_modules=selected_modules,
            )
            syntax = collect_syntax_facts(tree, include_references=prepared is not None)
            local_errors: dict[int, list[ExternalModelingError]] = {}
            matcher = None
            if prepared is not None:
                local_errors, record_local = _local_external_errors(tree)
                matcher = _ExternalStructures.for_facts(
                    syntax, prepared, on_local_error=record_local
                )
            statement_models: dict[int, Model] = {}
            result = _inspect_tree(
                tree,
                index=resolved_index,
                filename=str(path),
                name=module_name,
                external=matcher,
                statement_models=statement_models,
                local_external_errors=local_errors,
            )
        except ExternalModelingError as error:
            issues.append(_external_issue(error, str(path)))
            continue
        issues.extend(result.issues)
        if result.model is None:
            raise AssertionError("AST-based inspection must produce a module model")
        modules[module_name] = (result.model, is_init)
        source_facts[module_name] = (syntax, statement_models)

    root = ModelFactory(resolved_index).make(
        "model.package",
        name=folder.name,
        modules=tuple(module for module, _ in modules.values()),
    )
    candidates, bases, bindings = (
        _analyze_package_facts(modules, selected, source_facts)
        if not issues
        else ((), (), ())
    )
    return PackageInspection(
        PackageModel(
            root,
            candidates,
            bases,
            selected if not issues else frozenset(),
            bindings,
        ),
        tuple(issues),
    )
