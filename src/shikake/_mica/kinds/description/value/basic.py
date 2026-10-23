"""Kinds for literal and named values."""

from ...regulation import kind_id, parent_id, structure_ref


class Value:
    kind_id @= "model.value"
    parent_id @= "model"


class Named:
    kind_id @= "model.value.named"
    structure_ref @= "required_name"
    parent_id @= "model.value"


class Literal:
    kind_id @= "model.value.literal"
    structure_ref @= "scalar_value"
    parent_id @= "model.value"


class Slice:
    """One interval selector inside a subscript, including omitted bounds."""

    kind_id @= "model.value.slice"
    structure_ref @= "slice_bounds"
    parent_id @= "model.value"


class InterpolatedString:
    """Ordered literal fragments and formatted expression fields."""

    kind_id @= "model.value.interpolated_string"
    structure_ref @= "string_fragments"
    parent_id @= "model.value"


class TemplateString:
    """Ordered template fragments and preserved interpolation source text."""

    kind_id @= "model.value.template_string"
    structure_ref @= "string_fragments"
    parent_id @= "model.value"


class Selection:
    """A value selected by an expression, distinct from statement blocks."""

    kind_id @= "model.value.selection"
    structure_ref @= "selected_value"
    parent_id @= "model.value"


class SpecialValue:
    """Singleton values directly written in a source expression."""

    kind_id @= "model.value.literal.special"
    structure_ref @= "scalar_value"
    parent_id @= "model.value.literal"


class NoneValue:
    kind_id @= "model.value.literal.special.none"
    structure_ref @= "scalar_value"
    parent_id @= "model.value.literal.special"


class EllipsisValue:
    kind_id @= "model.value.literal.special.ellipsis"
    structure_ref @= "scalar_value"
    parent_id @= "model.value.literal.special"


class BindingExpression:
    """The written binding expression (:=), without simulating assignment."""

    kind_id @= "model.value.binding"
    structure_ref @= "single_target_value"
    parent_id @= "model.value"


class FunctionExpression:
    """Anonymous function expression; no synthesized name or statement block."""

    kind_id @= "model.value.function_expression"
    structure_ref @= "function_expression"
    parent_id @= "model.value"


class Yield:
    """Yield expression including the written omission of its operand."""

    kind_id @= "model.value.yield"
    structure_ref @= "optional_value"
    parent_id @= "model.value"


class YieldFrom:
    """Yield-from expression, with the delegated operand left intact."""

    kind_id @= "model.value.yield_from"
    structure_ref @= "expression_value"
    parent_id @= "model.value"


class Await:
    """Written await operand, without modeling scheduling or suspension."""

    kind_id @= "model.value.await"
    structure_ref @= "expression_value"
    parent_id @= "model.value"


class StarredExpansion:
    """An explicit * unpacking element at a value position."""

    kind_id @= "model.value.starred_expansion"
    structure_ref @= "expression_value"
    parent_id @= "model.value"
