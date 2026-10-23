"""v0.0.2以降のコメント位置情報に関する開発判断。"""

from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title


@summary("ソース上のコメントを構造Modelと独立して扱う開発判断。")
@canonical_source(
    "shikake 開発履歴: コメント位置情報",
    filename="comments.md",
    order=30,
    merge_policy="forbidden",
    heading="title",
)
class COMMENTS_HISTORY:
    """0.0.1の過去の設計判断を上書きせず、0.0.2の変更を追記する。"""

    class V0_0_2_LINE_FOUNDATION:
        """- 型コメントのAST構文解析では予期しないエラーが生じる場合があるため、従来どおり `ast.parse(..., type_comments=False)` を維持する。コメントはModelのKind・Structure・Featureに加えず、tokenizeの独立した原文・位置情報として提供する。
        - コメントとModelの意味的な所属・型解釈は推定しない。行番号と「コードがある行か」という字句上の事実だけを索引化する。空行は上方探索を遮断しない。複数行の関数引数や括弧の行についても、Modelを割り当てずに行番号範囲や行末コメントを照会できる。
        - 最初の公開段階は `collect_comments()`、不変の `Comment`・`SourceComments`、`in_lines`・`on_right_of_line`・`above_line`・`module_header`・`module_footer` とする。Model起点検索と各Modelへの位置索引は後続段階で検証してから追加する。Modelに位置属性を増やしたり、ASTパーサーの失敗契約を変更したりしない。
        - tokenize側の文字列列位置とAST側のUTF-8バイト位置の差異を明示する。コメントだけの入力ではheaderとfooterの双方が全件を返し、意味的な所属は判断しない。この変更は未公開のv0.0.2に記録する。"""

        title @= "2026-10-23: v0.0.2コメント抽出と行位置照会の第一段階"

    class V0_0_2_MODEL_LINE_COMPOSITION:
        """- 第一段階で将来の候補としていたModel起点の独立したコメント検索APIとidentity位置索引は追加しないと決定した。既存の `Model.span` に開始行・終了行が公開されているため、行番号ベースの `SourceComments` を利用側がそのまま組み合わせればよい。
        - `span=None` のModel（モジュール根など）からは行番号を取得できない。同一行の複数Modelは同じ行検索結果となり、別ソースのModelでも数値が一致すれば検索できてしまう。ソースの対応と解釈は利用側の責務とし、コメントとModelの所属・所有関係は推測しない。
        - この判断に合わせて公開例・仕様・開発状況を更新し、位置索引を実装しない方針を明示する。コメントAPIと型コメントの非解析、およびv0.0.2開発中という扱いは維持する。"""

        title @= "2026-10-24: 行検索とModel.spanの合成を正式方針とする"

    class V0_0_2_DOCUMENTATION_COMPOSITION_AUDIT:
        """- 追加の専用APIを設けず、関数・クラスのbodyの最初の文の `span.line` を `above_line()` に、代入文の `span.end_line` を `on_right_of_line()` に渡す代表的な利用方法を文書化した。複数行の構文では `in_lines()` を用いる。問い合わせは行位置のみであり、コメントを特定の宣言・代入へ所属させない。
        - 日本語仕様・API・README・STATUS・CHANGELOGの正本と英語公開文書を照合した。追加したコメント処理はPython標準ライブラリのtokenize/io/bisect/dataclassesを使用するため、pyproject.tomlの実行時依存は従来のShikumiのみとする。v0.0.2は未公開のままとする。"""

        title @= "2026-10-24: コメント行検索の利用例と文書・依存監査"

    class V0_0_2_REVIEW_STABILIZATION:
        """- CRのみの改行でtokenizeの行番号がASTとずれていたため、StringIOのuniversal newlinesを用いてCR/LF/CRLFを同一の論理行として扱う。
        - SourceCommentsのコメント行・コード行索引は同じtokenize走査から内部的にのみ構築し、直接構築とdataclasses.replaceは公開契約から除外する。コピー・pickleでの復元は引き続き許容する。
        - デコレータの直前を調べる場合はデコレータ群の最小開始行を使い、本体先頭のコメントの例は最初の文の前に同一行のコードがないケースに限定する。コメントとModelの対応関係は導入しない。
        - 不正ソースに対するtokenizeのPythonバージョン別挙動は統一せず、対象PythonでASTが構文解析可能なソースに対してのみコメント収集結果を保証する。ファイルのエンコーディングとBOMにはtokenize.openを案内する。v0.0.2は未公開のまま。"""

        title @= "2026-10-24: コメント機能のレビュー修正と入力契約の明確化"

    class V0_0_2_REVIEW_COMPATIBILITY_AND_LINE_GUARD:
        """- `dataclasses.replace()` が `init=False` フィールドを指定された場合の例外型はPython 3.11/3.12では `ValueError`、3.13以降では `TypeError` であるため、テストでは両者を許容する。copy/pickleのラウンドトリップは別テストとし、先行する検証が失敗しても独立に実行できるようにした。
        - Model.spanの開始列を調べる本体先頭コメントの利用レシピでは、`str.splitlines()` を使用するとASTの論理行とは異なり改ページやUnicode区切り文字でずれる。そのため `collect_comments()` と同様に `io.StringIO(source, newline=None).readlines()` を利用し、CR・LF・CRLFを統一する。これは利用例とテストの修正であり、ライブラリ本体の公開契約には変更を加えない。
        - v0.0.2は未公開のまま、型コメント非解析とコメントの非所属性も維持する。"""

        title @= "2026-10-24: コメント利用例の行分割とPython間テスト互換性"

    class V0_0_2_DOCUMENTATION_RELEASE_DECISION:
        """- v0.0.2の最終レビューでは、Python 3.11〜3.15の5バージョンすべてで全件成功し、コメント関連19件、Ruff・BasedPyright、および公開英語文書のコメント使用例7件について問題がないとの報告を受けた。これは別環境の報告であり、ローカル実行結果とは区別する。
        - READMEのデコレータ例は直前の無装飾関数を再利用すると空結果になるため、デコレータとその直前コメントを含む独立した例に変更する。英語APIリファレンスの同種の例も同様に単独実行可能にする。コメントとModelの意味的な関連付けは引き続き行わない。
        - 公開文書と日本語正本はv0.0.2を2026年10月24日付のリリース内容として記載する。実際のPyPI・GitHub公開操作は利用者が別途行う。従前の未公開という開発記録は書き換えず、新しい決定を追記する。"""

        title @= "2026-10-24: v0.0.2最終レビューの反映と公開文書の確定"
