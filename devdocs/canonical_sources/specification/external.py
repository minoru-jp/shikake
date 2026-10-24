"""外部構造の任意登録と静的な呼び出し照合の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, MUST_NOT, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.binding import BINDING
from devdocs.canonical_sources.specification.model import MODEL
from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.relations import RELATIONS


@summary("Shikumi外部宣言を利用する構造と登録済み呼び出しの照合契約。")
@canonical_source(
    "{{project.name}}: 外部構造の定義と照合",
    filename="external.md",
    order=70,
    merge_policy="all",
    heading="identity",
)
class EXTERNAL:
    """Shikumi外部宣言を利用する構造と登録済み呼び出しの照合契約。"""

    class SPEC_001:
        """外部構造定義は信頼済みのPythonモジュールまたは `ExternalDefinitions` として `definitions=` に明示的に渡す。解析対象のPythonソースやimport先を定義情報の取得のために実行してはならない。"""

        title @= "外部宣言の分離"
        level @= MUST
        related @= (PARSING.SPEC_001,)

    class SPEC_002:
        """外部定義のCall Mappingは、明示的なimportが対象ターゲットの完全経路へ静的に対応する場合だけ、専用Modelの候補となる。`pkg:Function` のような直接関数と、`pkg:Class.method` のような属性呼び出しを登録できる。通常の `import pkg` のみから書かれていない `pkg.child` を補完せず、静的な経路の照合のためにimport先を実行しない。"""

        title @= "外部Call対象の静的認識"
        level @= MUST
        related @= (RELATIONS.SPEC_006,)

    class SPEC_003:
        """Call Mappingに一致する呼び出しは専用KindへModel化する。登録されていない呼び出しは利用側の規則違反として拒絶せず、通常のCall Modelを保持する。"""

        title @= "登録済み呼び出しの任意適用"
        level @= MUST

    class SPEC_004:
        """外部インターフェースの参照は、値・引数・return・注釈・コンテナ要素・条件式などに現れてもshikakeが使用可否を判定しない。可能な限り通常のPython構造として保持し、採否は利用側に委ねる。"""

        title @= "外部インターフェースの値参照"
        level @= MUST_NOT

    class SPEC_005:
        """外部インターフェース名の再束縛・削除・属性変更は、それ自体を拒絶する理由としない。書かれた構文を通常のModelとして保持し、既存の束縛4軸に収集可能な事実は通常どおり公開する。登録されたCall Interfaceの呼び出し対象は値参照として数えず、使用の適否は利用側が判断する。"""

        title @= "外部名の変更"
        level @= MUST_NOT

    class SPEC_006:
        """複数の明示的importが同じ根を束縛するとき、同じ修飾パスを表すなら照合を維持できる。別の修飾パスを導入する同名aliasと競合する場合は、どの実体を指すか推測せず、そのaliasに対する専用Call認識を行わない。Source自体は拒絶しない。"""

        title @= "競合するimportの保守的な照合"
        level @= MUST
        related @= (RELATIONS.SPEC_006,)

    class SPEC_007:
        """登録済み外部構造呼び出しは、宣言されたMappingに従いKindとStructureへ対応付ける。構造オブジェクト自体を値へ変換したものとして扱わない。"""

        title @= "構造の呼び出し結果"
        level @= MUST
        related @= (MODEL.SPEC_004,)

    class SPEC_008:
        """Call Mappingへの一致失敗や引数の不一致はSourceのエラーではなく、通常のCall Modelへフォールバックする。引数は全件照合し終わるまで既存の子Modelを破壊的に消費せず、失敗時にも通常Callを構築できる状態を保つ。外部Callの不一致を理由とする例外やPartialの文単位回復は行わない。import文は `SPEC_013` の構造化規則に従う。"""

        title @= "不一致時のモデル化"
        level @= MUST
        related @= (PARSING.SPEC_005,)

    class SPEC_009:
        """外部Callの照合に動的alias追跡、任意の呼び出しの副作用、値伝播、他モジュールの実行状態の追跡を追加しない。共通ASTに記録された明示的import経路と書かれた呼び出し形だけを使用する。"""

        title @= "動的解析をしない"
        level @= MUST_NOT
        related @= (BINDING.SPEC_012,)

    class SPEC_010:
        """外部インターフェースの明示的importがモジュール直下の無条件な記述なら、登録済みCallの静的照合を試みる。条件付きimport、関数やクラス内部のimport、およびstar importは外部Callの照合を確定できない場合があるため、専用Model化を保証しない。これらのimport記述自体はshikakeによる外部定義の使用制限としては拒絶しない。"""

        title @= "外部importの認識範囲"
        level @= MUST
        related @= (PARSING.SPEC_005,)

    class SPEC_011:
        """外部インターフェースとして登録されたimport名はshikakeが予約名として保護しない。代入・削除・同名ローカル変数・型パラメータ等に現れた場合も通常のAST構造を保持する。登録済みの名前と実際の実行時参照先の同一性は保証しない。字句スコープで明示的に隠蔽される名前は専用Call・Type・Genericとして認定せず、通常Modelを保持する。lambdaの既定値と内包表記の最初のiterableは外側のスコープで扱う。クラス直下の内包表記の本体からクラス局所名を参照可能とはみなさない。利用側は必要なら束縛事実とModelを検査する。"""

        title @= "外部識別子の束縛は利用側が判断"
        level @= MUST
        related @= (BINDING.SPEC_012, PARSING.SPEC_005)

    class SPEC_012:
        """信頼済みのPythonデータから外部Kind・Structure・CallMappingを構築するビルダーは、Shikumi記述体の読み込み経路と同じKindIndex・Mappingの意味検証を適用しなければならない。直接関数を含むCallターゲット・引数の定義不整合は登録時に拒否する。解析対象のPythonコードや対象モジュールは実行またはimportしない。"""

        title @= "外部定義の共通検証"
        level @= MUST
        related @= (PARSING.SPEC_022,)

    class SPEC_013:
        """4つの解析APIは、import先が外部定義に登録されているかどうかをSourceの採否条件としない。Pythonのパーサ・コンパイラが受け入れ、shikakeがModel化に対応するimport文は通常のModelとして保持する。相対import・star importも外部登録だけを理由として拒否しない。外部Call・Type・Genericとして専用Model化するかどうかは登録済みインターフェースとの静的照合にのみ依存し、登録されないimportも保持する。importの採否は利用側が直接判断するか、明示されたImportPolicyとしてshikakeに委譲できる。対象モジュールの実在・実行時の参照先は確認しない。"""

        title @= "importは構造として保持し採否は利用側に委ねる"
        level @= MUST
        related @= (PARSING.SPEC_008, PARSING.SPEC_020)

    class SPEC_014:
        """信頼済み外部定義はCallに加えてType ReferenceとGeneric Applicationを登録できる。Typeは型注釈・関数の引数や戻り値・type aliasの右辺・基底型・登録済みGeneric引数などの型記述位置でのみ専用KindへModel化し、通常の値参照においては専用Kindへ変換しない。Genericは登録済みの `X[...]` に対して指定された固定位置引数の数と形が一致する場合だけ専用KindへModel化する。Call・Type・Genericは同じ名前に独立して登録できる。出力KindとStructureの整合性は登録時に検証し、型幅・型互換性・型推論などの意味判断は行わない。"""

        title @= "型およびGenericインターフェースの任意登録"
        level @= MUST
        related @= (BINDING.SPEC_018, MODEL.SPEC_004)

    class SPEC_015:
        """登録されたGeneric Interfaceに対する `X[T]` は、型注釈以外でもインターフェース構文としてModel化してよい。この場合、登録されたGenericの主識別子およびその型引数の使用は、通常の値参照として観測しない。引数数・形が登録に合わないときは通常のSubscript Modelを残す。値使用の観測は軽量で網羅性を保証せず、新しい追跡器や型推論を導入しない。未登録の `X[T]` は通常の添字式のままとし、型・Genericインターフェースと推測しない。"""

        title @= "Genericの構文使用と通常の値参照"
        level @= MUST
        related @= (BINDING.SPEC_018,)
