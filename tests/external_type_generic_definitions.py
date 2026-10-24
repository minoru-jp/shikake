"""Trusted Shikumi description of Type and Generic interfaces."""

from shikake.external import (
    ImportedGeneric,
    ImportedType,
    Role,
    emit,
    kind_id,
    match_generic,
    match_type,
    parent_id,
    part,
    slot,
    structure_id,
    structure_ref,
)


class TypeStructure:
    structure_id @= "demo.type.structure"


class TypeKind:
    kind_id @= "demo.type"
    parent_id @= "model.value"
    structure_ref @= "demo.type.structure"


class TypeUse:
    match_type @= ImportedType("demo.kinds:int32")
    emit @= "demo.type"


class ArrayStructure:
    structure_id @= "demo.array.structure"
    part @= Role("item", "node")
    part @= Role("length", "node")


class ArrayKind:
    kind_id @= "demo.array"
    parent_id @= "model.value"
    structure_ref @= "demo.array.structure"


class ArrayUse:
    match_generic @= ImportedGeneric("demo.kinds:Array")
    emit @= "demo.array"
    slot @= "item"
    slot @= "length"
