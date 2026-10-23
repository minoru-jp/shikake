"""Pattern structures used as selection criteria, distinct from expressions."""

from ..regulation import kind_id, parent_id, structure_ref


class Pattern:
    kind_id @= "model.pattern"
    parent_id @= "model"


class ValuePattern:
    kind_id @= "model.pattern.value"
    structure_ref @= "expression_value"
    parent_id @= "model.pattern"


class SingletonPattern:
    kind_id @= "model.pattern.singleton"
    structure_ref @= "expression_value"
    parent_id @= "model.pattern"


class CapturePattern:
    kind_id @= "model.pattern.capture"
    structure_ref @= "required_name"
    parent_id @= "model.pattern"


class WildcardPattern:
    kind_id @= "model.pattern.wildcard"
    structure_ref @= "empty"
    parent_id @= "model.pattern"


class SequencePattern:
    kind_id @= "model.pattern.sequence"
    structure_ref @= "ordered_elements"
    parent_id @= "model.pattern"


class MappingPattern:
    kind_id @= "model.pattern.mapping"
    structure_ref @= "pattern_mapping"
    parent_id @= "model.pattern"


class ClassPattern:
    kind_id @= "model.pattern.class"
    structure_ref @= "pattern_class"
    parent_id @= "model.pattern"


class StarPattern:
    kind_id @= "model.pattern.star"
    structure_ref @= "optional_name"
    parent_id @= "model.pattern"


class AliasPattern:
    kind_id @= "model.pattern.alias"
    structure_ref @= "pattern_alias"
    parent_id @= "model.pattern"


class AlternativePattern:
    kind_id @= "model.pattern.alternative"
    structure_ref @= "pattern_alternative"
    parent_id @= "model.pattern"
