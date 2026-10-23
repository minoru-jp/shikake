"""shikake.externalの公開拡張定義API参照。"""

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

from devdocs.canonical_sources.specification.external import EXTERNAL
from devdocs.canonical_sources.specification.model import MODEL


@summary("shikake.externalの宣言・呼び出し対応付けAPI。")
@canonical_source(
    "{{project.name}}: External Definitions API Reference",
    filename="external.md",
    order=20,
    merge_policy="all",
    heading="identity",
)
class EXTERNAL_API:
    """信頼済みShikumi記述体とPythonデータビルダーに利用する公開型とフィールド。

    `definitions=` は登録済み構造のModel化に使う。これとは独立して
    4つの解析APIの `import_policy` では、`"registered_interfaces"` が
    登録済み構造ルートだけの明示importを、`"registered_modules"` が
    CallMappingのモジュール名と `allowed_modules` に指定した任意の絶対名の
    import、および登録済み構造ルートそのものの明示importを許可する。
    `pkg:mod.Cls.make` の構造ルートは `pkg.mod.Cls` であり、`pkg.mod` を
    自動的に許可したモジュールとはみなさない。制限モードでも
    `from __future__ import annotations` の単独宣言は認める。既定の `"unrestricted"` は従来どおり。
    許可した通常モジュールの関数は、別途外部登録されていなければ通常Callである。
    名前の実在・実行時の同一性は検証せず、import文を実行しない。
    詳細は `EXTERNAL.SPEC_013` に従う。"""

    class API_001:
        "明示的importを通じて呼ぶ外部構造操作の宣言。"

        name @= "shikake.external.ImportedCall"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_003,)
        input @= 'path: str 例 "framework.memory:Memory.new"'
        output @= "ImportedCall"
        detail @= "モジュール名とClass.method以上の属性連鎖が必要。モジュール名・属性名はNFKC正規化済みの識別子に限る。"

    class API_002:
        "外部Call引数からModelのnode roleへの対応付け。"

        name @= "shikake.external.Argument"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_007,)
        input @= "role: str"
        input @= "position: int"
        input @= "keyword: str"
        output @= "Argument"
        detail @= "positionは0からの連続値。"

    class API_003:
        "検証済みの外部KindIndexと呼び出し対応付けを保持する。"

        name @= "shikake.external.ExternalDefinitions"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_001,)
        input @= "index: KindIndex"
        input @= "mappings: tuple[CallMapping, ...]"
        output @= "ExternalDefinitions"
        detail @= "解析器へdefinitions=で渡す。"

    class API_004:
        "信頼済みPython記述モジュールをShikumiで検証し外部定義を作成する。"

        name @= "shikake.external.load_external_definitions"
        kind @= OPERATION
        related @= (EXTERNAL.SPEC_001,)
        input @= "source: ModuleType"
        input @= "*"
        input @= "base: KindIndex | None = None"
        output @= "ExternalDefinitions"
        detail @= "解析対象ソースは実行しない。"

        class EXAMPLE:
            """次の2ファイルは、外部インターフェースの呼び出しを専用Kindへモデル化する例です。
            まず、信頼済みのPythonモジュール `memory_definitions.py` にShikumi形式の
            Structure・Kind・呼び出し対応付けを宣言します。

            ```python
            # memory_definitions.py
            from shikake.external import (
                Argument, ImportedCall, Role,
                bind, emit, kind_id, match, parent_id,
                part, structure_id, structure_ref,
            )

            class AllocationStructure:
                structure_id @= "demo.memory.allocation"
                part @= Role("size", "node")

            class AllocationKind:
                kind_id @= "demo.memory.allocate"
                parent_id @= "model.value"
                structure_ref @= "demo.memory.allocation"

            class AllocationCall:
                match @= ImportedCall("sample.memory:Memory.allocate")
                emit @= "demo.memory.allocate"
                bind @= Argument("size", 0, "size")
            ```

            次に同じディレクトリで次を実行します。

            ```python
            # example.py
            import shikake
            import memory_definitions
            from shikake.external import load_external_definitions

            definitions = load_external_definitions(memory_definitions)

            source = (
                "from sample.memory import Memory\\n"
                "item = Memory.allocate(64)\\n"
            )

            root = shikake.parse_source(source, definitions=definitions)
            for model in root.walk():
                if model.kind.id == "demo.memory.allocate":
                    print(model.get_node("size").get("value"))
            ```

            実行結果は `64` です。`sample.memory` の実体は不要で、解析対象のimport先を
            実行・読み込みすることもありません。一方、定義モジュールは信頼済みのPython
            コードとして読み込む必要があります。登録済み呼び出しだけが専用Modelになり、
            任意の呼び出しを動的に解決するものではありません。

            **対応範囲：** 外部Shikumi宣言で追加できるのは現在KindとStructureです。
            外部Feature宣言は未対応で、指定すると拒否されます。"""

    class API_005:
        "外部Structureのrole・shapeを定義するPartContractの公開別名。"

        name @= "shikake.external.Role"
        kind @= TYPE
        related @= (MODEL.SPEC_005,)
        input @= "role: str"
        input @= "shape: PartShape"
        output @= "Role"
        detail @= "role名とshapeを明示する。"

    class API_006:
        "ImportedCallを登録するShikumiフィールド代入子。"

        name @= "shikake.external.match"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_003,)
        input @= "ImportedCall"
        output @= "Shikumi field assignment"
        detail @= "外部構造の呼び出しを完全パスで登録する。"

    class API_007:
        "登録済み呼び出しの出力Kind IDを指定するフィールド代入子。"

        name @= "shikake.external.emit"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_007,)
        input @= "kind_id: str"
        output @= "Shikumi field assignment"
        detail @= "出力は登録済みの具象Kindである必要がある。"

    class API_008:
        "ArgumentをShikumiの外部Callに関連づけるフィールド代入子。"

        name @= "shikake.external.bind"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_007,)
        input @= "Argument"
        output @= "Shikumi field assignment"
        detail @= "出力Structureのnode roleと一致させる。"

    class API_009:
        "外部のKind宣言でIDを指定するShikumiフィールド代入子。"

        name @= "shikake.external.kind_id"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_001,)
        input @= "id: str"
        output @= "Shikumi field assignment"
        detail @= "親・Structure ID等のフィールドとともに宣言。"

    class API_010:
        "外部のKind宣言で分類上の親を指定するフィールド代入子。"

        name @= "shikake.external.parent_id"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_001,)
        input @= "parent_id: str"
        output @= "Shikumi field assignment"
        detail @= "Kind分類に関する指定。"

    class API_011:
        "外部のKindが直接使うStructureを参照するフィールド代入子。"

        name @= "shikake.external.structure_ref"
        kind @= VALUE
        related @= (MODEL.SPEC_004,)
        input @= "structure_id: str"
        output @= "Shikumi field assignment"
        detail @= "分類上の親からStructureは継承しない。"

    class API_012:
        "外部StructureのIDを宣言するフィールド代入子。"

        name @= "shikake.external.structure_id"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_001,)
        input @= "id: str"
        output @= "Shikumi field assignment"
        detail @= "重複IDは拒否される。"

    class API_013:
        "外部Structureのrole/shape定義を列挙するフィールド代入子。"

        name @= "shikake.external.part"
        kind @= VALUE
        related @= (MODEL.SPEC_005,)
        input @= "Role"
        output @= "Shikumi field assignment"
        detail @= "宣言順を保持する。"

    class API_014:
        "外部呼び出しの照合先・出力Kind・引数対応を保持する。"

        name @= "shikake.external.CallMapping"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_003, EXTERNAL.SPEC_007)
        input @= "target: ImportedCall"
        input @= "kind_id: str"
        input @= "arguments: tuple[Argument, ...]"
        output @= "CallMapping"
        detail @= "ExternalDefinitions.mappingsに保持する不変の対応付け。"

    class API_015:
        """PythonのデータからShikumi方式と同等の検証済み外部定義を構築するビルダー。"""

        name @= "shikake.external.ExternalDefinitionsBuilder"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_012,)
        input @= "__init__(*, base: KindIndex | None = None)"
        input @= (
            "add_kind(kind_id: str, parent_id: str, structure_id: str | None = None)"
        )
        input @= "add_structure(structure_id: str, parts: Sequence[Role])"
        input @= "add_mapping(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument])"
        input @= "add_call(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, parent_id: str = 'model.value', structure_id: str | None = None)"
        output @= "build() -> ExternalDefinitions"
        detail @= "add_callはKindとCallMappingを併せて宣言し、structure_id省略時はnode roleだけの専用Structureを生成する。既存Kindにマッピングのみ追加するときはadd_mappingを使う。文字列の引数名はrole名とキーワード名の両方に使用し、異なる場合はArgumentを指定する。argumentsには名前とArgumentを混在させず、単一の文字列も渡せない。build時にShikumi読み込みと共通の検証を適用し、保護import規則を緩和せず、外部Featureの追加もサポートしない。解析対象ソースやimport先は実行しない。"

        class EXAMPLE:
            """簡易な外部呼び出し定義の例です。Shikumiの記述クラスは不要です。

            ```python
            import shikake
            from shikake.external import ExternalDefinitionsBuilder

            definitions = (ExternalDefinitionsBuilder()
                .add_call("sample.memory:Memory.allocate", "demo.memory.allocate", ("size",))
                .build())
            source = "from sample.memory import Memory\\nitem = Memory.allocate(64)\\n"
            root = shikake.parse_source(source, definitions=definitions)
            for model in root.walk():
                if model.kind.id == "demo.memory.allocate":
                    print(model.get_node("size").get("value"))
            ```

            出力は `64` です。独自のKind分類・共有Structure・異なる引数keywordが必要なら
            `add_kind`、`add_structure`、`Argument` と `structure_id` を併用します。
            ビルダーは既存Shikumi宣言の代替入口であり、独自の許可規則を追加しません。"""
