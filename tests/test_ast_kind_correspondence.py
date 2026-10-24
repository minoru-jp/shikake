"""AST→Kind/Structure/Feature canonical contracts backed by parse_source."""

from __future__ import annotations

import ast
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import shikake
from shikake._mica.model import Model

SPEC_DIR = (
    Path(__file__).resolve().parents[1]
    / "devdocs"
    / "canonical_sources"
    / "specification"
)


@dataclass(frozen=True)
class Case:
    tag: str
    kind: str
    code: str
    path: str = "body.0.value"
    features: tuple[str, ...] = ()


def _catalog() -> dict[str, str]:
    rows: dict[str, str] = {}
    for filename in ("expressions.py", "statements.py"):
        tree = ast.parse((SPEC_DIR / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AugAssign):
                continue
            if not isinstance(node.target, ast.Name) or node.target.id != "detail":
                continue
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            if not value.value.startswith("AST: "):
                continue
            tag, kind = value.value.removeprefix("AST: ").split(" -> ")
            if tag in rows:
                raise AssertionError(f"duplicate AST mapping: {tag}")
            rows[tag] = kind
    return rows


def _node(source: str, path: str) -> Model:
    value: object = shikake.parse_source(source)
    for part in path.split(".") if path else ():
        if part.isdigit():
            assert isinstance(value, tuple)
            value = value[int(part)]
        else:
            assert isinstance(value, Model)
            value = value.get(part)
    assert isinstance(value, Model)
    return value


class AstKindCorrespondenceTests(unittest.TestCase):
    def test_catalog_uses_only_concrete_registered_kinds(self) -> None:
        catalog = _catalog()
        self.assertEqual(len(catalog), 136)
        kinds = {kind.id: kind for kind in shikake.kind_index().all_kinds()}
        for label, kind in catalog.items():
            with self.subTest(label=label):
                self.assertIn(kind, kinds)
                self.assertIsNotNone(kinds[kind].structure_id)

    def test_expressions_match_the_canonical_mapping(self) -> None:
        cases = [
            Case("ast.Name", "model.value.named", "result = name"),
            Case("ast.Constant [ordinary]", "model.value.literal", "result = 42"),
            Case(
                "ast.Constant [None]",
                "model.value.literal.special.none",
                "result = None",
            ),
            Case(
                "ast.Constant [Ellipsis]",
                "model.value.literal.special.ellipsis",
                "result = ...",
            ),
            Case("ast.Attribute", "model.value.access.attribute", "result = a.member"),
            Case("ast.Subscript", "model.value.access.index", "result = a[1:3]"),
            Case(
                "ast.Slice",
                "model.value.slice",
                "result = a[1:3]",
                "body.0.value.index",
            ),
            Case(
                "ast.Tuple [value]",
                "model.value.collection.sequence",
                "result = (a, b)",
            ),
            Case(
                "ast.List [value]", "model.value.collection.sequence", "result = [a, b]"
            ),
            Case("ast.Set", "model.value.collection.set", "result = {a, b}"),
            Case("ast.Dict", "model.value.collection.mapping", "result = {a: b}"),
            Case(
                "ast.Dict [entry]",
                "model.structural_part.dictionary_entry",
                "result = {a: b}",
                "body.0.value.inputs.0",
            ),
            Case(
                "ast.BoolOp [And]",
                "model.value.operation.logical.and",
                "result = a and b",
            ),
            Case(
                "ast.BoolOp [Or]", "model.value.operation.logical.or", "result = a or b"
            ),
            Case("ast.IfExp", "model.value.selection", "result = a if ok else b"),
            Case("ast.NamedExpr", "model.value.binding", "result = (x := foo())"),
            Case(
                "ast.Lambda", "model.value.function_expression", "result = lambda x: x"
            ),
            Case("ast.Call [ordinary]", "model.value.call", "result = fn(a)"),
            Case(
                "ast.keyword [call or class]",
                "model.structural_part.keyword_argument",
                "result = fn(k=a)",
                "body.0.value.arguments.0",
            ),
            Case(
                "ast.Starred [call argument]",
                "model.structural_part.starred_argument",
                "result = fn(*args)",
                "body.0.value.arguments.0",
            ),
            Case(
                "ast.JoinedStr", "model.value.interpolated_string", 'result = f"{x!r}"'
            ),
            Case(
                "ast.FormattedValue",
                "model.structural_part.formatted_field",
                'result = f"{x!r}"',
                "body.0.value.parts.0",
            ),
            Case(
                "ast.ListComp",
                "model.value.collection.sequence",
                "result = [x for x in seq]",
            ),
            Case(
                "ast.SetComp",
                "model.value.collection.set",
                "result = {x for x in seq}",
            ),
            Case(
                "ast.DictComp",
                "model.value.collection.mapping",
                "result = {x: x for x in seq}",
            ),
            Case(
                "ast.GeneratorExp",
                "model.value.comprehension.generator",
                "result = (x for x in seq)",
            ),
            Case(
                "ast.comprehension",
                "model.structural_part.comprehension_clause",
                "result = [x for x in seq]",
                "body.0.value.inputs.0.clauses.0",
            ),
            Case(
                "ast.Starred [value]",
                "model.value.starred_expansion",
                "result = [*seq]",
                "body.0.value.inputs.0",
            ),
            Case(
                "ast.Starred [target]",
                "model.structural_part.starred_target",
                "a, *tail = seq",
                "body.0.targets.0.elements.1",
            ),
            Case(
                "ast.Tuple [target]",
                "model.structural_part.sequence_target",
                "a, b = seq",
                "body.0.targets.0",
            ),
            Case(
                "ast.List [target]",
                "model.structural_part.sequence_target",
                "[a, b] = seq",
                "body.0.targets.0",
            ),
            Case(
                "ast.arg",
                "model.definition.parameter",
                "def f(x): pass",
                "body.0.parameters.0",
            ),
            Case(
                "ast.Await",
                "model.value.await",
                "async def f(): return await fn()",
                "body.0.body.statements.0.value",
            ),
            Case(
                "ast.Yield",
                "model.value.yield",
                "def f(): yield 1",
                "body.0.body.statements.0.value",
            ),
            Case(
                "ast.YieldFrom",
                "model.value.yield_from",
                "def f(): yield from xs",
                "body.0.body.statements.0.value",
            ),
            Case(
                "ast.Compare [chained]",
                "model.value.operation.comparison.chained",
                "result = a < b < c",
            ),
            Case(
                "ast.Compare [chained step]",
                "model.structural_part.comparison_step",
                "result = a < b < c",
                "body.0.value.comparisons.0",
            ),
        ]
        unary = (
            ("Not", "not a", "not"),
            ("UAdd", "+a", "positive"),
            ("USub", "-a", "negative"),
            ("Invert", "~a", "bitwise_invert"),
        )
        for op, expression, name in unary:
            cases.append(
                Case(
                    f"ast.UnaryOp [{op}]",
                    f"model.value.operation.{name}",
                    f"result = {expression}",
                )
            )
        binops = (
            ("Add", "+", "addition"),
            ("Sub", "-", "subtraction"),
            ("Mult", "*", "multiplication"),
            ("MatMult", "@", "matrix_multiplication"),
            ("Div", "/", "division"),
            ("FloorDiv", "//", "floor_division"),
            ("Mod", "%", "modulo"),
            ("Pow", "**", "power"),
            ("LShift", "<<", "left_shift"),
            ("RShift", ">>", "right_shift"),
            ("BitAnd", "&", "bitwise_and"),
            ("BitOr", "|", "bitwise_or"),
            ("BitXor", "^", "bitwise_xor"),
        )
        for op, symbol, name in binops:
            cases.append(
                Case(
                    f"ast.BinOp [{op}]",
                    f"model.value.operation.{name}",
                    f"result = a {symbol} b",
                )
            )
        compares = (
            ("Eq", "==", "equal"),
            ("NotEq", "!=", "not_equal"),
            ("Lt", "<", "less"),
            ("LtE", "<=", "less_equal"),
            ("Gt", ">", "greater"),
            ("GtE", ">=", "greater_equal"),
            ("Is", "is", "is"),
            ("IsNot", "is not", "is_not"),
            ("In", "in", "in"),
            ("NotIn", "not in", "not_in"),
        )
        for op, symbol, name in compares:
            cases.append(
                Case(
                    f"ast.Compare [{op}]",
                    f"model.value.operation.comparison.{name}",
                    f"result = a {symbol} b",
                )
            )
        if sys.version_info >= (3, 14):
            cases.extend(
                [
                    Case(
                        "ast.TemplateStr",
                        "model.value.template_string",
                        'result = t"{value!r}"',
                    ),
                    Case(
                        "ast.Interpolation",
                        "model.structural_part.template_interpolation",
                        'result = t"{value!r}"',
                        "body.0.value.parts.0",
                    ),
                ]
            )
        if sys.version_info >= (3, 15):
            cases.extend(
                [
                    Case(
                        "ast.ListComp [elt is ast.Starred]",
                        "model.value.collection.sequence",
                        "result = [*part for part in groups]",
                    ),
                    Case(
                        "ast.SetComp [elt is ast.Starred]",
                        "model.value.collection.set",
                        "result = {*part for part in groups}",
                    ),
                    Case(
                        "ast.GeneratorExp [elt is ast.Starred]",
                        "model.value.comprehension.generator",
                        "result = (*part for part in groups)",
                    ),
                    Case(
                        "ast.DictComp [value is None]",
                        "model.value.collection.mapping",
                        "result = {**part for part in groups}",
                    ),
                ]
            )
        self._check_cases(cases)

    def test_statements_and_context_sensitive_kinds(self) -> None:
        cases = [
            Case("ast.Module", "model.module", "pass", ""),
            Case("ast.Expr", "model.statement.expression", "1", "body.0"),
            Case("ast.Import", "model.import.direct", "import pkg", "body.0"),
            Case("ast.ImportFrom", "model.import.from", "from pkg import x", "body.0"),
            Case(
                "ast.alias", "model.import.alias", "import pkg as p", "body.0.names.0"
            ),
            Case("ast.Assign", "model.statement.assignment", "x = 1", "body.0"),
            Case(
                "ast.AnnAssign [simple name]",
                "model.definition.variable",
                "x: int",
                "body.0",
            ),
            Case(
                "ast.AnnAssign [other]",
                "model.statement.assignment.annotated",
                "obj.x: int",
                "body.0",
            ),
            Case(
                "ast.FunctionDef [function]",
                "model.definition.function",
                "def f(): pass",
                "body.0",
            ),
            Case(
                "ast.FunctionDef [method]",
                "model.definition.method",
                "class A:\n def f(self): pass",
                "body.0.body.statements.0",
            ),
            Case(
                "ast.FunctionDef [generator]",
                "model.definition.generator",
                "def f(): yield 1",
                "body.0",
            ),
            Case(
                "ast.AsyncFunctionDef [function]",
                "model.definition.function",
                "async def f(): pass",
                "body.0",
                ("async",),
            ),
            Case(
                "ast.AsyncFunctionDef [method]",
                "model.definition.method",
                "class A:\n async def f(self): pass",
                "body.0.body.statements.0",
                ("async",),
            ),
            Case(
                "ast.AsyncFunctionDef [generator]",
                "model.definition.generator",
                "async def f(): yield 1",
                "body.0",
                ("async",),
            ),
            Case("ast.ClassDef", "model.definition.class", "class A: pass", "body.0"),
            Case("ast.If", "model.statement.branch", "if x: pass", "body.0"),
            Case(
                "ast.If [path]",
                "model.structural_part.branch_path",
                "if x: pass",
                "body.0.paths.0",
            ),
            Case(
                "ast.Match",
                "model.statement.branch",
                "match x:\n case 1: pass",
                "body.0",
            ),
            Case(
                "ast.match_case",
                "model.structural_part.branch_path",
                "match x:\n case 1: pass",
                "body.0.paths.0",
            ),
            Case(
                "ast.For",
                "model.statement.control.iteration",
                "for x in seq: pass",
                "body.0",
            ),
            Case(
                "ast.AsyncFor",
                "model.statement.control.iteration",
                "async def f():\n async for x in seq: pass",
                "body.0.body.statements.0",
                ("async",),
            ),
            Case(
                "ast.While",
                "model.statement.control.iteration",
                "while x: break",
                "body.0",
            ),
            Case(
                "ast.Try",
                "model.statement.control.exception_handling",
                "try:\n pass\nexcept Exception:\n pass",
                "body.0",
            ),
            Case(
                "ast.TryStar",
                "model.statement.control.exception_handling",
                "try:\n pass\nexcept* Exception:\n pass",
                "body.0",
            ),
            Case(
                "ast.ExceptHandler",
                "model.structural_part.exception_handler",
                "try:\n pass\nexcept Exception:\n pass",
                "body.0.handlers.0",
            ),
            Case(
                "ast.With",
                "model.statement.control.context_block",
                "with cm() as x: pass",
                "body.0",
            ),
            Case(
                "ast.withitem",
                "model.structural_part.context_entry",
                "with cm() as x: pass",
                "body.0.contexts.0",
            ),
            Case(
                "ast.AsyncWith",
                "model.statement.control.context_block",
                "async def f():\n async with cm(): pass",
                "body.0.body.statements.0",
                ("async",),
            ),
            Case("ast.Assert", "model.statement.assertion", "assert value", "body.0"),
            Case("ast.Delete", "model.statement.deletion", "del value", "body.0"),
            Case("ast.Raise", "model.statement.raise", "raise ValueError()", "body.0"),
            Case(
                "ast.Return",
                "model.statement.return",
                "def f(): return 1",
                "body.0.body.statements.0",
            ),
            Case(
                "ast.Global",
                "model.statement.scope_declaration.global",
                "global value",
                "body.0",
            ),
            Case(
                "ast.Nonlocal",
                "model.statement.scope_declaration.nonlocal",
                "def f():\n x=1\n def g():\n  nonlocal x",
                "body.0.body.statements.1.body.statements.0",
            ),
            Case("ast.Pass", "model.statement.pass", "pass", "body.0"),
            Case(
                "ast.Break",
                "model.statement.break",
                "while True: break",
                "body.0.body.statements.0",
            ),
            Case(
                "ast.Continue",
                "model.statement.continue",
                "while True: continue",
                "body.0.body.statements.0",
            ),
        ]
        binops = (
            ("Add", "+=", "addition"),
            ("Sub", "-=", "subtraction"),
            ("Mult", "*=", "multiplication"),
            ("MatMult", "@=", "matrix_multiplication"),
            ("Div", "/=", "division"),
            ("FloorDiv", "//=", "floor_division"),
            ("Mod", "%=", "modulo"),
            ("Pow", "**=", "power"),
            ("LShift", "<<=", "left_shift"),
            ("RShift", ">>=", "right_shift"),
            ("BitAnd", "&=", "bitwise_and"),
            ("BitOr", "|=", "bitwise_or"),
            ("BitXor", "^=", "bitwise_xor"),
        )
        for op, symbol, kind in binops:
            cases.append(
                Case(
                    f"ast.AugAssign [{op}]",
                    f"model.statement.assignment.augmented.{kind}",
                    f"x {symbol} y",
                    "body.0",
                )
            )
        if sys.version_info >= (3, 12):
            cases += [
                Case(
                    "ast.TypeAlias",
                    "model.definition.type_alias",
                    "type Alias[T] = list[T]",
                    "body.0",
                ),
                Case(
                    "ast.TypeVar",
                    "model.definition.type_parameter.type_variable",
                    "type Alias[T] = T",
                    "body.0.type_parameters.0",
                ),
                Case(
                    "ast.TypeVarTuple",
                    "model.definition.type_parameter.type_variable_tuple",
                    "type Alias[*Ts] = tuple[*Ts]",
                    "body.0.type_parameters.0",
                ),
                Case(
                    "ast.ParamSpec",
                    "model.definition.type_parameter.parameter_specification",
                    "type Alias[**P] = Callable[P, int]",
                    "body.0.type_parameters.0",
                ),
            ]
        self._check_cases(cases)

    def test_match_patterns_and_structural_parts(self) -> None:
        prefix = "match value:\n case "
        patterns = [
            ("ast.MatchValue", "model.pattern.value", "1"),
            ("ast.MatchSingleton", "model.pattern.singleton", "None"),
            ("ast.MatchAs [wildcard]", "model.pattern.wildcard", "_"),
            ("ast.MatchAs [capture]", "model.pattern.capture", "name"),
            ("ast.MatchAs [alias]", "model.pattern.alias", "[x] as name"),
            ("ast.MatchSequence", "model.pattern.sequence", "[x, y]"),
            ("ast.MatchMapping", "model.pattern.mapping", "{'key': x}"),
            ("ast.MatchClass", "model.pattern.class", "Point(x, y=other)"),
            ("ast.MatchOr", "model.pattern.alternative", "1 | 2"),
        ]
        cases = [
            Case(tag, kind, prefix + pattern + ": pass", "body.0.paths.0.pattern")
            for tag, kind, pattern in patterns
        ]
        cases += [
            Case(
                "ast.MatchStar",
                "model.pattern.star",
                prefix + "[*tail]: pass",
                "body.0.paths.0.pattern.elements.0",
            ),
            Case(
                "ast.MatchMapping [entry]",
                "model.structural_part.mapping_pattern_entry",
                prefix + "{'key': x}: pass",
                "body.0.paths.0.pattern.entries.0",
            ),
            Case(
                "ast.MatchClass [keyword]",
                "model.structural_part.named_pattern",
                prefix + "Point(x=name): pass",
                "body.0.paths.0.pattern.keywords.0",
            ),
        ]
        self._check_cases(cases)

    def test_every_documented_mapping_has_an_executable_fixture(self) -> None:
        """Prevent the normative AST catalog from growing untested rows."""
        covered: set[str] = set()

        def capture(_: AstKindCorrespondenceTests, cases: list[Case]) -> None:
            for case in cases:
                self.assertNotIn(case.tag, covered)
                covered.add(case.tag)

        with patch.object(type(self), "_check_cases", capture):
            self.test_expressions_match_the_canonical_mapping()
            self.test_statements_and_context_sensitive_kinds()
            self.test_match_patterns_and_structural_parts()
        expected = set(_catalog())
        if sys.version_info < (3, 12):
            # These AST node types and their source syntax were added in 3.12.
            expected -= {
                "ast.TypeAlias",
                "ast.TypeVar",
                "ast.TypeVarTuple",
                "ast.ParamSpec",
            }
        if sys.version_info < (3, 14):
            expected -= {"ast.TemplateStr", "ast.Interpolation"}
        if sys.version_info < (3, 15):
            expected -= {
                "ast.ListComp [elt is ast.Starred]",
                "ast.SetComp [elt is ast.Starred]",
                "ast.GeneratorExp [elt is ast.Starred]",
                "ast.DictComp [value is None]",
            }
        self.assertEqual(covered, expected)

    def test_async_feature_is_attached_to_exact_construct(self) -> None:
        root = shikake.parse_source("async def f():\n return [x async for x in agen()]")
        function = root.get_nodes("body")[0]
        self.assertEqual(function.features, ("async",))
        comp = function.get_node("body").get_nodes("statements")[0].get_node("value")
        self.assertEqual(comp.kind.id, "model.value.collection.sequence")
        self.assertEqual(comp.features, ())
        self.assertEqual(comp.get("construction"), "comprehension")
        clause = comp.get_nodes("inputs")[0].get_nodes("clauses")[0]
        self.assertEqual(clause.kind.id, "model.structural_part.comprehension_clause")
        self.assertEqual(clause.features, ("async",))
        self.assertTrue(clause.get("is_async"))

    def _check_cases(self, cases: list[Case]) -> None:
        catalog = _catalog()
        for case in cases:
            with self.subTest(ast=case.tag, source=case.code):
                self.assertEqual(catalog[case.tag], case.kind)
                model = _node(case.code, case.path)
                self.assertEqual(model.kind.id, case.kind)
                self.assertEqual(model.features, case.features)
                self.assertEqual(
                    shikake.kind_index().require_structure(case.kind).id,
                    shikake.kind_index().get(case.kind).structure_id,
                )


if __name__ == "__main__":
    unittest.main()
