"""組み込み名の3軸統合についての開発判断。"""

from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title


@summary("v0.0.2公開後に検討した組み込み名の静的な暗黙導入。")
@canonical_source(
    "shikake 開発履歴: 組み込み名と束縛",
    filename="builtins.md",
    order=40,
    merge_policy="forbidden",
    heading="title",
)
class BUILTINS_HISTORY:
    """既存の3軸と字句スコープを利用し、型推論や値の確定は導入しない。"""

    class IMPLICIT_INTRODUCTION:
        """- v0.0.2の公開後、組み込み名を別の実行時名前解決エンジンで管理するのではなく、モジュール冒頭の仮想的な導入とみなし、既存の束縛3軸に `introduction="builtin"` を追加する方針を採用した。
        - 暗黙のモジュール初期導入は、実際にモジュールに同名の代入が行われたことを意味しない。モジュールの明示的書き込みやstar importは `may_rebind`、削除は `may_delete` で保守的に表す。関数・クラスのローカル導入と混合しない。既存の可視スコープ探索を利用し、実際の参照先は確定しない。
        - 全スコープに全組み込み名の束縛レコードを生成せず、PackageModelのモジュール範囲と完全なSourceInspectionの照会で必要時に合成する。列挙属性は引き続き明示操作の束縛を対象とする。star importの競合は共通AST事実に由来する情報を保持して補完する。
        - 対象の組み込み名は解析実行時のPythonバージョンに依存する。将来のコレクション一般化、immutable付加情報、型推論やランタイムの組み込みの同一性評価は本変更に含めない。次期リリース用として記録し、バージョンは未確定。"""

        title @= "2026-10-24: 組み込み名の暗黙導入を既存3軸へ統合"

    class COLLECTION_GENERALIZATION:
        """- CollectionをSequence・Mapping・Setの3つの具体Kindへ整理し、`construction:scalar`・`immutable:scalar`・`inputs:nodes` を共通Structureとした。リテラルを別のCallへ改変するのではなく、構築の入力列を一般化する。
        - 組み込みのlist/tuple/dict/set/frozenset、3.15+環境のfrozendictは、字句スコープ上の同名操作がないと保守的に認定できるときだけCallではなくCollectionへ変換する。Pythonマイナーバージョンで固定した標準組み込み名前一覧を用い、siteや実行中のbuiltins変更に左右されない。明示的上書き、ローカルの隠蔽、star import、lambdaや内包表記での束縛は通常Callを維持する。
        - Collection内包表記の元のclauses・element・key/value・mappingを消さないため、従来のcomprehension Modelをinputsの唯一の子として保持する。generator式はCollectionの対象外。
        - 代入・反復・with・内包表記のTuple/Listターゲットは値生成ではないため、専用`sequence_target`へ分離した。既存ModelのKind・Structure・等価性は破壊的に変化するので次期未公開項目とする。Type推論、構文実行、動的組み込み置換の追跡は行わない。"""

        title @= "2026-10-24: Collection構築の一般化"

    class REVIEW_CORRECTIONS:
        """- レビューで発見した、Python 3.14/3.15専用テストのKind・role期待値、PEP 695型パラメータによる隠蔽、Partial packageからの仮想組み込み束縛の生成を修正した。
        - SyntaxFactsに型パラメータの注釈スコープを追加し、関数注釈・クラス基底・型エイリアス値と内側のメソッドの可視性を区別する。デコレータ・デフォルト引数は外側のスコープで扱う。さらに、Model側の束縛索引とCollection側の認定で、共通の所有・可視性規則を用いる。
        - 標準組み込み名をPythonバージョン別の固定一覧に変更し、`site`・`gettext`・ホストプロセスの変更によるModel差を避ける。コンストラクタ引数の静的な構文形式を検査し、サポート範囲外はCallを維持する。star importの単一ソース解析とパッケージ全体の束縛判定の情報量差は意図した保守性として文書化する。
        - リテラル／コンストラクタ／内包表記の`inputs`契約、内包表記の二重ラップとspan重複を明記した。テスト環境にないPython 3.14・3.15の実行検証は残課題としている。"""

        title @= "2026-10-24: Collection一般化のレビュー修正"

    class REVIEW_FOLLOWUP:
        """- 3.11〜3.15の全621件のレビュー検証を外部レビューから報告された（直前の修正時点）。今回の追加修正はローカルのPython 3.13環境で再検証し、3.14/3.15の新パッチ適用後のCI確認は別途必要。
        - 共通可視性規則を調整し、注釈スコープだけを経由するクラス局所名参照を保ち、通常の関数・ネストクラス本体では従来どおりクラス局所名を隠す。Collectionと束縛関係が同一規則を使用する。
        - 型パラメータ注釈スコープと関数本体が同一Modelに対応するとき、NameBinding.scope_kindで字句的な2件を識別できるようにした。3軸自体は合成しない。
        - Python 3.15の標準名にImportCycleErrorと__lazy_import__を追加。固定名集合と分離起動インタープリターの組み込み名をCIで比較する回帰テストを追加。global/nonlocalイベント転送の所有者探索を共通規則へ統合し、モジュール直下globalの保守判定を維持した。連鎖したnonlocal宣言を中間スコープ自身の束縛と取り違えないようにも修正した。"""

        title @= "2026-10-24: 注釈スコープ可視性とNameBindingの公開識別"

    class RELEASE_0_0_3:
        """- レビュー通過を受け、組み込み名の3軸統合・Collection一般化・注釈スコープ対応・NameBinding.scope_kindの変更をv0.0.3に収録する方針を決定した。
        - 公開版READMEに残った「解析プロセスの組み込み名前空間から集合を得る」という古い説明を撤回し、「解析するPythonのマイナーバージョンごとに固定した標準名集合」へ統一した。
        - pyproject.tomlの版を0.0.3とし、日本語CHANGELOG/STATUS/README正本と英語公開文書の未公開見出しをv0.0.3に変更した。過去の未公開開発履歴は遡って書き換えない。
        - 公開操作（PyPI upload、gitタグv0.0.3、GitHub Release）は別途リリースワークフローで実行される。文書準備時点では公開成功を主張しない。"""

        title @= "2026-10-24: v0.0.3公開準備と標準組み込み名の説明統一"

    class RELEASE_DOCUMENTS_0_0_3:
        """- 公開前の文書確認でPyPIの0.0.2と挙動を比較し、組み込み名と同名のモジュール直下の定義・書き込み（例：`def open(...)`）の束縛状態、組み込み名を基底に書いた `BaseReference.binding`、`BindingState.introduction` の値域、総称定義の型パラメータ束縛の分割が既存の利用者に影響することを確認した。これらをCHANGELOGの破壊的変更として明記した。
        - レビュー中の修正はいずれも0.0.2で公開された挙動を直すものではなかったため、v0.0.3のCHANGELOGから「修正」節を除き、利用者に見える内容を追加・変更の記述へ統合した。内部の実装・検証上の修正は本履歴の `REVIEW_CORRECTIONS` と `REVIEW_FOLLOWUP` に残す。
        - 英語公開文書が先行していたREADME・STATUSの内容（コンストラクタ引数の条件、注釈スコープの可視性、`inputs` の契約、`scope_kind`、Python 3.15の固定名と照合テスト）を日本語正本へ反映し、正本を起点とする対応関係を回復した。STATUS正本のStructure数を実装どおり62へ訂正し、`BaseReference` の組み込み名の扱いをSTATUSとAPIリファレンスに追記し、v0.0.3公開候補の5バージョン検証結果を記録した。"""

        title @= "2026-10-24: v0.0.3公開文書の正本同期と既存束縛情報への影響の明記"
