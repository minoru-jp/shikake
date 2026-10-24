"""AST-only registered call recognition. Source usage is not validated here.

External registrations select a specialized Model when a statically recognized
explicit import and argument shape match. All other usages remain ordinary
Python Models; caller policy belongs to the consumer.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from shikake.external import (
    CallMapping,
    ExternalDefinitions,
    GenericMapping,
    TypeMapping,
)

from .ast_facts import SyntaxFacts, explicit_import_path
from .builtin_collections import BuiltinCollectionRecognition
from .model import Model, ModelFactory


def _attribute_path(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _imported_aliases(
    facts: SyntaxFacts, definitions: ExternalDefinitions
) -> dict[str, str]:
    """Resolve only explicit, unconditional module-level import spellings.

    Conflicting introductions are deliberately not rejected. A conflicted
    alias is simply not eligible for specialized call recognition, while
    ordinary Name/Call Models and binding facts remain available.
    """
    targets = tuple(
        (mapping.target.dotted, mapping.target.path.partition(":")[0])
        for mapping in (
            *definitions.mappings,
            *definitions.type_mappings,
            *definitions.generic_mappings,
        )
    )
    aliases: dict[str, str] = {}
    conflicted: set[str] = set()
    for event in facts.events:
        if event.kind != "import" or event.scope is not facts.root or event.conditional:
            continue
        full_path = explicit_import_path(event)
        if full_path is None or not any(
            (target == full_path or target.startswith(full_path + "."))
            and (
                not isinstance(event.statement, ast.Import)
                or full_path == module
                or full_path.startswith(module + ".")
            )
            for target, module in targets
        ):
            continue
        # `import pkg.child` binds `pkg`, not `pkg.child`.
        qualified = (
            full_path.partition(".")[0]
            if isinstance(event.statement, ast.Import)
            and event.explicit_module is not None
            else full_path
        )
        previous = aliases.get(event.name)
        if previous is not None and previous != qualified:
            conflicted.add(event.name)
        elif event.name not in conflicted:
            aliases[event.name] = qualified
    # Competing imports of the same local spelling are not resolved by
    # guessing which one wins, even if the competing module is unregistered.
    for event in facts.events:
        if event.kind != "import" or event.scope is not facts.root:
            continue
        if event.name not in aliases:
            continue
        full_path = explicit_import_path(event)
        qualified = (
            full_path.partition(".")[0]
            if full_path is not None
            and isinstance(event.statement, ast.Import)
            and event.explicit_module is not None
            else full_path
        )
        if qualified != aliases[event.name]:
            conflicted.add(event.name)
    return {name: path for name, path in aliases.items() if name not in conflicted}


def _qualified_path(node: ast.AST, aliases: dict[str, str]) -> str | None:
    written = _attribute_path(node)
    if written is None:
        return None
    root, _, suffix = written.partition(".")
    imported = aliases.get(root)
    if imported is None:
        return None
    return f"{imported}.{suffix}" if suffix else imported


@dataclass(frozen=True, slots=True)
class _ExternalStructures:
    by_call: dict[str, CallMapping]
    by_type: dict[str, TypeMapping]
    by_generic: dict[str, GenericMapping]
    aliases: dict[str, str]
    lexical: BuiltinCollectionRecognition

    @classmethod
    def for_facts(
        cls,
        facts: SyntaxFacts,
        definitions: ExternalDefinitions,
    ) -> _ExternalStructures:
        aliases = _imported_aliases(facts, definitions)
        by_call = {item.target.dotted: item for item in definitions.mappings}
        by_type = {item.target.dotted: item for item in definitions.type_mappings}
        by_generic = {item.target.dotted: item for item in definitions.generic_mappings}
        tree = facts.root.node
        assert isinstance(tree, ast.Module)
        return cls(
            by_call,
            by_type,
            by_generic,
            aliases,
            BuiltinCollectionRecognition(tree, facts),
        )

    def _resolved_path(self, node: ast.AST) -> str | None:
        written = _attribute_path(node)
        if written is None:
            return None
        root = written.partition(".")[0]
        if self.lexical.shadows_registered_import(node, root):
            return None
        return _qualified_path(node, self.aliases)

    def mapping(self, call: ast.Call) -> CallMapping | None:
        path = self._resolved_path(call.func)
        return self.by_call.get(path) if path is not None else None

    def type_mapping(self, node: ast.expr) -> TypeMapping | None:
        path = self._resolved_path(node)
        return self.by_type.get(path) if path is not None else None

    def generic_mapping(self, node: ast.expr) -> GenericMapping | None:
        path = self._resolved_path(node)
        return self.by_generic.get(path) if path is not None else None

    @staticmethod
    def generic_arguments(node: ast.Subscript) -> tuple[ast.expr, ...] | None:
        """Only positional subscripts, not slices or starred expansions."""
        args = node.slice.elts if isinstance(node.slice, ast.Tuple) else (node.slice,)
        return (
            tuple(args)
            if all(
                isinstance(arg, ast.expr)
                and not isinstance(arg, (ast.Slice, ast.Starred))
                for arg in args
            )
            else None
        )

    def try_build_generic(
        self,
        node: ast.Subscript,
        mapping: GenericMapping,
        built: dict[ast.expr, Model],
        factory: ModelFactory,
    ) -> Model | None:
        arguments = self.generic_arguments(node)
        if arguments is None or len(arguments) != len(mapping.roles):
            return None
        # A tuple subscript is already built as a collection Model: extract
        # the argument Models rather than reconstructing an expression tree.
        if isinstance(node.slice, ast.Tuple):
            values = built[node.slice].get_nodes("inputs")
        else:
            values = (built[node.slice],)
        from .modeling.common import _span

        create = cast(Callable[..., Model], factory.make)
        result = create(
            mapping.kind_id,
            span=_span(node),
            **dict(zip(mapping.roles, values, strict=True)),
        )
        built.pop(node.value)
        built.pop(node.slice)
        return result

    def try_build(
        self,
        node: ast.Call,
        mapping: CallMapping,
        built: dict[ast.expr, Model],
        factory: ModelFactory,
        *,
        span: object,
    ) -> Model | None:
        """Match the complete call before consuming any prebuilt child Model.

        A non-matching registration is ordinary Python call syntax, not a
        source error or a diagnostic. Shape mismatches leave `built` intact.
        """
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            return None
        if len(node.args) > len(mapping.arguments):
            return None
        keywords: dict[str, ast.expr] = {}
        for keyword in node.keywords:
            if keyword.arg is None or keyword.arg in keywords:
                return None
            keywords[keyword.arg] = keyword.value
        allowed = {arg.keyword for arg in mapping.arguments}
        if any(name not in allowed for name in keywords):
            return None
        selected_arguments: dict[str, ast.expr] = {}
        for arg in mapping.arguments:
            positional = (
                node.args[arg.position] if arg.position < len(node.args) else None
            )
            keyword = keywords.get(arg.keyword)
            if (positional is None) == (keyword is None):
                return None
            selected = positional if positional is not None else keyword
            assert selected is not None
            selected_arguments[arg.role] = selected
        from .model import SourceSpan

        create = cast(Callable[..., Model], factory.make)
        result = create(
            mapping.kind_id,
            span=span if isinstance(span, SourceSpan) else None,
            **{role: built[child] for role, child in selected_arguments.items()},
        )
        for child in selected_arguments.values():
            built.pop(child)
        return result
