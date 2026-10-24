"""Scope-aware static facts shared by selected relationship analyzers.

No analyzed Python source is imported or executed. Facts represent written
bindings and declaration locations, not guaranteed runtime object identities.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias, cast

from shikake.external import ExternalDefinitions

from .ast_facts import SyntaxEvent, SyntaxFacts, SyntaxScope, explicit_import_path
from .builtin_names import BUILTIN_NAMES
from .external_structures import _ExternalStructures
from .lexical_scopes import binding_owner, visible_owners
from .model import Model


def _nodes(node: Model, role: str) -> tuple[Model, ...]:
    return node.get_nodes(role)


def _node(node: Model, role: str) -> Model:
    return node.get_node(role)


def _name(node: Model) -> str:
    return node.get_name("name")


def _resolved_module(
    module_name: str, *, is_package: bool, level: int, module: str | None
) -> str | None:
    """Resolve the *written* relative module path, not Python imports."""
    if level == 0:
        return module
    pkg = module_name if is_package else module_name.rpartition(".")[0]
    parts = pkg.split(".") if pkg else []
    if len(parts) < level:
        return None
    prefix = parts[: len(parts) - (level - 1)]
    return ".".join((*prefix, *((module or "").split(".") if module else ())))


@dataclass(frozen=True, slots=True)
class BindingState:
    """Syntactic properties of a name *within one module and lexical scope*.

    Conditional introductions are unstable; 'external' is a stable imported
    interface. The remaining flags are lightweight syntactic observations,
    not runtime guarantees. A false value-use flag does not prove absence.
    """

    introduction: Literal["stable", "unstable", "builtin", "external"]
    may_rebind: bool
    may_delete: bool
    may_value_use: bool


@dataclass(frozen=True, slots=True, eq=False)
class NameBinding:
    """Properties of a written name in a module or nested lexical scope.

    The owner Model identifies the declaration or module. A generic
    definition's annotation and body scopes can have the *same* owner Model;
    scope_kind distinguishes those separate lexical bindings. A None kind is
    reserved for caller-created records without a declared lexical kind.
    """

    module: str
    scope: Model
    name: str
    state: BindingState
    scope_kind: Literal["module", "class", "function", "annotation"] | None = None


@dataclass(frozen=True, slots=True)
class _UnknownBinding:
    reason: str
    possible: tuple[Model, ...] = ()
    # A conditional/repeated introduction may still name explicit imports.
    # Resolve these through the same path as an unconditional import, without
    # treating any branch as the selected runtime value.
    alternatives: tuple[_BaseBinding, ...] = ()


@dataclass(frozen=True, slots=True)
class _ExplicitModulePath:
    """A written dotted import, with only its syntactically imported tail.

    `import pkg.a.b` binds `pkg`, not `pkg.a.b`; following `a` and `b`
    consumes only that exact, explicit path. Other attributes may still be
    looked up in the currently named module's source, if it is available.
    """

    module: str
    remaining: tuple[str, ...]


_BaseBinding: TypeAlias = (
    Model | tuple[str, str] | _ExplicitModulePath | _UnknownBinding
)


def _known_models(binding: _BaseBinding | None) -> tuple[Model, ...]:
    if isinstance(binding, Model):
        return (binding,)
    if isinstance(binding, _UnknownBinding):
        return binding.possible
    return ()


@dataclass(frozen=True, slots=True)
class _BindingEvent:
    name: str
    value: _BaseBinding | None
    sequence: int
    conditional: bool
    source: Model | None = None
    operation: Literal[
        "import",
        "definition",
        "write",
        "augmented_write",
        "delete",
        "star",
        "annotation",
    ] = "write"
    declaration: bool = False
    repeatable: bool = False


@dataclass(slots=True, eq=False)
class _Scope:
    kind: Literal["module", "class", "function", "annotation"]
    parent: _Scope | None
    module: str
    events: dict[str, list[_BindingEvent]] = field(default_factory=dict)
    globals: set[str] = field(default_factory=set)
    nonlocals: set[str] = field(default_factory=set)
    model: Model | None = None
    value_uses: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class _DefinitionSite:
    module: str
    definition: Model
    scope: _Scope
    header_type_parameters: frozenset[str] = frozenset()
    sequence: int | None = None


@dataclass(slots=True)
class _FactIndex:
    """Single lexical event index for candidate lookup and local flags.

    No copied environment or per-definition binding snapshot is retained.
    """

    definitions: tuple[_DefinitionSite, ...]
    modules: Mapping[str, _Scope]
    scopes: tuple[_Scope, ...]
    class_scopes: Mapping[int, _Scope]
    attribute_changes: Mapping[str, frozenset[str]]
    external_targets: frozenset[str] = frozenset()

    def builtin_value_uses(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            (module, name)
            for module, root in self.modules.items()
            for name in root.value_uses & BUILTIN_NAMES
        )

    def changes_attribute(self, module: str, written_path: str) -> bool:
        return any(
            written_path == path or written_path.startswith(path + ".")
            for path in self.attribute_changes.get(module, ())
        )

    def bindings(self) -> tuple[NameBinding, ...]:
        records: list[NameBinding] = []
        for scope in self.scopes:
            if scope.model is None:
                continue
            for name in scope.events:
                state = self.state(scope, name)
                if state is not None:
                    records.append(
                        NameBinding(scope.module, scope.model, name, state, scope.kind)
                    )
        return tuple(records)

    def state(self, scope: _Scope, name: str) -> BindingState | None:
        """Report written operations, never possible execution paths.

        The first independent write introduces a name without counting as a
        rebind. Later or repeatable writes may rebind even when paths are not
        resolved. Augmented assignment reads an existing binding and cannot
        be an independent stable introduction.
        """
        owner = self._owner(scope, name)
        return self._state_from_events(owner, name, owner.events.get(name, ()))

    def _state_from_events(
        self,
        owner: _Scope,
        name: str,
        events: tuple[_BindingEvent, ...] | list[_BindingEvent],
    ) -> BindingState | None:
        """One syntactic classification shared by public facts and lookup."""
        introductions = [
            event for event in events if event.operation not in {"delete", "annotation"}
        ]
        # A built-in name is a *virtual* unconditional initial introduction at
        # module scope. A written module-level operation is therefore a possible
        # rebind (or deletion), not the first introduction. Local shadowing
        # remains a separate lexical binding with its ordinary state.
        if owner.kind == "module" and name in BUILTIN_NAMES:
            return BindingState(
                "builtin",
                bool(introductions),
                any(event.operation == "delete" for event in events),
                name in owner.value_uses,
            )
        if not introductions:
            return None
        first = introductions[0]
        stable = not (
            first.conditional
            or first.operation == "augmented_write"
            or any(self._ambiguous_package_import(event) for event in introductions)
        )
        external = (
            owner.kind == "module"
            and first.operation == "import"
            and isinstance(first.value, tuple)
            and bool(first.value[1])
            and any(
                target == f"{first.value[0]}.{first.value[1]}"
                or target.startswith(f"{first.value[0]}.{first.value[1]}.")
                for target in self.external_targets
            )
        )
        return BindingState(
            "unstable" if not stable else "external" if external else "stable",
            len(introductions) > 1
            or any(
                event.repeatable or event.operation == "augmented_write"
                for event in introductions
            ),
            any(event.operation == "delete" for event in events),
            name in owner.value_uses,
        )

    def _ambiguous_package_import(self, event: _BindingEvent) -> bool:
        """An importable submodule and a package binding share one name."""
        source = event.value
        return (
            event.operation == "import"
            and isinstance(source, tuple)
            and bool(source[1])
            and self.package_name_conflicts(source[0], source[1])
        )

    def package_name_conflicts(self, package: str, name: str) -> bool:
        """A written package export might compete with its child module.

        Only explicitly written bindings can conflict with a submodule.
        """
        root = self.modules.get(package)
        return (
            root is not None
            and f"{package}.{name}" in self.modules
            and name in root.events
        )

    @staticmethod
    def _locally_binds(scope: _Scope, name: str) -> bool:
        return name in scope.events

    def _owner(self, scope: _Scope, name: str) -> _Scope:
        return binding_owner(
            scope, name, self.modules[scope.module], self._locally_binds
        )

    def _visible_owners(self, site: _DefinitionSite, name: str):
        """Use the same scope visibility policy as Collection recognition."""
        return visible_owners(
            site.scope, name, self.modules[site.module], self._locally_binds
        )

    def reference_state(self, site: _DefinitionSite, name: str) -> BindingState | None:
        """Return root-name syntactic facts in its visible lexical scope."""
        if name in site.header_type_parameters:
            return BindingState("stable", False, False, False)
        for owner in self._visible_owners(site, name):
            events = owner.events.get(name, ())
            if any(event.operation != "annotation" for event in events):
                return self.state(owner, name)
            if owner.kind == "function" and events:
                # Annotation-only locals mask outer bindings, even though the
                # annotation supplies no binding state of its own.
                return None
            if owner.kind == "module" and name in BUILTIN_NAMES:
                return self.state(owner, name)
        return None

    def lookup(
        self,
        site: _DefinitionSite,
        name: str,
        _seen: set[tuple[str, str]] | None = None,
        *,
        local_only: bool = False,
    ) -> _BaseBinding:
        """Locate written candidates within the same lexical visibility rules.

        A declaration's own name is not a possible base of that declaration.
        Other declarations/imports with that spelling remain candidates; the
        complete syntactic BindingState stays independent of this exclusion.
        """
        if name in site.header_type_parameters:
            return _UnknownBinding("type_parameter")
        owners = (site.scope,) if local_only else self._visible_owners(site, name)
        for owner in owners:
            all_events = owner.events.get(name, ())
            # Only a base reference in the *same* lexical scope has a useful
            # written position relative to this introduction. A function's
            # later execution, or a different module's import, is not ordered
            # by comparing source offsets. This filter limits candidates; it
            # never changes the three whole-scope binding properties.
            cutoff = site.sequence if owner is site.scope else None
            state_events = tuple(
                event
                for event in all_events
                if not (event.declaration and event.value is site.definition)
            )
            all_introductions = tuple(
                event for event in state_events if event.operation != "annotation"
            )
            events = tuple(
                event
                for event in all_introductions
                if cutoff is None or event.sequence <= cutoff
            )
            if not events and all_introductions:
                return _UnknownBinding("later_introduction")
            if not events:
                if any(event.operation == "definition" for event in all_events):
                    return _UnknownBinding("self_definition")
                if owner.kind == "function" and all_events:
                    return _UnknownBinding("unbound_name")
                continue
            known = tuple(
                {
                    id(event.value): event.value
                    for event in events
                    if isinstance(event.value, Model)
                }.values()
            )
            import_candidates: tuple[_BaseBinding, ...] = tuple(
                event.value
                for event in events
                if isinstance(event.value, (tuple, _ExplicitModulePath))
            )
            # Later operations still contribute to whole-scope classification;
            # only candidate discovery is restricted by the written position.
            state = self._state_from_events(owner, name, state_events)
            if any(event.operation == "delete" for event in events):
                return _UnknownBinding("deleted_name", known, import_candidates)
            if state is not None and state.may_rebind:
                return _UnknownBinding("rebound_name", known, import_candidates)
            if state is not None and state.introduction == "unstable":
                # Preserve a written import for candidate resolution when its
                # *only* instability is a competing package attribute/module.
                # The BindingState independently remains unstable.
                if (
                    len(events) == 1
                    and not events[0].conditional
                    and self._ambiguous_package_import(events[0])
                ):
                    return events[0].value or _UnknownBinding("unbound_name")
                return _UnknownBinding("conditional_binding", known, import_candidates)
            if len(events) == 1:
                event = events[0]
                return event.value or _UnknownBinding("unbound_name")
            return _UnknownBinding("conditional_binding", known, import_candidates)
        return _UnknownBinding("unbound_name")

    def export(
        self,
        module: str,
        name: str,
        _seen: set[tuple[str, str]] | None = None,
    ) -> _BaseBinding:
        root = self.modules.get(module)
        if root is None:
            return _UnknownBinding("unresolved_import")
        seen = set() if _seen is None else set(_seen)
        key = (module, name)
        if key in seen:
            return _UnknownBinding("circular_import")
        seen.add(key)
        assert root.model is not None
        # A dynamic __all__ is deliberately not guessed for star expansion.
        return self.lookup(_DefinitionSite(module, root.model, root), name, seen)


def _reference_root(node: ast.Name | ast.Attribute) -> ast.Name | None:
    """Inspect a recorded maximal attribute chain without a second AST pass."""
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current if isinstance(current, ast.Name) else None


def _make_scopes(
    module_name: str,
    module: Model,
    facts: SyntaxFacts,
    modeled: Mapping[int, Model],
    roots: dict[str, _Scope],
    scopes: list[_Scope],
    class_scopes: dict[int, _Scope],
) -> dict[SyntaxScope, _Scope]:
    """Project existing AST scopes onto their Model owners."""
    local: dict[SyntaxScope, _Scope] = {}
    for lexical in facts.scopes:
        parent = local.get(lexical.parent) if lexical.parent is not None else None
        scope_model = (
            module if lexical.kind == "module" else modeled.get(id(lexical.node))
        )
        scope = _Scope(lexical.kind, parent, module_name, model=scope_model)
        scope.globals.update(lexical.globals)
        scope.nonlocals.update(lexical.nonlocals)
        local[lexical] = scope
        scopes.append(scope)
        if lexical.kind == "module":
            roots[module_name] = scope
        if lexical.kind == "class" and scope_model is not None:
            class_scopes[id(scope_model)] = scope
    return local


def _append_definition_sites(
    module_name: str,
    facts: SyntaxFacts,
    modeled: Mapping[int, Model],
    local: Mapping[SyntaxScope, _Scope],
    definitions: frozenset[str],
    sites: list[_DefinitionSite],
) -> None:
    for item in facts.definitions:
        definition = modeled.get(id(item.statement))
        if definition is not None and definition.kind.id in definitions:
            sites.append(
                _DefinitionSite(
                    module_name,
                    definition,
                    local[item.scope],
                    frozenset(
                        name
                        for parameter in getattr(item.statement, "type_params", ())
                        if isinstance(name := getattr(parameter, "name", None), str)
                    ),
                    item.sequence,
                )
            )


def _append_observed_uses(
    facts: SyntaxFacts,
    local: Mapping[SyntaxScope, _Scope],
    external_definitions: ExternalDefinitions | None,
    value_occurrences: list[tuple[_Scope, str, bool]],
) -> None:
    """Observe value-use hints in already collected AST occurrences.

    No new use tracking or flow analysis is performed. The shared expression
    index is cached by SyntaxFacts for all existing consumers.
    """
    expression_scopes, _, type_positions = facts.expression_scopes(
        cast(ast.Module, facts.root.node)
    )
    matcher = (
        _ExternalStructures.for_facts(facts, external_definitions)
        if external_definitions is not None
        else None
    )
    # Collect registered Generic slices first, then mark their descendants
    # in one walk. No reference needs to search an arbitrarily deep ancestry.
    generic_slices: set[ast.AST] = set()
    if matcher is not None:
        for reference, parent in facts.references:
            if (
                isinstance(parent, ast.Subscript)
                and parent.value is reference
                and matcher.generic_mapping(reference) is not None
            ):
                generic_slices.add(parent.slice)
    generic_arguments: set[ast.AST] = set()
    if generic_slices:
        pending = [(facts.root.node, False)]
        while pending:
            node, inside_generic = pending.pop()
            inside_generic = inside_generic or node in generic_slices
            if inside_generic:
                generic_arguments.add(node)
            pending.extend(
                (child, inside_generic) for child in ast.iter_child_nodes(node)
            )
    for reference, parent in facts.references:
        root_name = _reference_root(reference)
        if root_name is None or not isinstance(root_name.ctx, ast.Load):
            continue
        if reference in type_positions:
            continue
        if matcher is not None:
            if (
                isinstance(parent, ast.Call)
                and parent.func is reference
                and matcher.mapping(parent) is not None
            ):
                continue
            if (
                isinstance(parent, ast.Subscript)
                and parent.value is reference
                and matcher.generic_mapping(reference) is not None
            ):
                continue
            # Registered Generic arguments are interface syntax, not values.
            if reference in generic_arguments:
                continue
        current = local.get(expression_scopes.get(reference, facts.root))
        if current is not None:
            value_occurrences.append(
                (
                    current,
                    root_name.id,
                    isinstance(parent, ast.Call) and parent.func is reference,
                )
            )


def _imported_binding(
    event: SyntaxEvent,
    module_name: str,
    *,
    is_package: bool,
) -> _BaseBinding:
    """Resolve only the import path written in the Source, not its contents."""
    assert event.imported is not None
    written, imported = event.imported
    if written is None:
        return _UnknownBinding("unresolved_import")
    if written.startswith("."):
        level = len(written) - len(written.lstrip("."))
        source = _resolved_module(
            module_name,
            is_package=is_package,
            level=level,
            module=written[level:] or None,
        )
        return (
            (source, imported)
            if source is not None
            else _UnknownBinding("unresolved_import")
        )
    # `import pkg.a` binds `pkg`, but carries its explicit suffix; an alias
    # binds directly to the imported complete module instead.
    if event.explicit_module is not None:
        path = explicit_import_path(event)
        assert path is not None
        segments = path.split(".")
        return _ExplicitModulePath(segments[0], tuple(segments[1:]))
    return (written, imported)


def _append_written_events(
    module_name: str,
    is_package: bool,
    facts: SyntaxFacts,
    modeled: Mapping[int, Model],
    local: Mapping[SyntaxScope, _Scope],
    attributes: dict[str, set[str]],
) -> None:
    """Record operations already seen in AST; never reject their use."""
    for event in facts.events:
        if event.kind == "attribute_write" or event.kind == "attribute_delete":
            attributes.setdefault(module_name, set()).add(event.name)
            continue
        if event.kind == "star":
            # Keep the import Model, but infer no implicit bindings from `*`.
            continue
        # Incomplete inspection never reaches relationship analysis.
        statement = modeled.get(id(event.statement))
        if statement is None:
            continue
        scope = local[event.scope]
        value: _BaseBinding | None
        if event.kind == "import":
            value = _imported_binding(event, module_name, is_package=is_package)
        elif (
            event.kind == "definition"
            and statement.kind.id == "model.definition.class"
            and event.node is event.statement
        ):
            value = statement
        else:
            value = _UnknownBinding(
                "lexical_parameter"
                if event.kind == "parameter"
                else "unknown_written_value"
            )
        scope.events.setdefault(event.name, []).append(
            _BindingEvent(
                event.name,
                value,
                event.sequence,
                event.conditional,
                source=statement,
                operation="definition" if event.kind == "parameter" else event.kind,
                declaration=event.kind == "definition"
                and event.node is event.statement,
                repeatable=event.repeatable,
            )
        )


def _redistribute_declared_events(
    scopes: list[_Scope], roots: Mapping[str, _Scope]
) -> None:
    """Honor global/nonlocal against the *original* lexical name inventory."""
    local_names = {scope: frozenset(scope.events) for scope in scopes}

    def originally_binds(scope: _Scope, name: str) -> bool:
        return name in local_names[scope]

    for scope in scopes:
        for name in (*scope.globals, *scope.nonlocals):
            entries = scope.events.pop(name, ())
            if not entries:
                continue
            owner = binding_owner(scope, name, roots[scope.module], originally_binds)
            if owner is scope and name in scope.nonlocals:
                # Do not invent an owner for an unresolved nonlocal declaration.
                scope.events[name] = entries
                continue
            owner.events.setdefault(name, []).extend(
                _BindingEvent(
                    event.name,
                    event.value,
                    event.sequence,
                    True,
                    event.source,
                    event.operation,
                    event.declaration,
                    event.repeatable,
                )
                for event in entries
            )


def _mark_observed_value_uses(
    occurrences: list[tuple[_Scope, str, bool]], roots: Mapping[str, _Scope]
) -> None:
    """Record only observable uses after global/nonlocal ownership is known."""
    for scope, name, direct_call in occurrences:
        for owner in visible_owners(
            scope, name, roots[scope.module], lambda current, key: key in current.events
        ):
            if name in owner.events or (
                owner.kind == "module" and name in BUILTIN_NAMES
            ):
                if (
                    direct_call
                    and owner.kind == "module"
                    and name in BUILTIN_NAMES
                    and name not in owner.events
                ):
                    break  # A virtual builtin call is not a first-class value use.
                owner.value_uses.add(name)
                break


def _collect_facts(
    modules: dict[str, tuple[Model, bool]],
    syntax: Mapping[str, tuple[SyntaxFacts, Mapping[int, Model]]],
    *,
    definitions: frozenset[str] = frozenset({"model.definition.class"}),
    external_definitions: ExternalDefinitions | None = None,
) -> _FactIndex:
    """Project collected AST facts onto Model scopes without rescanning."""
    sites: list[_DefinitionSite] = []
    roots: dict[str, _Scope] = {}
    scopes: list[_Scope] = []
    class_scopes: dict[int, _Scope] = {}
    attributes: dict[str, set[str]] = {}
    value_occurrences: list[tuple[_Scope, str, bool]] = []
    targets = (
        frozenset(
            mapping.target.dotted
            for mapping in (
                *external_definitions.mappings,
                *external_definitions.type_mappings,
                *external_definitions.generic_mappings,
            )
        )
        if external_definitions is not None
        else frozenset()
    )
    for module_name, (module, is_package) in modules.items():
        facts, modeled = syntax[module_name]
        local = _make_scopes(
            module_name, module, facts, modeled, roots, scopes, class_scopes
        )
        _append_definition_sites(module_name, facts, modeled, local, definitions, sites)
        _append_observed_uses(facts, local, external_definitions, value_occurrences)
        _append_written_events(
            module_name, is_package, facts, modeled, local, attributes
        )

    # Both operations use the same collected events, never a second AST pass.
    _redistribute_declared_events(scopes, roots)
    _mark_observed_value_uses(value_occurrences, roots)
    for scope in scopes:
        for entries in scope.events.values():
            entries.sort(key=lambda event: event.sequence)
    return _FactIndex(
        tuple(sites),
        roots,
        tuple(scopes),
        class_scopes,
        {module: frozenset(paths) for module, paths in attributes.items()},
        targets,
    )
