"""Private Mica implementation of the shikake public API."""

from .base_references import BaseReference
from .comments import Comment, SourceComments, collect_comments
from .external_structures import ExternalModelingError
from .inspection import (
    InspectionIssue,
    PackageInspection,
    SourceInspection,
    inspect_package,
    inspect_source,
)
from .kinds import Feature, Kind, KindIndex, Structure, kind_index
from .model import Model, ModelPart, SourceSpan
from .package import OverrideCandidate, PackageModel, parse_package
from .parser import UnsupportedSyntaxError, parse_source
from .position import utf8_byte_column_to_character_column
from .relation_facts import BindingState, NameBinding
from .tree_display import format_model_tree

__all__ = [
    "BaseReference",
    "BindingState",
    "Comment",
    "ExternalModelingError",
    "Feature",
    "InspectionIssue",
    "Kind",
    "KindIndex",
    "Model",
    "ModelPart",
    "NameBinding",
    "OverrideCandidate",
    "PackageInspection",
    "PackageModel",
    "SourceComments",
    "SourceInspection",
    "SourceSpan",
    "Structure",
    "UnsupportedSyntaxError",
    "collect_comments",
    "format_model_tree",
    "inspect_package",
    "inspect_source",
    "kind_index",
    "parse_package",
    "parse_source",
    "utf8_byte_column_to_character_column",
]
