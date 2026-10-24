"""Cross-cutting features, independent from Kind and Structure declarations."""

from ..regulation import feature_allowed, feature_id


class Async:
    feature_id @= "async"
    feature_allowed @= "model.definition.function"
    feature_allowed @= "model.statement.control.iteration"
    feature_allowed @= "model.statement.control.context_block"
    feature_allowed @= "model.structural_part.comprehension_clause"


class Generator:
    """A function or method body containing its own yield/yield from."""

    feature_id @= "generator"
    feature_allowed @= "model.definition.function"


class Lazy:
    feature_id @= "lazy"
    feature_allowed @= "model.import.direct"
    feature_allowed @= "model.import.from"
