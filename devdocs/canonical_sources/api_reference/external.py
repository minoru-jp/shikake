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

    `definitions=` は外部Call・Type・Genericの専用Model化に使う。
    外部登録の有無でimport文を拒絶しない。通常のimportはModelとして保持し、
    許可・不許可の判断は利用側が行う。解析対象のモジュールは実行・importしない。
    詳細は `EXTERNAL.SPEC_013` に従う。"""

    class API_001:
        "明示的importを通じて呼ぶ外部構造操作の宣言。"

        name @= "shikake.external.ImportedCall"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_003,)
        input @= 'path: str 例 "framework.memory:Memory.new"'
        output @= "ImportedCall"
        detail @= "モジュール名と1つ以上の識別子が必要。直接関数と属性呼び出しに対応する。モジュール名・属性名はNFKC正規化済みの識別子に限る。"

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
        "外部DefinitionIndex・マッピングとFeatureの宣言出自を保持する。"

        name @= "shikake.external.ExternalDefinitions"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_001, EXTERNAL.SPEC_018)
        input @= "index: DefinitionIndex"
        input @= "mappings: tuple[CallMapping, ...]"
        input @= "type_mappings: tuple[TypeMapping, ...]"
        input @= "generic_mappings: tuple[GenericMapping, ...]"
        input @= "external_feature_ids: frozenset[str]"
        output @= "ExternalDefinitions"
        detail @= "解析器へdefinitions=で渡す。外部Featureの出自とマッピングはbase合成後にも保持する。Builder・Shikumiローダー経由だけが整合性を検証する。ExternalDefinitionsを直接構築した場合は、公開されたexternal_feature_idsを含め利用側が妥当性と出自を保証する。"

    class API_004:
        "信頼済みPython記述モジュールをShikumiで検証し外部定義を作成する。"

        name @= "shikake.external.load_external_definitions"
        kind @= OPERATION
        related @= (EXTERNAL.SPEC_001,)
        input @= "source: ModuleType"
        input @= "*"
        input @= "base: DefinitionIndex | ExternalDefinitions | None = None"
        output @= "ExternalDefinitions"
        detail @= "解析対象ソースは実行しない。合成にはbase=ExternalDefinitionsを推奨する。組み込みIndexのみのbaseは利用できるが、独自・拡張済みIndex単体は先行マッピングや外部Feature出自を復元できないため拒否する。合成はload_external_definitions(module, base=previous)（previousはExternalDefinitions）で行う。解析APIのindex引数にExternalDefinitionsを渡さない。"

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

            **対応範囲：** 外部Shikumi宣言ではKind・Structure・Featureを追加できます。
            外部マッピングから付与できるFeatureは外部宣言されたIDだけです。組み込みの `async`・`generator`・`lazy` は明示付与できません。"""

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
        input @= "features: tuple[str, ...] = ()"
        output @= "CallMapping"
        detail @= "ExternalDefinitions.mappingsに保持する不変の対応付け。"

    class API_015:
        """PythonのデータからShikumi方式と同等の検証済み外部定義を構築するビルダー。"""

        name @= "shikake.external.ExternalDefinitionsBuilder"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_012,)
        input @= (
            "__init__(*, base: DefinitionIndex | ExternalDefinitions | None = None)"
        )
        input @= (
            "add_kind(kind_id: str, parent_id: str, structure_id: str | None = None)"
        )
        input @= "add_structure(structure_id: str, parts: Sequence[Role])"
        input @= "add_feature(feature_id: str, allowed_kind_ids: Sequence[str])"
        input @= "add_mapping(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, features: Sequence[str] = ())"
        input @= "add_call(target: str | ImportedCall, kind_id: str, arguments: Sequence[str] | Sequence[Argument], *, parent_id: str = 'model.value', structure_id: str | None = None, features: Sequence[str] = ())"
        input @= "add_type(target: str | ImportedType, kind_id: str, *, parent_id: str = 'model.value', features: Sequence[str] = ())"
        input @= "add_generic(target: str | ImportedGeneric, kind_id: str, roles: Sequence[str], *, parent_id: str = 'model.value', features: Sequence[str] = ())"
        output @= "build() -> ExternalDefinitions"
        detail @= "base=ExternalDefinitionsにより既存マッピングと外部Feature出自を引き継げる。拡張済みIndexのみでは両者を引き継げず、登録時に拒否される。Kind・Structure・Featureの外部IDは、ドット区切りで各セグメントがstr.isidentifier()を満たす2個以上の名前に限る（Python予約語・Unicode識別子は許可、先頭のmodel名前空間は予約）。IDのUnicode正規化は行わず、元の文字列で比較する。外部宣言Featureだけをマッピングから明示付与でき、正規解析経路のModelFactoryで生成するModelのFeature順序はID昇順に正規化する。Model直接構築では正規化しない。add_callはKindとCallMappingを併せて宣言し、structure_id省略時はnode roleだけの専用Structureを生成する。既存Kindにマッピングのみ追加するときはadd_mappingを使う。文字列の引数名はrole名とキーワード名の両方に使用し、異なる場合はArgumentを指定する。argumentsには名前とArgumentを混在させず、単一の文字列も渡せない。add_featureにより許可対象KindとFeatureを宣言できる。各マッピングのfeaturesでModelへの付与を明示する。build時にShikumi読み込みと共通の検証を適用し、保護import規則を緩和しない。解析対象ソースやimport先は実行しない。"

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

    class API_016:
        "明示的importから型注釈で利用される型名インターフェースの対象。"

        name @= "shikake.external.ImportedType"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_014,)
        input @= 'path: str 例 "pyinto.kinds:int32"'
        output @= "ImportedType"
        detail @= "Typeの参照は型記述位置でのみ専用Modelとなる。値参照は通常のName/Attribute Model。"

    class API_017:
        "角括弧で適用される外部Genericインターフェースの対象。"

        name @= "shikake.external.ImportedGeneric"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_014,)
        input @= 'path: str 例 "pyinto.kinds:Array"'
        output @= "ImportedGeneric"
        detail @= "登録された固定個数の位置引数でのみ専用Modelとなる。"

    class API_018:
        "外部Type参照と専用Kindとの対応情報。"

        name @= "shikake.external.TypeMapping"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_014,)
        input @= "target: ImportedType"
        input @= "kind_id: str"
        output @= "TypeMapping"
        input @= "features: tuple[str, ...] = ()"
        detail @= "出力KindのStructureは空のrolesで定義する。明示されたFeatureは専用Modelに付与する。"

    class API_019:
        "外部Generic適用と専用Kindとの対応情報。"

        name @= "shikake.external.GenericMapping"
        kind @= TYPE
        related @= (EXTERNAL.SPEC_014,)
        input @= "target: ImportedGeneric"
        input @= "kind_id: str"
        input @= "roles: tuple[str, ...]"
        output @= "GenericMapping"
        input @= "features: tuple[str, ...] = ()"
        detail @= "rolesは宣言順・固定個数のnode roles。明示されたFeatureは専用Modelに付与する。構文上の型意味は解釈しない。"

    class API_020:
        "Shikumi外部Type参照ターゲットを宣言する。"

        name @= "shikake.external.match_type"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_014,)
        input @= "ImportedType"
        output @= "Shikumi field assignment"
        detail @= "対応するKindをemitで指定する。"

    class API_021:
        "Shikumi外部Generic適用ターゲットを宣言する。"

        name @= "shikake.external.match_generic"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_014,)
        input @= "ImportedGeneric"
        output @= "Shikumi field assignment"
        detail @= "対応するKindをemitで指定する。"

    class API_022:
        "Shikumi外部Genericの固定位置引数のnode roleを列挙する。"

        name @= "shikake.external.slot"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_014,)
        input @= "role: str"
        output @= "Shikumi field assignment"
        detail @= "宣言順にGeneric引数の位置に対応する。"

    class API_023:
        "外部FeatureのIDを宣言するフィールド代入子。"

        name @= "shikake.external.feature_id"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_016,)
        input @= "feature_id: str"
        output @= "Shikumi field assignment"

    class API_024:
        "外部Featureを適用できるKind分類を列挙するフィールド代入子。"

        name @= "shikake.external.feature_allowed"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_016,)
        input @= "kind_id: str"
        output @= "Shikumi field assignment"
        detail @= "対象Kindとその子孫に適用できる。少なくとも1つの許可対象が必要。"

    class API_025:
        "外部Call・Type・Genericの専用Modelへ付与するFeatureを列挙する。"

        name @= "shikake.external.apply_feature"
        kind @= VALUE
        related @= (EXTERNAL.SPEC_017,)
        input @= "feature_id: str"
        output @= "Shikumi field assignment"
        detail @= "Model化が成立した場合だけ付与する。定義だけでは自動付与しない。"
