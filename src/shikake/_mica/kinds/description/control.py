"""Control-flow kinds: classify by role, not by Python spelling."""

from ..regulation import kind_id, parent_id, structure_ref


class Control:
    kind_id @= "model.statement.control"
    parent_id @= "model.statement"


class Iteration:
    """Enumeration and condition-driven loops share one top-level Kind."""

    kind_id @= "model.statement.control.iteration"
    structure_ref @= "iteration_blocks"
    parent_id @= "model.statement.control"


class ExceptionHandling:
    """Protected operation with ordered exceptional and completion paths."""

    kind_id @= "model.statement.control.exception_handling"
    structure_ref @= "exception_handling"
    parent_id @= "model.statement.control"


class Break:
    kind_id @= "model.statement.break"
    structure_ref @= "empty"
    parent_id @= "model.statement"


class Continue:
    kind_id @= "model.statement.continue"
    structure_ref @= "empty"
    parent_id @= "model.statement"


class ContextBlock:
    """An ordered sequence of context entries enclosing a statement block."""

    kind_id @= "model.statement.control.context_block"
    structure_ref @= "context_block"
    parent_id @= "model.statement.control"
