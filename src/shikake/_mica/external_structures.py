"""Strict AST-only external structure usage and call-model application.

Only explicit, unconditional module-level imports activate a declaration;
imports of protected structures in other positions are rejected. A declared
structure (and any written descendant) may be called only through a registered
CallMapping, never used as an ordinary value, alias, assignment or deletion target. Nothing is
imported or evaluated from the analyzed source.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from shikake.external import CallMapping, ExternalDefinitions

from .ast_facts import SyntaxEvent, SyntaxFacts, explicit_import_path
from .model import Model, ModelFactory

# Only these errors can be confined to one syntactic statement in Partial
# inspection. All other external violations remain file-wide failures.
_LOCAL_EXTERNAL_ERROR_CODES = frozenset(
    {
        "external.unregistered_call",
        "external.interface_value",
        "external.too_many_positional",
        "external.starred_positional",
        "external.keyword_arguments",
        "external.unknown_keyword",
        "external.argument_mismatch",
    }
)


class ExternalModelingError(ValueError):
    """A registered external structure cannot be applied unambiguously."""

    def __init__(
        self,
        message: str,
        node: ast.AST,
        *,
        code: str = "external.definition_error",
        details: Mapping[str, str | int] | None = None,
    ) -> None:
        self.code = code
        self.details: Mapping[str, str | int] = MappingProxyType(dict(details or {}))
        self.node_type = type(node).__name__
        self.line = getattr(node, "lineno", None)
        self.column = getattr(node, "col_offset", None)
        super().__init__(message)


def _attribute_path(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _registered_import_path(
    event: SyntaxEvent,
    modules: frozenset[str],
    structures: frozenset[str],
) -> str | None:
    """Match only explicitly written paths leading to protected structures.

    A star import from a registered module cannot establish which protected
    names it exposes, so it cannot activate safe structure references.
    """
    if event.kind == "star":
        if event.imported is None:
            return None
        module, _ = event.imported
        return (
            module
            if module in modules
            and any(root.startswith(module + ".") for root in structures)
            else None
        )
    full_path = explicit_import_path(event)
    if full_path is None:
        return None
    if any(
        (full_path == module or full_path.startswith(module + "."))
        and any(
            root == full_path or root.startswith(full_path + ".") for root in structures
        )
        for module in modules
    ):
        return full_path
    return None


def _imported_aliases(
    facts: SyntaxFacts, definitions: ExternalDefinitions
) -> dict[str, str]:
    """Activate structures only through fully written, relevant import paths.

    Multiple plain `import package.child` statements bind the *same* package
    root, so they are complementary, not conflicting alias introductions.
    `import package` alone never supplies an unwritten child module.
    """
    modules = frozenset(
        item.target.path.partition(":")[0] for item in definitions.mappings
    )
    structures = frozenset(
        item.target.dotted.rpartition(".")[0] for item in definitions.mappings
    )
    result: dict[str, str] = {}
    root_imports: set[str] = set()
    for event in facts.events:
        full_path = _registered_import_path(event, modules, structures)
        if full_path is None:
            continue
        if event.kind == "star":
            raise ExternalModelingError(
                f"wildcard import from registered external module: {full_path}",
                event.statement,
                code="external.registered_star_import",
                details={"path": full_path},
            )
        if event.scope is not facts.root or event.conditional:
            raise ExternalModelingError(
                f"registered external import must be unconditional at module level: "
                f"{full_path}",
                event.statement,
                code="external.import_scope",
                details={"path": full_path},
            )
        plain_root = (
            isinstance(event.statement, ast.Import)
            and event.explicit_module is not None
        )
        # Only a plain dotted import binds the first segment rather than the
        # complete explicit path. All other aliases bind that full path.
        qualified = full_path.partition(".")[0] if plain_root else full_path
        # A plain dotted import binds only the root, not the full path.
        if event.name in result:
            if (
                event.name not in root_imports
                or not plain_root
                or result[event.name] != qualified
            ):
                raise ExternalModelingError(
                    f"repeated or conflicting external import: {event.name}",
                    event.statement,
                    code="external.import_conflict",
                    details={"name": event.name},
                )
            continue
        result[event.name] = qualified
        if plain_root:
            root_imports.add(event.name)
    return result


def _qualified_path(node: ast.AST, aliases: dict[str, str]) -> str | None:
    written = _attribute_path(node)
    if written is None:
        return None
    root, _, suffix = written.partition(".")
    imported = aliases.get(root)
    if imported is None:
        return None
    return f"{imported}.{suffix}" if suffix else imported


def _protected_path(
    node: ast.AST, aliases: dict[str, str], structures: frozenset[str]
) -> tuple[str, bool] | None:
    """Recognize structure/namespace refs using only their written AST paths.

    The returned bool is true for a structural root or a descendant. An
    imported *namespace prefix* is protected against value extraction but is
    not itself an admissible structure call.
    """
    written = _attribute_path(node)
    if written is None:
        return None
    path = _qualified_path(node, aliases)
    if path is None:
        return None
    if any(path == root or path.startswith(root + ".") for root in structures):
        return written, True
    if any(root.startswith(path + ".") for root in structures):
        return written, False
    return None


def _assert_reserved_bindings(
    facts: SyntaxFacts,
    aliases: dict[str, str],
    structures: frozenset[str],
    registered_calls: frozenset[str],
    *,
    on_local_error: Callable[[ExternalModelingError, ast.AST], None] | None = None,
) -> None:
    if not aliases:
        return
    reserved = set(aliases)
    allowed_imports = {
        id(event.node)
        for event in facts.events
        if event.scope is facts.root
        and not event.conditional
        and event.kind == "import"
        and event.name in aliases
        and (
            # The alias's registered introduction, including multiple dotted
            # imports that explicitly bind the same package root.
            (
                isinstance(event.statement, ast.Import)
                and event.explicit_module is not None
                and aliases[event.name] == event.name
            )
            or (
                explicit_import_path(event) == aliases[event.name]
                and event.explicit_module is None
            )
            # A plain `import framework` following `import framework.memory`
            # is another syntactic import of the same root object, not a
            # distinct alias to an unrelated module.
            or (
                isinstance(event.statement, ast.Import)
                and event.explicit_module is None
                and event.imported == (event.name, "")
                and aliases[event.name] == event.name
            )
        )
    }
    for event in facts.events:
        if event.kind == "star":
            raise ExternalModelingError(
                "wildcard import may shadow a reserved external name",
                event.statement,
                code="external.wildcard_shadow",
            )
        if event.name in reserved and id(event.node) not in allowed_imports:
            raise ExternalModelingError(
                f"reserved external name rebound: {event.name}",
                event.node,
                code="external.reserved_name_rebound",
                details={"name": event.name},
            )
    for name, node in facts.special_bindings:
        if name in reserved:
            raise ExternalModelingError(
                f"reserved external name used as binding: {name}",
                node,
                code="external.reserved_name_binding",
                details={"name": name},
            )
    for node, parent in facts.references:
        protected = _protected_path(node, aliases, structures)
        if protected is not None:
            written, is_structure = protected
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                raise ExternalModelingError(
                    f"reserved external interface modified: {written}",
                    node,
                    code="external.interface_modified",
                    details={"target": written},
                )
            if isinstance(node.ctx, ast.Load):
                if not (
                    is_structure
                    and isinstance(parent, ast.Call)
                    and parent.func is node
                ):
                    error = ExternalModelingError(
                        f"external structure used as a value: {written}",
                        node,
                        code="external.interface_value",
                        details={"target": written},
                    )
                    if on_local_error is None:
                        raise error
                    on_local_error(error, node)
                # A call is allowed only when its full written path appears
                # in the trusted registration. No generic Call fallback.
                if _qualified_path(node, aliases) not in registered_calls:
                    error = ExternalModelingError(
                        f"unregistered external structure call: {written}",
                        node,
                        code="external.unregistered_call",
                        details={"target": written},
                    )
                    if on_local_error is None:
                        raise error
                    on_local_error(error, node)
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node.id in reserved
        ):
            raise ExternalModelingError(
                f"reserved external name rebound: {node.id}",
                node,
                code="external.reserved_name_rebound",
                details={"name": node.id},
            )


@dataclass(frozen=True, slots=True)
class _ExternalStructures:
    by_call: dict[str, CallMapping]
    aliases: dict[str, str]

    @classmethod
    def for_facts(
        cls,
        facts: SyntaxFacts,
        definitions: ExternalDefinitions,
        *,
        on_local_error: Callable[[ExternalModelingError, ast.AST], None] | None = None,
    ) -> _ExternalStructures:
        index = facts
        aliases = _imported_aliases(index, definitions)
        # Each ImportedCall describes a method on a structural root.  All
        # descendants of that root are structural, not only mapped methods.
        structures = frozenset(
            mapping.target.dotted.rpartition(".")[0]
            for mapping in definitions.mappings
            if isinstance(mapping, CallMapping)
        )
        by_call = {item.target.dotted: item for item in definitions.mappings}
        _assert_reserved_bindings(
            index,
            aliases,
            structures,
            frozenset(by_call),
            on_local_error=on_local_error,
        )
        return cls(by_call, aliases)

    def _resolved_path(self, node: ast.AST) -> str | None:
        return _qualified_path(node, self.aliases)

    def mapping(self, call: ast.Call) -> CallMapping | None:
        path = self._resolved_path(call.func)
        return self.by_call.get(path) if path is not None else None

    def build(
        self,
        node: ast.Call,
        mapping: CallMapping,
        built: dict[ast.expr, Model],
        factory: ModelFactory,
        *,
        span: object,
    ) -> Model:
        """Use only statically visible arguments, consuming each mapped node once."""
        # Report the written path, even when an import alias was used. This is
        # the source spelling users can locate in the diagnostic.
        target = _attribute_path(node.func) or mapping.target.dotted
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            raise ExternalModelingError(
                "expanded positional argument in external structure call",
                node,
                code="external.starred_positional",
                details={"target": target},
            )
        if len(node.args) > len(mapping.arguments):
            raise ExternalModelingError(
                "too many positional arguments in external structure call",
                node,
                code="external.too_many_positional",
                details={
                    "target": target,
                    "expected_count": len(mapping.arguments),
                    "actual_count": len(node.args),
                },
            )
        keywords: dict[str, ast.expr] = {}
        for kw in node.keywords:
            if kw.arg is None or kw.arg in keywords:
                details: dict[str, str | int] = {"target": target}
                if kw.arg is not None:
                    details["keyword"] = kw.arg
                raise ExternalModelingError(
                    "expanded or duplicate keyword argument",
                    node,
                    code="external.keyword_arguments",
                    details=details,
                )
            keywords[kw.arg] = kw.value
        allowed = {arg.keyword for arg in mapping.arguments}
        unknown = next((name for name in keywords if name not in allowed), None)
        if unknown is not None:
            raise ExternalModelingError(
                "unknown keyword in external structure call",
                node,
                code="external.unknown_keyword",
                details={"target": target, "keyword": unknown},
            )
        values: dict[str, Model] = {}
        for arg in mapping.arguments:
            positional = (
                node.args[arg.position] if arg.position < len(node.args) else None
            )
            keyword = keywords.get(arg.keyword)
            if (positional is None) == (keyword is None):
                raise ExternalModelingError(
                    f"missing or duplicate argument: {arg.keyword}",
                    node,
                    code="external.argument_mismatch",
                    details={"target": target, "keyword": arg.keyword},
                )
            selected = positional if positional is not None else keyword
            assert selected is not None
            values[arg.role] = built.pop(selected)
        # Other prebuilt expression children are discarded with the caller's
        # worklist. The callable itself is not modeled as a generic call node.
        from .model import SourceSpan

        create = cast(Callable[..., Model], factory.make)
        return create(
            mapping.kind_id,
            span=span if isinstance(span, SourceSpan) else None,
            **values,
        )
