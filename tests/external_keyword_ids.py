"""Trusted Shikumi declarations with Python keywords in qualified IDs."""

from shikake.external import feature_allowed, feature_id, kind_id, parent_id


class KeywordKind:
    kind_id @= "dsl.stmt.return"
    parent_id @= "model.value"


class KeywordFeature:
    feature_id @= "gpu.async"
    feature_allowed @= "dsl.stmt.return"
