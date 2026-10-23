"""Single comparisons and ordered chained comparisons without rewriting."""

from ....regulation import kind_id, parent_id, structure_ref


class Comparison:
    kind_id @= "model.value.operation.comparison"
    parent_id @= "model.value.operation"


class Equal:
    kind_id @= "model.value.operation.comparison.equal"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class NotEqual:
    kind_id @= "model.value.operation.comparison.not_equal"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class Less:
    kind_id @= "model.value.operation.comparison.less"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class LessEqual:
    kind_id @= "model.value.operation.comparison.less_equal"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class Greater:
    kind_id @= "model.value.operation.comparison.greater"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class GreaterEqual:
    kind_id @= "model.value.operation.comparison.greater_equal"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class Is:
    kind_id @= "model.value.operation.comparison.is"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class IsNot:
    kind_id @= "model.value.operation.comparison.is_not"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class In:
    kind_id @= "model.value.operation.comparison.in"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class NotIn:
    kind_id @= "model.value.operation.comparison.not_in"
    structure_ref @= "binary_operands"
    parent_id @= "model.value.operation.comparison"


class ChainedComparison:
    kind_id @= "model.value.operation.comparison.chained"
    structure_ref @= "chained_comparison"
    parent_id @= "model.value.operation.comparison"
