"""Public API for shikake, backed by private Mica implementation modules."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

from ._mica import (
    BaseReference,
    BindingState,
    Comment,
    Feature,
    ImportPolicy,
    ImportPolicyError,
    InspectionIssue,
    Kind,
    KindIndex,
    Model,
    ModelPart,
    NameBinding,
    OverrideCandidate,
    PackageInspection,
    PackageModel,
    SourceComments,
    SourceInspection,
    SourceSpan,
    Structure,
    UnsupportedSyntaxError,
    collect_comments,
    format_model_tree,
    inspect_package,
    inspect_source,
    kind_index,
    parse_package,
    parse_source,
    utf8_byte_column_to_character_column,
)

try:
    __version__ = _distribution_version("shikake")
except PackageNotFoundError:
    # A source checkout can be imported before an editable installation.
    import tomllib as _tomllib
    from pathlib import Path as _Path

    __version__ = _tomllib.loads(
        (_Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )["project"]["version"]

__all__ = [
    "BaseReference",
    "BindingState",
    "Comment",
    "Feature",
    "ImportPolicy",
    "ImportPolicyError",
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
