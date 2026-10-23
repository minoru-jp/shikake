"""Kind/Structure/Feature separation is the adopted architecture.

Keep this file name for historical continuity of the development tests.
"""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from shikake._mica.kinds import Kind, KindIndex, Structure, kind_index, load_kind_index
from shikake._mica.kinds.index import KindIndexRealizer
from shikake._mica.kinds.regulation import KIND_SHIKUMI
from shikake._mica.kinds.regulation import PartContract as Role
from shikake._mica.model import ModelFactory


class IndependentStructureTests(unittest.TestCase):
    def test_sharing_does_not_imply_ancestry(self) -> None:
        index = kind_index()
        self.assertEqual(len(index.all_kinds()), 143)
        self.assertEqual(len(index.all_structures()), 61)
        add = index.require_structure("model.value.operation.addition")
        equal = index.require_structure("model.value.operation.comparison.equal")
        self.assertIs(add, equal)
        self.assertEqual(add.id, "binary_operands")
        self.assertEqual([part.role for part in add.parts], ["left", "right"])
        self.assertFalse(
            index.is_a("model.value.operation.comparison.equal", "model.statement")
        )
        self.assertEqual(
            index.structure_of("model.definition.generator"),
            index.structure_of("model.definition.function"),
        )
        self.assertFalse(
            index.is_a("model.definition.generator", "model.definition.function")
        )
        self.assertNotIn(
            "model.value.operation.binary", {k.id for k in index.all_kinds()}
        )

    def test_classification_does_not_imply_structure_inheritance(self) -> None:
        index = kind_index()
        simple = index.require_structure("model.statement.assignment")
        augmented = index.require_structure(
            "model.statement.assignment.augmented.addition"
        )
        self.assertTrue(
            index.is_a(
                "model.statement.assignment.augmented", "model.statement.assignment"
            )
        )
        self.assertEqual([part.role for part in simple.parts], ["targets", "value"])
        self.assertEqual([part.role for part in augmented.parts], ["target", "value"])
        self.assertNotEqual(simple, augmented)
        self.assertIsNone(index.structure_of("model.statement"))
        self.assertIsNotNone(index.structure_of("model.statement.pass"))

    def test_factory_checks_structure_not_parent_roles(self) -> None:
        index = kind_index()
        factory = ModelFactory(index)
        name = factory.make("model.value.named", name="item")
        value = factory.make("model.value.literal", value=1)
        assign = factory.make(
            "model.statement.assignment", targets=(name,), value=value
        )
        augment = factory.make(
            "model.statement.assignment.augmented.addition", target=name, value=value
        )
        self.assertEqual([p.role for p in assign.parts()], ["targets", "value"])
        self.assertEqual([p.role for p in augment.parts()], ["target", "value"])
        with self.assertRaisesRegex(ValueError, "abstract Kind"):
            factory.make("model.statement")
        with self.assertRaisesRegex(ValueError, "expected roles"):
            factory.make("model.statement.assignment", target=name, value=value)

    def test_shikumi_graph_rejects_unknown_structure_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "mica_structure_invalid"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "description.py").write_text(
                "from shikake._mica.kinds.regulation import kind_id, parent_id, structure_ref\n"
                "class Root:\n    kind_id @= 'model'\n"
                "class Child:\n    kind_id @= 'model.child'\n"
                "    parent_id @= 'model'\n    structure_ref @= 'missing'\n",
                encoding="utf-8",
            )
            sys.path.insert(0, str(root))
            try:
                source = importlib.import_module("mica_structure_invalid")
                checked = KIND_SHIKUMI.validate(
                    source, placement=("mica", "kinds", "description")
                )
                self.assertFalse(checked.is_valid)
                self.assertTrue(
                    any(d.code == "mica.description.graph" for d in checked.diagnostics)
                )
                with self.assertRaisesRegex(ValueError, "unknown Structure"):
                    load_kind_index(source)
            finally:
                sys.path.remove(str(root))
                for name in tuple(sys.modules):
                    if name == "mica_structure_invalid" or name.startswith(
                        "mica_structure_invalid."
                    ):
                        del sys.modules[name]

    def test_index_rejects_duplicate_roles_and_missing_structures(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate or empty part role"):
            KindIndex(
                (Kind("model", None), Kind("model.child", "model", "dupe")),
                (Structure("dupe", (Role("x", "node"), Role("x", "nodes"))),),
            )
        with self.assertRaisesRegex(ValueError, "unknown Structure"):
            KindIndex((Kind("model", None), Kind("model.child", "model", "missing")))
        with self.assertRaisesRegex(ValueError, "duplicate Structure ID"):
            KindIndex(
                (Kind("model", None),), (Structure("dup", ()), Structure("dup", ()))
            )

    def test_async_feature_keeps_the_ordinary_kind_and_structure(self) -> None:
        index = kind_index()
        self.assertEqual([f.id for f in index.all_features()], ["async", "lazy"])
        factory = ModelFactory(index)
        block = factory.make("model.statement.block", statements=())
        definition = factory.make(
            "model.definition.function",
            name="fetch",
            parameters=(),
            type_parameters=(),
            decorators=(),
            returns=None,
            body=block,
            features=("async",),
        )
        self.assertEqual(definition.kind.id, "model.definition.function")
        self.assertEqual(definition.features, ("async",))
        with self.assertRaisesRegex(ValueError, "not applicable"):
            factory.make("model.value.named", name="x", features=("async",))
        with self.assertRaisesRegex(ValueError, "unknown Model feature"):
            factory.make("model.value.named", name="x", features=("no_such_feature",))
        with self.assertRaisesRegex(ValueError, "duplicate Model features"):
            index.validate_features("model.definition.function", ("async", "async"))

    def test_shikumi_realizer_returns_in_memory_index(self) -> None:
        from shikake._mica.kinds import description

        result = KIND_SHIKUMI.validate(
            description, placement=("mica", "kinds", "description")
        )
        self.assertTrue(result.is_valid)
        realizer = KindIndexRealizer()
        self.assertTrue(realizer.check(result.view).is_realizable)
        index = realizer.realize(result.view)
        self.assertEqual(len(index.all_kinds()), 143)
        self.assertEqual(len(index.all_structures()), 61)
        self.assertEqual(len(index.all_features()), 2)


if __name__ == "__main__":
    unittest.main()
