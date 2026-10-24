"""One syntax-only enumeration of child statement blocks for model and facts."""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatementBranch:
    statements: list[ast.stmt]
    # These are only syntactic branch headers; interpreting bindings belongs to
    # the lexical fact collector, not this shared AST shape enumeration.
    elif_header: ast.If | None = None
    pattern: ast.pattern | None = None
    handler: ast.ExceptHandler | None = None


def statement_branches(node: ast.stmt) -> tuple[StatementBranch, ...]:
    """List child blocks in source order, including an iterative elif chain."""
    if isinstance(node, ast.If):
        branches: list[StatementBranch] = []
        current = node
        while True:
            branches.append(
                StatementBranch(
                    current.body,
                    elif_header=current if current is not node else None,
                )
            )
            if (
                len(current.orelse) == 1
                and isinstance(current.orelse[0], ast.If)
                and current.orelse[0].col_offset == current.col_offset
            ):
                current = current.orelse[0]
                continue
            if current.orelse:
                branches.append(StatementBranch(current.orelse))
            return tuple(branches)
    if isinstance(node, ast.Match):
        return tuple(
            StatementBranch(case.body, pattern=case.pattern) for case in node.cases
        )
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return (StatementBranch(node.body), StatementBranch(node.orelse))
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return (StatementBranch(node.body),)
    if isinstance(node, (ast.Try, ast.TryStar)):
        return (
            StatementBranch(node.body),
            *(
                StatementBranch(handler.body, handler=handler)
                for handler in node.handlers
            ),
            StatementBranch(node.orelse),
            StatementBranch(node.finalbody),
        )
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return (StatementBranch(node.body),)
    return ()
