"""TitleBar component — custom window chrome for frameless windows.

Window-control actions are fully managed internally: each button
carries a ``data-window-action`` attribute that the JS runtime routes
to the LumiView ``WindowControls`` bridge scope.  Users get a pure
Python API: ``on_close(fn)`` extra callbacks, ``override_close(fn)``
full takeover.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self

from neony.application.theme import stub
from neony.dom import Button as _ButtonElem
from neony.dom import Color, Div, DomEvent, Span, Styles

from .base import Component
from .icon import Icon

# WindowControls bridge commands exposed by ``window.lumiview.window.*``.
_ACTIONS = {"minimize": "minimize", "maximize": "toggleMaximize", "close": "close"}
_ICONS = {"minimize": "—", "maximize": "□", "close": "✕"}


class TitleBar(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click", "mouseover", "mouseout"})

    """Draggable glass titlebar with minimize / maximize / close controls.

    The root carries ``data-lumiview-drag-region``; control buttons are
    excluded from dragging and dispatch through the bridge.
    """

    def __init__(
        self,
        title: str = "",
        *,
        icon: Icon | None = None,
        show_minimize: bool = True,
        show_maximize: bool = True,
        show_close: bool = True,
        height: str = "40px",
    ) -> None:
        super().__init__()
        self._title = title
        self._icon = icon
        self._height = height
        self._show_minimize = show_minimize
        self._show_maximize = show_maximize
        self._show_close = show_close

        self._close_hover = False
        self._min_hover = False
        self._max_hover = False

        self._btn_min = self._make_control_button("minimize", show_minimize)
        self._btn_max = self._make_control_button("maximize", show_maximize)
        self._btn_close = self._make_control_button("close", show_close)

        # line-height = height - 16px so the glyph's vertical margins
        # match the 8px side padding.
        self._title_span = Span(
            container=[self._title],
            styles=Styles(
                font_size="13px",
                font_weight="500",
                line_height=f"calc({self._height} - 16px)",
                color=stub.text_primary,
                white_space="nowrap",
                overflow="hidden",
            ),
        )

        # Optional inline icon for frameless windows: a fixed-size square
        # painted with the image, so it never stretches with the title.
        self._icon_el: Span | None = icon.render("18px") if icon is not None else None

        # Root: full-width drag region with aggressive frosted glass.
        self._root = Div(
            styles=Styles(
                display="flex",
                flex_direction="row",
                align_items="center",
                height=self._height,
                padding="0 12px",
                background_color=stub.surface_glass_bg,
                backdrop_filter="blur(20px) saturate(1.2)",
                border_bottom="1px solid var(--color-border-glass)",
                flex_shrink="0",
            ),
            container=[
                Div(
                    styles=Styles(
                        display="flex",
                        align_items="center",
                        gap="6px",
                        flex_grow="1",
                        overflow="hidden",
                    ),
                    container=[self._icon_el, self._title_span] if self._icon_el else [self._title_span],
                ),
                Div(
                    styles=Styles(
                        display="flex",
                        align_items="center",
                        gap="4px",
                        flex_shrink="0",
                    ),
                    container=[self._btn_min, self._btn_max, self._btn_close],
                ),
            ],
            args={"data-lumiview-drag-region": ""},
        )

        for btn in (self._btn_min, self._btn_max, self._btn_close):
            self._bind(btn, "click")
            self._bind(btn, "mouseover")
            self._bind(btn, "mouseout")

    # ---- internals ----

    def _make_control_button(self, kind: str, visible: bool) -> _ButtonElem:
        """Build one window-control button.

        ``data-window-action`` is what the JS routes to the bridge; the
        ``data-lumiview-no-drag`` keeps the drag script off it.
        """
        styles = Styles(
            width="28px",
            height="28px",
            border="none",
            border_radius="6px",
            background_color=Color(name="transparent"),
            color=stub.text_secondary,
            font_size="14px",
            display="flex",
            align_items="center",
            justify_content="center",
            cursor="pointer",
            padding="0",
        )
        if not visible:
            styles = styles.model_copy(update={"display": "none"})
        args: dict[str, str] = {"data-lumiview-no-drag": ""}
        if visible:
            args["data-window-action"] = _ACTIONS[kind]
        return _ButtonElem(
            type="button",
            container=[_ICONS[kind]],
            styles=styles,
            args=args,
        )

    def _apply_hover(self) -> None:
        """Recompute control-button hover styles.

        Close turns danger-red on hover; both branches set the full
        state, so mouseout explicitly restores the base colours.
        """
        if self._close_hover:
            self._btn_close.styles = self._btn_close.styles.model_copy(
                update={
                    "background_color": stub.danger,
                    "color": Color(name="white"),
                }
            )
        else:
            self._btn_close.styles = self._btn_close.styles.model_copy(
                update={
                    "background_color": Color(name="transparent"),
                    "color": stub.text_secondary,
                }
            )

        for btn, hover in (
            (self._btn_min, self._min_hover),
            (self._btn_max, self._max_hover),
        ):
            base = stub.surface if hover else Color(name="transparent")
            btn.styles = btn.styles.model_copy(update={"background_color": base})

    # ---- state ----

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        self._title_span.container = [value]

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            if event.key == self._btn_close.key:
                self._close_hover = True
            elif event.key == self._btn_min.key:
                self._min_hover = True
            elif event.key == self._btn_max.key:
                self._max_hover = True
            self._apply_hover()
        elif event_type == "mouseout":
            if event.key == self._btn_close.key:
                self._close_hover = False
            elif event.key == self._btn_min.key:
                self._min_hover = False
            elif event.key == self._btn_max.key:
                self._max_hover = False
            self._apply_hover()
        elif event_type == "click":
            if event.key == self._btn_close.key:
                await self._dispatch("close", event)
            elif event.key == self._btn_min.key:
                await self._dispatch("minimize", event)
            elif event.key == self._btn_max.key:
                await self._dispatch("maximize", event)
        await self._dispatch(event_type, event)

    # ---- user API ----

    def on_minimize(self, fn: Callable[..., Any]) -> Self:
        """Extra callback — runs *after* the window minimizes."""
        return self.on("minimize", fn)

    def on_maximize(self, fn: Callable[..., Any]) -> Self:
        """Extra callback — runs *after* the window toggles maximize."""
        return self.on("maximize", fn)

    def on_close(self, fn: Callable[..., Any]) -> Self:
        """Extra callback — runs *after* the window close is requested."""
        return self.on("close", fn)

    def override_minimize(self, fn: Callable[..., Any]) -> Self:
        """Take over the minimize button: disable the built-in window
        action; *fn* is the only handler.  Call ``app.minimize()`` inside
        *fn* if you still want the window to minimize."""
        return self._override("minimize", self._btn_min, fn)

    def override_maximize(self, fn: Callable[..., Any]) -> Self:
        """Take over the maximize button (see :meth:`override_minimize`)."""
        return self._override("maximize", self._btn_max, fn)

    def override_close(self, fn: Callable[..., Any]) -> Self:
        """Take over the close button (see :meth:`override_minimize`).

        Useful for confirm-before-close flows: the window action is
        stripped from the button, so the window only closes if *fn*
        calls ``app.close()``.
        """
        return self._override("close", self._btn_close, fn)

    def _override(self, kind: str, btn: _ButtonElem, fn: Callable[..., Any]) -> Self:
        btn.args.pop("data-window-action", None)
        return self.on(kind, fn)
