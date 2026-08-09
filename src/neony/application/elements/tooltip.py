"""Tooltip component — a hover bubble anchored to its child.

The root is a ``position: relative`` inline-flex wrapper holding the
anchor (the wrapped child) plus an absolutely-positioned panel with
per-placement offsets — no measurement channel needed.

Hover is driven by the engine's ``mouseover`` / ``mouseout`` pair, which
bubble and carry ``related_key`` — the keyed element the pointer moved
from/to.  A real enter is a ``mouseover`` whose related key is NOT
inside the wrapper's subtree; a real leave is the mirror ``mouseout``.
Inner-child hops (moving between the anchor's own elements) have a
related key inside the wrapper and stay silent — the earlier
mouseover/mouseout version treated each hop as enter+leave and kept
cancelling the show timer, which is why hover never worked.  (Native
``mouseenter`` / ``mouseleave`` can't be used: they do not propagate,
so no document listener can ever delegate them.)

Entering starts the ``delay`` timer; leaving cancels it and hides
immediately.  The show task is awaited inline: the bridge's event pool
cancels fire-and-forget tasks once the handler returns, which kept the
bubble from ever appearing.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from neony.application.theme import stub
from neony.dom import Div, DOMElement, DomEvent, Span, Styles, Transition

from .base import Component

_WRAP = Styles(position="relative", display="inline-flex")

_BUBBLE = Styles(
    position="absolute",
    z_index="300",
    display="none",
    white_space="nowrap",
    padding="6px 10px",
    border_radius="6px",
    background_color=stub.surface_raised,
    border="1px solid var(--color-border)",
    color=stub.text_primary,
    font_size="12px",
    box_shadow="0 4px 12px var(--color-shadow)",
    transition=Transition(property="opacity", duration="0.15s", timing="ease"),
)

# Per-placement offsets — all anchor-relative, zero measurement.
_PLACEMENTS: dict[str, Styles] = {
    "top": Styles(bottom="calc(100% + 8px)", left="50%", transform="translateX(-50%)"),
    "bottom": Styles(top="calc(100% + 8px)", left="50%", transform="translateX(-50%)"),
    "left": Styles(top="50%", right="calc(100% + 8px)", transform="translateY(-50%)"),
    "right": Styles(top="50%", left="calc(100% + 8px)", transform="translateY(-50%)"),
}


class Tooltip(Component):
    #: Wired internally.  mouseover/mouseout bubble and carry
    #: ``related_key``; the boundary check lives in ``_on_event``.
    _bound_events: frozenset[str] = frozenset({"mouseover", "mouseout", "focus", "blur"})

    """A hover bubble anchored to its wrapped child.

    - ``text`` — the bubble's content (first positional argument)
    - ``anchor`` — the wrapped element (a component is built on
      construction; a plain string is wrapped in a Span)
    - ``placement`` — ``"top"`` (default) / ``"bottom"`` / ``"left"``
      / ``"right"``
    - ``delay`` — seconds of hover before the bubble appears (default
      0.4); moving out cancels it and hides immediately
    """

    def __init__(
        self,
        text: str = "",
        *,
        anchor: Component | DOMElement | str | None = None,
        placement: Literal["top", "bottom", "left", "right"] = "top",
        delay: float = 0.4,
    ) -> None:
        super().__init__()
        self._delay = delay
        self._task: asyncio.Task | None = None

        if anchor is None:
            anchor_el: DOMElement | str = Span(container=[""])
        elif isinstance(anchor, Component):
            anchor_el = anchor.build()
        elif isinstance(anchor, str):
            anchor_el = Span(container=[anchor])  # element-only children (reactive mode)
        else:
            anchor_el = anchor
        self._bubble = Div(
            styles=_BUBBLE.model_copy(update=_PLACEMENTS[placement].model_dump(exclude_none=True)),
            container=[text],
        )
        self._root = Div(styles=_WRAP, container=[anchor_el, self._bubble])
        # Enter/leave/focus events target the keyed anchor — bubble them
        # to the wrapper, or the tooltip never sees them.
        self._root.bubble_events = True
        self._bind(self._root, "mouseover")
        self._bind(self._root, "mouseout")
        self._bind(self._root, "focus")
        self._bind(self._root, "blur")

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            if self._related_inside(event.related_key):
                return
            self._cancel_task()
            self._task = asyncio.create_task(self._show_after_delay())
            await self._task  # We can't put it aside due to probabale event pool design. Hahaha
        elif event_type == "mouseout":
            if self._related_inside(event.related_key):
                return
            self._cancel_task()
            self._hide()

    def _related_inside(self, key: str | None) -> bool:
        """True when *key* belongs to the wrapper's subtree — the
        pointer is still inside, so no enter/leave fires."""
        if key is None:
            return False
        stack = [self._root]
        while stack:
            el = stack.pop()
            if el.key == key:
                return True
            stack.extend(c for c in el.container if isinstance(c, DOMElement))
        return False

    def _hide(self) -> None:
        self._cancel_task()
        self._bubble.styles = self._bubble.styles.model_copy(update={"display": "none"})

    def _cancel_task(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _show_after_delay(self) -> None:
        try:
            await asyncio.sleep(self._delay)
            self._bubble.styles = self._bubble.styles.model_copy(update={"display": "block"})
        except asyncio.CancelledError:
            return
