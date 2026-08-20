"""Gallery sections — one module per navigation group.

Each module builds its panels as module-level values and exports
``PANELS`` (tree-leaf key → built panel).  Modules that wire things onto
the page (window-level key handlers, shortcuts, overlays mounted at the
page root) also export ``PAGE_HOOKS``: ``list[Callable[[Page], None]]``
called by :mod:`neony.gallery.assemble` after it creates the page.

The imports below are deliberately static (no importlib / dynamic
loading) so Nuitka can trace every section module when compiling the
gallery entry point.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from neony.application.elements import VStack

from . import buttons, chat, data, forms, glass, home, icons, interaction, layout, system

if TYPE_CHECKING:
    from neony.application import Page

_SECTION_MODULES = (home, buttons, forms, layout, glass, icons, interaction, data, chat, system)

PANELS: dict[str, VStack] = {}
for _module in _SECTION_MODULES:
    PANELS.update(_module.PANELS)

PAGE_HOOKS: list[Callable[[Page], None]] = []
for _module in _SECTION_MODULES:
    PAGE_HOOKS.extend(getattr(_module, "PAGE_HOOKS", []))

del _module
