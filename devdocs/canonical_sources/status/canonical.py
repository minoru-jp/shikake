"""shikake 0.0.4の実装状況（日本語正本）。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}} 開発状況",
    filename="STATUS.md",
    merge_policy="all",
    heading="title",
)
class STATUS:
    """**{{project.name}} {{project.version}}（2026年10月25日、公開済みとして記録）。**

    本書は現在の実装範囲・制約・検証結果を示す。リリース間の変更は日本語のCHANGELOG正本および英語 `CHANGELOG.md` に記載する。公開状態の記載は文書上のリリース区分であり、PyPI・GitHubのアップロード操作を代行しない。"""

    class IMPLEMENTED:
        """- Python 3.11以降のPython構文を、標準の `ast` に基づいてKind・Structure・Featureと役割付きModelに変換する。対象のソースやそのimport先を実行しない。`collect_comments()` では標準の `tokenize` を別途利用する。実行時依存は `shikumi>=0.2.4,<2.0.0`。
        - Strict APIは `parse_source()` / `parse_package()`、Partial APIは `inspect_source()` / `inspect_package()`。既定の `syntax_validation="compile"` はAST解析に加えて実行しないコンパイル検証を行い、`"ast"` は後者のみ省略する。警告は捕捉せずホストのPython警告設定に従う。警告を例外化して構文検証が失敗した場合は、既存の構文エラー経路で扱う。
        - パッケージ探索では `.py` を既定とし、`extensions` と `include(path, is_directory)` で入力を選べる。下位ディレクトリのシンボリックリンクは辿らず、実行時importや動的名前解決は行わない。
        - `Model.parts()`・`get()`・`get_scalar()`・`walk()`、`format_model_tree()` と、継承基底参照・override候補の静的関係解析を提供する。`PackageModel.bindings_for()` 等による関係照会はModelの同一性に基づく。
        - `BindingState` は `introduction`（`stable`・`unstable`・`builtin`・`external`）、`may_rebind`、`may_delete`、`may_value_use` の4軸。モデル化時に観測できた軽量な構文事実であり、`False` は当該操作の不在を保証しない。標準組み込み名はモジュール冒頭の仮想導入として扱う。
        - 信頼済みShikumi宣言または `ExternalDefinitionsBuilder` からCall・Type・Generic Interfaceを登録し、明示的なimportと構文形が対応すれば専用Modelを生成する。登録に一致しなければ通常Modelを保持する。外部名を値として使うことや再束縛することを独自の規則で拒絶しない。既存の字句スコープで明確な隠蔽があれば専用認定を見送る。
        - 必要な利用側だけが `ImportPolicy(default, allow, deny, allow_star_import=False)` を渡してimport検査を委譲できる。denyを優先し、モジュール名の階層はallow/deny双方で照合する。`from M import N` ではdenyに限り `M.N` も調べる。`M:N` は識別子の完全一致。指定がなければ検査せず、star importもModel化する。
        - star importが暗黙に導入する名前や競合は推論せず、4軸・Collection認定・継承候補へ影響させない。明示的な通常importの束縛解析は維持する。
        - 関数内の `yield` / `yield from` は専用Generator Kindではなく通常のfunction/method Kindに `generator` Featureを付ける。Featureは `async`・`generator`・`lazy`。generatorメソッドも通常のmethodとして扱う。
        - 対応するインタープリタでは、3.12の型パラメータ構文、3.13の型パラメータ既定値、3.14のt-string、3.15のPEP 798とlazy importをModel化する。Model化できる構文は実行環境のPythonバージョンに依存する。現行の構造一覧は[LAYOUTS仕様正本ソース](../devdocs/canonical_sources/specification/layouts.py)を参照する。"""

        title @= "実装済みの範囲"

    class LIMITATIONS:
        """- 実行時の名前解決、型推論、確定代入、型互換性、ソースコードの実行・変換は提供しない。BindingStateおよび継承候補は安全性の証明ではなく、利用側が解釈・採否を決める。
        - import先を実際に読み込まず、star importの `__all__` も展開しない。ImportPolicyはAST上のimport文に対する静的な委譲検査であり、動的importや属性アクセスを制限するセキュリティ境界ではない。相対importはパスを推論しない。
        - 外部Interfaceは、登録済みの明示的importと構文的に一致した場合にだけ専用Model化する。引数不一致・未登録・明確な局所的隠蔽では通常Modelへフォールバックする。任意のメソッド呼び出し先・動的aliasを解決しない。
        - 深いASTについては反復処理と構文コンテキストの再利用で処理負荷を抑えるが、CPythonパーサー・コンパイラの深さと資源制約、およびすべての深さでの動作を保証しない。
        - Partial解析の `complete=False` は完全なModelではなく、特にパッケージの不完全結果では関係解析を省く。警告は診断一覧へ加えないため、必要に応じてホストが標準 `warnings` で取得する。"""

        title @= "既知の制約"

    class VERIFICATION:
        """- stage9の開発環境（Python 3.13.5）では668件実行、655件成功・13件スキップ、失敗0件。Ruff check・format、BasedPyrightはエラー0件。
        - stage8のレビュー環境から、Python 3.11・3.12・3.13・3.14・3.15とfree-threaded版3.14で660件すべて成功したとの報告を受けた。分岐カバレッジ95%、実コード9,892ファイルでクラッシュ0件、9,891ファイルの完全Model化を報告。これらのログは本書の環境では独立に確認していない。
        - stage9の差分については上記の全バージョンでの再検証結果をまだ記録していない。公開前に対象環境での最終テストを実施することが望ましい。"""

        title @= "テスト・検証状況"

    class PUBLICATION:
        """- v0.0.4は公開版として記録する。公開成果物は `README.md`、`docs/STATUS.md`、`CHANGELOG.md`、`docs/api_reference/` と `docs/DOCUMENTATION_POLICY.md` の英語文書。正確な仕様の編集元は `devdocs/canonical_sources/` の日本語正本。
        - CIはPython 3.11〜3.15を対象とする。PyPIとGitHub Releaseへのアップロードは別の手動ワークフローで実行する。本書の更新はその操作を実行しない。"""

        title @= "公開・配布"
