"""Package discovery and Model assembly for local Python source trees.

Relationship facts and analyzers live in separate internal modules. No input
sources are imported or executed; composition and relation graphs are separate.
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from shikake.external import ExternalDefinitions

from .ast_facts import SyntaxFacts, collect_syntax_facts
from .base_references import BaseReference
from .builtin_collections import BuiltinCollectionRecognition
from .builtin_names import BUILTIN_NAMES
from .external_structures import _ExternalStructures
from .import_policy import (
    ImportPolicy,
    _assert_import_policy,
    _validated_import_options,
)
from .kinds import KindIndex
from .model import Model, ModelFactory, _clip_repr
from .parser import (
    SyntaxValidation,
    _Builder,
    _compile_check,
    _external_settings,
    _validated_syntax_validation,
)
from .relation_analysis import (
    OverrideCandidate,
    _analyze_package_facts,
    _selected_analyses,
)
from .relation_facts import BindingState, NameBinding


class _ModelIdentity:
    """Hash a Model by identity without invoking its structural hash.

    Keeping the Model alive also prevents identity reuse. Unlike stored id()
    integers, these keys remain valid after copying or unpickling a package.
    """

    __slots__ = ("model",)

    def __init__(self, model: Model) -> None:
        self.model = model

    def __hash__(self) -> int:
        return id(self.model)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _ModelIdentity) and self.model is other.model


@dataclass(frozen=True, slots=True)
class PackageModel:
    """Composition tree and explicitly selected static relationship analyses."""

    model: Model
    override_candidates: tuple[OverrideCandidate, ...] = ()
    base_references: tuple[BaseReference, ...] = ()
    analyses: frozenset[str] = frozenset()
    name_bindings: tuple[NameBinding, ...] = ()
    _binding_index: dict[tuple[_ModelIdentity, str], tuple[NameBinding, ...]] = field(
        init=False, repr=False, compare=False
    )
    _override_index: dict[_ModelIdentity, tuple[OverrideCandidate, ...]] = field(
        init=False, repr=False, compare=False
    )
    _base_index: dict[_ModelIdentity, tuple[BaseReference, ...]] = field(
        init=False, repr=False, compare=False
    )
    _module_index: dict[_ModelIdentity, str] = field(
        init=False, repr=False, compare=False
    )
    _builtin_star_conflicts: frozenset[tuple[str, str]] = field(
        default_factory=frozenset, repr=False, compare=False
    )
    _complete: bool = field(default=True, repr=False, compare=False)

    def __repr__(self) -> str:
        """Bounded diagnostic overview without expanding relationship facts."""
        return (
            f"PackageModel(model={_clip_repr(repr(self.model), 256)}, "
            f"override_candidates=<{len(self.override_candidates)} items>, "
            f"base_references=<{len(self.base_references)} items>, "
            f"analyses={_clip_repr(repr(self.analyses), 96)}, "
            f"name_bindings=<{len(self.name_bindings)} items>)"
        )

    def __post_init__(self) -> None:
        """Index the original ordered facts once, without hashing Models."""
        object.__setattr__(
            self,
            "_module_index",
            {
                _ModelIdentity(module): module.get_name("name")
                for module in (
                    self.model.get_nodes("modules")
                    if self.model.kind.id == "model.package"
                    else ()
                )
            },
        )
        bindings: defaultdict[tuple[_ModelIdentity, str], list[NameBinding]] = (
            defaultdict(list)
        )
        for binding in self.name_bindings:
            bindings[(_ModelIdentity(binding.scope), binding.name)].append(binding)
        object.__setattr__(
            self,
            "_binding_index",
            {key: tuple(value) for key, value in bindings.items()},
        )

        overrides: defaultdict[_ModelIdentity, list[OverrideCandidate]] = defaultdict(
            list
        )
        for candidate in self.override_candidates:
            overrides[_ModelIdentity(candidate.method)].append(candidate)
        object.__setattr__(
            self,
            "_override_index",
            {key: tuple(value) for key, value in overrides.items()},
        )

        bases: defaultdict[_ModelIdentity, list[BaseReference]] = defaultdict(list)
        for reference in self.base_references:
            bases[_ModelIdentity(reference.subject)].append(reference)
        object.__setattr__(
            self, "_base_index", {key: tuple(value) for key, value in bases.items()}
        )

    def bindings_for(self, scope: Model, name: str) -> tuple[NameBinding, ...]:
        """Find facts for a Model owner, including distinct lexical scope kinds."""
        key = _ModelIdentity(scope)
        recorded = self._binding_index.get((key, name), ())
        if recorded:
            return recorded
        # Do not materialize every built-in for every parsed module. The
        # synthesized fact belongs only to an exact module Model in this
        # package and does not appear in the written-name enumeration.
        module_name = self._module_index.get(key)
        if self._complete and module_name is not None and name in BUILTIN_NAMES:
            virtual = (
                NameBinding(
                    module_name,
                    scope,
                    name,
                    BindingState(
                        "builtin",
                        (module_name, name) in self._builtin_star_conflicts,
                        False,
                    ),
                    "module",
                ),
            )
            self._binding_index[(key, name)] = virtual
            return virtual
        return ()

    def walk(self) -> Iterator[Model]:
        """Walk only composition, without re-visiting linked Model objects."""
        return self.model.walk()

    def overrides_for(self, method: Model) -> tuple[OverrideCandidate, ...]:
        """Relations originating at *this exact* method Model object."""
        return self._override_index.get(_ModelIdentity(method), ())

    def bases_for(self, class_model: Model) -> tuple[BaseReference, ...]:
        """Return one independent reference per written base, in source order."""
        return self._base_index.get(_ModelIdentity(class_model), ())


def _validated_extensions(extensions: tuple[str, ...]) -> frozenset[str]:
    """Require explicit, distinct, case-sensitive single filename suffixes."""
    if not isinstance(extensions, tuple) or any(
        not isinstance(ext, str) for ext in extensions
    ):
        raise TypeError("extensions must be a tuple of strings")
    if not extensions:
        raise ValueError("extensions must not be empty")
    for ext in extensions:
        if (
            not ext.startswith(".")
            or len(ext) < 2
            or Path("source" + ext).suffix != ext
            or any(
                char in "/\\*?[]{}" or char.isspace() or ord(char) < 32 for char in ext
            )
        ):
            raise ValueError(f"invalid file extension: {ext!r}")
    if len(set(extensions)) != len(extensions):
        raise ValueError("duplicate file extension")
    return frozenset(extensions)


def _package_paths(
    directory: str | Path,
    *,
    include: Callable[[Path, bool], bool] | None = None,
    extensions: tuple[str, ...] = (".py",),
) -> tuple[Path, list[Path]]:
    """Find selected Python-syntax sources in one local tree, without importing code.

    An __init__.py is optional at every level. Directory/file symlinks are
    not traversed or modeled. The root is always included; an optional
    caller predicate prunes subdirectories and regular matching sources.
    """
    suffixes = _validated_extensions(extensions)
    supplied = Path(directory)
    if supplied.is_symlink():
        raise ValueError("package symlinks are not supported")
    folder = supplied.resolve()
    if not folder.is_dir():
        raise ValueError(f"not a Python source directory: {folder}")

    def raise_walk_error(error: OSError) -> None:
        raise error

    paths: list[Path] = []
    for current, dirs, files in os.walk(
        folder, followlinks=False, onerror=raise_walk_error
    ):
        parent = Path(current)
        dirs[:] = sorted(
            name
            for name in dirs
            if not (parent / name).is_symlink()
            and (include is None or include(parent / name, True))
        )
        for name in sorted(files):
            path = parent / name
            if (
                path.suffix in suffixes
                and not path.is_symlink()
                and (include is None or include(path, False))
            ):
                paths.append(path)
    paths.sort()
    identities: dict[str, Path] = {}
    for path in paths:
        name, _ = _module_identity(folder, path)
        if name in identities:
            raise ValueError(
                f"ambiguous module name {name!r} for {identities[name]} and {path}"
            )
        identities[name] = path
    return folder, paths


def _module_identity(folder: Path, path: Path) -> tuple[str, bool]:
    relative = path.relative_to(folder).with_suffix("")
    is_init = relative.name == "__init__"
    components = relative.parts[:-1] if is_init else relative.parts
    return ".".join((folder.name, *components)), is_init


def parse_package(
    directory: str | Path,
    *,
    index: KindIndex | None = None,
    analyses: Iterable[str] | None = None,
    definitions: ModuleType | ExternalDefinitions | None = None,
    include: Callable[[Path, bool], bool] | None = None,
    extensions: tuple[str, ...] = (".py",),
    import_policy: ImportPolicy = "unrestricted",
    allowed_modules: tuple[str, ...] = (),
    syntax_validation: SyntaxValidation = "compile",
) -> PackageModel:
    """Model selected regular Python-syntax sources without executing them."""
    selected = _selected_analyses(analyses)
    selected_modules = _validated_import_options(import_policy, allowed_modules)
    _validated_syntax_validation(syntax_validation)
    folder, paths = _package_paths(directory, include=include, extensions=extensions)
    resolved_index, prepared = _external_settings(definitions, index)
    modules: dict[str, tuple[Model, bool]] = {}
    source_facts: dict[str, tuple[SyntaxFacts, dict[int, Model]]] = {}
    for path in paths:
        module_name, is_init = _module_identity(folder, path)
        tree = ast.parse(path.read_bytes(), filename=str(path), type_comments=False)
        _compile_check(tree, str(path), syntax_validation)
        _assert_import_policy(
            tree,
            prepared,
            import_policy=import_policy,
            allowed_modules=selected_modules,
        )
        syntax = collect_syntax_facts(tree, include_references=prepared is not None)
        matcher = _ExternalStructures.for_facts(syntax, prepared) if prepared else None
        builder = _Builder(
            resolved_index,
            external=matcher,
            collections=BuiltinCollectionRecognition(tree, syntax),
        )
        modules[module_name] = (builder.module(tree, name=module_name), is_init)
        source_facts[module_name] = (syntax, builder.statement_models)
    package = ModelFactory(resolved_index).make(
        "model.package",
        name=folder.name,
        modules=tuple(module for module, _ in modules.values()),
    )
    builtin_stars: set[tuple[str, str]] = set()
    candidates, bases, bindings = _analyze_package_facts(
        modules, selected, source_facts, builtin_star_sink=builtin_stars
    )
    return PackageModel(
        package,
        candidates,
        bases,
        selected,
        bindings,
        _builtin_star_conflicts=frozenset(builtin_stars),
        _complete=True,
    )
