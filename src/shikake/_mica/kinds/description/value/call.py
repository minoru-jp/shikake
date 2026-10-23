"""Calls as written; no resolution of call target or effects."""

from ...regulation import kind_id, parent_id, structure_ref


class Call:
    kind_id @= "model.value.call"
    structure_ref @= "call_arguments"
    parent_id @= "model.value"
