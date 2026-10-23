"""基底参照と候補照合の正本仕様。"""

from shikumi_devdoc.fields.specification import MAY, MUST, MUST_NOT, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.binding import BINDING
from devdocs.canonical_sources.specification.model import MODEL
from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.statements import STATEMENTS


@summary("候補と束縛情報を分離した静的な基底参照・オーバーライド照合。")
@canonical_source(
    "{{project.name}}: 基底参照と候補照合",
    filename="relations.md",
    order=60,
    merge_policy="all",
    heading="identity",
)
class RELATIONS:
    """候補と束縛情報を分離した静的な基底参照・オーバーライド照合。"""

    class SPEC_001:
        """クラスの基底式は参照先が発見できなくても構文として保持する。静的に発見した定義候補と、根の識別子に対する束縛3軸は相互の代替情報としない。"""

        title @= "候補と構造の独立性"
        level @= MUST
        related @= (
            BINDING.SPEC_001,
            STATEMENTS.SPEC_009,
        )

    class SPEC_002:
        """書かれた各基底式について独立した `BaseReference` を保持する。`subject`、`expression`、`targets`、取得可能なら`binding`、属性変更の構文上の有無 `attribute_modified` を区別する。"""

        title @= "BaseReferenceの単位"
        level @= MUST

    class SPEC_003:
        """`PackageModel.base_references` / `bases_for(class_model)` は構文上の基底式ごとの関係をソース順で提供する。`PackageModel.override_candidates` / `overrides_for(method)` はMethod Modelを基点とした候補を提供する。問い合わせ対象のModelは構造的等価性でなくオブジェクト同一性で照合し、同形の別インスタンスを混ぜない。返却順は元の関係タプルの順序を維持し、該当しなければ空タプルを返す。いずれも構成木の `walk()` には混ぜない。"""

        title @= "照合関係の取得"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_004:
        """基底式の候補が見つからない場合も `targets=()` を保持する。`targets` が存在しても `binding=None` となり得る。複数要因をまとめた `resolved` 等の総合状態を復活させてはならない。"""

        title @= "候補不在と3軸の独立性"
        level @= MUST
        related @= (BINDING.SPEC_009,)

    class SPEC_005:
        """候補探索はASTの定義、字句スコープ、明示import経路、確認できる静的属性連鎖に限定する。外側のクラススコープへ根拠なく名前を漏らさず、クラスの自己定義をその基底に採用しない。同名の別定義や先行importがAST上にあれば、その候補まで同時に捨てない。"""

        title @= "候補探索の根拠"
        level @= MUST
        related @= (BINDING.SPEC_012,)

    class SPEC_006:
        """`import pkg.a` は束縛名 `pkg` と明示経路 `pkg.a` の両方を事実として保持する。`from pkg import a` や `from . import a` などで明示された子モジュールは、親パッケージに `__init__.py` がなく対応するModule Modelが存在しなくても、解析対象に `pkg.a` が存在すれば候補探索の対象とする。親のModule Modelを合成せず、`import pkg` だけで未記述の `pkg.a` を推測しない。既知のパッケージ属性との競合判定、外部import元の存在・実行時再束縛を推測しない制限は維持する。"""

        title @= "importの明示経路"
        level @= MUST
        related @= (
            STATEMENTS.SPEC_013,
            BINDING.SPEC_012,
            PARSING.SPEC_015,
        )

    class SPEC_007:
        """パッケージ属性と同名サブモジュールが曖昧でも、静的に見つけたクラス定義は候補として保持できる。ただし曖昧な根から存在を確認できない子属性へ候補を引き継がない。"""

        title @= "競合下の候補保持"
        level @= MUST
        related @= (BINDING.SPEC_011,)

    class SPEC_008:
        """ASTから静的に確認できるstar importの再公開は、候補照合の根拠として使ってよい。個々の識別子の3軸については束縛仕様の規則に従う。"""

        title @= "star importの限定追跡"
        level @= MAY
        related @= (BINDING.SPEC_010,)

    class SPEC_009:
        """静的に見つかった基底候補から、書かれた同名Method定義を `OverrideCandidate` として取得する。継承の実効性、MRO、メソッドの互換性や呼び出し先を確定しない。"""

        title @= "オーバーライド候補"
        level @= MUST

    class SPEC_010:
        """同一のMethod Modelを、そのMethod自身のオーバーライド候補として報告してはならない。書字順序の実行シミュレーションはこの除外規則の前提にしない。"""

        title @= "自己候補の排除"
        level @= MUST_NOT

    class SPEC_011:
        """参照した別モジュールでの動的な代入、属性変更、削除等を実行時の影響として追跡し、候補の確実性へ反映してはならない。"""

        title @= "他モジュールの変更"
        level @= MUST_NOT

    class SPEC_012:
        """`OverrideCandidate` は派生側・基底側のClass Model、双方のメンバー定義Model、両側のモジュール名と根拠 `evidence` を保持する。`evidence` は直接基底の同名定義を `direct_base_and_same_method_name`、間接祖先の同名定義を `ancestor_and_same_method_name` として区別し、クラス定義領域のGeneratorも候補照合対象とする。これは実行時のオーバーライドの確定ではない。"""

        title @= "候補の根拠と同名Generator"
        level @= MUST
        related @= (STATEMENTS.SPEC_016,)

    class SPEC_013:
        """star import元に `__all__` の記述がある場合、その値を実行・評価して公開識別子を確定しない。`__all__` がない場合に静的に認識できる公開名から候補を拾うことは許容するが、候補の発見だけで導入の3軸を合成しない。明示的な `from x import Name` はこのstar import固有の制限と区別する。"""

        title @= "__all__とstar importの境界"
        level @= MUST
        related @= (BINDING.SPEC_010,)

    class SPEC_014:
        """PEP 695の型パラメータ名は、対象となる定義内では外側の同名クラス候補を隠す構文上の名前として扱う。基底式中の同名型パラメータも、外側のクラスへ取り違えてはならない。型パラメータを実行時のクラスと推測しない。"""

        title @= "型パラメータによる候補の隠蔽"
        level @= MUST
        related @= (BINDING.SPEC_006,)

    class SPEC_015:
        """オーバーライド候補を祖先へたどる場合、同一Method Modelへ複数経路から到達しても同じ候補を重複報告しない。構文上循環して見える継承グラフは停止可能に探索し、探索の停止を実行時のMROの確定とは解釈しない。"""

        title @= "候補重複と循環の扱い"
        level @= MUST
        related @= (BINDING.SPEC_012,)

    class SPEC_016:
        """`BaseReference.attribute_modified` は参照式に対応する属性連鎖について、同一モジュールのASTに明示的な属性代入・変更・削除が記述されているかを表す。対象の変更が実際に発生するかは調べず、根の識別子の `BindingState` の3軸とも混同しない。他モジュールの変更事実は追跡しない。"""

        title @= "属性変更と束縛3軸の独立性"
        level @= MUST
        related @= (BINDING.SPEC_001,)

    class SPEC_017:
        """同一字句スコープの基底参照では、参照位置より後にのみ記述されたクラス定義・import等の導入を、参照先候補に採用しない。先行して記述された別の候補は保持し、後方の操作も識別子全体の束縛3軸には引き続き反映する。異なる字句スコープやモジュール間の実行順序はソース位置から推測しない。位置による除外は候補探索だけの制約であり、実行時のNameErrorや名前の存在を確定するものではない。"""

        title @= "同一スコープの後方導入を候補から除外"
        level @= MUST
        related @= (BINDING.SPEC_001, BINDING.SPEC_003)

    class SPEC_018:
        """基底候補の収集では、条件付きまたは複数の導入経路に含まれる明示importも、同じ字句スコープに記述されたクラス定義と同様に候補として扱う。`if` / `else` や `try` / `except` のどの経路が実行されるかを推測せず、記述されたimportパスから到達できる既知のクラス定義を重複なく保持する。後続の代入・削除は3軸に反映するが、先行importから静的に確認できる候補をそれだけで捨てない。同一スコープの後方導入制限、star importの制限、明示されないimport経路を補完しない規則は維持する。"""

        title @= "条件付き導入と明示importの候補保持"
        level @= MUST
        related @= (BINDING.SPEC_005, BINDING.SPEC_009)

    class SPEC_019:
        """`PackageModel` の `repr` は長さ制限付きの診断用概要とし、構成Modelの概要、選択された解析、`override_candidates`・`base_references`・`name_bindings` の件数を示す。関係オブジェクトの内容を展開せず、完全なデータ表現、`eval` による再構築、一意性を保証しない。詳細な関係は各属性と問い合わせAPIから取得する。"""

        title @= "PackageModelの省略付き診断表示"
        level @= MUST
        related @= (MODEL.SPEC_022,)
