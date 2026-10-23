"""Binary operators are kept as written, without semantic expansion."""

from ....regulation import kind_id, parent_id, structure_ref


class Operation:
    kind_id @= "model.value.operation"
    parent_id @= "model.value"


class Addition:
    kind_id @= "model.value.operation.addition"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class Subtraction:
    kind_id @= "model.value.operation.subtraction"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class Multiplication:
    kind_id @= "model.value.operation.multiplication"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class MatrixMultiplication:
    kind_id @= "model.value.operation.matrix_multiplication"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class Division:
    kind_id @= "model.value.operation.division"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class FloorDivision:
    kind_id @= "model.value.operation.floor_division"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class Modulo:
    kind_id @= "model.value.operation.modulo"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class Power:
    kind_id @= "model.value.operation.power"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class LeftShift:
    kind_id @= "model.value.operation.left_shift"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class RightShift:
    kind_id @= "model.value.operation.right_shift"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class BitwiseAnd:
    kind_id @= "model.value.operation.bitwise_and"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class BitwiseOr:
    kind_id @= "model.value.operation.bitwise_or"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"


class BitwiseXor:
    kind_id @= "model.value.operation.bitwise_xor"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation"
