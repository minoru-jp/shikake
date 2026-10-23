"""Statement kinds and structural contracts."""

from ..regulation import kind_id, parent_id, structure_ref


class Statement:
    kind_id @= "model.statement"
    parent_id @= "model"


class Block:
    kind_id @= "model.statement.block"
    structure_ref @= "statements_block"
    parent_id @= "model.statement"


class Assignment:
    kind_id @= "model.statement.assignment"
    structure_ref @= "multiple_targets_value"
    parent_id @= "model.statement"


class Branch:
    kind_id @= "model.statement.branch"
    structure_ref @= "branch_paths"
    parent_id @= "model.statement.control"


class Return:
    kind_id @= "model.statement.return"
    structure_ref @= "optional_value"
    parent_id @= "model.statement"


class ExpressionStatement:
    kind_id @= "model.statement.expression"
    structure_ref @= "expression_value"
    parent_id @= "model.statement"


class Raise:
    kind_id @= "model.statement.raise"
    structure_ref @= "raised_exception"
    parent_id @= "model.statement"


class Assertion:
    """Written assertion condition and optional message, without optimization semantics."""

    kind_id @= "model.statement.assertion"
    structure_ref @= "assertion"
    parent_id @= "model.statement"


class Deletion:
    """Written targets in a deletion statement, not its runtime effects."""

    kind_id @= "model.statement.deletion"
    structure_ref @= "ordered_targets"
    parent_id @= "model.statement"


class ScopeDeclaration:
    """Classification only; does not resolve identifiers across scopes."""

    kind_id @= "model.statement.scope_declaration"
    parent_id @= "model.statement"


class GlobalDeclaration:
    kind_id @= "model.statement.scope_declaration.global"
    structure_ref @= "declared_names"
    parent_id @= "model.statement.scope_declaration"


class NonlocalDeclaration:
    kind_id @= "model.statement.scope_declaration.nonlocal"
    structure_ref @= "declared_names"
    parent_id @= "model.statement.scope_declaration"


class Pass:
    """An explicit no-operation statement; not an omitted Model."""

    kind_id @= "model.statement.pass"
    structure_ref @= "empty"
    parent_id @= "model.statement"


class AnnotatedAssignment:
    """An annotation attached to a non-simple target, not a variable definition."""

    kind_id @= "model.statement.assignment.annotated"
    structure_ref @= "annotated_target"
    parent_id @= "model.statement.assignment"
