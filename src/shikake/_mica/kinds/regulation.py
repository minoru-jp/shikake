"""Shikumi regulation for independent Kind, Structure and Feature descriptions.

Kind declares subject taxonomy only. Structure describes ordered Model parts,
not language evaluation or transformation semantics. All descriptions are
trusted package-owned Python sources; source-under-analysis is never executed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shikumi import (
    Cardinality,
    Diagnostic,
    InformationType,
    SemanticView,
    Shikumi,
    StructuralKind,
    validator,
)
from shikumi.standard import PackageTreeStructure, assignment, information_type_rule

PartShape = Literal[
    "node", "optional_node", "nodes", "text", "optional_text", "scalar", "texts"
]


@dataclass(frozen=True, slots=True)
class PartContract:
    """One part's role and storage shape, in Structure declaration order."""

    role: str
    shape: PartShape


KIND_ID = InformationType("mica.kind_id", str)
PARENT_ID = InformationType("mica.parent_id", str)
STRUCTURE_REF = InformationType("mica.structure_ref", str)
STRUCTURE_ID = InformationType("mica.structure_id", str)
PART = InformationType("mica.part", PartContract, cardinality=Cardinality.MANY)
FEATURE_ID = InformationType("mica.feature_id", str)
FEATURE_ALLOWED = InformationType(
    "mica.feature_allowed_kind", str, cardinality=Cardinality.MANY
)

kind_id = assignment(KIND_ID)
parent_id = assignment(PARENT_ID)
structure_ref = assignment(STRUCTURE_REF)
structure_id = assignment(STRUCTURE_ID)
part = assignment(PART)
feature_id = assignment(FEATURE_ID)
feature_allowed = assignment(FEATURE_ALLOWED)


@validator(focus=StructuralKind.ENTITY)
def require_description_identity(view: SemanticView):  # type: ignore[no-untyped-def]
    """One entity defines exactly one Kind, Structure or Feature."""
    identities = sum(
        len(view.focused.values(info)) for info in (KIND_ID, STRUCTURE_ID, FEATURE_ID)
    )
    if identities != 1:
        yield Diagnostic(
            "exactly one Kind, Structure or Feature ID is required",
            code="mica.description.identity",
        )


@validator(focus=StructuralKind.PACKAGE)
def check_description_graph(view: SemanticView):  # type: ignore[no-untyped-def]
    """Validate all references after Shikumi has collected the package."""
    from .index import _index_from_view

    if not any(item.values(KIND_ID) == ("model",) for item in view.entities):
        return
    try:
        _index_from_view(view)
    except ValueError as exc:
        yield Diagnostic(str(exc), code="mica.description.graph")


KIND_SHIKUMI = Shikumi(
    structure=PackageTreeStructure(),
    information_types=[
        KIND_ID,
        PARENT_ID,
        STRUCTURE_ID,
        STRUCTURE_REF,
        PART,
        FEATURE_ID,
        FEATURE_ALLOWED,
    ],
    validators=[
        require_description_identity,
        check_description_graph,
        *(
            information_type_rule(info)
            for info in (
                KIND_ID,
                PARENT_ID,
                STRUCTURE_ID,
                STRUCTURE_REF,
                PART,
                FEATURE_ID,
                FEATURE_ALLOWED,
            )
        ),
    ],
)
