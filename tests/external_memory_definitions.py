"""Trusted test description, deliberately separate from importable interface."""

from shikake.external import (
    Argument,
    ImportedCall,
    Role,
    bind,
    emit,
    kind_id,
    match,
    parent_id,
    part,
    structure_id,
    structure_ref,
)


class AllocationStructure:
    structure_id @= "test.memory.allocation"
    part @= Role("size", "node")


class AllocationKind:
    kind_id @= "ext.memory.allocate"
    parent_id @= "model.value"
    structure_ref @= "test.memory.allocation"


class AllocationMapping:
    match @= ImportedCall("framework.memory:Memory.new")
    emit @= "ext.memory.allocate"
    bind @= Argument("size", 0, "size")


class ReleaseStructure:
    structure_id @= "test.memory.release"
    part @= Role("target", "node")


class ReleaseKind:
    kind_id @= "ext.memory.release"
    parent_id @= "model.value"
    structure_ref @= "test.memory.release"


class ReleaseMapping:
    match @= ImportedCall("framework.memory:Memory.add")
    emit @= "ext.memory.release"
    bind @= Argument("target", 0, "target")
