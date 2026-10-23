"""Root and module kinds."""

from ..regulation import kind_id, parent_id, structure_ref


class ModelKinds:
    kind_id @= "model"


class Module:
    kind_id @= "model.module"
    structure_ref @= "module_definition"
    parent_id @= "model"
