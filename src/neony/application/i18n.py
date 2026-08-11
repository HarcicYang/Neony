"""Framework i18n — chainable ``tr`` proxy + typed per-language catalogs.

- :class:`Catalog` is a frozen Pydantic model: each field is a translation
  key with an English default, and each language gets its own instance.
  Apps subclass it, adding flat ``str`` fields or nested sub-model groups;
  pydantic class defaults give per-key English fallback automatically.
- ``tr`` is a chainable proxy: ``tr.common.copy`` returns a
  :class:`~neony.dom.Computed` that re-resolves whenever the active
  language changes — bind it into any ``ReactiveText`` slot (Text,
  Button, ...) for live language switching without losing widget state.
- ``tr_now(tr.xx.xxx)`` reads the current value immediately, without
  subscribing — for display-time resolution (component defaults, menus).

The active language and per-language catalogs are module-level state
shared by every window in the process (mirroring theme state on the app).
Register catalogs at startup; a mid-session registration is only picked
up after the language changes again.

Reserved key names: any translation key that collides with
:class:`~neony.dom.Computed`'s API (``get``, ``format``) or starts with
``_`` is shadowed and cannot be referenced through the ``tr`` chain.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from neony.dom import Computed, Signal, untrack


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


class Common(BaseModel):
    """Framework-owned shared labels (context menus, dialog actions)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ``copy`` is a reserved pydantic v1 name (shadows BaseModel.copy) —
    # the key is ``copy_text`` but the resolved label stays "Copy".
    copy_text: str = "Copy"
    delete: str = "Delete"
    ok: str = "OK"
    cancel: str = "Cancel"
    close: str = "Close"


class Catalog(BaseModel):
    """Translation catalog — one field per key, English defaults.

    Subclass to add app keys (flat ``str`` fields or nested sub-model
    groups) and build one instance per language.  An instance that
    overrides nothing shows the English class defaults, so ``en`` needs
    no explicit registration beyond the base catalog.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    common: Common = Common()


#: Active language — reactive: ``tr`` Computeds subscribe to it.
_language: Signal[Language] = Signal(Language.EN)
#: Per-language catalogs; ``en`` always resolves to the base defaults.
_catalogs: dict[Language, Catalog] = {Language.EN: Catalog()}


def get_language() -> Language:
    """The active language (reads without subscribing)."""
    return untrack(_language.get)


def set_language(language: Language | str) -> None:
    """Switch the active language.  An invalid code raises ValueError; a
    valid language with no registered catalog falls back to English."""
    _language.set(Language(language))


def register_catalog(language: Language, catalog: Catalog) -> None:
    """Register the translation instance for *language* (startup-time)."""
    _catalogs[Language(language)] = catalog


def _resolve(path: tuple[str, ...], params: dict[str, object] | None = None) -> str:
    language = _language()
    for catalog in (_catalogs.get(language), _catalogs[Language.EN]):
        if catalog is None:
            continue
        node: object = catalog
        try:
            for part in path:
                node = getattr(node, part)
        except AttributeError:
            continue
        if not isinstance(node, str):
            raise TypeError(f"i18n key {'.'.join(path)!r} resolves to a non-string field")
        if params:
            node = node.format(**params)
        return node
    raise KeyError(path)


class TrRef(Computed[str]):
    """A reactive translation reference — also chainable.

    ``tr.common.copy`` builds a ``TrRef`` for the path ("common", "copy");
    attribute access appends to the path, so namespaced keys read like
    plain Python.  The reference re-resolves on every language change.
    """

    def __init__(self, path: tuple[str, ...], params: dict[str, object] | None = None) -> None:
        self._path = path
        self._params = params
        super().__init__(lambda: _resolve(path, params))

    def __getattr__(self, name: str) -> TrRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return TrRef((*self._path, name), self._params)

    def format(self, **params: object) -> TrRef:
        """Interpolate ``{placeholder}`` values in the resolved string."""
        merged = {**(self._params or {}), **params}
        return TrRef(self._path, merged)


class _TrRoot:
    def __getattr__(self, name: str) -> TrRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return TrRef((name,))


tr = _TrRoot()


def tr_now(ref: Computed[str]) -> str:
    """The current value of a ``tr`` chain, without subscribing.

    For display-time reads (component defaults, menu items) where a live
    binding isn't wanted — safe inside effects (no dependency leaks).
    """
    return untrack(ref.get)
