"""Trusted Shikumi declarations for opt-in external interface modeling.

Python interfaces remain independent of these descriptions. Registration never
imports or executes source-under-analysis or the named interface module.
"""

from __future__ import annotations

import keyword
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Self

from shikumi import Cardinality, InformationType, Shikumi
from shikumi.standard import PackageTreeStructure, assignment, information_type_rule

from shikake._mica.kinds.index import (
    DefinitionIndex,
    Feature,
    Kind,
    Structure,
    definition_index,
)
from shikake._mica.kinds.regulation import (
    FEATURE_ALLOWED,
    FEATURE_ID,
    KIND_ID,
    PARENT_ID,
    PART,
    STRUCTURE_ID,
    STRUCTURE_REF,
    PartContract,
    feature_allowed,
    feature_id,
    kind_id,
    parent_id,
    part,
    structure_id,
    structure_ref,
)

Role = PartContract


@dataclass(frozen=True, slots=True)
class _ImportedTarget:
    """A syntactic target referenced through a module-level explicit import."""

    path: str

    def _validate(self, *, minimum_attributes: int) -> None:
        module, separator, attributes = self.path.partition(":")
        if (
            not separator
            or not module
            or not attributes
            or unicodedata.normalize("NFKC", module) != module
            or unicodedata.normalize("NFKC", attributes) != attributes
            or not all(
                piece.isidentifier() and not keyword.iskeyword(piece)
                for piece in module.split(".")
            )
            or not all(
                piece.isidentifier() and not keyword.iskeyword(piece)
                for piece in attributes.split(".")
            )
            or len(attributes.split(".")) < minimum_attributes
        ):
            raise ValueError(f"invalid external target: {self.path!r}")

    @property
    def dotted(self) -> str:
        return self.path.replace(":", ".")


@dataclass(frozen=True, slots=True)
class ImportedCall(_ImportedTarget):
    """A call on an imported interface: 'package.module:function' or ':Class.method'."""

    def __post_init__(self) -> None:
        self._validate(minimum_attributes=1)


@dataclass(frozen=True, slots=True)
class ImportedType(_ImportedTarget):
    """A type name used in an annotation or registered generic argument."""

    def __post_init__(self) -> None:
        self._validate(minimum_attributes=1)


@dataclass(frozen=True, slots=True)
class ImportedGeneric(_ImportedTarget):
    """A generic interface applied with ``[...]``."""

    def __post_init__(self) -> None:
        self._validate(minimum_attributes=1)


@dataclass(frozen=True, slots=True)
class Argument:
    """Bind a call argument to one node-valued role, without executing it."""

    role: str
    position: int
    keyword: str

    def __post_init__(self) -> None:
        if (
            not self.role.isidentifier()
            or self.position < 0
            or not self.keyword.isidentifier()
        ):
            raise ValueError("invalid argument binding")


MATCH = InformationType("mica.external.match", ImportedCall)
TYPE_MATCH = InformationType("mica.external.type_match", ImportedType)
GENERIC_MATCH = InformationType("mica.external.generic_match", ImportedGeneric)
GENERIC_SLOT = InformationType(
    "mica.external.generic_slot", str, cardinality=Cardinality.MANY
)
EMIT = InformationType("mica.external.emit", str)
BIND = InformationType("mica.external.bind", Argument, cardinality=Cardinality.MANY)
APPLY_FEATURE = InformationType(
    "mica.external.apply_feature", str, cardinality=Cardinality.MANY
)
match = assignment(MATCH)
match_type = assignment(TYPE_MATCH)
match_generic = assignment(GENERIC_MATCH)
slot = assignment(GENERIC_SLOT)
emit = assignment(EMIT)
bind = assignment(BIND)
apply_feature = assignment(APPLY_FEATURE)

_EXTERNAL_SHIKUMI = Shikumi(
    structure=PackageTreeStructure(),
    information_types=[
        KIND_ID,
        PARENT_ID,
        STRUCTURE_REF,
        STRUCTURE_ID,
        PART,
        FEATURE_ID,
        FEATURE_ALLOWED,
        MATCH,
        TYPE_MATCH,
        GENERIC_MATCH,
        GENERIC_SLOT,
        EMIT,
        BIND,
        APPLY_FEATURE,
    ],
    validators=[
        *(
            information_type_rule(info)
            for info in (
                KIND_ID,
                PARENT_ID,
                STRUCTURE_REF,
                STRUCTURE_ID,
                PART,
                FEATURE_ID,
                FEATURE_ALLOWED,
                MATCH,
                TYPE_MATCH,
                GENERIC_MATCH,
                GENERIC_SLOT,
                EMIT,
                BIND,
                APPLY_FEATURE,
            )
        ),
    ],
)


@dataclass(frozen=True, slots=True)
class CallMapping:
    target: ImportedCall
    kind_id: str
    arguments: tuple[Argument, ...]
    features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TypeMapping:
    target: ImportedType
    kind_id: str
    features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GenericMapping:
    target: ImportedGeneric
    kind_id: str
    roles: tuple[str, ...]
    features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExternalDefinitions:
    """Immutable extension schema, validated by the builder or Shikumi loader.

    Direct construction bypasses provenance and consistency validation; trusted
    callers must ensure every field, including external_feature_ids, is sound.
    """

    index: DefinitionIndex
    mappings: tuple[CallMapping, ...]
    type_mappings: tuple[TypeMapping, ...]
    generic_mappings: tuple[GenericMapping, ...]
    external_feature_ids: frozenset[str] = frozenset()


def load_external_definitions(
    source: ModuleType, *, base: DefinitionIndex | ExternalDefinitions | None = None
) -> ExternalDefinitions:
    """Read trusted Shikumi Python descriptions and merge into a base index.

    External declarations may add Kinds, Structures and Features, without replacing base IDs.
    The description module must be trusted Python code; analyzed source is not
    imported, and all import targets are treated as static strings.
    """
    if not isinstance(source, ModuleType):
        raise TypeError("definitions must be a Python description module")
    result = _EXTERNAL_SHIKUMI.validate(source, placement=("mica", "external"))
    if not result.is_valid:
        raise ValueError(f"invalid external Shikumi description: {result.diagnostics}")
    kinds: list[Kind] = []
    structures: list[Structure] = []
    features: list[Feature] = []
    mappings: list[CallMapping] = []
    type_mappings: list[TypeMapping] = []
    generic_mappings: list[GenericMapping] = []
    for entity in result.view.entities:
        ids = entity.values(KIND_ID)
        structure_ids = entity.values(STRUCTURE_ID)
        matched = entity.values(MATCH)
        typed = entity.values(TYPE_MATCH)
        generic = entity.values(GENERIC_MATCH)
        slots = entity.values(GENERIC_SLOT)
        feature_ids = entity.values(FEATURE_ID)
        allowed = entity.values(FEATURE_ALLOWED)
        applied = entity.values(APPLY_FEATURE)
        if (
            sum(
                bool(group)
                for group in (ids, structure_ids, feature_ids, matched, typed, generic)
            )
            != 1
        ):
            raise ValueError(f"external entity needs one identity: {entity.node.path}")
        parents = entity.values(PARENT_ID)
        references = entity.values(STRUCTURE_REF)
        parts = entity.values(PART)
        emits = entity.values(EMIT)
        binds = entity.values(BIND)
        if ids:
            if (
                len(ids) != 1
                or len(parents) != 1
                or len(references) > 1
                or parts
                or matched
                or typed
                or generic
                or slots
                or emits
                or binds
                or allowed
                or applied
            ):
                raise ValueError(f"invalid external Kind: {ids}")
            kinds.append(
                Kind(ids[0], parents[0], references[0] if references else None)
            )
        elif structure_ids:
            if (
                len(structure_ids) != 1
                or parents
                or references
                or emits
                or binds
                or slots
                or allowed
                or applied
            ):
                raise ValueError(f"invalid external Structure: {structure_ids}")
            structures.append(Structure(structure_ids[0], parts))
        elif feature_ids:
            if (
                len(feature_ids) != 1
                or parents
                or references
                or parts
                or emits
                or binds
                or slots
                or allowed == ()
                or applied
            ):
                raise ValueError(f"invalid external Feature: {feature_ids}")
            features.append(Feature(feature_ids[0], allowed))
        else:
            if len(emits) != 1 or parents or references or parts or allowed:
                raise ValueError("invalid external interface mapping")
            if matched:
                if len(matched) != 1 or slots:
                    raise ValueError("invalid external call mapping")
                mappings.append(
                    CallMapping(matched[0], emits[0], tuple(binds), applied)
                )
            elif typed:
                if len(typed) != 1 or binds or slots:
                    raise ValueError("invalid external type mapping")
                type_mappings.append(TypeMapping(typed[0], emits[0], applied))
            elif generic:
                if len(generic) != 1 or binds:
                    raise ValueError("invalid external generic mapping")
                generic_mappings.append(
                    GenericMapping(generic[0], emits[0], slots, applied)
                )
    return _assemble_external_definitions(
        kinds,
        structures,
        features,
        mappings,
        type_mappings,
        generic_mappings,
        base=base,
    )


def _assemble_external_definitions(
    kinds: Sequence[Kind],
    structures: Sequence[Structure],
    features: Sequence[Feature],
    mappings: Sequence[CallMapping],
    type_mappings: Sequence[TypeMapping],
    generic_mappings: Sequence[GenericMapping],
    *,
    base: DefinitionIndex | ExternalDefinitions | None,
) -> ExternalDefinitions:
    """Shared semantic validation for Shikumi and programmatic declarations."""
    if not (
        kinds or structures or features or mappings or type_mappings or generic_mappings
    ):
        raise ValueError("external description contains no declarations")
    # DefinitionIndex is an effective lookup table, not a composable extension.
    # Only ExternalDefinitions carries prior mappings and declaration provenance.
    if isinstance(base, DefinitionIndex):
        builtins = definition_index()
        if (
            base.all_kinds() != builtins.all_kinds()
            or base.all_structures() != builtins.all_structures()
            or base.all_features() != builtins.all_features()
        ):
            raise ValueError(
                "a custom or extended DefinitionIndex cannot be combined with "
                "external declarations; only the built-in DefinitionIndex is "
                "accepted as base. For staged extensions, use "
                "load_external_definitions(module, base=previous) or "
                "ExternalDefinitionsBuilder(base=previous), where previous is "
                "an ExternalDefinitions"
            )
    previous = base if isinstance(base, ExternalDefinitions) else None
    existing = (
        previous.index
        if previous is not None
        else base
        if isinstance(base, DefinitionIndex)
        else definition_index()
    )
    for category, identifiers in (
        ("Kind", (item.id for item in kinds)),
        ("Structure", (item.id for item in structures)),
        ("Feature", (item.id for item in features)),
    ):
        for identifier in identifiers:
            _validate_external_id(identifier, category)
    merged = DefinitionIndex(
        (*existing.all_kinds(), *kinds),
        (*existing.all_structures(), *structures),
        (*existing.all_features(), *features),
    )
    allowed_external_features = (
        previous.external_feature_ids if previous is not None else frozenset()
    ) | frozenset(item.id for item in features)
    all_mappings = (*previous.mappings, *mappings) if previous else tuple(mappings)
    all_types = (
        (*previous.type_mappings, *type_mappings) if previous else tuple(type_mappings)
    )
    all_generics = (
        (*previous.generic_mappings, *generic_mappings)
        if previous
        else tuple(generic_mappings)
    )
    targets: set[str] = set()
    for mapping in (*all_mappings, *all_types, *all_generics):
        merged.validate_features(mapping.kind_id, mapping.features)
        for feature in mapping.features:
            if feature not in allowed_external_features:
                raise ValueError(
                    f"external mapping cannot apply non-external Feature: {feature}"
                )
    for mapping in all_mappings:
        key = f"call:{mapping.target.dotted}"
        if key in targets:
            raise ValueError(
                f"duplicate external target: {mapping.target.path} (matching key: {key})"
            )
        targets.add(key)
        structure = merged.require_structure(mapping.kind_id)
        bindings = mapping.arguments
        if {p.role for p in structure.parts} != {item.role for item in bindings}:
            raise ValueError(f"roles do not match Structure for {mapping.kind_id}")
        if any(p.shape != "node" for p in structure.parts):
            raise ValueError(f"external mapping requires node roles: {mapping.kind_id}")
        if len({item.role for item in bindings}) != len(bindings):
            raise ValueError("duplicate binding role")
        positions = [item.position for item in bindings]
        if len(set(positions)) != len(positions):
            raise ValueError("duplicate binding position")
        if sorted(positions) != list(range(len(bindings))):
            raise ValueError("binding positions must be contiguous starting at zero")
        if len({item.keyword for item in bindings}) != len(bindings):
            raise ValueError("duplicate argument keyword")
    for mapping in all_types:
        key = f"type:{mapping.target.dotted}"
        if key in targets:
            raise ValueError(f"duplicate external target: {mapping.target.path}")
        targets.add(key)
        if merged.require_structure(mapping.kind_id).parts:
            raise ValueError(
                f"external type mapping requires empty Structure: {mapping.kind_id}"
            )
    for mapping in all_generics:
        key = f"generic:{mapping.target.dotted}"
        if key in targets:
            raise ValueError(f"duplicate external target: {mapping.target.path}")
        targets.add(key)
        structure = merged.require_structure(mapping.kind_id)
        if not mapping.roles or any(not role.isidentifier() for role in mapping.roles):
            raise ValueError("generic roles must be nonempty identifiers")
        if len(set(mapping.roles)) != len(mapping.roles):
            raise ValueError("duplicate generic role")
        if tuple(p.role for p in structure.parts) != mapping.roles or any(
            p.shape != "node" for p in structure.parts
        ):
            raise ValueError(f"invalid generic Structure roles: {mapping.kind_id}")
    return ExternalDefinitions(
        merged, all_mappings, all_types, all_generics, allowed_external_features
    )


def _validate_external_id(identifier: str, category: str) -> None:
    """Reserve package-owned IDs and require a qualified external namespace."""
    if not isinstance(identifier, str):
        raise TypeError(f"external {category} ID must be a string")
    segments = identifier.split(".")
    if len(segments) < 2:
        raise ValueError(
            f"external {category} ID must be dotted (at least two segments): {identifier!r}"
        )
    if segments[0] == "model":
        raise ValueError(
            f"external {category} ID uses reserved 'model.*' namespace: {identifier!r}"
        )
    if any(not segment.isidentifier() for segment in segments):
        raise ValueError(
            f"external {category} ID has a non-identifier segment: {identifier!r}"
        )


class ExternalDefinitionsBuilder:
    """Build validated external definitions from trusted Python data.

    ``add_call`` declares a Kind and its call mapping together. For existing
    Kinds, use ``add_mapping`` instead. Both paths share the same semantic
    validation as ``load_external_definitions``.
    """

    def __init__(
        self, *, base: DefinitionIndex | ExternalDefinitions | None = None
    ) -> None:
        self._base = base
        self._kinds: list[Kind] = []
        self._structures: list[Structure] = []
        self._features: list[Feature] = []
        self._mappings: list[CallMapping] = []
        self._type_mappings: list[TypeMapping] = []
        self._generic_mappings: list[GenericMapping] = []

    def add_kind(
        self, kind_id: str, parent_id: str, structure_id: str | None = None
    ) -> Self:
        """Declare a Kind (abstract when structure_id is omitted)."""
        self._kinds.append(Kind(kind_id, parent_id, structure_id))
        return self

    def add_structure(self, structure_id: str, parts: Sequence[Role]) -> Self:
        """Declare a complete, ordered Structure."""
        self._structures.append(Structure(structure_id, tuple(parts)))
        return self

    def add_feature(self, feature_id: str, allowed_kind_ids: Sequence[str]) -> Self:
        """Declare a Feature and the Kind classifications on which it is allowed."""
        if not isinstance(feature_id, str):
            raise TypeError("external Feature ID must be a string")
        if isinstance(allowed_kind_ids, (str, bytes)):
            raise TypeError("allowed_kind_ids must be a sequence of strings")
        ids = tuple(allowed_kind_ids)
        if any(not isinstance(item, str) for item in ids):
            raise TypeError("allowed_kind_ids must be a sequence of strings")
        self._features.append(Feature(feature_id, ids))
        return self

    @staticmethod
    def _feature_ids(features: Sequence[str]) -> tuple[str, ...]:
        if isinstance(features, (str, bytes)):
            raise TypeError("features must be a sequence of strings")
        values = tuple(features)
        if any(not isinstance(item, str) for item in values):
            raise TypeError("features must be a sequence of strings")
        return values

    def add_mapping(
        self,
        target: str | ImportedCall,
        kind_id: str,
        arguments: Sequence[str] | Sequence[Argument],
        *,
        features: Sequence[str] = (),
    ) -> Self:
        """Map a target onto an already-declared concrete Kind.

        Plain argument strings name both the role and accepted keyword.
        Use Argument for different role and keyword names.
        """
        imported = ImportedCall(target) if isinstance(target, str) else target
        if not isinstance(imported, ImportedCall):
            raise TypeError("target must be an ImportedCall or path string")
        if isinstance(arguments, (str, bytes)):
            raise TypeError("arguments must be a sequence of names or Arguments")
        items = tuple(arguments)
        roles = tuple(item for item in items if isinstance(item, str))
        explicit = tuple(item for item in items if isinstance(item, Argument))
        if len(roles) == len(items):
            bindings = tuple(
                Argument(role, position, role) for position, role in enumerate(roles)
            )
        elif len(explicit) == len(items):
            bindings = explicit
        else:
            raise TypeError("arguments must contain only names or only Arguments")
        self._mappings.append(
            CallMapping(imported, kind_id, bindings, self._feature_ids(features))
        )
        return self

    def add_call(
        self,
        target: str | ImportedCall,
        kind_id: str,
        arguments: Sequence[str] | Sequence[Argument],
        *,
        parent_id: str = "model.value",
        structure_id: str | None = None,
        features: Sequence[str] = (),
    ) -> Self:
        """Declare a concrete Kind and map a call to it in one operation.

        Without structure_id, generate a dedicated node-only Structure from
        the supplied argument bindings. With structure_id, reuse an existing
        Structure; its roles and shapes are checked by build().
        """
        self.add_mapping(target, kind_id, arguments, features=features)
        bindings = self._mappings[-1].arguments
        resolved_structure = structure_id or f"{kind_id}.arguments"
        if structure_id is None:
            self.add_structure(
                resolved_structure,
                tuple(Role(binding.role, "node") for binding in bindings),
            )
        self.add_kind(kind_id, parent_id, resolved_structure)
        return self

    def add_type(
        self,
        target: str | ImportedType,
        kind_id: str,
        *,
        parent_id: str = "model.value",
        features: Sequence[str] = (),
    ) -> Self:
        """Declare an annotation-only, zero-role Type Interface."""
        imported = ImportedType(target) if isinstance(target, str) else target
        if not isinstance(imported, ImportedType):
            raise TypeError("target must be an ImportedType or path string")
        self._type_mappings.append(
            TypeMapping(imported, kind_id, self._feature_ids(features))
        )
        structure_id = f"{kind_id}.type"
        self.add_structure(structure_id, ())
        self.add_kind(kind_id, parent_id, structure_id)
        return self

    def add_generic(
        self,
        target: str | ImportedGeneric,
        kind_id: str,
        roles: Sequence[str],
        *,
        parent_id: str = "model.value",
        features: Sequence[str] = (),
    ) -> Self:
        """Declare a fixed-arity positional ``[...]`` interface."""
        imported = ImportedGeneric(target) if isinstance(target, str) else target
        if not isinstance(imported, ImportedGeneric):
            raise TypeError("target must be an ImportedGeneric or path string")
        if isinstance(roles, (str, bytes)):
            raise TypeError("roles must be a sequence of strings")
        values = tuple(roles)
        if any(not isinstance(role, str) for role in values):
            raise TypeError("roles must be a sequence of strings")
        self._generic_mappings.append(
            GenericMapping(imported, kind_id, values, self._feature_ids(features))
        )
        structure_id = f"{kind_id}.generic"
        self.add_structure(structure_id, tuple(Role(role, "node") for role in values))
        self.add_kind(kind_id, parent_id, structure_id)
        return self

    def build(self) -> ExternalDefinitions:
        """Validate and return immutable definitions, with no source imports."""
        return _assemble_external_definitions(
            self._kinds,
            self._structures,
            self._features,
            self._mappings,
            self._type_mappings,
            self._generic_mappings,
            base=self._base,
        )


__all__ = [
    "Argument",
    "CallMapping",
    "ExternalDefinitions",
    "ExternalDefinitionsBuilder",
    "GenericMapping",
    "ImportedCall",
    "ImportedGeneric",
    "ImportedType",
    "Role",
    "TypeMapping",
    "apply_feature",
    "bind",
    "emit",
    "feature_allowed",
    "feature_id",
    "kind_id",
    "load_external_definitions",
    "match",
    "match_generic",
    "match_type",
    "parent_id",
    "part",
    "slot",
    "structure_id",
    "structure_ref",
]
