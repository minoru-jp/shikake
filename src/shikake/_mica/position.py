"""Source-location utilities; never reinterpret stored AST byte offsets."""

from __future__ import annotations


def utf8_byte_column_to_character_column(line: str, column: int) -> int:
    """Convert a zero-based UTF-8 byte offset to a Unicode character column.

    `line` is the decoded source line containing the location, not the entire
    source. Both columns are zero-based. Invalid offsets, including offsets
    into the middle of a UTF-8 code point, raise ValueError. This does *not*
    calculate a terminal display width (tab expansion, wide glyphs, etc.).
    """
    if column < 0:
        raise ValueError("UTF-8 byte column must be nonnegative")
    encoded = line.encode("utf-8")
    if column > len(encoded):
        raise ValueError("UTF-8 byte column exceeds the source line")
    try:
        return len(encoded[:column].decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError("UTF-8 byte column falls inside a character") from error
