"""Collection-value kinds."""

from ...regulation import kind_id, parent_id, structure_ref


class Collection:
    kind_id @= "model.value.collection"
    parent_id @= "model.value"


class Tuple:
    kind_id @= "model.value.collection.tuple"
    structure_ref @= "ordered_elements"
    parent_id @= "model.value.collection"


class List:
    kind_id @= "model.value.collection.list"
    structure_ref @= "ordered_elements"
    parent_id @= "model.value.collection"


class Set:
    kind_id @= "model.value.collection.set"
    structure_ref @= "ordered_elements"
    parent_id @= "model.value.collection"


class Dictionary:
    kind_id @= "model.value.collection.dict"
    structure_ref @= "value_collection_dict"
    parent_id @= "model.value.collection"
