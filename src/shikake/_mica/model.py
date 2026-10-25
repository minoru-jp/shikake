"""Concrete Model data, kept separate from Kind classification."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from types import EllipsisType
from typing import TypeAlias, TypeVar, cast, overload

from .kinds import DefinitionIndex, Kind

Scalar: TypeAlias = str | int | float | complex | bool | bytes | None | EllipsisType
PartValue: TypeAlias = "Model | tuple[Model, ...] | tuple[str, ...] | Scalar"
_T = TypeVar("_T")


def _scalar_equal(left: object, right: object) -> bool:
    """Compare stored scalar data, not Python numeric coercion rules."""
    return type(left) is type(right) and left == right


def _scalar_hash(value: Scalar) -> int:
    """Include the concrete scalar type in the structural hash."""
    return hash((type(value), value))


def _part_value_equal(left: PartValue, right: PartValue) -> bool:
    """Compare a standalone ModelPart with the same scalar rules as Model."""
    if isinstance(left, Model) or isinstance(right, Model):
        return isinstance(left, Model) and isinstance(right, Model) and left == right
    if isinstance(left, tuple) or isinstance(right, tuple):
        if not isinstance(left, tuple) or not isinstance(right, tuple):
            return False
        if len(left) != len(right):
            return False
        for a, b in zip(left, right, strict=True):
            if isinstance(a, Model) or isinstance(b, Model):
                if not isinstance(a, Model) or not isinstance(b, Model) or a != b:
                    return False
            elif not _scalar_equal(a, b):
                return False
        return True
    return _scalar_equal(left, right)


def _part_value_hash(value: PartValue) -> int:
    if isinstance(value, Model):
        return hash(value)
    if isinstance(value, tuple):
        return hash(
            tuple(
                hash(item) if isinstance(item, Model) else _scalar_hash(item)
                for item in value
            )
        )
    return _scalar_hash(value)


# Repr is a bounded diagnostic summary, not a serialization of the Model tree.
_MODEL_REPR_MAX = 512
_PART_REPR_MAX = 256


def _clip_repr(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _short_text(value: str, limit: int = 48) -> str:
    # Slice before repr to avoid allocating the escaped form of a huge string.
    sample = value[:32]
    result = repr(sample)
    if len(value) > 32:
        result += f"... (len={len(value)})"
    return _clip_repr(result, limit)


def _summary(value: PartValue) -> str:
    """Describe only the immediate value without visiting child Models."""
    if isinstance(value, Model):
        return f"<Model {_short_text(value.kind.id, 48)}>"
    if isinstance(value, tuple):
        return f"<{len(value)} items>"
    if isinstance(value, str):
        return _short_text(value, 96)
    if isinstance(value, bytes):
        sample = value[:24]
        result = repr(sample)
        if len(value) > 24:
            result += f"... (len={len(value)})"
        return _clip_repr(result, 96)
    if isinstance(value, int) and value.bit_length() > 256:
        # Python limits conversion of very large integers to decimal strings.
        return f"<int {value.bit_length()} bits>"
    return _clip_repr(repr(value), 96)


def _parts_summary(parts: tuple[ModelPart, ...]) -> str:
    shown = [
        f"{_short_text(part.role, 36)}: {_summary(part.value)}" for part in parts[:5]
    ]
    if len(parts) > 5:
        shown.append(f"... ({len(parts) - 5} more parts)")
    return ", ".join(shown)


def _features_summary(features: tuple[str, ...]) -> str:
    shown = [_short_text(feature, 40) for feature in features[:4]]
    if len(features) > 4:
        shown.append(f"... ({len(features) - 4} more)")
    return "(" + ", ".join(shown) + ")"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class ModelPart:
    role: str
    value: PartValue

    def __repr__(self) -> str:
        """Bounded one-level diagnostic representation (never expand child Models)."""
        return _clip_repr(
            f"ModelPart(role={_short_text(self.role, 48)}, value={_summary(self.value)})",
            _PART_REPR_MAX,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelPart):
            return NotImplemented
        return self.role == other.role and _part_value_equal(self.value, other.value)

    def __hash__(self) -> int:
        return hash((self.role, _part_value_hash(self.value)))


class _StructuralHashStorage:
    """An internal slot, deliberately absent from Model's dataclass fields.

    An inherited slot preserves the public dataclass field layout. In particular,
    dataclass serialization does not persist a process-specific cached hash.
    """

    __slots__ = ("_cached_structural_hash",)

    _cached_structural_hash: int | None


def _get_cached_hash(model: Model) -> int | None:
    # Fresh Models initialize the slot. Older/unpickled/copied Models may not.
    return getattr(model, "_cached_structural_hash", None)


def _save_cached_hash(model: Model, value: int) -> None:
    # Only the derived, immutable hash is mutable; the Model data stays frozen.
    object.__setattr__(model, "_cached_structural_hash", value)


def _compute_model_hash(root: Model) -> int:
    """Compute and cache hashes bottom-up without recursion.

    Reuse cached descendants and save newly computed hashes for every Model
    visited, including shared descendants. Each Model's structural hash is
    independent of the path from which the node is reached.
    """
    pending: list[tuple[Model, bool]] = [(root, False)]
    hashes: dict[int, int] = {}
    while pending:
        current, ready = pending.pop()
        identity = id(current)
        if not ready:
            if identity in hashes:
                continue
            cached = _get_cached_hash(current)
            if cached is not None:
                hashes[identity] = cached
                continue
            pending.append((current, True))
            for part in current._parts:
                value = part.value
                if isinstance(value, Model):
                    pending.append((value, False))
                elif isinstance(value, tuple):
                    pending.extend(
                        (item, False) for item in value if isinstance(item, Model)
                    )
            continue
        if identity in hashes:
            continue
        role_hashes: list[tuple[str, int]] = []
        for part in current._parts:
            value = part.value
            if isinstance(value, Model):
                value_hash = hashes[id(value)]
            elif isinstance(value, tuple):
                value_hash = hash(
                    tuple(
                        hashes[id(item)]
                        if isinstance(item, Model)
                        else _scalar_hash(item)
                        for item in value
                    )
                )
            else:
                value_hash = _scalar_hash(value)
            role_hashes.append((part.role, value_hash))
        computed = hash(
            (current.kind, tuple(role_hashes), current.span, current.features)
        )
        hashes[identity] = computed
        _save_cached_hash(current, computed)
    return hashes[id(root)]


@dataclass(frozen=True, slots=True)
class Model(_StructuralHashStorage):
    kind: Kind
    _parts: tuple[ModelPart, ...]
    span: SourceSpan | None = None
    features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Avoid AttributeError on every cold cache read during tree hashing.
        object.__setattr__(self, "_cached_structural_hash", None)

    def __repr__(self) -> str:
        """Show a compact, non-recursive overview for debugging and logs."""
        span = self.span
        location = (
            "None"
            if span is None
            else f"{span.line}:{span.column}-{span.end_line}:{span.end_column}"
        )
        result = (
            f"Model(kind={_short_text(self.kind.id)}, span={location}, "
            f"features={_features_summary(self.features)}, "
            f"parts=({_parts_summary(self._parts)}))"
        )
        return _clip_repr(result, _MODEL_REPR_MAX)

    def __eq__(self, other: object) -> bool:
        """Compare complete structures without descending the Python call stack."""
        if not isinstance(other, Model):
            return NotImplemented
        pending: list[tuple[Model, Model]] = [(self, other)]
        while pending:
            left, right = pending.pop()
            if (
                left.kind != right.kind
                or left.span != right.span
                or left.features != right.features
                or len(left._parts) != len(right._parts)
            ):
                return False
            for a, b in zip(left._parts, right._parts, strict=True):
                if a.role != b.role:
                    return False
                if isinstance(a.value, Model) and isinstance(b.value, Model):
                    pending.append((a.value, b.value))
                elif isinstance(a.value, tuple) and isinstance(b.value, tuple):
                    if len(a.value) != len(b.value):
                        return False
                    for av, bv in zip(a.value, b.value, strict=True):
                        if isinstance(av, Model) and isinstance(bv, Model):
                            pending.append((av, bv))
                        elif (
                            isinstance(av, Model)
                            or isinstance(bv, Model)
                            or not _scalar_equal(av, bv)
                        ):
                            return False
                elif (
                    isinstance(a.value, Model)
                    or isinstance(b.value, Model)
                    or not _scalar_equal(a.value, b.value)
                ):
                    return False
        return True

    def __hash__(self) -> int:
        """Hash immutable structure iteratively, caching visited Models."""
        cached = _get_cached_hash(self)
        if cached is not None:
            return cached
        return _compute_model_hash(self)

    def parts(self) -> tuple[ModelPart, ...]:
        """All declared roles, including scalar values and absent optional nodes."""
        return self._parts

    def get(self, role: str) -> PartValue:
        for part in self._parts:
            if part.role == role:
                return part.value
        raise KeyError(role)

    @overload
    def get_scalar(self, role: str) -> Scalar: ...

    @overload
    def get_scalar(self, role: str, expected_type: type[_T]) -> _T: ...

    def get_scalar(
        self, role: str, expected_type: type[object] | None = None
    ) -> object:
        """Return a scalar without coercion; optionally require an exact Python type.

        An unknown role raises KeyError. Model values, tuples and other
        non-scalars raise TypeError. The optional type comparison uses `type`
        rather than `isinstance`, so bool is never accepted as int.
        """
        value = self.get(role)
        if type(value) not in (
            str,
            int,
            float,
            complex,
            bool,
            bytes,
            type(None),
            EllipsisType,
        ):
            raise TypeError(f"{self.kind.id}.{role} is not a scalar")
        if expected_type is not None and type(value) is not expected_type:
            raise TypeError(
                f"{self.kind.id}.{role} is not exactly {expected_type.__name__}"
            )
        return value

    def get_node(self, role: str) -> Model:
        """Return a single Model, rejecting absent or differently shaped values.

        An unknown role raises KeyError; a present non-Model value (including
        None for an absent optional node) raises TypeError.
        """
        value = self.get(role)
        if not isinstance(value, Model):
            raise TypeError(f"{self.kind.id}.{role} is not a Model")
        return value

    def get_nodes(self, role: str) -> tuple[Model, ...]:
        """Return a tuple of Models, rejecting other value shapes."""
        value = self.get(role)
        if not isinstance(value, tuple) or not all(
            isinstance(item, Model) for item in value
        ):
            raise TypeError(f"{self.kind.id}.{role} is not a Model sequence")
        return cast(tuple[Model, ...], value)

    def get_name(self, role: str) -> str:
        """Return a text-valued role, rejecting other value shapes."""
        value = self.get(role)
        if not isinstance(value, str):
            raise TypeError(f"{self.kind.id}.{role} is not text")
        return value

    def walk(self) -> Iterator[Model]:
        """Depth-first pre-order over Model-valued parts in declaration order.

        An explicit stack avoids Python call-stack growth for deep Models.
        """
        pending: list[Model] = [self]
        while pending:
            current = pending.pop()
            yield current
            children: list[Model] = []
            for part in current.parts():
                value = part.value
                if isinstance(value, Model):
                    children.append(value)
                elif isinstance(value, tuple):
                    children.extend(item for item in value if isinstance(item, Model))
            pending.extend(reversed(children))


class ModelFactory:
    """Validate concrete Models using the Kind's referenced Structure."""

    def __init__(self, kinds: DefinitionIndex) -> None:
        self.kinds = kinds

    def make(
        self,
        kind_id: str,
        *,
        span: SourceSpan | None = None,
        features: tuple[str, ...] = (),
        **values: PartValue,
    ) -> Model:
        kind = self.kinds.get(kind_id)
        self.kinds.validate_features(kind_id, features)
        structure = self.kinds.structure_of(kind_id)
        if structure is None:
            raise ValueError(f"{kind_id}: abstract Kind has no Structure")
        expected = {spec.role for spec in structure.parts}
        if values.keys() != expected:
            raise ValueError(
                f"{kind_id}: expected roles {sorted(expected)}, got {sorted(values)}"
            )
        for spec in structure.parts:
            value = values[spec.role]
            if spec.shape == "node":
                valid = isinstance(value, Model)
            elif spec.shape == "optional_node":
                valid = value is None or isinstance(value, Model)
            elif spec.shape == "nodes":
                valid = isinstance(value, tuple) and all(
                    isinstance(item, Model) for item in value
                )
            elif spec.shape == "texts":
                valid = isinstance(value, tuple) and all(
                    isinstance(item, str) for item in value
                )
            elif spec.shape == "text":
                valid = isinstance(value, str)
            elif spec.shape == "optional_text":
                valid = value is None or isinstance(value, str)
            elif spec.shape == "scalar":
                valid = (
                    isinstance(value, (str, int, float, complex, bool, bytes))
                    or value is None
                    or value is Ellipsis
                )
            else:
                raise ValueError(f"unknown part shape: {spec.shape}")
            if not valid:
                raise TypeError(f"{kind_id}.{spec.role} must have shape {spec.shape}")
        return Model(
            kind,
            tuple(ModelPart(s.role, values[s.role]) for s in structure.parts),
            span,
            tuple(sorted(features)),
        )
