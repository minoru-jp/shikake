"""Python 3.13-and-earlier baseline expression rules.

The worklist is shared by later version overlays; models remain version-agnostic.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, cast

from ..model import Model
from .common import (
    ExpressionPlan,
    UnsupportedSyntaxError,
    _span,
    build_comprehension,
    comprehension_children,
)
from .python314 import expression_plan as plan314
from .python315 import expression_plan as plan315
from .python315 import import_features

if TYPE_CHECKING:
    from ..parser import _Builder


def select_override(node: ast.expr) -> ExpressionPlan | None:
    """Most recent applicable AST refinement wins; not-applicable is not an error."""
    for rule in (plan315, plan314):
        plan = rule(node)
        if plan is not None:
            return plan
    return None


_BINARY_OPS = {
    ast.Add: "addition",
    ast.Sub: "subtraction",
    ast.Mult: "multiplication",
    ast.MatMult: "matrix_multiplication",
    ast.Div: "division",
    ast.FloorDiv: "floor_division",
    ast.Mod: "modulo",
    ast.Pow: "power",
    ast.LShift: "left_shift",
    ast.RShift: "right_shift",
    ast.BitAnd: "bitwise_and",
    ast.BitOr: "bitwise_or",
    ast.BitXor: "bitwise_xor",
}
_UNARY_OPS = {
    ast.Not: "model.value.operation.not",
    ast.UAdd: "model.value.operation.positive",
    ast.USub: "model.value.operation.negative",
    ast.Invert: "model.value.operation.bitwise_invert",
}
_COMPARISON_KINDS = {
    ast.Eq: ("equal", "=="),
    ast.NotEq: ("not_equal", "!="),
    ast.Lt: ("less", "<"),
    ast.LtE: ("less_equal", "<="),
    ast.Gt: ("greater", ">"),
    ast.GtE: ("greater_equal", ">="),
    ast.Is: ("is", "is"),
    ast.IsNot: ("is_not", "is not"),
    ast.In: ("in", "in"),
    ast.NotIn: ("not_in", "not in"),
}


def _expression_children(builder: _Builder, current: ast.expr) -> tuple[ast.expr, ...]:
    """Choose the AST children to visit before constructing this expression.

    Child selection and Model construction are separate steps: the worklist
    remains iterative and neither pass attempts value/type inference.
    """
    if isinstance(current, ast.BoolOp):
        if not isinstance(current.op, (ast.And, ast.Or)):
            raise UnsupportedSyntaxError(
                current, f"operator {type(current.op).__name__}"
            )
        children = tuple(current.values)
    elif isinstance(current, ast.BinOp):
        if type(current.op) not in _BINARY_OPS:
            raise UnsupportedSyntaxError(
                current, f"operator {type(current.op).__name__}"
            )
        children = (current.left, current.right)
    elif isinstance(current, ast.UnaryOp):
        if type(current.op) not in _UNARY_OPS:
            raise UnsupportedSyntaxError(
                current, f"operator {type(current.op).__name__}"
            )
        children = (current.operand,)
    elif isinstance(current, ast.Attribute):
        children = (current.value,)
    elif isinstance(current, ast.Subscript):
        children = (current.value, current.slice)
    elif isinstance(current, ast.IfExp):
        children = (current.test, current.body, current.orelse)
    elif isinstance(current, ast.Call):
        # Arguments are checked before the callee, as previously.
        children = (
            *(
                arg.value if isinstance(arg, ast.Starred) else arg
                for arg in current.args
            ),
            *(kw.value for kw in current.keywords),
            current.func,
        )
    elif isinstance(current, ast.Lambda):
        children = (
            *builder._parameter_expressions(current.args),
            current.body,
        )
    elif isinstance(current, ast.Slice):
        children = tuple(
            child
            for child in (current.lower, current.upper, current.step)
            if child is not None
        )
    elif isinstance(current, (ast.Await, ast.Yield, ast.YieldFrom, ast.Starred)):
        children = (current.value,) if current.value is not None else ()
    elif isinstance(current, ast.JoinedStr):
        children = tuple(current.values)
    elif isinstance(current, ast.FormattedValue):
        if current.conversion not in (-1, ord("s"), ord("r"), ord("a")):
            raise UnsupportedSyntaxError(
                current, "unknown string interpolation conversion"
            )
        children = (
            (current.value, current.format_spec)
            if current.format_spec is not None
            else (current.value,)
        )
    elif isinstance(current, ast.NamedExpr):
        children = (current.value,)
    elif isinstance(current, (ast.Tuple, ast.List, ast.Set)):
        children = tuple(current.elts)
    elif isinstance(current, ast.Dict):
        children = tuple(
            child
            for key, value in zip(current.keys, current.values, strict=True)
            for child in ((key, value) if key is not None else (value,))
        )
    elif isinstance(
        current, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
    ):
        if isinstance(current, ast.DictComp) and current.value is None:
            raise UnsupportedSyntaxError(
                current, "dictionary comprehension without value"
            )
        children = comprehension_children(current)
    elif isinstance(current, ast.Compare):
        if not current.ops or any(
            type(op) not in _COMPARISON_KINDS for op in current.ops
        ):
            raise UnsupportedSyntaxError(current, "unknown comparison operator")
        children = (current.left, *current.comparators)
    elif isinstance(current, (ast.Name, ast.Constant)):
        children = ()
    else:
        raise UnsupportedSyntaxError(current)
    return children


def build_expression(
    builder: _Builder, node: ast.expr, *, type_context: bool = False
) -> Model:
    """Build expression Models bottom-up without recursive expression calls.

    All supported expression families share this worklist. Comprehension
    targets and lambda parameters are delegated to their dedicated shape
    builders, which do not descend into the containing expression node.
    """
    f = builder.factory
    pending: list[tuple[ast.expr, bool, bool]] = [(node, False, type_context)]
    built: dict[ast.expr, Model] = {}
    planned: dict[ast.expr, ExpressionPlan] = {}
    while pending:
        current, ready, in_type = pending.pop()
        if not ready:
            # Newer syntax owns its AST shape before the 3.13 baseline can claim it.
            override = select_override(current)
            if override is not None:
                planned[current] = override
                pending.append((current, True, in_type))
                pending.extend(
                    (child, False, in_type) for child in reversed(override.children)
                )
                continue
            children = _expression_children(builder, current)
            pending.append((current, True, in_type))
            # Generic application is syntax, not value-reference, including
            # types nested inside its arguments. No general type inference.
            generic = (
                builder.external.generic_mapping(current.value)
                if isinstance(current, ast.Subscript) and builder.external is not None
                else None
            )
            generic_slice = (
                current.slice
                if isinstance(current, ast.Subscript) and generic is not None
                else None
            )
            parameter_annotations = (
                builder._annotation_expressions(current.args)
                if isinstance(current, ast.Lambda)
                else frozenset()
            )
            pending.extend(
                (
                    child,
                    False,
                    in_type
                    or (child is generic_slice)
                    or child in parameter_annotations,
                )
                for child in reversed(children)
            )
            continue

        override = planned.pop(current, None)
        if override is not None:
            built[current] = override.make(current, built, builder)
            continue
        span = _span(current)
        if isinstance(current, ast.Name):
            type_mapping = (
                builder.external.type_mapping(current)
                if in_type and builder.external is not None
                else None
            )
            model = (
                f.make(type_mapping.kind_id, span=span, features=type_mapping.features)
                if type_mapping is not None
                else f.make("model.value.named", span=span, name=current.id)
            )
        elif isinstance(current, ast.Constant):
            value = current.value
            if value is None:
                model = f.make(
                    "model.value.literal.special.none", span=span, value=None
                )
            elif value is Ellipsis:
                model = f.make(
                    "model.value.literal.special.ellipsis",
                    span=span,
                    value=Ellipsis,
                )
            elif isinstance(value, (str, int, float, complex, bool, bytes)):
                model = f.make("model.value.literal", span=span, value=value)
            else:
                raise UnsupportedSyntaxError(current, "literal value type")
        elif isinstance(current, ast.BoolOp):
            op_kind = (
                "model.value.operation.logical.and"
                if isinstance(current.op, ast.And)
                else "model.value.operation.logical.or"
            )
            model = f.make(
                op_kind,
                span=span,
                values=tuple(built.pop(item) for item in current.values),
            )
        elif isinstance(current, ast.BinOp):
            model = f.make(
                f"model.value.operation.{_BINARY_OPS[type(current.op)]}",
                span=span,
                left=built.pop(current.left),
                right=built.pop(current.right),
            )
        elif isinstance(current, ast.UnaryOp):
            model = f.make(
                _UNARY_OPS[type(current.op)],
                span=span,
                operand=built.pop(current.operand),
            )
        elif isinstance(current, ast.Attribute):
            type_mapping = (
                builder.external.type_mapping(current)
                if in_type and builder.external is not None
                else None
            )
            if type_mapping is not None:
                built.pop(current.value)
                model = f.make(
                    type_mapping.kind_id, span=span, features=type_mapping.features
                )
            else:
                model = f.make(
                    "model.value.access.attribute",
                    span=span,
                    target=built.pop(current.value),
                    attribute=current.attr,
                )
        elif isinstance(current, ast.Subscript):
            generic_mapping = (
                builder.external.generic_mapping(current.value)
                if builder.external is not None
                else None
            )
            specialized = (
                builder.external.try_build_generic(current, generic_mapping, built, f)
                if generic_mapping is not None and builder.external is not None
                else None
            )
            model = (
                specialized
                if specialized is not None
                else f.make(
                    "model.value.access.index",
                    span=span,
                    target=built.pop(current.value),
                    index=built.pop(current.slice),
                )
            )
        elif isinstance(current, ast.IfExp):
            model = f.make(
                "model.value.selection",
                span=span,
                condition=built.pop(current.test),
                when_true=built.pop(current.body),
                when_false=built.pop(current.orelse),
            )
        elif isinstance(current, ast.Call):
            mapping = (
                builder.external.mapping(current)
                if builder.external is not None
                else None
            )
            if mapping is not None and builder.external is not None:
                external_model = builder.external.try_build(
                    current, mapping, built, f, span=span
                )
                if external_model is not None:
                    built[current] = external_model
                    continue
            call_parts: list[tuple[ast.AST, Model]] = []
            for arg in current.args:
                item = (
                    f.make(
                        "model.structural_part.starred_argument",
                        span=_span(arg),
                        value=built.pop(arg.value),
                    )
                    if isinstance(arg, ast.Starred)
                    else built.pop(arg)
                )
                call_parts.append((arg, item))
            for kw in current.keywords:
                item = f.make(
                    "model.structural_part.keyword_argument",
                    span=_span(kw),
                    name=kw.arg,
                    value=built.pop(kw.value),
                )
                call_parts.append((kw, item))
            call_parts.sort(
                key=lambda pair: (
                    getattr(pair[0], "lineno", -1),
                    getattr(pair[0], "col_offset", -1),
                )
            )
            inputs = tuple(item for _, item in call_parts)
            collection = (
                builder.collections.collection(current)
                if builder.collections is not None
                else None
            )
            if collection is not None:
                category, immutable = collection
                # The callee's AST has been retained only for recognition;
                # the Collection input structure describes construction.
                built.pop(current.func)
                model = f.make(
                    f"model.value.collection.{category}",
                    span=span,
                    construction="builtin",
                    immutable=immutable,
                    inputs=inputs,
                )
            else:
                model = f.make(
                    "model.value.call",
                    span=span,
                    callee=built.pop(current.func),
                    arguments=inputs,
                )
        elif isinstance(current, ast.Lambda):
            model = f.make(
                "model.value.function_expression",
                span=span,
                parameters=builder._parameters(current.args, prebuilt=built),
                body=built.pop(current.body),
            )
        elif isinstance(current, ast.Slice):
            model = f.make(
                "model.value.slice",
                span=span,
                start=built.pop(current.lower) if current.lower is not None else None,
                stop=built.pop(current.upper) if current.upper is not None else None,
                step=built.pop(current.step) if current.step is not None else None,
            )
        elif isinstance(current, ast.Yield):
            model = f.make(
                "model.value.yield",
                span=span,
                value=built.pop(current.value) if current.value is not None else None,
            )
        elif isinstance(current, (ast.Await, ast.YieldFrom, ast.Starred)):
            kind = {
                ast.Await: "model.value.await",
                ast.YieldFrom: "model.value.yield_from",
                ast.Starred: "model.value.starred_expansion",
            }[type(current)]
            model = f.make(kind, span=span, value=built.pop(current.value))
        elif isinstance(current, ast.JoinedStr):
            model = f.make(
                "model.value.interpolated_string",
                span=span,
                parts=tuple(built.pop(item) for item in current.values),
            )
        elif isinstance(current, ast.FormattedValue):
            conversions = {-1: None, ord("s"): "s", ord("r"): "r", ord("a"): "a"}
            model = f.make(
                "model.structural_part.formatted_field",
                span=span,
                value=built.pop(current.value),
                conversion=conversions[current.conversion],
                format_spec=built.pop(current.format_spec)
                if current.format_spec is not None
                else None,
            )
        elif isinstance(current, ast.NamedExpr):
            model = f.make(
                "model.value.binding",
                span=span,
                target=builder.target(current.target),
                value=built.pop(current.value),
            )
        elif isinstance(current, (ast.Tuple, ast.List, ast.Set)):
            kind = "set" if isinstance(current, ast.Set) else "sequence"
            model = f.make(
                f"model.value.collection.{kind}",
                span=span,
                construction="literal",
                immutable=isinstance(current, ast.Tuple),
                inputs=tuple(built.pop(item) for item in current.elts),
            )
        elif isinstance(current, ast.Dict):
            model = f.make(
                "model.value.collection.mapping",
                span=span,
                construction="literal",
                immutable=False,
                inputs=tuple(
                    f.make(
                        "model.structural_part.dictionary_entry",
                        span=_span(value),
                        key=built.pop(key) if key is not None else None,
                        value=built.pop(value),
                    )
                    for key, value in zip(current.keys, current.values, strict=True)
                ),
            )
        elif isinstance(
            current, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
        ):
            model = build_comprehension(current, built, builder)
        elif isinstance(current, ast.Compare):
            operators = [_COMPARISON_KINDS[type(op)] for op in current.ops]
            if len(operators) == 1:
                model = f.make(
                    f"model.value.operation.comparison.{operators[0][0]}",
                    span=span,
                    left=built.pop(current.left),
                    right=built.pop(current.comparators[0]),
                )
            else:
                model = f.make(
                    "model.value.operation.comparison.chained",
                    span=span,
                    left=built.pop(current.left),
                    comparisons=tuple(
                        f.make(
                            "model.structural_part.comparison_step",
                            span=_span(right),
                            operator=operator[1],
                            right=built.pop(right),
                        )
                        for operator, right in zip(
                            operators, current.comparators, strict=True
                        )
                    ),
                )
        else:
            raise UnsupportedSyntaxError(current)
        built[current] = model
    return built.pop(node)


def build_statement(
    builder: _Builder, node: ast.stmt, *, class_body: bool = False
) -> Model:
    f = builder.factory
    span = _span(node)
    if isinstance(node, ast.Import):
        return f.make(
            "model.import.direct",
            span=span,
            features=import_features(node),
            names=tuple(
                f.make(
                    "model.import.alias",
                    span=_span(alias),
                    name=alias.name,
                    asname=alias.asname,
                )
                for alias in node.names
            ),
        )
    if isinstance(node, ast.ImportFrom):
        return f.make(
            "model.import.from",
            span=span,
            features=import_features(node),
            module=node.module,
            level=node.level,
            names=tuple(
                f.make(
                    "model.import.alias",
                    span=_span(alias),
                    name=alias.name,
                    asname=alias.asname,
                )
                for alias in node.names
            ),
        )
    if type(node).__name__ == "TypeAlias":
        alias = cast(ast.AST, node)
        name_node = getattr(alias, "name", None)
        if not isinstance(name_node, ast.Name):
            raise UnsupportedSyntaxError(node, "invalid type alias name")
        value = getattr(alias, "value", None)
        if not isinstance(value, ast.expr):
            raise UnsupportedSyntaxError(node, "invalid type alias value")
        return f.make(
            "model.definition.type_alias",
            span=span,
            name=name_node.id,
            type_parameters=builder._type_parameters(getattr(alias, "type_params", ())),
            value=builder.expression(value, type_context=True),
        )
    if isinstance(node, ast.AnnAssign):
        # A bare, simple name retains the established Variable definition.
        # Parenthesized names and access targets have a different written
        # shape: do not pretend they are bare variable definitions.
        if isinstance(node.target, ast.Name) and node.simple:
            return f.make(
                "model.definition.variable",
                span=span,
                name=node.target.id,
                annotation=builder.expression(node.annotation, type_context=True),
                initializer=builder.expression(node.value)
                if node.value is not None
                else None,
            )
        return f.make(
            "model.statement.assignment.annotated",
            span=span,
            target=builder.target(node.target),
            annotation=builder.expression(node.annotation, type_context=True),
            value=builder.expression(node.value) if node.value is not None else None,
            simple=bool(node.simple),
        )
    if isinstance(node, ast.ClassDef):
        return f.make(
            "model.definition.class",
            span=span,
            name=node.name,
            type_parameters=builder._type_parameters(getattr(node, "type_params", ())),
            bases=tuple(
                builder.expression(base, type_context=True) for base in node.bases
            ),
            keywords=tuple(
                f.make(
                    "model.structural_part.keyword_argument",
                    span=_span(item),
                    name=item.arg,
                    value=builder.expression(item.value),
                )
                for item in node.keywords
            ),
            decorators=tuple(builder.expression(item) for item in node.decorator_list),
            body=builder.block(node.body, class_body=True),
        )
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return builder._function(node, method=class_body)
    if isinstance(node, ast.Assign):
        if node.type_comment is not None:
            raise UnsupportedSyntaxError(node, "assignment type comment")
        return f.make(
            "model.statement.assignment",
            span=span,
            targets=tuple(builder.target(item) for item in node.targets),
            value=builder.expression(node.value),
        )
    if isinstance(node, ast.AugAssign):
        augmented_kinds = {
            ast.Add: "addition",
            ast.Sub: "subtraction",
            ast.Mult: "multiplication",
            ast.MatMult: "matrix_multiplication",
            ast.Div: "division",
            ast.FloorDiv: "floor_division",
            ast.Mod: "modulo",
            ast.Pow: "power",
            ast.LShift: "left_shift",
            ast.RShift: "right_shift",
            ast.BitAnd: "bitwise_and",
            ast.BitOr: "bitwise_or",
            ast.BitXor: "bitwise_xor",
        }
        operator = augmented_kinds.get(type(node.op))
        if operator is None:
            raise UnsupportedSyntaxError(node, "unknown augmented assignment")
        return f.make(
            f"model.statement.assignment.augmented.{operator}",
            span=span,
            target=builder.expression(node.target),
            value=builder.expression(node.value),
        )
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return builder._context_block(node, class_body=class_body)
    if isinstance(node, ast.Assert):
        return f.make(
            "model.statement.assertion",
            span=span,
            condition=builder.expression(node.test),
            message=builder.expression(node.msg) if node.msg is not None else None,
        )
    if isinstance(node, ast.Delete):
        return f.make(
            "model.statement.deletion",
            span=span,
            targets=tuple(builder.target(item) for item in node.targets),
        )
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        qualifier = "global" if isinstance(node, ast.Global) else "nonlocal"
        return f.make(
            f"model.statement.scope_declaration.{qualifier}",
            span=span,
            names=tuple(node.names),
        )
    if isinstance(node, ast.Pass):
        return f.make("model.statement.pass", span=span)
    if isinstance(node, ast.If):
        return builder._conditional_branch(node, class_body=class_body)
    if isinstance(node, ast.Match):
        return builder._pattern_branch(node, class_body=class_body)
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
        return builder._iteration(node, class_body=class_body)
    if isinstance(node, (ast.Try, ast.TryStar)):
        return builder._exception_handling(node, class_body=class_body)
    if isinstance(node, ast.Break):
        return f.make("model.statement.break", span=span)
    if isinstance(node, ast.Continue):
        return f.make("model.statement.continue", span=span)
    if isinstance(node, ast.Expr):
        return f.make(
            "model.statement.expression",
            span=span,
            value=builder.expression(node.value),
        )
    if isinstance(node, ast.Raise):
        return f.make(
            "model.statement.raise",
            span=span,
            exception=builder.expression(node.exc) if node.exc is not None else None,
            cause=builder.expression(node.cause) if node.cause is not None else None,
        )
    if isinstance(node, ast.Return):
        return f.make(
            "model.statement.return",
            span=span,
            value=builder.expression(node.value) if node.value is not None else None,
        )
    raise UnsupportedSyntaxError(node)
