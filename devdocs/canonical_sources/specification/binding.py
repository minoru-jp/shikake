"""字句スコープと束縛の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.statements import STATEMENTS


@summary("識別子の導入・変更・削除と、参照先候補から独立した3軸。")
@canonical_source(
    "{{project.name}}: 字句スコープと束縛",
    filename="binding.md",
    order=50,
    merge_policy="all",
    heading="identity",
)
class BINDING:
    """識別子の導入・変更・削除と、参照先候補から独立した3軸。"""

    class SPEC_001:
        """束縛の性質は参照式の値やFeatureではなく、字句スコープに属する識別子の構文上の事実として扱う。導入の安定性、再束縛可能性、喪失可能性を独立に収集する。これらの3軸は読み取り時点での確定代入を保証せず、3軸のみを根拠に確定代入を認定してはならない。"""

        title @= "束縛情報の対象"
        level @= MUST
        related @= (PARSING.SPEC_002,)

    class SPEC_002:
        """`BindingState.introduction` は識別子の導入が構文上明快な形式であるかを表す。`stable` には最初の独立した導入が無条件かつ競合のない形で書かれていることが必要だが、それだけでは十分ではない。`n += 1` のように既存の束縛を読み取る増分代入は単独で安定した導入とみなさず、他の導入がなければ `unstable` とする。複合文による条件性、既知の競合、または導入に不要なモジュール直下の `global` 宣言があれば `unstable` とする。Pythonの実行結果の安定性や一般的なコード品質を評価するものではない。"""

        title @= "導入の安定性"
        level @= MUST

    class SPEC_003:
        """`may_rebind=True` は対象の字句スコープにおける最初の構文上の導入とは別の導入・書き込み、または繰り返され得る書き込み・増分代入・star importによる競合が記述されることを意味する。最初の通常代入 `x = 1` だけならFalse、`x = 1; x = 2` ならTrueとする。`for` / `while` 本体や内包表記内の反復し得る単独書き込みはTrueとする。一方 `if` 内に一度だけ記述された条件付き導入それ自体は、導入が `unstable` でも追加の書き込みがなければFalseとする。繰り返しの回数や実行経路を評価せず、読み取り時点の代入確定性も表さない。"""

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
        """`B: type` のような値のない注釈は束縛を発生させず、それだけを根拠に3軸を生成しない。ただし関数内ではローカル名の宣言として作用するため、同名の外側の対象へ解決してはならない。"""

        title @= "値なし注釈"
        level @= MUST

    class SPEC_009:
        """識別子の3軸を認定できなければ `binding=None` とする。候補がない・誤りである・不安定であるなどの意味を付け足すステータスを設けない。"""

        title @= "取得不能な束縛"
        level @= MUST

    class SPEC_010:
        """star importから静的にクラス候補を発見できても、個別名の導入を3軸へ展開することは保証しない。`targets` に候補があっても `binding=None` は許容される。"""

        title @= "star importの制限"
        level @= MUST

    class SPEC_011:
        """パッケージが属性名を直接定義または静的なstar importで再公開し、同名のサブモジュールも存在する場合、導入の競合は `unstable` とする。候補の探索可否は別に扱う。"""

        title @= "パッケージ属性と同名サブモジュール"
        level @= MUST

    class SPEC_012:
        """代入、削除、import経路、字句スコープ、条件付き導入の基礎となるAST事実は共通の収集結果を用いる。参照先候補の判定と外部構造の保護のために、別々のスコープ意味を作ってはならない。"""

        title @= "共通のAST事実"
        level @= MUST

    class SPEC_013:
        """`global`・`nonlocal` は名前の束縛先を識別する構文事実として扱う。モジュール直下の `global X` はPythonの束縛先を変更しないが、同じモジュールで導入される `X` に不要なスコープ宣言が付いているため、その導入を `unstable` と判定する。宣言だけでは束縛を生成せず、`may_rebind`・`may_delete` は書き込み・削除の構文事実に基づいて別途判定する。"""

        title @= "宣言による束縛先の識別"
        level @= MUST

    class SPEC_014:
        """`PackageModel.name_bindings` は各 `NameBinding(module, scope, name, state)` を列挙し、`bindings_for(scope_model, name)` は渡されたModelと同一identityの字句スコープだけを照会する。`NameBinding.state` は `BindingState` の3軸を保持する。関係解析を指定しなくてもこの情報は取得可能で、別のスコープや参照先モジュールの束縛を合成しない。"""

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
