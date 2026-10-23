"""{{project.name}} の公開向けREADMEの日本語正本ソース。"""

from shikumi_devdoc.norms.common import canonical_source
from shikumi_devdoc.norms.document import title


@canonical_source(
    "{{project.name}}",
    filename="README.md",
    merge_policy="all",
    heading="title",
)
class README:
    """**{{project.name}}** は、PythonのASTを基礎に、Pythonソースコードの静的な構造や関係を、利用者が定めた個別の構造規約に基づいてModel化するライブラリです。

    主に、他言語への変換や制限付きPython文法の設計・検査など、Pythonコードを独自の規則に基づいて扱うための基盤を提供します。

    また、利用者が独自の構造を外部から定義し、特定のPython構文をその構造としてモデル化することもできます。"""

    class ALPHA:
        """{{project.name}} は現在Alpha版です。開発中のため、公開API・仕様・データ構造などに予告なく破壊的な変更が行われる場合があります。

        最新の開発状況については[STATUS](docs/STATUS.md)を参照してください。"""

        title @= "開発状況（Alpha）"

    class CONCEPTS:
        """{{project.name}} は、Pythonの構文をそのまま保存するのではなく、利用目的に応じて解釈できる抽象的な情報へ変換します。"""

        title @= "基本概念"

        class MODEL_STRUCTURE:
            """- **Kind**：構文要素の分類を表します。
            - **Structure**：構成要素の役割（role）と形式（shape）を定義します。
            - **Feature**：非同期指定や明示的なlazy import修飾など、分類とは独立した構文上の特徴を表します。
            - **Model**：これらに基づく具体的な構成要素を保持します。

            Kind・Structure・FeatureはModel体系を構成します。信頼済みのShikumi記述体、または `ExternalDefinitionsBuilder` によるPythonデータから外部KindとStructureを追加でき、登録された呼び出しは解析時に専用のModelとして扱われます。外部Feature宣言には対応していません。"""

            title @= "Modelの構造"

        class BINDINGS:
            """識別子の束縛について、次の性質を独立して表します。

            - `introduction`：導入が構文上明快か（`stable` / `unstable`）。
            - `may_rebind`：最初の導入とは別の書き込み、または反復・増分代入等による再束縛の可能性があるか。
            - `may_delete`：削除の可能性があるか。

            `x = 1` だけなら `may_rebind=False`、続けて `x = 2` があればTrueです。`n += 1` だけでは安定した導入とみなされません。これらは構文上の情報であり、実行結果やコードの品質、読み取り時点の確定代入を評価するものではありません。"""

            title @= "束縛の3軸"

        class RELATIONS:
            """基底クラスの参照先や、同名メソッドによるオーバーライド候補を取得できます。

            これらはASTから確認できる静的候補であり、実行時の参照先やメソッド解決順序を確定するものではありません。

            詳細なAPI契約と関連する仕様正本への導線は[APIリファレンス](docs/api_reference/INDEX.md)を参照してください。"""

            title @= "静的な関係候補"

    class INSTALL:
        """Python `{{project.requires_python}}` に対応し、CIでは3.11〜3.15を検証対象とします。Python 3.14のt-stringもModel化できます。

        ```bash
        python -m pip install {{project.name}}
        ```"""

        title @= "インストール"

    class QUICK_START:
        """```python
        import {{project.import_name}}

        source = '''
        class Counter:
            def __init__(self, start=0):
                self.value = start

            def increase(self, amount):
                if amount > 0:
                    self.value += amount
                return self.value

        def calculate(values):
            counter = Counter()
            for value in values:
                counter.increase(value)
            return counter.value
        '''

        root = {{project.import_name}}.parse_source(source)

        for model in root.walk():
            print(model.kind.id)
            print([part.role for part in model.parts()])
        ```

        `parse_source()` はPythonソースをModel化し、`walk()` はModelの構成木を走査します。

        ModelのKind・Structure・Featureを使うことで、元のASTに直接依存せず、構文要素を分類して扱えます。"""

        title @= "基本的な使い方"

        class STRICT_PARTIAL:
            """{{project.name}} には、目的に応じて2つの解析方法があります。

            - **Strict解析**：`parse_source()` / `parse_package()` を使用します。解析できない構文や構造がある場合は例外を送出し、完全な解析結果を要求します。
            - **Partial解析**：`inspect_source()` / `inspect_package()` を使用します。解析できない箇所があっても、取得可能な範囲の結果と診断情報を返します。

            完全な解析結果を必要とする処理にはStrict解析を、未対応箇所の調査や診断にはPartial解析を使用します。Partial解析の結果は不完全な場合があるため、完全な解析結果として扱うことはできません。

            4つの解析APIは既定で `syntax_validation="compile"` を用い、AST構築に加え
            CPythonコンパイラの構文検証を行います（入力コードは実行しません）。
            Pythonのコンパイル水準の制約を適用せずASTのみをモデル化したい場合は
            `syntax_validation="ast"` を明示してください。ASTのみの検証では
            PythonとしてコンパイルできないコードもModel化を試みますが、shikakeの未対応構文は引き続き拒否します。
            コンパイル可能性は実行時の正しさや安全性の保証ではありません。

            `parse_package()` / `inspect_package()` では `include(path, is_directory)` により
            下位ディレクトリや対象ファイルを選別できます。`False` のディレクトリには下降しません。
            `extensions=(".py",)` では対象の拡張子をタプルで指定でき、例えば `(".dot",)` なら
            `.dot` のみ、`(".py", ".dot")` なら両方をPython ASTとして解析します。
            省略時の拡張子は `.py` のみ、`include` 省略時は `.venv` 等も含め全候補を対象とし、除外方針は利用側が決定します。

            解析対象コードの静的なimport文を制限したい場合は、4つの解析APIで
            `import_policy` を指定できます。既定の `"unrestricted"` は従来どおり、
            `"registered_interfaces"` は登録済みinterfaceの明示importだけ、
            `"registered_modules"` は登録済みモジュールと任意の絶対モジュール名を
            `allowed_modules=("math", "custom_tools")` のように許可します。
            `"registered_modules"` は登録済みinterfaceの明示importも許可します。両制限モードで
            `from __future__ import annotations` のみをfuture宣言の例外として認めます。
            制限モードではパッケージ内部の相対import（例：`from . import helper`）も拒否します。
            これは許可名を増やしても変わらないため、必要なら絶対importへ書き換え、
            利用側がその絶対モジュール名を許可してください。`allowed_modules` はNFKC正規化済みの名前を指定します。
            指定名の実在・ランタイム同一性は調べず、importの制限はサンドボックスではありません。

            詳しくは[APIリファレンス](docs/api_reference/INDEX.md)を参照してください。"""

            title @= "Strict解析とPartial解析"

    class EXTERNAL:
        """{{project.name}} では、利用者がShikumi記述体または `shikake.external.ExternalDefinitionsBuilder` により独自のKind・Structureを定義し、解析に組み込むことができます。

        例えば、他言語への変換先が独自のメモリ操作や入出力機構を備えている場合、それらのインターフェースに対応する構造を定義できます。

        登録された外部構造へのimportと呼び出しは、規定された条件を満たす場合、通常のPython呼び出しとは異なる専用のModelとして表現されます。

        これにより、利用者はPython側の呼び出し構文を利用しながら、解析結果では変換先に適した独自の構造を取得できます。

        外部構造の認識には明示的なimportや名前の保護に関する制約があります。また、任意のライブラリ呼び出しを自動的に解決する機能ではありません。

        詳細は[APIリファレンス](docs/api_reference/INDEX.md)を参照してください。"""

        title @= "外部構造の定義"

    class APPLICATIONS:
        """他言語への変換と制限付きPythonの検査は、基本的に同じ手順で構築できます。

        ModelのKind・Structure・Featureを調べ、必要に応じて束縛情報や静的な関係候補を取得し、**利用側で定義した規則**に従って変換または許可・拒否を判断します。

        {{project.name}} 自体は変換規則や許可規則を定義しません。

        また、Modelは正規の解析経路から取得して利用することを想定しており、利用者による独自のModel構築はサポート対象外です。"""

        title @= "解析結果の利用"

    class LIMITATIONS:
        """{{project.name}} はソースコードを実行せず、値の評価、型推論、動的な名前解決を行いません。

        Modelは元のPythonコードの完全な復元や、実行時の意味の再現を目的としていません。また、構文の解析・制限だけでは安全な実行環境を保証できません。

        個別の保証と制約は[APIリファレンス](docs/api_reference/INDEX.md)を、文書体系は[文書管理ポリシー](docs/DOCUMENTATION_POLICY.md)を参照してください。"""

        title @= "制約"

    class DOCUMENTS:
        """[APIリファレンス](docs/api_reference/INDEX.md) | [開発状況](docs/STATUS.md) | [変更履歴](CHANGELOG.md) | [文書管理ポリシー](docs/DOCUMENTATION_POLICY.md)"""

        title @= "ドキュメント"

    class LICENSE:
        """{{project.name}} は[MIT License](LICENSE)で公開されています。"""

        title @= "ライセンス"
