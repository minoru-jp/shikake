"""shikakeのREADMEに対応する日本語正本ソース。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}}",
    filename="README.md",
    merge_policy="all",
    heading="title",
)
class README:
    """**注意：アルファ版です。** APIやModelの契約には破壊的変更が加わる可能性があります。

    **{{project.name}}** は、Pythonソースを構造化されたModelへ変換します。**構造を提供し、意味と採否の判断は利用側に委ねます。**

    - **構成要素**：**Kind**（分類）、**Structure**（役割と形式）、**Feature**（独立した構文上の特徴）。
    - **基盤**：Python標準の `ast`・`tokenize` と、外部ライブラリ **Shikumi**。
    - **拡張**：利用側がCall・Type・Genericなどの外部インターフェースとFeatureを登録できます。"""

    class INSTALL:
        """Python 3.11以降に対応します。

        ```bash
        python -m pip install shikake
        ```

        開発状況と対応範囲については[STATUS](docs/STATUS.md)を参照してください。"""

        title @= "インストール"

    # Keep fenced examples unindented in generated Markdown.
    # fmt: off
    class EXAMPLE:
        """以下の作例で、次の要素をまとめてModel化します。

        - **Pythonの構造**：クラス、メソッド、ループ、型注釈。
        - **登録した構造**：外部Call・Type・Genericインターフェース。

        `demo` は説明用のモジュール名です。shikakeは解析対象を実行せず、`demo` もimportしません。"""

        title @= "作例"

        class SOURCE:
            r"""```python
source = '''from demo.kinds import Int32, Vector
from demo.ops import clamp

class Accumulator:
    def __init__(self, start: Int32):
        self.value = start

    def accumulate(self, numbers: Vector[Int32, 4]) -> Int32:
        total: Int32 = 0
        for number in numbers:
            total += number
        self.value += total
        return clamp(self.value, 0, 100)

def summarize(values: Vector[Int32, 4]) -> Int32:
    accumulator = Accumulator(0)
    return accumulator.accumulate(values)
'''
```"""

            title @= "1. 入力するPythonコード"

        class MODELING:
            r"""`ExternalDefinitionsBuilder` で、インポートした名前と構文上の使用形態を登録します。

- **Type**：`Int32` → `demo.type.int32`
- **Generic**：`Vector[...]` → `demo.type.vector`
- **Call**：`clamp(...)` → `demo.operation.clamp`

一致した構文は、通常の型参照・添字式・Callの代わりに専用Modelになります。

```python
from collections import Counter

import shikake
from shikake.external import ExternalDefinitionsBuilder

definitions = (
    ExternalDefinitionsBuilder()
    .add_type("demo.kinds:Int32", "demo.type.int32")
    .add_generic(
        "demo.kinds:Vector",
        "demo.type.vector",
        ("element", "length"),
    )
    .add_call(
        "demo.ops:clamp",
        "demo.operation.clamp",
        ("value", "lower", "upper"),
    )
    .build()
)

inspection = shikake.inspect_source(source, definitions=definitions)
assert inspection.complete and inspection.model is not None
root = inspection.model
counts = Counter(node.kind.id for node in root.walk())

for kind in (
    "model.definition.class",
    "model.definition.function",
    "demo.type.int32",
    "demo.type.vector",
    "demo.operation.clamp",
):
    print(f"{kind}: {counts[kind]}")
```

出力：

```text
model.definition.class: 1
model.definition.function: 1
demo.type.int32: 6
demo.type.vector: 2
demo.operation.clamp: 1
```

Modelに保持される構造の例：

- `Vector[Int32, 4]`：`element` に `demo.type.int32`、`length` にリテラル値 `4`。
- `clamp(...)`：`demo.operation.clamp`。

**Kindの名前は構造を表します。** `Int32` の整数幅などの意味をshikakeが解釈するわけではありません。"""

            title @= "2. 外部インターフェースの登録とModel化"

        class BINDINGS:
            r"""Model化の際に観測された、識別子の導入や使用も確認できます。前節の `inspection` と `root` を使います。

```python
method = next(
    node for node in root.walk()
    if node.kind.id == "model.definition.method"
    and node.get_scalar("name") == "accumulate"
)

for scope, name in (
    (root, "Int32"),
    (root, "clamp"),
    (method, "total"),
):
    state = inspection.bindings_for(scope, name)[0].state
    print(name, state)
```

出力：

```text
Int32 BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)
clamp BindingState(introduction='external', may_rebind=False, may_delete=False, may_value_use=False)
total BindingState(introduction='stable', may_rebind=True, may_delete=False, may_value_use=True)
```

4軸の`BindingState`は、**軽量な観測情報**です。

- **`introduction`**：名前の導入方法（`Int32`・`clamp` は `external`）。
- **`may_rebind` / `may_delete`**：再束縛・削除が観測されたか。
- **`may_value_use`**：値としての使用が観測されたか。登録済みのType・Callとしての使用は数えません。

`total` では増分代入と値参照が観測されます。各軸は網羅的な追跡ではなく、**`False` は不在の証明ではありません。**"""

            title @= "3. 識別子の束縛情報"

    # fmt: on
    class DESIGN:
        """shikakeは、Pythonのコードを完全に理解する代わりに、**利用側が判断できる構造**を提供します。

        - **構造を表す**：Kind・Structure・Feature、ソース位置、静的な関係候補。
        - **大まかに観測する**：名前の導入・再束縛・削除・値としての使用。型推論や識別子の詳細な追跡はしません。
        - **意味を決めない**：Pythonの実行時の振る舞い、Modelの受け入れ可否、変換先での解釈。
        - **利用側が決める**：例えば、再束縛が観測された構造を拒否する、登録済みインターフェースのTarget側での意味を定める。

        必要な場合のみ、`ModelRef(model, source_path)` でModel個体と `Path` に変換されるソースパスを束ね、辞書キーや外部ツールとのソース位置照合の手掛かりにできます。`ModelRef` の比較はModelの `is` とPathの `==` の双方に基づき、Model本体の構造的等価性を変更しません。

        **境界**：Pythonの構文規則や一部のスコープ規則は利用しますが、実行時意味論の完全な再現は目指しません。また、観測されていない事柄が存在しないとは限りません。強い保証が必要な利用側は、別途検証を行ってください。"""

        title @= "設計：構造を共有し、解釈は利用側へ"

    # Keep Shikumi examples unindented in rendered Markdown.
    # fmt: off
    class EXTERNAL:
        """外部インターフェースは、`ExternalDefinitionsBuilder` のほか、shikake自身も使う **Shikumiの宣言記法** で登録できます。

        - **`@=`**：Pythonの行列積代入構文を宣言に利用します。通常の `=` とは交換できません。
        - **解析対象**：Model化するPythonソース。実行・importしません。
        - **信頼済み定義**：利用側がimportする、Shikumiの定義モジュール。"""

        title @= "Shikumiによる外部定義"

        class BUILTIN:
            r"""shikake自身も、次のようにStructureとKindを宣言しています（内部定義からの抜粋）。

```python
# shikake内部の定義例（説明用にimportをまとめた抜粋）
from shikake._mica.kinds.regulation import (
    PartContract as Role, kind_id, parent_id,
    part, structure_id, structure_ref,
)

class ModuleDefinition:
    structure_id @= "module_definition"
    part @= Role("name", "text")
    part @= Role("body", "nodes")

class Module:
    kind_id @= "model.module"
    parent_id @= "model"
    structure_ref @= "module_definition"
```

- **`structure_id`・`part`**：Structureと構成要素を定義します。
- **`kind_id`・`parent_id`・`structure_ref`**：KindとStructureを結び付けます。

外部定義には内部モジュールではなく、公開APIの `shikake.external` を使います。"""

            title @= "1. shikake自身の定義"

        class DECLARATIONS:
            r"""前の `Int32`・`Vector`・`clamp` に対応する定義を、`trusted_definitions.py` として用意します。

```python
# trusted_definitions.py（利用側が用意する信頼済み定義）
from shikake.external import (
    Argument, ImportedCall, ImportedGeneric, ImportedType, Role,
    bind, emit, kind_id, match, match_generic, match_type,
    parent_id, part, slot, structure_id, structure_ref,
)

class Int32Structure:
    structure_id @= "demo.type.int32.type"

class Int32Kind:
    kind_id @= "demo.type.int32"
    parent_id @= "model.value"
    structure_ref @= "demo.type.int32.type"

class Int32Use:
    match_type @= ImportedType("demo.kinds:Int32")
    emit @= "demo.type.int32"

class VectorStructure:
    structure_id @= "demo.type.vector.generic"
    part @= Role("element", "node")
    part @= Role("length", "node")

class VectorKind:
    kind_id @= "demo.type.vector"
    parent_id @= "model.value"
    structure_ref @= "demo.type.vector.generic"

class VectorUse:
    match_generic @= ImportedGeneric("demo.kinds:Vector")
    emit @= "demo.type.vector"
    slot @= "element"
    slot @= "length"

class ClampStructure:
    structure_id @= "demo.operation.clamp.arguments"
    part @= Role("value", "node")
    part @= Role("lower", "node")
    part @= Role("upper", "node")

class ClampKind:
    kind_id @= "demo.operation.clamp"
    parent_id @= "model.value"
    structure_ref @= "demo.operation.clamp.arguments"

class ClampUse:
    match @= ImportedCall("demo.ops:clamp")
    emit @= "demo.operation.clamp"
    bind @= Argument("value", 0, "value")
    bind @= Argument("lower", 1, "lower")
    bind @= Argument("upper", 2, "upper")
```

- **Type**：`match_type` で型名を指定。Structureは空です。
- **Generic**：`match_generic` と `slot` で `[...]` の引数を指定。
- **Call**：`match` と `bind` で `(...)` の引数を指定。
- **共通**：`emit` は生成するKind ID。登録対象は `モジュール:名前` 形式です。"""

            title @= "2. 外部のType・Generic・Callを登録する"

        class LOADING:
            r"""定義モジュールはShikumiで検証して読み込み、前の作例と同じ `source` に渡せます。

```python
import shikake
import trusted_definitions
from shikake.external import load_external_definitions

definitions = load_external_definitions(trusted_definitions)
root = shikake.parse_source(source, definitions=definitions)
print([node.kind.id for node in root.walk()].count("demo.operation.clamp"))
# 1
```

外部定義が指定するのは **Model化の方法** だけです。実行・意味解釈・採否判定は行いません。詳細は[External Definitions API](docs/api_reference/external.md)を参照してください。"""

            title @= "3. 定義の読み込み"

    # fmt: on
    class FURTHER:
        """- **Modelの探索**：`walk()`、Kind、Structure、Feature、ソース位置を利用できます。
        - **定義への照会**：`definition_index()` または `definitions.index` の `classified_under`・`defines_role`・`allows_feature` で分類、role定義、Featureの適用可能性を個別に照会できます。Modelの内容とは別の問い合わせです。
        - **静的な関係候補**：基底クラスの参照先や同名メソッドのオーバーライド候補を取得できます。
        - **外部定義**：Call・Type・GenericインターフェースとFeatureはPython APIまたは信頼済みのShikumi記述で登録でき、Featureは外部宣言されたものだけ対応付けで明示的に付与でき、組み込みFeatureを付与することはできません。外部定義の合成には `ExternalDefinitionsBuilder(base=previous_definitions)` を使い、既存マッピングを維持します。外部IDには各部分が `str.isidentifier()` を満たす2個以上のドット区切り名を用い、Python予約語は許容します。先頭のmodel名前空間は予約されています。
        - **解析方法**：完全な解析には `parse_source()` / `parse_package()`、診断を伴う解析には `inspect_source()` / `inspect_package()` を使います。
        - **import検査**：必要なら利用側が `ImportPolicy` を指定して許可・禁止規則を委譲できます。star import自体はModel化しますが、暗黙の名前導入や束縛への影響は推論しません。

        詳細な契約と制約は[APIリファレンス](docs/api_reference/INDEX.md)を参照してください。"""

        title @= "Modelの利用"

    class DOCUMENTS:
        """- [APIリファレンス](docs/api_reference/INDEX.md)：公開APIと詳細契約
        - [STATUS](docs/STATUS.md)：現在の開発状況と既知の制約
        - [CHANGELOG](CHANGELOG.md)：バージョンごとの変更履歴
        - [文書管理ポリシー](docs/DOCUMENTATION_POLICY.md)：正本ソースと公開文書の管理方法"""

        title @= "ドキュメント"

    class LICENSE:
        """[MIT License](LICENSE)"""

        title @= "ライセンス"
