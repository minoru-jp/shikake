"""Versioned, deterministic CPython built-in name vocabulary.

These names describe the standard interpreter language environment, not the
mutable `builtins` module of the process doing the inspection. `site` additions
and names installed by client code deliberately do not alter the Model.
"""

from __future__ import annotations

import sys

# The CPython 3.11 vocabulary, without `site` convenience functions.
_BASE_NAMES: frozenset[str] = frozenset(
    """
    ArithmeticError AssertionError AttributeError BaseException BaseExceptionGroup BlockingIOError BrokenPipeError BufferError
    BytesWarning ChildProcessError ConnectionAbortedError ConnectionError ConnectionRefusedError ConnectionResetError DeprecationWarning EOFError
    Ellipsis EncodingWarning EnvironmentError Exception ExceptionGroup False FileExistsError FileNotFoundError
    FloatingPointError FutureWarning GeneratorExit IOError ImportError ImportWarning IndentationError IndexError
    InterruptedError IsADirectoryError KeyError KeyboardInterrupt LookupError MemoryError ModuleNotFoundError NameError
    None NotADirectoryError NotImplemented NotImplementedError OSError OverflowError PendingDeprecationWarning PermissionError
    ProcessLookupError RecursionError ReferenceError ResourceWarning RuntimeError RuntimeWarning StopAsyncIteration StopIteration
    SyntaxError SyntaxWarning SystemError SystemExit TabError TimeoutError True TypeError
    UnboundLocalError UnicodeDecodeError UnicodeEncodeError UnicodeError UnicodeTranslateError UnicodeWarning UserWarning ValueError
    Warning ZeroDivisionError __build_class__ __debug__ __doc__ __import__ __loader__ __name__
    __package__ __spec__ abs aiter all anext any ascii
    bin bool breakpoint bytearray bytes callable chr classmethod
    compile complex delattr dict dir divmod enumerate eval
    exec filter float format frozenset getattr globals hasattr
    hash hex id input int isinstance issubclass iter
    len list locals map max memoryview min next
    object oct open ord pow print property range
    repr reversed round set setattr slice sorted staticmethod
    str sum super tuple type vars zip
    """.split()  # noqa: SIM905 - deliberately readable static vocabulary
)

BUILTIN_NAMES: frozenset[str] = (
    _BASE_NAMES
    | (
        frozenset({"PythonFinalizationError", "_IncompleteInputError"})
        if sys.version_info >= (3, 13)
        else frozenset()
    )
    | (
        frozenset({"frozendict", "sentinel", "ImportCycleError", "__lazy_import__"})
        if sys.version_info >= (3, 15)
        else frozenset()
    )
)
