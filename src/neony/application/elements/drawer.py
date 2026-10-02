"""Drawer — a portal-backed edge panel with a modal scrim."""

from __future__ import annotations

import asyncio
from typing import Literal, Self

from neony.application.theme import stub
from neony.dom import Animation, Border, Div, DOMElement, DomEvent, Styles

from ..layers import Layer, LayerHandle, layer_manager
from ._overlay import mark_portal
from .base import Component, ReactiveText, _mount_text

DrawerSide = Literal["left", "right", "top", "bottom"]

_ROOT = Styles(position="fixed", top="0", right="0", bottom="0", left="0", display="none")
_ROOT_OPEN = _ROOT.model_copy(update={"display": "flex"})
_SCRIM = Styles(
    position="absolute",
    top="0",
    right="0",
    bottom="0",
    left="0",
    background_color=stub.bg_overlay,
    opacity=0,
)
_SCRIM_OPEN = _SCRIM.model_copy(update={"opacity": 1.0})
_PANEL = Styles(
    position="absolute",
    display="flex",
    flex_direction="column",
    gap="12px",
    padding="20px",
    background_color=stub.surface,
    border=Border(width="1px", color=stub.border),
)


def _panel_style(side: DrawerSide, size: str) -> Styles:
    if side == "left":
        return _PANEL.model_copy(update={"left": "0", "top": "0", "bottom": "0", "width": size})
    if side == "right":
        return _PANEL.model_copy(update={"right": "0", "top": "0", "bottom": "0", "width": size})
    if side == "top":
        return _PANEL.model_copy(update={"left": "0", "right": "0", "top": "0", "height": size})
    return _PANEL.model_copy(update={"left": "0", "right": "0", "bottom": "0", "height": size})


class Drawer(Component):
    """A modal edge panel that slides in from the chosen side."""

    _bound_events: frozenset[str] = frozenset({"click", "keydown", "open", "close"})

    def __init__(
        self,
        content: Component | DOMElement,
        *,
        title: ReactiveText = "",
        side: DrawerSide = "right",
        width: str = "360px",
        open: bool = False,
        closable: bool = True,
    ) -> None:
        super().__init__()
        if side not in ("left", "right", "top", "bottom"):
            raise ValueError(f"Drawer: invalid side {side!r}")
        self._side = side
        self._open = False
        self._closable = closable
        self._layer_handle: LayerHandle | None = None
        self._close_task: asyncio.Task | None = None

        self._scrim = Div(styles=_SCRIM)
        header_parts: list[DOMElement | str] = []
        self._title_span = Div(styles=Styles(font_size="18px", font_weight="600", color=stub.text_primary))
        self._title_span.id_ = self._title_span.key
        _mount_text(self._title_span, title)
        if title:
            header_parts.append(self._title_span)
        content_el = content.build() if isinstance(content, Component) else content
        self._panel = Div(
            styles=_panel_style(side, width),
            container=[*header_parts, content_el],
        )
        self._panel_restore = self._panel.styles
        self._root = Div(
            styles=_ROOT,
            args={"role": "dialog", "aria-modal": "true", "aria-labelledby": self._title_span.key},
            container=[self._scrim, self._panel],
        )
        mark_portal(self._root)
        self._bind(self._scrim, "click")
        self._bind(self._root, "keydown")
        if open:
            self.open = True

    @property
    def open(self) -> bool:
        return self._open

    @open.setter
    def open(self, value: bool) -> None:
        if value == self._open:
            return
        self._open = value
        if value:
            self._cancel_close()
            self._root.styles = _ROOT_OPEN
            self._scrim.styles = _SCRIM_OPEN
            self._panel.styles = self._panel_restore.model_copy(
                update={
                    "animation": Animation(
                        name=f"neony-drawer-in-{self._side}",
                        duration="0.22s",
                        timing="ease-out",
                    )
                }
            )
            self._layer_handle = layer_manager(self._root).open(
                self._root,
                kind=Layer.MODAL,
                group="drawer",
                on_close=self._close_from_layer,
                focus_scope="trap",
            )
        else:
            if self._layer_handle is not None:
                self._layer_handle.close()
                self._layer_handle = None
            self._scrim.styles = _SCRIM
            self._panel.styles = self._panel_restore.model_copy(
                update={
                    "animation": Animation(
                        name=f"neony-drawer-in-{self._side}",
                        duration="0.18s",
                        timing="ease-in",
                        direction="reverse",
                        fill_mode="forwards",
                    )
                }
            )
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                self._complete_close()
            else:
                self._close_task = asyncio.create_task(self._finish_close())
        self._dispatch_pseudo("open" if value else "close", self)

    def _close_from_layer(self) -> None:
        self.open = False

    async def _finish_close(self) -> None:
        try:
            await asyncio.sleep(0.2)
            if not self._open:
                self._complete_close()
        finally:
            if self._close_task is asyncio.current_task():
                self._close_task = None

    def _complete_close(self) -> None:
        self._panel.styles = self._panel_restore
        self._root.styles = _ROOT

    def _cancel_close(self) -> None:
        if self._close_task is not None:
            self._close_task.cancel()
            self._close_task = None

    def on_open(self, fn) -> Self:
        return self.on("open", fn)

    def on_close(self, fn) -> Self:
        return self.on("close", fn)

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if (event_type == "click" and event.key == self._scrim.key and self._closable) or (
            event_type == "keydown"
            and event.value == "Escape"
            and not layer_manager(self._root).handle_escape(self._root)
        ):
            self.open = False
        await self._dispatch(event_type, event)
