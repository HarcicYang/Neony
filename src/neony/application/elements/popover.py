"""Popover — a portal-backed anchored floating surface."""

from __future__ import annotations

import json
from typing import Literal

from neony.application.theme import stub
from neony.dom import Border, BoxShadow, Div, DOMElement, DomEvent, Filter, Shadow, Span, Styles

from .. import motion
from ..layers import Layer, LayerHandle, layer_manager
from ._overlay import mark_portal
from .base import Component

Placement = Literal["top", "right", "bottom", "left"]
Align = Literal["start", "center", "end"]

_ROOT = Styles(display="inline-flex", position="relative")
_PANEL = Styles(
    position="fixed",
    display="none",
    flex_direction="column",
    min_width="180px",
    max_width="calc(100vw - 16px)",
    max_height="calc(100vh - 16px)",
    overflow="auto",
    padding="12px",
    border_radius="9px",
    border=Border(width="1px", color=stub.border_glass),
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="20px", saturate=1.2),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=stub.shadow)]),
)
_PANEL_OPEN = _PANEL.model_copy(update={"display": "flex", "animation": motion.popup_animation(fill_mode="both")})


class Popover(Component):
    """An anchored surface positioned by the browser runtime."""

    _bound_events: frozenset[str] = frozenset({"keydown", "outsideclick", "open", "close"})

    def __init__(
        self,
        anchor: Component | DOMElement | str,
        content: Component | DOMElement,
        *,
        placement: Placement = "bottom",
        align: Align = "start",
        open: bool = False,
        owner: Component | DOMElement | None = None,
        focus_scope: Literal["none", "trap"] = "none",
        initial_focus: Component | DOMElement | None = None,
    ) -> None:
        super().__init__()
        anchor_el = anchor.build() if isinstance(anchor, Component) else anchor
        if isinstance(anchor_el, str):
            anchor_el = Span(container=[anchor_el])
        self._anchor = anchor_el
        self._content = content
        self._placement = placement
        self._align = align
        self._open = False
        self._owner = owner
        self._focus_scope = focus_scope
        self._initial_focus = initial_focus
        self._layer_handle: LayerHandle | None = None

        content_el = content.build() if isinstance(content, Component) else content
        self._panel = Div(styles=_PANEL, container=[content_el], args={"role": "dialog"})
        mark_portal(self._panel)
        self._root = Div(styles=_ROOT, container=[self._anchor, self._panel])
        self._root.bubble_events = True
        self._bind(self._panel, "keydown")
        self._bind(self._panel, "outsideclick")
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
            owner_el = self._owner._root if isinstance(self._owner, Component) else self._owner
            initial = self._initial_focus.build() if isinstance(self._initial_focus, Component) else self._initial_focus
            self._panel.styles = _PANEL_OPEN
            self._panel.args = {
                **self._panel.args,
                "data-neony-outside": "true",
                "data-neony-outside-anchor": self._anchor.key,
                "data-neony-popover-anchor": self._anchor.key,
                "data-neony-popover-placement": self._placement,
                "data-neony-popover-align": self._align,
            }
            self._layer_handle = layer_manager(self._root).open(
                self._panel,
                kind=Layer.POPOVER,
                group="popover",
                exclusive=True,
                owner=owner_el,
                on_close=self._close_from_layer,
                focus_scope=self._focus_scope,
                initial_focus=initial,
            )
            self._position()
        else:
            if self._layer_handle is not None:
                self._layer_handle.close()
                self._layer_handle = None
            self._panel.styles = _PANEL
            self._panel.args = {
                key: value
                for key, value in self._panel.args.items()
                if key
                not in {
                    "data-neony-outside",
                    "data-neony-outside-anchor",
                    "data-neony-popover-anchor",
                    "data-neony-popover-placement",
                    "data-neony-popover-align",
                }
            }
        self._dispatch_pseudo("open" if value else "close", self)

    def toggle(self) -> None:
        self.open = not self._open

    def _close_from_layer(self) -> None:
        self.open = False

    def _position(self) -> None:
        key = json.dumps(self._panel.key)
        self._schedule_js(f"window.__neonyPopoverPosition({key})")

    def on_open(self, fn) -> Popover:
        return self.on("open", fn)

    def on_close(self, fn) -> Popover:
        return self.on("close", fn)

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "keydown" and event.value == "Escape":
            if not layer_manager(self._root).handle_escape(self._panel):
                self.open = False
        elif event_type == "outsideclick":
            self.open = False
        await self._dispatch(event_type, event)
