"""Definition kinds and structural contracts."""

from ..regulation import kind_id, parent_id, structure_ref


class Definition:
    kind_id @= "model.definition"
    parent_id @= "model"


class Variable:
    kind_id @= "model.definition.variable"
    structure_ref @= "variable_definition"
    parent_id @= "model.definition"


class Function:
    kind_id @= "model.definition.function"
    structure_ref @= "callable_definition"
    parent_id @= "model.definition"


class Parameter:
    kind_id @= "model.definition.parameter"
    structure_ref @= "parameter_definition"
    parent_id @= "model.definition"


class Class:
    kind_id @= "model.definition.class"
    structure_ref @= "class_definition"
    parent_id @= "model.definition"


class Method:
    kind_id @= "model.definition.method"
    structure_ref @= "callable_definition"
    parent_id @= "model.definition.function"


class TypeAlias:
    """A declared type alias, distinct from ordinary assignment."""

    kind_id @= "model.definition.type_alias"
    structure_ref @= "type_alias_definition"
    parent_id @= "model.definition"


class TypeParameter:
    """Classification-only parent of generic type parameter declarations."""

    kind_id @= "model.definition.type_parameter"
    parent_id @= "model.definition"


class TypeVariable:
    kind_id @= "model.definition.type_parameter.type_variable"
    structure_ref @= "type_variable_parameter"
    parent_id @= "model.definition.type_parameter"


class TypeVariableTuple:
    kind_id @= "model.definition.type_parameter.type_variable_tuple"
    structure_ref @= "variadic_type_parameter"
    parent_id @= "model.definition.type_parameter"


class ParameterSpecification:
    kind_id @= "model.definition.type_parameter.parameter_specification"
    structure_ref @= "variadic_type_parameter"
    parent_id @= "model.definition.type_parameter"
