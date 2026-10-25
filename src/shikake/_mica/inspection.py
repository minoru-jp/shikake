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

from .ast_facts import SyntaxFacts
from .base_references import BaseReference
from .builtin_names import BUILTIN_NAMES
from .import_policy import ImportPolicy, ImportPolicyError
from .kinds import DefinitionIndex
from .model import Model, ModelFactory, SourceSpan
from .package import (
    OverrideCandidate,
    PackageModel,
    _analyze_package_facts,
    _ModelIdentity,
    _module_identity,
    _package_paths,
    _selected_analyses,
)
from .parser import (
    SyntaxValidation,
    UnsupportedSyntaxError,
    _build_module,
    _external_settings,
    _modeling_context,
    _ModelingContext,
    _prepare_source,
    _span,
    _validated_syntax_validation,
)
from .relation_facts import BindingState, NameBinding, _collect_facts

IssueCategory = Literal[
    "unsupported_syntax",
    "syntax_error",
    "import_policy",
]


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
    """Model is None when syntax validation fails."""

    model: Model | None
    issues: tuple[InspectionIssue, ...]
    name_bindings: tuple[NameBinding, ...] = ()
    _builtin_value_names: frozenset[str] = field(
        default_factory=frozenset, repr=False, compare=False
    )
    _binding_index: dict[tuple[_ModelIdentity, str], tuple[NameBinding, ...]] | None = (
        field(default=None, init=False, repr=False, compare=False)
    )

    def bindings_for(self, scope: Model, name: str) -> tuple[NameBinding, ...]:
        """Query written facts for a Model owner or a virtual module built-in.

        A generic definition Model may own both annotation and body lexical
        scopes; distinguish the returned bindings by their scope_kind.
        Incomplete inspection never asserts virtual binding facts.
        """
        if not self.complete:
            return ()
        index = self._binding_index
        if index is None:
            entries: dict[tuple[_ModelIdentity, str], list[NameBinding]] = {}
            for fact in self.name_bindings:
                entries.setdefault((_ModelIdentity(fact.scope), fact.name), []).append(
                    fact
                )
            index = {key: tuple(value) for key, value in entries.items()}
            object.__setattr__(self, "_binding_index", index)
        written = index.get((_ModelIdentity(scope), name), ())
        if written:
            return written
        if scope is self.model and name in BUILTIN_NAMES:
            virtual = (
                NameBinding(
                    "<source>",
                    scope,
                    name,
                    BindingState(
                        "builtin",
                        False,
                        False,
                        name in self._builtin_value_names,
                    ),
                    "module",
                ),
            )
            index[(_ModelIdentity(scope), name)] = virtual
            return virtual
        return ()

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


def _inspect_tree(
    tree: ast.Module,
    *,
    index: DefinitionIndex,
    filename: str,
    name: str,
    context: _ModelingContext,
    statement_models: dict[int, Model] | None = None,
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

    model, built_statements = _build_module(
        tree, index, context, name=name, on_unsupported=record
    )
    if statement_models is not None:
        statement_models.update(built_statements)
    return SourceInspection(model, tuple(issues))


def _import_policy_issue(error: ImportPolicyError, filename: str) -> InspectionIssue:
    return InspectionIssue(
        "import_policy",
        filename,
        error.node_type,
        str(error),
        error.line,
        error.column,
        code=error.code,
    )


def inspect_source(
    source: str,
    *,
    filename: str = "<source>",
    index: DefinitionIndex | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    syntax_validation: SyntaxValidation = "compile",
    import_policy: ImportPolicy | None = None,
) -> SourceInspection:
    """Return the modelable portions of one source plus omission diagnostics.

    Unsupported statements are skipped atomically, never hoisted from an
    unsupported enclosing construct. Other statements at the same level are
    visited. A syntax error prevents modeling this source, but is returned as
    a diagnostic instead of raising SyntaxError.
    """
    _validated_syntax_validation(syntax_validation)
    resolved_index, prepared = _external_settings(definitions, index)
    prepared_source = _prepare_source(
        source, filename, syntax_validation, import_policy
    )
    if prepared_source.error is not None:
        error = prepared_source.error
        issue = (
            _import_policy_issue(error, filename)
            if isinstance(error, ImportPolicyError)
            else _syntax_issue(
                error, filename, compiler_error=prepared_source.phase == "compile"
            )
        )
        return SourceInspection(None, (issue,))
    tree = prepared_source.tree
    assert tree is not None
    context = _modeling_context(tree, prepared)
    statement_models: dict[int, Model] = {}
    result = _inspect_tree(
        tree,
        index=resolved_index,
        filename=filename,
        name="<source>",
        context=context,
        statement_models=statement_models,
    )
    # Do not expose a partial binding index as if it were complete. Reuse
    # the same lexical fact index as package analysis, with no relation pass.
    if not result.complete or result.model is None:
        return result
    facts = _collect_facts(
        {"<source>": (result.model, False)},
        {"<source>": (context.syntax, statement_models)},
        definitions=frozenset(),
        external_definitions=prepared,
    )
    return SourceInspection(
        result.model,
        result.issues,
        facts.bindings(),
        frozenset(name for module, name in facts.builtin_value_uses()),
    )


def inspect_package(
    directory: str | Path,
    *,
    index: DefinitionIndex | None = None,
    analyses: Iterable[str] | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    include: Callable[[Path, bool], bool] | None = None,
    extensions: tuple[str, ...] = (".py",),
    syntax_validation: SyntaxValidation = "compile",
    import_policy: ImportPolicy | None = None,
) -> PackageInspection:
    """Inspect each module independently; keep other modules on syntax errors.

    Selected regular files with requested suffixes are inspected, regardless
    of __init__ files. Symlinks are not followed; include selects matching
    files and prunes subdirectories. Invalid roots, I/O errors, and Model
    contract bugs remain fatal. Incomplete packages have no override candidates, because
    omitted definitions may otherwise produce misleading matches.
    """
    selected = _selected_analyses(analyses)
    _validated_syntax_validation(syntax_validation)
    folder, paths = _package_paths(directory, include=include, extensions=extensions)
    resolved_index, prepared = _external_settings(definitions, index)
    modules: dict[str, tuple[Model, bool]] = {}
    source_facts: dict[str, tuple[SyntaxFacts, dict[int, Model]]] = {}
    issues: list[InspectionIssue] = []
    for path in paths:
        module_name, is_init = _module_identity(folder, path)
        prepared_source = _prepare_source(
            path.read_bytes(), str(path), syntax_validation, import_policy
        )
        if prepared_source.error is not None:
            error = prepared_source.error
            issues.append(
                _import_policy_issue(error, str(path))
                if isinstance(error, ImportPolicyError)
                else _syntax_issue(
                    error,
                    str(path),
                    compiler_error=prepared_source.phase == "compile",
                )
            )
            continue
        tree = prepared_source.tree
        assert tree is not None
        context = _modeling_context(tree, prepared)
        statement_models: dict[int, Model] = {}
        result = _inspect_tree(
            tree,
            index=resolved_index,
            filename=str(path),
            name=module_name,
            context=context,
            statement_models=statement_models,
        )
        issues.extend(result.issues)
        if result.model is None:
            raise AssertionError("AST-based inspection must produce a module model")
        modules[module_name] = (result.model, is_init)
        source_facts[module_name] = (context.syntax, statement_models)

    root = ModelFactory(resolved_index).make(
        "model.package",
        name=folder.name,
        modules=tuple(module for module, _ in modules.values()),
    )
    builtin_values: set[tuple[str, str]] = set()
    candidates, bases, bindings = (
        _analyze_package_facts(
            modules,
            selected,
            source_facts,
            builtin_value_sink=builtin_values,
            external_definitions=prepared,
        )
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
            _builtin_value_uses=frozenset(builtin_values),
            _complete=not issues,
        ),
        tuple(issues),
    )
