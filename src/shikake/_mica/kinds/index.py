"""Validated Kind taxonomy, independent ordered Structures, and Features.

Shikumi reads trusted Python descriptions; no JSON intermediate or CLI is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from types import ModuleType

from shikumi import Diagnostic, RealizationCheck, Realizer, SemanticView, StructuralKind

from . import description
from .regulation import (
    FEATURE_ALLOWED,
    FEATURE_ID,
    KIND_ID,
    KIND_SHIKUMI,
    PARENT_ID,
    PART,
    STRUCTURE_ID,
    STRUCTURE_REF,
    PartContract,
)


@dataclass(frozen=True, slots=True)
class Kind:
    """Public subject classification, independent from its structural roles."""

    id: str
    parent_id: str | None
    structure_id: str | None = None


@dataclass(frozen=True, slots=True)
class Structure:
    """Complete, ordered part layout; no Kind hierarchy or runtime semantics."""

    id: str
    parts: tuple[PartContract, ...]


@dataclass(frozen=True, slots=True)
class Feature:
    id: str
    allowed_kind_ids: tuple[str, ...]


class KindIndex:
    """Single-parent Kind tree with independently indexed Structures/Features."""

    def __init__(
        self,
        kinds: tuple[Kind, ...],
        structures: tuple[Structure, ...] = (),
        features: tuple[Feature, ...] = (),
    ) -> None:
        mapping = {kind.id: kind for kind in kinds}
        if len(mapping) != len(kinds):
            raise ValueError("duplicate Kind ID in description")
        if "model" not in mapping or mapping["model"].parent_id is not None:
            raise ValueError("the Kind tree must contain a root 'model'")
        structure_map = {structure.id: structure for structure in structures}
        if len(structure_map) != len(structures):
            raise ValueError("duplicate Structure ID")
        for structure in structures:
            if not structure.id:
                raise ValueError("empty Structure ID")
            roles = tuple(p.role for p in structure.parts)
            if any(not role for role in roles) or len(set(roles)) != len(roles):
                raise ValueError(f"duplicate or empty part role for {structure.id}")
            if any(
                spec.shape
                not in {
                    "node",
                    "optional_node",
                    "nodes",
                    "text",
                    "optional_text",
                    "scalar",
                    "texts",
                }
                for spec in structure.parts
            ):
                raise ValueError(f"unknown part shape in {structure.id}")
        for kind in kinds:
            if not kind.id:
                raise ValueError("empty Kind ID")
            if kind.id != "model" and kind.parent_id is None:
                raise ValueError(f"missing parent for {kind.id}")
            if kind.parent_id is not None and kind.parent_id not in mapping:
                raise ValueError(f"unknown parent for {kind.id}: {kind.parent_id}")
            if kind.structure_id is not None and kind.structure_id not in structure_map:
                raise ValueError(
                    f"unknown Structure for {kind.id}: {kind.structure_id}"
                )
        # Ancestry is a taxonomy only. It does not impose structural roles.
        visited: set[str] = set()
        active: set[str] = set()

        def check_ancestry(kind_id: str) -> None:
            if kind_id in visited:
                return
            if kind_id in active:
                raise ValueError(f"cyclic Kind ancestry at {kind_id}")
            active.add(kind_id)
            parent = mapping[kind_id].parent_id
            if parent is not None:
                check_ancestry(parent)
            active.remove(kind_id)
            visited.add(kind_id)

        for kind in kinds:
            check_ancestry(kind.id)
        feature_map = {feature.id: feature for feature in features}
        if len(feature_map) != len(features):
            raise ValueError("duplicate feature ID")
        for feature in features:
            if not feature.id or not feature.allowed_kind_ids:
                raise ValueError(f"feature {feature.id!r} must have allowed Kinds")
            for target in feature.allowed_kind_ids:
                if target not in mapping:
                    raise ValueError(f"unknown allowed Kind for {feature.id}: {target}")
        self._mapping = mapping
        self._structures = structure_map
        self._features = feature_map

    def get(self, kind_id: str) -> Kind:
        return self._mapping[kind_id]

    def parent(self, kind_id: str) -> Kind | None:
        parent_id = self.get(kind_id).parent_id
        return self.get(parent_id) if parent_id is not None else None

    def is_a(self, kind_id: str, ancestor_id: str) -> bool:
        current: Kind | None = self.get(kind_id)
        self.get(ancestor_id)
        while current is not None:
            if current.id == ancestor_id:
                return True
            current = self.parent(current.id)
        return False

    def structure_of(self, kind_id: str) -> Structure | None:
        """Return this Kind's exact Structure, without ancestor inheritance."""
        kind = self.get(kind_id)
        return (
            self._structures[kind.structure_id]
            if kind.structure_id is not None
            else None
        )

    def require_structure(self, kind_id: str) -> Structure:
        """Get the complete layout for a concrete Kind, rejecting abstract Kinds."""
        structure = self.structure_of(kind_id)
        if structure is None:
            raise ValueError(f"{kind_id}: abstract Kind has no Structure")
        return structure

    def get_structure(self, structure_id: str) -> Structure:
        return self._structures[structure_id]

    def all_structures(self) -> tuple[Structure, ...]:
        return tuple(self._structures.values())

    def validate_features(self, kind_id: str, features: tuple[str, ...]) -> None:
        self.get(kind_id)
        if len(set(features)) != len(features):
            raise ValueError("duplicate Model features")
        for feature_id in features:
            feature = self._features.get(feature_id)
            if feature is None:
                raise ValueError(f"unknown Model feature: {feature_id}")
            if not any(
                self.is_a(kind_id, target) for target in feature.allowed_kind_ids
            ):
                raise ValueError(f"feature {feature_id} is not applicable to {kind_id}")

    def all_kinds(self) -> tuple[Kind, ...]:
        return tuple(self._mapping.values())

    def all_features(self) -> tuple[Feature, ...]:
        return tuple(self._features.values())


def _index_from_view(view: SemanticView) -> KindIndex:
    entities = (item for item in view.items if item.kind is StructuralKind.ENTITY)
    kinds: list[Kind] = []
    structures: list[Structure] = []
    features: list[Feature] = []
    for item in entities:
        kind_ids = item.values(KIND_ID)
        structure_ids = item.values(STRUCTURE_ID)
        feature_ids = item.values(FEATURE_ID)
        if sum(map(len, (kind_ids, structure_ids, feature_ids))) != 1:
            raise ValueError(f"ambiguous description identity at {item.node.path}")
        parents = item.values(PARENT_ID)
        references = item.values(STRUCTURE_REF)
        parts = item.values(PART)
        allowed = item.values(FEATURE_ALLOWED)
        if kind_ids:
            if parts or allowed or len(parents) > 1 or len(references) > 1:
                raise ValueError(f"invalid Kind metadata for {kind_ids[0]}")
            kind_id = kind_ids[0]
            if kind_id == "model" and parents:
                raise ValueError("root Model Kind cannot have a parent")
            if kind_id != "model" and not parents:
                raise ValueError(f"missing parent ID for {kind_id}")
            kinds.append(
                Kind(
                    kind_id,
                    parents[0] if parents else None,
                    references[0] if references else None,
                )
            )
        elif structure_ids:
            if parents or references or allowed:
                raise ValueError(f"invalid Structure metadata for {structure_ids[0]}")
            structures.append(Structure(structure_ids[0], parts))
        else:
            if parents or references or parts:
                raise ValueError(f"invalid Feature metadata for {feature_ids[0]}")
            features.append(Feature(feature_ids[0], allowed))
    return KindIndex(tuple(kinds), tuple(structures), tuple(features))


class KindIndexRealizer(Realizer[KindIndex]):
    """Optional non-persistent realization of the validated description view."""

    def check(self, view: SemanticView) -> RealizationCheck:
        try:
            _index_from_view(view)
        except ValueError as exc:
            return RealizationCheck(
                view, (Diagnostic(str(exc), code="mica.kind.realization"),)
            )
        return RealizationCheck(view)

    def realize(self, view: SemanticView) -> KindIndex:
        return _index_from_view(view)


def load_kind_index(source: ModuleType = description) -> KindIndex:
    """Validate trusted descriptions and realize in-memory taxonomy/layouts."""
    result = KIND_SHIKUMI.validate(source, placement=("mica", "kinds", "description"))
    if not result.is_valid:
        raise ValueError(f"invalid Shikumi Kind description: {result.diagnostics}")
    realizer = KindIndexRealizer()
    check = realizer.check(result.view)
    if not check.is_realizable:
        raise ValueError(f"invalid Kind realization: {check.diagnostics}")
    return realizer.realize(result.view)


@lru_cache(maxsize=1)
def kind_index() -> KindIndex:
    return load_kind_index()
