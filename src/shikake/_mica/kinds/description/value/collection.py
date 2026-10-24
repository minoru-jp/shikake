"""Generalized collection-construction kinds."""

from ...regulation import kind_id, parent_id, structure_ref


class Collection:
    kind_id @= "model.value.collection"
    parent_id @= "model.value"


class Sequence:
    kind_id @= "model.value.collection.sequence"
    structure_ref @= "collection_construction"
    parent_id @= "model.value.collection"


class Mapping:
    kind_id @= "model.value.collection.mapping"
    structure_ref @= "collection_construction"
    parent_id @= "model.value.collection"


class Set:
    kind_id @= "model.value.collection.set"
    structure_ref @= "collection_construction"
    parent_id @= "model.value.collection"
