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

    `0.0.5` は2026年10月25日の公開版として記録します。`0.0.1` は2026年10月23日付の初回Alphaリリース、`0.0.2` は2026年10月24日付のリリースとして記録します。`0.0.3` は2026年10月24日の旧版として記録します。`0.0.4` は2026年10月25日の公開版として記録し、実際のPyPI・GitHubアップロードは別途行います。
    変更項目は公開APIと利用者向け機能の範囲を示します。"""

    class VERSION_0_0_5:
        """shikake v0.0.5（2026年10月25日公開版）。ModelRefの追加と定義体系の整理、外部Featureの宣言と明示的付与に対応。Modelの構造的等価性は変更しない。"""

        title @= "0.0.5（2026-10-25）"

        class ADDED:
            """- **ModelRef**：公開型 `ModelRef(model: Model, source_path: str | Path)` を追加。内部ではPathを保持し、Model個体（`is`）とPathの同値性の両方で比較・ハッシュ化する。利用側が必要な場合に明示的に生成し、辞書・集合のキーや外部解析ツールとのソース位置照合に利用できる。ファイルの実在確認やPathの解決は行わない。
            - **定義クエリ**：DefinitionIndexの`classified_under`・`defines_role`・`allows_feature`からKind分類、Structure role定義、Feature適用可能性を独立に照会できる。
            - **外部Feature**：ShikumiとExternalDefinitionsBuilderの両方でFeatureを宣言でき、Call・Type・Genericマッピングから専用Modelへ明示的に付与できる。
            - **合成と出自**：base=ExternalDefinitionsで先行マッピングと外部Feature宣言の出自を引き継ぎ、組み込みFeatureの外部マッピング付与を禁止する。"""

            title @= "追加"

        class CHANGED:
            """- **定義Index**：KindIndexをDefinitionIndexに、kind_index()をdefinition_index()に、is_a()をclassified_under()に改名。互換エイリアスは提供しない。定義クエリはModelへ移さず、外部定義を取り込んだIndexから行う。外部IDはドット付き修飾名を必須とし、model名前空間は予約する。Featureの順序はModelFactory生成時にID昇順へ正規化するが、直接構築したModelは順序を保持する。外部IDのセグメントにPython予約語とUnicode識別子を許容し、Unicode正規化を行わず元の文字列で識別する。拒否理由を分類して通知する。独自Indexの合成は拒否し、正規の合成経路を案内する。直接構築したExternalDefinitionsは出自検証の対象外であることを明記した。ModelRefは実行時にModel以外を拒否する。"""

            title @= "変更（非互換APIの改名）"

        class VERIFIED:
            """- 更新済みv0.0.5は702件のテストを対象とし、Python 3.13.5で689件成功・13件スキップ・失敗0件をローカル確認した。Ruff check・formatとBasedPyrightも成功した。
            - Python 3.11・3.12・3.13・3.14・free-threaded版3.14・3.15b4の全6環境でテストが正常終了（失敗0件）した結果として記録する。複数インタープリタでの実行ログはこの作業環境では独立に検証していない。"""

            title @= "検証記録"

        class UNCHANGED:
            """- Modelの構造的等価性、既存のPython構文のModel化規則、関係分析・コメント検索の意味は変更しない。ModelRefはModelメンバーへの委譲や子Modelの自動ラップを行わない。ASTとtokenizeの公開も追加しない。互換用レイヤーは設けない。"""

            title @= "維持する契約"

    class VERSION_0_0_4:
        """shikake v0.0.4（2026年10月25日公開版）。外部インターフェースを任意のModel化へ整理し、束縛4軸、ImportPolicy、Generator Feature、解析性能と構文スコープを更新した。後方互換性は提供しない。"""

        title @= "0.0.4（2026-10-25）"

        class ADDED:
            """- **外部Call・Type・Generic**：明示的importから、直接関数Call、Type参照、固定長のGeneric適用をShikumi宣言またはビルダーで登録できる。同じ名前に複数の使用形式を独立に登録できる。
            - **識別子4軸**：`BindingState` に `may_value_use` と `introduction="external"` を追加。登録済みInterface構文による利用と通常の値参照を区別する。観測は軽量で、Falseは操作が存在しないことの証明ではない。
            - **委譲ImportPolicy**：`default`・`allow`・`deny`・`allow_star_import=False` で利用側が許可・禁止を指定できる。指定なしは無検査、deny優先。モジュール指定は当該モジュールと子モジュールに適用し、`module:Name` は完全一致、`from M import N` はdeny側で `M.N` も照合する。star importはポリシー指定時には明示許可が必要。"""

            title @= "追加"

        class CHANGED:
            """- **外部Interfaceの採否を利用側へ**：外部名の値使用・再束縛・削除、未登録の操作、引数不一致だけでSourceを拒絶しない。専用Modelの条件が満たせない場合は通常Call・Subscript・参照のModelに戻す。外部Callの引数照合をModelの消費前に完了し、部分消費による `KeyError` を解消した。
            - **字句スコープの判定**：外部Interfaceと組み込みCollectionの認定で、明確なローカル束縛・仮引数・lambda・内包表記による隠蔽を考慮する。lambdaの既定値、内包表記の最初のiterableは外側のスコープで評価し、クラス本体内の内包表記の本体はクラス局所名を参照しない。型推論や任意の名前追跡器は追加しない。
            - **star importの非推論**：star importは構文としてModel化するが、暗黙の名前導入や既存の識別子への競合を4軸・組み込みCollection・継承候補に反映しない。明示的な通常importの扱いは維持する。
            - **Generatorの一般化**：`model.definition.generator` を廃止。generator関数もメソッドも通常の `model.definition.function` / `.method` に `generator` Featureを付与する。`async` と併用可能であり、Structureは通常の関数・メソッドと同じ。
            - **解析性能と重複**：ASTの構文コンテキストを一度収集し、型位置、式スコープ、Genericの引数領域、外部Interfaceおよび組み込みCollectionの認定に再利用する。深い式の反復的な祖先走査を減らし、4つの解析APIの共通前処理とASTブロック列挙を整理した。
            - **Python警告の制御**：解析中の警告を捕捉・抑制・`InspectionIssue` に変換しない。ホストの `warnings` 設定に従い、例外化によりPython構文検証が失敗すれば通常の構文エラー経路で扱う。"""

            title @= "変更（破壊的変更を含む）"

        class REMOVED:
            """- 旧3モードの `import_policy`、`allowed_modules`、登録済み外部構造の使用禁止・予約名保護と、旧外部使用違反の例外・診断経路を削除。`ExternalModelingError` も公開APIから削除した。
            - `BindingState` の3引数構築は廃止。Generator専用Kind／Structureは残さない。警告専用の診断区分と重大度フィールドは最終APIに存在しない。旧互換レイヤーは提供しない。"""

            title @= "削除・移行事項"

        class VERIFIED:
            """- stage9ではPython 3.13.5の回帰テストに失敗なし、RuffとBasedPyrightはエラーなし。
            - stage8のレビューにてPython 3.11〜3.15およびfree-threaded版3.14で全テスト成功、分岐カバレッジ95%、実コード9,892ファイルの検証でクラッシュ0件との報告を受けた。stage9固有の全バージョン再検証はまだ記録していない。"""

            title @= "検証記録"

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
