"""Import declarations and their written aliases, without importing input code."""

from ..regulation import kind_id, parent_id, structure_ref


class Import:
    kind_id @= "model.import"
    parent_id @= "model"


class ImportFrom:
    kind_id @= "model.import.from"
    structure_ref @= "import_from"
    parent_id @= "model.import"


class ImportAlias:
    kind_id @= "model.import.alias"
    structure_ref @= "import_alias"
    parent_id @= "model.import"


class ImportDirect:
    kind_id @= "model.import.direct"
    structure_ref @= "import_direct"
    parent_id @= "model.import"
