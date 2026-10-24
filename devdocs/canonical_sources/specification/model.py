"""Model・分類・構造の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, MUST_NOT, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.policy.canonical import MODELING_POLICY


@summary("Model、Kind、Structure、Featureと、その間に成立する契約。")
@canonical_source(
    "{{project.name}}: Model・分類・構造",
    filename="model.md",
    order=10,
    merge_policy="all",
    heading="identity",
)
class MODEL:
    """Model、Kind、Structure、Featureと、その間に成立する契約。"""

    class SPEC_001:
        """ModelはPython ASTから採用した処理のKind、ソース位置（取得可能な場合）、Feature、および順序を持つ役割付きの構成要素を保持する。実行時の値、型、効果を確定した情報として保持してはならない。"""

        title @= "Modelに保持する情報"
        level @= MUST
        related @= (MODELING_POLICY,)

    class SPEC_002:
        """Kindの「一種である」関係と、Modelが子要素を「含む」関係は別である。Kindの親子関係からModelのrole、Structureの継承、構成上の互換性を推論してはならない。"""

        title @= "分類と構成の独立性"
        level @= MUST

    class SPEC_003:
        """Kindには文字列IDを与え、根 `model` を除く各Kindはただ一つの親Kindを持つ。`KindIndex.is_a` はこの分類上の祖先関係だけを表す。Kindの分類IDから利用側が対応可否を決める。"""

        title @= "Kindの分類木"
        level @= MUST

    class SPEC_004:
        """StructureはKindから独立したIDと、宣言順のrole/shape定義を持つ。各Kindは0個または1個のStructureを参照する。複数のKindが同じStructureを参照してもよい。"""

        title @= "Structureの独立定義"
        level @= MUST

    class SPEC_005:
        """ライブラリの正規解析経路が生成するModelの各roleは参照Structureで宣言されたshapeに一致しなければならない。許容するshapeは `node`、`optional_node`、`nodes`、`text`、`optional_text`、`texts`、`scalar` の7種類に限り、未知のshapeは拒否する。宣言順と子Modelの順序を保持する。"""

        title @= "構成要素のshape"
        level @= MUST

    class SPEC_006:
        """FeatureはKindの分類木とは独立した構文上の特徴を表す。`async` および `generator` は規定済みのFunction/Method Kindに付与でき、`lazy` は `model.import.direct` と `model.import.from` にのみ付与できる。`lazy` はソースに明示されたキーワードの存在だけを表し、暗黙の遅延import設定や実際のモジュール初期化時刻は表さない。Featureの付与はPythonの非同期実行や遅延実行をシミュレートすることではない。"""

        title @= "Featureの位置付け"
        level @= MUST

    class SPEC_007:
        """`Model.parts()` は宣言順の `ModelPart` を返し、`Model.get(role)` は既存roleの値をそのまま返す。未定義roleの取得は `KeyError` とする。型付きアクセサの型・欠落に対する失敗条件は独立した契約で規定する。"""

        title @= "構造の取得"
        level @= MUST

    class SPEC_008:
        """`Model.walk()` は自己を先頭に、構成要素の宣言順で深さ優先に子Modelを辿る。パッケージの照合関係は構成木に混入させない。"""

        title @= "構成木の走査"
        level @= MUST

    class SPEC_009:
        """ModelとModelPartの構造的比較およびハッシュでは、保持するスカラーの値と具体的な型を区別する。例として `True`、`1`、`1.0` を同一視してはならない。"""

        title @= "スカラーの同一性"
        level @= MUST

    class SPEC_010:
        """ライブラリの正規解析経路は、Structure参照を持たない抽象KindからModelを構築してはならない。roleが0件の具体Structureを持つKindと、Structure参照自体を持たない抽象Kindは異なる。利用者による `Model(...)` の直接構築にはこの妥当性保証を適用しない。"""

        title @= "構造なしKindと検証"
        level @= MUST

    class SPEC_011:
        """Kind・Structure・Featureの定義は信頼済みのShikumi Python記述体を正本とし、PackageTreeStructureを検証してメモリ内のIndexを実現する。解析対象のPythonソースをKind記述体として実行してはならない。"""

        title @= "Kind記述体とIndex"
        level @= MUST

    class SPEC_012:
        """特定の変換先・業務ドメインの意味や対応可否を基本ModelのKind・Structureへ埋め込んではならない。ドメイン拡張情報の解釈と利用判断は利用側が担う。"""

        title @= "ドメイン意味の分離"
        level @= MUST_NOT

    class SPEC_013:
        """信頼済みShikumi記述体におけるKind・Structure・FeatureのID重複、未知の親・Structure参照、分類の巡回、不正なrole/shape、Featureの適用違反は拒否する。"""

        title @= "信頼済み記述体の検証"
        level @= MUST

    class SPEC_014:
        """`Model.get_node`、`get_nodes`、`get_name` は既存roleの値を型変換せず取得する。未定義のroleは `KeyError`、roleが存在しても要求した型でなければ `TypeError` とする。省略されたoptional roleの `None` も `TypeError` とし、欠落を含めて取得する場合は `get(role)` を使う。`get_nodes` は空のタプルを許容する。"""

        title @= "型付きアクセサの失敗契約"
        level @= MUST

    class SPEC_015:
        """Modelの構造的な等価性・ハッシュは、Kind、宣言順のroleと値、Feature、SourceSpanを反映する。SourceSpanはファイル名・モジュール名を保持しないため、異なるファイルから得た別個のModelでも構造と位置が一致すれば等しくなり得る。等しいModelは同じハッシュ値を持ち、辞書・集合では同じキーとして扱われる。構造的等価性と個々のModelインスタンスの同一性は区別する。ハッシュは各Modelインスタンスで初回の計算結果を遅延キャッシュし、同じインスタンスの2回目以降の呼び出しでは再利用する。初回計算は非再帰で行い、計算済みの子Modelのキャッシュも利用し、未計算の子孫Modelについては計算したハッシュをそれぞれのインスタンスに保存する。スカラー値の型に関する比較規則は別の規則に従い、元の数値リテラル表記は復元しない。"""

        title @= "構造的等価性に含む情報"
        level @= MUST

    class SPEC_016:
        """`kind_index()` が返すIndexは、`get`、`parent`、`is_a`、`all_kinds` による分類照会と、`structure_of`、`require_structure`、`get_structure`、`all_structures`、`all_features` による構造・Featureの照会を区別して提供する。`structure_of` の結果からKind親子関係によるStructure継承を推測してはならない。"""

        title @= "KindIndexによる照会"
        level @= MUST

    class SPEC_017:
        """`KindIndex.get` と `get_structure` は未登録IDを `KeyError` として拒否する。`parent` は根Kindで `None` を返し、`is_a` は同一Kindを祖先に含む。`structure_of` は抽象Kindで `None` を返すが、`require_structure` は同じ場合に `ValueError` とする。分類と構造の照会を混同しない。"""

        title @= "KindIndex照会の境界と失敗条件"
        level @= MUST

    class SPEC_018:
        """ライブラリの正規解析経路でModelへ適用するFeatureは既知のIDであり、対象KindがFeatureの許可された分類範囲に属さなければならない。同一Model内のFeature ID重複、未知のFeature ID、適用対象外のKindは拒否する。`validate_features` はこの構文上の妥当性を検証し、実行時の非同期処理を判定しない。"""

        title @= "Feature適用の検証条件"
        level @= MUST

    class SPEC_019:
        """`SourceSpan` はASTから取得可能な開始行・開始列・終了行・終了列をそのまま保持する。行番号は1始まり、列は0始まりのUTF-8バイトオフセットとする。4値を揃えて取得できないAST要素では `span=None` を許容する。ソース文字列中の文字インデックスや元のリテラル表記を復元した情報ではない。構成要素の列挙順はソース位置の非重複を保証せず、t-stringやf-stringのデバッグ指定子などでは、ASTに由来する文字列片と補間要素のスパンが重なることがある。この場合も位置を独自に補正しない。"""

        title @= "ソース位置の単位と欠落"
        level @= MUST

    class SPEC_020:
        """`kind_index()` は検証済みのメモリ上のIndexを再利用する。公開されたKind・Structure・Featureの照会結果は不変のデータであり、分類木やrole定義を変更するための公開編集APIを設けない。"""

        title @= "検証済みIndexの再利用と公開操作"
        level @= MUST

    class SPEC_021:
        """`Model` は解析APIが返す結果を読み取るための公開型であり、利用者による直接の `Model(...)` 構築はサポートしない。Kind・Structure・Featureの整合性保証は、正規の `parse_*` / `inspect_*` 解析経路でライブラリが生成したModelに適用する。利用者が独自に構築したModelの妥当性、そのModelを他のAPIに渡したときの動作は保証しない。公開されたコンストラクタの内部引数は構築APIの契約に含めない。"""

        title @= "解析結果としてのModelと直接構築の保証境界"
        level @= MUST
        related @= (MODELING_POLICY,)

    class SPEC_022:
        """`Model` と `ModelPart` の `repr` は診断用の短い概要を提供し、子Modelの構成を再帰的に展開しない。ModelはKind ID、取得可能な位置、Feature、直接のroleとその値の概要を示し、ModelPartはroleと値の概要を示す。子ModelはKind IDだけ、タプルは要素数だけを示し、長い値・多数の要素は省略する。通常の解析結果に対する各文字列表現は有限の長さに制限し、完全な構成の復元、文字列の一意性、`eval` による再構築を保証しない。完全な情報はアクセサ・`walk()` で取得する。`deepcopy`・`pickle` の深い構成木への対応は本規則の対象外とする。"""

        title @= "ModelとModelPartの非再帰的な診断用repr"
        level @= MUST

    class SPEC_023:
        """`Model.get_scalar(role, expected_type=None)` はスカラー値を型変換せず取得し、Modelやタプルなどの非スカラーを `TypeError` とする。未定義roleは `KeyError` とする。型を指定した場合は実際のPython型の同一性で検査し、`bool` と `int` を区別する。NoneとEllipsisもスカラーとして許容する。optional roleの不在を区別したい場合は既存の `get(role)` とStructureのrole契約を使用する。"""

        title @= "スカラーの型付き取得"
        level @= MUST

    class SPEC_024:
        """`format_model_tree(model, *, max_depth=8, max_nodes=200, max_chars=12000)` はModelの構成木を診断用テキストとして反復的に表示する。Kind ID、role、直接のスカラー概要、取得可能なスパンとFeatureを表示し、子Modelは指定された深さ・ノード数・文字数の範囲で辿る。深さの基準はrootが0、ノード数にはrootを含める。max_depthが負、max_nodesが1未満、max_charsが4未満の場合はValueErrorとする。文字数上限を超えず、表示は完全なシリアライズ・Modelの同一性判定に使わない。`repr` の契約は変更しない。"""

        title @= "制限付きModel構成木の診断表示"
        level @= MUST
