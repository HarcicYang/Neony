"""Framework i18n — typed per-language catalogs + reactive ``tr`` refs.

- :class:`TrRef` is a reactive translation reference: ``tr.common.copy_text``
  returns one that re-resolves whenever the active language changes.  Bind it
  into any ``ReactiveText`` slot (Text, Button, ...) for live language
  switching without losing widget state.
- A :class:`Catalog` is a frozen Pydantic model whose fields are ``TrRef``
  keys; sub-models group keys by section.  Each language gets its own catalog
  instance — fields written as plain strings (``Nav(home="首页")``) become
  translated override refs automatically.
- ``tr_now(tr.xx)`` reads the current value immediately, without subscribing
  — for display-time resolution (component defaults, menus).
- The path of a ``TrRef`` (``("nav", "home")``) is injected automatically by
  :func:`_inject_paths` after every catalog instance is built; never hand-write
  paths when declaring a catalog.

The active language and per-language catalogs are module-level state shared by
every window in the process (mirroring theme state on the app).  Register
catalogs at startup; a mid-session registration is only picked up after the
language changes again.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_core import core_schema

from neony.dom import Computed, Signal, untrack

S = TypeVar("S")
"""Type-parameter of a :class:`TrRef`: the keys' interpolation-param shape.

``TrRef[None]`` means no interpolation; ``TrRef[dict[str, str]]`` means
``.format(value="x")`` etc.  Used only for static typing — at runtime a
``TrRef`` carries an opaque ``params`` dict.
"""


class Language(StrEnum):
    """Built-in languages the framework recognizes."""

    EN = "en"
    ZH = "zh"
    JA = "ja"
    FR = "fr"
    DE = "de"
    ES = "es"
    PT = "pt"
    RU = "ru"


LANGUAGES: tuple[Language, ...] = tuple(Language)


_CFG = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)


class TrRef(Computed[str], Generic[S]):
    """A reactive translation reference — also a pydantic field value.

    Write ``TrRef("English default")`` as a field default.  Write a plain
    string (``"首页"``) when constructing a per-language catalog — pydantic
    coerces it into an override ref via :meth:`__get_pydantic_core_schema__`.
    The field path (``("nav", "home")``) is injected after construction.

    Calling :meth:`get` subscribes to the active language signal, so a
    ``TrRef`` read inside an effect / ``bind_text`` fmt re-resolves on
    :func:`set_language`.  Use :func:`tr_now` for an untracked snapshot.
    """

    def __init__(
        self,
        default: str = "",
        *,
        params: dict[str, object] | None = None,
        path: tuple[str, ...] | None = None,
        override: bool = False,
        owner: type[Catalog] | None = None,
        root: Catalog | None = None,
    ) -> None:
        self._default = default
        self._params = params or {}
        self._path = path
        self._override = override
        self._owner = owner
        self._root = root
        super().__init__(self._resolve)

    def _resolve(self) -> str:
        if self._path is None:
            value = self._default
        else:
            language = _language()
            value = _find_registered(self._owner, language, self._path)
            if value is None and language is not Language.EN:
                value = _find_registered(self._owner, Language.EN, self._path)
            if value is None:
                value = self._default
        return value.format(**self._params) if self._params else value

    def format(self, **params: object) -> TrRef[S]:
        """Return a new ref with ``params`` merged in (path preserved)."""
        return TrRef[S](
            self._default,
            params={**self._params, **params},
            path=self._path,
            override=self._override,
            owner=self._owner,
            root=self._root,
        )

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any) -> core_schema.CoreSchema:
        def _coerce(value: object) -> TrRef[Any]:
            if isinstance(value, TrRef):
                return value
            if isinstance(value, str):
                ref: TrRef[Any] = object.__new__(cls)
                TrRef.__init__(ref, value)
                ref._override = True
                return ref
            raise TypeError(f"expected str or TrRef, got {type(value).__name__}")

        return core_schema.no_info_after_validator_function(
            _coerce,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(TrRef),
                    core_schema.str_schema(),
                ]
            ),
        )


def _find_registered(
    owner: type[Catalog] | None,
    language: Language,
    path: tuple[str, ...],
) -> str | None:
    """Resolve a path from the catalog family that declared the ref."""
    if owner is None:
        return None
    catalog = _catalogs.get((owner, language))
    if catalog is not None:
        return _lookup(catalog, path)
    # Framework refs declared on Catalog are shared by application subclasses.
    # A concrete app catalog may therefore satisfy a base Catalog ref, while
    # unrelated catalog families remain isolated.
    if owner is Catalog:
        for (_registered_owner, registered_language), candidate in reversed(tuple(_catalogs.items())):
            if registered_language is language and isinstance(candidate, owner):
                value = _lookup(candidate, path)
                if value is not None:
                    return value
    return None


def _lookup(catalog: Catalog, path: tuple[str, ...]) -> str | None:
    """Walk *path* on *catalog*; return the leaf ``TrRef``'s default str."""
    node: object = catalog
    for part in path:
        if not isinstance(node, BaseModel):
            return None
        try:
            node = getattr(node, part)
        except AttributeError:
            return None
    if not isinstance(node, TrRef):
        return None
    return node._default


def _inject_paths(
    model: BaseModel,
    prefix: tuple[str, ...],
    owner: type[Catalog],
    root: Catalog,
) -> None:
    """Bind each leaf ``TrRef`` to its path and catalog family."""
    for fname in type(model).model_fields:
        value = getattr(model, fname)
        if isinstance(value, TrRef):
            object.__setattr__(
                model,
                fname,
                TrRef(
                    value._default,
                    params=value._params,
                    path=(*prefix, fname),
                    override=value._override,
                    owner=owner,
                    root=root,
                ),
            )
        elif isinstance(value, BaseModel):
            sub = value.model_copy(deep=True)
            _inject_paths(sub, (*prefix, fname), owner, root)
            object.__setattr__(model, fname, sub)


class TrMeta(ModelMetaclass):
    """Mark catalog classes so :func:`_inject_paths` runs post-init.

    The heavy lifting happens in :meth:`Catalog.model_post_init` (instance
    time, with deep copies); this metaclass only stamps the class so the
    framework recognises catalogs without an ``isinstance`` check.
    """

    def __new__(mcs, name, bases, namespace, **kwargs):  # type: ignore[override]
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class Common(BaseModel, metaclass=TrMeta):
    """Framework-owned shared labels (context menus, dialog actions)."""

    model_config = _CFG

    # ``copy`` is a reserved pydantic v1 name (shadows BaseModel.copy) —
    # the key is ``copy_text`` but the resolved label stays "Copy".
    copy_text: TrRef[None] = TrRef("Copy")
    delete: TrRef[None] = TrRef("Delete")
    ok: TrRef[None] = TrRef("OK")
    cancel: TrRef[None] = TrRef("Cancel")
    close: TrRef[None] = TrRef("Close")


class Catalog(BaseModel, metaclass=TrMeta):
    """Translation catalog — one ``TrRef`` field per key.

    Subclass to add app keys.  Flat fields are ``TrRef`` values; nested
    groups are plain :class:`~pydantic.BaseModel` sub-models (NOT ``Catalog``
    subclasses — only the root catalog runs :meth:`model_post_init`, which
    walks the whole tree once).  Build one instance per language: an
    instance that overrides nothing shows the English class defaults, so
    ``en`` needs no explicit registration beyond the base catalog.
    """

    model_config = _CFG

    common: Common = Common()

    def model_post_init(self, __context: object) -> None:
        # Walk the whole instance tree and bind each leaf TrRef to its dotted
        # path.  Runs once per catalog instance; sub-models stay plain
        # BaseModels so they don't independently inject root-relative paths.
        _inject_paths(self, (), type(self), self)
        super().model_post_init(__context)


#: Active language — reactive: ``TrRef.get`` subscribes to it.
_language: Signal[Language] = Signal(Language.EN)
#: Per-language catalogs, isolated by concrete catalog family.
_catalogs: dict[tuple[type[Catalog], Language], Catalog] = {}


def _register_owner(catalog: Catalog) -> type[Catalog]:
    """Return the concrete catalog family used for registration."""
    return type(catalog)


# Base framework defaults are available to framework ``tr`` refs.
_base_catalog = Catalog()
_catalogs[(Catalog, Language.EN)] = _base_catalog


def get_language() -> Language:
    """The active language (reads without subscribing)."""
    return untrack(_language.get)


def set_language(language: Language | str) -> None:
    """Switch the active language.  An invalid code raises ValueError; a
    valid language with no registered catalog falls back to English."""
    _language.set(Language(language))


def register_catalog(language: Language, catalog: Catalog) -> None:
    """Register the translation instance for *language* (startup-time)."""
    _catalogs[(_register_owner(catalog), Language(language))] = catalog


#: Framework-default catalog — only carries :class:`Common` keys.  Apps that
#: subclass :class:`Catalog` define their own module-level ``tr``.
tr: Catalog = Catalog()


def tr_now(ref: TrRef[Any]) -> str:
    """The current value of a ``tr`` ref, without subscribing.

    For display-time reads (component defaults, menu items) where a live
    binding isn't wanted — safe inside effects (no dependency leaks).
    """
    return untrack(ref.get)
