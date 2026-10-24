"""解析・入力・診断の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.model import MODEL


@summary("単一ソースとローカルパッケージの解析、Strict・Partialの失敗契約。")
@canonical_source(
    "{{project.name}}: 解析・入力・診断",
    filename="parsing.md",
    order=20,
    merge_policy="all",
    heading="identity",
)
class PARSING:
    """単一ソースとローカルパッケージの解析、Strict・Partialの失敗契約。"""

    class SPEC_001:
        """`parse_source(source, *, filename, index, definitions, syntax_validation)` は文字列のPythonソースを構文解析し、対応するModelを返す。与えられたソースを実行しない。"""

        title @= "単一ソースの解析"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_002:
        """`parse_package(directory, *, index, analyses, definitions, include, extensions, syntax_validation)` と `inspect_package(directory, *, index, analyses, definitions, include, extensions, syntax_validation)` は、実在するディレクトリ以下で指定された拡張子を持つ通常ファイルをファイルパス順に対象とする。`extensions` の既定値は `(".py",)` とし、詳細な照合・検証は `PARSING.SPEC_025` に従う。`include` 省略時は拡張子に一致する全ファイルを対象とし、指定時は `PARSING.SPEC_024` の選別後に残ったファイルだけを対象とする。`__init__` ファイルを必要とせず、特定のディレクトリ名やファイル名を暗黙に除外しない。"""

        title @= "パッケージの入力範囲"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_003:
        """入力ディレクトリは正規化する。ルートがシンボリックリンクなら拒否し、配下のシンボリックリンクを辿らない。重複したモジュール名へ対応する複数ファイルを発見した場合は拒否する。"""

        title @= "パスとシンボリックリンク"
        level @= MUST

    class SPEC_004:
        """パッケージ内の各ファイルはbytesとして読み取り、Pythonの `ast.parse(bytes, type_comments=False)` へ渡す。Pythonソースのエンコーディング宣言はPythonパーサに従い、型コメントはModel化対象としない。"""

        title @= "ソースのデコード"
        level @= MUST

    class SPEC_005:
        """Strictの `parse_source` / `parse_package` はAST解析時と、既定のコンパイル水準の検証時に生じる構文エラーを `SyntaxError`、未対応AST構文を `UnsupportedSyntaxError` として拒否する。外部定義そのものの不整合は定義の検証時に拒否する。未対応部分を成功した完全なModelとして黙って省略しない。"""

        title @= "Strict解析の失敗"
        level @= MUST

    class SPEC_006:
        """`inspect_source` は `SourceInspection` を、`inspect_package` は `PackageInspection` を返す。診断は `InspectionIssue` として分類・ファイル・ASTノード種別・位置、および省略単位を取得可能な範囲で保持する。完全性は `complete` で確認できる。"""

        title @= "Partial解析の診断"
        level @= MUST

    class SPEC_007:
        """未対応の式を直接構成要素として含む文は、その文を単位として省略する。対応可能な親構造の内部Blockに未対応の子文がある場合は、親と前後の対応済み兄弟文を保持してよい。未対応の親構造から子文だけを上位Blockへ持ち上げてはならない。"""

        title @= "Partialの省略単位"
        level @= MUST

    class SPEC_008:
        """単一ソースの構文エラー、または利用側が明示したImportPolicyへの違反では、`SourceInspection.model` は `None` とする。既定のコンパイル水準の検証に失敗したソースも構文エラーとして同様に扱う。一方、未登録の外部呼び出しや値参照、引数不一致は通常Modelとして保持し、外部使用規則によって拒絶しない。"""

        title @= "構文エラーと外部定義エラー"
        level @= MUST

    class SPEC_009:
        """不完全な `PackageInspection` では `base_references` と `override_candidates` を空にし、`analyses` も空集合とする。省略された定義を根拠に関係を断定してはならない。"""

        title @= "不完全パッケージの関係"
        level @= MUST

    class SPEC_010:
        """パッケージの関係解析は `analyses` による明示的指定に従い、`inheritance` と `override` を受け付ける。関係解析をソースModelの構成木とは別に扱う。"""

        title @= "明示的な関係解析指定"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_011:
        """`InspectionIssue.category` は `unsupported_syntax`、`syntax_error`、`external_definition`、`import_policy` のいずれかとする。`filename`、`node_type`、`message` と取得可能な `line`・`column` を保持し、行は1始まり、列は0始まりのUTF-8バイトオフセットとする。AST解析時の構文エラーの文字位置をUTF-8バイト位置へ変換し、ASTコンパイラの構文エラーはテキストがない場合もコンパイラ由来のUTF-8バイト位置を利用する。位置が得られない場合は `None` とする。"""

        title @= "診断のカテゴリと位置"
        level @= MUST

    class SPEC_012:
        """未対応式を含む文を省略するときは、原因となるASTの `node_type` と、実際に省略した文の `skipped_node_type`・`skipped_span` を区別する。位置を取得できない場合は `None` を許容する。局所的な外部構造違反でも原因位置と省略された文の位置を区別し、構文エラー・ファイル全体の外部構造違反では省略文を捏造しない。"""

        title @= "省略箇所の診断"
        level @= MUST

    class SPEC_013:
        """Partialでは、未対応構文を含む文を省略しても、対応可能な兄弟文や別のモジュールのModel化を続ける。入力が完全にModel化できた場合はStrictと同じModelを返す。不完全な結果は `complete=False` として区別し、ファイルI/Oエラー、モジュール名衝突、内部実装の不整合を未対応構文として一律に握り潰してはならない。"""

        title @= "Partialの回復範囲と完全性"
        level @= MUST

    class SPEC_014:
        """`# type: ...`、`# type: ignore` 等の型コメントはModel化・診断の対象外とし、その存在だけでStrictまたはPartialの成否を変更しない。一方、`x: T`、引数・戻り値の注釈など、Pythonの注釈構文はASTに基づいてModel化する。"""

        title @= "型コメントの非採用"
        level @= MUST

    class SPEC_015:
        """入力ルートのディレクトリ名をモジュール名の根とし、`pkg/util.py` または `pkg/util.dot` を `pkg.util`、`pkg/sub/__init__.py` または `pkg/sub/__init__.dot` を `pkg.sub` として識別する（実際に対象となるのは指定された拡張子だけ）。ルートの対象ファイルに `__init__` がある場合に限り根自身の `pkg` モジュールを生成し、初期化ファイルのない階層でも下位の対象ファイルを落とさない。異なる拡張子や通常ファイルと `__init__` が同じモジュール名になれば、既存の衝突規則により拒否する。複数の探索ルートを結合して名前空間パッケージを合成しない。"""

        title @= "モジュール名と__init__ファイルの境界"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_016:
        """`analyses` 省略時は `override` を選択し、その依存解析 `inheritance` も実施する。`analyses={"inheritance"}` は基底参照のみ、`analyses=set()` は関係解析なしとし、いずれも識別子の束縛事実を収集する。`analyses` は `None` または解析名文字列のIterableを受け付けるが、文字列単体（空文字列を含む）は `TypeError` として拒否する。解析名は `override` と `inheritance` の2種類に限り、未知の解析名は `ValueError` として拒否する。`PackageModel.analyses` は依存解析を含む実施済み集合を示す。"""

        title @= "関係解析の既定値と依存関係"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_017:
        """`inspect_package` の診断が1件でもある場合、`PackageInspection.name_bindings` と `PackageInspection.package.name_bindings` は空とする。不完全なモジュール群から得た識別子の束縛事実を、完全なパッケージの結果として公開しない。完全な場合はStrict解析と同じ束縛情報を取得できる。"""

        title @= "不完全パッケージの束縛情報"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_018:
        """`inspect_package` は構文エラーまたは利用側が明示したimport制限への違反があるモジュールを構成Modelから除外し、診断を残す。未登録の外部Call、値としての参照、再束縛、引数不一致はそれ自体でモジュールを除外しない。未対応構文は従来どおり文単位で回復可能な範囲の結果を残す。他の解析可能なモジュールは保持する。"""

        title @= "不完全パッケージのモジュール保持"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_019:
        """`PackageInspection` は `package` に加え、`model`、`override_candidates`、`base_references`、`analyses`、`name_bindings` を同名の `PackageModel` 属性から読み取り専用で提供する。診断が1件でもあれば候補・基底参照・解析済み集合・束縛情報は空とし、`model` には省略可能な範囲で保持した構成木を返す。"""

        title @= "PackageInspectionの結果取得プロパティ"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_020:
        """`InspectionIssue.code` は機械可読な識別子とする。構文エラーは `syntax.invalid`、未対応ASTは `syntax.unsupported` とする。import文の採否を理由とする専用診断コードは設けない。Call Mappingの不一致は診断ではなく通常のCall Modelに変換する。診断の `details` は読み取り専用で、確定した情報だけを載せる。"""

        title @= "診断コードと構造化情報"
        level @= MUST

    class SPEC_021:
        """`utf8_byte_column_to_character_column(line, column)` は指定したソース行の0始まりUTF-8バイト位置を、0始まりUnicodeコードポイント位置へ変換する。負の位置、範囲外およびUTF-8文字の途中を指す位置は `ValueError` とし、AST・SourceSpan・InspectionIssueの格納位置は変更しない。タブ展開・表示幅の算出は行わない。"""

        title @= "診断列位置のUnicode変換"
        level @= MUST

    class SPEC_022:
        """外部Call Mappingの引数不一致・未登録経路・値参照・再束縛を局所的な解析エラーとみなさず、通常のModelを保持する。そのため専用の外部Call違反の文単位省略・回復処理は行わない。未対応構文によるPartial解析の回復は別の契約に従う。"""

        title @= "外部Callに由来する局所エラー回復は不要"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_023:
        """`inspect_source` の `SourceInspection.name_bindings` は、診断がなく完全なModelを返せた場合に限り、パッケージ解析と同じ構文事実収集器から得た `NameBinding` を公開する。束縛の単位はModelに対応する字句スコープであり、単一ソースのモジュール名は `<source>` とする。構文エラー・未対応構文による不完全な解析では、部分的にModelが得られても `name_bindings=()` とする。不完全な構文から束縛の全体像を断定してはならない。`parse_source` の戻り値と `inspect_package` の契約は維持する。"""

        title @= "単一ソースの名前束縛事実"
        level @= MUST

    class SPEC_024:
        """`parse_package` と `inspect_package` は任意の `include: Callable[[Path, bool], bool] | None = None` を受け取る。`None`（省略時）は全候補を許可するコールバックと同じで、`.venv` 等の隠しディレクトリやビルド成果物も暗黙には除外しない。コールバックにはルートを基準に既存の入力パス解決を行った絶対 `Path` と、ディレクトリなら `True`、指定拡張子に一致する通常ファイルなら `False` を渡す。ルート自身は選別せず、下位ディレクトリには下降前、指定拡張子に一致する通常ファイルには読み取り前に適用する。`False` のディレクトリへは下降せず、その配下の候補もコールバックへ渡さない。指定拡張子に一致しないファイルとシンボリックリンクは対象外でありコールバックへ渡さない。コールバックの例外はStrict・Partialともに伝播する。選別後の入力集合に対してモジュール名の衝突を検査し、構成・関係・束縛解析を行う。除外はエラーやPartialの省略診断ではなく、選別後の集合を完全に解析できれば `complete=True` とする。除外された入力から未確認の関係を推論しない。コールバックの書式解釈、パス照合、警告の抑制はshikakeで実装しない。"""

        title @= "パッケージ入力の利用側コールバックによる選別"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_025:
        """`parse_package` と `inspect_package` の `extensions: tuple[str, ...] = (".py",)` は、探索対象の拡張子を指定する。空タプル・重複する拡張子・先頭の `.` を欠く値・単一拡張子でない値（例：`.tar.gz`）・globやパス区切り、空白を含む不正な値は `ValueError`、タプル以外や文字列でない要素は `TypeError` として拒否する。指定された拡張子だけを `Path.suffix` によって大文字小文字を区別して一致判定し、`.py` を暗黙に追加しない。指定順序はモジュールの探索順・優先度を変更せず、既存のファイルパス順を用いる。異なる拡張子で同一モジュール名になった場合は、どちらかを優先せず衝突エラーとする。`__init__` は指定拡張子のいずれでもパッケージ初期化ファイルとして扱う。拡張子指定は入力の発見方法のみを変更し、各ファイルはPython ASTとして解析する。独自構文・独自言語の解析を追加するものではない。`include` のファイル選別は拡張子照合後・読み取り前に適用し、除外による完全性の意味は `PARSING.SPEC_024` のままとする。"""

        title @= "パッケージ入力の拡張子指定とモジュール名の同一性"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_026:
        """4つの解析APIは `syntax_validation: Literal["compile", "ast"] = "compile"` を受け付ける。既定の `"compile"` では `ast.parse(..., type_comments=False)` の後にASTを `compile(tree, filename, "exec", dont_inherit=True)` へ渡し、実行せずCPythonコンパイラの構文・スコープ検査を行う。`"ast"` はこの追加検査を省き、従来のAST解析水準でModel化を試みる。追加検査の省略はshikakeの非対応構文を許可するものではない。コンパイル検査が拒否したソースはStrictでは `SyntaxError` を送出し、Partialの単一ソースは `syntax.invalid`・`model=None`、パッケージでは当該ファイルを省略して他のファイルを継続する。既存の構文エラーと同じ診断カテゴリを用いる。`syntax_validation` が非文字列なら `TypeError`、未知の文字列なら `ValueError` とし、空のパッケージでも検証する。コンパイル検査ではコードオブジェクトを生成するが入力コードを実行・importせず、コンパイル成功は意味上の正しさ・実行時の安全性・確定代入を保証しない。対象Pythonのバージョンの文法・コンパイラ規則に従い、解析中の警告はPython標準の警告機構を通じて呼び出し元へ渡す。shikakeは警告の捕捉・抑制・InspectionIssueへの変換を行わず、ホストのwarningsフィルタ設定に従う。警告が構文エラーへ変換されれば通常のSyntaxErrorとして扱う。ASTコンパイラ自体の深さ・資源制約を保証なく取り除くものではない。"""

        title @= "任意に省略できるコンパイル水準の構文検証"
        level @= MUST

    class SPEC_027:
        """既存ASTノードに新しい意味が加わる場合も、採用された構文は明示的なModel契約へ対応付け、未採用の構文を黙って読み飛ばしてはならない。Python 3.15の `ast.Import` / `ast.ImportFrom` の `is_lazy` が真である場合は、通常のimportと同一Kind・Structureを用い、import文Modelに `lazy` Featureを付与して明示された修飾を保持する。通常のimportには付与せず、aliasのModelにも付与しない。これは実行時の遅延ロードや初期化順序を判断するものではなく、束縛4軸と静的な参照先候補の評価規則を変更しない。古いPythonがlazy構文を構文解析できない場合は、そのPythonのパーサーの制約に従う。Python 3.15の展開付き内包表記（PEP 798）は `EXPRESSIONS.SPEC_031` に従ってModel化し、辞書型も新しいKind・Structureで通常の内包表記と区別する。通常のimportの従来Model化と、3.14以前のASTノードの扱いは維持する。今後追加されるすべてのASTフィールドや構文の自動検出を保証するものではなく、対応するPythonのバージョンごとにModelとの意味的な対応を検証する。"""

        title @= "未採用の新しいAST表現を黙って通常構文へ写さない"
        level @= MUST

    class SPEC_028:
        """AST→Modelの内部構築規則は、Python 3.13までに採用した構文を基礎規則とし、Python 3.14以降で導入された構文の差分を後続の内部規則として適用する。差分規則は、新しいASTノードだけでなく、既存ノードの新しい形や意味を基礎規則より優先して認識し、必要に応じて基礎規則を追加・上書き・明示拒否できる。どの規則でも対象外であれば未対応構文として拒否し、対象を認識した規則の失敗を「対象外」として別規則へ握り潰して再試行しない。非再帰のAST走査、子Model構築、ModelFactoryおよびPartialの診断・省略契約は共有する。規則の優先順位と委譲は非公開の内部実装とし、Modelに構文導入Pythonバージョンを付与せず、利用側が規則を選択する公開APIも提供しない。利用者はshikakeのリリースによりModel化契約を参照し、解析可能な入力構文は実行環境のPythonパーサーにも依存する。`syntax_validation` はコンパイル検査の水準の指定であり規則バージョンの選択ではない。"""

        title @= "3.13基礎規則と3.14以降の内部差分規則"
        level @= MUST

    class SPEC_029:
        """`SourceInspection` の `repr` はModelの省略付き概要と `name_bindings` の件数を示し、`NameBinding` の各要素を展開しない。一方、`SourceInspection` と `PackageInspection` の `issues` は診断内容を確認できるよう全件表示する。`PackageInspection` に含まれる `PackageModel` の表示は関係要素を展開しない。これらの `repr` はデータのシリアライズや `eval` による復元を保証せず、診断件数に応じて表示全体が長くなる場合はある。"""

        title @= "Partial解析結果の省略表示と診断の保持"
        level @= MUST
        related @= (MODEL.SPEC_022,)

    class SPEC_030:
        """`collect_comments(source: str)` は、ASTと独立して `tokenize` により原文のコメントトークンを収集し、`SourceComments` を返す。`Comment` は `#` を含む原文、1始まりの行、0始まりのUnicode文字列位置（開始列・終了列）を持つ不変の付帯情報で、Model構成木の要素・Feature・型推論結果ではない。型コメントと `# type: ignore` も解釈せず原文のまま収集する。CR・LF・CRLFの改行は統一して行番号を数え、ASTの行番号と一致させる。`SourceComments` は `collect_comments()` のみから生成し、直接構築や `dataclasses.replace()` をサポートしない。コメント行索引は同じ字句解析結果から構築し、不整合な内部索引を外部から渡せないようにする。従来の `ast.parse(..., type_comments=False)` と `PARSING.SPEC_014` のModel化非採用を変更しない。"""

        title @= "ASTから独立したコメント原文の収集"
        level @= MUST

    class SPEC_031:
        """`SourceComments.comments` はコメントをソース順のタプルで返す。`in_lines(first, last)` は1始まりの閉区間にあるコメントをソース順で返す。`on_right_of_line(line)` は同じ行にコメント以前のコードトークンがある場合だけ当該行のコメントを返す。`above_line(line)` は指定行を含めず上方のコードを含む直近の行まで探索し、間のコメントをソース順で返す。空行とコメントのみの行は遮断しない。`module_header()` は最初のコード行より前、`module_footer()` は最後のコード行より後のコメントを返す。コードが存在しないソースでは両方とも全コメントを返す。位置や改行数から意味上の所属関係を推測しない。行番号は整数かつ1以上とし、不正型はTypeError、不正範囲はValueErrorとする。"""

        title @= "意味的な関連付けを行わない行検索"
        level @= MUST

    class SPEC_032:
        """`collect_comments()` は独立のUnicodeソース文字列を入力とし、結果の保証対象は利用中のPythonのASTで構文解析できるソースに限定する。AST解析を内部で実行することはなく、不正なソースでのtokenizeの結果・例外種別はPythonのバージョン間で保証しない。ファイルから文字列を読む際は `tokenize.open(path)` を利用し、エンコーディング宣言やUTF-8 BOMを処理してから、同じ文字列をModel解析とコメント抽出へ渡せる。tokenizeに伴う字句エラー（`TokenError`、`IndentationError`等）を利用側へ伝播する。Strict/PartialのAST解析APIを内部で呼ばず、既存解析の成否や診断結果を変更しない。コメントの列はtokenizeのUnicode文字オフセットで、AST/SourceSpanのUTF-8バイトオフセットとは異なる。文字列リテラル内部の`#`はコメントではなく、複数行トークンが占める行はコードのある行として扱う。既存の `Model.span` の行番号を `above_line`・`on_right_of_line`・`in_lines` に渡すことはできるが、Modelを受け取る専用検索やASTとの位置対応索引は提供しない。span=None のModelには利用できず、同じ行の複数Modelからは同一の行検索結果になる。ソースとModelの出自の一致およびコメントの所属は検証・推定しない。関数・クラスの本体先頭にあるコメントを調べる際は、定義Modelの開始行ではなく、bodyの最初の文のspan.lineを上方検索に指定できる。ただしその文の開始列より前が同じ行のコードではなく空白のみの場合に限り、本体先頭のコメントを探す利用例として適用する。ヘッダーと本体が同じ行の場合は適用しない。デコレータ付き定義の直前を調べるときは、定義の開始行と各デコレータの開始行の最小値から上方検索する。代入文の行末コメントを調べる際は、代入文のspan.end_lineを行末検索に指定できる。いずれも単なる行位置照会であり、内部のコメントを含む複数行構文にはin_linesを利用する。"""

        title @= "コメント字句解析のエラー・座標系と境界"
        level @= MUST

    class SPEC_033:
        """4つの解析APIは `import_policy: ImportPolicy | None = None` を受け付ける。指定がなければimport規制を行わない。指定時は、文字列パス `module` は当該モジュールと、その `module.` 以下の子モジュールを階層照合し、`module:Name` は完全一致とする。`from M import N` では、denyに限り `M.N` の候補パスも照合する（名前が実際にサブモジュールであるかは解決しない）。`deny`、`allow`、`default` の順に評価する。`deny`を優先する。`ImportPolicy` の既定は `default="allow"` と `allow_star_import=False` であり、star importは許可を明示したときだけ、対象のモジュールを通常ルールでも検査する。相対importは実体を推論せず、`default`に従う。Strictは`ImportPolicyError`を出し、Partialは`category="import_policy"`の診断としてファイル単位で不完全を示す。import先を実際に読み込んだり、star importから名前を展開したりしない。"""

        title @= "明示的に委譲されたimport検査"
        level @= MUST
