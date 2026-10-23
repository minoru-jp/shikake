"""Independent written base references and possible method-name matches.

Neither object classifies a relationship or asserts a runtime hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .model import Model
from .relation_facts import BindingState


@dataclass(frozen=True, slots=True, eq=False)
class BaseReference:
    """One base expression written on a class, in source order.

    ``targets`` contains only locally identifiable *possible* class definitions;
    it need not contain all possible runtime targets. ``binding`` describes the
    lexical root name in the referring module (not the imported source module).
    A missing root binding or an unmodeled expression leaves ``binding=None``.
    """

    subject: Model
    expression: Model
    targets: tuple[Model, ...]
    binding: BindingState | None
    attribute_modified: bool = False


@dataclass(frozen=True, slots=True, eq=False)
class OverrideCandidate:
    """A written same-name method candidate, never a proven runtime override.

    Consumers inspect the class's BaseReferences and NameBindings themselves.
    The candidate is not suppressed simply because an edge is uncertain.
    """

    method: Model
    base_method: Model
    derived_class: Model
    base_class: Model
    derived_module: str
    base_module: str
    evidence: Literal[
        "direct_base_and_same_method_name", "ancestor_and_same_method_name"
    ] = "direct_base_and_same_method_name"
