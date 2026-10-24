"""字句スコープと束縛の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.statements import STATEMENTS


@summary("識別子の導入・変更・削除・値参照についての軽量な4軸。")
@canonical_source(
    "{{project.name}}: 字句スコープと束縛",
    filename="binding.md",
    order=50,
    merge_policy="all",
    heading="identity",
)
class BINDING:
    """識別子の導入・変更・削除・値参照についての軽量な4軸。"""

    class SPEC_001:
        """束縛の性質は参照式の値やFeatureではなく、字句スコープに属する識別子の構文上の事実として扱う。導入形式、再束縛可能性、喪失可能性、値としての使用の観測を独立に収集する。これらの4軸は読み取り時点での確定代入を保証せず、4軸のみを根拠に確定代入を認定してはならない。"""

        title @= "束縛情報の対象"
        level @= MUST
        related @= (PARSING.SPEC_002,)

    class SPEC_002:
        """`BindingState.introduction` は識別子の導入が構文上明快な形式であるかを表す。通常の導入には `stable` と `unstable` を用い、暗黙の組み込み導入には `builtin`、登録済み外部インターフェースの明示的な安定導入には `external` を用いる。`builtin` と `external` は安定した導入の特化であり、識別子の利用許可を意味しない。`stable` には最初の独立した導入が無条件かつ競合のない形で書かれていることが必要だが、それだけでは十分ではない。`n += 1` のように既存の束縛を読み取る増分代入は単独で安定した導入とみなさず、他の導入がなければ `unstable` とする。複合文による条件性、既知の競合、または導入に不要なモジュール直下の `global` 宣言があれば `unstable` とする。Pythonの実行結果の安定性や一般的なコード品質を評価するものではない。"""

        title @= "導入の安定性"
        level @= MUST

    class SPEC_003:
        """`may_rebind=True` は対象の字句スコープにおける最初の構文上の導入（組み込み名では暗黙の初期導入）とは別の導入・書き込み、または繰り返され得る書き込み・増分代入が記述されることを意味する。最初の通常代入 `x = 1` だけならFalse、`x = 1; x = 2` ならTrueとする。`for` / `while` 本体や内包表記内の反復し得る単独書き込みはTrueとする。一方 `if` 内に一度だけ記述された条件付き導入それ自体は、導入が `unstable` でも追加の書き込みがなければFalseとする。繰り返しの回数や実行経路を評価せず、読み取り時点の代入確定性も表さない。"""

        title @= "再束縛可能性"
        level @= MUST

    class SPEC_004:
        """`may_delete=True` は明示的な `del`、または `except ... as X` / `except* ... as X` に構文仕様が直接規定する暗黙の削除があることを意味する。削除の実行可能性や順序を調べない。"""

        title @= "喪失可能性"
        level @= MUST

    class SPEC_005:
        """複合文 `if`、`while`、`for`、`async for`、`try`、`try*`（`except*` を含む）、`with`、`async with`、`match` のヘッダーおよび本体に書かれた導入は `unstable` とする。この複合文の対象は列挙したAST構文に限り、関数・クラス定義の本体は `SPEC_006` に従って別の字句スコープとして扱う。`if True` も例外とせず、条件式を評価して `stable` に救済しない。ループの本体・反復ターゲットにある書き込みは繰り返され得るため、最初の導入であっても `may_rebind=True` とする。式の内側で評価が省略され得る導入は別の規則として扱う。"""

        title @= "複合文の保守判定"
        level @= MUST

    class SPEC_006:
        """関数・クラス等の新たな字句スコープ内部に、外側の複合文の条件性を自動的に伝播させない。条件付きの定義文自身の導入と、定義内部での導入を区別する。"""

        title @= "独立した字句スコープ"
        level @= MUST

    class SPEC_007:
        """lambdaの位置・キーワード専用既定値式および `except` / `except*` の型式中の代入式は、その式が属する外側のスコープの書き込みとして記録する。lambda本体の内部スコープとは混同しない。"""

        title @= "式の書き込み"
        level @= MUST

    class SPEC_008:
        """`B: type` のような値のない注釈は束縛を発生させず、それだけを根拠に4軸を生成しない。ただし関数内ではローカル名の宣言として作用するため、同名の外側の対象へ解決してはならない。"""

        title @= "値なし注釈"
        level @= MUST

    class SPEC_009:
        """組み込み名の暗黙導入も含め、識別子の導入状態を認定できなければ `binding=None` とする。候補がない・誤りである・不安定であるなどの意味を付け足すステータスを設けない。"""

        title @= "取得不能な束縛"
        level @= MUST

    class SPEC_010:
        """star importにより導入される名前も、既知識別子との競合も推論しない。4軸、継承候補、組み込みCollection正規化のいずれにもその影響を反映しない。import文のModel自体は保持し、利用側が必要な判断を行う。"""

        title @= "star importの制限"
        level @= MUST

    class SPEC_011:
        """パッケージが属性名を明示的に定義し、同名のサブモジュールも存在する場合、導入の競合は `unstable` とする。候補の探索可否は別に扱う。"""

        title @= "パッケージ属性と同名サブモジュール"
        level @= MUST

    class SPEC_012:
        """代入、削除、import経路、字句スコープ、条件付き導入、値参照の観測に利用するAST事実は既存の共通収集結果を用いる。外部構造の使用規則を強制するために独立した追跡器を設けてはならない。"""

        title @= "共通のAST事実"
        level @= MUST

    class SPEC_013:
        """`global`・`nonlocal` は名前の束縛先を識別する構文事実として扱う。モジュール直下の `global X` はPythonの束縛先を変更しないが、同じモジュールで導入される `X` に不要なスコープ宣言が付いているため、その導入を `unstable` と判定する。宣言だけでは束縛を生成せず、`may_rebind`・`may_delete` は書き込み・削除の構文事実に基づいて別途判定する。"""

        title @= "宣言による束縛先の識別"
        level @= MUST

    class SPEC_014:
        """`PackageModel.name_bindings` は各 `NameBinding(module, scope, name, state, scope_kind)` を列挙し、`bindings_for(scope_model, name)` は渡されたModelと同一identityに属する束縛を照会する。`NameBinding.state` は `BindingState` の4軸を保持する。PEP 695の注釈スコープと定義本体スコープは同一の定義Modelを `scope` として共有する場合があり、 `scope_kind`（`module` / `class` / `function` / `annotation`）で字句的に区別する。照会は同一Modelに結び付いた別種の字句スコープを両方返し得る。利用者が手作りしたNameBindingはこの項目を省略でき、省略時はNoneとなる。関係解析を指定しなくてもこの情報は取得可能で、別のスコープや参照先モジュールの束縛を合成しない。組み込み名に限り、モジュールModelへの `bindings_for()` 照会時に、列挙されていない暗黙導入を必要時に補完する（`SPEC_017`）。"""

        title @= "NameBindingの取得単位"
        level @= MUST
        related @= (PARSING.SPEC_016,)

    class SPEC_015:
        """関数の引数名はその関数の字句スコープへの構文上の導入として扱うが、引数があることだけを理由に `may_rebind=True` としてはならない。引数名への追加の代入・再導入・削除は、通常のAST操作事実として独立に記録する。"""

        title @= "引数名の導入と再束縛"
        level @= MUST
        related @= (STATEMENTS.SPEC_009,)

    class SPEC_016:
        """式の評価規則により選択的・反復的・省略可能な位置にある導入は `unstable` とする。対象には `and` / `or` の第2被演算子以降、条件式の分岐側、内包表記の要素・各節、`assert` 内の式、連鎖比較の第2比較式以降を含む。短絡演算の先頭、条件式のテスト、比較の最初の比較式は、その構文だけでは条件付きとしない。内包表記内の代入式は反復し得る書き込みとして記録する。外側で既に条件付きならその性質を保持し、値・反復回数・最適化設定を評価して `stable` に救済しない。"""

        title @= "式の選択的評価と導入の安定性"
        level @= MUST

    class SPEC_017:
        """対象Pythonバージョンに固定された標準組み込み名前は、各モジュール冒頭で暗黙に導入されたものとみなし、`BindingState.introduction="builtin"` を返す。これは安定した暗黙の導入という**構文解析上の前提**であり、実行時の組み込みオブジェクトの解決・不変性を保証しない。モジュールスコープで当該名への最初の明示的な書き込みがあれば `may_rebind=True` とし、削除があれば `may_delete=True` とする。star importによる競合可能性は判定に含めない。`global` 書き込みはそのモジュールへ帰属させる。関数・クラス・型パラメータなど別スコープの同名の導入は組み込み導入と合成せず、既存の通常の4軸を適用する。
        - 対象名の集合は実行インタープリターのPythonマイナーバージョン別に固定する。`site`による `exit`・`help` などの追加、`gettext.install()`、実行中の `builtins` 辞書の変更では集合を変えない。`__builtins__`・`globals()`・`locals()` の動的変更も追跡しない。Python 3.15からは `frozendict`、`sentinel`、`ImportCycleError`、`__lazy_import__` を含む。CPythonの分離起動（`-S -I`）で得た標準の組み込み名と固定集合の一致をバージョン別CIで検査する。対象Pythonバージョン間でModelが変わり得ることは明示的に許容する。
        - `PackageModel.bindings_for(実在するモジュールModel, name)` と完全な `SourceInspection.bindings_for(モジュールModel, name)` は、組み込み名であればソースに書き込みがなくても必要時に仮想的な `NameBinding` を返す。identityが異なるModel、別スコープ、または不完全なPartial結果（`PackageInspection.package.bindings_for()`を含む）へ暗黙の束縛を生成しない。`name_bindings` 属性は引き続き**明示的な操作から収集した束縛一覧**であり、読み取り専用の組み込み名を無制限に列挙しない。組み込み名の仮想照会はモジュールスコープの情報であり、参照位置の実際の解決先を確定しない。"""

        title @= "組み込み名の暗黙導入と4軸の評価"
        level @= MUST

    class SPEC_018:
        """`BindingState.may_value_use` は既存のAST事実とModel化の過程で識別子を値参照として観測した場合にTrueとなる、軽量な補助情報である。型注釈・クラス基底式における型位置と登録済みCall Interfaceの呼び出し対象は値参照とみなさない。通常の値参照、値の一部への埋め込み、未登録の通常Callは観測の対象とする。登録されたGenericの型引数を値参照と扱わない一方、未登録の添字式をインターフェースと推測してはならない。この情報の収集に新しい包括的な参照追跡器、データフロー解析、制御フロー解析、型推論を導入しない。`False` は観測されなかったことのみを意味し、コード中に値参照が存在しないことを証明しない。利用側は4軸だけで厳密な採否や使用箇所の特定が可能だと想定してはならない。"""

        title @= "値参照の軽量な観測"
        level @= MUST

    class SPEC_019:
        """登録済みの外部Call・Type・Generic Mappingに接続するインターフェース名が、無条件な明示的from importを通して最初に導入されれば `BindingState.introduction="external"` として報告できる。条件付きの初回importなど通常の導入が不安定な場合は `unstable` とする。別名importは元の登録先と静的に照合する。`external` は導入経路の種類のみを表し、値使用の許可、再束縛の禁止、実行時の参照先の保証は一切意味しない。通常の名前と同じ方法で残り3軸を記録する。いずれのMappingもない対象を外部インターフェースであると推測しない。"""

        title @= "外部識別子の安定導入"
        level @= MUST
