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
        """`parse_source(source, *, filename, index, definitions, import_policy, allowed_modules, syntax_validation)` は文字列のPythonソースを構文解析し、対応するModelを返す。与えられたソースを実行しない。"""

        title @= "単一ソースの解析"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_002:
        """`parse_package(directory, *, index, analyses, definitions, include, extensions, import_policy, allowed_modules, syntax_validation)` と `inspect_package(directory, *, index, analyses, definitions, include, extensions, import_policy, allowed_modules, syntax_validation)` は、実在するディレクトリ以下で指定された拡張子を持つ通常ファイルをファイルパス順に対象とする。`extensions` の既定値は `(".py",)` とし、詳細な照合・検証は `PARSING.SPEC_025` に従う。`include` 省略時は拡張子に一致する全ファイルを対象とし、指定時は `PARSING.SPEC_024` の選別後に残ったファイルだけを対象とする。`__init__` ファイルを必要とせず、特定のディレクトリ名やファイル名を暗黙に除外しない。"""

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
        """Strictの `parse_source` / `parse_package` はAST解析時と、既定のコンパイル水準の検証時に生じる構文エラーを `SyntaxError`、未対応AST構文を `UnsupportedSyntaxError` として拒否する。外部宣言との不整合は `ExternalModelingError` とする。未対応部分を成功した完全なModelとして黙って省略しない。"""

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
        """単一ソースの構文エラー、または外部構造の予約名・import配置・明示されたimport許可規則・保護された参照の書き換えなどファイル全体の整合性を損なう違反では、`SourceInspection.model` は `None` とする。既定のコンパイル水準の検証に失敗したソースも構文エラーとして同様に扱う。一方、未登録の構造呼び出し・外部構造の値としての使用・登録呼び出しの引数不整合は、局所エラーとして省略単位とともに診断し、回復できる構成木を返してよい。どちらも `complete=False` であり、Strict解析は従来どおり拒否する。"""

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
        """`InspectionIssue.category` は `unsupported_syntax`、`syntax_error`、`external_definition` のいずれかとする。`filename`、`node_type`、`message` と取得可能な `line`・`column` を保持し、行は1始まり、列は0始まりのUTF-8バイトオフセットとする。AST解析時の構文エラーの文字位置をUTF-8バイト位置へ変換し、ASTコンパイラの構文エラーはテキストがない場合もコンパイラ由来のUTF-8バイト位置を利用する。位置が得られない場合は `None` とする。"""

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
        """`inspect_package` は構文エラーまたはファイル全体の外部構造制約違反のあるモジュールを構成Modelから除外し、診断を残す。局所的な外部構造違反および未対応構文については、文単位の省略規則に従って回復できる範囲を保持する。他の解析可能なモジュールは保持する。エラーを含むファイルの存在だけを理由に、他の正常なファイルの構造を削除してはならない。"""

        title @= "不完全パッケージのモジュール保持"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_019:
        """`PackageInspection` は `package` に加え、`model`、`override_candidates`、`base_references`、`analyses`、`name_bindings` を同名の `PackageModel` 属性から読み取り専用で提供する。診断が1件でもあれば候補・基底参照・解析済み集合・束縛情報は空とし、`model` には省略可能な範囲で保持した構成木を返す。"""

        title @= "PackageInspectionの結果取得プロパティ"
        level @= MUST
        related @= (MODEL.SPEC_008,)

    class SPEC_020:
        """`InspectionIssue.code` は機械可読な識別子とし、`message` の文言から推測してはならない。構文エラーは `syntax.invalid`、未対応ASTは `syntax.unsupported` とする。外部構造違反のコードは以下の閉じた集合とする：`external.registered_star_import`、`external.unregistered_import`、`external.import_scope`、`external.import_conflict`、`external.wildcard_shadow`、`external.reserved_name_rebound`、`external.reserved_name_binding`、`external.interface_modified`、`external.interface_value`、`external.unregistered_call`、`external.too_many_positional`、`external.starred_positional`、`external.keyword_arguments`、`external.unknown_keyword`、`external.argument_mismatch`。外部例外を直接構築した場合の未分類コード `external.definition_error` と、診断オブジェクトを利用側で直接構築した場合の未分類コード `diagnostic.unspecified` を許容する。`details` は読み取り専用のキー/値情報であり、コードごとに確定した情報だけを載せる。登録済み外部CallMappingの引数診断では、`details.target` にソースに記述された呼び出し先を入れ、過剰な位置引数では `expected_count`（宣言数）と `actual_count`（明示された位置引数数）、未知のキーワードでは `keyword`、引数不足・重複では問題の `keyword` を返す。`*` 展開で実効引数数は推測せず、コード `external.starred_positional` を用いる。`**` 展開と重複キーワードは `external.keyword_arguments` に残し、既知なら `keyword` を付ける。`external.unregistered_import` は `details.path` に違反したimport記述、`details.policy` に許可モードを保持する。個別の英語メッセージを解析して補完してはならない。"""

        title @= "診断コードと構造化付加情報"
        level @= MUST

    class SPEC_021:
        """`utf8_byte_column_to_character_column(line, column)` は指定したソース行の0始まりUTF-8バイト位置を、0始まりUnicodeコードポイント位置へ変換する。負の位置、範囲外およびUTF-8文字の途中を指す位置は `ValueError` とし、AST・SourceSpan・InspectionIssueの格納位置は変更しない。タブ展開・表示幅の算出は行わない。"""

        title @= "診断列位置のUnicode変換"
        level @= MUST

    class SPEC_022:
        """外部構造のPartial回復は `external.unregistered_call`、`external.interface_value` と、登録済みCallMappingの引数検証違反（`external.too_many_positional`、`external.starred_positional`、`external.keyword_arguments`、`external.unknown_keyword`、`external.argument_mismatch`）だけを文単位で省略して継続する。同じ文中の複数違反は把握できる範囲で診断できるが、全件列挙の保証はしない。`if`/`elif` は一つの分岐Modelなので、`elif` 条件の違反では全分岐文を省略する。予約名の再束縛、保護された参照の書き換え、star import、外部importの位置や衝突、`import_policy` に対する違反はモジュール全体で拒否し、局所エラーよりも優先する。不完全なModelを完全な解析結果として扱わず、パッケージの関係候補・名前束縛の非公開規則を維持する。省略による情報欠落は省略箇所だけに限らず、保持した後続Modelの解釈（確定代入の判断等）にも影響し得る。保持されたModelの構造が正しくても、欠落した文や束縛が元ソースに存在しないと結論づけてはならない。省略文の書き込み事実は追加保証しない。"""

        title @= "外部構造違反の局所回復とファイル全体の拒否"
        level @= MUST
        related @= (MODEL.SPEC_001,)

    class SPEC_023:
        """`inspect_source` の `SourceInspection.name_bindings` は、診断がなく完全なModelを返せた場合に限り、パッケージ解析と同じ構文事実収集器から得た `NameBinding` を公開する。束縛の単位はModelに対応する字句スコープであり、単一ソースのモジュール名は `<source>` とする。構文エラー・外部構造違反・未対応構文による不完全な解析では、部分的にModelが得られても `name_bindings=()` とする。不完全な構文から束縛の全体像を断定してはならない。`parse_source` の戻り値と `inspect_package` の契約は維持する。"""

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
        """4つの解析APIは `syntax_validation: Literal["compile", "ast"] = "compile"` を受け付ける。既定の `"compile"` では `ast.parse(..., type_comments=False)` の後にASTを `compile(tree, filename, "exec", dont_inherit=True)` へ渡し、実行せずCPythonコンパイラの構文・スコープ検査を行う。`"ast"` はこの追加検査を省き、従来のAST解析水準でModel化を試みる。追加検査の省略はshikakeの非対応構文を許可するものではない。コンパイル検査が拒否したソースはStrictでは `SyntaxError` を送出し、Partialの単一ソースは `syntax.invalid`・`model=None`、パッケージでは当該ファイルを省略して他のファイルを継続する。既存の構文エラーと同じ診断カテゴリを用いる。`syntax_validation` が非文字列なら `TypeError`、未知の文字列なら `ValueError` とし、空のパッケージでも検証する。コンパイル検査ではコードオブジェクトを生成するが入力コードを実行・importせず、コンパイル成功は意味上の正しさ・実行時の安全性・確定代入を保証しない。対象Pythonのバージョンの文法・コンパイラ規則に従い、コンパイラ由来の警告を一律に抑制しない。ASTコンパイラ自体の深さ・資源制約を保証なく取り除くものではない。"""

        title @= "任意に省略できるコンパイル水準の構文検証"
        level @= MUST

    class SPEC_027:
        """既存ASTノードに新しい意味が加わる場合も、採用された構文は明示的なModel契約へ対応付け、未採用の構文を黙って読み飛ばしてはならない。Python 3.15の `ast.Import` / `ast.ImportFrom` の `is_lazy` が真である場合は、通常のimportと同一Kind・Structureを用い、import文Modelに `lazy` Featureを付与して明示された修飾を保持する。通常のimportには付与せず、aliasのModelにも付与しない。これは実行時の遅延ロードや初期化順序を判断するものではなく、束縛3軸と静的な参照先候補の評価規則を変更しない。古いPythonがlazy構文を構文解析できない場合は、そのPythonのパーサーの制約に従う。Python 3.15の展開付き内包表記（PEP 798）は `EXPRESSIONS.SPEC_031` に従ってModel化し、辞書型も新しいKind・Structureで通常の内包表記と区別する。通常のimportの従来Model化と、3.14以前のASTノードの扱いは維持する。今後追加されるすべてのASTフィールドや構文の自動検出を保証するものではなく、対応するPythonのバージョンごとにModelとの意味的な対応を検証する。"""

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
