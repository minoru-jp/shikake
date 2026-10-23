"""Augmented assignments are written statements, not expanded operations."""

from ..regulation import kind_id, parent_id, structure_ref


class AugmentedAssignment:
    kind_id @= "model.statement.assignment.augmented"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment"


class AddAssignment:
    kind_id @= "model.statement.assignment.augmented.addition"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class SubAssignment:
    kind_id @= "model.statement.assignment.augmented.subtraction"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class MultAssignment:
    kind_id @= "model.statement.assignment.augmented.multiplication"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class MatMultAssignment:
    kind_id @= "model.statement.assignment.augmented.matrix_multiplication"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class DivAssignment:
    kind_id @= "model.statement.assignment.augmented.division"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class FloorDivAssignment:
    kind_id @= "model.statement.assignment.augmented.floor_division"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class ModAssignment:
    kind_id @= "model.statement.assignment.augmented.modulo"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class PowAssignment:
    kind_id @= "model.statement.assignment.augmented.power"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class LShiftAssignment:
    kind_id @= "model.statement.assignment.augmented.left_shift"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class RShiftAssignment:
    kind_id @= "model.statement.assignment.augmented.right_shift"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class BitAndAssignment:
    kind_id @= "model.statement.assignment.augmented.bitwise_and"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class BitOrAssignment:
    kind_id @= "model.statement.assignment.augmented.bitwise_or"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"


class BitXorAssignment:
    kind_id @= "model.statement.assignment.augmented.bitwise_xor"
    structure_ref @= "single_target_value"
    parent_id @= "model.statement.assignment.augmented"
