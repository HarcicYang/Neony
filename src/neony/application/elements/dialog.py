"""Dialog component — a modal overlay with a themed scrim and a
centered panel.

The root is a fixed, full-viewport layer (``z-index: 1000``) that shows
/hides as a whole — the scrim is a keyed child, so clicks inside the
panel resolve to panel-descendant keys and never hit the scrim's close
handler.  Close paths: scrim click (unless ``closable=False``), Escape
(while focus is inside the dialog), and the engine's synthetic
``outsideclick``.

``actions`` render as a row of themed buttons at the bottom — typical
confirm / cancel / close setups; each button's label and variant are
configurable, and clicking runs its callback (called with the dialog)
then closes it unless ``close_on_click=False``.

NOTE: any ``backdrop-filter`` / ``transform`` ancestor becomes the
containing block for ``position: fixed`` in WebKit — mount a Dialog at
the page root or in a non-filtered, non-transformed container.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel

from neony.dom import Animation, Color, Div, DOMElement, DomEvent, Span, Styles, Transition

from .base import Component
from .button import Button


class DialogAction(BaseModel):
    """One themed button in a :class:`Dialog`'s action row.

    - ``text`` — the button label (first positional argument)
    - ``on_click`` — sync or async callback, called with the dialog
    - ``variant`` — ``"primary"`` (default) / ``"ghost"`` / ``"danger"``
    - ``close_on_click`` — close the dialog after the click (default
      True)
    """

    text: str
    on_click: Callable[[Any], Any] | None = None
    variant: Literal["primary", "ghost", "danger"] = "primary"
    close_on_click: bool = True

    def __init__(
        self,
        text: str = "",
        *,
        on_click: Callable[[Any], Any] | None = None,
        variant: Literal["primary", "ghost", "danger"] = "primary",
        close_on_click: bool = True,
    ) -> None:
        # Hand-written __init__ so ``text`` is positional, like the
        # component constructors (pydantic v2 only takes keywords).
        super().__init__(text=text, on_click=on_click, variant=variant, close_on_click=close_on_click)


_ROOT = Styles(
    position="fixed",
    top="0",
    left="0",
    right="0",
    bottom="0",
    z_index="1000",
    display="none",
    align_items="center",
    justify_content="center",
)

# Both open and the closing phase show the root (display:flex); only
# ``_finish_close`` drops it to display:none once the exit has played.
_ROOT_OPEN = _ROOT.model_copy(update={"display": "flex"})

# The scrim dims the whole page — token-driven, so it follows the theme.
# opacity transitions so opening fades the scrim in and closing fades
# it out.
_SCRIM = Styles(
    position="absolute",
    top="0",
    left="0",
    right="0",
    bottom="0",
    background_color=Color(var="--color-bg-overlay"),
    opacity=0.0,
    transition=Transition(property="opacity", duration="0.2s", timing="ease"),
)
_SCRIM_OPEN = _SCRIM.model_copy(update={"opacity": 1.0})

_GLASS_PANEL = Styles(
    position="relative",
    z_index="1",
    max_width="90%",
    max_height="90%",
    overflow="auto",
    padding="20px",
    border_radius="12px",
    background_color=Color(var="--color-surface-panel-glass-bg"),
    backdrop_filter="blur(20px) saturate(1.2)",
    border="1px solid var(--color-border-glass)",
    box_shadow="0 16px 48px var(--color-shadow)",
    transition=Transition(property="opacity", duration="0.2s", timing="ease"),
    animation=Animation(name="fade-slide", duration="0.2s", timing="ease-out"),
)

_SOLID_PANEL = _GLASS_PANEL.model_copy(
    update={
        "background_color": Color(var="--color-surface"),
        "backdrop_filter": None,
        "border": "1px solid var(--color-border)",
    }
)

_TITLE = Styles(
    font_size="16px",
    font_weight="700",
    color=Color(var="--color-text-primary"),
    margin="0 0 12px 0",
)

_ACTION_BAR = Styles(display="flex", justify_content="flex-end", gap="8px", margin_top="16px")


class Dialog(Component):
    #: Wired internally.  ``open`` / ``close`` are pseudo-events
    #: dispatched by the component (TitleBar precedent).
    _bound_events: frozenset[str] = frozenset({"click", "keydown", "outsideclick", "open", "close"})

    """A modal overlay: themed scrim + centered panel with action
    buttons.

    - ``dialog.open`` reads / sets the visible state (immediate write,
      no callback)
    - ``on_open(fn)`` / ``on_close(fn)`` fire on state changes with the
      dialog itself (sync or async callbacks)
    - ``actions`` — a row of themed buttons (confirm / cancel / ...);
      each runs its callback with the dialog, then closes unless
      ``close_on_click=False``
    - ``closable=False`` disables scrim-click closing (Escape and
      outsideclick still close)
    """

    def __init__(
        self,
        *,
        title: str = "",
        content: Component | DOMElement | None = None,
        open: bool = False,
        width: str = "480px",
        glass: bool = True,
        closable: bool = True,
        actions: Sequence[DialogAction] = (),
    ) -> None:
        super().__init__()
        self._open = False
        self._closable = closable
        self._actions = list(actions)
        self._pseudo_tasks: set[asyncio.Task] = set()
        self._close_task: asyncio.Task | None = None

        self._scrim = Div(styles=_SCRIM)
        self._title_span = Span(container=[title], styles=_TITLE)
        header = Div(styles=Styles(display="flex", align_items="center"), container=[self._title_span])
        panel_parts: list[DOMElement | str] = [header]
        if content is not None:
            panel_parts.append(content.build() if isinstance(content, Component) else content)
        if self._actions:
            panel_parts.append(self._build_action_bar())
        panel_style = (_GLASS_PANEL if glass else _SOLID_PANEL).model_copy(update={"width": width})
        self._panel_restore = panel_style
        self._panel = Div(styles=panel_style, container=panel_parts)
        self._root = Div(styles=_ROOT, container=[self._scrim, self._panel])
        # Keydowns from anything focused inside the dialog bubble here.
        self._root.bubble_events = True

        self._bind(self._scrim, "click")
        self._bind(self._root, "keydown")
        self._bind(self._root, "outsideclick")

        if open:
            self.open = True

    # ---- state ----

    @property
    def open(self) -> bool:
        return self._open

    @open.setter
    def open(self, value: bool) -> None:
        if value == self._open:
            return
        self._open = value
        if value:
            # Cancel any in-flight closing fade, then show: scrim fades in over 0.2s, the panel plays its rise-in.
            self._cancel_close()
            self._root.styles = _ROOT_OPEN
            self._scrim.styles = _SCRIM_OPEN
            self._root.args = {**self._root.args, "data-neony-outside": "true"}
        else:
            self._root.styles = _ROOT_OPEN
            self._scrim.styles = _SCRIM
            self._panel.styles = self._panel_restore.model_copy(update={"opacity": 0.0, "z_index": -1})
            self._root.args = {k: v for k, v in self._root.args.items() if k != "data-neony-outside"}
            try:
                self._close_task = asyncio.create_task(self._finish_close())
            except RuntimeError:
                # No running event loop — hide immediately, skip the fade.
                self._root.styles = _ROOT
                self._panel.styles = self._panel_restore
        self._dispatch_pseudo("open" if value else "close")

    async def _finish_close(self) -> None:
        # await asyncio.sleep(0.2)  # the reversed fade-slide plays out
        if not self._open:
            self._panel.styles = self._panel_restore
            self._root.styles = _ROOT

    def _cancel_close(self) -> None:
        if self._close_task is not None:
            self._close_task.cancel()
            self._close_task = None

    @property
    def title(self) -> str:
        return str(self._title_span.container[0]) if self._title_span.container else ""

    @title.setter
    def title(self, value: str) -> None:
        self._title_span.container = [value]

    def on_open(self, fn) -> Self:
        """Register a callback fired when the dialog opens (called with
        the dialog itself; sync or async)."""
        return self.on("open", fn)

    def on_close(self, fn) -> Self:
        """Register a callback fired when the dialog closes (called with
        the dialog itself; sync or async)."""
        return self.on("close", fn)

    # ---- internals ----

    def _build_action_bar(self) -> Div:
        bar = Div(styles=_ACTION_BAR, container=[])
        self._actions_buttons: list[Button] = []
        for action in self._actions:
            btn = Button(action.text, variant=action.variant)
            btn.on_click(self._make_action_handler(action))
            self._actions_buttons.append(btn)
            bar.container.append(btn.build())
        return bar

    def _make_action_handler(self, action: DialogAction):
        async def handler(event: DomEvent) -> None:
            if action.on_click is not None:
                result = action.on_click(self)
                if asyncio.iscoroutine(result):
                    await result
            if action.close_on_click:
                self.open = False

        return handler

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click":
            # Bound to the scrim only — a click inside the panel targets
            # a panel-descendant key.
            if event.key == self._scrim.key and self._closable:
                self.open = False
        elif event_type == "keydown":
            if event.value == "Escape":
                self.open = False
        elif event_type == "outsideclick":
            self.open = False
        await self._dispatch(event_type, event)

    def _dispatch_pseudo(self, event_type: str) -> None:
        """Fire an ``open`` / ``close`` notification with the dialog
        itself; async callbacks run as fire-and-forget tasks (the state
        change is synchronous)."""
        for fn in self._callbacks.get(event_type, []):
            result = fn(self)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                # Keep a reference so the task isn't GC'd mid-run.
                self._pseudo_tasks.add(task)
                task.add_done_callback(self._pseudo_tasks.discard)
