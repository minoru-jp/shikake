"""shikake公開APIの正本参照。"""

from shikumi_devdoc.fields.api_reference import (
    OPERATION,
    TYPE,
    VALUE,
    detail,
    input,
    kind,
    name,
    output,
    related,
)
from shikumi_devdoc.norms.common import canonical_source, summary

from devdocs.canonical_sources.specification.binding import BINDING
from devdocs.canonical_sources.specification.external import EXTERNAL
from devdocs.canonical_sources.specification.model import MODEL
from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.relations import RELATIONS


@summary("shikake公開Python APIの名前・種別・入力・結果・関連仕様。")
@canonical_source(
    "{{project.name}}: Python API Reference",
    filename="public.md",
    order=10,
    merge_policy="all",
    heading="identity",
)
class PUBLIC_API:
    """トップレベル公開APIと、主要なModel・Index・解析結果のメンバー。

    **関係解析の選択（`analyses`）**

    `parse_package()` と `inspect_package()` の `analyses` には、解析名
    `"inheritance"`（基底参照候補）と `"override"`（同名メソッド候補）を
    **文字列のIterable**として指定できます。`None`（省略時）は両方を有効にします。
    `"override"` を選択すると、依存する `"inheritance"` も自動的に有効になります。

    | 指定例 | 有効になる関係解析 |
    | --- | --- |
    | `None`（省略時） | `inheritance`, `override` |
    | `{"inheritance"}` | `inheritance` |
    | `{"override"}` | `inheritance`, `override` |
    | `{"inheritance", "override"}` | `inheritance`, `override` |
    | `set()` | なし |

    **パッケージ入力の拡張子と選別（`extensions`・`include`）**

    `parse_package()` と `inspect_package()` の `extensions=(".py",)` は対象の単一拡張子を
    タプルで指定します。`(".dot",)` なら独自拡張子だけ、`(".py", ".dot")` なら両方を
    解析します。大文字小文字は区別し、同じモジュール名への衝突は拒否します。
    `__init__.dot` も指定された拡張子なら初期化ファイルです。ファイルの中身は常に
    Python ASTとして解釈されます。詳しくは `PARSING.SPEC_025` を参照してください。

    任意の `include(path: Path, is_directory: bool) -> bool`
    を受け付けます。`False` を返したディレクトリへは下降せず、`False` を返した指定拡張子の
    ファイルは読み取りません。渡す `Path` は入力ルートから得た絶対パスで、`is_directory`
    はディレクトリで `True`、一致するファイルで `False` です。ルート自身は対象から外せません。
    `None`（省略時）は全件許可であり、`.venv` などをshikakeが自動除外しません。
    コールバック例外は伝播し、選別で除外されたファイルはPartial診断ではありません。
    `complete` は選別後の入力集合に対する完全性です。除外パターンの照合・警告抑制は
    利用側に委ねます。詳細は `PARSING.SPEC_024` を参照してください。

    **利用側のimport許可規則（`import_policy`・`allowed_modules`）**

    4つの解析APIで `import_policy="unrestricted"`（既定）・
    `"registered_interfaces"`（登録済み構造ルートの明示的from importだけ）・
    `"registered_modules"`（登録済み外部モジュール名と利用側が `allowed_modules` に指定した
    モジュール名の合計と、登録済みinterfaceの明示import）の3モードを選べます。
    `registered_interfaces` の許可対象は `registered_modules` に包含され、
    例えば `pkg:mod.Cls.make` の `from pkg.mod import Cls` は両方で許可しますが、
    `from pkg.mod import helper` は `pkg.mod` 自体を許可していない限り通りません。
    両制限モードで `from __future__ import annotations` の単独宣言を許可します。
    `allowed_modules` は `tuple[str, ...] = ()`、非空指定は `registered_modules` のみです。
    モジュール名はNFKC正規化済みの絶対名を完全一致で比較し、非正規化名は拒否します。実行時の解決、実在確認、
    標準ライブラリの特例扱いは行いません。制限モードで相対・star importを禁止します（パッケージ内の相対importも例外ではなく、絶対importへの書換えと許可名の指定が必要です）。
    違反はファイル全体の外部構造診断 `external.unregistered_import` となり、全違反の列挙は保証しません。
    許可した通常のモジュール呼び出しは、登録されていない限り通常Callです。
    この機能はPython実行時の安全性を保証するサンドボックスではありません。
    詳しくは `EXTERNAL.SPEC_013` を参照してください。

    **Python 3.14のt-string**

    Python 3.14の `t"..."` は `model.value.template_string` として表現され、
    補間箇所は `model.structural_part.template_interpolation` になります。
    補間には `value`、`expression_text`（ASTの文字列表現、None可）、
    `conversion`、`format_spec` が保持されます。f-stringのKindとは別です。
    詳細は `EXPRESSIONS.SPEC_030` と `LAYOUTS.SPEC_061` を参照してください。

    空のIterableは関係解析のみを無効にし、`name_bindings` の収集は維持します。
    文字列単体（例：`"override"` または `""`）は `TypeError`、未知の解析名は
    `ValueError` になります。不完全なPartial結果を完全な関係情報として扱わないでください。"""

    class API_001:
        "一つのPythonソース文字列をStrictにModel化する。"

        name @= "shikake.parse_source"
        kind @= OPERATION
        related @= (
            PARSING.SPEC_001,
            PARSING.SPEC_026,
            PARSING.SPEC_027,
            EXTERNAL.SPEC_013,
        )
        input @= "source: str"
        input @= "*"
        input @= 'filename: str = "<source>"'
        input @= "index: KindIndex | None = None"
        input @= "definitions: ModuleType | ExternalDefinitions | None = None"
        input @= 'import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted"'
        input @= "allowed_modules: tuple[str, ...] = ()"
        input @= 'syntax_validation: Literal["compile", "ast"] = "compile"'
        detail @= "import_policyは既定ではunrestricted。registered_interfacesは登録済みinterfaceの明示的importだけ、registered_modulesは登録済み外部モジュールとallowed_modulesで指定した任意の絶対名を許可する。追加の通常importを登録済み外部構造としてModel化しない。制限モードで相対・star importは拒否する（futureのannotations単独宣言のみ例外）。登録済みinterfaceの明示importはregistered_modulesでも通り、allowed_modulesの非NFKC名は拒否する。禁止されたimportはファイル全体のexternal.unregistered_importとなり全件収集は保証しない。実行時の同一性・存在・安全性は保証しない。"
        output @= "Model"
        detail @= "未対応構文・外部宣言の違反は例外として返す。"
        detail @= "syntax_validationは既定でcompile水準の検証を実行し、CPythonでコンパイルできないASTをSyntaxError（Partialではsyntax.invalid）として扱う。ast指定では追加のコンパイル検証だけを省き、未対応構文は引き続き拒否する。解析対象コードは実行しない。"

    class API_002:
        "指定ディレクトリ以下で拡張子とincludeで選別した通常のPython構文ファイルをStrictにモデル化する。"

        name @= "shikake.parse_package"
        kind @= OPERATION
        related @= (
            PARSING.SPEC_002,
            PARSING.SPEC_015,
            PARSING.SPEC_016,
            PARSING.SPEC_024,
            PARSING.SPEC_025,
            PARSING.SPEC_026,
            PARSING.SPEC_027,
            EXTERNAL.SPEC_013,
        )
        input @= "directory: str | Path"
        input @= "*"
        input @= "index: KindIndex | None = None"
        input @= "analyses: Iterable[str] | None = None"
        input @= "definitions: ModuleType | ExternalDefinitions | None = None"
        input @= "include: Callable[[Path, bool], bool] | None = None"
        input @= 'extensions: tuple[str, ...] = (".py",)'
        input @= 'import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted"'
        input @= "allowed_modules: tuple[str, ...] = ()"
        input @= 'syntax_validation: Literal["compile", "ast"] = "compile"'
        detail @= "import_policyは既定ではunrestricted。registered_interfacesは登録済みinterfaceの明示的importだけ、registered_modulesは登録済み外部モジュールとallowed_modulesで指定した任意の絶対名を許可する。追加の通常importを登録済み外部構造としてModel化しない。制限モードで相対・star importは拒否する（futureのannotations単独宣言のみ例外）。登録済みinterfaceの明示importはregistered_modulesでも通り、allowed_modulesの非NFKC名は拒否する。禁止されたimportはファイル全体のexternal.unregistered_importとなり全件収集は保証しない。実行時の同一性・存在・安全性は保証しない。"
        output @= "PackageModel"
        detail @= "analysesはNoneまたは解析名Iterable。文字列単体（空文字列を含む）はTypeError、未知の解析名はValueError。extensionsの既定値は('.py',)で、指定拡張子だけを対象とする。includeでは下位ディレクトリと対象ファイルを利用側が選別し、省略時は全件許可。ルートは選別対象外で、選別後のモジュール名衝突・Strict解析の失敗は例外となる。"
        detail @= "syntax_validationは既定でcompile水準の検証を実行し、CPythonでコンパイルできないASTをSyntaxError（Partialではsyntax.invalid）として扱う。ast指定では追加のコンパイル検証だけを省き、未対応構文は引き続き拒否する。解析対象コードは実行しない。"

    class API_003:
        "単一ソースをPartial解析し、Modelと診断を返す。"

        name @= "shikake.inspect_source"
        kind @= OPERATION
        related @= (
            PARSING.SPEC_006,
            PARSING.SPEC_013,
            PARSING.SPEC_022,
            PARSING.SPEC_026,
            PARSING.SPEC_027,
            EXTERNAL.SPEC_013,
        )
        input @= "source: str"
        input @= "*"
        input @= 'filename: str = "<source>"'
        input @= "index: KindIndex | None = None"
        input @= "definitions: ModuleType | ExternalDefinitions | None = None"
        input @= 'import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted"'
        input @= "allowed_modules: tuple[str, ...] = ()"
        input @= 'syntax_validation: Literal["compile", "ast"] = "compile"'
        detail @= "import_policyは既定ではunrestricted。registered_interfacesは登録済みinterfaceの明示的importだけ、registered_modulesは登録済み外部モジュールとallowed_modulesで指定した任意の絶対名を許可する。追加の通常importを登録済み外部構造としてModel化しない。制限モードで相対・star importは拒否する（futureのannotations単独宣言のみ例外）。登録済みinterfaceの明示importはregistered_modulesでも通り、allowed_modulesの非NFKC名は拒否する。禁止されたimportはファイル全体のexternal.unregistered_importとなり全件収集は保証しない。実行時の同一性・存在・安全性は保証しない。"
        output @= "SourceInspection"
        detail @= "未対応構文と局所的な外部構造違反は、違反を含む文を省略して診断し、対応できる兄弟文を保持する。予約名の再束縛などファイル全体の外部構造違反や構文エラーではmodel=Noneとなる。不完全なModelは検査済みの完全な入力として扱わない。省略された文によって後続Modelの解釈に必要な構文・束縛情報が失われる可能性があり、保持したModelから代入の不在等を推定しない。"
        detail @= "syntax_validationは既定でcompile水準の検証を実行し、CPythonでコンパイルできないASTをSyntaxError（Partialではsyntax.invalid）として扱う。ast指定では追加のコンパイル検証だけを省き、未対応構文は引き続き拒否する。解析対象コードは実行しない。"

    class API_004:
        "パッケージをPartial解析し、不完全性と診断を返す。"

        name @= "shikake.inspect_package"
        kind @= OPERATION
        related @= (
            PARSING.SPEC_006,
            PARSING.SPEC_016,
            PARSING.SPEC_017,
            PARSING.SPEC_018,
            PARSING.SPEC_022,
            PARSING.SPEC_024,
            PARSING.SPEC_025,
            PARSING.SPEC_026,
            PARSING.SPEC_027,
            EXTERNAL.SPEC_013,
        )
        input @= "directory: str | Path"
        input @= "*"
        input @= "index: KindIndex | None = None"
        input @= "analyses: Iterable[str] | None = None"
        input @= "definitions: ModuleType | ExternalDefinitions | None = None"
        input @= "include: Callable[[Path, bool], bool] | None = None"
        input @= 'extensions: tuple[str, ...] = (".py",)'
        input @= 'import_policy: Literal["unrestricted", "registered_interfaces", "registered_modules"] = "unrestricted"'
        input @= "allowed_modules: tuple[str, ...] = ()"
        input @= 'syntax_validation: Literal["compile", "ast"] = "compile"'
        detail @= "import_policyは既定ではunrestricted。registered_interfacesは登録済みinterfaceの明示的importだけ、registered_modulesは登録済み外部モジュールとallowed_modulesで指定した任意の絶対名を許可する。追加の通常importを登録済み外部構造としてModel化しない。制限モードで相対・star importは拒否する（futureのannotations単独宣言のみ例外）。登録済みinterfaceの明示importはregistered_modulesでも通り、allowed_modulesの非NFKC名は拒否する。禁止されたimportはファイル全体のexternal.unregistered_importとなり全件収集は保証しない。実行時の同一性・存在・安全性は保証しない。"
        output @= "PackageInspection"
        detail @= "analysesはNoneまたは解析名Iterable。文字列単体（空文字列を含む）はTypeError、未知の解析名はValueError。extensionsで指定した拡張子の候補だけをincludeで選別してPartial解析し、除外したファイルを診断に含めない。completeは選別後の入力に対する完全性であり、不完全なパッケージで関係解析結果を断定しない。"
        detail @= "syntax_validationは既定でcompile水準の検証を実行し、CPythonでコンパイルできないASTをSyntaxError（Partialではsyntax.invalid）として扱う。ast指定では追加のコンパイル検証だけを省き、未対応構文は引き続き拒否する。解析対象コードは実行しない。"

    class API_005:
        "信頼済みのKind・Structure・Feature定義を表すIndexを得る。"

        name @= "shikake.kind_index"
        kind @= OPERATION
        related @= (MODEL.SPEC_020,)
        output @= "KindIndex"
        detail @= "同一プロセスでキャッシュされる。"

    class API_006:
        "一つの構文要素の分類、role別の構成要素、位置、Featureを保持する。"

        name @= "shikake.Model"
        kind @= TYPE
        related @= (MODEL.SPEC_001, MODEL.SPEC_015, MODEL.SPEC_021, MODEL.SPEC_022)
        output @= "Model"
        detail @= "解析APIの結果を読むための公開型。kind・span・featuresとparts()等を取得できる。利用者による直接構築はサポートせず、コンストラクタの内部引数は公開契約に含めない。Modelの等価性・ハッシュはKind・順序付き構成要素・Feature・SourceSpanに基づく構造的なもので、ファイル同一性を含まない。別ファイルの同形Modelも辞書や集合では同じキーになり得るため、個々のインスタンスの識別にはisまたは生存期間中のid()を使う。ハッシュはModelインスタンスごとに初回計算してキャッシュする。再度の呼び出しではキャッシュ値を返し、初回計算中は既にキャッシュ済みの子Modelの値を再利用し、未計算の子孫Modelにも計算結果をキャッシュする。reprは浅い・長さ制限付きの診断表示であり、構成木の完全表示ではない。"

    class API_007:
        "構成要素のroleと値を組にした不変データ型。"

        name @= "shikake.ModelPart"
        kind @= TYPE
        related @= (MODEL.SPEC_005, MODEL.SPEC_022)
        input @= "role: str"
        input @= "value: PartValue"
        output @= "ModelPart"
        detail @= "valueはModel、Model列、文字列列またはScalar。reprは非再帰の省略付き診断表示であり、完全な構成表現ではない。"

    class API_008:
        "Python ASTに由来する開始・終了行列位置。"

        name @= "shikake.SourceSpan"
        kind @= TYPE
        related @= (MODEL.SPEC_019,)
        input @= "line: int"
        input @= "column: int"
        input @= "end_line: int"
        input @= "end_column: int"
        output @= "SourceSpan"
        detail @= "行は1始まり、列はUTF-8バイト単位の0始まり。"

    class API_009:
        "Kind ID、直接親、直接参照するStructure IDを保持する。"

        name @= "shikake.Kind"
        kind @= TYPE
        related @= (MODEL.SPEC_003,)
        input @= "id: str"
        input @= "parent_id: str | None"
        input @= "structure_id: str | None = None"
        output @= "Kind"
        detail @= "Kind分類とrole/shapeの継承は独立。"

    class API_010:
        "StructureのIDと順序付きrole/shape契約を保持する。"

        name @= "shikake.Structure"
        kind @= TYPE
        related @= (MODEL.SPEC_004,)
        input @= "id: str"
        input @= "parts: tuple[PartContract, ...]"
        output @= "Structure"
        detail @= "partはroleとshapeを持つ。"

    class API_011:
        "Kind分類、Structure、Featureの検証済み一覧と照会を提供する。"

        name @= "shikake.KindIndex"
        kind @= TYPE
        related @= (MODEL.SPEC_016, MODEL.SPEC_017)
        input @= "kinds: tuple[Kind, ...]"
        input @= "structures: tuple[Structure, ...] = ()"
        input @= "features: tuple[Feature, ...] = ()"
        output @= "KindIndex"
        detail @= "Kindの分類祖先と構成roleを混同しない。"

    class API_012:
        "パッケージの構成木と、選択した静的関係情報を提供する。"

        name @= "shikake.PackageModel"
        kind @= TYPE
        related @= (RELATIONS.SPEC_003, RELATIONS.SPEC_019)
        input @= "model: Model"
        input @= "override_candidates: tuple[OverrideCandidate, ...] = ()"
        input @= "base_references: tuple[BaseReference, ...] = ()"
        input @= "analyses: frozenset[str] = frozenset()"
        input @= "name_bindings: tuple[NameBinding, ...] = ()"
        output @= "PackageModel"
        detail @= "構成木と関係候補は別の情報。reprは構成Model・解析の概要と関係タプルの件数だけを示す長さ制限付き診断表示であり、各関係を展開しない。完全な内容は属性・問い合わせAPIから取得し、reprからの復元は保証しない。"

    class API_013:
        "クラスに記述された一つの基底式と、静的候補・束縛3軸を保持する。"

        name @= "shikake.BaseReference"
        kind @= TYPE
        related @= (RELATIONS.SPEC_002,)
        input @= "subject: Model"
        input @= "expression: Model"
        input @= "targets: tuple[Model, ...]"
        input @= "binding: BindingState | None"
        input @= "attribute_modified: bool = False"
        output @= "BaseReference"
        detail @= "候補の発見は実行時の継承関係を確定しない。"
        detail @= '根の識別子が標準組み込み名で、内側の可視スコープに同名の束縛がない場合、bindingはモジュールでの組み込み名の3軸となる。例えば同名の書き込みがない `class AppError(Exception)` では `BindingState("builtin", False, False)` となる。'

    class API_014:
        "同名定義の可能なオーバーライド関係と根拠を保持する。"

        name @= "shikake.OverrideCandidate"
        kind @= TYPE
        related @= (RELATIONS.SPEC_012,)
        input @= "method: Model"
        input @= "base_method: Model"
        input @= "derived_class: Model"
        input @= "base_class: Model"
        input @= "derived_module: str"
        input @= "base_module: str"
        input @= 'evidence: Literal["direct_base_and_same_method_name", "ancestor_and_same_method_name"] = "direct_base_and_same_method_name"'
        output @= "OverrideCandidate"
        detail @= "直接基底と間接祖先の同名定義の2区分を示す。実行時MROは計算しない。"

    class API_015:
        "識別子の最初の構文上の導入・再束縛し得る追加/反復書き込み・削除を独立した3軸として示す。"

        name @= "shikake.BindingState"
        kind @= TYPE
        related @= (
            BINDING.SPEC_001,
            BINDING.SPEC_002,
            BINDING.SPEC_003,
            BINDING.SPEC_004,
        )
        input @= 'introduction: Literal["stable", "unstable", "builtin"]'
        input @= "may_rebind: bool"
        input @= "may_delete: bool"
        output @= "BindingState"
        detail @= "組み込み名はモジュールの暗黙の初期導入として `(builtin, False, False)` から始まり、当該名へのモジュール書き込みがあれば `may_rebind=True`。通常名の `x = 1` の単独代入は `(stable, False, False)`、`x = 1; x = 2` は `(stable, True, False)`、単独の `n += 1` は `(unstable, True, False)`。条件付きの単独代入は導入のみ `unstable` になり得る。ループ内の書き込みは反復し得る。操作が実際に実行されるか・読み取り時点の確定代入は保証せず、必要なら利用側の言語規則・変換条件に基づいて別途検査する。"

    class API_016:
        "指定モジュールと字句スコープに属する名前の3軸を記録する。"

        name @= "shikake.NameBinding"
        kind @= TYPE
        related @= (BINDING.SPEC_014,)
        input @= "module: str"
        input @= "scope: Model"
        input @= "name: str"
        input @= "state: BindingState"
        input @= 'scope_kind: Literal["module", "class", "function", "annotation"] | None = None'
        output @= "NameBinding"
        detail @= "同名でもスコープを混同しない。PEP 695の型パラメータ用annotationと定義のfunction/classは、同じscope Modelを共有し得るためscope_kindで区別する。同じModelを対象としたbindings_for()は双方を返し得る。ライブラリ生成レコードのscope_kindは必ず設定され、利用者が手動作成して省略した場合はNone。stateの3軸は確定代入の結果ではない。"

    class API_017:
        "単一ソースのModelまたは診断を持つPartial結果。"

        name @= "shikake.SourceInspection"
        kind @= TYPE
        related @= (
            PARSING.SPEC_006,
            PARSING.SPEC_022,
            PARSING.SPEC_023,
            PARSING.SPEC_029,
        )
        input @= "model: Model | None"
        input @= "issues: tuple[InspectionIssue, ...]"
        input @= "name_bindings: tuple[NameBinding, ...] = ()"
        output @= "SourceInspection"
        detail @= "completeはmodelの有無と診断の両方に従う。局所外部構造違反ではmodelを部分的に返せるが、構文エラー・ファイル全体の外部違反ではNoneとなる。完全な場合にのみ字句スコープ別のname_bindingsを返し、不完全なら空。reprはmodelの概要とname_bindingsの件数を表示し、束縛要素を展開しない。issuesは診断内容を全件表示し、reprによるデータの復元は保証しない。"

    class API_018:
        "パッケージ解析のPartial結果。"

        name @= "shikake.PackageInspection"
        kind @= TYPE
        related @= (
            PARSING.SPEC_009,
            PARSING.SPEC_017,
            PARSING.SPEC_018,
            PARSING.SPEC_019,
            PARSING.SPEC_029,
        )
        input @= "package: PackageModel"
        input @= "issues: tuple[InspectionIssue, ...]"
        output @= "PackageInspection"
        detail @= "packageのほか同名の結果プロパティも提供する。不完全なら関係候補・解析済み一覧・名前束縛を空とする。reprではpackageの関係要素は省略され、issuesは診断内容を全件表示する。"

    class API_019:
        "Partial解析での失敗種別・位置・省略範囲を記録する。"

        name @= "shikake.InspectionIssue"
        kind @= TYPE
        input @= "category: IssueCategory"
        input @= "filename: str"
        input @= "node_type: str"
        input @= "message: str"
        input @= "line: int | None"
        input @= "column: int | None"
        input @= "skipped_node_type: str | None = None"
        input @= "skipped_span: SourceSpan | None = None"
        input @= 'code: str = "diagnostic.unspecified"'
        input @= "details: Mapping[str, str | int] = {} (read-only)"
        output @= "InspectionIssue"
        related @= (PARSING.SPEC_011, PARSING.SPEC_020)
        detail @= "codeは機械可読な安定識別子、messageは人間向けの説明。detailsは読み取り専用。主なコードはsyntax.invalid、syntax.unsupported、external.unregistered_call等。全コードはPARSING.SPEC_020を参照。局所外部違反でもskipped_node_typeとskipped_spanで実際に省略した文を示す。省略は保持された後続Modelの解釈にも影響し得る。外部構造の引数診断ではtargetは記述上の呼び出し先、too_many_positionalはexpected_countとactual_count、starred_positionalでは推測した引数数を返さず、unknown_keywordとargument_mismatchはkeywordを含める。"

    class API_020:
        "Strict解析で扱えないAST構文を示す例外。"

        name @= "shikake.UnsupportedSyntaxError"
        kind @= TYPE
        related @= (PARSING.SPEC_005,)
        input @= "node: ast.AST"
        input @= "detail: str | None = None"
        output @= "UnsupportedSyntaxError"
        detail @= "未対応構文の記録はPartialではInspectionIssueに変換される。"

    class API_021:
        "Strict解析で外部構造の使用規則に違反したことを示す例外。"

        name @= "shikake.ExternalModelingError"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_008,)
        input @= "message: str"
        input @= "node: ast.AST"
        input @= "*"
        input @= 'code: str = "external.definition_error"'
        input @= "details: Mapping[str, str | int] | None = None"
        output @= "ExternalModelingError"
        detail @= "Partialではexternal_definition診断となり、コードと判明している詳細を引き継ぐ。"

    class API_022:
        "宣言順のrole/値の一覧。"

        name @= "shikake.Model.parts"
        kind @= OPERATION
        related @= (MODEL.SPEC_007,)
        output @= "tuple[ModelPart, ...]"

    class API_023:
        "roleに対応する値。未定義roleはKeyError。"

        name @= "shikake.Model.get"
        kind @= OPERATION
        related @= (MODEL.SPEC_007,)
        input @= "role: str"
        output @= "PartValue"

    class API_024:
        "node取得。欠落やshape不一致ではKeyErrorまたはTypeError。"

        name @= "shikake.Model.get_node"
        kind @= OPERATION
        related @= (MODEL.SPEC_014,)
        input @= "role: str"
        output @= "Model"

    class API_025:
        "nodes取得。欠落やshape不一致ではKeyErrorまたはTypeError。"

        name @= "shikake.Model.get_nodes"
        kind @= OPERATION
        related @= (MODEL.SPEC_014,)
        input @= "role: str"
        output @= "tuple[Model, ...]"

    class API_026:
        "text取得。欠落やshape不一致ではKeyErrorまたはTypeError。"

        name @= "shikake.Model.get_name"
        kind @= OPERATION
        related @= (MODEL.SPEC_014,)
        input @= "role: str"
        output @= "str"

    class API_027:
        "構成木を自己から深さ優先で走査。"

        name @= "shikake.Model.walk"
        kind @= OPERATION
        related @= (MODEL.SPEC_008,)
        output @= "Iterator[Model]"

    class API_028:
        "指定IDのKind。存在しないIDはKeyError。"

        name @= "shikake.KindIndex.get"
        kind @= OPERATION
        related @= (MODEL.SPEC_017,)
        input @= "kind_id: str"
        output @= "Kind"

    class API_029:
        "分類木の直接親。"

        name @= "shikake.KindIndex.parent"
        kind @= OPERATION
        related @= (MODEL.SPEC_017,)
        input @= "kind_id: str"
        output @= "Kind | None"

    class API_030:
        "分類上の祖先関係。Structure継承ではない。"

        name @= "shikake.KindIndex.is_a"
        kind @= OPERATION
        related @= (MODEL.SPEC_003,)
        input @= "kind_id: str, ancestor_id: str"
        output @= "bool"

    class API_031:
        "Kindが直接参照するStructure。親KindのStructureを推測しない。"

        name @= "shikake.KindIndex.structure_of"
        kind @= OPERATION
        related @= (MODEL.SPEC_016, MODEL.SPEC_017)
        input @= "kind_id: str"
        output @= "Structure | None"

    class API_032:
        "Structureのない抽象KindはValueError。"

        name @= "shikake.KindIndex.require_structure"
        kind @= OPERATION
        related @= (MODEL.SPEC_017,)
        input @= "kind_id: str"
        output @= "Structure"

    class API_033:
        "IDに対応するStructure。"

        name @= "shikake.KindIndex.get_structure"
        kind @= OPERATION
        related @= (MODEL.SPEC_017,)
        input @= "structure_id: str"
        output @= "Structure"

    class API_034:
        "登録済みKind全体。"

        name @= "shikake.KindIndex.all_kinds"
        kind @= OPERATION
        related @= (MODEL.SPEC_016,)
        output @= "tuple[Kind, ...]"

    class API_035:
        "登録済みStructure全体。"

        name @= "shikake.KindIndex.all_structures"
        kind @= OPERATION
        related @= (MODEL.SPEC_016,)
        output @= "tuple[Structure, ...]"

    class API_036:
        "登録済みFeature全体。"

        name @= "shikake.KindIndex.all_features"
        kind @= OPERATION
        related @= (MODEL.SPEC_016,)
        output @= "tuple[Feature, ...]"

    class API_037:
        "指定Kindに付与したFeatureの妥当性を検証する。"

        name @= "shikake.KindIndex.validate_features"
        kind @= OPERATION
        related @= (MODEL.SPEC_018,)
        input @= "kind_id: str, features: tuple[str, ...]"
        output @= "None"

    class API_038:
        "指定Modelの字句スコープだけを検索。"

        name @= "shikake.PackageModel.bindings_for"
        kind @= OPERATION
        related @= (BINDING.SPEC_014, BINDING.SPEC_017)
        input @= "scope: Model, name: str"
        output @= "tuple[NameBinding, ...]"
        detail @= "scopeはNameBinding.scopeと同一オブジェクトでなければ一致しない。同じModelへ所属する注釈スコープ・定義本体スコープの束縛が複数返る場合はscope_kindで区別する。明示された束縛は元の列挙順で返す。組み込み名の場合、パッケージ内のモジュールModelであれば未列挙でも必要時に暗黙導入を返す。ほかの未一致は空タプル。構造的に等しい別Modelは一致させない。"

    class API_039:
        "同一クラスの書かれた基底式を順に返す。"

        name @= "shikake.PackageModel.bases_for"
        kind @= OPERATION
        related @= (RELATIONS.SPEC_003,)
        input @= "class_model: Model"
        output @= "tuple[BaseReference, ...]"
        detail @= "BaseReference.subjectと同じModelインスタンスを起点として照会する。同形の別Modelは含めず、元の関係タプルにおける順序を維持し、該当なしでは空タプルを返す。"

    class API_040:
        "同一Method Modelを起点とする候補。"

        name @= "shikake.PackageModel.overrides_for"
        kind @= OPERATION
        related @= (RELATIONS.SPEC_003,)
        input @= "method: Model"
        output @= "tuple[OverrideCandidate, ...]"
        detail @= "OverrideCandidate.methodと同じModelインスタンスを起点として照会する。同形の別Modelは含めず、元の関係タプルにおける順序を維持し、該当なしでは空タプルを返す。"

    class API_041:
        "PackageModelの構成木だけを走査。"

        name @= "shikake.PackageModel.walk"
        kind @= OPERATION
        related @= (MODEL.SPEC_008, RELATIONS.SPEC_003)
        output @= "Iterator[Model]"

    class API_042:
        "Modelが存在し診断が空であるときTrue。"

        name @= "shikake.SourceInspection.complete"
        kind @= VALUE
        related @= (PARSING.SPEC_013,)
        output @= "bool"

    class API_043:
        "診断が空であるときTrue。"

        name @= "shikake.PackageInspection.complete"
        kind @= VALUE
        related @= (PARSING.SPEC_013, PARSING.SPEC_017)
        output @= "bool"

    class API_044:
        "構成木だけを走査。"

        name @= "shikake.PackageInspection.walk"
        kind @= OPERATION
        related @= (PARSING.SPEC_006,)
        output @= "Iterator[Model]"

    class API_045:
        "Kind分類と独立した横断的なFeature定義。"

        name @= "shikake.Feature"
        kind @= TYPE
        related @= (MODEL.SPEC_006, MODEL.SPEC_018)
        input @= "id: str"
        input @= "allowed_kind_ids: tuple[str, ...]"
        output @= "Feature"
        detail @= "KindIndex.all_features() から得られる不変の定義。標準Featureは `async` と、Python 3.15の明示的lazy importを表す `lazy`。`lazy` はimport文の `model.import.direct` / `model.import.from` にだけ付与し、aliasには付与しない。実行時の遅延を判定するものではない。"

    class API_046:
        "Partialパッケージの構成木。"

        name @= "shikake.PackageInspection.model"
        kind @= VALUE
        related @= (PARSING.SPEC_019,)
        output @= "Model"
        detail @= "package.model と同一のModel。"

    class API_047:
        "Partialパッケージで確認できた同名メソッド候補。"

        name @= "shikake.PackageInspection.override_candidates"
        kind @= VALUE
        related @= (PARSING.SPEC_009, PARSING.SPEC_019)
        output @= "tuple[OverrideCandidate, ...]"
        detail @= "package.override_candidates と同じ。不完全な解析では空。"

    class API_048:
        "Partialパッケージで確認できた基底参照。"

        name @= "shikake.PackageInspection.base_references"
        kind @= VALUE
        related @= (PARSING.SPEC_009, PARSING.SPEC_019)
        output @= "tuple[BaseReference, ...]"
        detail @= "package.base_references と同じ。不完全な解析では空。"

    class API_049:
        "Partialパッケージで完了した関係解析の種類。"

        name @= "shikake.PackageInspection.analyses"
        kind @= VALUE
        related @= (PARSING.SPEC_016, PARSING.SPEC_019)
        output @= "frozenset[str]"
        detail @= "package.analyses と同じ。不完全な解析では空集合。"

    class API_050:
        "Partialパッケージの字句スコープ単位の名前束縛事実。"

        name @= "shikake.PackageInspection.name_bindings"
        kind @= VALUE
        related @= (PARSING.SPEC_017, PARSING.SPEC_019)
        output @= "tuple[NameBinding, ...]"
        detail @= "package.name_bindings と同じ。不完全な解析では空。"

    class API_051:
        "スカラーroleを型変換せず取得し、指定型と厳密に照合する。"

        name @= "shikake.Model.get_scalar"
        kind @= OPERATION
        related @= (MODEL.SPEC_023,)
        input @= "role: str"
        input @= "expected_type: type[T] | None = None"
        output @= "Scalar | T"
        detail @= "未定義roleはKeyError、非スカラーまたは型の不一致はTypeError。boolはintとは一致しない。NoneとEllipsisは取得可能。"

    class API_052:
        "ASTのUTF-8バイト列位置をUnicodeコードポイント列位置に変換する。"

        name @= "shikake.utf8_byte_column_to_character_column"
        kind @= OPERATION
        related @= (PARSING.SPEC_021,)
        input @= "line: str"
        input @= "column: int"
        output @= "int"
        detail @= "位置はいずれも0始まり。位置が負・範囲外・マルチバイト文字の途中ならValueError。ターミナル表示幅への変換ではない。"

    class API_053:
        "Model構成木を上限付き・非再帰的な診断用テキストとして表示する。"

        name @= "shikake.format_model_tree"
        kind @= OPERATION
        related @= (MODEL.SPEC_024,)
        input @= "model: Model"
        input @= "*"
        input @= "max_depth: int = 8"
        input @= "max_nodes: int = 200"
        input @= "max_chars: int = 12000"
        output @= "str"
        detail @= "rootの深さは0。指定の深さ・ノード数・文字数に達したら省略する。上限不正時はValueError。完全なシリアライズではない。"

        class EXAMPLE:
            """構成木を深さと出力数を制限して表示します。

            ```python
            import shikake

            model = shikake.parse_source("value = 1 + 2")
            print(shikake.format_model_tree(model, max_depth=4, max_nodes=30))
            ```

            この表示は診断用で、Modelの完全なシリアライズではありません。"""

    class API_054:
        "完全な単一ソース解析から字句スコープ別の名前束縛を取得する。"

        name @= "shikake.SourceInspection.name_bindings"
        kind @= VALUE
        related @= (PARSING.SPEC_023,)
        output @= "tuple[NameBinding, ...]"
        detail @= (
            "完全な解析でのみ取得可能。不完全なら、Modelが部分的に残っていても空。"
        )

        class EXAMPLE:
            """完全な単一ソースの束縛情報を参照します。

            ```python
            import shikake

            inspection = shikake.inspect_source("count = 1\\ncount = 2\\n")
            if inspection.complete:
                for binding in inspection.name_bindings:
                    print(binding.name, binding.state.may_rebind)
            ```

            不完全な解析ではname_bindingsは空になります。"""

    class API_055:
        "ソースのコメントをASTモデル化とは独立して抽出する。"

        name @= "shikake.collect_comments"
        kind @= OPERATION
        related @= (PARSING.SPEC_030, PARSING.SPEC_032)
        input @= "source: str"
        output @= "SourceComments"
        detail @= "型コメントを解釈せず全コメント原文を収集する。CR・LF・CRLFでASTと同じ行番号を用いる。保証対象は同一PythonでASTが構文解析可能なソースとし、不正ソースのコメント結果・例外種別はPython間で保証しない。ファイル入力はtokenize.open()でエンコーディングとBOMを処理する。tokenize由来の字句エラーは伝播し、既存のparse/inspect APIには影響しない。"

        # The generator preserves docstring indentation; keep runnable fences.
        # fmt: off
        class EXAMPLE:
            r"""行番号ベースのコメント検索を行います。

```python
import shikake

source = "# note\nvalue = 1  # type: int\n"
comments = shikake.collect_comments(source)
model = shikake.parse_source(source).get_nodes("body")[0]
if model.span is not None:
    print(comments.above_line(model.span.line))
    print(comments.on_right_of_line(model.span.line))
    print(comments.in_lines(model.span.line, model.span.end_line))
```

関数・クラス直下のコメントや代入文の行末コメントも、同じ公開APIを組み合わせるだけで取得できます。

```python
import io
import shikake

source = (
    "def f():\n    # function note\n    value = 1  # assignment note\n    return value\n"
    "class C:\n    # class note\n    item = 2  # class assignment note\n"
)
comments = shikake.collect_comments(source)
function, cls = shikake.parse_source(source).get_nodes("body")
for definition in (function, cls):
    first = definition.get("body").get_nodes("statements")[0]
    if first.span is not None:
        # ASTの列はUTF-8バイト単位です。
        lines = io.StringIO(source, newline=None).readlines()
        prefix = lines[first.span.line - 1].encode("utf-8")[: first.span.column]
        if not prefix.strip():
            print(comments.above_line(first.span.line))
        print(comments.on_right_of_line(first.span.end_line))
```

本体冒頭コメントのレシピは、その文が行の先頭（インデント以外のコードが前にない位置）から始まる場合に限ります。開始列の前をソースのUTF-8バイト列で調べ、空白のみか確認します。行の分割には `io.StringIO(source, newline=None).readlines()` を使い、ASTでは改行にならない改ページやUnicode区切り文字も分割する `str.splitlines()` は使いません。`def f(): return 1` のようにヘッダーと本体が同じ行なら使用しません。デコレータ付き関数・クラスの直前を調べる場合、デコレータ付きソースを独立に解析し、定義Modelの開始行と `get_nodes("decorators")` の各開始行の最小行を `above_line()` に渡します。

```python
import shikake

source = "# definition note\n\n@decorator\ndef decorated():\n    return 1\n"
comments = shikake.collect_comments(source)
function = shikake.parse_source(source).get_nodes("body")[0]
if function.span is not None:
    lines = [function.span.line]
    lines.extend(d.span.line for d in function.get_nodes("decorators") if d.span is not None)
    print(tuple(comment.text for comment in comments.above_line(min(lines))))
    # ('# definition note',)
```

ファイルのエンコーディング宣言やBOMは `tokenize.open(path)` で処理し、Model解析とコメント収集へ同じUnicode文字列を渡します。最初の本体文の開始行への上方検索は、間にコード行が存在すればそこで停止します。代入文の終了行への検索は行単位であり、同一行の別の文とも区別しません。複数行にまたがる構文内部のコメントは `in_lines()` を使います。Model.spanの行番号を既存の行検索に渡すだけでよく、Modelからコメントへの専用照会は不要です。ルートModelなどspan=Noneの場合には照会できません。同じ行の別のModelでも行検索結果は同じです。必ず同一ソースを使用し、コメントの意味的な所属は推測しません。"""

        # fmt: on

    class API_056:
        "原文コメント1件を表す不変の位置情報。"

        name @= "shikake.Comment"
        kind @= TYPE
        related @= (PARSING.SPEC_030, PARSING.SPEC_032)
        output @= "Comment"
        detail @= "textは#を含む原文。lineは1始まり、column/end_columnは0始まりUnicode文字位置。AST/SourceSpanのUTF-8バイト列とは異なる。"

    class API_057:
        "ソースのコメントと行位置索引を保持する不変の結果型。"

        name @= "shikake.SourceComments"
        kind @= TYPE
        related @= (PARSING.SPEC_030, PARSING.SPEC_031)
        output @= "SourceComments"
        detail @= "collect_comments()が生成。内部のコメント行索引とコード行索引の一貫性を維持するため、直接構築やdataclasses.replace()はサポートしない。copy/pickleによる複製は可能。構造Modelへの追加・意味的な所有関係の推測は行わない。reprは件数のみ表示。"

    class API_058:
        "指定された両端を含む行範囲内のコメントを列挙する。"

        name @= "shikake.SourceComments.in_lines"
        kind @= OPERATION
        related @= (PARSING.SPEC_031,)
        input @= "first: int"
        input @= "last: int"
        output @= "tuple[Comment, ...]"
        detail @= "1始まりの行の閉区間。コメントをソース順に返す。Model.spanがあればline/end_lineをそのまま指定できるが、モデルへの所属は保証しない。"

    class API_059:
        "行末コメントをコードとの位置関係から取得する。"

        name @= "shikake.SourceComments.on_right_of_line"
        kind @= OPERATION
        related @= (PARSING.SPEC_031,)
        input @= "line: int"
        output @= "tuple[Comment, ...]"
        detail @= "コメントより前にコードのある同一行のみ。対応するModelは必要ない。代入文Modelのspan.end_lineを指定すれば終了行の行末コメントを照会できる。開始行のModel.span.lineも指定できるが、同じ行にある別Modelとの区別やコメントの所有関係の判定はしない。"

    class API_060:
        "コード行に遮られない上方コメントを取得する。"

        name @= "shikake.SourceComments.above_line"
        kind @= OPERATION
        related @= (PARSING.SPEC_031,)
        input @= "line: int"
        output @= "tuple[Comment, ...]"
        detail @= "照会行は含めない。直近のコード行で探索を止め、空行は通過する。関数・クラス本体の最初の文のspan.lineを指定すると、その文の上にあるコメントを検索できる。定義Modelの開始行を使って本体内のコメントが得られるわけではない。本体先頭の利用例は、その行の文より前に空白以外のコードがない場合のみ適用する。同じ行に関数ヘッダーがある場合は該当しない。デコレータ付き定義の上を検索する場合は各デコレータ開始行も考慮して最も早い行から照会する。意味やモデルへの所属は判断しない。"

    class API_061:
        "最初のコード行より前のコメント群を取得する。"

        name @= "shikake.SourceComments.module_header"
        kind @= OPERATION
        related @= (PARSING.SPEC_031,)
        output @= "tuple[Comment, ...]"
        detail @= "コードのないファイルでは全コメントを返す。"

    class API_062:
        "最後のコード行より後のコメント群を取得する。"

        name @= "shikake.SourceComments.module_footer"
        kind @= OPERATION
        related @= (PARSING.SPEC_031,)
        output @= "tuple[Comment, ...]"
        detail @= "コードのないファイルでは全コメントを返す。"

    class API_063:
        "ソース順のコメント全件を取得する。"

        name @= "shikake.SourceComments.comments"
        kind @= VALUE
        related @= (PARSING.SPEC_030, PARSING.SPEC_031)
        output @= "tuple[Comment, ...]"
        detail @= (
            "元の # コメントをすべて保持した不変タプル。型コメントも特別扱いしない。"
        )

    class API_064:
        """完全な単一ソースの束縛をidentity単位で検索し、組み込み名の暗黙導入も必要時に取得する。"""

        name @= "shikake.SourceInspection.bindings_for"
        kind @= OPERATION
        related @= (BINDING.SPEC_014, BINDING.SPEC_017)
        input @= "scope: Model, name: str"
        output @= "tuple[NameBinding, ...]"
        detail @= "完全なSourceInspectionのみ。scopeには同じ解析結果のModelを渡す。記述された名前の束縛はidentityで照会する。同じ定義Modelに注釈スコープと本体スコープが付く場合はscope_kindで区別する。ソースのモジュールModelとPython組み込み名であれば暗黙導入を合成して返す。問い合わせ結果がname_bindingsの列挙に含まれるとは限らない。入れ子スコープを越えた参照先の確定や実行時の名前解決は行わない。"
