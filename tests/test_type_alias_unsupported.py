"""Simulate a future unadopted AST construct in Partial recovery tests.

TypeAlias is now supported by the public parser, but regression tests for
skipping an unadopted *statement* still need a reproducible stand-in. Patch
only those tests, without weakening or special-casing the real parser.
"""

from __future__ import annotations

from functools import wraps
from unittest.mock import patch

from shikake._mica.parser import UnsupportedSyntaxError, _Builder


def simulate_unadopted_syntax(*, generic_class: bool = False):
    def decorate(test):
        @wraps(test)
        def run(*args, **kwargs):
            original = _Builder.statement

            def statement(self, node, *, class_body=False):
                if type(node).__name__ == "TypeAlias" or (
                    generic_class
                    and type(node).__name__ == "ClassDef"
                    and getattr(node, "type_params", ())
                ):
                    raise UnsupportedSyntaxError(node, "simulated unadopted statement")
                return original(self, node, class_body=class_body)

            with patch.object(_Builder, "statement", statement):
                return test(*args, **kwargs)

        return run

    return decorate
