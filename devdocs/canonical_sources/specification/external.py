"""外部構造の定義と保護の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, MUST_NOT, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.binding import BINDING
from devdocs.canonical_sources.specification.model import MODEL
from devdocs.canonical_sources.specification.parsing import PARSING
from devdocs.canonical_sources.specification.relations import RELATIONS


@summary("Shikumi外部宣言を利用する構造の保護と登録済み呼び出しの契約。")
@canonical_source(
    "{{project.name}}: 外部構造の定義と保護",
    filename="external.md",
    order=70,
    merge_policy="all",
    heading="identity",
)
class EXTERNAL:
    """Shikumi外部宣言を利用する構造の保護と登録済み呼び出しの契約。"""

    class SPEC_001:
        """外部構造定義は信頼済みのPythonモジュールまたは `ExternalDefinitions` として `definitions=` に明示的に渡す。解析対象のPythonソースやimport先を定義情報の取得のために実行してはならない。"""

        title @= "外部宣言の分離"
        level @= MUST
        related @= (PARSING.SPEC_001,)

    class SPEC_002:
        """登録済みのimport可能な外部呼び出し定義に基づき、明示的importで認識できる外部構造のルートと属性連鎖を保護対象とする。`pkg:mod.Cls.make` は宣言モジュールが `pkg`、構造ルートが `pkg.mod.Cls` であり、`pkg.mod` という実在サブモジュールを意味しない。宣言ターゲットのモジュール・属性名はPython ASTと一致するNFKC正規化済み識別子であり、Pythonの予約語でないものに限る。登録モジュールへの明示経路がない `import framework` 等だけから未記述のサブモジュールを補完しない。"""

        title @= "構造ルートの認識"
        level @= MUST
        related @= (RELATIONS.SPEC_006,)

    class SPEC_003:
        """保護対象の構造ルートまたはその属性連鎖を直接呼び出す場合は、既存の `ImportedCall` / `CallMapping` に登録されたパスだけを許可する。未登録の任意属性の呼び出しを通常Callへフォールバックしてはならない。"""

        title @= "登録済み呼び出しの許可"
        level @= MUST

    class SPEC_004:
        """保護対象の構造ルートや属性連鎖を、代入の右辺、引数、return、コンテナ要素、条件式等で値として取り出してはならない。ただし登録済み直接呼び出しの戻り値は通常の値として利用してよい。"""

        title @= "構造自体を値にしない"
        level @= MUST_NOT

    class SPEC_005:
        """保護対象の構造またはその属性連鎖へ代入・削除等の変更を加えてはならない。Pythonの動的な属性取得を推測し、未登録経路に抜け道を作ってはならない。"""

        title @= "構造の変更禁止"
        level @= MUST_NOT

    class SPEC_006:
        """`import framework.memory` と `import framework.other` のように同じ根を共有する明示的サブモジュールimportを、それだけで競合する別の束縛とはみなさない。対象ルートの再束縛とは区別する。"""

        title @= "importパスの併記"
        level @= MUST
        related @= (RELATIONS.SPEC_006,)

    class SPEC_007:
        """登録済み外部構造呼び出しは、宣言されたMappingに従いKindとStructureへ対応付ける。構造オブジェクト自体を値へ変換したものとして扱わない。"""

        title @= "構造の呼び出し結果"
        level @= MUST
        related @= (MODEL.SPEC_004,)

    class SPEC_008:
        """外部構造の未登録操作や不正な使用はStrictで `ExternalModelingError` として拒否し、Partialでは `external_definition` の診断で報告する。名前解決が不足する場合も外部ソースを実行して補完しない。"""

        title @= "エラー契約"
        level @= MUST
        related @= (PARSING.SPEC_005,)

    class SPEC_009:
        """外部構造の保護のために動的alias追跡、任意の関数の副作用、値伝播、他モジュールの実行状態の追跡を追加してはならない。共通AST事実を利用した保守判定に限る。"""

        title @= "追加解析をしない"
        level @= MUST_NOT
        related @= (BINDING.SPEC_012,)

    class SPEC_010:
        """登録された外部構造へ到達する明示的importは、モジュール直下の無条件な記述だけを許可する。`if`、`try`、ループ等の複合文内部や関数・クラス本体内の対象importは、使用の有無や条件式の内容によらず、import文自体を拒否する。外部構造の保護規則自体は無関係なimportへこの配置・条件の制約を拡張しない。利用側が指定するimport許可範囲については `SPEC_013` に従う。登録済みモジュールからのstar importは、保護対象となる名前を確定できないため拒否する。認識済みの予約名を保護する別の制約は `SPEC_011` に定める。"""

        title @= "外部構造importの許可位置と不明な公開名"
        level @= MUST
        related @= (PARSING.SPEC_005,)

    class SPEC_011:
        """許可された明示的importで認識した外部構造の束縛名（別名や通常のdotted importで束縛される先頭名を含む）は、解析対象ファイル全体で予約名として保護する。予約名に対する再束縛・削除や、同名の定義・別のimport・仮引数・内包表記の変数・型パラメータ等の束縛は、記述順序、条件、字句スコープ、外部構造の使用の有無によらず拒否する。ただし、元の許可済みimportおよび同じ根を共有する許可済みの明示的サブモジュールimportは、競合する再束縛とはみなさない。予約名が存在するときは、無関係なモジュールからのstar importも予約名を導入する可能性を除外できないため、import元や記述位置によらず拒否する。外部モジュールを実行して公開名を調べたり、実行順序から安全性を推測したりしない。予約名が存在しない場合、無関係なimportにこの保護制約を課さない。"""

        title @= "外部構造の予約名とstar importの保護"
        level @= MUST
        related @= (BINDING.SPEC_012, PARSING.SPEC_005)

    class SPEC_012:
        """信頼済みのPythonデータから外部Kind・Structure・CallMappingを構築するビルダーは、Shikumi記述体の読み込み経路と同じKindIndex・Mappingの意味検証を適用しなければならない。ビルダーは記述量を減らす便宜APIであり、保護対象のimport経路、登録済み呼び出しの許可範囲、引数規約、外部Featureの非対応を緩和しない。利用者が渡すKind・Structure・Mappingは解析対象のPythonコードとは独立し、解析対象や外部インターフェースを実行・importしない。"""

        title @= "プログラムによる外部定義と共通検証"
        level @= MUST
        related @= (PARSING.SPEC_022,)

    class SPEC_013:
        """`parse_source`・`inspect_source`・`parse_package`・`inspect_package` は利用側の選択により `import_policy` を受け取る。既定の `"unrestricted"` は従来どおりimportの許可集合を制限しない。`"registered_interfaces"` では信頼済み `ExternalDefinitions` のCallMappingから得る構造ルート（`dot:Fn.sin` なら `dot.Fn`）について、`from dot import Fn` のようにinterface自身を明示導入する絶対importだけを許可し、`import dot`、未登録の名前、サブモジュールの推測を許可しない。`"registered_modules"` では外部定義のCallMappingに記述されたモジュール名と `allowed_modules` に指定された任意の絶対モジュール名を合算し、`import module` / `import module as alias` / `from module import name` を許可する。さらに `"registered_interfaces"` が許可する登録済み構造ルートの明示的from importは、宣言モジュール名とimport元が一致しなくても必ず許可する。`pkg:mod.Cls.make` の `from pkg.mod import Cls` は両モードで許可するが、このことだけで `pkg.mod` 全体のimportや `from pkg.mod import helper` を許可しない。`from module import name` の `name` の実在・種類・使用可能性は調べず、追加で許可したモジュールの呼び出しは登録された外部構造でない限り通常CallとしてModel化する。`allowed_modules: tuple[str, ...] = ()` は `"registered_modules"` にだけ非空指定でき、重複、空文字列、相対名、Pythonの絶対モジュール名でない指定、NFKC正規化されていない指定は拒否し、黙って正規化してはならない。`import_policy` の未知の値、`allowed_modules` の不正な型や名前は明示的に拒否し、選別されたファイルにimportがなくても検証する。モジュール名は大文字小文字を区別し、ASTに明記された絶対import元と完全一致させる。`import pkg.child` と `from pkg import child` を実行時に同等とは推測しない。制限モードでは、相対importと `from module import *` を拒否する。ただし `from __future__ import annotations` という単独の宣言は両制限モードで許可し、`__future__` モジュール全体や他のfuture名を特別に許可しない。Pythonのimport解決、標準ライブラリ判定、ファイル探索、属性の実在、ランタイムのライブラリ同一性を確認しない。外部構造の保護・予約名・import配置に関する既存規則はこの許可判定の後も有効とし、動的importを阻止するセキュリティ・サンドボックスとして扱ってはならない。違反した構文は `external.unregistered_import` としてモジュール単位で拒否し、Strictでは `ExternalModelingError`、Partialでは `model=None` のファイル全体の診断とする。Partialのパッケージでは違反モジュールを除いて残りのモジュールを保持し、不完全な関係・束縛事実を断定しない。`details.path` は違反したAST記述のimport名、`details.policy` は指定されたモードとする。同一ファイル内の全違反を収集する保証は設けず、構文上の位置（行・列）の早いimport違反を最初に検出して拒否してよい。"""

        title @= "利用側が選択するimport許可範囲"
        level @= MUST
        related @= (PARSING.SPEC_008, PARSING.SPEC_020)
