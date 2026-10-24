"""Caller-selected, syntax-only allow/deny checks for written imports.

The policy does not import source modules, resolve exports, or affect binding
facts. In particular, wildcard imports never expand into imported names.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Literal


def _valid_path(path: str) -> bool:
    """Paths are absolute module names, optionally followed by one symbol."""
    module, separator, member = path.partition(":")
    return (
        bool(module)
        and all(part.isidentifier() for part in module.split("."))
        and (not separator or (member.isidentifier() and ":" not in member))
    )


@dataclass(frozen=True, slots=True)
class ImportPolicy:
    """Explicit consumer policy. With no policy, imports are not restricted.

    Module entries (``pkg.mod``) match the module and its dotted descendants,
    for both ``import`` and ``from ... import``. Symbol entries
    (``pkg.mod:Name``) match only that explicit import name.
    For ``from pkg import name``, deny additionally tests the written
    ``pkg.name`` path; allow checks the import source module only. This is a
    syntactic heuristic, not a claim that ``name`` is a submodule. Deny wins
    on overlap. Relative imports use ``default`` because no absolute path is
    known. A star import also needs allow_star_import=True.
    """

    default: Literal["allow", "deny"] = "allow"
    allow: tuple[str, ...] = ()
    deny: tuple[str, ...] = ()
    allow_star_import: bool = False

    def __post_init__(self) -> None:
        if self.default not in ("allow", "deny"):
            raise ValueError("default must be 'allow' or 'deny'")
        if not isinstance(self.allow_star_import, bool):
            raise TypeError("allow_star_import must be a bool")
        for field_name, entries in (("allow", self.allow), ("deny", self.deny)):
            if not isinstance(entries, tuple) or any(
                not isinstance(item, str) for item in entries
            ):
                raise TypeError(f"{field_name} must be a tuple of strings")
            if any(not _valid_path(item) for item in entries):
                raise ValueError(f"invalid {field_name} path")
            if len(entries) != len(set(entries)):
                raise ValueError(f"duplicate {field_name} path")


class ImportPolicyError(ValueError):
    """A written import is rejected by the caller-provided ImportPolicy."""

    def __init__(self, node: ast.Import | ast.ImportFrom, message: str) -> None:
        self.node_type = type(node).__name__
        self.line = node.lineno
        self.column = node.col_offset
        self.code = "import.policy_denied"
        super().__init__(message)


def _permitted(policy: ImportPolicy, module: str | None, name: str | None) -> bool:
    if module is None:
        return policy.default == "allow"

    def matches(entry: str, *, include_member_path: bool) -> bool:
        if ":" in entry:
            return name is not None and entry == f"{module}:{name}"
        paths = (
            (module, f"{module}.{name}") if include_member_path and name else (module,)
        )
        return any(path == entry or path.startswith(entry + ".") for path in paths)

    if any(matches(entry, include_member_path=True) for entry in policy.deny):
        return False
    if any(matches(entry, include_member_path=False) for entry in policy.allow):
        return True
    return policy.default == "allow"


def check_imports(tree: ast.Module, policy: ImportPolicy | None) -> None:
    """Check every written import, including inside branches or functions.

    No import is executed. For ``from pkg import *``, the module alone is
    checked, never the unknown names it could introduce.
    """
    if policy is None:
        return
    if not isinstance(policy, ImportPolicy):
        raise TypeError("import_policy must be ImportPolicy or None")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _permitted(policy, alias.name, None):
                    raise ImportPolicyError(node, f"import not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.level == 0 else None
            for alias in node.names:
                if alias.name == "*" and not policy.allow_star_import:
                    raise ImportPolicyError(node, "star import is not allowed")
                name = None if alias.name == "*" else alias.name
                if not _permitted(policy, module, name):
                    written = ("." * node.level) + (node.module or "")
                    raise ImportPolicyError(
                        node, f"import not allowed: {written}:{alias.name}"
                    )
