"""Logical operations preserve AST operand grouping and order."""

from ....regulation import kind_id, parent_id, structure_ref


class Logical:
    kind_id @= "model.value.operation.logical"
    structure_ref @= "ordered_values"
    parent_id @= "model.value.operation"


class And:
    kind_id @= "model.value.operation.logical.and"
    structure_ref @= "ordered_values"
    parent_id @= "model.value.operation.logical"


class Or:
    kind_id @= "model.value.operation.logical.or"
    structure_ref @= "ordered_values"
    parent_id @= "model.value.operation.logical"
