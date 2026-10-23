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
    `devdocs/canonical_sources/development_history/pre_release.py` および
    `devdocs/canonical_sources/development_history/performance.py` に記録します。

    `0.0.1` は2026年10月23日付の初回Alphaリリースとして記録します。
    変更項目は公開APIと利用者向け機能の範囲を示します。"""

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
