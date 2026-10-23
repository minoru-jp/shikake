"""Optional syntactic import restrictions; no module resolution or execution.

This checks exactly the absolute names written in AST import statements.
Trusted external mappings and caller-supplied module names are independent
sources of permission. The ordinary external-interface protection remains
responsible for registered structure use and reserved-name rules.
"""

from __future__ import annotations

import ast
import keyword
import unicodedata
from typing import Literal

from shikake.external import ExternalDefinitions

from .external_structures import ExternalModelingError

ImportPolicy = Literal["unrestricted", "registered_interfaces", "registered_modules"]
_POLICIES = frozenset(("unrestricted", "registered_interfaces", "registered_modules"))


def _validated_import_options(
    import_policy: ImportPolicy,
    allowed_modules: tuple[str, ...],
) -> frozenset[str]:
    """Validate options even when no import statement or source file exists."""
    if not isinstance(import_policy, str):
        raise TypeError("import_policy must be a string")
    if import_policy not in _POLICIES:
        raise ValueError(f"unknown import_policy: {import_policy!r}")
    if not isinstance(allowed_modules, tuple) or any(
        not isinstance(module, str) for module in allowed_modules
    ):
        raise TypeError("allowed_modules must be a tuple of strings")
    if len(set(allowed_modules)) != len(allowed_modules):
        raise ValueError("duplicate allowed module name")
    for module in allowed_modules:
        if unicodedata.normalize("NFKC", module) != module:
            raise ValueError(f"module name must be NFKC-normalized: {module!r}")
        if not module or any(
            not component.isidentifier() or keyword.iskeyword(component)
            for component in module.split(".")
        ):
            raise ValueError(f"invalid absolute module name: {module!r}")
    if allowed_modules and import_policy != "registered_modules":
        raise ValueError("allowed_modules requires import_policy='registered_modules'")
    return frozenset(allowed_modules)


def _assert_import_policy(
    tree: ast.Module,
    definitions: ExternalDefinitions | None,
    *,
    import_policy: ImportPolicy,
    allowed_modules: frozenset[str],
) -> None:
    """Reject forbidden static import syntax across the whole AST.

    Imports do not imply runtime object identity, and neither ``import X``
    nor ``from X import Y`` causes us to inspect X or check Y's existence.
    """
    if import_policy == "unrestricted":
        return
    mappings = definitions.mappings if definitions is not None else ()
    registered_modules = frozenset(
        mapping.target.path.partition(":")[0] for mapping in mappings
    )
    permitted_modules = registered_modules | allowed_modules
    # Registered structural roots are explicit import permissions in both
    # restrictive modes, even when the root is under a dotted namespace that
    # is not registered as a module in its own right.
    interfaces = frozenset(
        mapping.target.dotted.rpartition(".")[0] for mapping in mappings
    )

    # Report the first violation in lexical source order, not ast.walk's
    # breadth-first tree order. Keep memory bounded to import nodes only.
    imports = (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    for node in sorted(imports, key=lambda n: (n.lineno, n.col_offset)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    import_policy == "registered_modules"
                    and alias.name in permitted_modules
                ):
                    continue
                raise ExternalModelingError(
                    f"import not permitted by {import_policy}: {alias.name}",
                    node,
                    code="external.unregistered_import",
                    details={"path": alias.name, "policy": import_policy},
                )
        elif isinstance(node, ast.ImportFrom):
            # A relative import is never a literally known absolute module.
            module = node.module or ""
            written = "." * node.level + module
            if node.level or any(alias.name == "*" for alias in node.names):
                # Preserve the written import target in the structured issue.
                name = node.names[0].name
                path = f"{written}.{name}" if module else f"{written}{name}"
                raise ExternalModelingError(
                    f"import not permitted by {import_policy}: {path}",
                    node,
                    code="external.unregistered_import",
                    details={"path": path, "policy": import_policy},
                )
            # This future statement is a language directive, not permission
            # to import arbitrary objects from the __future__ module.
            if (
                module == "__future__"
                and len(node.names) == 1
                and node.names[0].name == "annotations"
                and node.names[0].asname is None
            ):
                continue
            for alias in node.names:
                structural_root = f"{module}.{alias.name}" in interfaces
                permitted = structural_root or (
                    import_policy == "registered_modules"
                    and module in permitted_modules
                )
                if permitted:
                    continue
                path = f"{module}.{alias.name}" if module else alias.name
                raise ExternalModelingError(
                    f"import not permitted by {import_policy}: {path}",
                    node,
                    code="external.unregistered_import",
                    details={"path": path, "policy": import_policy},
                )
