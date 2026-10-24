"""Shared lexical ownership and visibility rules for collected AST facts.

Scopes are lightweight records from either the AST pass or its Model-indexed
projection. The lookup policy must not diverge between these consumers.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Protocol, TypeVar, cast


class LexicalScope(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def parent(self) -> LexicalScope | None: ...

    @property
    def globals(self) -> set[str]: ...

    @property
    def nonlocals(self) -> set[str]: ...


_ScopeT = TypeVar("_ScopeT", bound=LexicalScope)


def binding_owner(
    scope: _ScopeT,
    name: str,
    root: _ScopeT,
    locally_binds: Callable[[_ScopeT, str], bool],
) -> _ScopeT:
    """Scope receiving a written operation, honoring global and nonlocal."""
    if name in scope.globals:
        return root
    if name in scope.nonlocals:
        current = cast(_ScopeT | None, scope.parent)
        while current is not None and current.kind != "module":
            if (
                current.kind == "function"
                and name not in current.globals
                and name not in current.nonlocals
                and locally_binds(current, name)
            ):
                # A declaration forwarded by a parent function is not a
                # binding *owned* by that parent. Continue to its real owner.
                return current
            current = cast(_ScopeT | None, current.parent)
    return scope


def visible_owners(
    scope: _ScopeT,
    name: str,
    root: _ScopeT,
    locally_binds: Callable[[_ScopeT, str], bool],
) -> Iterator[_ScopeT]:
    """Yield visible owners, preserving class locals through annotation scopes.

    Annotation scopes immediately nested under classes can see class locals,
    including across further annotation scopes. An ordinary nested function or
    class body ends that special visibility. The same rule is shared by
    reference facts and built-in collection recognition.
    """
    sees_class = True
    current: _ScopeT | None = scope
    while current is not None:
        if current.kind == "class" and not sees_class:
            current = cast(_ScopeT | None, current.parent)
            continue
        owner = binding_owner(current, name, root, locally_binds)
        yield owner
        if owner is root:
            return
        sees_class = sees_class and owner.kind == "annotation"
        current = cast(_ScopeT | None, owner.parent)
