"""Kinds for accesses written in source code."""

from ...regulation import kind_id, parent_id, structure_ref


class Access:
    kind_id @= "model.value.access"
    parent_id @= "model.value"


class Index:
    kind_id @= "model.value.access.index"
    structure_ref @= "value_access_index"
    parent_id @= "model.value.access"


class Attribute:
    kind_id @= "model.value.access.attribute"
    structure_ref @= "value_access_attribute"
    parent_id @= "model.value.access"
