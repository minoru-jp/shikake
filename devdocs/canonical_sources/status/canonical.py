"""現時点の{{project.name}}の開発状況。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}} 開発状況",
    filename="STATUS.md",
    merge_policy="all",
    heading="title",
)
class STATUS:
    """{{project.name}} `{{project.version}}` は2026年10月24日付の公開バージョンとして記録します。本書は実装済み機能、制限、および確認済みのテスト実績を記録します。リリース別の変更内容は日本語CHANGELOG正本と英語 `CHANGELOG.md` に記録します。"""

    class AVAILABLE:
        """- 配布名・公開import名は `shikake` です。内部実装は `shikake._mica` に置き、トップレベルの `mica` は配布しません。実行時のShikumi依存は `>=0.2.4,<2.0.0` です。
        - Pythonソースまたは `__init__.py` のないディレクトリも含むローカルソースツリーをASTから読み取り、Kind・Structure・Featureと役割付きModelを取得できます。パッケージ探索は既定では通常の `.py` ファイルをすべて対象とします。`extensions` で複数の拡張子や独自拡張子を選べ、`include(path, is_directory)` で下位ディレクトリの枝刈りと候補ファイルの選別ができます。除外の既定ルールはなく、下位のシンボリックリンクは辿りません。選別後に名前の衝突を検査し、Partialの完全性は選別した入力集合に対するものです。各ファイルは拡張子にかかわらずPython ASTで解析します。`parse_source` の `filename` は構文エラー表示に利用できます。
        - Strict APIは `parse_source()` / `parse_package()`、診断付きのPartial APIは `inspect_source()` / `inspect_package()` です。 4つとも `syntax_validation="compile"` を既定とし、AST解析に加えてCPythonの実行しないコンパイル検証を行います。`"ast"` を指定するとコンパイル検証のみを省きます。コンパイル可能性は実行時の正しさの保証ではありません。 4つの解析APIはいずれも `import_policy` によって、従来どおりのimport、登録済みinterfaceの明示importだけ、または登録済み外部モジュールと `allowed_modules` に指定した任意の絶対モジュール名のimportを許可できます。制限モードでは相対・star importを拒否しますが、`from __future__ import annotations` の単独宣言は許可します。登録済みinterfaceの明示importは両制限モードで許可し、登録済みinterfaceの保護規則は維持します。import先の実在・実行時の同一性を検証せず、セキュリティ上の隔離機能ではありません。
        - Modelは `parts()`・`get(role)`・`get_scalar()`・`walk()` を提供し、`format_model_tree()` で上限付きの診断用構成木を表示できます。`analyses` により継承・オーバーライドの静的な候補照合を選択できます。既知の単一・多重継承グラフ上で確認できた同名メソッド候補を優先順位を付けずに提示し、個々の基底式に `BaseReference` を提供します。宣言・束縛をスコープごとに収集する共通インデックスを用い、入れ子のクラス定義も継承解析の対象にします。
        - 信頼できるShikumi記述体、または `ExternalDefinitionsBuilder` で構築した `ExternalDefinitions` を `definitions=` で渡し、明示的にimportされた外部インターフェースの呼び出しだけを登録Kind・StructureのModelにできます。外部宣言された構造・その子属性は直接呼び出す以外の値使用を拒否し、呼び出し**結果**に対する添字アクセス等は標準Modelとして維持します。`shikake.external` はShikumi宣言とPythonデータによるビルダーの両方式を公開し、動的な参照解決や実行は行いません。
        - Python 3.12の `type` 文・ジェネリック宣言と、3.13の型パラメータ既定値、3.14のt-string（TemplateStr・Interpolation）をModel化できます。Python 3.14の括弧なしの複数例外指定は従来の例外処理と同じModelで扱います。 Python 3.15のPEP 798展開付き内包表記は構文としてModel化します。明示的lazy importは通常のimportと同じKind・Structureを用いて、文に `lazy` Featureを保持します。実行時の遅延ロード・初期化順序を評価せず、束縛3軸や静的参照候補の規則にも反映しません。内部のModel化処理は3.13までの基礎規則と3.14以降の差分規則に整理されています。検証実績は次節に記録します。CIはPython 3.11〜3.15を対象としています。現行の記述体には143 Kind、61 Structure、2 Featureがあります。具体的なKind・Structureの一覧は[LAYOUTS仕様正本ソース](../devdocs/canonical_sources/specification/layouts.py)を参照してください。"""

        title @= "実装済みの範囲"

    class COMMENTS_V0_0_2:
        """- v0.0.2で `collect_comments(source)` を追加し、tokenizeによるコメント原文を `SourceComments` として独立して保持します。行範囲、行末、直前コード行に遮られない上方、モジュール先頭/末尾の検索を提供します。
        - CR・LF・CRLFはASTと一致する行番号で処理します。`SourceComments` は収集APIからのみ生成し、直接構築・dataclasses.replaceはサポートしません。空行は探索を遮りません。コメント中の型情報は解釈せず、既存の `type_comments=False` とModelの構成木・ハッシュ・束縛3軸は変更しません。列位置はUnicode文字オフセットで、ASTのUTF-8バイト位置と異なります。
        - Model起点の専用照会は追加しません。既存の `Model.span` がある場合、その `line`・`end_line` を行検索に渡して組み合わせられます。`span=None` ではこの方法は使えません。ソースの同一性、同一行の複数Modelの区別、コメントの意味的な所属は検証しません。パッケージ横断検索も提供せず、ソースごとに `collect_comments` を呼びます。関数・クラス本体の最初の文の `span.line` で真上のコメント（その文より前に同じ行のコードがない場合に限る）、デコレータ付き定義の直前は各デコレータを含めた最小開始行から、代入文の `span.end_line` で終了行の行末コメントを照会できますが、対象構文への所属を保証しません。複数行の構文内は `in_lines` を使います。コメント用APIを既存の解析APIに暗黙に組み込まないため、tokenizeのエラーは明示的な `collect_comments` 呼び出しでのみ発生します。新規の実行時依存はありません（tokenizeは標準ライブラリ）。ファイル入力ではtokenize.openでエンコーディング/BOMを処理し、同じ文字列を解析に渡します。構文解析できない入力へのtokenize挙動はPythonのバージョン間で保証しません。"""

        title @= "v0.0.2：独立コメントと行検索"

    class PERFORMANCE:
        """- `Model` の構造的ハッシュはインスタンス内に遅延キャッシュされます。親Modelを初回ハッシュしたときに計算した子孫Modelのハッシュも保存し、後続の照会で再走査を減らします。ハッシュ値の算出規則と構造的等価性、非再帰的な計算は維持しています。
        - `PackageModel.bindings_for()`・`bases_for()`・`overrides_for()` は、生成時に構築するModelの同一性に基づく内部索引を使用します。構造的に等しい別Modelを混同せず、返却内容・順序・空タプルの契約を維持します。これらの索引はModelの構造ハッシュを利用しません。
        - いずれも内部実装の最適化であり、新しい公開APIはありません。Model生成時のキャッシュ領域初期化、初回ハッシュ時の子孫キャッシュ保存、PackageModel生成時の索引構築には時間・メモリ上のコストがあります。
        - `PackageModel` の `repr` は構成Modelと解析種別の概要、関係タプルの件数だけを示す長さ制限付きの診断表示です。各関係要素を展開せず、完全な情報は従来どおり公開属性と照会APIから取得します。
        - `SourceInspection` の `repr` はModelの概要と名前束縛の件数を示し、`NameBinding` の各要素を展開しません。両Inspectionの `issues` は診断内容を省略しないため、多数の診断がある場合は表示全体が長くなり得ます。"""

        title @= "性能リファクタリングの実装状況"

    class VERIFICATION:
        """- Python 3.13.5：開発環境で548件中539件成功、9件スキップを確認しました。
        - Python 3.14.6：レビュー環境で548件のテストスイート成功との報告を受けています。
        - Python 3.15.0b4：レビュー環境で548件のテストスイート成功との報告を受けています。
        - Python 3.15.1（2026-10-21公開の正式版）：レビュー環境で548件のテストスイート成功との報告を受けています。
        - 上記の548件は性能リファクタリング以前の検証記録です。変更後の開発環境（Python 3.13.5）では561件実行、552件成功・9件スキップを確認しました。
        - v0.0.1の診断表示と文書テスト出力の修正後、Python 3.13.5の開発環境で563件実行、554件成功・9件スキップを確認しました。こちらの追加修正について他バージョンの再検証は行っていません。
        - v0.0.1のSourceInspection表示修正後、Python 3.13.5の開発環境で566件実行、557件成功・9件スキップを確認しました。この追加修正の他Pythonバージョンでの再検証結果は記録していません。
        - v0.0.1のlazy Feature対応後、Python 3.13.5の開発環境で570件実行、560件成功・10件スキップを確認しました（ASTフラグを模擬した回帰テストを含む）。このPython 3.13.5環境ではPython 3.15の実構文による統合テストを実行しておらず、別のレビュー環境での結果を次項に記録します。
        - v0.0.1のlazy Feature対応後、Python 3.15.0b4のレビュー環境で570件すべて成功、スキップ0件との報告を受けています。Python 3.15の実際のlazy import構文によるテストも含まれます。この実行のログは本書では独立に確認していません。
        - v0.0.2の独立コメント検索とModel.spanの行番号合成を確認後、Python 3.13.5の開発環境で582件実行、572件成功・10件スキップを確認しました。この582件は開発途中の記録です。
        - v0.0.2の公開文書整備時、Python 3.13.5の開発環境で589件実行、579件成功・10件スキップを確認しました。
        - v0.0.2の最終レビュー後、別のレビュー環境でPython 3.11〜3.15の5バージョンすべてについて全テスト成功との報告を受けています。コメント関連の19件も各バージョンで成功し、Ruff check・format、BasedPyrightはエラー0件でした。英語READMEのコメント利用例4件と英語APIリファレンスの3件も正常動作が報告されています。これらはレビュー環境の報告であり、本書では実行ログを独立に確認していません。最終レビュー時のバージョン別総件数・スキップ数の内訳は未取得です。
        - 上記の性能リファクタリング変更後のテストが対象のPython各バージョンでも成功したことは開発者が別環境で確認済みとの報告を受けています。これらの過去の実行の件数・スキップ数は未詳で、ログも本書では独立に確認していません。
        - 以前の548件のレビュー環境の報告についてはスキップ数の内訳が未取得ですが、最新のPython 3.15.0b4での570件の報告ではスキップ0件です。これらの報告はGitHub Actionsの実行結果とは区別します。CIマトリクスはPython 3.11〜3.15で、従来のPython 3.11〜3.13でも検証実績があります。"""

        title @= "Pythonバージョン別のテスト実績"

    class RELEASE_AUTOMATION:
        """- 通常のpushとpull requestでは `.github/workflows/ci.yml` からテスト・静的検査を実行します。PyPIへの公開はpushでは起動せず、`.github/workflows/release.yml` の `workflow_dispatch` をリポジトリのデフォルトブランチで手動実行したときだけ開始します。
        - 公開ワークフローはPython 3.11〜3.15の共通チェック、sdist検証、配布物のビルドとTwine検証を先に実行します。続いてGitHubの `pypi` EnvironmentとPyPI Trusted Publishingを使ってアップロードし、成功した場合に限り同じコミットへ `v<project.version>` タグを付けてGitHub Releaseを作成します。`0.0.1` のタグは `v0.0.1`、`0.0.2` のタグは `v0.0.2` です。
        - GitHub Releaseにはビルドした配布物も添付します。タグがすでに存在するバージョンで新たな公開を開始することは拒否します。公開後のタグやReleaseの作成に失敗した際は、**元のワークフロー実行で失敗したジョブだけ**を再実行し、成功済みのPyPI公開ジョブを再実行しません。アップロード成否が不明な場合はPyPIの実際の公開状態を先に確認します。
        - PyPI側にはGitHubの所有者・リポジトリ・ワークフローファイル `release.yml`・Environment `pypi` に一致するTrusted Publisher設定が必要です。ここでの記載はワークフローの設定であり、外部サービスでのリリース成功を示すものではありません。"""

        title @= "初回リリースのCIとPyPI・GitHub公開手順"

    class BINDING_FACTS:
        """- `PackageModel.base_references` / `bases_for(class_model)` は、基底式ごとに `BaseReference(subject, expression, targets, binding, attribute_modified)` を公開する。`targets` は発見済みのクラス候補、`binding` は根の識別子の `BindingState(introduction, may_rebind, may_delete)` または `None`、`attribute_modified` は同じモジュールの明示的な属性変更を示す。
        - `PackageModel.name_bindings` / `bindings_for(scope, name)` からスコープごとの束縛3軸を取得でき、`analyses=set()` でも利用できる。完全な単一ソースの `inspect_source()` からも `SourceInspection.name_bindings` を取得でき、不完全なPartial結果では空になる。これらはFeatureではない。初回の構文上の導入、追加・反復し得る書き込み、削除を区別するが、実行順序・分岐の成立・読み取り時点の確定代入は判定しない。
        - 継承全体に確定性のstatusは付けず、基底参照ごとの事実とオーバーライド候補を独立して提供する。候補は実行時の正しさを証明せず、利用側が採否を判断する。共通のAST事実収集器を継承解析と外部構造の制約検証で共有する。"""

        title @= "基底参照と束縛3軸の公開契約"

    class ISSUES:
        """- `shikake.Model` は正規の解析APIから返された結果を読むための公開型です。利用者による `Model(...)` の直接構築は想定・サポートせず、独自に構築したModelの妥当性や、それを他のAPIへ渡した際の動作は保証しません。Kind・Structure・Featureに関する整合性の保証はライブラリの正規解析経路で生成したModelを対象とします。
        - Strict解析は未対応構文を `UnsupportedSyntaxError` で拒否します。Partial解析は可能な範囲を返しますが、`complete=False` の結果は完全な解析結果ではありません。局所的な外部構造違反では問題のある文を省略して後続のModelを保持できる場合があり、省略によって後続の解釈に必要な先行情報が失われ得ます。不完全なパッケージのPartial解析では、基底参照・オーバーライド候補・名前束縛などの関係解析を実行しません。
        - Python標準ASTの深さ制限は原理的な制約です。Modelの式構築（演算・アクセス・コレクション・内包表記・f-string・lambdaの引数既定値など）、代入先・パターン・文とBlockの入れ子、走査・比較・ハッシュには反復処理を用います。パッケージの名前束縛とクラス内メソッド探索も反復処理に対応しています。ただし、あらゆる深さや実装経路の無制限な解析は保証せず、Partialも `RecursionError` の診断変換は行いません。
        - 外部パッケージや `.pyi` の自動探索・定義元照合はありません。登録された外部呼び出しの照合はモジュール最上位の明示的なimportに限り、自由関数の直接importは対応しません。呼び出し引数の不足／過剰や展開、再束縛の曖昧さは診断します。インスタンス経由の参照に対する型推論は行いません。基底式の照合候補は実行時の同一性を保証せず、未知の実行時依存を網羅しません。既知の多重継承の記述と候補は追跡しますが、MRO・基底クラスの実行時優先順位、ジェネリック基底の解決などは未対応です。構文上の候補がないことも実行時の候補不在の保証ではありません。
        - ソースを実行せず、値の評価、型推論、動的な名前解決、コード変換を行いません。"""

        title @= "既知の制約・問題"

    class PLANS:
        """- 未対応構文の採否を、利用側に必要な情報に基づいて継続検討します。
        - 外部の `.py` / `.pyi` を明示的な情報源として使う参照照合、Partial診断の改善は今後の検討対象です。
        - 公開APIの継続的な整理、使用例の検証、配布手順の確認を進めます。"""

        title @= "今後の開発"
