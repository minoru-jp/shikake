"""Independent comment locations and syntax-agnostic line lookups."""

import copy
import dataclasses
import io
import pickle
import tempfile
import tokenize
import unittest
from pathlib import Path
from tokenize import TokenError

import shikake


class CommentCollectionTests(unittest.TestCase):
    def test_comments_are_lossless_and_do_not_enter_model(self) -> None:
        source = '"# not a comment"\nx = 1  # type: int\n# type: ignore\n'
        found = shikake.collect_comments(source)
        self.assertEqual(
            tuple(item.text for item in found.comments),
            ("# type: int", "# type: ignore"),
        )
        self.assertEqual(found.comments[0], shikake.Comment("# type: int", 2, 7, 18))
        self.assertEqual(
            shikake.parse_source(source),
            shikake.parse_source('"# not a comment"\nx = 1\n'),
        )
        self.assertEqual(found.on_right_of_line(2), (found.comments[0],))
        self.assertEqual(found.on_right_of_line(3), ())

    def test_above_line_ignores_blank_lines_and_stops_at_code(self) -> None:
        source = "# A\n\n# B\nx = 1  # C\n\n# D\n\n# E\ny = 2\n"
        facts = shikake.collect_comments(source)
        self.assertEqual(
            tuple(item.text for item in facts.above_line(4)), ("# A", "# B")
        )
        self.assertEqual(
            tuple(item.text for item in facts.above_line(9)), ("# D", "# E")
        )
        self.assertEqual(facts.above_line(5), ())
        self.assertEqual(facts.above_line(1), ())
        self.assertEqual(facts.on_right_of_line(4)[0].text, "# C")

    def test_function_header_comments_are_available_without_association(self) -> None:
        source = (
            "# A\ndef calculate(\n"
            "    x: int,  # B\n"
            "    # C\n"
            "    y: int,\n"
            "    # D\n"
            "):  # E\n"
            "    # F\n\n"
            "    return x + y  # G\n"
        )
        comments = shikake.collect_comments(source)
        self.assertEqual(
            tuple(item.text for item in comments.in_lines(3, 7)),
            ("# B", "# C", "# D", "# E"),
        )
        self.assertEqual(tuple(x.text for x in comments.above_line(5)), ("# C",))
        self.assertEqual(tuple(x.text for x in comments.above_line(10)), ("# F",))
        self.assertEqual(comments.on_right_of_line(7)[0].text, "# E")
        self.assertEqual(comments.above_line(2)[0].text, "# A")
        # The library doesn't guess that D belongs to the function or y.
        self.assertEqual(comments.above_line(7)[0].text, "# D")

    def test_model_span_composes_with_existing_line_queries(self) -> None:
        source = "# heading\n\nvalue = 1  # type: int\n"
        root = shikake.parse_source(source)
        comments = shikake.collect_comments(source)
        self.assertIsNone(root.span)  # No invented position for the module.

        statement = root.get_nodes("body")[0]
        self.assertIsNotNone(statement.span)
        assert statement.span is not None
        self.assertEqual(statement.span.line, 3)
        self.assertEqual(
            tuple(comment.text for comment in comments.above_line(statement.span.line)),
            ("# heading",),
        )
        self.assertEqual(
            tuple(
                comment.text
                for comment in comments.on_right_of_line(statement.span.line)
            ),
            ("# type: int",),
        )
        self.assertEqual(
            comments.in_lines(statement.span.line, statement.span.end_line),
            comments.on_right_of_line(statement.span.line),
        )

    def test_multiline_model_spans_and_same_line_models_are_not_associations(
        self,
    ) -> None:
        source = (
            "# heading\n\n"
            "def f(\n"
            "    x: int,  # x\n"
            "    # before y\n"
            "    y: int,\n"
            "):  # closing line\n"
            "    # before return\n"
            "    return x + y  # inline\n"
        )
        root = shikake.parse_source(source)
        comments = shikake.collect_comments(source)
        nodes = tuple(root.walk())
        fn = next(node for node in nodes if node.kind.id == "model.definition.function")
        x, y = (node for node in nodes if node.kind.id == "model.definition.parameter")
        ret = next(node for node in nodes if node.kind.id == "model.statement.return")
        expr = next(
            node for node in nodes if node.kind.id == "model.value.operation.addition"
        )
        assert fn.span is not None
        assert x.span is not None
        assert y.span is not None
        assert ret.span is not None
        assert expr.span is not None

        self.assertEqual(
            tuple(c.text for c in comments.in_lines(fn.span.line, fn.span.end_line)),
            ("# x", "# before y", "# closing line", "# before return", "# inline"),
        )
        self.assertEqual(comments.above_line(fn.span.line)[0].text, "# heading")
        self.assertEqual(comments.on_right_of_line(x.span.line)[0].text, "# x")
        self.assertEqual(comments.above_line(y.span.line)[0].text, "# before y")
        self.assertEqual(comments.above_line(ret.span.line)[0].text, "# before return")
        self.assertEqual(comments.on_right_of_line(7)[0].text, "# closing line")
        # An expression sharing the return line observes that line's comment too.
        # The result is not a semantic link to either Model.
        self.assertEqual(ret.span.line, expr.span.line)
        self.assertEqual(
            comments.on_right_of_line(ret.span.line),
            comments.on_right_of_line(expr.span.line),
        )

    def test_module_header_and_footer(self) -> None:
        facts = shikake.collect_comments(
            "# header\n\nvalue = 1  # inline\n\n# footer\n"
        )
        self.assertEqual(tuple(x.text for x in facts.module_header()), ("# header",))
        self.assertEqual(tuple(x.text for x in facts.module_footer()), ("# footer",))
        self.assertEqual(
            tuple(x.text for x in facts.in_lines(1, 5)),
            ("# header", "# inline", "# footer"),
        )
        only = shikake.collect_comments("# first\n\n# last\n")
        self.assertEqual(only.module_header(), only.comments)
        self.assertEqual(only.module_footer(), only.comments)
        empty = shikake.collect_comments("\n\n")
        self.assertEqual(empty.module_header(), ())
        self.assertEqual(empty.module_footer(), ())

    def test_columns_are_character_offsets_not_ast_byte_offsets(self) -> None:
        facts = shikake.collect_comments('変数 = "日本語"  # 文字\n')
        comment = facts.comments[0]
        self.assertEqual(comment.column, len('変数 = "日本語"  '))
        self.assertEqual(comment.end_column - comment.column, len("# 文字"))
        self.assertEqual(facts.on_right_of_line(1), (comment,))
        statement = shikake.parse_source('変数 = "日本語"  # 文字\n').get_nodes("body")[
            0
        ]
        assert statement.span is not None
        self.assertEqual(statement.span.line, comment.line)
        self.assertEqual(facts.on_right_of_line(statement.span.line), (comment,))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            comment.text = "modified"  # type: ignore[misc]

    def test_multiline_string_is_not_comments_or_blank_line(self) -> None:
        facts = shikake.collect_comments(
            'x = """hello\n# inside string\n"""\n# outside\ny = 1\n'
        )
        self.assertEqual(tuple(x.text for x in facts.comments), ("# outside",))
        self.assertEqual(facts.above_line(5), (facts.comments[0],))
        self.assertEqual(facts.above_line(4), ())

    def test_inclusive_query_and_invalid_line_arguments(self) -> None:
        found = shikake.collect_comments("# a\nx=1 # b\n# c\n")
        self.assertEqual(tuple(x.text for x in found.in_lines(2, 3)), ("# b", "# c"))
        self.assertEqual(found.in_lines(9, 11), ())
        with self.assertRaises(ValueError):
            found.in_lines(5, 4)
        with self.assertRaises(ValueError):
            found.above_line(0)
        with self.assertRaises(TypeError):
            found.on_right_of_line(True)
        with self.assertRaises(TypeError):
            shikake.collect_comments(b"# not unicode")  # type: ignore[arg-type]

    def test_tokenizer_failures_do_not_change_ast_parsing_contract(self) -> None:
        bad = "x = (\n# trailing\n"
        with self.assertRaises(TokenError):
            shikake.collect_comments(bad)
        with self.assertRaises(SyntaxError):
            shikake.parse_source(bad)
        self.assertFalse(shikake.inspect_source(bad).complete)

    def test_code_locations_affect_result_equality(self) -> None:
        with_code = shikake.collect_comments("x=1\n# note\n")
        without_code = shikake.collect_comments("\n# note\n")
        self.assertEqual(with_code.comments, without_code.comments)
        self.assertNotEqual(with_code, without_code)
        self.assertNotEqual(hash(with_code), hash(without_code))
        self.assertEqual(without_code.module_header(), without_code.comments)

    def test_universal_newlines_match_ast_statement_lines(self) -> None:
        for newline in ("\n", "\r", "\r\n"):
            with self.subTest(newline=repr(newline)):
                source = (
                    newline.join(
                        ("# header", "value = 1  # inline", "", "# above", "other = 2")
                    )
                    + newline
                )
                first, second = shikake.parse_source(source).get_nodes("body")
                assert first.span is not None
                assert second.span is not None
                facts = shikake.collect_comments(source)
                self.assertEqual(first.span.line, 2)
                self.assertEqual(second.span.line, 5)
                self.assertEqual(
                    tuple(c.text for c in facts.on_right_of_line(first.span.end_line)),
                    ("# inline",),
                )
                self.assertEqual(
                    tuple(c.text for c in facts.above_line(second.span.line)),
                    ("# above",),
                )
                self.assertEqual(facts.module_header()[0].text, "# header")
                self.assertEqual(facts.module_footer(), ())

        mixed = "# first\rvalue = 1  # inline\r\n# before\nother = 2"
        facts = shikake.collect_comments(mixed)
        second = shikake.parse_source(mixed).get_nodes("body")[1]
        assert second.span is not None
        self.assertEqual(second.span.line, 4)
        self.assertEqual(facts.above_line(second.span.line)[0].text, "# before")
        self.assertEqual(facts.on_right_of_line(2)[0].text, "# inline")

    def test_source_comments_must_be_collected_not_constructed_or_replaced(
        self,
    ) -> None:
        facts = shikake.collect_comments("x = 1\n# note\n")
        with self.assertRaisesRegex(TypeError, "collect_comments"):
            shikake.SourceComments(  # type: ignore[call-arg]
                comments=facts.comments,
                _comment_lines=(),
                _code_lines=(),
            )
        with self.assertRaisesRegex(TypeError, "collect_comments"):
            dataclasses.replace(facts, comments=())
        # Python 3.11-3.12 raise ValueError; 3.13+ raise TypeError.
        with self.assertRaises((TypeError, ValueError)):
            dataclasses.replace(facts, _comment_lines=())

    def test_source_comments_copy_and_pickle_round_trip(self) -> None:
        facts = shikake.collect_comments("x = 1\n# note\n")
        for recovered in (
            copy.copy(facts),
            copy.deepcopy(facts),
            pickle.loads(pickle.dumps(facts)),
        ):
            self.assertEqual(recovered, facts)
            self.assertEqual(recovered.above_line(2), facts.above_line(2))
            self.assertEqual(recovered.in_lines(1, 2), facts.in_lines(1, 2))

    def test_decorator_start_line_recipe_for_function_and_class(self) -> None:
        source = (
            "# function note\n"
            "@first\n"
            "@second(arg)\n"
            "def f():\n"
            "    pass\n"
            "# class note\n"
            "@class_decorator\n"
            "class C:\n"
            "    pass\n"
        )
        facts = shikake.collect_comments(source)
        function, cls = shikake.parse_source(source).get_nodes("body")
        for model, expected in ((function, "# function note"), (cls, "# class note")):
            assert model.span is not None
            decorators = model.get_nodes("decorators")
            self.assertTrue(decorators)
            starts = [model.span.line]
            starts.extend(d.span.line for d in decorators if d.span is not None)
            self.assertEqual(
                tuple(c.text for c in facts.above_line(min(starts))), (expected,)
            )
            # Looking up the def/class line alone stops at the decorator code.
            self.assertEqual(facts.above_line(model.span.line), ())

    def test_body_header_same_line_requires_restricting_recipe(self) -> None:
        cases = (
            "# definition note\ndef f(): return 1\n",
            "def f(\n    # signature note\n): return 1\n",
        )
        for source in cases:
            with self.subTest(source=source):
                definition = shikake.parse_source(source).get_nodes("body")[0]
                block = definition.get("body")
                assert isinstance(block, shikake.Model)
                first = block.get_nodes("statements")[0]
                assert first.span is not None
                line = io.StringIO(source, newline=None).readlines()[
                    first.span.line - 1
                ]
                # AST columns are UTF-8 byte offsets, not character indices.
                prefix = line.encode("utf-8")[: first.span.column]
                self.assertTrue(prefix.strip())
                # A raw line query can reach unrelated comments, hence the
                # recipe must not label these as body-opening comments.
                found = shikake.collect_comments(source).above_line(first.span.line)
                self.assertTrue(found)

        normal = "def f():\n    # body note\n    return 1\n"
        definition = shikake.parse_source(normal).get_nodes("body")[0]
        block = definition.get("body")
        assert isinstance(block, shikake.Model)
        first = block.get_nodes("statements")[0]
        assert first.span is not None
        prefix = (
            io.StringIO(normal, newline=None)
            .readlines()[first.span.line - 1]
            .encode("utf-8")[: first.span.column]
        )
        self.assertFalse(prefix.strip())
        self.assertEqual(
            shikake.collect_comments(normal).above_line(first.span.line)[0].text,
            "# body note",
        )

    def test_same_line_recipe_uses_ast_compatible_line_boundaries(self) -> None:
        # splitlines() treats form feeds and U+2028 as new lines even though
        # the AST and tokenizer do not. The guard must use universal newlines.
        cases = (
            (
                "import os\n\x0c\n# section: helpers\n\ndef f(): return 1\n",
                "# section: helpers",
                True,
            ),
            (
                'note = "\u2028"\n# function note\ndef f(): return 1\n',
                "# function note",
                True,
            ),
            ('def f():\r\n    # body note\r\n    return "é"\r\n', "# body note", False),
        )
        for source, comment_text, has_prior_code in cases:
            with self.subTest(source=source):
                definition = shikake.parse_source(source).get_nodes("body")[-1]
                block = definition.get("body")
                assert isinstance(block, shikake.Model)
                first = block.get_nodes("statements")[0]
                assert first.span is not None
                lines = io.StringIO(source, newline=None).readlines()
                prefix = lines[first.span.line - 1].encode("utf-8")[: first.span.column]
                got = shikake.collect_comments(source).above_line(first.span.line)
                self.assertEqual(tuple(c.text for c in got), (comment_text,))
                # Inline definitions must not be mistaken for body comments.
                self.assertEqual(bool(prefix.strip()), has_prior_code)

    def test_tokenize_open_file_with_bom_uses_matching_unicode_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.py"
            path.write_bytes(b"\xef\xbb\xbf" + b"value = 1  # note\n")
            with tokenize.open(path) as file:
                source = file.read()
            self.assertFalse(source.startswith("\ufeff"))
            model = shikake.parse_source(source).get_nodes("body")[0]
            assert model.span is not None
            self.assertEqual(
                shikake.collect_comments(source)
                .on_right_of_line(model.span.end_line)[0]
                .text,
                "# note",
            )

    def test_public_reexport_and_bounded_repr(self) -> None:
        from shikake import _mica

        self.assertIs(shikake.Comment, _mica.Comment)
        self.assertIs(shikake.SourceComments, _mica.SourceComments)
        self.assertIs(shikake.collect_comments, _mica.collect_comments)
        self.assertEqual(
            repr(shikake.collect_comments("# hi\n")),
            "SourceComments(<1 comments>)",
        )


if __name__ == "__main__":
    unittest.main()
