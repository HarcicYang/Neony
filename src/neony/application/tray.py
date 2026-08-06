"""System tray — native icon with a context menu (lumiview .dev4).

Neony-typed wrapper over lumiview's tray API: :class:`TrayItem` is pure
data (text / id / accelerator / on_activate / checked), :class:`Tray`
carries the icon + menu + behaviour flags.  Assign ``app.tray = tray``
before :meth:`~neony.application.NeonApplication.run`; the icon
materializes once the app is up (``Menu.create`` / ``TrayIcon.create``
need the main thread).  ``close_to_tray=True`` intercepts window close
requests and hides the whole app instead of quitting — restore from the
tray menu or a left click (on macOS a Dock click).

Platform notes: Linux needs libayatana-appindicator; the tooltip is
unsupported there and the menu cannot be replaced after creation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class TrayItem(BaseModel):
    """One native tray-menu entry (pure data).

    - ``text`` — the label
    - ``id`` — stable id carried by activation callbacks
    - ``accelerator`` — muda syntax (e.g. ``"CmdOrCtrl+Q"``); Windows
      may not fire it from the keyboard
    - ``on_activate`` — sync or async handler, run on the asyncio loop
      (never the GUI thread)
    - ``checked=True`` renders a check item (CheckMenuItem)
    """

    text: str
    id: str | None = None
    accelerator: str | None = None
    on_activate: Callable[[Any], Any] | None = None
    checked: bool | None = None

    #: Internal marker for :meth:`separator` (excluded from the model).
    _separator: bool = False

    def __init__(
        self,
        text: str = "",
        *,
        id: str | None = None,
        accelerator: str | None = None,
        on_activate: Callable[[Any], Any] | None = None,
        checked: bool | None = None,
    ) -> None:
        # Hand-written __init__ so ``text`` is positional, like the
        # component constructors (pydantic v2 only takes keywords).
        super().__init__(
            text=text,
            id=id,
            accelerator=accelerator,
            on_activate=on_activate,
            checked=checked,
        )

    @classmethod
    def separator(cls) -> TrayItem:
        """A menu divider."""
        item = cls(text="")
        item._separator = True
        return item


class Tray(BaseModel):
    """System tray configuration — assign to ``app.tray`` before run().

    - ``icon`` — a file path or raw RGBA ``(bytes, width, height)``
      (same accepted forms as ``WindowConfig.icon``)
    - ``tooltip`` — hover text (unsupported on Linux)
    - ``items`` — menu entries; empty = no menu
    - ``menu_on_left_click`` — also open the menu on left click
      (default True; set False to free left-click for ``on_left_click``)
    - ``on_left_click`` — sync or async handler for a left-click on the
      icon (typical use: toggle the window); ignored while the menu
      opens on left click
    - ``close_to_tray`` — intercept window close and hide the app
      instead of quitting (restore from the menu / tray click)
    """

    icon: str | tuple[bytes, int, int]
    tooltip: str | None = None
    items: list[TrayItem] = Field(default_factory=list)
    menu_on_left_click: bool = True
    on_left_click: Callable[[Any], Any] | None = None
    close_to_tray: bool = False

    def _to_lumiview_items(self) -> list[Any]:
        """Map the Neony items to lumiview menu items (pure data —
        materialized by ``Menu.create`` on the main thread)."""
        from lumiview.menu import CheckMenuItem, MenuItem, PredefinedMenuItem

        result: list[Any] = []
        for item in self.items:
            if item._separator:
                result.append(PredefinedMenuItem.separator())
            elif item.checked is not None:
                result.append(
                    CheckMenuItem(
                        text=item.text,
                        id=item.id,
                        accelerator=item.accelerator,
                        checked=item.checked,
                        on_activate=item.on_activate,
                    )
                )
            else:
                result.append(
                    MenuItem(
                        text=item.text,
                        id=item.id,
                        accelerator=item.accelerator,
                        on_activate=item.on_activate,
                    )
                )
        return result
