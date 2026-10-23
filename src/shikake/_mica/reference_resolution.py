"""Single static reference resolver over the shared lexical binding facts.

The resolver traces written paths; it does not execute Python code, infer
runtime values, or turn missing source modules into binding modifications.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Model
from .relation_facts import (
    _BaseBinding,
    _DefinitionSite,
    _ExplicitModulePath,
    _FactIndex,
    _known_models,
    _name,
    _node,
    _UnknownBinding,
)


def _written_parts(expression: Model) -> tuple[str, ...] | None:
    """Return root name plus written attributes, without resolving values."""
    attributes: list[str] = []
    current = expression
    while current.kind.id == "model.value.access.attribute":
        attributes.append(current.get_name("attribute"))
        current = _node(current, "target")
    if current.kind.id != "model.value.named":
        return None
    return (_name(current), *reversed(attributes))


@dataclass(frozen=True, slots=True)
class _Resolution:
    binding: _BaseBinding
    module: str


class _ReferenceResolver:
    def __init__(self, facts: _FactIndex) -> None:
        self.facts = facts

    def resolve(self, expression: Model, site: _DefinitionSite) -> _Resolution:
        """Resolve a Name/attribute expression at its written lexical site."""
        written = _written_parts(expression)
        if written is None:
            return _Resolution(_UnknownBinding("computed_base"), site.module)
        root, *parts = written
        binding = self.facts.lookup(site, root)
        written_path = ".".join(written)
        altered = self.facts.changes_attribute(site.module, written_path)
        module = site.module
        binding, module = self._follow(binding, module, set())
        for member in parts:
            binding, module = self._member(binding, module, member)
            binding, module = self._follow(binding, module, set())
        if altered:
            return _Resolution(
                _UnknownBinding("attribute_change", _known_models(binding)), module
            )
        return _Resolution(binding, module)

    def _follow(
        self, binding: _BaseBinding, module: str, visited: set[tuple[str, str]]
    ) -> tuple[_BaseBinding, str]:
        if isinstance(binding, _UnknownBinding) and binding.alternatives:
            # Keep every syntactically written import path as an independent
            # candidate. A conditional import is not a value-flow branch:
            # source order and exception outcomes do not select a winner.
            resolved = tuple(
                self._follow(option, module, visited.copy())[0]
                for option in binding.alternatives
            )
            models = {id(model): model for model in binding.possible}
            for option in resolved:
                for model in _known_models(option):
                    models.setdefault(id(model), model)
            return (
                _UnknownBinding(binding.reason, tuple(models.values()), resolved),
                module,
            )
        while isinstance(binding, tuple):
            source, name = binding
            if not name:
                return binding, source
            key = (source, name)
            if key in visited:
                return _UnknownBinding("circular_import"), module
            visited.add(key)
            # A namespace package need not have an `__init__.py` Model.
            # Check the explicitly named child module independently of whether
            # the parent package has source of its own.
            found = self.facts.export(source, name)
            # `from . import submodule` can refer to the package attribute or
            # the submodule. Do not prefer a submodule over a known attribute.
            child_module = f"{source}.{name}"
            if child_module in self.facts.modules:
                if not self.facts.package_name_conflicts(source, name):
                    return (child_module, ""), child_module
                resolved = found
                if isinstance(found, tuple):
                    resolved, _ = self._follow(found, source, visited.copy())
                return _UnknownBinding(
                    "ambiguous_import", _known_models(resolved)
                ), source
            binding, module = found, source
        return binding, module

    def _member(
        self, binding: _BaseBinding, module: str, name: str
    ) -> tuple[_BaseBinding, str]:
        if isinstance(binding, _ExplicitModulePath):
            if binding.remaining and name == binding.remaining[0]:
                next_module = f"{binding.module}.{name}"
                if len(binding.remaining) == 1:
                    return (next_module, ""), next_module
                return _ExplicitModulePath(
                    next_module, binding.remaining[1:]
                ), next_module
            # A separate attribute may be explicitly defined by the package,
            # but never infer an unrelated submodule solely from its filename.
            return self.facts.export(binding.module, name), binding.module
        if isinstance(binding, tuple) and not binding[1]:
            target_module = binding[0]
            return self.facts.export(target_module, name), target_module
        if isinstance(binding, Model) and binding.kind.id == "model.definition.class":
            scope = self.facts.class_scopes.get(id(binding))
            if scope is None:
                return _UnknownBinding("outside_analysis_scope"), module
            return self.facts.lookup(
                _DefinitionSite(scope.module, binding, scope),
                name,
                local_only=True,
            ), scope.module
        if isinstance(binding, _UnknownBinding):
            if binding.alternatives:
                # Explicit alternatives can be followed member by member.
                # Do not project merely possible classes of an ambiguous root
                # onto an attribute that was never shown to exist.
                return (
                    _UnknownBinding(
                        binding.reason,
                        alternatives=tuple(
                            self._member(option, module, name)[0]
                            for option in binding.alternatives
                        ),
                    ),
                    module,
                )
            return _UnknownBinding("unsupported_attribute_reference"), module
        return _UnknownBinding("unsupported_attribute_reference"), module
