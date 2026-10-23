"""Python 3.14 AST refinements: template strings and interpolations."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, cast

from ..model import Model
from .common import ExpressionPlan, UnsupportedSyntaxError, _span

if TYPE_CHECKING:
    from ..parser import _Builder

_TEMPLATE_STR = getattr(ast, "TemplateStr", None)
_INTERPOLATION = getattr(ast, "Interpolation", None)


def expression_plan(node: ast.expr) -> ExpressionPlan | None:
    if _TEMPLATE_STR is not None and isinstance(node, _TEMPLATE_STR):
        return ExpressionPlan(tuple(cast(ast.JoinedStr, node).values), _build_template)
    if _INTERPOLATION is not None and isinstance(node, _INTERPOLATION):
        field = cast(ast.FormattedValue, node)
        if field.conversion not in (-1, ord("s"), ord("r"), ord("a")):
            raise UnsupportedSyntaxError(
                node, "unknown string interpolation conversion"
            )
        raw_text = getattr(node, "str", None)
        if raw_text is not None and not isinstance(raw_text, str):
            raise UnsupportedSyntaxError(node, "invalid interpolation text")
        children = (
            (field.value,)
            if field.format_spec is None
            else (field.value, field.format_spec)
        )
        return ExpressionPlan(children, _build_interpolation)
    return None


def _build_template(
    node: ast.expr, built: dict[ast.expr, Model], builder: _Builder
) -> Model:
    template = cast(ast.JoinedStr, node)
    return builder.factory.make(
        "model.value.template_string",
        span=_span(node),
        parts=tuple(built.pop(item) for item in template.values),
    )


def _build_interpolation(
    node: ast.expr, built: dict[ast.expr, Model], builder: _Builder
) -> Model:
    field = cast(ast.FormattedValue, node)
    conversions = {-1: None, ord("s"): "s", ord("r"): "r", ord("a"): "a"}
    return builder.factory.make(
        "model.structural_part.template_interpolation",
        span=_span(node),
        value=built.pop(field.value),
        expression_text=getattr(node, "str", None),
        conversion=conversions[field.conversion],
        format_spec=built.pop(field.format_spec)
        if field.format_spec is not None
        else None,
    )
