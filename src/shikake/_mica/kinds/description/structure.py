"""Auxiliary Model roles, which are neither calls nor values themselves."""

from ..regulation import kind_id, parent_id, structure_ref


class StructuralPart:
    kind_id @= "model.structural_part"
    parent_id @= "model"


class KeywordArgument:
    kind_id @= "model.structural_part.keyword_argument"
    structure_ref @= "structural_part_keyword_argument"
    parent_id @= "model.structural_part"


class StarredArgument:
    kind_id @= "model.structural_part.starred_argument"
    structure_ref @= "expression_value"
    parent_id @= "model.structural_part"


class StarredTarget:
    """The written * element in a structural binding target."""

    kind_id @= "model.structural_part.starred_target"
    structure_ref @= "expression_value"
    parent_id @= "model.structural_part"


class DictionaryEntry:
    kind_id @= "model.structural_part.dictionary_entry"
    structure_ref @= "structural_part_dictionary_entry"
    parent_id @= "model.structural_part"


class FormattedField:
    """An embedded expression and its written f-string conversion/format."""

    kind_id @= "model.structural_part.formatted_field"
    structure_ref @= "formatted_field"
    parent_id @= "model.structural_part"


class TemplateInterpolation:
    """Interpolation expression, source text, conversion, and format spec."""

    kind_id @= "model.structural_part.template_interpolation"
    structure_ref @= "template_interpolation"
    parent_id @= "model.structural_part"


class ComparisonStep:
    """One written operator and its right-hand expression in a comparison chain."""

    kind_id @= "model.structural_part.comparison_step"
    structure_ref @= "structural_part_comparison_step"
    parent_id @= "model.structural_part"


class BranchPath:
    """One ordered branch route with its original selector and contents."""

    kind_id @= "model.structural_part.branch_path"
    structure_ref @= "structural_part_branch_path"
    parent_id @= "model.structural_part"


class ExceptionHandler:
    kind_id @= "model.structural_part.exception_handler"
    structure_ref @= "structural_part_exception_handler"
    parent_id @= "model.structural_part"


class MappingPatternEntry:
    kind_id @= "model.structural_part.mapping_pattern_entry"
    structure_ref @= "structural_part_mapping_pattern_entry"
    parent_id @= "model.structural_part"


class NamedPattern:
    kind_id @= "model.structural_part.named_pattern"
    structure_ref @= "structural_part_named_pattern"
    parent_id @= "model.structural_part"


class ContextEntry:
    """One context expression and an optional written `as` binding."""

    kind_id @= "model.structural_part.context_entry"
    structure_ref @= "structural_part_context_entry"
    parent_id @= "model.structural_part"


class ComprehensionClause:
    """One ordered comprehension generator and its own ordered filters."""

    kind_id @= "model.structural_part.comprehension_clause"
    structure_ref @= "comprehension_clause"
    parent_id @= "model.structural_part"
