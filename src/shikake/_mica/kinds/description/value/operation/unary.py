"""Unary operators retain their original operand and operator Kind."""

from ....regulation import kind_id, parent_id, structure_ref


class Unary:
    kind_id @= "model.value.operation.unary"
    structure_ref @= "unary_operand"
    parent_id @= "model.value.operation"


class Not:
    kind_id @= "model.value.operation.not"
    structure_ref @= "unary_operand"
    parent_id @= "model.value.operation.unary"


class Positive:
    kind_id @= "model.value.operation.positive"
    structure_ref @= "unary_operand"
    parent_id @= "model.value.operation.unary"


class Negative:
    kind_id @= "model.value.operation.negative"
    structure_ref @= "unary_operand"
    parent_id @= "model.value.operation.unary"


class BitwiseInvert:
    kind_id @= "model.value.operation.bitwise_invert"
    structure_ref @= "unary_operand"
    parent_id @= "model.value.operation.unary"
