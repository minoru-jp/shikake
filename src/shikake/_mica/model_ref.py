"""Explicit identity-and-source reference to a Model instance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import Model


@dataclass(frozen=True, slots=True, eq=False, init=False)
class ModelRef:
    """Identify a Model *instance* together with a source path.

    The source path uses ``Path`` equality, not file-system identity. In
    particular, neither path resolution nor a file-existence check is done.
    This type deliberately does not proxy Model attributes or wrap children.
    """

    model: Model
    source_path: Path

    def __init__(self, model: Model, source_path: str | Path) -> None:
        if not isinstance(model, Model):
            raise TypeError("model must be a Model instance")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "source_path", Path(source_path))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelRef):
            return NotImplemented
        return self.model is other.model and self.source_path == other.source_path

    def __hash__(self) -> int:
        return hash((id(self.model), self.source_path))
