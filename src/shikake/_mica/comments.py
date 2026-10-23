"""Source comment facts, independent of AST modeling and type-comment parsing."""

from __future__ import annotations

import io
import tokenize
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Comment:
    """A literal ``#...`` token at its written source location.

    Lines are one-based; columns are zero-based Unicode character offsets,
    unlike the UTF-8 byte columns in AST SourceSpan. Comments occupy one line.
    """

    text: str
    line: int
    column: int
    end_column: int


@dataclass(frozen=True, slots=True, init=False)
class SourceComments:
    """Immutable source-ordered comments and mechanical line-only queries.

    This is not a Model tree. No ownership, type meaning, or declaration-to-
    comment association is inferred. Empty lines never block a query.
    """

    comments: tuple[Comment, ...]
    _comment_lines: tuple[int, ...] = field(init=False, repr=False, compare=False)
    _code_lines: tuple[int, ...] = field(init=False, repr=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("SourceComments must be created with collect_comments()")

    @classmethod
    def _from_scan(
        cls, comments: tuple[Comment, ...], code_lines: tuple[int, ...]
    ) -> SourceComments:
        """Build all derived indexes from the same tokenizer pass."""
        result = object.__new__(cls)
        object.__setattr__(result, "comments", comments)
        object.__setattr__(
            result, "_comment_lines", tuple(item.line for item in comments)
        )
        object.__setattr__(result, "_code_lines", code_lines)
        return result

    def __repr__(self) -> str:
        return f"SourceComments(<{len(self.comments)} comments>)"

    @staticmethod
    def _positive_line(line: int) -> None:
        if isinstance(line, bool) or not isinstance(line, int):
            raise TypeError("line number must be an integer")
        if line < 1:
            raise ValueError("line number must be at least 1")

    def in_lines(self, first: int, last: int) -> tuple[Comment, ...]:
        """Comments whose lines fall in the inclusive [first, last] range."""
        self._positive_line(first)
        self._positive_line(last)
        if last < first:
            raise ValueError("last line must not precede first line")
        start = bisect_left(self._comment_lines, first)
        end = bisect_right(self._comment_lines, last)
        return self.comments[start:end]

    def on_right_of_line(self, line: int) -> tuple[Comment, ...]:
        """Trailing comments on a line with code before the comment."""
        self._positive_line(line)
        index = bisect_left(self._code_lines, line)
        if index < len(self._code_lines) and self._code_lines[index] == line:
            return self.in_lines(line, line)
        return ()

    def above_line(self, line: int) -> tuple[Comment, ...]:
        """Comments reachable upward without crossing a line containing code.

        Blank lines are traversable. The queried line itself is excluded.
        """
        self._positive_line(line)
        previous_code_index = bisect_left(self._code_lines, line) - 1
        previous_code = (
            self._code_lines[previous_code_index] if previous_code_index >= 0 else 0
        )
        if previous_code + 1 >= line:
            return ()
        return self.in_lines(previous_code + 1, line - 1)

    def module_header(self) -> tuple[Comment, ...]:
        """Comments strictly preceding the first source line containing code."""
        if not self._code_lines:
            return self.comments
        if self._code_lines[0] == 1:
            return ()
        return self.in_lines(1, self._code_lines[0] - 1)

    def module_footer(self) -> tuple[Comment, ...]:
        """Comments strictly following the last source line containing code.

        With no code, all comments belong to both header and footer.
        """
        if not self._code_lines:
            return self.comments
        if not self.comments or self.comments[-1].line <= self._code_lines[-1]:
            return ()
        return self.in_lines(self._code_lines[-1] + 1, self.comments[-1].line)


def collect_comments(source: str) -> SourceComments:
    """Tokenize one Unicode source string without calling ``ast.parse``.

    Unlike ``ast.parse(..., type_comments=True)``, this never validates type
    comments. Lexically malformed input may raise ``tokenize.TokenError`` or
    ``IndentationError``; calling this API does not change parse/inspect results.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    comments: list[Comment] = []
    code_lines: set[int] = set()
    ignored = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
    # Universal newlines keep tokenize line numbers aligned with ast.parse.
    for token in tokenize.generate_tokens(io.StringIO(source, newline=None).readline):
        if token.type == tokenize.COMMENT:
            comments.append(
                Comment(token.string, token.start[0], token.start[1], token.end[1])
            )
            continue
        if token.type in ignored or not token.string.strip():
            continue
        # A multiline string or token also blocks its intermediate lines.
        last_line = token.end[0] - (token.end[1] == 0)
        code_lines.update(range(token.start[0], max(token.start[0], last_line) + 1))
    items = tuple(comments)
    return SourceComments._from_scan(items, tuple(sorted(code_lines)))
