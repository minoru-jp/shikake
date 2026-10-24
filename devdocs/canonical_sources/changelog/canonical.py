"""shikakeの公開リリース単位の変更履歴（日本語正本）。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "shikake 変更履歴",
    filename="CHANGELOG.md",
    merge_policy="forbidden",
    heading="title",
)
class CHANGELOG:
    """本書は利用者に影響する変更を**リリース単位**で記録します。設計経緯と採否理由は
    `devdocs/canonical_sources/development_history/pre_release.py`、
    `devdocs/canonical_sources/development_history/performance.py`、
    `devdocs/canonical_sources/development_history/comments.py`、
    `devdocs/canonical_sources/development_history/builtins.py` に記録します。

    `0.0.1` は2026年10月23日付の初回Alphaリリース、`0.0.2` は2026年10月24日付のリリースとして記録します。`0.0.3` は2026年10月24日付の公開準備済み変更として記録し、PyPI・GitHubへの公開完了とは区別します。
    変更項目は公開APIと利用者向け機能の範囲を示します。"""

    class VERSION_0_0_3:
        """v0.0.3の公開準備版。組み込み名を既存の束縛3軸へ統合し、Collection Modelを一般化します。公開Model契約と既存の束縛情報に破壊的変更を含みます。"""

        title @= "0.0.3（2026-10-24、公開準備）"

        class ADDED:
            """- **組み込み名の暗黙導入**：Pythonマイナーバージョンごとに固定した標準組み込み名を、各モジュールの仮想的な初期導入 `BindingState(introduction="builtin", may_rebind=False, may_delete=False)` として既存3軸で評価します。モジュールでの書き込み・削除とstar importによる競合の可能性は通常どおり `may_rebind`・`may_delete` に反映し、同名のローカル束縛は別に扱います。標準名の一覧は `site` の追加名や実行中の `builtins` の変更に左右されません。
            - **必要時の束縛照会**：`PackageModel.bindings_for(module, name)` と完全な `SourceInspection.bindings_for(module, name)` は、明示的な書き込みがない組み込み名の暗黙導入も返します。読み取り専用の組み込み名を `name_bindings` に大量展開せず、不完全なPartial結果（`PackageInspection.package` 経由の照会を含む）では生成しません。実行時の参照先や型は確定しません。
            - **字句スコープの識別**：ライブラリが生成する `NameBinding` は `scope_kind`（`module`・`class`・`function`・`annotation`）を持ちます。利用者が手動で構築する場合は省略でき、省略時は `None` です。"""

            title @= "追加した機能"

        class CHANGED:
            """- **Collectionの一般化**：値のCollectionはSequence・Mapping・Setの3つの具体Kind（`model.value.collection.sequence`・`.mapping`・`.set`）と共通Structure `collection_construction`（`construction`・`immutable`・`inputs`）へ整理しました。従来の `.list`・`.tuple`・`.dict` Kindとコレクション固有のroleは生成しません。`inputs` はliteralでは直接の要素・辞書entry、builtinでは記述された引数Model、comprehensionでは元の内包表記Model1個を保持します。Featureは増やしません。
            - **保守的な組み込みコンストラクタの認定**：`list`・`tuple`・`dict`・`set`・`frozenset` と、Python 3.15以降の `frozendict` の呼び出しは、可視スコープに同名の書き込み・削除・star importがなく、引数の記述形式が対応範囲内のときだけCollectionになります。`list`・`tuple`・`set`・`frozenset` は位置引数0〜1個でキーワード引数と `*` 引数なし、`dict`・`frozendict` は位置引数0〜1個とキーワード引数（`**` を含む）で `*` 引数なしです。PEP 695の型パラメータとクラス直下の注釈スコープの可視性はPythonの字句規則に従います。それ以外は通常の `model.value.call` のままで、実行時の参照先や要素は推論しません。
            - **内包表記と代入ターゲット**：リスト・集合・辞書の内包表記は、元の内包表記Modelを唯一の `inputs` 子に持つCollectionになります。generator式は変わりません。Tuple/Listの代入先は値のCollectionではなく、`spelling`・`elements` を持つ `model.structural_part.sequence_target` で表します。`async`・`lazy` Featureは変わりません。
            - **既存の束縛情報への影響**：組み込み名と同名のモジュール直下の書き込み・定義（例：`def open(...)`）は、0.0.2の `BindingState("stable", False, False)` から `BindingState("builtin", True, False)` になります。組み込み名を基底に書いた `BaseReference.binding`（例：`class AppError(Exception)`）は `None` から `BindingState("builtin", False, False)` になります。`BindingState.introduction` には `"builtin"` が加わりました。
            - **型パラメータの束縛**：PEP 695の型パラメータは、定義本体とは別の注釈スコープの束縛になりました。総称定義の型パラメータと本体の同名束縛は1件に合成されず、`scope_kind` の異なる2件として同じ定義Modelから返ります。型エイリアスの型パラメータも束縛として報告します。"""

            title @= "変更（公開Model契約と束縛情報の破壊的変更を含む）"

    class VERSION_0_0_2:
        """0.0.2の公開内容。コメント情報と行番号による照会を追加しました。"""

        title @= "0.0.2（2026-10-24）"

        class ADDED:
            """- **独立コメント情報**：`collect_comments(source)` がtokenizeから `Comment` と `SourceComments` を生成し、行範囲・行末・コードを挟まない上方・モジュール先頭/末尾の検索を提供します。空行やコメント内容から意味上の対応付けを推測しません。
            - **型コメントの原文**：`# type: ...` や `# type: ignore` も通常コメントとして収集します。型コメントのAST解析や型推論を導入せず、`type_comments=False` を維持します。
            - **Model位置との組み合わせ**：`Model.span` が保持する開始・終了行を既存の行検索に指定できます。関数・クラスの本体内コメントは最初の文の開始行、代入文の行末コメントは文の終了行から照会できます。専用のModel起点検索は追加せず、コメントとの意味的な関連付けも行いません。パッケージ横断検索とコメントの構造Model化は提供しません。"""

            title @= "追加した機能"

        class FIXED:
            """- **改行の統一**：CR・LF・CRLFでコメントの行番号とASTの行番号を揃えました。
            - **コメント結果の生成契約**：SourceCommentsの直接構築・dataclasses.replaceを非サポートとし、内部索引の一貫性を保証します。デコレータ・同一行本体・BOM入力・不正ソースに関する検索例と制約を明記しました。"""

            title @= "修正"

    class VERSION_0_0_1:
        """PythonのASTを基礎とする静的な構造Model化ライブラリの初回リリースです。
        Python 3.11以降に対応し、Python 3.14・3.15の追加構文には実行環境に応じた
        内部差分規則で対応します。公開APIはAlpha段階であり、今後変更される可能性があります。"""

        title @= "0.0.1（2026-10-23）"

        class ADDED:
            """- **基本のModel化**：Kind、Structure、Featureと役割付きModel。
            `parse_source()`・`parse_package()` のStrict解析、`inspect_source()`・
            `inspect_package()` のPartial解析と診断。上限付き `format_model_tree()` を提供。
            - **入力の選択**：パッケージ走査の `extensions` と `include` コールバック。
            既定では通常の `.py` ファイルを対象とし、独自拡張子もPython ASTとして解析。
            - **構文検証**：実行しないCPythonのコンパイル水準を既定とし、
            `syntax_validation="ast"` で追加のコンパイル検証を省略可能。
            - **外部構造**：信頼済みShikumi宣言または `ExternalDefinitionsBuilder` から
            外部Kind・Structure・呼び出しのマッピングを作成。
            - **import制限**：`import_policy` の3モード、および任意の絶対モジュール名を
            指定する `allowed_modules`。実行時のimport解決や安全な実行環境は提供しない。
            - **静的な関係と束縛**：基底クラス参照・オーバーライド候補、スコープごとの
            `name_bindings` と束縛3軸。実行時の名前解決や確定代入は保証しない。"""

            title @= "追加した機能"

        class SYNTAX:
            """- Python 3.12の `type` 文・ジェネリック宣言、3.13の型パラメータ既定値、
            3.14のt-stringと複数例外指定、3.15のPEP 798展開付き内包表記をModel化。
            - PEP 798の辞書展開付き内包表記は
            `model.value.comprehension.dict.unpacking` として表現。
            - Python 3.15の明示的な `lazy import` / `lazy from ... import` は通常のimportのKind・Structureで受け入れ、import文に `lazy` Featureを付与。実行時の遅延ロードを評価せず、束縛3軸や参照候補の規則は維持。
            - Python 3.13までの基礎規則と以降の差分規則は**内部実装**であり、
            利用者が規則バージョンを選ぶ公開APIは設けない。"""

            title @= "Python構文への対応"

        class PERFORMANCE:
            """- **Modelの構造的ハッシュ**：計算結果をModelごとに遅延キャッシュし、
            親Modelのハッシュ計算で得た子孫Modelの結果も保存します。構造的等価性と
            ハッシュ算出規則、非再帰計算は維持し、同じModelや子孫Modelの再利用時の
            重複走査を削減します。
            - **関係情報の照会**：`PackageModel.bindings_for()`・`bases_for()`・
            `overrides_for()` はModelのオブジェクト同一性に基づく内部索引を用い、
            問い合わせごとの全件走査を避けます。返却内容・順序・公開APIは維持します。
            - いずれも内部最適化で、Model生成や索引構築、キャッシュ保存には
            追加の処理時間・メモリが必要です。"""

            title @= "性能改善"

        class DIAGNOSTICS:
            """- **PackageModelの診断表示**：`repr(package)` は構成Modelと解析名の概要、束縛・基底参照・オーバーライド候補の件数を表示します。関係要素を全展開しない長さ制限付きの表示であり、データを復元する用途には使いません。
            - **SourceInspectionの診断表示**：`repr(inspection)` では名前束縛の全展開を避けて件数を示します。SourceInspection・PackageInspectionの `issues` は診断を省略せずに表示します。
            - **文書生成テスト**：不正引数のテストで予期したargparseの標準エラー出力を捕捉し、終了コードと内容を検証します。文書生成CLIの実際のエラー表示は変更しません。"""

            title @= "診断表示と開発時の検証"

        class PUBLICATION:
            """- 配布・公開import名は **`shikake`** です。旧開発名 `kangen` の互換importはありません。
            - 公開API・制約は日本語正本仕様を規範とします。英語の利用案内は
            `README.md`、`docs/api_reference/`、`docs/STATUS.md` を参照してください。
            - 変更履歴はリリース別の機能と互換性情報を扱い、実際の配布物の取得先や
            公開状況はPyPI・GitHubの各配布先で確認してください。"""

            title @= "公開・互換性に関する注意"
