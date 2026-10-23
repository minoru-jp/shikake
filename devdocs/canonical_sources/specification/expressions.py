"""値式のModel化の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, MUST_NOT, detail, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.layouts import LAYOUTS
from devdocs.canonical_sources.specification.model import MODEL


@summary("値・演算・アクセス・内包表記などの構造契約。")
@canonical_source(
    "{{project.name}}: 値式のModel化",
    filename="expressions.md",
    order=30,
    merge_policy="all",
    heading="identity",
)
class EXPRESSIONS:
    """値・演算・アクセス・内包表記などの構造契約。"""

    class SPEC_001:
        """名前参照は記述された名前をModelに保持する。真偽値と数値・文字列などのリテラルは元のスカラーの型を保持し、`None` と `Ellipsis` は別の特殊リテラルKindとして表現する。名前の値を解決しない。"""

        title @= "名前・リテラル・特殊値"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_002:
        """属性アクセスは対象式と属性名、添字アクセスは対象式と添字式を独立したroleとして保持する。スライスは省略可能なstart/stop/stepを持つ独立した値式とし、添字の内側に置く。"""

        title @= "属性・添字・スライス"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_003:
        """リスト・タプル・集合・辞書リテラル、呼び出し引数および属性連鎖などの採用済み式では、構文上の要素と順序を保持する。実行時の評価順や重複排除を示すものではない。"""

        title @= "式の書字順序"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_004:
        """単項・二項・論理・比較演算を別のPython構文へ展開または正規化してはならない。`-1` を負のリテラルへ潰したり、`a < b < c` を `and` の式へ変換したりしない。"""

        title @= "演算子の非正規化"
        level @= MUST_NOT

    class SPEC_005:
        """二項演算は `left`・`right`、単項演算は `operand` として役割を保持する。演算子の違いは具体Kindで示し、オペランドの構成形状とKindの分類を混同しない。"""

        title @= "二項・単項演算"
        level @= MUST

    class SPEC_006:
        """比較演算は元の比較演算子とオペランド列を保持し、連鎖比較を別の比較へ分解しない。`and` / `or` は個々の具体Kindと順序付きの被演算子列を持つ。"""

        title @= "比較と論理演算"
        level @= MUST

    class SPEC_007:
        """`a if condition else b` は文のbranchではなく値式のselectionとして表現し、`condition`、`when_true`、`when_false` を区別する。式の値を計算しない。"""

        title @= "条件式"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_008:
        """リスト・集合・辞書内包表記とgenerator式は区別する。各comprehension clauseは対象・反復元・フィルタ・非同期の有無を保持し、generatorsの書字順序を保持する。"""

        title @= "内包表記"
        level @= MUST

    class SPEC_009:
        """f-stringは文字列片と埋め込み式を順序付きの要素として保持し、変換フラグや書式指定が記述されていればそれを構造として保持する。埋め込み式を評価しない。"""

        title @= "文字列補間"
        level @= MUST

    class SPEC_010:
        """値位置の `*expr` と代入先のStarredは区別する。代入式 `target := value` は文の通常代入に変換せず独立した値式のbindingとして対象と値を保持する。"""

        title @= "展開と名前付き式"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_011:
        """lambdaは関数式として引数の種類、既定値と本文の構造を保持する。外側の束縛への既定値式中の書き込みと、独立したlambda本体のスコープは区別する。"""

        title @= "Lambda"
        level @= MUST

    class SPEC_012:
        """`yield` は `model.value.yield` の `value: optional_node`、`yield from` は `model.value.yield_from` の `value: node` として区別する。オペランドのない `yield` と明示した `yield None` は同一視しない。`yield from` をfor文や複数のyieldへ展開しない。"""

        title @= "yield式と委譲式"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_013:
        """内包表記の各clauseは `target`、`iterable`、`filters`、`is_async` を持つ。`is_async` は構文上の真偽値を保持し、非同期である節自身にのみ `async` Featureを付与する。内包表記全体を非同期専用のKindへ置き換えない。"""

        title @= "非同期内包節の独立性"
        level @= MUST
        related @= (MODEL.SPEC_006,)

    class SPEC_014:
        """関数・メソッドの呼び出しはcalleeと順序付きのargumentsを保持し、位置引数、キーワード引数、記述された `*`・`**` 展開を区別する。実行時の引数束縛、展開結果、呼び出し先を解釈しない。"""

        title @= "Callの引数構造"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_015:
        """`ast.Name`、通常の `ast.Constant`、`None` と `Ellipsis` のConstantを、以下のKindへ対応付ける。リテラルの保持規則は一般の値式契約に従う。"""

        title @= "単純な値と特殊リテラル"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_036, LAYOUTS.SPEC_037)
        detail @= "AST: ast.Name -> model.value.named"
        detail @= "AST: ast.Constant [ordinary] -> model.value.literal"
        detail @= "AST: ast.Constant [None] -> model.value.literal.special.none"
        detail @= "AST: ast.Constant [Ellipsis] -> model.value.literal.special.ellipsis"

    class SPEC_016:
        """`ast.Attribute`、`ast.Subscript`、`ast.Slice` を、それぞれ属性アクセス、添字アクセス、スライスのKindへ対応付ける。"""

        title @= "アクセスとスライス"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_040,
            LAYOUTS.SPEC_054,
            LAYOUTS.SPEC_055,
        )
        detail @= "AST: ast.Attribute -> model.value.access.attribute"
        detail @= "AST: ast.Subscript -> model.value.access.index"
        detail @= "AST: ast.Slice -> model.value.slice"

    class SPEC_017:
        "値式のリスト・タプル・集合・辞書はそれぞれ固有のKindと宣言順の要素を持つ。辞書の `**` はkeyが省略されたentryで表す。"

        title @= "コレクション"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_026,
            LAYOUTS.SPEC_046,
            LAYOUTS.SPEC_056,
        )
        detail @= "AST: ast.Tuple [value] -> model.value.collection.tuple"
        detail @= "AST: ast.List [value] -> model.value.collection.list"
        detail @= "AST: ast.Set -> model.value.collection.set"
        detail @= "AST: ast.Dict -> model.value.collection.dict"
        detail @= "AST: ast.Dict [entry] -> model.structural_part.dictionary_entry"

    class SPEC_018:
        "演算子の違いを具体Kindに保持し、符号付きリテラルなどへ式を畳み込まない。"

        title @= "単項演算"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_053)
        detail @= "AST: ast.UnaryOp [Not] -> model.value.operation.not"
        detail @= "AST: ast.UnaryOp [UAdd] -> model.value.operation.positive"
        detail @= "AST: ast.UnaryOp [USub] -> model.value.operation.negative"
        detail @= "AST: ast.UnaryOp [Invert] -> model.value.operation.bitwise_invert"

    class SPEC_019:
        "論理演算の種類と順序付きの被演算子列を保持する。短絡評価をシミュレートしない。"

        title @= "論理演算"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_028)
        detail @= "AST: ast.BoolOp [And] -> model.value.operation.logical.and"
        detail @= "AST: ast.BoolOp [Or] -> model.value.operation.logical.or"

    class SPEC_020:
        "各二項演算子を個別の具体Kindに対応させ、同じbinary_operands Structureを共有する。演算結果を計算しない。"

        title @= "二項演算"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_003)
        detail @= "AST: ast.BinOp [Add] -> model.value.operation.addition"
        detail @= "AST: ast.BinOp [Sub] -> model.value.operation.subtraction"
        detail @= "AST: ast.BinOp [Mult] -> model.value.operation.multiplication"
        detail @= (
            "AST: ast.BinOp [MatMult] -> model.value.operation.matrix_multiplication"
        )
        detail @= "AST: ast.BinOp [Div] -> model.value.operation.division"
        detail @= "AST: ast.BinOp [FloorDiv] -> model.value.operation.floor_division"
        detail @= "AST: ast.BinOp [Mod] -> model.value.operation.modulo"
        detail @= "AST: ast.BinOp [Pow] -> model.value.operation.power"
        detail @= "AST: ast.BinOp [LShift] -> model.value.operation.left_shift"
        detail @= "AST: ast.BinOp [RShift] -> model.value.operation.right_shift"
        detail @= "AST: ast.BinOp [BitAnd] -> model.value.operation.bitwise_and"
        detail @= "AST: ast.BinOp [BitOr] -> model.value.operation.bitwise_or"
        detail @= "AST: ast.BinOp [BitXor] -> model.value.operation.bitwise_xor"

    class SPEC_021:
        "比較演算子が1つの場合は演算子別の具体Kind、複数の場合は順序付きのcomparison_stepを持つchained Kindを使う。"

        title @= "単独比較と連鎖比較"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_003,
            LAYOUTS.SPEC_007,
            LAYOUTS.SPEC_044,
        )
        detail @= "AST: ast.Compare [Eq] -> model.value.operation.comparison.equal"
        detail @= (
            "AST: ast.Compare [NotEq] -> model.value.operation.comparison.not_equal"
        )
        detail @= "AST: ast.Compare [Lt] -> model.value.operation.comparison.less"
        detail @= (
            "AST: ast.Compare [LtE] -> model.value.operation.comparison.less_equal"
        )
        detail @= "AST: ast.Compare [Gt] -> model.value.operation.comparison.greater"
        detail @= (
            "AST: ast.Compare [GtE] -> model.value.operation.comparison.greater_equal"
        )
        detail @= "AST: ast.Compare [Is] -> model.value.operation.comparison.is"
        detail @= "AST: ast.Compare [IsNot] -> model.value.operation.comparison.is_not"
        detail @= "AST: ast.Compare [In] -> model.value.operation.comparison.in"
        detail @= "AST: ast.Compare [NotIn] -> model.value.operation.comparison.not_in"
        detail @= (
            "AST: ast.Compare [chained] -> model.value.operation.comparison.chained"
        )
        detail @= (
            "AST: ast.Compare [chained step] -> model.structural_part.comparison_step"
        )

    class SPEC_022:
        "条件式、名前付き式、lambdaはそれぞれ別の値Kindとし、文のbranch・通常代入・関数定義へ変換しない。"

        title @= "選択・名前付き式・Lambda"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_017,
            LAYOUTS.SPEC_038,
            LAYOUTS.SPEC_039,
        )
        detail @= "AST: ast.IfExp -> model.value.selection"
        detail @= "AST: ast.NamedExpr -> model.value.binding"
        detail @= "AST: ast.Lambda -> model.value.function_expression"

    class SPEC_023:
        """登録済み外部構造Callを除いた `ast.Call` と、引数位置の `ast.keyword`・`ast.Starred` を、以下のKindへ対応付ける。"""

        title @= "通常の呼び出しと引数"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_005,
            LAYOUTS.SPEC_015,
            LAYOUTS.SPEC_048,
        )
        detail @= "AST: ast.Call [ordinary] -> model.value.call"
        detail @= (
            "AST: ast.keyword [call or class] -> model.structural_part.keyword_argument"
        )
        detail @= (
            "AST: ast.Starred [call argument] -> model.structural_part.starred_argument"
        )

    class SPEC_024:
        """f-stringを構成する `ast.JoinedStr` と `ast.FormattedValue` を、別々のKindへ対応付ける。"""

        title @= "補間文字列"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_016, LAYOUTS.SPEC_042)
        detail @= "AST: ast.JoinedStr -> model.value.interpolated_string"
        detail @= "AST: ast.FormattedValue -> model.structural_part.formatted_field"

    class SPEC_025:
        "内包表記の種別を独立したKindで保持し、節の反復元・フィルタ・非同期Featureを個別にModel化する。"

        title @= "4種の内包表記"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_009,
            LAYOUTS.SPEC_010,
            LAYOUTS.SPEC_057,
        )
        detail @= "AST: ast.ListComp -> model.value.comprehension.list"
        detail @= "AST: ast.SetComp -> model.value.comprehension.set"
        detail @= "AST: ast.DictComp -> model.value.comprehension.dict"
        detail @= "AST: ast.GeneratorExp -> model.value.comprehension.generator"
        detail @= "AST: ast.comprehension -> model.structural_part.comprehension_clause"

    class SPEC_026:
        """`ast.Await`、`ast.Yield`、`ast.YieldFrom` を、それぞれ固有の値Kindへ対応付ける。"""

        title @= "awaitとyield"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_015, LAYOUTS.SPEC_025)
        detail @= "AST: ast.Await -> model.value.await"
        detail @= "AST: ast.Yield -> model.value.yield"
        detail @= "AST: ast.YieldFrom -> model.value.yield_from"

    class SPEC_027:
        "値位置の星付き展開とターゲット位置の星付き要素を区別する。Tuple/ListターゲットはコレクションKindを再利用しても値を束縛したと確定しない。"

        title @= "展開と代入先"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_015, LAYOUTS.SPEC_026)
        detail @= "AST: ast.Starred [value] -> model.value.starred_expansion"
        detail @= "AST: ast.Starred [target] -> model.structural_part.starred_target"
        detail @= "AST: ast.Tuple [target] -> model.value.collection.tuple"
        detail @= "AST: ast.List [target] -> model.value.collection.list"

    class SPEC_028:
        "パラメータは定義・lambda双方の共通の独立した構造要素とする。パラメータの既定値・注釈を式として保持する。"

        title @= "仮引数"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_030)
        detail @= "AST: ast.arg -> model.definition.parameter"

    class SPEC_029:
        """ASTの補助ノードをすべて独立したModelとみなしてはならない。`ast.operator`・`ast.expr_context` 等の構文上の分類と、引数集合の `ast.arguments` 等は、適切な具体Kind・role・scalarへ反映する。ASTノードとModelの一対一対応を保証しない。"""

        title @= "ASTとModelの非一対一対応"
        level @= MUST_NOT
        related @= (MODEL.SPEC_002, MODEL.SPEC_005)

    class SPEC_030:
        """Python 3.14以降のt-stringをf-stringとは異なるKindで保持する。`ast.TemplateStr` の文字列片と補間の順序を保ち、`ast.Interpolation` は式Model、ASTの `str`（`None` を許容）、`conversion`、`format_spec` を個別のroleとして保持する。補間式の評価・文字列化や書式の実行はしない。旧バージョンにこれらの構文の受理を要求しない。"""

        title @= "Python 3.14のt-string"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_042, LAYOUTS.SPEC_061)
        detail @= "AST: ast.TemplateStr -> model.value.template_string"
        detail @= (
            "AST: ast.Interpolation -> model.structural_part.template_interpolation"
        )

    class SPEC_031:
        """Python 3.15（PEP 798）で導入された展開付き内包表記を構文としてModel化する。`ast.ListComp`・`ast.SetComp`・`ast.GeneratorExp` の直接の `elt` が `ast.Starred` の場合、既存の内包表記Kindと `model.value.starred_expansion` を組み合わせ、要素の展開を保持する。通常のコレクション要素内にある `Starred` はこの条件と区別する。`ast.DictComp.value is None` の場合、`key` が展開対象の式であることを保持し、専用Kind `model.value.comprehension.dict.unpacking` の `mapping: node`・`clauses: nodes` へ対応付ける。通常の辞書内包表記の `key`・`value`・`clauses` は変更しない。値や展開結果の評価、ループへの書き換えは行わない。3.15より前のCPythonでこの記法を構文解析できるとは保証しない。"""

        title @= "Python 3.15の展開付き内包表記（PEP 798）"
        level @= MUST
        related @= (LAYOUTS.SPEC_010, LAYOUTS.SPEC_057, LAYOUTS.SPEC_062)
        detail @= (
            "AST: ast.ListComp [elt is ast.Starred] -> model.value.comprehension.list"
        )
        detail @= (
            "AST: ast.SetComp [elt is ast.Starred] -> model.value.comprehension.set"
        )
        detail @= "AST: ast.GeneratorExp [elt is ast.Starred] -> model.value.comprehension.generator"
        detail @= "AST: ast.DictComp [value is None] -> model.value.comprehension.dict.unpacking"
