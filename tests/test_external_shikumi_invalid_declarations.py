"""Malformed Shikumi declarations must fail before external definitions are built."""

from __future__ import annotations

import unittest
from types import ModuleType

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
    load_external_definitions,
    match,
    match_generic,
    match_type,
    parent_id,
    part,
    slot,
    structure_id,
)


def _description(*fields: tuple[str, object]) -> ModuleType:
    """Provide actual Shikumi class bindings in a minimal trusted module.

    The assignment writers return descriptors whose ``__set_name__`` registers
    information when the class is created. No validation internals are mocked.
    """
    module = ModuleType("test_shikumi_invalid_declaration")
    declaration = type(
        "Declaration",
        (),
        {"__module__": module.__name__, **dict(fields)},
    )
    module.__dict__["Declaration"] = declaration
    return module


class ExternalShikumiInvalidDeclarationsTests(unittest.TestCase):
    def test_invalid_kind_structure_and_feature_placements(self) -> None:
        cases = (
            (
                "Kind with a mapping emit",
                (
                    ("kind_id", kind_id.__imatmul__("vendor.invalid_kind")),
                    ("parent_id", parent_id.__imatmul__("model.value")),
                    ("emit", emit.__imatmul__("vendor.invalid_kind")),
                ),
                "invalid external Kind",
            ),
            (
                "Kind with a generic slot",
                (
                    ("kind_id", kind_id.__imatmul__("vendor.invalid_kind")),
                    ("parent_id", parent_id.__imatmul__("model.value")),
                    ("slot", slot.__imatmul__("value")),
                ),
                "invalid external Kind",
            ),
            (
                "Kind with a call argument binding",
                (
                    ("kind_id", kind_id.__imatmul__("vendor.invalid_kind")),
                    ("parent_id", parent_id.__imatmul__("model.value")),
                    ("bind", bind.__imatmul__(Argument("value", 0, "value"))),
                ),
                "invalid external Kind",
            ),
            (
                "Structure with a call argument binding",
                (
                    ("structure_id", structure_id.__imatmul__("vendor.structure")),
                    ("part", part.__imatmul__(Role("value", "node"))),
                    ("bind", bind.__imatmul__(Argument("value", 0, "value"))),
                ),
                "invalid external Structure",
            ),
            (
                "Structure with a mapping emit",
                (
                    ("structure_id", structure_id.__imatmul__("vendor.structure")),
                    ("emit", emit.__imatmul__("vendor.kind")),
                ),
                "invalid external Structure",
            ),
            (
                "Structure with an applied Feature",
                (
                    ("structure_id", structure_id.__imatmul__("vendor.structure")),
                    ("apply_feature", apply_feature.__imatmul__("vendor.tag")),
                ),
                "invalid external Structure",
            ),
            (
                "Feature without allowed Kinds",
                (("feature_id", feature_id.__imatmul__("vendor.tag")),),
                "invalid external Feature",
            ),
            (
                "Feature with a mapping emit",
                (
                    ("feature_id", feature_id.__imatmul__("vendor.tag")),
                    ("feature_allowed", feature_allowed.__imatmul__("model.value")),
                    ("emit", emit.__imatmul__("vendor.kind")),
                ),
                "invalid external Feature",
            ),
            (
                "Feature with a generic slot",
                (
                    ("feature_id", feature_id.__imatmul__("vendor.tag")),
                    ("feature_allowed", feature_allowed.__imatmul__("model.value")),
                    ("slot", slot.__imatmul__("value")),
                ),
                "invalid external Feature",
            ),
            (
                "Feature with a call argument binding",
                (
                    ("feature_id", feature_id.__imatmul__("vendor.tag")),
                    ("feature_allowed", feature_allowed.__imatmul__("model.value")),
                    ("bind", bind.__imatmul__(Argument("value", 0, "value"))),
                ),
                "invalid external Feature",
            ),
            (
                "Feature with another applied Feature",
                (
                    ("feature_id", feature_id.__imatmul__("vendor.tag")),
                    ("feature_allowed", feature_allowed.__imatmul__("model.value")),
                    ("apply_feature", apply_feature.__imatmul__("vendor.other")),
                ),
                "invalid external Feature",
            ),
        )
        for name, fields, expected_message in cases:
            with (
                self.subTest(declaration=name),
                self.assertRaisesRegex(ValueError, expected_message),
            ):
                load_external_definitions(_description(*fields))

    def test_invalid_interface_mapping_shapes_are_rejected(self) -> None:
        call = ("match", match.__imatmul__(ImportedCall("vendor.api:call")))
        typed = ("match_type", match_type.__imatmul__(ImportedType("vendor.api:Item")))
        generic = (
            "match_generic",
            match_generic.__imatmul__(ImportedGeneric("vendor.api:Array")),
        )
        output = ("emit", emit.__imatmul__("vendor.kind"))
        arg = ("bind", bind.__imatmul__(Argument("value", 0, "value")))
        role = ("slot", slot.__imatmul__("value"))
        cases = (
            ("Call without emit", (call,), "invalid external interface mapping"),
            ("Type without emit", (typed,), "invalid external interface mapping"),
            ("Generic without emit", (generic,), "invalid external interface mapping"),
            ("Call with slot", (call, output, role), "invalid external call mapping"),
            ("Type with bind", (typed, output, arg), "invalid external type mapping"),
            ("Type with slot", (typed, output, role), "invalid external type mapping"),
            (
                "Generic with bind",
                (generic, output, arg),
                "invalid external generic mapping",
            ),
            (
                "Call with parent_id",
                (call, output, ("parent_id", parent_id.__imatmul__("model.value"))),
                "invalid external interface mapping",
            ),
        )
        for name, fields, expected_message in cases:
            with (
                self.subTest(mapping=name),
                self.assertRaisesRegex(ValueError, expected_message),
            ):
                load_external_definitions(_description(*fields))

    def test_interface_mapping_rejects_duplicate_emit(self) -> None:
        module = _description(
            ("match", match.__imatmul__(ImportedCall("vendor.api:call"))),
            ("first_emit", emit.__imatmul__("vendor.kind")),
            ("second_emit", emit.__imatmul__("vendor.other")),
        )
        with self.assertRaisesRegex(ValueError, "invalid external Shikumi description"):
            load_external_definitions(module)

    def test_multiple_identity_fields_are_rejected(self) -> None:
        module = _description(
            ("kind_id", kind_id.__imatmul__("vendor.kind")),
            ("parent_id", parent_id.__imatmul__("model.value")),
            ("feature_id", feature_id.__imatmul__("vendor.tag")),
        )
        with self.assertRaisesRegex(ValueError, "needs one identity"):
            load_external_definitions(module)


if __name__ == "__main__":
    unittest.main()
