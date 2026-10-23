"""Internal shared modeling primitives and the nonrecursive comprehension builder."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..model import Model, SourceSpan

if TYPE_CHECKING:
    from ..parser import _Builder


class UnsupportedSyntaxError(ValueError):
    """A source construct was not adopted by this modeling implementation."""

    def __init__(self, node: ast.AST, detail: str | None = None) -> None:
        self.node_type = type(node).__name__
        self.detail = detail
        self.line = getattr(node, "lineno", None)
        self.column = getattr(node, "col_offset", None)
        position = f" at {self.line}:{self.column}" if self.line is not None else ""
        explanation = f" ({detail})" if detail else ""
        super().__init__(
            f"unsupported Python syntax: {self.node_type}{position}{explanation}"
        )


def _span(node: ast.AST) -> SourceSpan | None:
    line = getattr(node, "lineno", None)
    column = getattr(node, "col_offset", None)
    end_line = getattr(node, "end_lineno", None)
    end_column = getattr(node, "end_col_offset", None)
    if (
        not isinstance(line, int)
        or not isinstance(column, int)
        or not isinstance(end_line, int)
        or not isinstance(end_column, int)
    ):
        return None
    return SourceSpan(line, column, end_line, end_column)


@dataclass(frozen=True, slots=True)
class ExpressionPlan:
    """One claimed AST shape: children first, then construction after children."""

    children: tuple[ast.expr, ...]
    make: Callable[[ast.expr, dict[ast.expr, Model], _Builder], Model]


def comprehension_children(node: ast.expr) -> tuple[ast.expr, ...]:
    """Shared AST traversal shape for the 3.13 and 3.15 comprehension forms."""
    if isinstance(node, ast.DictComp):
        initial = (node.key,) if node.value is None else (node.key, node.value)
    elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        initial = (node.elt,)
    else:
        raise UnsupportedSyntaxError(node)
    return (
        *initial,
        *(child for clause in node.generators for child in (clause.iter, *clause.ifs)),
    )


def build_comprehension(
    node: ast.expr, built: dict[ast.expr, Model], builder: _Builder
) -> Model:
    """Build a comprehension from its already-built children, without recursion."""
    f = builder.factory
    assert isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
    clauses = tuple(
        f.make(
            "model.structural_part.comprehension_clause",
            features=("async",) if item.is_async else (),
            target=builder.target(item.target),
            iterable=built.pop(item.iter),
            filters=tuple(built.pop(test) for test in item.ifs),
            is_async=bool(item.is_async),
        )
        for item in node.generators
    )
    if isinstance(node, ast.DictComp):
        if node.value is None:
            return f.make(
                "model.value.comprehension.dict.unpacking",
                span=_span(node),
                mapping=built.pop(node.key),
                clauses=clauses,
            )
        return f.make(
            "model.value.comprehension.dict",
            span=_span(node),
            key=built.pop(node.key),
            value=built.pop(node.value),
            clauses=clauses,
        )
    kind = {ast.ListComp: "list", ast.SetComp: "set", ast.GeneratorExp: "generator"}[
        type(node)
    ]
    return f.make(
        f"model.value.comprehension.{kind}",
        span=_span(node),
        element=built.pop(node.elt),
        clauses=clauses,
    )
