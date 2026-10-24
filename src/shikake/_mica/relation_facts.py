"""Scope-aware static facts shared by selected relationship analyzers.

No analyzed Python source is imported or executed. Facts represent written
bindings and declaration locations, not guaranteed runtime object identities.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .ast_facts import SyntaxFacts, SyntaxScope, explicit_import_path
from .builtin_names import BUILTIN_NAMES
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

    A conditional first introduction is unstable. Modification flags describe
    additional or repeatable operations, not guaranteed runtime execution.
    """

    introduction: Literal["stable", "unstable", "builtin"]
    may_rebind: bool
    may_delete: bool


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
    stars: list[_BindingEvent] = field(default_factory=list)
    globals: set[str] = field(default_factory=set)
    nonlocals: set[str] = field(default_factory=set)
    model: Model | None = None


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

    def changes_attribute(self, module: str, written_path: str) -> bool:
        return any(
            written_path == path or written_path.startswith(path + ".")
            for path in self.attribute_changes.get(module, ())
        )

    def builtin_star_conflicts(self) -> frozenset[tuple[str, str]]:
        """Possible module-level wildcard writes to interpreter built-in names.

        Only modules with star imports pay for this finite check. Query-time
        synthesized bindings therefore agree with the shared AST fact rules.
        """
        return frozenset(
            (module, name)
            for module, root in self.modules.items()
            if root.stars
            for name in BUILTIN_NAMES
            if any(self._star_may_write(event, name) for event in root.stars)
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
                bool(introductions)
                or any(self._star_may_write(item, name) for item in owner.stars),
                any(event.operation == "delete" for event in events),
            )
        if not introductions:
            return None
        return BindingState(
            "unstable"
            if introductions[0].conditional
            or introductions[0].operation == "augmented_write"
            or any(self._ambiguous_package_import(event) for event in introductions)
            else "stable",
            len(introductions) > 1
            or any(
                event.repeatable or event.operation == "augmented_write"
                for event in introductions
            )
            or any(self._star_may_write(item, name) for item in owner.stars),
            any(event.operation == "delete" for event in events),
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

        Used by both root-name stability and target resolution. A star import
        only supplies a *possibility*, not an invented BindingState for names.
        """
        root = self.modules.get(package)
        return (
            root is not None
            and f"{package}.{name}" in self.modules
            and (
                name in root.events
                or any(self._star_may_write(item, name) for item in root.stars)
            )
        )

    def _star_may_write(self, event: _BindingEvent, name: str) -> bool:
        source = event.value
        if not isinstance(source, tuple) or source[0] not in self.modules:
            return True
        root = self.modules[source[0]]
        if "__all__" in root.events:
            return True  # Unknown exports, including dynamically built __all__.
        if name.startswith("_"):
            return False
        # Do not recursively resolve export chains merely to decide whether a
        # star import *might* shadow the name. This also handles cyclic stars.
        return name in root.events or bool(root.stars)

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
            return BindingState("stable", False, False)
        for owner in self._visible_owners(site, name):
            events = owner.events.get(name, ())
            if any(event.operation != "annotation" for event in events) or any(
                self._star_may_write(event, name) for event in owner.stars
            ):
                return self.state(owner, name)
            if owner.kind == "function" and events:
                # Annotation-only locals mask outer bindings, even though the
                # annotation supplies no binding state of its own.
                return None
            if owner.kind == "module" and name in BUILTIN_NAMES:
                return self.state(owner, name)
        return None

    def _star_candidate_is_known(self, event: _BindingEvent, name: str) -> bool:
        """Only expand star imports with an unambiguous implicit export rule.

        Explicit imports may follow __all__, but wildcard exports with an
        explicit (potentially dynamic) __all__ cannot be guessed from names.
        """
        source = event.value
        if not isinstance(source, tuple) or name.startswith("_"):
            return False
        root = self.modules.get(source[0])
        return root is not None and "__all__" not in root.events

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
            all_stars = tuple(
                item for item in owner.stars if self._star_may_write(item, name)
            )
            stars = tuple(
                item for item in all_stars if cutoff is None or item.sequence <= cutoff
            )
            if not events and not stars and (all_introductions or all_stars):
                # A later local declaration must not be borrowed from an outer
                # name, and a later import cannot create an earlier candidate.
                return _UnknownBinding("later_introduction")
            if not events and not stars:
                # The declaration itself still occupies its lexical name.
                # If no earlier/sibling introduction survives, do not borrow
                # an unrelated name from an enclosing scope as its base.
                if events or any(
                    event.operation == "definition" for event in all_events
                ):
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
            if stars:
                if (
                    len(stars) == 1
                    and not events
                    and not stars[0].conditional
                    and self._star_candidate_is_known(stars[0], name)
                ):
                    source = stars[0].value
                    assert isinstance(source, tuple)
                    exported = self.export(source[0], name, _seen)
                    if not isinstance(exported, _UnknownBinding):
                        return exported
                return _UnknownBinding("wildcard_import", known, import_candidates)
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


def _collect_facts(
    modules: dict[str, tuple[Model, bool]],
    syntax: Mapping[str, tuple[SyntaxFacts, Mapping[int, Model]]],
    *,
    definitions: frozenset[str] = frozenset({"model.definition.class"}),
) -> _FactIndex:
    """Attach Model identities to AST-only lexical facts, without rescanning.

    The AST traversal has already happened once, prior to Model conversion.
    A model is used only to identify supported declarations and their spans;
    it never supplies lexical binding or import facts.
    """
    sites: list[_DefinitionSite] = []
    roots: dict[str, _Scope] = {}
    scopes: list[_Scope] = []
    class_scopes: dict[int, _Scope] = {}
    attributes: dict[str, set[str]] = {}
    for module_name, (module, is_package) in modules.items():
        ast_facts, modeled = syntax[module_name]
        local: dict[SyntaxScope, _Scope] = {}
        for lexical in ast_facts.scopes:
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
        for item in ast_facts.definitions:
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
        for event in ast_facts.events:
            if event.kind == "attribute_write" or event.kind == "attribute_delete":
                attributes.setdefault(module_name, set()).add(event.name)
                continue
            # Incomplete source inspection never calls relationship analysis.
            # A direct parse has a Model for every supported statement.
            statement = modeled.get(id(event.statement))
            if statement is None:
                continue
            scope = local[event.scope]
            value: _BaseBinding | None
            if event.kind in {"import", "star"}:
                assert event.imported is not None
                written, imported = event.imported
                if written is None:
                    value = _UnknownBinding("unresolved_import")
                elif written.startswith("."):
                    level = len(written) - len(written.lstrip("."))
                    source = _resolved_module(
                        module_name,
                        is_package=is_package,
                        level=level,
                        module=written[level:] or None,
                    )
                    value = (
                        (source, imported)
                        if source is not None
                        else _UnknownBinding("unresolved_import")
                    )
                else:
                    # Plain `import pkg.a` binds `pkg`, but retains the full
                    # path explicitly named by the AST. `import pkg.a as a`
                    # instead binds `a` directly to the complete module.
                    if event.explicit_module is not None:
                        path = explicit_import_path(event)
                        assert path is not None
                        segments = path.split(".")
                        value = _ExplicitModulePath(segments[0], tuple(segments[1:]))
                    else:
                        value = (written, imported)
                if event.kind == "star":
                    scope.stars.append(
                        _BindingEvent(
                            "*",
                            value,
                            event.sequence,
                            event.conditional,
                            operation="star",
                        )
                    )
                    continue
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

    # Lexical global/nonlocal declarations apply to an entire scope. Use the
    # shared binding-owner policy against the original lexical name inventory:
    # moving an event must not change another declaration's ownership decision.
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
                # An unresolved nonlocal is not mapped to an invented owner.
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
        # Other scopes remain independent, even if names have the same spelling.
    for scope in scopes:
        for entries in scope.events.values():
            entries.sort(key=lambda event: event.sequence)
    return _FactIndex(
        tuple(sites),
        roots,
        tuple(scopes),
        class_scopes,
        {module: frozenset(paths) for module, paths in attributes.items()},
    )
