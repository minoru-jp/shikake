"""One index of class member declarations and written ancestor edges.

No match-level certainty, MRO order, or runtime binding status is inferred.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base_references import BaseReference
from .model import Model
from .relation_facts import _FactIndex

_METHOD_KINDS = frozenset({"model.definition.method", "model.definition.generator"})


@dataclass(slots=True)
class _ClassMembers:
    facts: _FactIndex
    _methods: dict[int, dict[str, tuple[Model, ...]]] = field(default_factory=dict)
    _ordered: dict[int, tuple[Model, ...]] = field(default_factory=dict)

    def _populate(self, class_model: Model) -> None:
        identity = id(class_model)
        if identity in self._methods:
            return
        scope = self.facts.class_scopes.get(identity)
        if scope is None:
            self._methods[identity] = {}
            self._ordered[identity] = ()
            return
        declarations: list[tuple[int, str, Model]] = []
        for name, events in scope.events.items():
            for event in events:
                source = event.source
                if (
                    event.declaration
                    and source is not None
                    and source.kind.id in _METHOD_KINDS
                ):
                    declarations.append((event.sequence, name, source))
        declarations.sort(key=lambda record: record[0])
        by_name: dict[str, list[Model]] = {}
        for _, name, source in declarations:
            by_name.setdefault(name, []).append(source)
        self._methods[identity] = {
            name: tuple(models) for name, models in by_name.items()
        }
        self._ordered[identity] = tuple(source for _, _, source in declarations)

    def methods_by_name(self, class_model: Model) -> dict[str, tuple[Model, ...]]:
        self._populate(class_model)
        return self._methods[id(class_model)]

    def methods(self, class_model: Model) -> tuple[Model, ...]:
        self._populate(class_model)
        return self._ordered[id(class_model)]


@dataclass(slots=True)
class _ClassHierarchy:
    facts: _FactIndex
    inheritance: dict[int, tuple[BaseReference, ...]] = field(default_factory=dict)
    members: _ClassMembers = field(init=False)
    class_modules: dict[int, str] = field(init=False)
    _ancestor_cache: dict[tuple[int, str], tuple[tuple[Model, Model], ...]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.members = _ClassMembers(self.facts)
        self.class_modules = {
            id(site.definition): site.module
            for site in self.facts.definitions
            if site.definition.kind.id == "model.definition.class"
        }

    def direct_bases(self, class_model: Model) -> set[int]:
        return {
            id(base)
            for reference in self.inheritance.get(id(class_model), ())
            for base in reference.targets
            if base.kind.id == "model.definition.class"
        }

    def _ancestors(self, class_model: Model) -> tuple[Model, ...]:
        return tuple(
            target
            for reference in self.inheritance.get(id(class_model), ())
            for target in reference.targets
            if target.kind.id == "model.definition.class"
        )

    def lookup_bases(
        self, class_model: Model, name: str
    ) -> tuple[tuple[Model, Model], ...]:
        """Collect known same-name declarations, irrespective of edge stability."""
        unique: dict[int, tuple[Model, Model]] = {}
        for base in self._ancestors(class_model):
            for owner, method in self._inherited_members(base, name):
                unique.setdefault(id(method), (owner, method))
        return tuple(unique.values())

    def _inherited_members(
        self, base: Model, name: str
    ) -> tuple[tuple[Model, Model], ...]:
        """Iterative, cycle-safe traversal with diamond deduplication."""
        key = (id(base), name)
        cached = self._ancestor_cache.get(key)
        if cached is not None:
            return cached
        # Stack traversal has no recursion depth limit. Cache the result of a
        # completed acyclic traversal only: cycles must not hide declarations.
        pending: list[tuple[Model, bool]] = [(base, False)]
        active: set[int] = set()
        children: dict[int, tuple[Model, ...]] = {}
        local: dict[int, tuple[tuple[Model, Model], ...]] = {}
        cyclic = False
        while pending:
            current, finish = pending.pop()
            identity = id(current)
            if (identity, name) in self._ancestor_cache:
                continue
            if not finish:
                if identity in active:
                    cyclic = True
                    continue
                active.add(identity)
                pending.append((current, True))
                kids = self._ancestors(current)
                children[identity] = kids
                for child in reversed(kids):
                    if id(child) in active:
                        cyclic = True
                    elif (id(child), name) not in self._ancestor_cache:
                        pending.append((child, False))
                continue
            unique: dict[int, tuple[Model, Model]] = {
                id(method): (current, method)
                for method in self.members.methods_by_name(current).get(name, ())
            }
            for child in children[identity]:
                for owner, method in local.get(
                    id(child), self._ancestor_cache.get((id(child), name), ())
                ):
                    unique.setdefault(id(method), (owner, method))
            result = tuple(unique.values())
            local[identity] = result
            if not cyclic:
                self._ancestor_cache[(identity, name)] = result
            active.remove(identity)
        return local.get(id(base), ())
