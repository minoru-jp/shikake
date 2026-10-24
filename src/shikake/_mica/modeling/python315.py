"""Python 3.15 AST refinements: PEP 798 and explicit lazy import Feature."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ..model import Model
from .common import (
    ExpressionPlan,
    build_comprehension,
    comprehension_children,
)

# Python 3.15 adds frozendict to the built-in namespace (PEP 814).
# Recognition additionally checks the running interpreter's BUILTIN_NAMES.
COLLECTION_BUILTINS_315: dict[str, tuple[str, bool]] = {
    "frozendict": ("mapping", True),
}


if TYPE_CHECKING:
    from ..parser import _Builder


def import_features(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    """Preserve the written lazy modifier, not runtime import scheduling."""
    return ("lazy",) if getattr(node, "is_lazy", False) else ()


def expression_plan(node: ast.expr) -> ExpressionPlan | None:
    # PEP 798 uses existing AST node classes in previously unavailable shapes.
    # Claim them *before* the baseline to avoid silently treating them as old forms.
    if isinstance(node, ast.DictComp) and node.value is None:
        return ExpressionPlan(comprehension_children(node), _build_pep798)
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and isinstance(
        node.elt, ast.Starred
    ):
        return ExpressionPlan(comprehension_children(node), _build_pep798)
    return None


def _build_pep798(
    node: ast.expr, built: dict[ast.expr, Model], builder: _Builder
) -> Model:
    # Non-dictionary flattening retains the existing comprehension/starred Kinds.
    # Dictionary expansion needs its own Structure because there is no value.
    return build_comprehension(node, built, builder)
