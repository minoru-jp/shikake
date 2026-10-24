"""Conservative, AST-only recognition of stable built-in collection calls.

No source is executed and no runtime object is resolved. A written name in a
visible lexical scope is sufficient to withhold normalization, even if a
control-flow analysis could prove that write is not reached.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping

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


def _target_names(node: ast.AST) -> set[str]:
    found: set[str] = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.Name):
            found.add(current.id)
        elif isinstance(current, (ast.Tuple, ast.List)):
            pending.extend(current.elts)
        elif isinstance(current, ast.Starred):
            pending.append(current.value)
    return found


class BuiltinCollectionRecognition:
    """Check whole-lexical-scope names using the shared SyntaxFacts events."""

    def __init__(self, tree: ast.Module, facts: SyntaxFacts) -> None:
        self._root = facts.root
        self._node_scopes, self._parents = facts.expression_scopes(tree)
        # Index lexical write names once; the owner query below is O(depth),
        # not O(number of prior writes) for every global/nonlocal occurrence.
        declarations: dict[SyntaxScope, set[str]] = {}
        for event in facts.events:
            if event.kind != "star":
                declarations.setdefault(event.scope, set()).add(event.name)
        self._declarations = declarations
        self._events: dict[int, set[str]] = {}
        self._stars: set[int] = set()
        for event in facts.events:
            if event.kind == "star":
                self._stars.add(id(event.scope))
                continue
            if event.kind == "annotation" and event.scope.kind == "module":
                continue
            owner = binding_owner(
                event.scope, event.name, self._root, self._locally_binds
            )
            self._events.setdefault(id(owner), set()).add(event.name)

    def _locally_binds(self, scope: SyntaxScope, name: str) -> bool:
        return name in self._declarations.get(scope, ())

    def _expression_shadows(self, node: ast.AST, name: str) -> bool:
        """Do not mistake lambda/comprehension locals for builtins.

        The shared lexical fact index deliberately does not model expression
        scopes as named binding scopes. Treat their captures as shadowing
        conservatively, including first-iterable false negatives.
        """
        current = node
        while current in self._parents:
            current = self._parents[current]
            if isinstance(current, ast.Lambda):
                args = current.args
                captures = (
                    *args.posonlyargs,
                    *args.args,
                    *args.kwonlyargs,
                    *((args.vararg,) if args.vararg else ()),
                    *((args.kwarg,) if args.kwarg else ()),
                )
                if any(arg.arg == name for arg in captures):
                    return True
                if any(
                    isinstance(child, ast.NamedExpr) and child.target.id == name
                    for child in ast.walk(current.body)
                ):
                    return True
            if isinstance(
                current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ) and any(
                name in _target_names(clause.target) for clause in current.generators
            ):
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
        scope = self._node_scopes.get(node, self._root)
        for owner in visible_owners(scope, name, self._root, self._locally_binds):
            if name in self._events.get(id(owner), ()) or id(owner) in self._stars:
                return None
        return classification
