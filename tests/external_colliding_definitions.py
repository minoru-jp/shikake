"""Trusted fixture declaring two distinct spellings of one matcher lookup key."""

from shikake.external import (
    ImportedCall,
    emit,
    kind_id,
    match,
    parent_id,
    structure_id,
    structure_ref,
)


class Shape:
    structure_id @= "test.collision.shape"


class Kind:
    kind_id @= "ext.collision"
    parent_id @= "model.value"
    structure_ref @= "test.collision.shape"


class FirstMapping:
    match @= ImportedCall("pkg:mod.Cls.make")
    emit @= "ext.collision"


class SecondMapping:
    match @= ImportedCall("pkg.mod:Cls.make")
    emit @= "ext.collision"
