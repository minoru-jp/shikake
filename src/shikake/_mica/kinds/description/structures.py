"""Independent, ordered Structure definitions for concrete Model parts.

No Kind ancestry or Python execution semantics are declared here.
"""

from ..regulation import PartContract as Role
from ..regulation import part, structure_id


class BinaryOperands:
    structure_id @= "binary_operands"
    part @= Role("left", "node")
    part @= Role("right", "node")


class AnnotatedTarget:
    """Annotated assignment whose target is not a bare simple name."""

    structure_id @= "annotated_target"
    part @= Role("target", "node")
    part @= Role("annotation", "node")
    part @= Role("value", "optional_node")
    part @= Role("simple", "scalar")


class Assertion:
    structure_id @= "assertion"
    part @= Role("condition", "node")
    part @= Role("message", "optional_node")


class BranchPaths:
    structure_id @= "branch_paths"
    part @= Role("subject", "optional_node")
    part @= Role("paths", "nodes")


class CallArguments:
    structure_id @= "call_arguments"
    part @= Role("callee", "node")
    part @= Role("arguments", "nodes")


class CallableDefinition:
    structure_id @= "callable_definition"
    part @= Role("name", "text")
    part @= Role("parameters", "nodes")
    part @= Role("type_parameters", "nodes")
    part @= Role("decorators", "nodes")
    part @= Role("returns", "optional_node")
    part @= Role("body", "node")


class ChainedComparison:
    structure_id @= "chained_comparison"
    part @= Role("left", "node")
    part @= Role("comparisons", "nodes")


class ClassDefinition:
    structure_id @= "class_definition"
    part @= Role("name", "text")
    part @= Role("type_parameters", "nodes")
    part @= Role("bases", "nodes")
    part @= Role("keywords", "nodes")
    part @= Role("decorators", "nodes")
    part @= Role("body", "node")


class ComprehensionClause:
    structure_id @= "comprehension_clause"
    part @= Role("target", "node")
    part @= Role("iterable", "node")
    part @= Role("filters", "nodes")
    part @= Role("is_async", "scalar")


class ComprehensionElements:
    structure_id @= "comprehension_elements"
    part @= Role("element", "node")
    part @= Role("clauses", "nodes")


class ContextBlock:
    structure_id @= "context_block"
    part @= Role("contexts", "nodes")
    part @= Role("body", "node")


class ExceptionHandling:
    structure_id @= "exception_handling"
    part @= Role("body", "node")
    part @= Role("handlers", "nodes")
    part @= Role("else_block", "optional_node")
    part @= Role("finally_block", "optional_node")
    part @= Role("grouped", "scalar")


class ExpressionValue:
    structure_id @= "expression_value"
    part @= Role("value", "node")


class FunctionExpression:
    structure_id @= "function_expression"
    part @= Role("parameters", "nodes")
    part @= Role("body", "node")


class FormattedField:
    structure_id @= "formatted_field"
    part @= Role("value", "node")
    part @= Role("conversion", "optional_text")
    part @= Role("format_spec", "optional_node")


class TemplateInterpolation:
    structure_id @= "template_interpolation"
    part @= Role("value", "node")
    part @= Role("expression_text", "optional_text")
    part @= Role("conversion", "optional_text")
    part @= Role("format_spec", "optional_node")


class DeclaredNames:
    structure_id @= "declared_names"
    part @= Role("names", "texts")


class ImportAlias:
    structure_id @= "import_alias"
    part @= Role("name", "text")
    part @= Role("asname", "optional_text")


class ImportDirect:
    structure_id @= "import_direct"
    part @= Role("names", "nodes")


class ImportFrom:
    structure_id @= "import_from"
    part @= Role("module", "optional_text")
    part @= Role("level", "scalar")
    part @= Role("names", "nodes")


class IterationBlocks:
    structure_id @= "iteration_blocks"
    part @= Role("binding", "optional_node")
    part @= Role("source", "optional_node")
    part @= Role("condition", "optional_node")
    part @= Role("body", "node")
    part @= Role("else_block", "optional_node")


class ModuleDefinition:
    structure_id @= "module_definition"
    part @= Role("name", "text")
    part @= Role("body", "nodes")


class MultipleTargetsValue:
    structure_id @= "multiple_targets_value"
    part @= Role("targets", "nodes")
    part @= Role("value", "node")


class OptionalName:
    structure_id @= "optional_name"
    part @= Role("name", "optional_text")


class OptionalValue:
    structure_id @= "optional_value"
    part @= Role("value", "optional_node")


class OrderedElements:
    structure_id @= "ordered_elements"
    part @= Role("elements", "nodes")


class OrderedTargets:
    structure_id @= "ordered_targets"
    part @= Role("targets", "nodes")


class OrderedValues:
    structure_id @= "ordered_values"
    part @= Role("values", "nodes")


class PackageDefinition:
    structure_id @= "package_definition"
    part @= Role("name", "text")
    part @= Role("modules", "nodes")


class ParameterDefinition:
    structure_id @= "parameter_definition"
    part @= Role("name", "text")
    part @= Role("annotation", "optional_node")
    part @= Role("category", "text")
    part @= Role("default", "optional_node")


class PatternAlias:
    structure_id @= "pattern_alias"
    part @= Role("pattern", "node")
    part @= Role("name", "optional_text")


class PatternAlternative:
    structure_id @= "pattern_alternative"
    part @= Role("alternatives", "nodes")


class PatternClass:
    structure_id @= "pattern_class"
    part @= Role("type", "node")
    part @= Role("positional", "nodes")
    part @= Role("keywords", "nodes")


class PatternMapping:
    structure_id @= "pattern_mapping"
    part @= Role("entries", "nodes")
    part @= Role("rest", "optional_text")


class RaisedException:
    structure_id @= "raised_exception"
    part @= Role("exception", "optional_node")
    part @= Role("cause", "optional_node")


class RequiredName:
    structure_id @= "required_name"
    part @= Role("name", "text")


class ScalarValue:
    structure_id @= "scalar_value"
    part @= Role("value", "scalar")


class SelectedValue:
    structure_id @= "selected_value"
    part @= Role("condition", "node")
    part @= Role("when_true", "node")
    part @= Role("when_false", "node")


class SingleTargetValue:
    structure_id @= "single_target_value"
    part @= Role("target", "node")
    part @= Role("value", "node")


class SliceBounds:
    structure_id @= "slice_bounds"
    part @= Role("start", "optional_node")
    part @= Role("stop", "optional_node")
    part @= Role("step", "optional_node")


class StatementsBlock:
    structure_id @= "statements_block"
    part @= Role("statements", "nodes")


class StringFragments:
    structure_id @= "string_fragments"
    part @= Role("parts", "nodes")


class StructuralPartBranchPath:
    structure_id @= "structural_part_branch_path"
    part @= Role("condition", "optional_node")
    part @= Role("pattern", "optional_node")
    part @= Role("guard", "optional_node")
    part @= Role("body", "node")


class StructuralPartComparisonStep:
    structure_id @= "structural_part_comparison_step"
    part @= Role("operator", "text")
    part @= Role("right", "node")


class StructuralPartContextEntry:
    structure_id @= "structural_part_context_entry"
    part @= Role("expression", "node")
    part @= Role("target", "optional_node")


class StructuralPartDictionaryEntry:
    structure_id @= "structural_part_dictionary_entry"
    part @= Role("key", "optional_node")
    part @= Role("value", "node")


class StructuralPartExceptionHandler:
    structure_id @= "structural_part_exception_handler"
    part @= Role("exception", "optional_node")
    part @= Role("name", "optional_text")
    part @= Role("body", "node")


class StructuralPartKeywordArgument:
    structure_id @= "structural_part_keyword_argument"
    part @= Role("name", "optional_text")
    part @= Role("value", "node")


class StructuralPartMappingPatternEntry:
    structure_id @= "structural_part_mapping_pattern_entry"
    part @= Role("key", "node")
    part @= Role("pattern", "node")


class StructuralPartNamedPattern:
    structure_id @= "structural_part_named_pattern"
    part @= Role("name", "text")
    part @= Role("pattern", "node")


class UnaryOperand:
    structure_id @= "unary_operand"
    part @= Role("operand", "node")


class ValueAccessAttribute:
    structure_id @= "value_access_attribute"
    part @= Role("target", "node")
    part @= Role("attribute", "text")


class ValueAccessIndex:
    structure_id @= "value_access_index"
    part @= Role("target", "node")
    part @= Role("index", "node")


class ValueCollectionDict:
    structure_id @= "value_collection_dict"
    part @= Role("entries", "nodes")


class ValueComprehensionDictUnpacking:
    """Python 3.15 PEP 798 mapping expansion has no separate value."""

    structure_id @= "value_comprehension_dict_unpacking"
    part @= Role("mapping", "node")
    part @= Role("clauses", "nodes")


class ValueComprehensionDict:
    structure_id @= "value_comprehension_dict"
    part @= Role("key", "node")
    part @= Role("value", "node")
    part @= Role("clauses", "nodes")


class VariableDefinition:
    structure_id @= "variable_definition"
    part @= Role("name", "text")
    part @= Role("annotation", "node")
    part @= Role("initializer", "optional_node")


class Empty:
    """A source element with no structural parts (e.g. pass)."""

    structure_id @= "empty"


class TypeAliasDefinition:
    structure_id @= "type_alias_definition"
    part @= Role("name", "text")
    part @= Role("type_parameters", "nodes")
    part @= Role("value", "node")


class TypeVariableParameter:
    structure_id @= "type_variable_parameter"
    part @= Role("name", "text")
    part @= Role("restriction", "optional_node")
    part @= Role("default", "optional_node")


class VariadicTypeParameter:
    structure_id @= "variadic_type_parameter"
    part @= Role("name", "text")
    part @= Role("default", "optional_node")
