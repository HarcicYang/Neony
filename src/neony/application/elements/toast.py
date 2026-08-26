"""Toast component — transient in-app notifications from a screen edge.

A host component: mount one ``Toast`` at the page root (like
:class:`Dialog`); ``placement`` picks which corner/edge notifications
stack against, and :meth:`Toast.show` pushes a card that auto-dismisses
after ``duration`` seconds.  Each card enters with a placement-specific
directional animation — sliding in from the edge/corner it sits at
(top placements drop down, bottom ones rise up, corners slide
diagonally) — and leaves by replaying the same keyframe reversed,
sliding back toward that edge/corner.

NOTE: the host is a full-viewport ``position: fixed`` notification layer at
``z-index: 1200`` (above Dialog and dropdown/cascade popups) with ``pointer-events: none``, so
clicks pass through to the page except on the cards themselves.  Mount
it at the page root — any ``backdrop-filter`` / ``transform`` ancestor
would become the containing block for ``position: fixed`` in WebKit
(Dialog precedent).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any, Literal

from neony.application.theme import stub
from neony.dom import (
    Animation,
    Border,
    BoxShadow,
    Color,
    Div,
    DOMElement,
    DomEvent,
    Filter,
    Shadow,
    Span,
    Styles,
)
from neony.dom import Button as _ButtonElem

from .base import Component
from .icon import Icon

_Placement = Literal[
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]
_Type = Literal["success", "info", "error"]

# The enter keyframes live in _BUILTIN_KEYFRAMES as ``neony-toast-in-<suffix>``
# with the 0% offset pointing at this placement; the exit replays the same
# keyframe reversed, so the card leaves toward the same edge/corner.
_PLACEMENT_SUFFIX: dict[str, str] = {
    "top-left": "tl",
    "top-center": "tc",
    "top-right": "tr",
    "bottom-left": "bl",
    "bottom-center": "bc",
    "bottom-right": "br",
}

_ROOT = Styles(
    position="fixed",
    top="0",
    left="0",
    right="0",
    bottom="0",
    z_index="1200",
    pointer_events="none",
    display="flex",
    flex_direction="column",
    gap="8px",
    padding="16px",
)

_CARD = Styles(
    pointer_events="auto",
    display="flex",
    align_items="center",
    gap="10px",
    max_width="360px",
    padding="12px 14px",
    border_radius="10px",
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="20px", saturate=1.2),
    border=Border(width="1px", color=stub.border_glass),
    box_shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=24, color=stub.shadow)]),
)

_DOT = Styles(width="8px", height="8px", border_radius="50%", flex_shrink="0")

_TEXT = Styles(flex_grow="1", color=stub.text_primary, font_size="14px", line_height="1.4")

_CLOSE = Styles(
    display="flex",
    align_items="center",
    justify_content="center",
    flex_shrink="0",
    width="22px",
    height="22px",
    padding="0",
    border="none",
    border_radius="50%",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    font_size="12px",
    cursor="pointer",
)

_TYPE_COLORS: dict[str, Color] = {
    "success": stub.success,
    "info": stub.accent,
    "error": stub.danger,
}


class _Card:
    """One live toast card: the DOM node, its ✕ button, and the optional
    click callback (the ✕ itself never fires it)."""

    __slots__ = ("close", "el", "exiting", "on_click")

    def __init__(self, el: Div, close: _ButtonElem, on_click: Callable[[], Any] | None = None) -> None:
        self.el = el
        self.close = close
        self.exiting = False
        self.on_click = on_click


class Toast(Component):
    #: Wired internally — card + ✕ clicks (routed by key).
    _bound_events: frozenset[str] = frozenset({"click"})

    """Transient notifications stacked at a chosen screen edge.

    - ``toast.show(text, type=...)`` pushes a card — success / info /
      error pick the accent dot colour; ``duration`` overrides the host
      default, and ``0`` sticks until the ✕ is clicked; ``on_click`` is
      an optional callback (sync or async) fired when the card is
      clicked — the ✕ never fires it
    - ``toast.clear()`` removes everything immediately
    - ``placement`` — which corner/edge the stack hugs; enter and exit
      animations are directionally tied to it
    - ``top_offset`` — where top placements start (below a ``TitleBar``,
      e.g. ``"40px"``); bottom placements always hug the window edge
    """

    def __init__(
        self,
        *,
        placement: _Placement = "top-right",
        duration: float = 3.0,
        max_toasts: int = 5,
        top_offset: str = "0px",
    ) -> None:
        super().__init__()
        self._placement = placement
        self._duration = duration
        self._max_toasts = max_toasts
        self._top_offset = top_offset
        self._prepend = placement.startswith("top")
        self._suffix = _PLACEMENT_SUFFIX[placement]
        self._cards: list[_Card] = []
        self._card_by_close: dict[str, _Card] = {}
        self._tasks: dict[_Card, asyncio.Task] = {}

        self._root = Div(
            styles=_ROOT.model_copy(update=self._alignment(placement, top_offset)),
            container=[],
            args={"aria-live": "polite"},
        )

    # ---- state ----

    @property
    def placement(self) -> str:
        """The corner/edge the stack hugs (readable, writable)."""
        return self._placement

    @placement.setter
    def placement(self, value: _Placement) -> None:
        """Move the stack to another corner/edge.  New cards use that
        placement's directional animation; cards already on screen keep
        theirs."""
        if value == self._placement:
            return
        self._placement = value
        self._prepend = value.startswith("top")
        self._suffix = _PLACEMENT_SUFFIX[value]
        self._root.styles = self._root.styles.model_copy(update=self._alignment(value, self._top_offset))

    @staticmethod
    def _alignment(placement: str, top_offset: str) -> dict[str, str]:
        if placement.endswith("left"):
            align = "flex-start"
        elif placement.endswith("right"):
            align = "flex-end"
        else:
            align = "center"
        return {
            "align_items": align,
            "justify_content": "flex-start" if placement.startswith("top") else "flex-end",
            # Top placements start below ``top_offset`` — e.g. a 40px
            # TitleBar — so notifications never sit under the chrome.
            "top": top_offset if placement.startswith("top") else "0",
        }

    # ---- public API ----

    def show(
        self,
        text: str,
        *,
        type: _Type = "info",
        duration: float | None = None,
        on_click: Callable[[], Any] | None = None,
    ) -> None:
        """Push a notification card onto the stack.

        ``type`` selects the accent dot colour (success / info / error);
        ``duration`` overrides the host default, and ``0`` sticks until
        the ✕ is clicked.  ``on_click`` — a sync or async callback fired
        when the card is clicked (the ✕ never fires it).
        """
        if duration is None:
            duration = self._duration
        card, close = self._build_card(text, type, on_click)
        record = _Card(card, close, on_click)
        self._card_by_close[close.key] = record
        if self._prepend:
            self._cards.insert(0, record)  # top stacks: newest sits on top
            self._root.container.insert(0, card)
        else:
            self._cards.append(record)  # bottom stacks: newest hugs the edge
            self._root.container.append(card)

        if duration is not None and duration > 0:
            self._schedule_dismiss(record, duration)
        if len(self._cards) > self._max_toasts:
            # Evict the card furthest from the edge it hugs.
            oldest = self._cards[-1] if self._prepend else self._cards[0]
            self._schedule_dismiss(oldest, 0.0)

    def clear(self) -> None:
        """Remove every card immediately (cancels pending auto-dismiss)."""
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        for record in self._cards:
            record.exiting = True
        self._cards.clear()
        self._card_by_close.clear()
        self._root.container.clear()

    # ---- internals ----

    def _build_card(self, text: str, type: _Type, on_click: Callable[[], Any] | None = None) -> tuple[Div, _ButtonElem]:
        dot = Span(styles=_DOT.model_copy(update={"background_color": _TYPE_COLORS[type]}))
        label = Span(container=[text], styles=_TEXT)
        close = _ButtonElem(type="button", container=[Icon._font("close").render("12px")], styles=_CLOSE)
        self._bind(close, "click")
        card_styles = _CARD.model_copy(update={"animation": self._enter_animation()})
        if on_click is not None:
            card_styles = card_styles.model_copy(update={"cursor": "pointer"})
        card = Div(
            styles=card_styles,
            container=[dot, label, close],
            args={"role": "status"},
        )
        # Clicks on the dot/label (keyed but handler-less) bubble here;
        # the ✕ has its own handler, so it never reaches this path.
        card.bubble_events = True
        self._bind(card, "click")
        return card, close

    def _enter_animation(self) -> Animation:
        return Animation(name=f"neony-toast-in-{self._suffix}", duration="0.18s", timing="ease-out")

    def _exit_animation(self) -> Animation:
        # Reverse the placement's enter keyframe so the card slides back
        # toward the edge/corner it appeared from; ease-out (fast start,
        # settle) reads as the card accelerating away; fill forwards holds
        # the hidden end state until the node is removed.
        return Animation(
            name=f"neony-toast-in-{self._suffix}",
            duration="0.15s",
            timing="ease-out",
            direction="reverse",
            fill_mode="forwards",
        )

    def _schedule_dismiss(self, record: _Card, delay: float) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no running event loop — the card sticks until clear()/✕
        task = asyncio.create_task(self._auto_dismiss(record, delay))
        self._tasks[record] = task
        task.add_done_callback(lambda _t, r=record: self._tasks.pop(r, None))

    async def _auto_dismiss(self, record: _Card, delay: float) -> None:
        if delay > 0:
            await asyncio.sleep(delay)
        await self._dismiss(record)

    async def _dismiss(self, record: _Card) -> None:
        """Play the exit animation, then remove the card."""
        if record.exiting:
            return
        record.exiting = True
        task = self._tasks.pop(record, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        record.el.styles = record.el.styles.model_copy(update={"animation": self._exit_animation()})
        await asyncio.sleep(0.2)
        self._remove(record)

    def _remove(self, record: _Card) -> None:
        if record in self._cards:
            self._cards.remove(record)
        self._card_by_close.pop(record.close.key, None)
        # Already removed when clear() raced the exit animation.
        with contextlib.suppress(ValueError):
            self._root.container.remove(record.el)

    def _card_for_key(self, key: str) -> _Card | None:
        """The card whose subtree *key* belongs to (None when it's an
        unknown key).  The ✕ keys are resolved first, so they never reach
        this — card clicks only."""
        for record in self._cards:
            if self._subtree_contains(record.el, key):
                return record
        return None

    @staticmethod
    def _subtree_contains(el: DOMElement, key: str) -> bool:
        if el.key == key:
            return True
        return any(isinstance(child, DOMElement) and Toast._subtree_contains(child, key) for child in el.container)

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type != "click":
            await self._dispatch(event_type, event)
            return
        # The ✕ carries its own handler and key — a click there dismisses
        # and never counts as a card click.
        record = self._card_by_close.get(event.key)
        if record is not None:
            await self._dismiss(record)
            return
        record = self._card_for_key(event.key)
        if record is not None and record.on_click is not None:
            result = record.on_click()
            if asyncio.iscoroutine(result):
                await result
