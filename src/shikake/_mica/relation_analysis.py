"""Build written base references and possible same-name method candidates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from shikake.external import ExternalDefinitions

from .ast_facts import SyntaxFacts
from .base_references import BaseReference, OverrideCandidate
from .class_hierarchy import _ClassHierarchy
from .model import Model
from .reference_resolution import _ReferenceResolver, _written_parts
from .relation_facts import (
    NameBinding,
    _collect_facts,
    _FactIndex,
    _known_models,
    _name,
    _nodes,
)


@dataclass(slots=True)
class _AnalysisContext:
    facts: _FactIndex
    hierarchy: _ClassHierarchy
    candidates: list[OverrideCandidate]


class _Analyzer(Protocol):
    name: str
    required_definitions: frozenset[str]
    dependencies: frozenset[str]

    def analyze(self, context: _AnalysisContext) -> None: ...


class _InheritanceAnalyzer:
    name = "inheritance"
    required_definitions = frozenset({"model.definition.class"})
    dependencies: frozenset[str] = frozenset()

    def analyze(self, context: _AnalysisContext) -> None:
        resolver = _ReferenceResolver(context.facts)
        for site in context.facts.definitions:
            derived = site.definition
            if derived.kind.id != "model.definition.class":
                continue
            references: list[BaseReference] = []
            for expression in _nodes(derived, "bases"):
                resolution = resolver.resolve(expression, site)
                written = _written_parts(expression)
                state = (
                    context.facts.reference_state(site, written[0])
                    if written is not None
                    else None
                )
                references.append(
                    BaseReference(
                        derived,
                        expression,
                        tuple(
                            target
                            for target in _known_models(resolution.binding)
                            if target.kind.id == "model.definition.class"
                        ),
                        state,
                        context.facts.changes_attribute(
                            site.module, ".".join(written) if written else ""
                        ),
                    )
                )
            context.hierarchy.inheritance[id(derived)] = tuple(references)


class _OverrideAnalyzer:
    name = "override"
    required_definitions = frozenset({"model.definition.class"})
    dependencies = frozenset({"inheritance"})

    def analyze(self, context: _AnalysisContext) -> None:
        for site in context.facts.definitions:
            derived = site.definition
            if derived.kind.id != "model.definition.class":
                continue
            direct = context.hierarchy.direct_bases(derived)
            for method in context.hierarchy.members.methods(derived):
                for owner, base_method in context.hierarchy.lookup_bases(
                    derived, _name(method)
                ):
                    # A method cannot override its own exact declaration,
                    # even when write-order-agnostic edges appear cyclic.
                    if method is base_method:
                        continue
                    context.candidates.append(
                        OverrideCandidate(
                            method=method,
                            base_method=base_method,
                            derived_class=derived,
                            base_class=owner,
                            derived_module=site.module,
                            base_module=context.hierarchy.class_modules.get(
                                id(owner), site.module
                            ),
                            evidence=(
                                "direct_base_and_same_method_name"
                                if id(owner) in direct
                                else "ancestor_and_same_method_name"
                            ),
                        )
                    )


_ANALYZERS: dict[str, _Analyzer] = {
    "inheritance": _InheritanceAnalyzer(),
    "override": _OverrideAnalyzer(),
}
SUPPORTED_ANALYSES = frozenset(_ANALYZERS)


def _selected_analyses(analyses: Iterable[str] | None) -> frozenset[str]:
    if isinstance(analyses, str):
        raise TypeError(
            "analyses must be an iterable of analysis names, not a string; "
            "use {'override'} instead"
        )
    selected = set({"override"} if analyses is None else analyses)
    invalid = selected - SUPPORTED_ANALYSES
    if invalid:
        raise ValueError(f"unknown relation analyses: {sorted(invalid)}")
    pending = list(selected)
    while pending:
        analyzer = _ANALYZERS[pending.pop()]
        for prerequisite in analyzer.dependencies - selected:
            selected.add(prerequisite)
            pending.append(prerequisite)
    return frozenset(selected)


def _analyze_package_facts(
    modules: dict[str, tuple[Model, bool]],
    selected: frozenset[str],
    syntax: Mapping[str, tuple[SyntaxFacts, Mapping[int, Model]]],
    *,
    builtin_value_sink: set[tuple[str, str]] | None = None,
    external_definitions: ExternalDefinitions | None = None,
) -> tuple[
    tuple[OverrideCandidate, ...], tuple[BaseReference, ...], tuple[NameBinding, ...]
]:
    scheduled = tuple(
        analyzer for name, analyzer in _ANALYZERS.items() if name in selected
    )
    required = frozenset().union(
        *(analyzer.required_definitions for analyzer in scheduled)
    )
    facts = _collect_facts(
        modules, syntax, definitions=required, external_definitions=external_definitions
    )
    if builtin_value_sink is not None:
        builtin_value_sink.update(facts.builtin_value_uses())
    context = _AnalysisContext(facts, _ClassHierarchy(facts), [])
    completed: set[str] = set()
    for analyzer in scheduled:
        if not analyzer.dependencies <= completed:
            raise ValueError(f"unsatisfied dependencies for {analyzer.name}")
        analyzer.analyze(context)
        completed.add(analyzer.name)
    references = tuple(
        reference
        for site in facts.definitions
        for reference in context.hierarchy.inheritance.get(id(site.definition), ())
    )
    return tuple(context.candidates), references, facts.bindings()
