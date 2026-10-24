"""文・定義のModel化の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, detail, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.expressions import EXPRESSIONS
from devdocs.canonical_sources.specification.layouts import LAYOUTS
from devdocs.canonical_sources.specification.model import MODEL


@summary("代入、制御フロー、定義、import、非同期構文の構造契約。")
@canonical_source(
    "{{project.name}}: 文・定義のModel化",
    filename="statements.md",
    order=40,
    merge_policy="all",
    heading="identity",
)
class STATEMENTS:
    """代入、制御フロー、定義、import、非同期構文の構造契約。"""

    class SPEC_001:
        """`ast.Assign` は一つの文を一つのModelとして保持する。複数のtargetsと単一のvalueを区別し、`a = b = x` を複数文に展開しない。タプル・リストによる分配先も構造を保持する。"""

        title @= "通常代入"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_002:
        """`AugAssign` はtarget、operator、valueを持つ独立の拡張代入Kindとし、通常代入と二項演算へ展開しない。"""

        title @= "拡張代入"
        level @= MUST

    class SPEC_003:
        """注釈付き単純名と、属性・添字などを対象にする注釈は、それぞれの構造上の相違を失わず表す。値のない注釈について、initializerを捏造してはならない。"""

        title @= "注釈付きの対象"
        level @= MUST

    class SPEC_004:
        """`if` / `elif` / `else` と `match` / `case` は、分岐条件またはsubject、順序付き経路、ガード、パターン等の構文上の違いを保持する。分岐の成立可能性を評価しない。"""

        title @= "分岐文"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_005:
        """`match` の採用済みpattern Kindは `value`、`singleton`、`capture`、`wildcard`、`sequence`、`mapping`、`class`、`star`、`alias`、`alternative` の10種類とし、値式と混同せず独立したKindと構成roleで保持する。"""

        title @= "matchパターン"
        level @= MUST

    class SPEC_006:
        """`for` / `async for` / `while` は代入先、反復元、条件、本文、else経路などの該当するroleを区別する。実際に反復される回数や条件の真偽は推測しない。"""

        title @= "反復"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_007:
        """`try` / `try*` は保護本文、順序付きのhandlers、else、finallyを区別する。各handlerは例外の型式、別名、本文を保持する。Python 3.14以降の `except` / `except*` の複数例外指定で括弧を省略しても、括弧付きのタプルと同じ構造にModel化する。括弧の有無や例外発生・制御経路を実行・推測しない。"""

        title @= "例外処理"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_008:
        """`with` / `async with` は順序付きのcontext itemと本文を保持し、各itemの式と省略可能な `as` 対象を区別する。managerを実行した結果は解釈しない。"""

        title @= "コンテキスト管理"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_009:
        """関数・メソッドには引数種別、既定値、デコレータ、返り値注釈、本文を、クラスには名前、基底式、キーワード、デコレータ、本文を保持する。デコレータは実行時の定義へ適用・展開しない。"""

        title @= "関数とクラスの定義"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_010:
        """関数定義自身の本文に属する `yield` / `yield from` が存在するとき、通常のFunction/Method Kindに `generator` Featureを付与する。generator式とは別であり、到達可能性を評価しない。"""

        title @= "Generatorの分類"
        level @= MUST

    class SPEC_011:
        """Class領域内の直接のMethod定義だけでなく、クラス本体中の分岐・反復・例外処理等の内部に記述されたMethod定義を認識する。入れ子の別関数・別クラスの本体には踏み込まない。"""

        title @= "Methodの判定領域"
        level @= MUST

    class SPEC_012:
        """`async def`、`async for`、`async with`、非同期の内包節は対応する同期Kindの構造を原則として共有し、必要な箇所へ `async` Featureを付与する。構文を実行するわけではない。"""

        title @= "非同期の表現"
        level @= MUST
        related @= (MODEL.SPEC_006,)

    class SPEC_013:
        """直接importとfrom-importは独立したKindとして保持し、明示された完全なモジュールパス、導入名、別名と書字順序を失わない。importに伴う実行時のモジュールロードは行わない。"""

        title @= "import構文"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_014:
        """`return`、`raise`、`assert`、`pass`、`break`、`continue`、`del`、`global`、`nonlocal` などの採用済み文は別の構文を捏造せず、式の有無と記述された名前の順序を保持する。`pass` は空の文ModelでありPartialの省略とは異なる。"""

        title @= "その他の採用済み文"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_015:
        """Python 3.12以降の `type Alias = expression` は通常代入と区別した型エイリアス定義として保持し、名前・型パラメータ・値式のroleを失わない。"""

        title @= "型エイリアス"
        level @= MUST

    class SPEC_016:
        """`generator` はFunction/Methodに付くFeatureであり、専用のGenerator KindやStructureを設けない。クラス定義領域にあるgeneratorも通常のMethod Kindのまま扱う。`async` と `generator` は独立して併用できる。"""

        title @= "Generatorの共通Feature"
        level @= MUST
        related @= (MODEL.SPEC_002,)

    class SPEC_017:
        """Generator判定では、対象関数に帰属する `yield` と `yield from` だけを数える。到達不能な分岐中のyieldも数えるが、入れ子関数・クラス・lambdaの本文、およびGenerator式そのものを外側の関数のyieldとして数えない。内側の定義のデコレータ・既定値や内包表記の最初の反復元など、外側の定義に帰属する式は区別する。"""

        title @= "Generatorを判定する式の帰属"
        level @= MUST
        related @= (EXPRESSIONS.SPEC_012,)

    class SPEC_018:
        """`if` と `match` は `model.statement.branch` の `subject: optional_node` と `paths: nodes` を共有する。各経路に条件・パターン・ガード・本文の該当するroleを保持する。`elif` は同一のbranchの経路列となり、明示された `else` 内の別の `if` は独立したbranchのままとする。"""

        title @= "分岐の共通構造"
        level @= MUST
        related @= (MODEL.SPEC_005,)

    class SPEC_019:
        """`return`、`yield`、`assert` 等の省略可能な式・メッセージは `optional_node` で保持する。省略された値は `None` とし、ソース中の明示的な `None` リテラルを表すModelとは区別する。"""

        title @= "省略された文の値と明示されたNone"
        level @= MUST
        related @= (EXPRESSIONS.SPEC_001,)

    class SPEC_020:
        "モジュールの文のまとまりと、式を文位置に書いたことを区別する。"

        title @= "ソース全体と式文"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_015, LAYOUTS.SPEC_022)
        detail @= "AST: ast.Module -> model.module"
        detail @= "AST: ast.Expr -> model.statement.expression"

    class SPEC_021:
        "直接importとfrom-importは異なるKindとし、各import項目の名前と別名は共通のalias要素として表す。"

        title @= "importの構文と各別名"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_018,
            LAYOUTS.SPEC_019,
            LAYOUTS.SPEC_020,
        )
        detail @= "AST: ast.Import -> model.import.direct"
        detail @= "AST: ast.ImportFrom -> model.import.from"
        detail @= "AST: ast.alias -> model.import.alias"

    class SPEC_022:
        """`ast.Assign` と `ast.AnnAssign` を区別し、注釈付き代入は対象が単純名かどうかでVariable定義またはannotated assignmentへ対応付ける。"""

        title @= "通常代入と注釈付き代入"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_001,
            LAYOUTS.SPEC_023,
            LAYOUTS.SPEC_058,
        )
        detail @= "AST: ast.Assign -> model.statement.assignment"
        detail @= "AST: ast.AnnAssign [simple name] -> model.definition.variable"
        detail @= "AST: ast.AnnAssign [other] -> model.statement.assignment.annotated"

    class SPEC_023:
        """`ast.AugAssign` の各演算子を、対応する拡張代入の具体Kindへ対応付ける。"""

        title @= "拡張代入の演算種別"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_039)
        detail @= (
            "AST: ast.AugAssign [Add] -> model.statement.assignment.augmented.addition"
        )
        detail @= "AST: ast.AugAssign [Sub] -> model.statement.assignment.augmented.subtraction"
        detail @= "AST: ast.AugAssign [Mult] -> model.statement.assignment.augmented.multiplication"
        detail @= "AST: ast.AugAssign [MatMult] -> model.statement.assignment.augmented.matrix_multiplication"
        detail @= (
            "AST: ast.AugAssign [Div] -> model.statement.assignment.augmented.division"
        )
        detail @= "AST: ast.AugAssign [FloorDiv] -> model.statement.assignment.augmented.floor_division"
        detail @= (
            "AST: ast.AugAssign [Mod] -> model.statement.assignment.augmented.modulo"
        )
        detail @= (
            "AST: ast.AugAssign [Pow] -> model.statement.assignment.augmented.power"
        )
        detail @= "AST: ast.AugAssign [LShift] -> model.statement.assignment.augmented.left_shift"
        detail @= "AST: ast.AugAssign [RShift] -> model.statement.assignment.augmented.right_shift"
        detail @= "AST: ast.AugAssign [BitAnd] -> model.statement.assignment.augmented.bitwise_and"
        detail @= "AST: ast.AugAssign [BitOr] -> model.statement.assignment.augmented.bitwise_or"
        detail @= "AST: ast.AugAssign [BitXor] -> model.statement.assignment.augmented.bitwise_xor"

    class SPEC_024:
        "関数定義はクラス定義領域かどうかでMethodとFunctionを区別し、yieldの帰属ではKindを変えない。asyncとgeneratorは独立した共通Featureであり、KindとStructureを専用化しない。"

        title @= "関数・Method・Generatorの文脈依存"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_006)
        detail @= "AST: ast.FunctionDef [function] -> model.definition.function"
        detail @= "AST: ast.FunctionDef [method] -> model.definition.method"
        detail @= "AST: ast.FunctionDef [generator] -> model.definition.function"
        detail @= "AST: ast.AsyncFunctionDef [function] -> model.definition.function"
        detail @= "AST: ast.AsyncFunctionDef [method] -> model.definition.method"
        detail @= "AST: ast.AsyncFunctionDef [generator] -> model.definition.function"

    class SPEC_025:
        "クラス定義とPython 3.12以降の型エイリアス定義を異なるKindとして保持し、型パラメータは独立した構造にする。"

        title @= "クラスと型エイリアスの定義"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_008,
            LAYOUTS.SPEC_051,
            LAYOUTS.SPEC_052,
            LAYOUTS.SPEC_059,
        )
        detail @= "AST: ast.ClassDef -> model.definition.class"
        detail @= "AST: ast.TypeAlias -> model.definition.type_alias"
        detail @= "AST: ast.TypeVar -> model.definition.type_parameter.type_variable"
        detail @= "AST: ast.TypeVarTuple -> model.definition.type_parameter.type_variable_tuple"
        detail @= "AST: ast.ParamSpec -> model.definition.type_parameter.parameter_specification"

    class SPEC_026:
        "if/matchはbranch Kindとし、条件式とpatternをそれぞれ独立のbranch_path要素に収める。"

        title @= "ifとmatchの共通分岐"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_004, LAYOUTS.SPEC_043)
        detail @= "AST: ast.If -> model.statement.branch"
        detail @= "AST: ast.Match -> model.statement.branch"
        detail @= "AST: ast.If [path] -> model.structural_part.branch_path"
        detail @= "AST: ast.match_case -> model.structural_part.branch_path"

    class SPEC_027:
        "forとwhileを共通のiteration Kindに保持し、async forだけにasync Featureを付与する。"

        title @= "3種の反復"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_021)
        detail @= "AST: ast.For -> model.statement.control.iteration"
        detail @= "AST: ast.AsyncFor -> model.statement.control.iteration"
        detail @= "AST: ast.While -> model.statement.control.iteration"

    class SPEC_028:
        "tryとtry*は同じKind、`grouped` scalarで区別し、各handlerを独立のstructural_partとして保持する。"

        title @= "例外処理とハンドラ"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_014, LAYOUTS.SPEC_047)
        detail @= "AST: ast.Try -> model.statement.control.exception_handling"
        detail @= "AST: ast.TryStar -> model.statement.control.exception_handling"
        detail @= "AST: ast.ExceptHandler -> model.structural_part.exception_handler"

    class SPEC_029:
        """`ast.With` と `ast.AsyncWith` を同じcontext管理のKindへ対応付け、各context itemを独立の要素とする。非同期の有無はFeatureで区別する。"""

        title @= "withとコンテキスト項目"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_011, LAYOUTS.SPEC_045)
        detail @= "AST: ast.With -> model.statement.control.context_block"
        detail @= "AST: ast.AsyncWith -> model.statement.control.context_block"
        detail @= "AST: ast.withitem -> model.structural_part.context_entry"

    class SPEC_030:
        """`ast.Assert`、`ast.Delete`、`ast.Raise`、`ast.Return` を、それぞれ対応する文Kindへ対応付ける。"""

        title @= "検査と制御の単文"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_002,
            LAYOUTS.SPEC_025,
            LAYOUTS.SPEC_027,
            LAYOUTS.SPEC_035,
        )
        detail @= "AST: ast.Assert -> model.statement.assertion"
        detail @= "AST: ast.Delete -> model.statement.deletion"
        detail @= "AST: ast.Raise -> model.statement.raise"
        detail @= "AST: ast.Return -> model.statement.return"

    class SPEC_031:
        """`ast.Global`、`ast.Nonlocal`、`ast.Pass`、`ast.Break`、`ast.Continue` を、それぞれ対応する文Kindへ対応付ける。"""

        title @= "宣言・空文・ループ制御"
        level @= MUST
        related @= (MODEL.SPEC_005, LAYOUTS.SPEC_012, LAYOUTS.SPEC_013)
        detail @= "AST: ast.Global -> model.statement.scope_declaration.global"
        detail @= "AST: ast.Nonlocal -> model.statement.scope_declaration.nonlocal"
        detail @= "AST: ast.Pass -> model.statement.pass"
        detail @= "AST: ast.Break -> model.statement.break"
        detail @= "AST: ast.Continue -> model.statement.continue"

    class SPEC_032:
        "単純値とsingletonは別Kind、`_` はwildcard、名前はcapture、`as` はaliasとして保持する。"

        title @= "単純・capture・別名のパターン"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_013,
            LAYOUTS.SPEC_015,
            LAYOUTS.SPEC_031,
            LAYOUTS.SPEC_036,
        )
        detail @= "AST: ast.MatchValue -> model.pattern.value"
        detail @= "AST: ast.MatchSingleton -> model.pattern.singleton"
        detail @= "AST: ast.MatchAs [wildcard] -> model.pattern.wildcard"
        detail @= "AST: ast.MatchAs [capture] -> model.pattern.capture"
        detail @= "AST: ast.MatchAs [alias] -> model.pattern.alias"

    class SPEC_033:
        "Star・sequence・mapping・class・orの各patternを値式に変換せず保持する。"

        title @= "集合・選択・クラスのパターン"
        level @= MUST
        related @= (
            MODEL.SPEC_005,
            LAYOUTS.SPEC_024,
            LAYOUTS.SPEC_026,
            LAYOUTS.SPEC_032,
            LAYOUTS.SPEC_033,
            LAYOUTS.SPEC_034,
            LAYOUTS.SPEC_049,
            LAYOUTS.SPEC_050,
        )
        detail @= "AST: ast.MatchStar -> model.pattern.star"
        detail @= "AST: ast.MatchSequence -> model.pattern.sequence"
        detail @= "AST: ast.MatchMapping -> model.pattern.mapping"
        detail @= "AST: ast.MatchClass -> model.pattern.class"
        detail @= "AST: ast.MatchOr -> model.pattern.alternative"
        detail @= "AST: ast.MatchMapping [entry] -> model.structural_part.mapping_pattern_entry"
        detail @= "AST: ast.MatchClass [keyword] -> model.structural_part.named_pattern"
