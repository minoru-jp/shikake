"""公開文書と日本語正本ソースの管理・配備に関する正本。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}}: 文書管理ポリシー",
    filename="DOCUMENTATION_POLICY.md",
    merge_policy="all",
    heading="title",
)
class DOCUMENTATION_POLICY:
    """本文書は {{project.name}} の正本ソース、生成物、公開文書の区別と、変更・公開の手順を定めます。

    文書に記載されたAPIやモデルの個別の契約は、本ポリシーではなく、それぞれの仕様正本・API正本に従います。"""

    class AUTHORITY:
        """すべての管理対象文書の唯一の編集元は、`devdocs/canonical_sources/` にある**日本語の正本ソース**です。

        英語の公開Markdownは、その正本ソースから生成した日本語文書を基に翻訳・検証した成果物であり、独立した仕様の正本ではありません。公開版だけを直接修正して契約を変えてはいけません。"""

        title @= "正本と公開成果物"

    class PUBLICATION:
        """英語で公開する文書は、原則として次の5種類に限定します。

        - `README.md`：目的、概念、導入、基本的な利用例（リポジトリ直下）。
        - `CHANGELOG.md`：リリースバージョンと日付別の利用者向け変更履歴（リポジトリ直下）。
        - `docs/STATUS.md`：現在の開発状況と既知の制限。
        - `docs/api_reference/`：公開APIの説明・契約と索引。
        - `docs/DOCUMENTATION_POLICY.md`：この文書管理方針。

        `LICENSE` はリポジトリ直下に維持します。詳細仕様、モデリングポリシー、開発履歴は英訳しないで正本ソースとして保持します。変更履歴は日本語の `changelog/canonical.py` を正本とし、英語のルート `CHANGELOG.md` を配備します。v0.0.1は2026年10月23日付の初回リリースとして通常の変更履歴に記載します。公開APIの利用に不可欠な保証・制約は、英語のAPI Reference側にも簡潔に記載します。"""

        title @= "公開範囲と配置"

    class TRANSIENT:
        """日本語の正本文書は `devdocs/generate.py` で必要なときだけ一時生成し、内容検証・英訳を終えたら破棄します。

        リポジトリの `devdocs/canonical_documents/` には配置しません。後続工程へ一時生成物を渡すときは `-o` にリポジトリ外の一時ディレクトリを指定し、呼び出し元が終了時に削除します。生成した日本語文書そのものは版管理しません。"""

        title @= "日本語正本文書の一時生成"

    class CHANGES:
        """仕様・API・案内の変更は、該当する日本語正本ソースを先に修正し、参照とテストを検証します。その後、公開対象だけを翻訳し、正本の意味・API名・値・例外・制約と人手で照合します。正本と公開英訳の記述一致を自動テストで保証しようとはせず、発見した差異は正本に立ち返って個別に修正します。正本の検証・一時生成や公開文書のリンク確認、使用例の動作確認は別の検証として維持します。

        公開版の修正依頼があった場合も正本ソースへ戻って修正します。過去の開発履歴は書き換えず、新しい運用変更を履歴に追記します。正本の検証と公開英訳の更新は別工程であり、英訳が古いときは公開に進めません。"""

        title @= "変更・翻訳・検証の手順"

    class LINKS:
        """READMEは入口として簡潔に保ち、詳細な公開API契約へは `docs/api_reference/` を主な参照先とします。公開API参照では必要に応じて `MODEL.SPEC_005` のような**規則ID**と、対応する `devdocs/canonical_sources/specification/*.py` へのリンクを併記します。

        GitHub上の文書同士は配備位置に応じた相対リンクを使います。規則を指す際に変動しやすいPythonファイルの行番号を固定リンクにしません。PyPIにも表示されるルートREADMEからのリンクは、公開リポジトリ `https://github.com/minoru-jp/shikake` の絶対URLを使い、デフォルトブランチを指す `blob/HEAD/` に接続します。公開前にはリポジトリへのアクセスとリンク先の実在を確認します。

        公開しない日本語正本ソースは翻訳済みMarkdownとして存在するように案内せず、直接ソースへリンクします。"""

        title @= "公開文書の参照規則"

    class DISTRIBUTION:
        """sdistには `devdocs/`（正本ソースと生成スクリプト）を同梱し、`devdocs/canonical_documents/` は除外します。公開MarkdownはルートのREADME・CHANGELOGと `docs/` に置き、これらを通常の公開文書として配布します。

        リリース前に公開文書の配置、リンクの到達先、訳文と正本の整合性（人手のレビュー）、sdistの同梱・除外内容を確認します。翻訳内容の自動一致テストは実施しません。"""

        title @= "配布とリリース前検証"
