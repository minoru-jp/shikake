"""Trusted external Feature declarations and explicit model attachments."""

from shikake.external import (
    Argument,
    ImportedCall,
    ImportedGeneric,
    ImportedType,
    Role,
    apply_feature,
    bind,
    emit,
    feature_allowed,
    feature_id,
    kind_id,
    match,
    match_generic,
    match_type,
    parent_id,
    part,
    slot,
    structure_id,
    structure_ref,
)


class ExternalTag:
    feature_id @= "demo.tag"
    feature_allowed @= "demo.parent"


class Parent:
    kind_id @= "demo.parent"
    parent_id @= "model.value"


class CallStructure:
    structure_id @= "demo.call.layout"
    part @= Role("value", "node")


class CallKind:
    kind_id @= "demo.call"
    parent_id @= "demo.parent"
    structure_ref @= "demo.call.layout"


class CallUse:
    match @= ImportedCall("sample.helpers:do_work")
    emit @= "demo.call"
    bind @= Argument("value", 0, "value")
    apply_feature @= "demo.tag"


class TypeStructure:
    structure_id @= "demo.type.layout"


class TypeKind:
    kind_id @= "demo.type"
    parent_id @= "demo.parent"
    structure_ref @= "demo.type.layout"


class TypeUse:
    match_type @= ImportedType("sample.helpers:TaggedType")
    emit @= "demo.type"
    apply_feature @= "demo.tag"


class GenericStructure:
    structure_id @= "demo.generic.layout"
    part @= Role("element", "node")


class GenericKind:
    kind_id @= "demo.generic"
    parent_id @= "demo.parent"
    structure_ref @= "demo.generic.layout"


class GenericUse:
    match_generic @= ImportedGeneric("sample.helpers:TaggedArray")
    emit @= "demo.generic"
    slot @= "element"
    apply_feature @= "demo.tag"
