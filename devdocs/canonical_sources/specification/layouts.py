"""各Structureと具体Kindの正確なrole/shape対応の正本仕様。"""

from shikumi_devdoc.fields.specification import MUST, detail, level, related
from shikumi_devdoc.norms.common import canonical_source, summary
from shikumi_devdoc.norms.document import title

from devdocs.canonical_sources.specification.model import MODEL


@summary(
    "公開Kindの構成形状。Structureのroleとshapeおよび直接参照するKindを独立した規則として列挙。"
)
@canonical_source(
    "{{project.name}}: Structure・Kind対応表",
    filename="layouts.md",
    order=15,
    merge_policy="all",
    heading="identity",
)
class LAYOUTS:
    """具体Kindのrole/shapeを定める。Kindの分類上の親からStructureを継承しない。"""

    class SPEC_001:
        """Structure `annotated_target` のrole/shapeを記述順に保持する。"""

        title @= "Structure: annotated_target"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= (
            "roles: target:node, annotation:node, value:optional_node, simple:scalar"
        )
        detail @= "kinds: model.statement.assignment.annotated"

    class SPEC_002:
        """Structure `assertion` のrole/shapeを記述順に保持する。"""

        title @= "Structure: assertion"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: condition:node, message:optional_node"
        detail @= "kinds: model.statement.assertion"

    class SPEC_003:
        """Structure `binary_operands` のrole/shapeを記述順に保持する。"""

        title @= "Structure: binary_operands"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: left:node, right:node"
        detail @= "kinds: model.value.operation.addition, model.value.operation.subtraction, model.value.operation.multiplication, model.value.operation.matrix_multiplication, model.value.operation.division, model.value.operation.floor_division, model.value.operation.modulo, model.value.operation.power, model.value.operation.left_shift, model.value.operation.right_shift, model.value.operation.bitwise_and, model.value.operation.bitwise_or, model.value.operation.bitwise_xor, model.value.operation.comparison.equal, model.value.operation.comparison.not_equal, model.value.operation.comparison.less, model.value.operation.comparison.less_equal, model.value.operation.comparison.greater, model.value.operation.comparison.greater_equal, model.value.operation.comparison.is, model.value.operation.comparison.is_not, model.value.operation.comparison.in, model.value.operation.comparison.not_in"

    class SPEC_004:
        """Structure `branch_paths` のrole/shapeを記述順に保持する。"""

        title @= "Structure: branch_paths"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: subject:optional_node, paths:nodes"
        detail @= "kinds: model.statement.branch"

    class SPEC_005:
        """Structure `call_arguments` のrole/shapeを記述順に保持する。"""

        title @= "Structure: call_arguments"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: callee:node, arguments:nodes"
        detail @= "kinds: model.value.call"

    class SPEC_006:
        """Structure `callable_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: callable_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, parameters:nodes, type_parameters:nodes, decorators:nodes, returns:optional_node, body:node"
        detail @= "kinds: model.definition.function, model.definition.method"

    class SPEC_007:
        """Structure `chained_comparison` のrole/shapeを記述順に保持する。"""

        title @= "Structure: chained_comparison"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: left:node, comparisons:nodes"
        detail @= "kinds: model.value.operation.comparison.chained"

    class SPEC_008:
        """Structure `class_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: class_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, type_parameters:nodes, bases:nodes, keywords:nodes, decorators:nodes, body:node"
        detail @= "kinds: model.definition.class"

    class SPEC_009:
        """Structure `comprehension_clause` のrole/shapeを記述順に保持する。"""

        title @= "Structure: comprehension_clause"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: target:node, iterable:node, filters:nodes, is_async:scalar"
        detail @= "kinds: model.structural_part.comprehension_clause"

    class SPEC_010:
        """Structure `comprehension_elements` のrole/shapeを記述順に保持する。"""

        title @= "Structure: comprehension_elements"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: element:node, clauses:nodes"
        detail @= "kinds: model.value.comprehension.list, model.value.comprehension.set, model.value.comprehension.generator"

    class SPEC_011:
        """Structure `context_block` のrole/shapeを記述順に保持する。"""

        title @= "Structure: context_block"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: contexts:nodes, body:node"
        detail @= "kinds: model.statement.control.context_block"

    class SPEC_012:
        """Structure `declared_names` のrole/shapeを記述順に保持する。"""

        title @= "Structure: declared_names"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: names:texts"
        detail @= "kinds: model.statement.scope_declaration.global, model.statement.scope_declaration.nonlocal"

    class SPEC_013:
        """Structure `empty` のrole/shapeを記述順に保持する。"""

        title @= "Structure: empty"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: (none)"
        detail @= "kinds: model.statement.break, model.statement.continue, model.pattern.wildcard, model.statement.pass"

    class SPEC_014:
        """Structure `exception_handling` のrole/shapeを記述順に保持する。"""

        title @= "Structure: exception_handling"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: body:node, handlers:nodes, else_block:optional_node, finally_block:optional_node, grouped:scalar"
        detail @= "kinds: model.statement.control.exception_handling"

    class SPEC_015:
        """Structure `expression_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: expression_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: value:node"
        detail @= "kinds: model.pattern.value, model.pattern.singleton, model.statement.expression, model.structural_part.starred_argument, model.structural_part.starred_target, model.value.yield_from, model.value.await, model.value.starred_expansion"

    class SPEC_016:
        """Structure `formatted_field` のrole/shapeを記述順に保持する。"""

        title @= "Structure: formatted_field"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= (
            "roles: value:node, conversion:optional_text, format_spec:optional_node"
        )
        detail @= "kinds: model.structural_part.formatted_field"

    class SPEC_017:
        """Structure `function_expression` のrole/shapeを記述順に保持する。"""

        title @= "Structure: function_expression"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: parameters:nodes, body:node"
        detail @= "kinds: model.value.function_expression"

    class SPEC_018:
        """Structure `import_alias` のrole/shapeを記述順に保持する。"""

        title @= "Structure: import_alias"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, asname:optional_text"
        detail @= "kinds: model.import.alias"

    class SPEC_019:
        """Structure `import_direct` のrole/shapeを記述順に保持する。"""

        title @= "Structure: import_direct"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: names:nodes"
        detail @= "kinds: model.import.direct"

    class SPEC_020:
        """Structure `import_from` のrole/shapeを記述順に保持する。"""

        title @= "Structure: import_from"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: module:optional_text, level:scalar, names:nodes"
        detail @= "kinds: model.import.from"

    class SPEC_021:
        """Structure `iteration_blocks` のrole/shapeを記述順に保持する。"""

        title @= "Structure: iteration_blocks"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: binding:optional_node, source:optional_node, condition:optional_node, body:node, else_block:optional_node"
        detail @= "kinds: model.statement.control.iteration"

    class SPEC_022:
        """Structure `module_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: module_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, body:nodes"
        detail @= "kinds: model.module"

    class SPEC_023:
        """Structure `multiple_targets_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: multiple_targets_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: targets:nodes, value:node"
        detail @= "kinds: model.statement.assignment"

    class SPEC_024:
        """Structure `optional_name` のrole/shapeを記述順に保持する。"""

        title @= "Structure: optional_name"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:optional_text"
        detail @= "kinds: model.pattern.star"

    class SPEC_025:
        """Structure `optional_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: optional_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: value:optional_node"
        detail @= "kinds: model.statement.return, model.value.yield"

    class SPEC_026:
        """Structure `ordered_elements` のrole/shapeを記述順に保持する。"""

        title @= "Structure: ordered_elements"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: elements:nodes"
        detail @= "kinds: model.pattern.sequence"

    class SPEC_027:
        """Structure `ordered_targets` のrole/shapeを記述順に保持する。"""

        title @= "Structure: ordered_targets"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: targets:nodes"
        detail @= "kinds: model.statement.deletion"

    class SPEC_028:
        """Structure `ordered_values` のrole/shapeを記述順に保持する。"""

        title @= "Structure: ordered_values"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: values:nodes"
        detail @= "kinds: model.value.operation.logical, model.value.operation.logical.and, model.value.operation.logical.or"

    class SPEC_029:
        """Structure `package_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: package_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, modules:nodes"
        detail @= "kinds: model.package"

    class SPEC_030:
        """Structure `parameter_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: parameter_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, annotation:optional_node, category:text, default:optional_node"
        detail @= "kinds: model.definition.parameter"

    class SPEC_031:
        """Structure `pattern_alias` のrole/shapeを記述順に保持する。"""

        title @= "Structure: pattern_alias"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: pattern:node, name:optional_text"
        detail @= "kinds: model.pattern.alias"

    class SPEC_032:
        """Structure `pattern_alternative` のrole/shapeを記述順に保持する。"""

        title @= "Structure: pattern_alternative"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: alternatives:nodes"
        detail @= "kinds: model.pattern.alternative"

    class SPEC_033:
        """Structure `pattern_class` のrole/shapeを記述順に保持する。"""

        title @= "Structure: pattern_class"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: type:node, positional:nodes, keywords:nodes"
        detail @= "kinds: model.pattern.class"

    class SPEC_034:
        """Structure `pattern_mapping` のrole/shapeを記述順に保持する。"""

        title @= "Structure: pattern_mapping"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: entries:nodes, rest:optional_text"
        detail @= "kinds: model.pattern.mapping"

    class SPEC_035:
        """Structure `raised_exception` のrole/shapeを記述順に保持する。"""

        title @= "Structure: raised_exception"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: exception:optional_node, cause:optional_node"
        detail @= "kinds: model.statement.raise"

    class SPEC_036:
        """Structure `required_name` のrole/shapeを記述順に保持する。"""

        title @= "Structure: required_name"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text"
        detail @= "kinds: model.pattern.capture, model.value.named"

    class SPEC_037:
        """Structure `scalar_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: scalar_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: value:scalar"
        detail @= "kinds: model.value.literal, model.value.literal.special, model.value.literal.special.none, model.value.literal.special.ellipsis"

    class SPEC_038:
        """Structure `selected_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: selected_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: condition:node, when_true:node, when_false:node"
        detail @= "kinds: model.value.selection"

    class SPEC_039:
        """Structure `single_target_value` のrole/shapeを記述順に保持する。"""

        title @= "Structure: single_target_value"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: target:node, value:node"
        detail @= "kinds: model.statement.assignment.augmented, model.statement.assignment.augmented.addition, model.statement.assignment.augmented.subtraction, model.statement.assignment.augmented.multiplication, model.statement.assignment.augmented.matrix_multiplication, model.statement.assignment.augmented.division, model.statement.assignment.augmented.floor_division, model.statement.assignment.augmented.modulo, model.statement.assignment.augmented.power, model.statement.assignment.augmented.left_shift, model.statement.assignment.augmented.right_shift, model.statement.assignment.augmented.bitwise_and, model.statement.assignment.augmented.bitwise_or, model.statement.assignment.augmented.bitwise_xor, model.value.binding"

    class SPEC_040:
        """Structure `slice_bounds` のrole/shapeを記述順に保持する。"""

        title @= "Structure: slice_bounds"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: start:optional_node, stop:optional_node, step:optional_node"
        detail @= "kinds: model.value.slice"

    class SPEC_041:
        """Structure `statements_block` のrole/shapeを記述順に保持する。"""

        title @= "Structure: statements_block"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: statements:nodes"
        detail @= "kinds: model.statement.block"

    class SPEC_042:
        """Structure `string_fragments` のrole/shapeを記述順に保持する。"""

        title @= "Structure: string_fragments"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: parts:nodes"
        detail @= "kinds: model.value.interpolated_string, model.value.template_string"

    class SPEC_043:
        """Structure `structural_part_branch_path` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_branch_path"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: condition:optional_node, pattern:optional_node, guard:optional_node, body:node"
        detail @= "kinds: model.structural_part.branch_path"

    class SPEC_044:
        """Structure `structural_part_comparison_step` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_comparison_step"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: operator:text, right:node"
        detail @= "kinds: model.structural_part.comparison_step"

    class SPEC_045:
        """Structure `structural_part_context_entry` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_context_entry"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: expression:node, target:optional_node"
        detail @= "kinds: model.structural_part.context_entry"

    class SPEC_046:
        """Structure `structural_part_dictionary_entry` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_dictionary_entry"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: key:optional_node, value:node"
        detail @= "kinds: model.structural_part.dictionary_entry"

    class SPEC_047:
        """Structure `structural_part_exception_handler` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_exception_handler"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: exception:optional_node, name:optional_text, body:node"
        detail @= "kinds: model.structural_part.exception_handler"

    class SPEC_048:
        """Structure `structural_part_keyword_argument` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_keyword_argument"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:optional_text, value:node"
        detail @= "kinds: model.structural_part.keyword_argument"

    class SPEC_049:
        """Structure `structural_part_mapping_pattern_entry` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_mapping_pattern_entry"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: key:node, pattern:node"
        detail @= "kinds: model.structural_part.mapping_pattern_entry"

    class SPEC_050:
        """Structure `structural_part_named_pattern` のrole/shapeを記述順に保持する。"""

        title @= "Structure: structural_part_named_pattern"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, pattern:node"
        detail @= "kinds: model.structural_part.named_pattern"

    class SPEC_051:
        """Structure `type_alias_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: type_alias_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, type_parameters:nodes, value:node"
        detail @= "kinds: model.definition.type_alias"

    class SPEC_052:
        """Structure `type_variable_parameter` のrole/shapeを記述順に保持する。"""

        title @= "Structure: type_variable_parameter"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, restriction:optional_node, default:optional_node"
        detail @= "kinds: model.definition.type_parameter.type_variable"

    class SPEC_053:
        """Structure `unary_operand` のrole/shapeを記述順に保持する。"""

        title @= "Structure: unary_operand"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: operand:node"
        detail @= "kinds: model.value.operation.unary, model.value.operation.not, model.value.operation.positive, model.value.operation.negative, model.value.operation.bitwise_invert"

    class SPEC_054:
        """Structure `value_access_attribute` のrole/shapeを記述順に保持する。"""

        title @= "Structure: value_access_attribute"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: target:node, attribute:text"
        detail @= "kinds: model.value.access.attribute"

    class SPEC_055:
        """Structure `value_access_index` のrole/shapeを記述順に保持する。"""

        title @= "Structure: value_access_index"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: target:node, index:node"
        detail @= "kinds: model.value.access.index"

    class SPEC_056:
        """Collectionの共通構築情報と入力Model列を保持する。"""

        title @= "Structure: collection_construction"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: construction:scalar, immutable:scalar, inputs:nodes"
        detail @= "kinds: model.value.collection.sequence, model.value.collection.mapping, model.value.collection.set"

    class SPEC_057:
        """Structure `value_comprehension_dict` のrole/shapeを記述順に保持する。"""

        title @= "Structure: value_comprehension_dict"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: key:node, value:node, clauses:nodes"
        detail @= "kinds: model.value.comprehension.dict"

    class SPEC_058:
        """Structure `variable_definition` のrole/shapeを記述順に保持する。"""

        title @= "Structure: variable_definition"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, annotation:node, initializer:optional_node"
        detail @= "kinds: model.definition.variable"

    class SPEC_059:
        """Structure `variadic_type_parameter` のrole/shapeを記述順に保持する。"""

        title @= "Structure: variadic_type_parameter"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: name:text, default:optional_node"
        detail @= "kinds: model.definition.type_parameter.type_variable_tuple, model.definition.type_parameter.parameter_specification"

    class SPEC_060:
        """Structureを直接持たない抽象Kindの集合。"""

        title @= "抽象Kindの一覧"
        level @= MUST
        related @= (MODEL.SPEC_010,)
        detail @= "kinds: model.statement.control, model, model.definition, model.definition.type_parameter, model.import, model.pattern, model.statement, model.statement.scope_declaration, model.structural_part, model.value.access, model.value, model.value.collection, model.value.comprehension, model.value.operation, model.value.operation.comparison"

    class SPEC_061:
        """Structure `template_interpolation` はt-stringの補間式、原文、変換指定、書式指定を保持する。"""

        title @= "Structure: template_interpolation"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: value:node, expression_text:optional_text, conversion:optional_text, format_spec:optional_node"
        detail @= "kinds: model.structural_part.template_interpolation"

    class SPEC_062:
        """Python 3.15 PEP 798の辞書展開付き内包表記専用Structureを定義する。値が存在しない形を、通常のkey/value内包表記と混同しない。"""

        title @= "Structure: value_comprehension_dict_unpacking"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: mapping:node, clauses:nodes"
        detail @= "kinds: model.value.comprehension.dict.unpacking"

    class SPEC_063:
        """代入先のTuple/Listは構築式ではなく専用のターゲット形状で表す。"""

        title @= "Structure: target_sequence"
        level @= MUST
        related @= (MODEL.SPEC_004, MODEL.SPEC_005)
        detail @= "roles: spelling:scalar, elements:nodes"
        detail @= "kinds: model.structural_part.sequence_target"
