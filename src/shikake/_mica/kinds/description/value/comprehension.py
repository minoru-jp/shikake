"""Value constructions with ordered iteration/filter clauses, not loop statements."""

from ...regulation import kind_id, parent_id, structure_ref


class Comprehension:
    """Shared subject: build a value from clauses without lowering them."""

    kind_id @= "model.value.comprehension"
    parent_id @= "model.value"


class ListConstruction:
    kind_id @= "model.value.comprehension.list"
    structure_ref @= "comprehension_elements"
    parent_id @= "model.value.comprehension"


class SetConstruction:
    kind_id @= "model.value.comprehension.set"
    structure_ref @= "comprehension_elements"
    parent_id @= "model.value.comprehension"


class DictConstruction:
    kind_id @= "model.value.comprehension.dict"
    structure_ref @= "value_comprehension_dict"
    parent_id @= "model.value.comprehension"


class DictUnpackingConstruction:
    """PEP 798 dictionary comprehension that expands a mapping."""

    kind_id @= "model.value.comprehension.dict.unpacking"
    structure_ref @= "value_comprehension_dict_unpacking"
    parent_id @= "model.value.comprehension.dict"


class GeneratorConstruction:
    kind_id @= "model.value.comprehension.generator"
    structure_ref @= "comprehension_elements"
    parent_id @= "model.value.comprehension"
