"""Conservative, AST-only recognition of stable built-in collection calls.

No source is executed and no runtime object is resolved. A written name in a
visible lexical scope is sufficient to withhold normalization, even if a
control-flow analysis could prove that write is not reached.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping

from .ast_facts import SyntaxFacts, SyntaxScope
from .builtin_names import BUILTIN_NAMES
from .lexical_scopes import binding_owner, visible_owners

# Constructor vocabulary is classified only when the name is a known standard built-in.
_BASE: Mapping[str, tuple[str, bool]] = {
    "list": ("sequence", False),
    "tuple": ("sequence", True),
    "dict": ("mapping", False),
    "set": ("set", False),
    "frozenset": ("set", True),
}


class BuiltinCollectionRecognition:
    """Check whole-lexical-scope names using the shared SyntaxFacts events."""

    def __init__(self, tree: ast.Module, facts: SyntaxFacts) -> None:
        self._root = facts.root
        self._node_scopes, _, _ = facts.expression_scopes(tree)
        self._facts = facts
        self._shadow_cache: dict[tuple[object, str], bool] = {}
        # Index lexical write names once; the owner query below is O(depth),
        # not O(number of prior writes) for every global/nonlocal occurrence.
        declarations: dict[SyntaxScope, set[str]] = {}
        for event in facts.events:
            if event.kind != "star":
                declarations.setdefault(event.scope, set()).add(event.name)
        self._declarations = declarations
        self._events: dict[int, set[str]] = {}
        self._non_import_events: dict[int, set[str]] = {}
        for event in facts.events:
            if event.kind == "star":
                continue
            if event.kind == "annotation" and event.scope.kind == "module":
                continue
            owner = binding_owner(
                event.scope, event.name, self._root, self._locally_binds
            )
            self._events.setdefault(id(owner), set()).add(event.name)
            if event.kind != "import":
                self._non_import_events.setdefault(id(owner), set()).add(event.name)

    def _locally_binds(self, scope: SyntaxScope, name: str) -> bool:
        return name in self._declarations.get(scope, ())

    def _expression_shadows(self, node: ast.AST, name: str) -> bool:
        """Check cached expression-local captures without ancestor AST scans."""
        frame = self._facts.expression_frame(node)
        visited: list[tuple[object, str]] = []
        result = False
        while frame is not None:
            key = (frame, name)
            cached = self._shadow_cache.get(key)
            if cached is not None:
                result = cached
                break
            visited.append(key)
            if name in frame.names:
                result = True
                break
            frame = frame.parent
        for key in visited:
            self._shadow_cache[key] = result
        return result

    def _visible_owners(self, node: ast.AST, name: str) -> Iterator[SyntaxScope]:
        """Ignore class locals inside lambda/comprehension expression bodies.

        Their outermost iterable and lambda defaults use the enclosing frame,
        so class bindings remain visible there. This shares the existing
        expression index without introducing a separate scope analysis.
        """
        scope = self._node_scopes.get(node, self._root)
        in_nested_expression = self._facts.expression_frame(node) is not None
        for owner in visible_owners(scope, name, self._root, self._locally_binds):
            if in_nested_expression and owner.kind == "class":
                continue
            yield owner

    def shadows_registered_import(self, node: ast.AST, name: str) -> bool:
        """Whether a lexical binding masks an explicitly imported interface.

        The matching root import is not a shadow; ordinary writes and local
        introductions are. Star imports are deliberately ignored. This uses
        the same lightweight facts as built-in Collection recognition.
        """
        if self._expression_shadows(node, name):
            return True
        for owner in self._visible_owners(node, name):
            if owner is self._root:
                return name in self._non_import_events.get(id(owner), ())
            if name in self._events.get(id(owner), ()):
                return True
        return False

    def collection(self, node: ast.Call) -> tuple[str, bool] | None:
        if not isinstance(node.func, ast.Name):
            return None
        name = node.func.id
        # Deferred import avoids a reverse dependency on the expression engine.
        from .modeling.python315 import COLLECTION_BUILTINS_315

        classification = _BASE.get(name) or COLLECTION_BUILTINS_315.get(name)
        if classification is None or name not in BUILTIN_NAMES:
            return None
        # The syntax-only constructor contract is known without evaluating
        # any argument. Unsupported forms stay ordinary Call Models.
        if len(node.args) > 1 or any(isinstance(arg, ast.Starred) for arg in node.args):
            return None
        if name not in {"dict", "frozendict"} and node.keywords:
            return None
        if self._expression_shadows(node, name):
            return None
        for owner in self._visible_owners(node, name):
            if name in self._events.get(id(owner), ()):
                return None
        return classification
