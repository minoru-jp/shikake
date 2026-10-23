"""Micaの初回リリース前の開発履歴。"""

from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title


@summary("初回リリース前の設計判断、実装、実験および文書整理の記録。")
@canonical_source(
    "Mica 開発履歴: リリース前の開発",
    filename="pre-release.md",
    order=10,
    merge_policy="forbidden",
    heading="title",
)
class HISTORY:
    """初回リリース前の作業・設計判断・試作と検討結果を記録します。過去の `examples/` などのパスは当時の記録であり、整理後には存在しない場合があります。"""

    class OCT_18:
        """- 開発名を `Mica` とし、公開時の名称は別途検討する。
        - 初期開発バージョンを `0.0.1` とする。
        - 旧 `pyinto` は参考資料とし、直接の移行を行わない。
        - Python ASTから、旧設計より抽象度の高いModelを作るライブラリに目的を限定する。
        - 再帰的テンプレート機構の考え方は直ちに破棄せず、採否を今後検討する。
        - 開発履歴とCHANGELOGを分離し、公開向け変更のみをCHANGELOGに記載する。
        - パッケージ・テスト・文書管理のスケルトンを作成。ModelのAPI・実装にはまだ着手しない。
        """

        title @= "2026-10-18: プロジェクト初期化"

    class OCT_18_DESIGN:
        """- Model化の目的を、Python構文の忠実な再表現ではなく、処理の役割・構造・関係の抽出に置くことで合意した。
        - 主な想定用途はコード変換だが、特定の変換先・実行環境・業務ドメインには結び付けない。
        - 設計では「何をModelに含める／含めないか」という採用境界を常に明示的に判断する。
        - 検討の結果Modelに採用しないものは、設計上の「不採用」として理由を記録する。未検討・未実装と混同しない。
        - 採用した概念について利用側に必要な情報は保持する一方、CPython実行仕様の完全再現を目的としない。
        - 詳細な分類、構文の対応、保持すべき情報の契約、走査・変換機構は引き続き設計課題とする。
        """

        title @= "2026-10-18: Model化の設計目標と採用境界"

    class OCT_18_KIND_INDEX:
        """- 変換等の利用側が、処理開始前に入力Modelに出現した種類を調べ、対応可否を判断できる設計を目指すことに合意した。
        - Kindを平坦な対応表ではなく、一般的な分類から特殊化した分類へ参照できる階層的Indexとする方針を採用した。
        - Kindの分類関係（「一種である」）とModelの構成関係（「含む」）を区別する。
        - 対応、拒否、上位Kindへの一般化の判断はMicaではなく利用側が行う。Micaは自動的に丸めず、変換の妥当性を保証しない。
        - 分類体系・単一親の木で十分か・出現位置の扱い・具体的APIについては未決定とした。
        - 文書上の設計方針のみ更新し、Modelや検査機能の実装には着手しない。
        """

        title @= "2026-10-18: Model Kind分類Indexの基本方針"

    class OCT_18_EXTENSION:
        """- 基本Modelを処理の抽象的な役割・構造・関係に集中させる方針を確認した。
        - ドメイン固有の意味・制約は基本Modelに埋め込まず、利用側が追加できる拡張性を設計要件とした。
        - 拡張情報の解釈・対応可否と利用方法は利用側が決定し、Micaは特定の変換方法を規定しない。
        - Model Kindの分類Indexと追加のドメイン情報は異なる役割として整理する。
        - 拡張機構の形式、情報の照会方法、非対応時の扱いは未決定とし、仕様上の方針だけを文書化した。
        - CHANGELOGは利用者向けの公開変更に限るため、今回の設計経緯は開発履歴に記録した。
        """

        title @= "2026-10-18: 基本Modelとドメイン拡張の責務分離"

    class OCT_19_KIND_STRUCTURE:
        """- Kindの階層分類に加え、Kindごとの役割付き構造契約を定義する方針を整理した。
        - 分類関係（「一種である」）とModelの構成関係（「含む」）は明確に分離する。
        - Shikumiで信頼できるPython定義を読み、Mica固有の規則で検証し、Index成果物を永続化する構成を推奨方針とした。Mica実行時は生成済みIndexを使い、Shikumiを必須としない方向とした。
        - KindにはPythonのクラス名に依存しない安定IDを設ける。単一親の分類木を初期案とするが、具体的なKind体系とShikumiの定義体・生成形式は未確定。
        - モデル化の検討はPython構文の意味論への写像から始めず、コードに書かれた部分を素直に説明するところから始める。
        - `remaining[line.sku]` を例に、添字アクセスから対象・添字を、添字の属性アクセスから対象・属性名を役割付きで再帰的に辿る構造を検討した。
        - Micaは値（オブジェクト）がコード上でどう記述されているかを扱い、参照先・共有関係の解決を引き受けない。
        - Index生成、Model構造、利用側の対応検査を分離する方針を文書化し、具体的な公開APIやModel実装は行わない。
        - CHANGELOGは公開向け変更ではないため更新しない。"""

        title @= "2026-10-19: Kind定義・永続化・構造探索の設計方針"

    class OCT_19_SHIKUMI_CORRECTION:
        """- Shikumiの「規定体」「記述体」「実現器」の責務を実装・同梱仕様と照合して再整理した。
        - 規定体は構造・付随情報・検証規則を定め、記述体はその規則に従ってKind階層と構造契約をPythonで記述するものとした。
        - Python記述体のソースが永続化された正本となるため、内部処理用のIndexをJSON等として別途生成・保存する前提を撤回した。
        - Micaが実行時にShikumiのPython APIからSemanticView等を取得する方向へ修正した。必要であれば実現器がメモリ上のMica用Indexを構築できるが、実現器の利用自体は必須としない。
        - この方式ではShikumiへの実行時依存が生じるため、具体的な依存関係・初期化・キャッシュは実装時に決める。
        - 前項の「生成済みIndexを保存して利用し、Shikumiを実行時依存から外す」案は、この判断によって置き換えられた。公開向けCHANGELOGは変更しない。"""

        title @= "2026-10-19: Shikumi規定体・記述体によるIndex運用への修正"

    class OCT_19_INITIAL_IMPL:
        """- Shikumiの規定体・記述体からPython APIのみでKind Indexを構成し、単一親の分類・役割付き構造契約を検証する初期実装を追加した。
        - `mica.parse_source()` を設け、送料計算サンプルのASTからModelオブジェクトを生成できるようにした。
        - 型注記付き変数定義、関数・引数、単一代入、True/Falseブロックを持つ分岐、返却、名前・値・アクセス・演算をModel化した。
        - Modelは `parts()`、`get(role)`、`walk()` を提供し、構成要素の役割・順序と再帰的な導線を保持する。
        - 既知の入力だけを処理し、未対応構文を明示的に拒否する。これは未検討・未採用の最終判断とは区別する。
        - `examples/shipping.py` で初期統合試験を実施し、46 Modelノード・24 Kindを確認した。実行時の参照解決・値評価・コード変換は実装しない。
        - 初期仕様を `initial-implementation.md` として追加し、現在のREADME・STATUS・関連仕様書に反映した。開発段階の変更であり、CHANGELOGは変更しない。"""

        title @= "2026-10-19: 初期Kind IndexとASTからのModel化を実装"

    class OCT_19_KIND_SPLIT:
        """- Kind定義の増加に備え、単一の `description.py` から `description/` パッケージ配下のトピック別モジュールへ移行した。
        - 規定体はShikumi標準の `PackageTreeStructure` を採用し、記述体パッケージのモジュールをPython APIから一括解釈する。
        - Kind分類上の親子関係はモジュールの配置やクラスのネストではなく、明示的な `parent_id` で規定する。既存24 KindのIDと構造契約は維持した。
        - 別ファイル追加時の自動発見と未知の親分類の拒否をテストし、既存の送料計算サンプルのModel化を回帰検証した。
        - 複合代入演算子（例: `+=`）と比較演算子（例: `>=`）を混同しないよう整理した。今後のモデル化でも、書かれた操作を別の文・演算へ暗黙に展開しない方針を確認したが、複合代入Modelは未実装である。
        - 内部JSON・CLIは導入せず、開発履歴と現行仕様を更新した。CHANGELOGは公開向けのリリース記録に限定するため変更しない。"""

        title @= "2026-10-19: Kind記述体の分割管理を実装"

    class OCT_19_PACKAGE_IMPL:
        """- 送料計算の4ファイルパッケージ（`shop`）を新たな統合サンプルとして作成した。
        - `parse_package` によりローカルのPythonパッケージをAST解析し、Module・Class・Method・ImportFrom・Call・FloorDivisionを含む役割付きModelオブジェクトを構築する処理を追加した。
        - Shikumiの分割記述体でKindと役割契約を管理し、Kind数は24から32に増えた。既存の46ノードを返す `parse_source` の回帰テストを維持した。
        - AST内の基底クラス指定と同名メソッドをパッケージ内で照合し、`OverrideCandidate` として派生・基底両側の実際のModelオブジェクトへの導線を保持した。
        - 継承メソッドの捏造、外部importの実行、MROの解決は行わない。構成木の走査と照合関係の探索は独立させた。
        - 仕様書に入力・Kind・API・照合の根拠・制限を記録し、README・STATUS・関連仕様書を更新した。CHANGELOGは未公開開発のため変更しない。"""

        title @= "2026-10-19: パッケージModel化とオーバーライド候補の試作"

    class OCT_19_PARTIAL:
        """- Strictの `parse_source` / `parse_package` を変更せず、開発・検証用の `inspect_source` / `inspect_package` を追加した。
        - 対応済みの兄弟文やモジュールは継続してModel化するが、未対応の親構造の内部を上位ブロックに移動しない。未対応式を含む文は文単位で省略し、診断に原因・省略範囲・ファイル・位置を残す。
        - Python構文エラーはソース単位の診断にし、単一ソースではModel=None、パッケージでは当該モジュールを省略して他モジュールを継続する。
        - 部分的なパッケージに対して確実でないオーバーライド候補を報告しないため、診断が存在する場合の候補照合は抑止した。完全な入力はStrictと一致する。
        - ShikumiによるKind分類・構造契約は変更せず、開発用の欠落情報をModelとは別の `InspectionIssue` として表現した。
        - `partial-modeling.md` を新規作成し、README・STATUS・関連仕様書を更新。通常のコード変換用APIと混同しない条件を明文化した。CHANGELOGは公開向け履歴のため変更しない。"""

        title @= "2026-10-19: 開発用Partial Model化を実装"

    class OCT_19_REFERENCE_BOUNDARY:
        """- AST上で定義元の情報を照合することと、外部ライブラリの実行挙動を解釈することを分離する方針を採用した。
        - 標準ライブラリとサードパーティー製ライブラリは同じ照合原則で扱う。変換先のライブラリ選択、置換、非対応判定、実行上の意味付けは変換側の責務とした。
        - import記述は照合の成否と独立に保持し、照合できない場合も元のModelを欠落させず、未解決・曖昧を推測で埋めない方針とした。
        - 外部情報源として `.py` と `.pyi` を検討する。ソースやスタブをASTとして読むことと、任意のPythonコード・対象ライブラリを実行・importすることを混同しない。
        - 外部探索は利用側の明示的な情報源・範囲を前提とし、照合結果の根拠・供給元を追える方向で検討する。現行の `parse_package()` の内部パッケージ照合は維持し、外部探索を実装済みとは扱わない。
        - `reference-resolution.md` を追加し、既存の対象範囲・Model・構造・拡張性・パッケージ仕様、READMEとSTATUSに責務境界を反映。実装やCHANGELOGは変更しない。"""

        title @= "2026-10-19: ASTによる定義元照合と変換側の責務分離"

    class OCT_19_FUNCTION_CLASS_FORMS:
        """- 関数定義と呼び出し形式を優先し、ABC・標準デコレータを併せて検証する注文計算サンプル `examples/order_calculation.py` を追加した。サンプル自体の計算結果は3100。
        - 既存のFunction/Method/Parameter/Class/Call Kindを再利用して、位置専用、可変長位置、キーワード専用、可変長キーワード引数、デフォルト値、デコレータを役割付きで保持するよう契約を拡充した。
        - KeywordArgument・StarredArgument・DictionaryEntryはClass/Call/Dictionaryの下位Kindではなく、共通の構造補助Kindとして分類した。Kind IDの重複と誤分類を回避した。
        - リスト、辞書、減算、論理否定、raise、単独の式文もサンプルに必要な範囲で採用した。複合演算やオブジェクトの実行上の意味へ展開しない。
        - Shikumiの分割記述体からIndexを構成する方式と既存APIを維持。Strictで168ノードのModelが得られ、42 Kindを確認した。既存サンプルの46/91ノードも維持した。
        - 新規仕様 `function-class-modeling.md` とREADME・STATUSを更新。初期仕様に残っていた未対応記述は現行実装に合わせ修正した。CHANGELOGは未公開開発の記録と区別して変更しない。"""

        title @= "2026-10-19: 関数・呼び出し形式とデコレータ付きクラスのModel化"

    class OCT_19_OPERATION_KINDS:
        """- Partial方式の標準ライブラリ・Mica・Shikumiに対する外部レビューを踏まえ、比較・論理・二項・単項の演算表現を拡張した。
        - 単一比較10種、二項演算13種、単項演算4種、論理演算2種、連鎖比較をASTの書かれた形のままModel化する。連鎖比較は順序付きの比較ステップで保持し、`and` や複数文へ展開しない。
        - 既存の比較・演算Kindを再利用し、Shikumiの記述体を領域別ファイルへ配置。構造補助KindはOperationの下位ではなくStructuralPartの下位とする。
        - `not` は既存IDと`operand`契約を維持し、分類上の親を `model.value.operation.unary` に移動した。
        - `int | None` はUnion型へ、`-1` は負数リテラルへ推論・変換しない。評価意味や変換先の実装方式をMicaへ持ち込まない。
        - 既存42 Kindから69 Kindへ増加。`examples/quote_rules.py` の出力と比較・論理・二項・単項演算の網羅テストを追加した。
        - サンプル・一般的PythonコードのModel残存率や自己ホスト性は採用判断の参考に過ぎず、Modelの網羅自体を開発目標としない。
        - `pass`、Ellipsis、通常import、複合代入は本作業の対象外に据え、改めて採否を判断する。CHANGELOGは未公開開発のため変更しない。"""

        title @= "2026-10-19: 演算Kindの分類とModel化の拡充"

    class OCT_19_SPECIAL_STATEMENTS:
        """- Modelの採否判断に基づき、`pass`、`None`・`Ellipsis`、通常import、複合代入13演算子を採用した。
        - `pass` は空の構造契約を持つ明示的な文、`None`と`Ellipsis`は `Literal` / `SpecialValue` 配下の別Kindとし、実際のシングルトンを値として保持する。`return` の値の不在と `return None` を区別する。
        - 通常importには既存の `Import` 分類と `ImportAlias` 構造を再利用し、複合代入は通常代入Kindの下位分類に13種を追加。記述された操作を代入＋二項演算へ展開しない。
        - これらの構文がどのような目的で使われるべきか、適切な記述であるかの判断はMicaの責務としない。基底Kindや構造契約は重複定義しない。
        - Shikumiの記述体から取得するKind数は69から88に増加。`examples/fee_adjustments.py` とテストでStrict/Partial双方のモデル化・分類・構造保持を確認した。
        - `special-statements.md` を新規仕様として作成し、README・STATUS・Index・関連仕様を更新。開発履歴に追加し、未公開の開発変更であるためCHANGELOGは変更しない。"""

        title @= "2026-10-19: 特殊値・import・複合代入のModel化"

    class OCT_19_CONTROL_FLOW:
        """- Modelの抽象度は一律に決めず、利用側が変換対象の主題を把握できることから採否・一般化を判断する方針を改めて確認した。
        - `if` と `match` はBranch、`for` と `while` はIterationとして扱い、条件式・パターン・ブロックは独立してModel化する。演算子などの既存の個別分類は一般化しない。
        - 既存 `model.statement.branch` Kind IDを維持しつつ、`subject` と役割付き `paths` に契約を更新した。旧 `condition`/`true_block`/`false_block` を利用する側には互換性上の変更が生じる。
        - 条件・パターン・ガード・各経路を分け、`elif` と入れ子 `else: if` の区別、パターンの構成要素、反復のelse、break/continue、try/except/else/finally、except*の記述上の違いを保持する。
        - Shikumi記述体を `control.py` / `pattern.py` / `structure.py` に分離して拡充し、Kind ID・親分類・構成要素の重複を検証した。Kind Indexは88種類から108種類となった。
        - 在庫イベント処理サンプルとModel木の出力例、Strict/Partialと各経路を検証するテスト、新規仕様 `control-flow-modeling.md` を追加した。Micaは入力ソースを実行しない。
        - 今回の変更は開発中の設計変更として開発履歴に記録し、CHANGELOGは変更しない。"""

        title @= "2026-10-19: 制御構造の役割による一般化と初期Model化"

    class OCT_19_VALUE_EXPRESSIONS:
        """- Partial方式による実コードのフィードバックを踏まえ、まず値を構成する式を個別に採否判断した。受理率向上は補助指標であり、あらゆるPython構文を網羅することを開発目的にはしない。
        - スライスはIndexAccessの子として `start` / `stop` / `step`、f-stringは文字列片と埋め込み式の列（変換指定・入れ子書式を含む）、条件式は独立したValue Selection、集合リテラルは既存Collectionの一種としてModel化した。
        - `# type: ignore` は `Module.type_ignores` に保持される型チェック用の付随情報であり、Model化の採用対象外としてStrict/Partialの拒否・診断から除外した。他の型コメントの非対応条件は維持した。
        - Kindは108から113種類となり、既存Kind ID・契約を維持した。新しい値式サンプル、Model出力、構造・回帰テストを追加した。
        - `value-expressions.md` を新たなCanonical Sourceとして追加し、README・STATUS・Partial仕様・初期仕様・開発履歴を再生成した。CHANGELOGは未公開開発のため変更しない。"""

        title @= "2026-10-19: 値式の第1段階拡張とtype ignoreの非モデル化"

    class OCT_19_ASSIGNMENT_STRUCTURES:
        """- ASTの `Assign.targets`、入れ子のTuple/ListとStarred、`NamedExpr.target/value` を検証し、値の配分・実行意味を推測せずに構成情報を採用した。
        - 既存の `model.statement.assignment` の契約を `target: node` から `targets: nodes` に変更し、単一代入でも要素1個のタプルとした。多重代入は1つの文として保持し、元の記述順序を維持する。既存利用側の `get('target')` は互換性のない変更として記録した。
        - タプル・リスト・名前・属性・添字の既存Modelを再利用し、スター付き代入先 `model.structural_part.starred_target` を追加。`for` のbindingにも同じ構造を使用する。
        - セイウチ演算子 `:=` は文ではなく `model.value.binding` とし、targetとvalueを式の構成要素として保持する。複合代入の個別Kindや `target/value` 契約は維持する。
        - パッケージの候補照合におけるモジュール直下の名前再束縛検出も、複数代入と入れ子の束縛先に対応した。属性・添字アクセスを名前の再束縛とはみなさない。
        - Kindは113から115種類。新規サンプル・再帰的Model木、Strict/Partialと旧Modelの回帰テスト、Canonical Source `assignment-structures.md` を追加し、README・STATUS・初期仕様・開発履歴を同期させた。CHANGELOGは未公開開発のため変更しない。"""

        title @= "2026-10-19: 多重代入・アンパック代入・束縛式のModel化"

    class OCT_19_CONTEXT_COMPREHENSIONS:
        """- 第3段階として、AST上の`With.items`と`body`、4種類の内包表記にある`generators`、`elt`/`key`/`value`等を調査した。既存のAST情報を利用側へ渡し、変換方法の推奨や実行意味の補完は行わない方針を再確認した。
        - 同期`with`を文脈ブロックとしてModel化し、複数文脈項目の順序、各式と省略可能な`as`束縛先、Blockとの関係を維持した。
        - `model.value.comprehension`を分類上の親として4形式の構築式Kindを追加し、構築する要素、辞書のkey/value、多段の反復節・各節に属する条件を保持する。通常のIterationへ展開しない。
        - `comprehension_clause`の`target`/`iterable`/`filters`/`is_async`は構造情報であり、変換側が反復へ展開するための材料となる。ただし方法論、スコープ、評価順序、Generatorの振る舞いの実装責務は変換側とする。非同期構文の採否は別段階とし、混同しない。
        - Kind数は115から123へ。`examples/context_comprehensions.py`と再帰Model木、Strict/Partialの境界を検証するテスト、Canonical Source `context-comprehensions.md`を追加し、既存のテスト・仕様・README・STATUSを更新した。開発中の変更なのでCHANGELOGは変更しない。"""

        title @= "2026-10-19: 文脈ブロック・内包表記の第3段階Model化"

    class OCT_19_GENERATOR_SUBJECT:
        """- 利用側の早期の対応判断を重視し、Generatorを通常のFunction/Methodの下位ではなく、`model.definition.generator` という独立した主題に分類する方針を採用した。`OrdinaryFunction`などの対称分類は新設しない。
        - Generatorの署名・デコレータ・戻り値注釈・本文は既存のFunctionと同じ役割契約で保持し、Kindの親子関係と構造の共通性を区別した。クラス内にあるGeneratorはクラスの本文との構成関係で表す。
        - `yield`と`yield from`の式を採用し、式文・代入式の内部・値の省略を区別して保持する。元の記述を反復や状態遷移へ変換しない。
        - 定義自身に属するyieldのみで分類し、入れ子関数・クラスの本文のyieldを外側へ混入させない。入れ子定義のデフォルト値・デコレータと内包表記の外側反復対象の式は区別する。到達可能性や実行意味は解析しない。
        - パッケージの同名メンバー照合でGeneratorを定義として認識するよう更新したが、実行時のオーバーライドは保証しない。既存のGenerator相当のMethodについてはKind IDが変わるため利用側の移行が必要になる。
        - Kind Indexは123から126種類へ増加。Strict/Partial、Shikumi構造契約、パッケージ関係、サンプルのModel出力、文書正本と回帰テストで検証した。未公開開発のためCHANGELOGは更新しない。"""

        title @= "2026-10-19: Generatorを独立した定義主題としてModel化"

    class OCT_19_KIND_CONTRACT_FEASIBILITY:
        """- 利用側の対応判断を保ちつつ、Kindの単一親分類・共通構造契約・非同期の横断的特徴を分離できるか実験コピーで検証した。
        - Shikumiの規定体へ共通契約定義・参照、横断的特徴の定義・適用先、親子契約互換性の検証を追加した。Shikumi本体の変更は不要であった。
        - Function/Method/Generatorの共通契約を統一し、二項演算・特殊値・単項・論理Kindの契約継承を試した。
        - `Realizer[KindIndex]` を使い、SemanticViewからJSON等を保存せず、メモリ上でKind Indexを実現できた。
        - 複合代入の再親付けは契約整合性に効果があるが、既存の`is_a()`とKind IDプレフィックスに互換性上の課題を残すため、最終案としては未決定とした。
        - `async` 特徴は宣言・適用範囲・ModelFactoryでの検証までの試作に限定し、非同期構文のパーサー実装・変換方式は未着手とした。
        - 実験コピーは127 Kind / 1特徴 / 97テストを確認した。開発過程の検証なのでCHANGELOGは変更しない。"""

        title @= "2026-10-19: ShikumiによるKind契約・横断的特徴の実現可能性を検証"

    class OCT_19_KIND_STRUCTURE_ARCHITECTURE:
        """- Kindに分類と構造規約を重ねた従来方式を見直し、Kind・Structure・Featureを独立したShikumi記述体で管理するアーキテクチャを正式採用した。
        - Kindは主題の単一親分類およびStructure参照のみを保持し、is_a()は分類のみを問い合わせる。親子のrole/shape継承・自動合成は採用しない。
        - Structureは順序付きrole/shapeの完全な定義であり、異なるKind間で共有する。通常代入のtargets/valueと複合代入のtarget/valueは分類の親子関係を維持したまま別々のStructureとして保持できる。
        - Function/Method/Generatorはcallable_definition、二項演算・単一比較はbinary_operands Structureを共有する。共有のためだけに実験で加えたBinaryOperation分類は除き、126 Kind、51 Structure、1 Featureとした。
        - Shikumi規定体ではKind・Structure・FeatureのIDを相互排他的に検証し、未知Structure参照・二重宣言・role重複・Kind分類の親子巡回などを拒否する。Realizerで検証済み記述体からメモリ内Indexを生成する。Shikumi本体の改変は行わない。
        - ModelFactoryはKindから辿るStructureでModelのrole/shape/順序を検証し、parts()/get()/walk()は維持する。Kind.contractsは廃止し、index.structure_of()/require_structure()で照会する。is_aの意味は以前からの分類問い合わせのままである。
        - 利用側がPythonの言語仕様を知っていることを前提とし、評価順序・Generator状態・コード変換手順などをStructureへ持ち込まない。非同期ASTの受理拡張は今回の作業外とする。
        - テスト99件、Ruff、BasedPyright、Canonical Source文書同期、wheelビルドで検証する。新仕様kind-structure-architecture.mdおよびREADME・STATUS・既存のKind/Model仕様を更新。未公開開発のためCHANGELOGには記さない。"""

        title @= "2026-10-19: Kind・Structure・Featureの正式分離とモデル規約の移行"

    class OCT_19_ASYNC_MODELING:
        """- 採用済みKind・Structure・Feature分離に基づき、非同期構文を独立した組み合わせKindへ増殖させず、`async` Featureで分類する方針を実装した。
        - `AsyncFunctionDef` は通常Function/MethodまたはGeneratorに分類し、`async` Featureを付与する。自身に属するyieldだけを判定し、入れ子定義を誤分類しない。
        - `AsyncFor` はIteration、`AsyncWith` はContextBlockのKindとStructureを再利用し、各Modelに`async` Featureを持たせる。`Await` を新規の式Kind `model.value.await` としてModel化し、既存 `expression_value` Structureを使用する。
        - 4種類の内包表記で節ごとの非同期指定を保持し、ComprehensionClauseのFeatureと既存 `is_async` 情報を一致させて生成する。Awaitは独立したValue式として格納する。内包表記全体の非同期性を推測してFeature伝播させない。
        - Shikumi Featureの適用先にComprehensionClauseを採用し、未知／不適切なFeatureの検証を維持した。既存Structureのrole/shapeと順序、Kindの親子関係・`is_a`の意味を変更しない。
        - Strict/Partial、パッケージ内の同名メンバー照合、クラス内の非同期Generator、構築式の混合反復をテストで確認。Kind 126から127、Structureは51、Featureは1。新しいサンプルとModel出力、非同期仕様書を正本から生成し、README/STATUSを更新。未公開の開発履歴なのでCHANGELOGは更新しない。
        - Pythonのスケジューリングやスコープ・変換方式はMicaに持ち込まない。"""

        title @= "2026-10-19: 非同期構造のModel化とFeatureの実適用"

    class OCT_19_REMAINING_STATEMENTS:
        """- Pythonの文は原則としてModel化する方針を踏まえ、`lambda`（式）、`assert`、`del`、`global`、`nonlocal`（文）を一括して採用した。
        - `lambda` はParameter Modelを通常関数と共有するが、無名関数式でありFunction定義やBlockに変形しない。assertは条件と任意メッセージを保持し、delは既存アクセス・コレクションKindによる順序付き削除対象を保持する。
        - globalとnonlocalは分類上の`scope_declaration`を共有するが、具体Kindを区別し、構造は同じ`declared_names`を参照する。宣言名の列を保持するため、Structureの新しいshape `texts`（文字列タプル）を追加した。Modelのwalkでは非Modelの文字列を再帰探索しない。
        - Pythonの実行時スコープ解決、assertの最適化、削除の副作用、lambdaの呼び出し実装は扱わず、利用側がPythonを知っていることを前提として構成情報を提供する。
        - Kind127→133、Structure51→55、Feature1を確認。新サンプルとStrict/Partial・パッケージの回帰テスト、`remaining-statement-forms.md`、README・STATUS・関連仕様を更新した。旧テストのlambda/assert等の未対応例は別の未対応構文へ移行した。CHANGELOGは未公開開発のため変更しない。"""

        title @= "2026-10-19: 無名関数式・断言・削除・スコープ宣言のModel化"

    class OCT_19_STRUCTURAL_PLACEMENTS:
        """- AST上の値位置のStarred（リスト／タプル／集合）、クラス定義のkeywordsと*付き基底、属性／添字を対象とするAnnAssign、およびクラス内の制御ブロック下にある関数の静的配置をModel化した。
        - 値のStarredExpansionは独立したValue Kindとし、既存StarredTargetとStarredArgumentは分類を維持。共通のexpression_value Structureを再利用する。
        - ClassDefinition Structureへkeywords（順序付き）を追加し、KeywordArgument(name=None)によって**指定を表す。型パラメータや実行時のメタクラス動作は未対応のままとする。
        - 単純Nameの注釈付き定義は従来のVariableとStructureを維持し、複雑なターゲットと括弧付きNameにはAnnotatedAssignment Kind、annotated_target Structureを追加。AnnAssign.simpleを保持する。
        - Method分類はAST上のClass定義領域とし、if/match/iteration/try/withを経由しても維持するが、別関数本文へは伝播しない。追加マーカーは作らず、実行時に定義が実在するとは主張しない。
        - パッケージのOverrideCandidate照合をClass領域内の制御Blockへ拡張。基底クラス名と同名定義を静的に対応付けるだけで、条件成立やMROの意味解析を行わない。
        - Kind 133→135 / Structure 55→56 / Feature 1。123件の回帰テスト、Ruff、BasedPyright、文書同期、wheelの別環境での検証を行う。新仕様書structural-placements.mdとサンプルを追加し、README/STATUS/関連仕様へ反映。開発履歴のためCHANGELOGは変更しない。"""

        title @= "2026-10-19: 値展開・注釈付き代入・クラス内静的配置のModel化"

    class OCT_19_SOURCE_INGESTION:
        """- BOM付きUTF-8とエンコーディング宣言付きソースを、バイト列 `ast.parse(..., type_comments=False)` で解析する方式に移行。文字列APIも `type_comments=False` とし、型コメントの正しさをModel生成の成否に関与させない。通常の注釈構文は引き続きModel化する。
        - パッケージルートは `Path.resolve()` で正規化し、`.`／相対パス／絶対パスで同じモジュール識別名とAST上のオーバーライド候補を得られるよう修正。
        - ルートには引き続き `__init__.py` を要求し、その配下の `__init__.py` のないディレクトリを通常パッケージの対象から除外。Strictは対象モジュールを完全解析し、Partialは除外ディレクトリを `skipped_subtree` として診断し、完全性・照合候補を抑制する。
        - 入力のエンコーディング、型コメント、探索範囲はModelの主題分類とは独立させ、135 Kind / 56 Structure / 1 Featureを変更しない。回帰テストと新仕様書 `source-ingestion.md`、README、STATUS、関連仕様を更新。未公開開発のためCHANGELOGは変更しない。"""

        title @= "2026-10-19: ソース入力・型コメント・パッケージ探索範囲の整理"

    class OCT_19_OVERRIDE_ORDER_AND_RECURSION_BOUNDARY:
        """- 再帰制限はPythonのAST解析とMicaのModel生成・走査に別々の上限があると整理した。Partialの回復保証は未対応構文と構文エラーに関するものであり、`RecursionError` の診断変換や部分回復は保証しない。Builder、walk、等価比較の全面的な非再帰化は行わない。
        - OverrideCandidateの根拠をモジュール全体の名前一覧から、個々のClass定義より前に記述された束縛の追跡へ改めた。後続の同名Classを遡って照合せず、直接importの別名、代入、forターゲット、条件付きブロックなどの再束縛が曖昧な場合は候補を出さない。
        - パッケージ内from-importの明示的な照合、ローカルクラスの同名メソッド照合、条件付きのクラスメンバーの候補保持は継続。対象コードの実行や完全なPythonの名前解決は行わない。
        - 新しいKind・Structure・Featureは追加せず、回帰テスト、パッケージ仕様、Partial仕様、参照照合の仕様を更新。古い実験コード・監査レポート、CHANGELOGは変更しない。"""

        title @= "2026-10-19: 記述順序を踏まえた候補照合と再帰制限の非保証"

    class PRE_PUBLICATION_DOCUMENT_REVIEW:
        """- 公開準備にあたり、**仕様書には現行の仕様、STATUSには現在の状況、開発履歴には過去の判断と経緯**を記す役割分担とした。
        - 月別の開発履歴を初回リリース前の単一記録としてまとめ、設計の方針変更や実験・採否の経緯をここに保存する。
        - 仕様書内の古いAPI、移行時の互換性説明、試験段階の検証記録を公開仕様から外す。公開前の試作記録は履歴へ集約し、現行のKind・Structure・Feature分離契約を正本とする。
        - CHANGELOGには初回公開以降の利用者向けの変更のみを記録するため、公開前の履歴をリセットする。旧CHANGELOGには移すべき利用者向け変更項目はなかった。
        - examplesは開発用の実験・出力記録だったため公開用例としては破棄し、回帰テストに必要な入力だけをtests/fixturesへ移す。
        - Shikumi-devdocのCanonical SourceとMarkdown再生成という管理方式は継続する。"""

        title @= "2026-10-19: 公開に向けた文書とサンプルの整理"

    class PUBLIC_NAME_BOUNDARY:
        """- 開発名 `Mica` を内部実装とShikumi記述体の識別子として維持し、公開名を `shushi` と定めた。
        - 公開Python配布名は `pyproject.toml` の `project.name` を正本とし、`shushi` パッケージから公開APIを提供する。Mica側のモジュール、Kind ID、内部診断コード、既存テストは名称変更に伴って改名しない。
        - README・STATUS・仕様書は外部Contextによって公開名・バージョンを差し込む。開発履歴とCHANGELOGは過去の記録が外部設定で変わらないよう開発名を使用する。
        - `shikumi-devdoc==0.3.5` では外部Context参照とlocalマージを共存させるため、README・STATUS・仕様書のmerge_policyを暫定的に `all` とする。将来のdevdoc改修による `local` 復帰は別作業とする。
        - 公開表示名のみの変更は文書再生成で反映できるが、Pythonの配布名・import名を再変更する際は公開用パッケージの調整が必要である。
        """

        title @= "2026-10-20: 公開名shushiと開発名Micaの役割分担"

    class ENGLISH_PUBLIC_DOCUMENTATION:
        """- 日本語のCanonical Sourceと生成済みCanonical Documentを維持したまま、README・STATUS・CHANGELOG・仕様書・開発履歴の公開Markdownを英語へ差し替えた。
        - 英訳文は`translations/en/`に公開パスを反映して管理し、翻訳ツールを使わずに原文を確認して作成した。公開コピーは正本とはせず、正本に変更があった場合は英訳の再確認を要求する。
        - `scripts/docs.py`で日本語正本を再生成し、英訳と正本ソースのfingerprintを検証して英語版を配備する。正本が変化したままなら公開コピーの更新を拒否する。
        - 公開名・import名・現バージョンは英訳上のプレースホルダーから`pyproject.toml`の情報を差し込み、開発履歴の過去の名称は固定の記録として保持する。
        - `devdocs/`の管理構成やShikumi-devdocのmerge_policyは変更せず、実装ライブラリのAPIも変更しない。"""

        title @= "2026-10-20: 公開文書の英訳と配備の分離"

    class INIT_OPTIONAL_SOURCE_TRAVERSAL:
        """- 公開前の利用者レビューを受け、`__init__.py` がない下位ディレクトリをStrictでは黙って除外する旧方針を廃止した。ルートにも `__init__.py` は要求せず、指定されたローカルソースツリーの全 `.py` を走査する。
        - PEP 420のように `__init__.py` を省く構成も単一ルート内では解析するが、複数のsys.pathエントリにまたがる実際のimport解決や名前空間パッケージの合成は行わない。
        - ディレクトリやソースのsymlinkは拒否し、`a.py` と `a/__init__.py` のモジュール名衝突も例外にする。解析可能なソースが暗黙に欠落しないことを優先した。
        - Strictは見つけた全ファイルの解析を要求し、Partialは構文不正や未対応構文だけを診断する。不要となった `skipped_subtree` 診断カテゴリを廃止し、Kind・Structure・Feature体系は変更しない。仕様書・英訳・回帰テストを更新し、未公開開発のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: `__init__.py` に依存しないソース探索への変更"

    class ITERATIVE_MODELING_FIRST_PHASE:
        """- Python標準ASTの深さ・複雑さの制限はMicaの原理的な制約として受け入れ、回避処理やPartial診断化は行わない方針を決めた。
        - ユーザ報告の3,000項の加算式を再現し、AST構築後のMica内部の再帰処理で停止する問題を修正した。二項演算・単項演算・属性・添字アクセスについて、明示的な処理スタックからModelを組み立てる第一段階の非再帰化を行った。関数自身に属するyieldの検出も反復的なAST走査にした。
        - `Model.walk()` の深さ優先・親優先の宣言順を保ちつつ反復走査に変更。Modelの構造的な等価比較とハッシュ計算も反復的に処理する。
        - 既存のKind・Structure・FeatureとStrict/Partialの契約は変えず、ASTで表現できる深い演算式とアクセス連鎖を回帰テストで確認した。その他のBuilder構文と補助解析は引き続き再帰処理を含み、任意の深さでのModel化は保証しない。
        - 現行仕様・STATUS・公開英訳を更新し、初回公開前の作業としてCHANGELOGは変更しない。"""

        title @= "2026-10-20: 深い演算式とModel操作の非再帰化（第一段階）"

    class ITERATIVE_MODELING_SECOND_PHASE:
        """- AST構築が成功する深い条件式・連続呼び出し・lambdaの連鎖に対し、Model生成時の再帰を除去した。await・yield・starred・sliceも既存の演算・アクセスと同じ反復処理にまとめた。
        - 代入先のTuple/List/Starred、およびmatchのAlias・Sequence・Mapping・Class・Or等のパターンを後行順の明示スタックで組み立てる。既存のKind ID、role、構造、宣言順は維持する。
        - ソースのAST構築制限を回避するものではなく、静的解析の根本的な適用範囲も変更しない。残る文の入れ子、未移行の式、補助解析の再帰処理は次の段階で検討する。
        - Strict/PartialとModel出力の回帰テストを追加し、仕様書・STATUS・英訳を更新。未公開の作業なのでCHANGELOGは変更しない。"""

        title @= "2026-10-20: 条件式・呼び出し・代入先・パターンの非再帰化（第二段階）"

    class ITERATIVE_MODELING_THIRD_PHASE:
        """- `statement()` と `block()` の相互再帰を、ASTの文ブロックを明示スタックで後行順に構築する方式へ変更した。if/elif、for/while、try/except/finally、with、match、関数・クラスを含む深い文の入れ子をModel化できる。
        - Class内のメソッド判定、Kind・Structure・Featureのrole/shape・宣言順は維持する。elif連鎖では個々のelifを余分な独立したBranchとして組み立てないことで重複構築を防ぐ。
        - Partial診断は、親文の構築が成立した時だけ子Block分を公開する。未対応の親文を省略するときは、その内部の子文の診断を漏らさず、Strictでは親の未対応原因を優先する。
        - Python標準ASTの深さ制限は引き続き原理的な制約として扱う。残る式処理と補助解析の再帰処理や `RecursionError` をPartialで診断へ変換しない方針は維持する。
        - 深い文・elif・Strict/Partialの回帰テストを追加し、現行仕様・STATUS・公開英訳を更新した。未公開のためCHANGELOGは更新しない。"""

        title @= "2026-10-20: 文とBlockの反復構築（第三段階）"

    class ITERATIVE_MODELING_FOURTH_PHASE:
        """- AST構築に成功する長い `and` / `or` の交互の論理式を、Builder内の他の深い式と同じ明示的なスタックでModel化するよう修正した。
        - パッケージのオーバーライド候補照合では、クラス内の制御Block下のメソッド探索と、クラス定義前の名前束縛追跡を非再帰化した。Tuple/List/Starredの代入先とmatchパターンの捕捉名判定も反復処理に改めた。
        - AST上の候補と同名束縛の既存契約を維持し、関数・クラスの別スコープには入り込まない。深い論理式・制御文・代入先・パターン・メソッド探索について回帰テストを追加した。
        - Python標準ASTの深さ制限は引き続き原理的な制約として受け入れる。未移行の式処理の再帰依存と、Partialでの `RecursionError` 非診断化は残る。日本語正本・公開英訳とSTATUSを更新し、未公開のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 論理演算とパッケージ照合補助処理の非再帰化（第四段階）"

    class ITERATIVE_MODELING_FIFTH_PHASE:
        """- 対応済みの式Model化を単一の明示的な後行順スタックへ統合した。Tuple/List/Set/Dict、4種類の内包表記、f-stringのJoinedStr/FormattedValue、比較・代入式に残っていた式どうしの再帰呼び出しを廃止した。
        - lambdaの引数既定値・注釈も子式を先に構築する方式へ改め、引数既定値内にlambdaが入れ子になった場合もPythonの関数呼び出しスタックに依存しないようにした。内包表記のターゲットは既存の代入先Model化を引き続き使用する。
        - 既存のKind・Structure・Feature、roleと構成順序、Strict/Partialの結果は変更しない。ASTを直接生成した深いコレクション・内包表記・書式指定・引数既定値・比較式の回帰テストを追加した。
        - Python標準AST自体の深さ制限は回避しない。任意の深さの動作保証や `RecursionError` のPartial診断化は追加せず、STATUS・仕様書と公開英訳を現状に合わせて更新した。未公開開発なのでCHANGELOGには記載しない。"""

        title @= "2026-10-20: 残る式の反復型Model化への統合（第五段階）"

    class PEP695_TYPE_DECLARATIONS:
        """- Python 3.12の `type` 文、関数・クラス・メソッド・Generatorの型パラメータ、3種類の型パラメータと上限・制約をModel化した。Python 3.13の型パラメータ既定値もASTから利用可能な場合に保持する。
        - Shikumiの記述体に型エイリアスと型パラメータのKind 5件・Structure 3件を追加し、既存のCallable/Class Structureに `type_parameters: nodes` を追加した。Feature追加は行わず、140 Kind・59 Structure・1 Featureとした。
        - Python 3.11では標準ASTが新構文を解析できないため独自の文法処理を設けない。型推論や実行時のスコープ解決も行わない。オーバーライド候補照合では型エイリアス名を通常のモジュール束縛として扱い、型パラメータ名は外側の束縛として扱わない。
        - 旧来の「type文が未対応」という回帰テストを現行仕様と切り分け、Partialの未対応構文回復テストは意図的に未採用のASTを模擬して継続した。仕様書・STATUS・日本語正本と英語公開版を更新。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: Python 3.12/3.13の型宣言構文への対応"

    class SELECTABLE_RELATION_ANALYSIS:
        """- `analyses` 引数により静的な継承解析・オーバーライド解析を選択できるよう整理した。`override` には `inheritance` が必要で、空集合なら両方を実行しない。実行済み解析は `PackageModel.analyses` に保持する。
        - 当時は構成Modelとは別に `RelationResult(subject, relation, reference, targets, status, reasons)` を追加した。`resolved` は当時の限定的な静的照合結果であり、実行時の同一性を保証しない。条件付き再束縛やワイルドカードimportには曖昧・未解決の理由を付ける設計とした。これらのstatus型は**後日の再設計で廃止済み**である。
        - 式中の `:=` や制御ブロック内の `from ... import *` の収集漏れを修正し、関数・lambda・クラスを別スコープとして扱った。無関係な変数変更を関係として報告しない。
        - 全Model組み合わせ比較を避け、モジュール内の束縛と基底式を収集した。`override_candidates` は維持し、欠落のあるPartialでは関係解析しない。テスト・仕様・STATUS・英訳を更新し、未公開のためCHANGELOGは変更しなかった。"""

        title @= "2026-10-20: 関係解析の選択実行と束縛の不確実性"

    class PUBLIC_NAME_CHANGE_TO_KANGEN:
        """- 初回公開前の名称調査で公開名 `shushi` がPyPI上ですでに使用されていると判明したため、公開名を `kangen`（換言）へ変更した。ASTに記述された情報を抽象的なModelへ言い換える意味を込めた。
        - `pyproject.toml` の配布名、公開Pythonパッケージとimport、GitHub上の文書参照、PyPI公開設定を更新した。公開名は引き続き配布メタデータを正本として文書へ差し込む。
        - 開発名 `Mica`、内部実装 `src/mica/`、Shikumiの内部識別子、Kind・Structure・Featureと既存の設計契約は維持する。過去の公開名 `shushi` に関する履歴は改変しない。
        - 日本語のCanonical Sourceから文書を再生成し、英訳原稿と公開英語文書を同期した。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 公開名をkangen（換言）へ変更"

    class SHARED_RELATION_FACT_INDEX_FIRST_PHASE:
        """- 開発名Micaのパッケージ関係解析で、モジュール直下のクラスだけを拾うため、条件・クラス・関数・メソッドの内部にある基底クラス参照が無報告になる問題を確認した。Modelの欠落とは区別し、静的事実収集の対象範囲を拡張した。
        - `relation_facts.py` へ宣言位置・束縛・importとスコープの走査を分離し、Kindごとに必要な定義の情報を収集できる内部インデックスを導入した。`relation_analysis.py` に継承・オーバーライドの独立した内部解析器と依存関係を置いた。ModelのKind・Structure・Featureおよび公開APIは変更しない。
        - `if`・`match`・`try`・`with`・関数・クラス・メソッド内のクラスを漏らさず、各明示的基底式に継承解析結果を付与するテストを追加した。スコープを越える書き込みを隔離し、メソッドからクラスローカルを誤参照せず、定義後のstar importで過去の関係を遡って破棄しないようにした。
        - 今回はまず収集経路と内部拡張インターフェースを整備した。間接継承・MRO・再エクスポート、属性・型引数付き基底の解決、候補なしと祖先未解析の区別は次の段階で扱う。実行時の関係を保証しない。日本語正本と英訳を更新し、初回公開前のためCHANGELOGは変更しない。"""

        title @= (
            "2026-10-20: 関係解析の共通静的事実インデックスと解析器の分離（第一段階）"
        )

    class ANCESTOR_RELATION_ANALYSIS_SECOND_PHASE:
        """- 関係解析の共通静的事実インデックスと独立した解析器を引き継ぎ、祖先メソッド探索を第二段階として拡張した。
        - 直接基底に同名のメソッドがない場合も、既知の単一継承チェーンを反復的に遡って最も近い宣言を候補にする。`OverrideCandidate.evidence` で直接基底と間接祖先を区別し、定義元のモジュール情報を保持する。
        - 最後まで探索できて候補がない場合にはオーバーライド関係を `no_match` とする。未知の祖先、多重継承の優先順位など静的に探索を完了できない場合は `unresolved` を維持し、未検査状態も混同しない。`no_match` はランタイムでの非存在保証ではない。
        - 継承グラフの走査は反復処理と探索結果のキャッシュを使用し、ModelのKind・Structure・Featureを変更しない。多重継承MRO、外部参照、動的な基底指定は今後の対象とする。仕様書・STATUS・英訳・回帰テストを更新し、初回公開前なのでCHANGELOGは変更しない。"""

        title @= "2026-10-20: 単一継承の祖先メソッド照合と候補なしの区別（第二段階）"

    class MULTIPLE_BASE_RELATIONS_THIRD_PHASE:
        """- 関係解析の第三段階として、単一継承で最も近い祖先だけを選ぶ規則を廃止し、既知の単一・多重継承グラフで確認できた同名メソッド宣言をすべて候補にした。
        - MROや実行時の優先順位は計算せず、基底式の記述順は既存Class Modelの `bases` に保持する。ダイヤモンド継承で同じ宣言へ到達した場合は重複を取り除き、既存の静的事実インデックスと反復型のキャッシュ付き探索を再利用した。
        - 既知候補と未知の祖先が混在すれば `ambiguous` と理由を返し、確認できた候補は捨てない。対応する静的経路をすべて調べて候補がなければ `no_match` とする。不確定な名前束縛からの候補は `RelationResult.targets` に記録し、確実な束縛経路を要する `override_candidates` には入れない。
        - Kind・Structure・FeatureとModelの構成木、公開APIは変更しない。日本語正本・英訳・STATUS・回帰テストを更新した。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 多重継承を含む静的候補収集（第三段階）"

    class SOURCE_DISCOVERY_AND_EXCLUSIONS:
        """- パッケージ解析で `x.py` というディレクトリをソースファイルとして開こうとする問題と、仮想環境の `lib64` 等のシンボリックリンクで探索が停止する問題を修正した。
        - Strict/Partial共通の探索処理を `os.walk()` による通常ファイルの `.py` の収集へ変更。下位のsymlinkは追跡・解析せず、ルート自体がsymlinkの場合は従来どおり拒否する。探索上のI/Oエラーは隠さない。
        - `parse_package` と `inspect_package` に、ルート相対のリテラルなディレクトリ・ファイルパスを除外する `exclude` 引数を追加した。除外後の解析・識別名衝突検査・関係解析に同じ対象範囲を使う。デフォルトでは明示的な除外をしない。
        - `parse_source` に `filename` を追加し、SyntaxErrorがソース識別子を保持するようにした。Kind・Structure・Featureと関係解析規則は維持する。仕様書・STATUS・英語版・回帰テストを更新し、初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: ソース探索の除外指定とfilename対応"

    class SYNTAX_ERROR_UTF8_COLUMN_NORMALIZATION:
        """- `InspectionIssue.column` はAST由来の診断ではUTF-8バイト単位だが、`SyntaxError.offset` をそのまま引いた構文エラーでは文字単位になっていたため、表現を統一した。
        - `SyntaxError.text` と1始まりの文字位置から0始まりのUTF-8バイト位置へ変換する。位置情報が得られない場合は、不正確な値を推測せずNoneとする。
        - 日本語・絵文字・ASCIIを含む文字列入力、複数行、PEP 263のLatin-1ファイル入力について回帰テストを追加した。Model本体やKind・Structure・Featureは変更せず、日本語仕様書と英語公開版を更新した。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 構文エラー診断のUTF-8バイト列位置への統一"

    class DEEP_MODEL_GENERIC_OPERATIONS_DEFERRED:
        """- 深さ約2,500のModelに対する `repr`・`deepcopy`・`pickle` が標準の再帰制限により `RecursionError` となるというレビュー指摘を確認した。
        - Modelの生成・走査・等価性・ハッシュ等の主機能の非再帰化と、Python標準の任意の汎用操作の深さ無制限対応は別の保証範囲である。初回公開では `repr`・`deepcopy`・`pickle` の極端な深さへの対応を行わず、一般的な利用範囲を超えた非再帰化を保証しないと決定した。
        - `hash` のキャッシュ化も、実利用時の反復コストがボトルネックだと確認されるまでは実装しない。これらの指摘を未対応の既知事項として開発履歴に残し、再レビュー時の判断材料とする。"""

        title @= "2026-10-20: 深いModelに対する汎用操作の対応見送り"

    class PACKAGING_PRE_RELEASE_REFINEMENT:
        """- 初回公開前の整備として、旧Kind/Structure数（126/51）の監査結果 `reports/kind-structure-audit.txt` と、廃止済みAPIを呼ぶ `experiments/audit_kind_contracts.py` を削除した。現行140 Kind/59 Structureの検証は正式なテストで維持する。
        - 未使用の開発依存 `shikumi-contrace` を除外し、実行時のShikumi依存を `>=0.2.4,<2.0.0` に緩和した。将来のShikumi 1.xも許容するが、リリース時にkangenのテストを再実行して互換性を確認する。
        - 内部実装をトップレベル `mica` から `kangen._mica` に移し、配布物に余分なトップレベルimport名が含まれない構成へ変更した。公開API名は `kangen` に統一し、Shikumiの診断コード等の内部識別子と開発名Micaは維持した。
        - 公開CHANGELOGの見出しを中立的な `Changelog` とし、公開前の変更記録は引き続き開発履歴にのみ記載する。日本語Canonical Sourceと英語公開文書を同期し、配布物の内容を検証する。"""

        title @= "2026-10-20: 初回公開前の古い成果物・依存・配布構成の整理"

    class DIRECT_ENGLISH_PUBLIC_DOCUMENTATION:
        """- 英訳本文の二重管理を解消し、`translations/en/` の英語コピーを廃止した。英訳はルートのREADME・STATUS・CHANGELOGと `docs/` の最終公開パスを直接編集・公開する。
        - 日本語のCanonical Sourceと `devdocs/canonical_documents/` の生成済みCanonical Documentは正本管理・翻訳確認のため維持する。Shikumi-devdocのレンダリング処理やnotice運用は変更しない。
        - 翻訳のレビュー状態を検査するソースfingerprintのみ `devdocs/config/translation_manifest.json` へ移した。`scripts/docs.py render` は日本語正本を再生成し、公開先の英語文書とレビュー印を検査するが、英語文書を別ディレクトリから複製しない。
        - 英訳そのものは日本語Canonical Documentを参照して直接公開文書に反映する。自動翻訳を行わず、正本更新時の再確認を要求する。プロジェクト名やバージョンの変更時には公開英語文書も直接更新する。初回公開前なのでCHANGELOGには記録しない。"""

        title @= "2026-10-20: 英語公開文書の中間コピー廃止と直接配備"

    class DEEP_ACCESS_TEST_CPYTHON_PARSER_LIMIT:
        """- Python 3.11のCIで `test_deep_mixed_access_chain` が標準 `ast.parse()` の再帰制限により失敗するという指摘を受け、テストの責務を修正した。
        - 1,500回の属性・添字アクセス連鎖はASTを直接組み立て、MicaのBuilder・walk・等価比較・ハッシュが深いASTを扱えることを検証する。公開 `parse_source` / `inspect_source` の経路は短い同形式の式で別途検証する。
        - Python標準パーサーの制限を超えるソース文字列の解析は保証しない従来方針を維持する。Model・公開API・Kind・Structure・Featureは変更せず、未公開のためCHANGELOGにも記録しない。"""

        title @= (
            "2026-10-20: Python 3.11のAST解析制限を踏まえた深いアクセス連鎖テストの修正"
        )

    class SOURCE_DISTRIBUTION_SELF_CONTAINED_TESTS:
        """- sdistに `tests/test_*.py` のテスト本体だけが含まれ、`tests/fixtures/`・`scripts/` が欠落して、展開後のテストでエラーになるという指摘を確認した。
        - `MANIFEST.in` でテスト入力、文書検証用スクリプト、日本語Canonical Sourceと生成物、公開英語Markdown、Makefileをsdistに同梱する。wheelには開発用ファイルを追加しない。
        - 共通CIにsdist生成・独立ディレクトリへの展開・開発依存のインストール・ `make check` の一連の再現性検証を追加した。ソース配布物からテストと文書検証を実行可能にする。
        - 未使用の `shikumi-contrace` は以前の整理で開発依存から削除済みであることを再確認したため、依存指定の変更は不要だった。Modelと公開APIには変更を加えず、初回公開前のためCHANGELOGは更新しない。"""

        title @= "2026-10-20: sdist単体で再現可能なテスト・文書検証の整備"

    class SCALAR_MODEL_EQUALITY_AND_HASH:
        """- `True` と `1`、`1` と `1.0` はPythonの数値比較では等しいため、Modelのスカラー値を型を見ずに比較すると異なるASTリテラルが同一Modelと判定される問題を修正した。
        - Modelと公開ModelPartの等価性・ハッシュの両方でスカラー値の具体的な型を含める。SourceSpanを含む従来の構造比較、Kind・Structure・Feature、非再帰的なModel操作は維持する。`1` と `0x1` などASTが失う表記情報は復元しない。
        - 型の異なる定数、同一Modelのハッシュ一致、set・辞書キーの分離、直接ModelPart比較、深さ3,000項のModelを回帰テストに追加した。初回公開前の修正のためCHANGELOGは更新しない。"""

        title @= "2026-10-20: スカラー値の型を考慮したModelの等価性とハッシュ"

    class SOURCE_FILENAME_DEFAULT_AND_GENERATOR_ROLES:
        """- 単一ソース解析の `parse_source` と `inspect_source` で `filename` の既定値が異なる問題を修正し、両者を `<source>` に統一した。明示した `filename` は構文エラー・診断の発生元表示にのみ使い、Modelの論理モジュール名 `<source>` とは独立させる。
        - ModelはASTを抽象化するため、ファイルパスから単一ソースのモジュール名を推測しない。Strict/Partialの正常系・構文エラー系に回帰テストを追加した。
        - Generatorの構造契約に実装済みの `type_parameters: nodes` をroles表へ追記した。Kind・Structure・Featureの定義やモデル化処理は変更せず、日本語正本と英語公開文書を同期した。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 単一ソースのfilename既定値統一とGenerator役割表の補完"

    class PUBLIC_TYPED_ROLE_ACCESSORS:
        """- Modelの汎用 `get(role)` は単一ノード、ノード列、テキスト、スカラー等のUnion型を返すため、利用側で繰り返し型検査やcastが必要になるという指摘を採用した。
        - `get_node(role) -> Model`、`get_nodes(role) -> tuple[Model, ...]`、`get_name(role) -> str` を公開し、既存の `get(role)`・`parts()` を維持した。型付きアクセサは値を推論・補完せず、欠損roleはKeyError、実際の値が想定する型と異なる場合（optional値のNoneを含む）はTypeErrorとする。
        - 関係解析の内部 `_node`・`_nodes`・`_name` も公開アクセサへ委譲し、同じ型検査契約を共有する。空タプルは実際の要素型を識別できないため受理する。Kind・Structure・FeatureとModelの実体構造には変更を加えない。
        - 型付きアクセサの正常系・型不一致・未定義role・optional値をテストし、日本語Canonical Sourceと公開英語文書を更新した。初回公開前につきCHANGELOGは変更しない。"""

        title @= "2026-10-20: Modelの公開型付きroleアクセサの追加"

    class EXTERNAL_DECLARATIONS_FIRST_PHASE:
        """- フレームワーク利用者向けのPythonインターフェースと、フレームワークがMicaへ渡すShikumi記述体を分離する設計を採用した。利用者のPythonコードにMicaの宣言属性やデコレーターを要求しない。
        - `kangen.external` に信頼できるPython記述体向けのKind・Structure宣言と `ImportedCall` / `Argument` を用いる照合規則を追加した。Shikumiで内容を検証し、標準KindIndexと衝突なく結合する。元のPythonインターフェースや変換対象コードを実行・importせず、AST上のimport記述と呼び出しから静的に照合する。
        - `parse_source`・`inspect_source`・`parse_package`・`inspect_package` に `definitions` 引数を追加した。importの別名と位置／キーワード引数のrole割り当てを実装。衝突する定義や予約されたimport識別子の再束縛、不明確な引数は黙って受け入れずエラーにする。Partialでは専用の `external_definition` 診断を返す。
        - 初期対象は明示的な最上位importによる呼び出しと、必須の単一node roleのみ。未importの同名式、未定義の動的参照、MRO、外部ライブラリの実行時意味は推測しない。標準の140 Kind／59 Structure／1 Featureを変更せず、未公開なのでCHANGELOGは変更しない。"""

        title @= "2026-10-20: 外部Shikumi記述体とimport呼び出しのModel化（第一段階）"

    class EXTERNAL_EXPRESSIONS_SECOND_PHASE:
        """- 外部Shikumi記述体の第二段階として、明示的にimportされたインターフェースの属性参照 `Memory.NULL` と添字アクセス `Array[int, 128]` を外部Kindへ直接Model化できるようにした。
        - `ImportedAttribute` は空Structure、`ImportedSubscript` は `SubscriptItem(role, position)` で指定された必須node roleを用いる。Kind定義・Structure定義・構文対応付けは引き続き独立した記述とする。対象のPythonインターフェースや変換対象コードは実行しない。
        - モジュール最上位の明示的import、別名import、予約された参照の再束縛禁止、Partialでの専用診断を継承した。添字の要素数不一致・展開・スライスは無理に補完せず拒否する。未登録の式は標準Modelのまま残す。
        - インスタンスの型推論、任意のASTパターン照合、外部ライブラリの意味解釈は追加しない。標準140 Kind・59 Structure・1 Featureは変更せず、公開前につきCHANGELOGは変更しない。"""

        title @= "2026-10-20: 外部属性・添字のModel化（第二段階）"

    class EXTERNAL_CALL_ONLY_ROLLBACK:
        """- 外部属性・添字のModel化を広げた第二段階を再検討し、外部Kindは明示的に登録されたインターフェースの呼び出しだけに限定する方針へ戻した。Pythonの書き味に合わせて個別の構文を特別扱いする機能を増やさず、フレームワーク側が必要な操作を呼び出しAPIとして設計する。
        - `ImportedAttribute`、`ImportedSubscript`、`SubscriptItem` と専用の照合処理・テスト定義を公開APIと実装から削除した。既存の `ImportedCall`、`Argument`、Shikumi定義の独立性、importの別名照合と静的な再束縛検証は維持する。
        - `Memory.NULL` や `Memory[x, y]` は標準の属性参照・添字アクセスModelとして保持し、`Memory.new(Memory.NULL)[index]` では外側の添字と内側の通常属性を標準Model、登録された呼び出しを外部Kindとして組み合わせる。将来のインスタンス型推論や汎用ASTパターン照合は実装しない。公開前につきCHANGELOGは変更しない。"""

        title @= (
            "2026-10-20: 外部構造化をimport済み呼び出しのみに限定（第二段階の撤回）"
        )

    class EXTERNAL_INTERFACE_TYPING_GUIDANCE:
        """- 外部Kindへの置換を登録済みの `ImportedCall` に限定する原則を、フレームワーク開発者向けの変換ガイドに明記した。呼び出しの内側・外側にある属性参照・添字アクセス等は標準Modelとして保持する。
        - MicaはASTを解析するだけなので、Pythonインターフェース自体の実行可能性、戻り値の実行時型や特殊メソッドの実装をModel化の必須条件としない。一方、IDE補完と静的型チェックを支援するため、引数・戻り値、必要なら `__getitem__` 等の型宣言を提供することを推奨する。 `.pyi` スタブも選択肢とする。
        - PythonインターフェースとShikumi記述体の独立性は維持し、追加の照合方式や実行時検証は実装しない。日本語Canonical Sourceと英語公開文書に設計指針を反映し、初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 外部呼び出し構造のガイドとIDE向け型定義の推奨"

    class STATIC_EXTERNAL_MAPPING_AND_BINDING_FIXES:
        """- 外部構造の対応付けを登録時の `target.path` と照合時の `target.dotted` で異なるキーとして扱うと、表記の異なるターゲットが同じ照合キーに衝突し、後から登録された定義で黙って上書きされる問題を修正した。登録と照合の双方で `dotted` を共有し、衝突を定義エラーとする。モジュール・属性境界が違う参照を同一の実体と推測するのではなく、現在の照合能力では識別できないため拒否する。
        - 登録済みインターフェースのimport名とPEP 695の `TypeVar`・`TypeVarTuple`・`ParamSpec` が衝突する場合、外部Kindへの誤変換を避けるため保守的に `ExternalModelingError` とする。Python 3.11では該当ASTノードが存在しないため、ノード種の検出はPythonバージョンに依存せず安全に行う。
        - クラス本体の条件付きブロックにあるメソッド定義を静的な名前束縛として収集し、同名の基底クラスを参照する後続の継承解析を `resolved` と誤判定せず、候補と不確定性を保持する。既存の共通束縛収集を修正し、関係解析器へ個別の例外処理を追加しない。
        - 3つの不具合を失敗する回帰テストで再現して修正した。標準Kind・Structure・Feature、外部構造化を呼び出しに限定する契約、MROを扱わない原則は変更しない。日本語正本と公開英語文書を同期し、初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-20: 外部照合キー衝突・型パラメータの隠蔽・条件付きメソッド束縛の修正"

    class BINDING_EVENTS_REDESIGN_START:
        """- 継承・再束縛解析の実験的な修正が、事実グラフと既存スナップショットを並行稼働させ、重複スコープ解析と性能低下を招いたというレビューを受けた。実験はクローン上で破棄され、従来の開発履歴には含まれていなかったため、この記述は今回の再設計の背景であり現行コードに残った変更を示すものではない。
        - 利用側が欲しい情報を「導入の安定性」「再束縛操作の存在」「削除操作の存在」の3軸に整理した。Featureではなく識別子の束縛情報として提供し、別モジュールからの変更や実行条件は推論しない方針とした。
        - 旧 `_collect_facts` の定義位置ごとの辞書スナップショットを、スコープ別のイベント収集に置換した。参照解決を共通の内部Resolverに切り替え、クラス本体のメンバー抽出も同じイベントから行うことで走査の二重化を抑えた。新しい `BindingState` / `NameBinding` と `PackageModel.name_bindings` / `bindings_for` を追加した。
        - 導入・分岐・代入・`del`・スコープ・import再公開・属性・循環・中間祖先でのメンバー再設定に回帰テストを追加した。これは段階的な改修であり、祖先グラフ処理の完全共通化と外部照合側の束縛検査統合は未完了である。初回公開前につきCHANGELOGは変更しない。"""

        title @= "2026-10-21: 識別子3軸分類と束縛イベント基盤の再設計着手"

    class HIERARCHY_CONSOLIDATION:
        """- 束縛イベント基盤への移行を受け、`relation_analysis.py` に残っていた祖先辺の解釈、反復的な祖先探索、候補の重複除去、候補status判定を `class_hierarchy.py` の共通ClassHierarchy層へ移した。
        - ClassHierarchyは継承辺・クラスメンバー表・メソッド探索結果のキャッシュをまとめて管理する。override解析器では同名メソッド候補の照会と公開関係結果への変換だけを行い、重複したstatus・候補除去ロジックを保持しない。公開関係型を循環importなしで共有するため内部 `relation_types.py` へ整理した。公開APIの型とstatus値は維持する。
        - ダイヤモンド継承での重複回避、既知・未知の祖先の混在、中間クラスの `del` の3件を回帰テストに追加した。旧イベントインデックスの二重構築は追加していない。
        - `external_matching` は構造Modelの構築前にASTのimportを検査するため、既存のModel側束縛インデックスへそのまま切り替えることはできない。第二のAST事実グラフを追加して二重化する失敗を避けるため、ここは未完了として残し、ASTとModelの接続方針を別途検証する。文書は日本語正本から更新し、未公開につきCHANGELOGは変更しない。"""

        title @= "2026-10-21: クラス階層の責務集約と外部照合統合の保留"

    class EXTERNAL_STRUCTURE_VALUE_RESTRICTION:
        """- Phase 4の外部定義の扱いを再検討し、外部構造 `Memory` とその属性連鎖 `Memory.X.Y` 等は**直接呼び出しだけを許す**仕様とした。構造を値として引数・代入右辺・return・注釈・リスト・条件等に渡すこと、構造への代入・削除を拒否する。動的なエイリアス推論・実行可否推論は導入しない。
        - 明示的なモジュールimportからの構造参照も同じルールで扱い、構造に至る名前空間の別名作成も保守的に拒否する。既存の `Memory.NULL` の値使用を正当とする仕様とテストを撤回した。呼び出し結果の添字アクセス等は引き続き通常のModelとなる。
        - AST上の最大属性連鎖を1つの参照として扱い、直接 `Call.func` に置かれた場合のみ構造呼び出しとして受理する。構造の書換え・削除は同じAST走査内のLoad/Store/Delで検出し、代入文に特化した二重検査を削除した。
        - **未完了:** 外部構造の使用制限は共有イベントインデックスへ未統合であり、現行のModel側束縛収集と外部照合のAST走査は別経路のままである。第二のイベントグラフを作らず、統合方針の再設計を必要とする。初回公開前につきCHANGELOGは変更しない。"""

        title @= "2026-10-21: 外部構造の直接呼び出し制限とPhase 4の継続"

    class AST_FIRST_SHARED_BINDING_FACTS:
        """- Phase 4で外部構造の専用照合器を維持する前提を撤回し、Python ASTだけを束縛事実の正本とする設計へ切り替えた。実行時の参照先や値の伝播は推論しない。
        - `ast_facts.py` がスコープ・構文上の導入・再束縛・削除・import・参照文脈を取得する。Model化に成功したAST文にのみModel同一性を付与する小さな対応表を `_Builder` で作り、関係解析が同一の構文事実から束縛イベントを組み立てる。旧Model走査の束縛収集処理は撤去した。
        - 外部構造の保護・呼び出し対応付けは `external_structures.py` が共通AST事実を消費する構文ポリシーとして実装し、旧 `external_matching.py` を削除した。構造の直接呼び出し以外の値使用・構造への書き込みや削除は引き続き拒否する。外部構造がない解析では不要な参照文脈の収集も行わない。
        - 既存の289テストに、条件付きimport、elifの束縛、モジュール境界、外部構造参照を検証する4テストを加え、計293件を確認。10,800件の関係結果を返す暫定ベンチマークでは前版約1.44秒、今回約1.64秒（各3回の中央値）。性能は継続監視し、動的なstar importや型パラメータの境界は今後の確認対象とする。初回公開前のためCHANGELOGは更新しない。"""

        title @= "2026-10-21: AST由来の束縛事実への統合と外部専用照合器の撤去"

    class SYNTAX_ONLY_BINDING_POLICY:
        """- 参照時点の実行時状態を予測するかのような従来の束縛照合を撤回し、構文上に存在する操作だけで導入の安定性、再束縛、削除を区別する方針を確定した。初回の `X = Y` も `may_rebind=True` とし、書き込みがどの分岐・位置にあっても実行可否を推測しない。
        - `_FactIndex.state` の分岐経路両立性検査、`lookup` のパスに応じた状態更新と関数の遅延実行を推測する補正、ASTイベントの不要な分岐経路ID・ヘッダスコープIDを削除した。参照解決はスコープごとの導入候補・変更・削除から確定できる場合だけ照合し、複数候補は確定しない。保守的なソース位置検査は、参照より後にしか定義がない場合の誤確定を防ぐ用途に限定した。
        - 関数引数による遮蔽、関数既定値・match guardの代入式、デコレータの代入をメソッド宣言と取り違える問題を修正した。静的に記述された同一モジュールの属性代入・削除も、書字経路の一致する参照・メンバーについて確定候補を抑止する。動的エイリアス解析や他モジュールからの変更追跡は行わない。
        - 旧仕様の順序依存テストを更新し、構文上の操作の存在と誤った確定結果を回避する回帰テストを追加した。初回公開前のスクラッチであり、互換レイヤーは作らず不要な処理を撤去した。変更は開発履歴にのみ記録し、CHANGELOGは更新しない。"""

        title @= "2026-10-21: 実行経路推測の撤去と構文上の操作だけによる束縛分類"

    class PER_BASE_REFERENCE_CONTRACT:
        """- 公開前のスクラッチとして、継承関係全体に `resolved / ambiguous / unresolved / no_match` の分類を与える旧設計を破棄した。`RelationStatus`、`RelationResult`、`relations` / `relations_for()` と status/reason の統合処理を削除し、互換レイヤーは設けない。
        - `BaseReference(subject, expression, targets, binding, attribute_modified)` を基底式単位の独立した情報として追加した。根の識別子についてモジュール内の3軸をそのまま示し、構文上確認できるクラス候補がある場合はその候補を別に示す。計算式などでは `binding=None` とし、対象不明でも元の基底式は残す。静的な属性書換えは3軸とは独立の操作情報にした。
        - 同名メソッドの `OverrideCandidate` も関係全体の確定判定から切り離し、不安定な継承参照を経由する既知候補も構造的候補として提示する。利用者は個々の基底参照の3軸から自ら採否を判断する。実行順序やMROによる正しさを保証しない。
        - 旧statusに依存した祖先候補の抑止・統合処理と公開テストを更新し、仕様・STATUS・英語公開文書を日本語正本から追随させた。初回公開前のためCHANGELOGは変更しない。"""

        title @= "2026-10-21: 継承全体のstatus廃止と基底式ごとの3軸情報への置換"

    class DOCUMENT_CONTRACT_AUDIT:
        """- 公開前の文書監査として、継承関係の旧statusや移行経緯が現行仕様・STATUSに残っていた記述を整理した。旧APIの撤去経緯は本開発履歴に保持し、現行仕様では `BaseReference` と識別子の3軸だけを説明する。
        - 参照解決仕様の日本語正本に残っていた旧来の「照合／未解決・曖昧」分類と順序依存の説明を、AST上の基底式・候補・束縛事実を独立に提供する現行契約へ置換した。英語公開仕様の実装済み情報も本文へ統合した。
        - Partial仕様のAPI署名に `definitions=` を追記し、実装済みの `external_definition` 診断と不完全パッケージで空になる基底参照・束縛事実・解析一覧を明記した。関連する入力仕様・Model構造仕様を同期し、撤回済みの外部属性・添字APIについては現行仕様から経緯の説明を除いた。
        - 日本語Canonical Sourceから文書を再生成し、英語公開文書をレビューしたうえで翻訳マニフェストを更新する。ソースコード・公開API・初回リリース前のCHANGELOGは変更しない。"""

        title @= "2026-10-21: 現行実装に合わせた仕様・公開文書の棚卸し"

    class TRANSLATION_PARITY_REVIEW:
        """- 日本語Canonical Sourceと英語公開文書を再照合したところ、`extensions.md` のコード識別子の変更と節の統合、`package-modeling.md` の別内容の使用例と英語専用表、STATUSの節順の変更を確認した。英訳を第二の仕様正本として編集していたことが原因であった。
        - 実装に合う情報は日本語Canonical Sourceへ取り込み、`AllocateShape` 等の識別子とPythonコード例を一致させた。英語版の節構造・表・順序を日本語正本に揃え、Partialの除外動作も正しく記述した。英語のみにあった2026-10-20の開発判断も日本語正本の同日位置に追加した。
        - `scripts/docs.py` に見出し・コードブロック・表の軽量な対応検査を追加した。これは意味的な同等性を保証せず、英訳原稿の人的レビューは引き続き必要である。日本語文書を再生成し、公開英訳・翻訳指紋を同期した。ライブラリ本体は変更せず、未公開のためCHANGELOGも変更しない。"""

        title @= "2026-10-21: 日英公開文書の構造・翻訳整合性の再確認"

    class CANONICAL_SOURCES_ONLY_DURING_DEVELOPMENT:
        """- 日本語正本ソース `devdocs/canonical_sources/` のみを開発中の文書管理対象とする方針を採用した。英訳とのずれを避けるため、生成済み日本語Markdownと英語公開Markdownはリポジトリから削除し、開発中は生成・英訳しない。
        - `extensions.py` のPartialで外部構造制約に違反した場合について、`inspect_package` では当該モジュールをModelから除外することを日本語正本に明記した。
        - 文書生成・翻訳整合性チェックスクリプト、翻訳マニフェスト、関連テスト、CIと配布設定から不要な文書生成・検証処理を撤去した。削除確認専用のテストは追加せず、通常のコードテスト・静的検査は維持する。公開前のスクラッチのため互換レイヤーは設けない。"""

        title @= "2026-10-21: 開発中の文書管理を日本語正本ソースに一本化"

    class PACKAGE_EXCLUSION_REMOVED:
        """- リリース前の入力契約を再検討し、`parse_package()` と `inspect_package()` の `exclude` 引数を廃止した。Micaに渡されるソースツリーは利用者が解析目的に合わせて構成し、内部の通常の `.py` はすべて対象とする。`.venv` / `build` などのディレクトリも名前による暗黙の除外をしない。
        - `_excluded_paths` と探索中の除外条件、除外専用のテストを削除した。モジュール識別名の衝突は引き続きエラーであり、除外指定による回避は提供しない。シンボリックリンクの扱い、Strict/Partialの区別、解析種類の選択は維持する。
        - Windows固有の `Path` の区切り文字を原因とする除外指定の問題は、不要になったAPIごと撤去した。互換レイヤーは設けず、現行仕様とSTATUSは日本語Canonical Sourceのみ更新する。生成文書や英語公開文書は開発中に作成しない。"""

        title @= "2026-10-21: パッケージ入力から除外指定を廃止"

    class LEXICAL_SCOPE_BOUNDARIES:
        """- 既知のクラスに対する属性式 `Outer.Inner` の照合が、クラス本体にない `Inner` を外側の同名識別子から補っていた問題を修正した。クラス属性の探索は対象クラスの束縛だけに限定し、存在しない属性から誤った基底・オーバーライド候補を生成しない。継承属性などの実行時探索は追加しない。
        - 外側の条件付きブロック内で宣言された関数・クラスの内部へ、外側の条件フラグが伝播していた問題を修正した。宣言そのものの条件付き判定は維持し、内部の新しい字句スコープでは条件をリセットする。内側の条件分岐と `global` / `nonlocal` のスコープ振り分けは保持する。
        - いずれもAST由来の情報の適用範囲を正す修正であり、実行順序・値伝播の推定や別の束縛収集器を追加していない。回帰テストを追加し、日本語Canonical Sourceのみ更新した。公開用Markdownは生成しない。"""

        title @= "2026-10-21: クラス属性探索と条件付き導入のスコープ境界を修正"

    class REFERENCE_SCOPE_BOUNDARIES_AND_HEADER_FACTS:
        """- 5件の継承候補・束縛情報のレビューを受け、個別の例外処理を増やす代わりに、名前・属性の参照範囲とASTヘッダーからの操作収集の共通規則を修正した。
        - 基底参照候補と `BindingState` が同じ字句スコープ探索を利用するようにし、内側のクラスから外側のクラス名前空間への誤った遡上を撤去した。クラス属性 `Outer.Inner` の局所探索規則は維持する。
        - クラスの基底式には定義中のクラス自身を含めず、同名で再定義されるクラスの先行importや別定義は候補として残した。この限定は参照候補だけに適用し、名前の3軸への再導入記録は変更しない。
        - PEP 695の型パラメータを定義内の字句束縛として共通のイベントに載せ、クラス自身の基底式では型パラメータによる隠蔽を認識する。`__all__` が記述されたモジュールからのstar importは内容を評価せず、暗黙公開規則に基づく候補採用をしない。明示的importには影響しない。
        - ヘッダー内の代入式収集を `ast.expr` だけの列挙からASTの非文ノード全般の走査へ統一し、`metaclass=(A := M)` 等のキーワード値を検出できるようにした。動的属性探索・実行時推論は追加せず、回帰テストと日本語Canonical Sourceのみ更新した。生成文書や英訳は作成しない。"""

        title @= (
            "2026-10-21: スコープ境界・定義中の基底照合・ヘッダーのAST事実収集を共通化"
        )

    class EXPLICIT_DOTTED_IMPORT_PATH:
        """- `import pkg.a` の束縛名 `pkg` だけを残し、ASTに明示された `pkg.a` の完全パスを捨てていたため、`pkg.a.Base` の静的候補が空になっていた問題を修正した。
        - 共通ASTイベントに、エイリアスなしのドット区切りimportの完全パスを記録する。名前の束縛と外部構造の保護判定に用いる既存import情報はそのまま維持し、関係解析側では書かれたパスの各要素だけを順に照合する。別の名前解決器や外部ソース探索は追加しない。
        - `import pkg.a as a` は従来どおり完全なモジュールへの別名導入として扱う。`import pkg` だけで子モジュールを導入したと推測せず、解析対象外のimportは導入の構文的安定性と候補の発見を分けて報告する。回帰テストを追加し、日本語Canonical Sourceのみ更新した。"""

        title @= "2026-10-21: ドット区切りの明示importパスを束縛事実に保持"

    class MODELING_POLICY_CANONICAL:
        """- ASTに基づくモデル化の責務、識別子の3軸、候補照合の保守的な原則、外部構造の拒否規則、レビュー基準を独立した基本方針として正式採用した。
        - `specification/modeling_policy.py` を公開予定の `modeling-policy.md` の日本語Canonical Sourceとして追加し、Model仕様とREADME正本から参照する。既存の具体的な仕様・APIは変更しない。
        - 開発中の文書管理方針に従い、生成済み日本語Markdown・英語公開文書の生成や翻訳、文書整合性チェックは行わない。初回リリース前のためCHANGELOGは変更しない。"""

        title @= "2026-10-21: モデル化基本方針を公開文書の正本ソースへ昇格"

    class EXCEPT_HANDLER_IMPLICIT_DELETION:
        """- `except E as X` と `except* E as X` は、構文仕様上ハンドラ終了時の暗黙の `X` 削除を伴うため、`may_delete=True` とする方針を採用した。明示的な `del` 文だけを対象とする旧説明は置換した。
        - ASTの `ExceptHandler.name` は既に共通の束縛イベント基盤で収集していたため、同じスコープへ削除イベントを追加した。実行順序の推定、後処理のシミュレーション、独立した解析器は導入しない。
        - `except` / `except*`、名前なしハンドラ、関数ローカルと `global` のスコープ境界、基底参照の3軸について回帰テストを追加した。日本語Canonical Sourceのみ更新し、文書生成・英訳は行わない。"""

        title @= "2026-10-21: exceptハンドラ名の暗黙の削除を束縛事実に反映"

    class BARE_ANNOTATION_AND_EXTERNAL_CALL_ALLOWLIST:
        """- 値のない `B: type` は代入ではないため、共通AST事実の書き込みではなく非束縛の注釈宣言として記録する。`BindingState` の生成から除外し、関数内のローカル名としての隠蔽だけを保つ。値付き注釈は書き込みのままとする。
        - 外部宣言構造への直接Callは登録済みの完全パスだけを受け入れる。未登録の属性連鎖は汎用Callへフォールバックせず、`ExternalModelingError`（Partialでは `external_definition`）として拒否する。`__dunder__` 等の個別禁止リストを設けない。
        - 外部記述体の既存 `ImportedCall` / `CallMapping` を許可リストとして用い、公開インターフェースは増やさない。新しい実行時推論や別の束縛解析器も設けない。回帰テストと日本語正本ソースだけを更新する。"""

        title @= "2026-10-21: 値なし注釈の非束縛化と外部構造呼び出しの登録制限"

    class MODELING_POLICY_INDEPENDENT_DOCUMENT:
        """- モデル化基本方針を個別仕様の一部ではなく、仕様・実装・レビューを横断する独立した方針文書として配置し直した。
        - 正本ソースを `devdocs/canonical_sources/specification/modeling_policy.py` から `devdocs/canonical_sources/policy/canonical.py` へ移し、将来の公開先をルートの `MODELING_POLICY.md` に変更した。READMEとModel仕様からの参照も更新した。
        - 文書本文とライブラリの仕様・実装は変更していない。開発中の方針に従い、Markdownの生成・英訳は行わない。"""

        title @= "2026-10-21: モデル化基本方針を仕様書から独立した文書へ移動"

    class SHARED_HEADER_AND_IMPORT_FACT_FIXES:
        """- ASTのヘッダー式収集で、lambdaの位置・キーワード専用既定値と `except` / `except*` の例外型式にある代入式を拾えていなかった問題を修正した。lambda本体や例外ハンドラの文ブロックを外側のヘッダーとして走査せず、共通のイベント収集だけを補正した。
        - 書字位置を推測しない継承候補探索では循環状の辺が発見され得るため、OverrideCandidateの生成時にMethod Model自身との同一性を確認し、自己候補だけを除外する。候補を実行時MROとして確定しない。
        - パッケージ属性と同名サブモジュールの競合判定を束縛3軸・候補探索間で共通化した。直接公開とstar再公開のいずれでも束縛は `unstable` とし、確認できたクラス候補は保持するが、曖昧な根を子属性へ無条件に伝播しない。star importの個々の3軸を合成しない。
        - 外部構造のimport認識で共通ASTイベントの明示importパスを用い、`import framework` だけから未記述の `framework.memory` を補完しないようにした。同一の根を束縛する補完的なドット区切りimportは許可し、異なる同名aliasによる衝突は拒否する。外部宣言APIは増やさず、日本語Canonical Sourceのみ更新した。"""

        title @= "2026-10-21: ヘッダーの書き込み・候補同一性・import判定の共通化"

    class SPECIFICATION_REBUILD:
        """- 説明中心の旧仕様書21モジュールを正本から撤去し、現在の構造を引き継がない新仕様書の作成を開始した。
        - 日本語Canonical Sourceを7領域（Model、解析、値式、文と定義、束縛、関係、外部構造）へ整理した。80の独立した `SPEC_NNN` 規則、`level`、`heading="identity"`、意味的な依存を示す `related` を採用した。
        - 独立したモデル化基本方針、README、開発履歴、ガイドは維持する。旧仕様の設計経緯は本履歴に残し、古い配布ZIPも参照資料として扱う。
        - 今回は初回の再構築であり、公開API各識別子の専用API Reference、全Kindの細かなrole/shape一覧、旧規則との完全な意味的照合は未完了である。未移行の契約は引き続きレビュー対象とする。
        - 生成Markdown、INDEX、英訳は作成しない。ライブラリの実装と公開APIは変更しない。"""

        title @= "2026-10-21: 規則中心の新仕様書へ再構築を開始"

    class SPECIFICATION_REBUILD_PHASE2:
        """- 旧仕様21モジュールと新仕様7モジュールを契約単位で照合し、初回再構築で欠落していたModelの型付き取得失敗契約、構造比較、KindIndex照会、Partial診断のフィールド・位置・省略範囲、Generatorの分類境界、非同期内包節のFeature、分岐構造等を、独立した規則ノードとして追加した。
        - 混在していた抽象Kindの構築制限と記述体の検証、字句スコープの独立性と `global` / `nonlocal` の束縛先宣言は、責務別に規則を分離した。既存の規則IDは改番せず、参照を付与した。
        - 旧仕様に存在した使用例、内部実装手順、将来の未決定事項は現行の規範契約としては移行しない。全Kindのrole/shape一覧と識別子別の専用API Reference、および旧仕様との網羅的な移行照合は引き続き作業対象である。
        - 実装・公開API・独立したモデル化ポリシーは変更せず、日本語Canonical Sourceと仕様構造テストのみ更新する。Markdown、INDEX、英訳は生成しない。"""

        title @= "2026-10-21: 新仕様書の規則単位監査と欠落契約の第2段階移行"

    class SPECIFICATION_REBUILD_PHASE3:
        """- 新仕様の規則と信頼済みKind記述体を照合し、140 Kind・59 Structureのうち59の具体Structureについて、宣言順のrole/shapeと直接参照するKindの対応を独立した `SPEC_NNN` として新しい `layouts.py` に記録した。Structureを直接持たない15の抽象Kindも別規則に列挙した。既存97規則の識別子は維持する。
        - トップレベルの `kangen` 公開シンボルと `kangen.external` の外部宣言用APIを、`API_NNN`・`name`・`kind`・`input`・`output`・`related` を持つ2つのAPI Reference正本に分離した。Modelの型付きアクセサ、KindIndexの構造照会、PackageModelの候補取得など主要な公開メンバーも独立したAPI subjectとした。
        - 仕様表のrole/shape・Kind対応が実装により不意に変わった場合、および公開APIが文書から欠落した場合に検出できる構造テストを追加した。README正本にはAPI Referenceへの導線を追加した。
        - 今回は検証可能な公開面を優先して文書化した。Python ASTの構文対応を網羅する全ての個別Kind規則や旧仕様との意味的な移行監査が完了したという意味ではない。ライブラリ実装・独立ポリシーは変更せず、生成Markdown・INDEX・英訳は作成しない。"""

        title @= "2026-10-21: Structure対応表と公開API Referenceの第3段階整備"

    class SPECIFICATION_REBUILD_PHASE4:
        """- AST構文と具体Kindの対応を検証可能な規範契約へ移行した。既存の `expressions.py` と `statements.py` に29規則・130対応行を追加し、既存157規則のidentityを維持した。1対1の構文だけでなく、AnnAssignのsimple、Function/Method/Generator、TypeAlias・型パラメータ、比較の単独/連鎖、matchパターン、Callの通常/外部構造、ターゲット位置のStarred等の文脈依存も明記した。
        - 各規則は実際に利用するStructureの `LAYOUTS.SPEC_NNN` へ意味的な `related` を張る。130対応の具体Kind実在とStructure参照、および130件のソース例についてStrict解析でKindが一致することを構造テストで確認する。非同期Featureは関数・反復・with・内包節の該当位置だけに付けることを別途検証した。
        - 文書規則を実装の自動翻訳として生成するのではなく、採用するAST対応を規範として独立に定義した。旧仕様との意味的な移行監査と例外条件・制限の最終点検は後続工程とする。ライブラリ実装、公開API、独立したポリシーは変更しない。生成Markdown、INDEX、英訳は作成しない。"""

        title @= "2026-10-21: AST構文とKind/Structure/Feature対応の第4段階照合"

    class SPECIFICATION_REBUILD_PHASE5_AUDIT:
        """- 旧21仕様モジュールを契約・説明・将来構想に分類して新正本との照合を継続した。構文とKind・Structureの表は前段階で移行済みだが、パッケージのモジュール識別規則、関係解析の既定値と依存関係、`NameBinding` の公開取得、引数名の束縛、`__all__`、型パラメータの候補隠蔽、候補の重複除去と循環、属性変更の独立情報については具体的契約が不足していたため規則として追加した。
        - `related` を用いて既存の規則からの依存を明示し、これまでの仕様IDを維持した。旧文書を再追加したり、使用方法や未決定の構想を規範規則へ戻したりしない。
        - 実装の既知の不一致として、モジュール直下の `global` だけで識別子の導入が `unstable` になる問題は依然残っている。これは独立したポリシーおよび `BINDING.SPEC_013` に合致しない。監査中に見つかった実装上の問題を現在の仕様として追認せず、実装修正の対象とする。
        - 今回は監査で裏付けた契約だけを補完し、旧仕様の全条項の意味的移行と実装適合の完了は宣言しない。ライブラリ本体と独立ポリシーは変更せず、Markdown・INDEX・英訳は生成しない。"""

        title @= "2026-10-21: 新仕様の第5段階監査と重要契約の補完"

    class SPECIFICATION_REBUILD_PHASE5_INDEX_BOUNDARIES:
        """- 旧仕様21モジュールとの意味的移行監査を継続し、旧KindIndex仕様とModel構造仕様にあった公開契約のうち、Index照会の失敗条件、Featureの重複・不適用、SourceSpanのバイト位置、検証済みIndexの再利用について規範上の記述不足を確認した。
        - `MODEL.SPEC_017` から `SPEC_020` へ独立した契約として追加し、API Referenceの参照を該当する新規規則へ変更した。既存194規則のidentityは維持し、導入済みの7+1仕様モジュール構成も変えない。
        - 規則の内容は実装の公開APIと既存のテストで裏付け、同じ振る舞いを別仕様に重複定義しない。旧文書の使用例や実装内部の説明、将来構想を規範へ移すことはしない。
        - モジュール直下の `global` による不適切な `unstable` 判定は引き続き未修正の実装不一致とする。実装・独立ポリシー・公開APIは変更せず、生成Markdown・INDEX・英訳も作成しない。"""

        title @= "2026-10-21: 第5段階継続監査でKindIndexと位置情報の契約を補完"

    class SPECIFICATION_REBUILD_PHASE5_PARTIAL_BOUNDARIES:
        """- 旧仕様21モジュールとの追加照合で、Partialパッケージの `name_bindings` の失効条件と、モジュール単位での不完全な結果の保持について、規範契約に記述漏れがあることを確認した。
        - `PARSING.SPEC_017` と `SPEC_018` に、不完全なパッケージでは `package.name_bindings` も空とすること、構文エラー・外部構造制約違反のモジュールを除外しながら他の正常なモジュールを残すことを別々の規則として追加した。既存の `SPEC_007` は、未対応の親文と対応可能な親Blockを混同しない記述へ明確化した。既存198規則のidentityは維持する。
        - 実際の `inspect_package` で構文不正と外部構造違反を再現し、正常ファイルの構造、関係解析、束縛結果の境界を回帰テストに固定した。Model identityに依存する束縛レコードは公開された値と位置で比較し、異なる解析呼び出しのオブジェクト同一性を要求しない。
        - 旧文書の逐次的な使用例、再帰回避の内部実装手順、未決定の将来構想は規範へ移さない。既知のモジュール直下の `global` の実装不一致は引き続き未修正。日本語Canonical Sourceとテストのみ更新し、ライブラリ本体・独立ポリシー・公開APIは変更しない。Markdown、INDEX、英訳は生成しない。"""

        title @= "2026-10-21: 第5段階のPartial解析失効・保持境界を補完"

    class SPECIFICATION_REBUILD_PHASE5_TRACEABILITY:
        """- 旧仕様書21モジュールを話題別に照合し、それぞれの主要契約が新しいSPEC規則に帰属することを追跡する監査表を構造テストへ追加した。これは旧版の散文・使用例・将来構想まで同じ意味で移行したことを保証するものではない。
        - 新仕様200規則のidentity、規範レベル、`related` の参照先・重複・循環、および独立したAPI Reference 57 subjectからの仕様参照をASTとして検査する。規則参照の構造的整合性と実装適合性は別の評価である。
        - 旧モジュールへの現行の文書リンクは見当たらず、旧名への言及は開発経緯を記録する本履歴に限られる。新規の仕様規則を必要以上に増やさず、既存IDを維持した。
        - 実装との既知の不一致（モジュール直下の `global` が `unstable` になる問題）は未解決のまま保持する。第5段階の構造的な追跡性は整備したが、旧仕様の全文章との意味的同等性や未発見の実装不一致がゼロであるとは宣言しない。
        - ライブラリ実装、独立ポリシー、公開APIは変更せず、日本語正本とテストだけを更新する。生成Markdown、INDEX、英訳は作成しない。"""

        title @= "2026-10-21: 旧仕様21領域の追跡表と新仕様参照グラフの監査"

    class SPECIFICATION_REBUILD_PHASE6_EDITORIAL:
        """- 第6段階として200規則と57 API subjectの責務・参照を点検した。AST→Kind対応の詳細規則は対応表を担い、一般規則は値の保持・取得・拒否条件を担うよう、一部の重複した説明を整理した。既存の規則ID・公開API名・対応表の行は変更しない。
        - `Model` の基本取得と型付きアクセサの失敗条件、外部構造の呼び出し許可とMapping結果、不完全パッケージの関係情報と束縛情報の失効など、隣接規則の責務を切り分けた。
        - API Reference 14 subjectについて、汎用的な規則だけでなく `NameBinding` の取得単位、KindIndexの失敗条件、Partialの完全性・失効条件、Modelのwalkなど、実際の公開操作に対応する規則への参照を精密化した。
        - 構造テストでAPIの重要な参照先とAST→Kind対応の `detail` を固定した。Shikumiの正本・参照検証と全テストを通し、生成Markdown・INDEX・英訳は作成しない。
        - 旧仕様の全文章の意味的同等性はこの構造監査によって自動的には証明できず、モジュール直下の `global` による誤った `unstable` 判定も未解決の実装不一致として維持する。今回、ライブラリ本体と独立ポリシーは変更しない。"""

        title @= "2026-10-21: 第6段階の規則責務・API参照の最終構造レビュー"

    class MODELING_POLICY_STRUCTURAL_CERTAINTY:
        """- モデリングポリシーを、識別子の3軸やimport等の個別判定条件を列挙する上位仕様から、他言語変換・制限付きPythonを支える「記述の構造的な確かさ」の判断基準を説明する独立文書へ再構成した。具体的な判定条件は引き続き仕様書に置く。
        - `stable` はPythonの実行結果に影響がないことと同義ではなく、名前の導入が構文上明快かどうかの評価とした。モジュール直下の `global X` は束縛先を変更しないが、同じモジュールの `X` の導入に不要なスコープ宣言が伴うため、従来実装が返していた `unstable` を意図した規範として採用する。宣言だけで架空の束縛や書き込み・削除を生成しない。
        - `BINDING.SPEC_002` と `SPEC_013` を上記の境界に合わせて更新した。従来の本履歴にある「モジュール直下のglobalは未解決の実装不一致」という記述は、当時の判断の記録として残すが、この判断によって置き換える。
        - 構文に直接関係する保守的な評価と、一般的なコード品質・作法の採点は区別する。ライブラリ本体と公開APIは変更せず、日本語Canonical Sourceと回帰テストのみ更新し、公開Markdown・INDEX・英訳は生成しない。"""

        title @= "2026-10-22: 記述の構造的な確かさを中心としたポリシー改訂"

    class EXTERNAL_IMPORT_LOCATION_PROTECTION:
        """- 外部構造の保護が、条件付き・関数・クラス等の内部で宣言されたimportを無視することで外れ、構造属性の値利用や未登録の汎用Callが受理されていた問題を修正した。
        - 共通AST事実の明示importパス・字句スコープ・条件性を用い、登録済み外部構造へ到達可能なimportは、モジュール直下かつ無条件でなければimport文の時点で `ExternalModelingError` とする。条件式や利用有無は評価しない。関連しないimportや単なる親パッケージimportに禁止を波及させない。
        - 登録済みモジュールからのstar importは公開名を確定できず構造保護が成立しないため拒否する。Strict / Partialおよび正常モジュールの保持について回帰テストを追加し、`EXTERNAL.SPEC_010` を制定した。
        - 新たな実行時探索・動的alias追跡・外部宣言APIは追加しない。日本語Canonical Sourceのみ更新し、公開Markdown・INDEX・英訳は生成しない。"""

        title @= "2026-10-22: 外部構造importの不適切な配置を構文上拒否"

    class FORWARD_BASE_REFERENCE_POSITION:
        """- `class D(B)` より後に同じ字句スコープで `class B` が書かれた場合、`B` を静的な基底候補に採用していた問題を修正した。これまでの `SYNTAX_ONLY_BINDING_POLICY` に記録された限定的なソース位置検査の方針を、共通AST事実の `SyntaxDefinition.sequence` と束縛イベントの位置を用いて復元した。
        - 同一スコープの後方導入は `targets` から除外し、そこから派生する `OverrideCandidate` も生成しない。先行importと同名の新クラス定義、自分自身のクラス定義との区別を維持する。後方の再定義・代入も名前全体の `BindingState` には含め、3軸を参照時点の状態へ変更しない。
        - 異なる字句スコープ・別モジュールのコードの実行順序は比較しない。関数の呼び出し時点、分岐の実行可能性、実行時の名前の存在・NameErrorは推測しない。新たな公開ステータス・位置情報の軸は追加しない。
        - `RELATIONS.SPEC_017` を追加し、前方参照、先行importと自己定義、再定義、字句スコープ境界、後方importとstar importを回帰テストに固定した。日本語Canonical Sourceのみ更新し、生成Markdown・INDEX・英訳は作成しない。"""

        title @= "2026-10-22: 基底候補の同一字句スコープ内の後方導入を除外"

    class CONDITIONAL_EXPRESSION_BINDING:
        """- 論理演算の短絡評価、条件式の分岐、内包表記の反復、最適化時に除外される `assert` 内の代入式が `stable` と判定されていた問題を修正した。連鎖比較の後続比較式にも同じ構文上の条件性を適用する。
        - 共通AST事実収集器で式の子要素に条件性を伝播し、既存の `SyntaxEvent.conditional` を用いる。短絡演算の先頭・条件式のテスト・比較の最初の比較式を一律に不安定とはしない。lambdaの既定値と本体の字句スコープ境界も維持する。
        - `BINDING.SPEC_005` の複合文に関する範囲を明確化し、式内部の省略可能な評価位置は独立規則 `BINDING.SPEC_016` に記述した。3軸の型・公開API・独立ポリシーは変更せず、回帰テストと日本語正本ソースのみ更新する。生成Markdown・INDEX・英訳は作成しない。"""

        title @= "2026-10-22: 式内の選択的評価に伴う束縛導入を保守的に判定"

    class NAMESPACE_PACKAGE_EXPLICIT_CHILD_IMPORT:
        """- `__init__.py` を持たない階層で `from . import base`、`from app import base`、`from app.sub import base` から既知の `base.py` に到達できず、基底参照の `targets` が空になる問題を修正した。
        - 共通AST事実に記録された明示importパスの解決で、親パッケージのModule Modelがないことを理由に子モジュールの探索を早期終了しない。明示された子モジュールが実在する場合だけ候補とし、架空の `__init__.py`・親Modelは生成しない。
        - `import app` から未記述の子モジュールを推測しない制約、パッケージ属性と同名の子モジュールの競合判定、束縛3軸と静的候補の分離を維持する。
        - `RELATIONS.SPEC_006` を明確化し、名前空間階層・通常階層・別名・直接import・欠落モジュール・override候補の回帰テストを追加した。公開APIと独立ポリシーは変更せず、公開Markdown・INDEX・英訳は生成しない。"""

        title @= "2026-10-22: __init__.pyのない階層の明示子モジュール参照を修正"

    class CONDITIONAL_IMPORT_TARGET_CANDIDATES:
        """- `try` / `except` や `if` / `else` に書かれた複数の明示importについて、束縛が `unstable` となると参照先候補が空になっていた問題を修正した。同じ字句スコープに記述されたクラス定義と明示importの双方を、共通の束縛イベントから候補として保持する。
        - 条件付き・再導入・書き込み・削除を表す既存の不確定な束縛情報に、探索可能な明示import経路を保持する。参照解決器は各記述経路を既存のimport解決規則で個別にたどり、到達したクラスModelを同一性で重複除去する。条件の値、例外の発生、導入や代入の実行順序、実際に採用される値は判定しない。
        - `BindingState` の3軸、同一スコープの後方導入制限、明示import以外からの子モジュール推測禁止、star import制限、公開APIを維持する。従来の「import後の別書き込みで候補を消す」テストは、候補と再束縛可能性の独立性に合わせて更新した。
        - `RELATIONS.SPEC_018` を追加し、条件付きの複数import、クラス定義との混在、モジュール別名からの属性参照、存在しないimport、循環import、位置制限、オーバーライド候補を回帰テストに固定した。生成Markdown・INDEX・英訳は作成しない。"""

        title @= "2026-10-22: 条件付き明示import経由の基底候補を保持"

    class EXTERNAL_RESERVED_NAME_SPECIFICATION:
        """- 外部構造に無関係なstar importや別スコープの同名束縛まで拒否される理由が、既存の `EXTERNAL.SPEC_010` から読み取りにくいというレビュー指摘を検討した。外部構造照合器が認識済みのimport名をファイル全体で保護し、実行時の公開名やスコープごとの参照先を推測せず誤変換を防ぐ設計であることを確認した。
        - `EXTERNAL.SPEC_010` の「無関係なimportへ拡張しない」は、登録済み外部構造へ到達するimportの位置・無条件性についての制約だと明確化した。登録済みモジュールからのstar importを単独で拒否する条件は維持した。
        - `EXTERNAL.SPEC_011` を追加し、許可済みimportが導入する予約名への再束縛・削除、仮引数・内包表記・型パラメータ等による同名束縛、予約名が存在する場合の無関係なstar importの拒否を規範化した。記述順序・字句スコープ・使用の有無による例外を設けず、許可済みの同根サブモジュールimportは競合とみなさない。
        - ファイル全体での保守的な判定は必要十分な名前衝突解析ではなく、実行時情報を補完しないための意図的な境界として記録した。実装・テスト・公開API・独立したポリシーは変更せず、日本語Canonical Sourceのみ更新した。Markdown、INDEX、英訳は生成しない。"""

        title @= "2026-10-22: 外部構造の予約名保護とstar import拒否の境界を明文化"

    class PUBLIC_API_CONTRACT_ALIGNMENT:
        """- 公開 `Model(...)` の直接構築が内部の `ModelFactory` のshape・抽象Kind・Feature検証を迂回できるとの指摘について、生成禁止やProtocol化は行わず、ライブラリの正規解析APIから得たModelだけを整合性保証の対象とする契約を採用した。利用者が直接構築したModelの妥当性・利用時動作はサポートせず、公開API参照から内部引数 `_parts` を構築入力として扱う説明を除いた。`MODEL.SPEC_005`・`010`・`018` の適用範囲と新規 `MODEL.SPEC_021`、STATUSに反映した。
        - `Feature` を `kangen` の明示公開シンボルへ、`CallMapping` を `kangen.external.__all__` へ追加した。`PackageInspection` に `name_bindings` の読み取りプロパティを追加し、他の4属性とともにAPI Referenceへ記載した。不完全なパッケージで束縛事実を空にする既存挙動は維持する。
        - `OverrideCandidate.evidence` に直接基底と間接祖先の2値を `Literal` として型注釈し、仕様・API Referenceに列挙した。静的候補の意味やMROの非推測は変更しない。
        - 解析ロジック、Modelクラス/ModelFactoryの生成経路、独立したモデリングポリシーは変更しない。日本語Canonical Sourceと回帰テストを更新するが、公開Markdown、INDEX、英訳および正本文書は生成しない。"""

        title @= "2026-10-22: Model保証境界と公開APIの契約整備"

    class PY311_TESTS_AND_TRANSIENT_CANONICAL_DOCUMENTS:
        """- Python 3.11のCIで、PEP 695構文を含む5件のテストにPython 3.12以上のスキップ条件が欠けていた問題を修正した。AST・Kindの網羅テストでは正本の130項目を維持しつつ、3.11では導入前の `ast.TypeAlias`・`ast.TypeVar`・`ast.TypeVarTuple`・`ast.ParamSpec` の4項目を実行対象から除外する。ライブラリの構文解析・公開API・正本仕様は変更しない。
        - 正本文書は `devdocs/canonical_sources/` の日本語正本ソースから必要時に一時生成し、翻訳・確認等の用途を終えたら破棄する方針にした。永続的な `devdocs/canonical_documents/` は作らず、開発中は生成Markdown・英訳・INDEXを作成しない。英訳公開文書を作る際は、一時生成した正本文書を基にレビューして公開成果物へ反映する。
        - `devdocs/generate.py` は出力先省略時にOSの一時ディレクトリを使い、実行失敗時も生成物を削除する。外部の翻訳工程へ中間成果物を渡すときのみ明示的な `-o` を利用し、呼び出し元が破棄する。`canonical_documents/` への明示出力も禁止する。出力先の存在だけで失敗していたテストを削除し、生成フロー自体の動作を検証するテストへ置き換える。
        - sdistには `devdocs` の正本ソース・生成スクリプトを引き続き同梱し、誤って残った `canonical_documents/` だけを `MANIFEST.in` で除外する。独立したモデリングポリシーとライブラリ本体には変更を加えない。"""

        title @= "2026-10-22: Python 3.11テスト互換性と正本文書の一時生成運用"

    class CLOSED_SPEC_ENUMERATIONS_AND_ANALYSES_INPUT:
        """- MUST規則の `など`・`等` を横断点検し、適合判定に使う閉じた集合と、説明上の例示・将来の動的可能性を区別した。`MODEL.SPEC_005` のshapeは7種類、`BINDING.SPEC_005` の複合文は対象AST構文（`try*`を含む）、`STATEMENTS.SPEC_005` のpattern Kindは10種類を、現行の検証器・AST事実収集器・Kind記述体に基づいて明示した。説明のための例示まで有限の集合だとは扱わない。
        - `analyses` に `"override"` 等の単一文字列を渡すと、以前は文字ごとに分解され未知の解析名になり、空文字列は解析なしとして受理されていた。共通の `_selected_analyses` で文字列単体（空文字列を含む）を `TypeError` として拒否し、`parse_package` と `inspect_package` の双方へ適用した。`None`・解析名Iterable・空Iterable・未知の解析名の既存契約は維持した。
        - `PARSING.SPEC_016` と公開API参照に入力型・例外を明記し、Strict / Partialの回帰テストを追加した。公開APIのシグネチャ、解析ロジック、独立したモデリングポリシーは変更しない。日本語正本ソースのみ編集し、正本文書・公開Markdown・INDEX・英訳は生成しない。"""

        title @= "2026-10-22: MUST規則の閉じた列挙とanalyses文字列入力の拒否"

    class README_GUIDE_CONSOLIDATION:
        """- 他言語変換と制限付きPythonの利用ガイドは解析結果の読み取り・利用側の規則適用という共通の流れを扱うため、独立した2本のガイド正本を廃止し、README正本に統合した。旧ガイドへの参照はREADMEから削除した。過去の開発履歴は改変しない。
        - READMEでは、用途と基本概念（Kind・Structure・Feature・Model、束縛3軸、静的な関係候補）、外部構造の登録と専用Model化、短い解析例、Strict/Partialの使い分け、利用上の制約を説明する。詳しい契約はモデル化ポリシー・仕様書・API Referenceへ委ね、READMEを別の規範文書にはしない。
        - Alpha版のため予告なく破壊的な変更があり得ることとMITライセンスを簡潔に記載し、作者情報はライセンスへ委ねる。日本語正本ソースのみ変更し、正本文書・公開Markdown・INDEX・英訳は生成しない。ライブラリ本体・公開API・独立ポリシー・仕様規則は変更しない。"""

        title @= "2026-10-22: 利用ガイド2本のREADME正本への統合"

    class PUBLIC_DOCUMENTATION_DEPLOYMENT_POLICY:
        """- 公開用文書を英語のREADME（ルート）、STATUS・API Reference・DOCUMENTATION_POLICY（docs/以下）に限定する。LICENSEはルートに維持する。その他の仕様・基本方針・履歴は日本語正本ソースのまま `devdocs/` に保持し、全仕様の英訳は行わない。
        - 正本ソースを唯一の編集元とし、日本語正本文書を一時生成・破棄して英訳成果物だけを公開する。`canonical_documents/` の永続保存を再開しない。sdistへの `devdocs` 同梱は維持する。
        - READMEは概要とAPI Referenceへの入口として簡潔に保つ。詳細な公開契約はAPI Referenceに置き、仕様IDと `.py` 正本ソースへの参照を使う。GitHub向け相対リンクとPyPI向けの確定した絶対リンクは、公開先によって区別する。実在が未確認のURLは推測しない。
        - `documentation_policy/canonical.py` を追加し、文書の配備先・翻訳・リンク・配布確認を文書管理ポリシーとして定める。README・STATUSの旧Markdownリンクを整理した。これは文書管理の運用変更であり、ライブラリの解析挙動や公開APIは変更しない。"""

        title @= "2026-10-22: 公開文書の範囲と正本ソース直接参照の運用を確定"

    class PUBLIC_ENGLISH_DOCUMENTS_DEPLOYMENT:
        """- 公開対象のREADME、STATUS、DOCUMENTATION_POLICY、API Reference（公開API 50項目、外部宣言API 14項目）を、各日本語正本ソースから一時レンダリングした文書を照合して英訳・配備する。日本語の中間文書は後続処理の終了後に破棄し、公開英語MarkdownのみをルートREADMEと `docs/` 以下に保存する。
        - API Referenceの仕様参照は `SPEC_XXX` に対応する日本語正本ソースの `.py` ファイルへ置き換え、正本ソースの規則ID（例：`MODEL.SPEC_021`）をリンク名にする。公開しない仕様Markdownへのリンクを残さず、`INDEX.md` は公開API正本の項目と対応付けた索引生成物とする。
        - `README.md` と `docs/` の公開文書をsdistに含める設定と、公開READMEを配布メタデータとして読み込む設定を加える。開発段階の表示はREADMEに合わせAlphaへ揃える。`devdocs/` は従来どおり同梱し、`canonical_documents/` は同梱しない。
        - リポジトリの公開URLは未確定なので推測せず、GitHub上の相対リンクを維持する。PyPIリリース前にはREADMEのリンクを確認済みの絶対URLへ変換する必要があり、公開前検証の残項目として扱う。独立したモデリングポリシー、仕様規則、ライブラリ本体・公開APIは変更しない。"""

        title @= "2026-10-22: 公開英語Markdownの配備とAPI仕様ソース参照"

    class API_REFERENCE_USABILITY_EXAMPLES:
        """- 英語公開文書に `analyses` の許容名と既定動作がなく、外部構造宣言の具体例もないというレビューを受け、API Referenceの利用に必要な契約と最小実行例を補完した。
        - 公開Python API正本に `"inheritance"` と `"override"` の2種、`None` の既定選択、overrideによるinheritanceの自動有効化、空集合でも束縛収集を維持すること、文字列単体と未知名の例外をまとめた。英語公開版も同じ選択表を提供する。
        - 外部定義API正本と英語公開版へ、信頼済みShikumi定義モジュールでStructure・Kind・ImportedCall対応付けを宣言し、別ファイルから `definitions=` へ渡す2ファイル構成の実行例を追加する。解析対象のimport先は実在・実行不要だが、定義モジュールは信頼済みPythonコードであることを明記する。
        - 外部Shikumi記述体はKind・Structureの追加に対応しFeature宣言は未対応である点をREADME正本と英語版に明記した。既存の独立モデリングポリシー・仕様規則・解析実装・公開APIは変更しない。正本文書を永続保存せず、公開英訳と回帰テストで対応を検証する。"""

        title @= "2026-10-22: 公開APIの解析選択肢と外部定義の実行例を整備"

    class REPOSITORY_PUBLICATION_READINESS:
        """- 公開リポジトリの指定URL `https://github.com/minoru-jp/kangen` を配布メタデータのHomepage・Repository・Documentationに記載し、用途が明確なキーワードを追加した。PyPI上に表示するREADMEの内部リンクはすべて、ブランチ名を仮定しない `blob/HEAD/` 形式のGitHub絶対URLへ置き換える。
        - READMEリンクの原典は日本語正本ソースに維持し、公開媒体に応じた絶対URLの変換規則は文書管理ポリシーの正本に明文化した。英語版文書管理ポリシーも同期する。日本語正本文書の保存・公開範囲・独立したモデル化ポリシーは変更しない。
        - CIの既存Python 3.11/3.12/3.13マトリクスとsdist展開後の共通チェックを維持し、pushに加えてpull_requestと手動実行で検証を起動できるようにする。sdist生成物の配布メタデータもTwineで検査する。公開GitHub Actionsの成否は、リポジトリ公開後に別途確認する。"""

        title @= "2026-10-22: 公開リポジトリURL・PyPIリンク・配布メタデータとCIの整備"

    class BOUNDED_MODEL_DIAGNOSTIC_REPR:
        """- 自動生成されたdataclassの `repr(Model)`・`repr(ModelPart)` が深い構成木を再帰的に展開し、比較的浅い構文でも `RecursionError` を起こし、大量のログ文字列を生成していた問題を修正した。
        - 2026-10-20の汎用操作の見送り判断は `deepcopy`・`pickle` に関して維持する。`repr` は日常のデバッグ表示という独立した責務があるため、Kind ID・位置・Feature・直接のroleと値の概要だけを非再帰で表示し、子ModelはKind、タプルは件数だけに省略する。文字列や表示件数に上限を設ける。
        - `MODEL.SPEC_022` を新設し、API Referenceの日英記述を更新した。`repr` を構成データのシリアライズや再構築可能な表現としない。Modelの比較・ハッシュ・アクセサ・走査、解析ロジック、独立ポリシーは変更しない。"""

        title @= "2026-10-22: ModelとModelPartの浅い診断用reprを導入"

    class PYTHON_314_SYNTAX_ADOPTION:
        """- 既存のPython 3.14実行環境での互換性テスト成功を前提に、新構文のModel化を拡張した。t-string用の `ast.TemplateStr` と `ast.Interpolation` をそれぞれ独立したKindへ対応付け、f-stringとは区別する。
        - t-string全体は既存の `string_fragments` Structureを使用し、補間要素には式Model、元の式文字列（None可）、変換指定、書式指定の4 roleを持つ新Structureを定義した。補間や書式は評価せず、式構築の作業スタックを維持する。Python 3.11〜3.13では新ASTノードを参照できなくても解析できるようにする。
        - Python 3.14のPEP 758に基づく括弧なし `except` / `except*` は既存のタプルと例外処理Kindを再利用し、新Kindを設けない。新しい構文の回帰テストとAST対応表に関する検証を追加する。
        - `EXPRESSIONS.SPEC_030`、`LAYOUTS.SPEC_061` と関連仕様・公開STATUS・CI・配布メタデータを更新する。Python 3.11〜3.14対応、142 Kind・60 Structure・1 Featureとする。独立したモデリングポリシーは変更せず、日本語正本文書の永続生成や仕様全体の英訳は行わない。"""

        title @= "2026-10-22: Python 3.14のt-stringと例外構文をModel化"

    class PYTHON_314_VERIFICATION_AND_SPAN_REGRESSION:
        """- 別環境のPython 3.14.6で440件すべてのテストがスキップなしで成功し、Ruff lint・formatとBasedPyrightもエラー・警告なしで通過したという検証結果を確認した。Python 3.11・3.13でも既存テストが成功した（3.11で36件、3.13で3件スキップ）。これは提示された検証報告であり、本作業環境で3.14を再実行した結果ではない。
        - 既存テストとは独立した43ケースで、TemplateStr・InterpolationのASTとModelの要素数、書式・変換指定、Strict/Partial、束縛・継承との統合、例外構文、スパン、不正構文の扱いに問題がないことが報告された。
        - `MODEL.SPEC_019` に、AST由来の構成要素の位置が重複し得ることを追記した。特にt-string/f-stringのデバッグ指定子ではリテラル片と補間要素のスパンが重複しても補正しない。ソース位置と構成要素の並び順を混同しない。
        - t-stringのデバッグ指定子と暗黙のrepr変換、書式指定、t-stringの暗黙連結、不正なプレフィックス混在の拒否、ASTとModelのスパン一致を回帰テストに追加した。Python 3.14専用テストは3.11〜3.13ではスキップする。ライブラリ本体・Kind/Structure・公開API・独立ポリシーは変更しない。正本文書の永続生成や仕様書の英訳は行わない。"""

        title @= "2026-10-22: Python 3.14の実機検証結果とt-string境界条件・スパンの契約を確定"

    class DIAGNOSTIC_CODES_AND_ACCESSOR_STAGE1:
        """- 制限付きPython方言の利用実績に基づき、API改善計画の第1段階として機械可読な診断コードと構造化情報、UTF-8バイト列からUnicode文字列への位置変換、型付きスカラー取得を追加した。
        - `InspectionIssue.code` をメッセージからの文字列推測に依存せず発生箇所で確定し、外部構造違反は `ExternalModelingError` のコードをそのままPartial診断へ渡す。構造化詳細は確実な文字列と整数だけを読み取り専用で保持する。Strictのエラー種別・発生箇所・解析終了条件は変更しない。
        - `Model.get_scalar()` は通常のスカラーを型変換せず取得し、任意の期待型とはPythonの実型を比較する（bool/intを混同しない）。Unicode文字位置変換関数は元のAST由来のバイト位置を変更しない。
        - 正本仕様とAPIリファレンス正本を更新し、公開英語API参照・索引・テストを同期した。第2段階のPartial外部構造エラー回復、外部定義ビルダー、ツリー表示、単一ソース束縛情報は未実装。"""

        title @= "2026-10-22: API改善第1段階の診断コード・列位置・スカラー取得"

    class PARTIAL_EXTERNAL_RECOVERY_STAGE2:
        """- 制限付きPython方言の利用例で、未登録の外部呼び出しが一件あるだけでPartial解析結果のModel全体が失われ、利用側の検査に進めない問題を改善した。
        - 登録済み外部構造への未登録呼び出し・外部構造の値としての参照・CallMappingの引数不整合を局所違反として識別し、所属する文だけを省略して兄弟文・入れ子Blockの対応可能部分を保持する。複数箇所の診断を可能な範囲で収集するが、1文中の網羅性は保証しない。
        - 外部importの位置・別名衝突、予約名の再束縛、star import、保護された参照の書き換えは従来どおりモジュール全体の失敗とし、局所違反より優先する。Strictは従来と同じ例外で即時停止する。不完全パッケージでは関係候補・束縛解析結果を公開しない。
        - PARSING.SPEC_008・012・018を調整し、局所回復とファイル全体の拒否の境界をPARSING.SPEC_022で明文化した。日本語API正本ソース、英語公開API Reference、回帰テストを更新する。独立したモデリングポリシー・Model形状・公開APIシグネチャは変更しない。正本文書の永続生成や仕様全体の英訳は行わない。"""

        title @= "2026-10-22: API改善第2段階の外部構造Partial局所回復"

    class EXTERNAL_DEFINITIONS_BUILDER_STAGE3:
        """- 制限付きPython方言の宣言コストに関するフィードバックを受け、Shikumi定義クラスを多数記述せず、信頼済みPythonデータからKind・Structure・CallMappingを生成する `ExternalDefinitionsBuilder` を公開する。
        - Shikumi記述モジュールの検証結果を組み立てる共通処理を切り出し、ビルダーの `build()` にも同じKindIndex・CallMappingの意味検証を適用する。外部Feature・重複ターゲット・引数role/順序・非nodeの引数等の従来の拒否を維持し、解析対象や登録先のPythonモジュールを実行しない。
        - `add_call()` はKindとMappingを1回で追加し、専用Structure自動生成または共有Structure指定を選べる。既存KindへのMappingだけを追加する場合は `add_mapping()` を提供する。dotlangに相当する11関数でも共有Structureと独立Kindを保持する。
        - `from dot import sin` のような直接関数importは今回実装しない。現行の `ImportedCall` はモジュール名の後にClass.method以上の属性連鎖を要求し、保護対象root・予約名・明示importの扱いがその前提に依存する。追加するなら仕様と安全境界を別途検討し、ビルダーの便宜APIには紛れ込ませない。
        - `EXTERNAL.SPEC_012` と外部API正本・英語公開版・索引・回帰テストを更新する。独立モデル化ポリシーと既存のKind/Structureの意味は変更しない。日本語正本文書を永続生成しない。"""

        title @= "2026-10-22: API改善第3段階の外部定義ビルダーと直接import調査"

    class API_USABILITY_STAGE4:
        """- 制限付きPythonの実装例から得たAPI改善の第4段階として、単一ソースから名前束縛情報を取得する `SourceInspection.name_bindings` と、Model構成木を安全に可視化する `format_model_tree()` を追加する。
        - 束縛情報はパッケージ解析と同一のAST事実収集・字句スコープ索引を再利用する。Module名は `<source>` に固定し、返されたModelの同一性を保持する。SourceInspectionが不完全であれば部分Modelがあっても束縛事実は公開しない。`parse_source()` の戻り値は変更しない。
        - ツリー表示は明示呼び出しの補助APIとして、Kind、role、スカラー概要、span、Featureを反復的に辿る。深さ・ノード数・文字数に制限を持ち、Modelの `repr` や比較・ハッシュ・構成の意味を変更しない。完全なシリアライズには使用しない。
        - `PARSING.SPEC_023` と `MODEL.SPEC_024`、APIリファレンス正本、公開英語API Reference、INDEX、回帰テストを更新する。独立モデリングポリシーや外部定義規則、関係解析の契約は維持する。日本語正本文書や仕様書の英訳は永続生成しない。"""

        title @= "2026-10-22: API改善第4段階の単一ソース束縛とModelツリー表示"

    class PARTIAL_OMISSION_CONTRACT_AND_ARGUMENT_DIAGNOSTICS:
        """- Partial解析で局所違反の文を省略すると、保持した後続Modelの構文自体は正しくても、確定代入等の利用側の判断に必要な先行情報が失われ得る。省略文の書き込みの追跡APIは追加せず、`PARSING.SPEC_022`・API正本・英語公開API Referenceで不完全性の波及を明記した。`name_bindings`非公開とStrictの拒否条件は変更しない。
        - 外部CallMappingの引数違反では、位置引数過多と `*` 展開を `external.too_many_positional` / `external.starred_positional` へ分ける。ソース表記の呼び出し先 `target` を付与し、過多の際は明示された位置引数の `actual_count` と宣言数の `expected_count`、未知のキーワード・引数不整合では問題の `keyword` を返す。`*`・`**` 展開の実行結果は推測しない。
        - `PARSING.SPEC_020` の閉じたコード一覧・局所回復コード集合・日英API Reference・回帰テストを同期する。Model構造、外部構造の予約名保護、解析可能部分の選択、独立したモデリングポリシーは維持する。正本文書や仕様書全体の英訳は作成しない。"""

        title @= "2026-10-22: Partialの省略情報の保証境界と外部引数診断の改善"

    class DEFINITE_ASSIGNMENT_OUT_OF_SCOPE:
        """- 制限付きPython実装者から、3軸の `name_bindings` では読み取り時点の確定代入を判定できず、利用側で独自解析を行ったとのフィードバックを受け、従来から見送っていた確定代入解析の扱いを再検討した。
        - 束縛3軸は字句スコープとAST上の導入・書き込み・削除の性質を示すもので、制御フローを踏まえた確定代入結果ではない。Python一般に対する詳細な意味・データフロー解析をライブラリの責務に加えず、入力の正しさはコード作成者、利用上必要な確定代入検査は各変換器・制限付き言語の規則に委ねる方針を明文化する。
        - 独立した `MODELING_POLICY` に責務境界を追加し、`BINDING.SPEC_001` とAPI Referenceの `BindingState` / `NameBinding` へ3軸の限界を補足した。新しい公開API、診断、確定代入解析や回帰用の解析ロジックは追加しない。正本文書や仕様書全体の英訳は生成しない。"""

        title @= "2026-10-22: 確定代入解析を利用側へ委ねる設計上の境界を明文化"

    class STRUCTURAL_MODEL_EQUALITY_PUBLIC_CONTRACT:
        """- 別ファイルの同形クラスから生成したModelが `==` で等しく、辞書・集合で同じキーになるというレビューを受け、従来から意図した構造的等価性の公開説明を補完した。
        - `MODEL.SPEC_015` はKind、順序付きroleと値、Feature、SourceSpanを比較・ハッシュ対象とするが、SourceSpanにはファイル名・モジュール名を含めない。したがって、異なるファイルのModelも構造と位置が一致すれば等しくなる。個別インスタンスを区別する場合は `is` または生存期間中の `id()` を利用し、構造比較と同一性を混同しない。
        - ハッシュは再帰を避けて毎回構成木を走査し、キャッシュしない。以前のキャッシュ見送り判断を維持し、反復ハッシュが実利用でボトルネックになった場合に再検討する。等価比較・ハッシュの実装や新しい同一性キーAPIは変更しない。
        - `MODEL.SPEC_015`、日本語API Reference正本の `API_006`、英語公開API Referenceを整合させた。独立モデリングポリシー・Modelの挙動は変更せず、正本文書や仕様書全体の英訳は生成しない。"""

        title @= "2026-10-22: Modelの構造的等価性・ハッシュとインスタンス同一性の公開契約を明確化"

    class BINDING_FIRST_INTRODUCTION_REDESIGN:
        """- 束縛3軸の `may_rebind` が通常の初回代入だけでもTrueになることと、単独の `n += 1` が安定導入になることを再検討した。これは初期のclass/import名の保護を汎用の構文イベントへ拡張した際の意味のずれであり、確定代入の推論を導入せずに分類を修正する。
        - 共通のAST事実で通常代入と増分代入を区別し、条件性とは独立に反復し得る書き込みを記録する。最初の独立した通常代入は再束縛に数えず、後続の導入、ループ/内包表記内の反復し得る書き込み、単独の増分代入、star importによる競合を `may_rebind=True` とする。単独の増分代入は独立した安定導入ではないため `unstable` とする。
        - 値評価、実行経路、確定代入の判定は引き続き行わず、候補探索はクラス定義や明示importから既知候補を保持する。特に条件付きimport、後方導入、循環import、外部構造の予約名保護の既存境界を回帰テストで維持する。
        - `BINDING.SPEC_002`・`003`・`005`・`016`、README正本、APIリファレンス日本語正本・英語公開文書、既存回帰テストを更新する。独立モデリングポリシーは変更せず、正本文書は永続生成しない。"""

        title @= "2026-10-22: 初回導入・後続書き込み・反復性の区別による束縛3軸の再設計"

    class PACKAGE_INCLUDE_CALLBACK:
        """- `.venv` を含む入力ツリーで想定外の第三者製Pythonファイルまで解析されるという実利用上の報告を受け、廃止済みのリテラル `exclude` の復活や隠しディレクトリの暗黙的除外ではなく、利用側の `include(path: Path, is_directory: bool) -> bool` に入力選択の責務を委ねる。
        - `parse_package` と `inspect_package` に `include=None` を追加し、省略時は従来どおり全件許可する。指定されたコールバックはルート自体には適用せず、シンボリックリンクを除く下位ディレクトリには下降前、通常の `.py` には読み取り前に適用する。ディレクトリの枝刈りにより子孫の探索・コールバック呼び出しを防ぐ。利用側例外は伝播させる。
        - モジュール名衝突検査・構成木・名前束縛・関係解析は選別後の同じ入力集合で行い、Partialの `complete` は選別した範囲の完全性を表す。除外されたファイルは診断しない。欠落した依存先の静的関係は推測しない。
        - `warnings.catch_warnings()` による警告抑制・診断への変換、パスのglob解釈や除外パターンの正規化は導入しない。`PARSING.SPEC_002`・新設 `PARSING.SPEC_024`、公開API正本、英語公開API Reference、README日英、回帰テストを更新する。正本文書の永続生成や仕様書の全訳は行わない。"""

        title @= "2026-10-22: パッケージ走査対象を利用側コールバックで選別"

    class PACKAGE_SOURCE_EXTENSIONS:
        """- Python構文を用いる制限付き言語・方言の独自拡張子への需要を踏まえ、`parse_package` と `inspect_package` に `extensions: tuple[str, ...] = (".py",)` を追加した。既定動作の `.py` のみは維持し、複数拡張子・単独の独自拡張子を選択可能にする。
        - Path.suffixの大文字小文字を区別した一致を行い、非空の単一拡張子タプルだけを許容する。空指定、glob、複数段の拡張子、重複、パス区切り、非文字列の要素等は明示的に拒否する。拡張子の優先順位を定めず、複数候補が同一モジュール名になる場合は衝突エラーとする。`__init__.dot` も指定対象であれば初期化ファイルと認識する。
        - 既存のincludeコールバックは拡張子を照合した後にファイルの選別を行い、ディレクトリの枝刈り・シンボリックリンク規則は維持する。拡張子は入力発見に限り、PythonのAST解析契約は変えず、独自文法は解析しない。
        - `PARSING.SPEC_002`・`015`・`024` と新設 `025`、公開API正本、日本語README正本、英語公開API Reference・README、回帰テストを更新した。正本文書を永続生成せず、英語の仕様全訳は行わない。"""

        title @= "2026-10-22: パッケージの複数拡張子選択と独自Python方言ソースへの対応"

    class DOCUMENTATION_DRIFT_AUDIT_OCT22:
        """- 連続したAPI改善後の文書ドリフトを日本語正本ソースから点検し、公開中の英語README・STATUS・API Referenceとの対応を確認した。
        - STATUSに残っていたパッケージ解析の「通常の `.py` を全件対象」とする説明を、`extensions` による拡張子選択と `include` による枝刈り・除外がある現在の契約へ更新した。ルート・シンボリックリンク・モジュール名衝突・Partialの選択入力に対する完全性と、独自文法を追加しない点を併記した。
        - 外部構造がShikumi方式のみであるかのようなSTATUS・READMEの記述を修正し、`ExternalDefinitionsBuilder` を同等の定義経路として案内した。STATUSには完全な単一ソースの `name_bindings`、初回導入を区別する束縛3軸、局所エラー時のPartial省略と後続解釈の限界を反映した。
        - STATUSに残っていたPython 3.14検証の「今回の追加回帰テスト」表現を、過去の検証時点の事実として明記し、その後の全追加テストをPython 3.14で実機検証済みとは主張しないようにした。
        - `PARSING.SPEC_015` の見出しから `.py` 固定の含意を除き、API正本のパッケージ解析説明を拡張子選択に合わせた。英語公開API Referenceに紛れ込んだ `API_049` の非正本仕様参照を削除した。
        - 公開APIの規則リンクと日本語正本 `related` の一致、STATUS・READMEの直近API機能の同期を回帰検査する。ライブラリ本体、Model、解析アルゴリズム、公開APIは変更せず、正本文書の永続化や詳細仕様の一括英訳は行わない。"""

        title @= "2026-10-22: 連続したAPI改善後の正本・公開文書ドリフト監査"

    class PUBLIC_API_SIGNATURE_DOCS_AND_MANUAL_TRANSLATION_REVIEW:
        """- 公開APIの引数列挙からキーワード専用区切りの `*` が欠け、文書に従う位置引数呼び出しが失敗するというレビューを受け、実装シグネチャを確認して日本語API正本の `parse_source`・`parse_package`・`inspect_source`・`inspect_package`・`format_model_tree`・`load_external_definitions`・`ExternalDefinitionsBuilder.__init__`・`ExternalModelingError` の宣言を修正した。英語公開API Referenceにも同じ呼び出し契約を反映する。
        - Builderの各メソッドの型注釈、InspectionIssue.detailsの読み取り専用表示を英語版に反映し、ツリー表示と単一ソース束縛の短い使用例、およびBuilderの引数列の制約を日本語正本へ補った。既存の実装とAPI意味は変更しない。
        - 正本と英訳の人手による翻訳・編集に機械的な一致を要求しても意味的な完全性を保証できず、保守負荷に見合わないため、翻訳内容の一致を自動テストで検証する方針を廃止する。直近に追加したリンクID・直近機能の対照テスト、および従来の正本・英語公開API名/結果の対照テストを削除する。正本の一時生成と検証、公開リンクの存在確認、使用例の動作検査、実装のユニットテストは別の検証として維持する。
        - 文書管理ポリシー正本と英語公開版に人手レビューの位置付けを明記する。開発履歴の過去項目は書き換えず、今回の見直しを追記した。日本語生成文書の永続化や詳細仕様全体の英訳は行わない。"""

        title @= "2026-10-22: 公開APIのキーワード専用引数記載と翻訳ドリフトテストの廃止"

    class CALLER_SELECTED_IMPORT_POLICY:
        """- 制限付きPython方言を利用側が設計できるよう、4つの解析APIに `import_policy` の3値（既定の `unrestricted`、`registered_interfaces`、`registered_modules`）と `allowed_modules: tuple[str, ...] = ()` を追加した。互換性のため既定は従来のimport規則を保つ。
        - 登録済み外部構造のルート（`from dot import Fn`）だけを許すモードと、外部定義のモジュールおよび利用者が任意に宣言した絶対モジュール名を丸ごと許すモードを分ける。Python実行環境でのimport解決やライブラリ同一性の推定、標準ライブラリ特例、モジュール内の個別属性の許可リストは実装しない。後者で登録のない呼び出しは通常Callとして残す。
        - 制限モードは記述された絶対モジュール名を完全一致で照合し、相対・star importは拒否する。`allowed_modules` は後者にだけ有効で、空・重複・不正な名前を検証する。禁止されたimportは `external.unregistered_import` でモジュール単位の失敗とし、Strictでは例外、Partialでは診断を返す。既存の外部構造import配置・予約名・保護ルートの使用規則は変更しない。動的importを含む実行の安全性を保証する機能ではない。
        - `EXTERNAL.SPEC_013` と `PARSING.SPEC_001`・`002`・`008`・`020`・`022`、日英のAPI Reference、README・STATUS、回帰テストを更新した。正本と英語版の翻訳一致自動テストは追加せず、正本は必要に応じて一時生成するのみとした。"""

        title @= "2026-10-23: 利用側によるimport許可モードと任意の許可モジュール名"

    class PUBLIC_NAME_CHANGE_TO_SHIKAKE:
        """- 初回公開前の公開名を `kangen` から `shikake`（仕掛）へ変更した。Shikumi（仕組）と対になる名称として、動的・総論的な構造規約と、Python ASTを基礎に静的・各論的な構造規約をモデル化する役割の違いを示す。詳細な実行時意味解析まで引き受けるという意味ではない。
        - PyPI配布名・トップレベルimport名・リポジトリ参照・CI・公開API正本・英語公開文書・README・STATUS・ドキュメント生成コンテキスト・実行例と回帰テストを `shikake` に統一する。旧 `kangen` への互換importは設けない。Shikumi依存、非公開実装名 `_mica`、Kind ID・診断コード・APIシンボル名は変更しない。
        - READMEは「PythonのASTを基礎に、利用者が定めた個別の構造規約に基づいて静的にモデル化する」旨へ改訂する。過去の開発履歴にある旧名称は当時の事実として保持し、日本語正本ソースを変更の起点として英語公開文書へ反映する。正本文書の生成物や仕様全体の英訳は永続化しない。"""

        title @= "2026-10-23: 公開名をshikake（仕掛）へ変更"

    class IMPORT_POLICY_NESTED_ROOTS_FUTURE_AND_NFKC:
        """- 3段以上の外部ターゲット（`pkg:mod.Cls.make` など）で `registered_interfaces` が許可する明示importを、`registered_modules` が拒否する不整合を修正した。構造ルートと宣言モジュールの区別は維持し、`registered_modules` の許可対象を「登録済みモジュールまたは利用側が許可したモジュール」および「登録済み構造ルートの明示import」の和集合とした。`pkg.mod` をサブモジュールと推測したり、その全属性を自動許可したりしない。
        - 制限モードでも単独の `from __future__ import annotations` を許可するが、`__future__` 全体のimportや他のfuture名は特例に含めない。`allowed_modules` の非NFKC名は自動正規化せず拒否し、ASTとの照合に使用する外部 `ImportedCall` ターゲットのモジュール・属性名にも同じ条件を適用した。
        - 同一ソースのimport違反を全件収集する機能は導入しない。最初に検出された違反でソース全体を拒否する現行のStrict・Partial契約を維持する。パッケージ内の相対importも制限モードでは拒否され、絶対importへ書き換えたうえで必要な許可名を利用側が明示することをREADME・API Referenceへ説明した。
        - `EXTERNAL.SPEC_002`・`013`、日本語API正本、README・STATUS正本を先に変更し、英語公開文書へ手作業で反映した。正本と英語版を自動比較するテストは追加せず、実装の回帰テスト・正本の一時生成を維持した。"""

        title @= "2026-10-23: import制限モードの包含関係・future宣言・名前正規化"

    class COMPILER_SYNTAX_VALIDATION_AND_AST_GUARDS:
        """- `ast.parse` が許す一方でCPythonコンパイラが拒否する入力がStrictを通る問題に対して、4つの解析APIへ `syntax_validation: Literal["compile", "ast"] = "compile"` を追加した。既定はAST構築後の `compile(tree, filename, "exec", dont_inherit=True)` で実行を伴わず検証する。意図的な制限付き方言には明示的な `"ast"` モードを残し、既存のコンパイル不可能な入力を使うテストはこのモードを指定して維持した。
        - Strictはコンパイル失敗をSyntaxErrorとし、Partialは `syntax.invalid` でソース単位に省略する。ASTコンパイラ由来の列位置がUTF-8バイト位置であり `SyntaxError.text` がない場合でも取得できるようにした。コンパイルが実行時の成功や安全性を保証するものではなく、CPythonの深さ制約と警告発生は残る。
        - Python 3.15の `Import` / `ImportFrom.is_lazy` と値を省略した `DictComp` は現行Modelで忠実に表せないため、通常構文へ誤って写さず未対応として拒否する。すべての将来AST変更への自動対応を保証するものではない。
        - import制限で最初に報告する違反を幅優先走査順からソースの行・列順に変更し、外部ImportedCallのパス構成要素がPython予約語の場合は宣言時に拒否する。全件違反収集は追加しない。
        - 日本語正本仕様・API正本・README・STATUSを先に更新し、英語公開版へ人手で反映する。翻訳一致テストは追加せず、既存の正本一時生成と実装回帰テストを使用する。Python 3.14・3.15での全件テスト実行は検証環境の範囲でのみ結果を記録する。"""

        title @= "2026-10-23: コンパイル水準の既定検査・Python 3.15 AST未対応形の拒否・import診断順"

    class VERSIONED_AST_MODELING_RULES_313_315:
        """- Python 3.13までのAST→Model対応を基礎規則とし、Python 3.14（t-string）と3.15（PEP 798・lazy import）の差分を内部規則へ切り出した。共通の非再帰エンジン・ModelFactory・Strict/Partial診断は維持し、新規ASTノードだけでなく既存ノードの新形も差分規則が先に扱う。規則を選ぶ公開APIやModel上のバージョンラベルは追加しない。
        - PEP 798のリスト・集合・generatorは既存の内包表記Kindとstarred_expansionを保持する。辞書の`DictComp.value=None`は新Kind `model.value.comprehension.dict.unpacking` と新Structure `value_comprehension_dict_unpacking`（mapping、clauses）で表現し、既存の辞書内包表記契約は変更しない。lazy importは引き続き未対応として拒否する。
        - 正本仕様 `PARSING.SPEC_027`・`028`、`EXPRESSIONS.SPEC_031`、`LAYOUTS.SPEC_062` に記録し、英語公開STATUS・API Referenceへ人手で反映する。正本と英語版の意味的一致をテストで検査しない従来方針を維持する。Python 3.15の構文を古いPythonで解析する独自パーサーは導入しない。"""

        title @= (
            "2026-10-23: 3.13基礎と3.14/3.15差分の内部Model化規則、およびPEP 798対応"
        )

    class RELEASE_PREPARATION_001_CI_AND_CHANGELOG:
        """- 初回公開に向けてv0.0.1の機能範囲がまとまったため、既存のCHANGELOG正本の `Unreleased` という準備用記述を廃止し、`0.0.1` の公開直前の利用者向け変更履歴として整理する。英語 `CHANGELOG.md` は日本語正本の一時生成物から人手で翻訳・配備する。PyPIやGitHub Releaseの完了を示すものではない。
        - Python 3.15.0が正式リリースされたため、CIマトリクスに3.15を加え、`allow-prereleases` は指定しない。既存のPython 3.11〜3.14は維持する。
        - レビュー環境のPython 3.14.6と3.15.0b4で548件のテストスイートが成功したとの報告をSTATUSに出所付きで記録し、3.13.5の開発環境で確認した539成功・9スキップと区別する。3.15.0正式版のCI結果まで確認したと主張しない。今後も検証結果はバージョン・報告環境を明示して更新する。
        - API Referenceの古い未検証表現を更新し、詳細なテスト実績はSTATUSに集約する。READMEと文書管理ポリシーをCHANGELOG公開へ対応させ、sdistに含める。正本・英訳の記述一致を自動テストで保証する方式は復活させない。"""

        title @= "2026-10-23: v0.0.1公開直前準備、Python 3.15 CI追加、検証実績とCHANGELOGの公開"

    class V001_RELEASE_DOCUMENTATION_AND_ACTIONS:
        """- v0.0.1はまだ配布サービスへ公開していないが、配布物として完成したCHANGELOGとSTATUSに公開準備の進捗説明が紛れ込まないよう、2026-10-23付の通常の初回リリース記述に改めた。バージョン `0.0.1` は変更しない。過去の開発履歴は当時の意思決定記録として保持する。
        - 日本語CHANGELOG・STATUS・文書管理ポリシー正本を先に変更し、英語のCHANGELOG・STATUS・DOCUMENTATION_POLICY・API Referenceへ人手で反映した。Python 3.15.1での548件のテストスイート成功はレビュー環境からの報告として記録し、CI実行と混同しない。報告にないスキップ数は記載しない。
        - GitHub Actionsのcheckout・setup-python・artifact操作をNode.js 24対応の現行版へ移行し、公開Partial解析モジュールのdocstringから `Development-only` を削除した。ライブラリの解析仕様・Model・API挙動は変更しない。正本英訳の自動内容一致テストは追加しない。"""

        title @= "2026-10-23: v0.0.1配布文書・Python 3.15.1実績・GitHub Actionsを整理"

    class EXPLICIT_LAZY_IMPORT_AS_FEATURE_V001:
        """- v0.0.1公開直前の見直しで、Python 3.15の明示的なlazy importを拒絶する従来判断を改めた。旧判断の履歴は残す。`ast.Import` / `ast.ImportFrom.is_lazy` はASTが持つ構文事実であり、通常importと同じKind・Structureを維持し、文Modelの `lazy` Featureとして公開する。個々のaliasにはFeatureを付与しない。
        - `lazy` Featureはソース中に明示されたキーワードだけを示す。`__lazy_modules__` や実行環境設定による暗黙の遅延化は表現しない。実行時のロード順序・副作用・import成功の判定は提供しない。束縛3軸および静的参照候補、既存のimport制限規則は同じAST上の対象・名前を用い、lazy指定だけでは変更しない。ModelはFeatureを含むため通常importとは構造的に等価ではない。
        - 構文は対象のPythonパーサーに依存し、旧Python向けの独自構文解析を追加しない。3.15 ASTフラグを旧Pythonで模擬した回帰テスト、3.15実構文の条件付き統合テストを整備し、正本 `MODEL.SPEC_006` と `PARSING.SPEC_027`、v0.0.1の公開文書に反映する。"""

        title @= "2026-10-23: Python 3.15の明示的lazy importをFeatureとして採用"

    class RELEASE_WORKFLOW_MANUAL_DISPATCH_AFTER_PYPI:
        """- 従来の `.github/workflows/release.yml` はGitHub Releaseの `published` イベントを起点としており、PyPI公開の前にGitHub Releaseを作る必要があった。v0.0.1初回公開前に、pushは検証、正式公開はGitHub Actionsからの手動実行、と責務を分ける方針へ変更した。既存のPython 3.11〜3.15検証とsdist展開検証は維持する。
        - 新しい公開ワークフローは `workflow_dispatch` 専用で、デフォルトブランチ・配布バージョン・既存タグを事前検査し、検証→ビルド→PyPI Trusted Publishing→タグ作成→GitHub Releaseの順に実行する。PyPIのOIDC権限は公開ジョブに限定し、GitHubリポジトリへの書込権限は公開後のタグ・Release作成ジョブだけに与える。公開済みの配布物はGitHub Releaseにも添付する。
        - 公開後にタグ/Release作成が失敗した際は、同じワークフローの失敗ジョブだけ再実行する。既存タグが同じコミットを指していれば再利用し、異なるコミットなら停止する。公開済みバージョンのPyPIへの無条件再アップロードや、タグ・Release作成を公開成功より前へ移すフォールバックは設けない。なお外部サービスでの初回実動作は公開後に確認する。
        - リリース実行手順は日本語STATUS正本と英語公開STATUSに反映する。これはv0.0.1の配布運用変更であり、ライブラリの公開API・Model化の仕様やリリース内容のCHANGELOGは変更しない。"""

        title @= "2026-10-23: PyPI公開成功後にGitタグとGitHub Releaseを作る手動公開CI"
