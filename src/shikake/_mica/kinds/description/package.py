"""Package container kind, distinct from the module and class hierarchy."""

from ..regulation import kind_id, parent_id, structure_ref


class Package:
    kind_id @= "model.package"
    structure_ref @= "package_definition"
    parent_id @= "model"
