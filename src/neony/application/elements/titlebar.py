"""TitleBar component — custom window chrome for frameless windows.

Window-control actions are fully managed internally: each button
carries a ``data-window-action`` attribute that the JS runtime routes
to the LumiView ``WindowControls`` bridge scope.  Users get a pure
Python API: ``on_close(fn)`` extra callbacks, ``override_close(fn)``
full takeover.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Self

from neony.application.theme import stub
from neony.dom import Border, Color, Div, DOMElement, DomEvent, Filter, Span, Styles, calc
from neony.dom import Button as _ButtonElem

from .base import Component, ReactiveText, _mount_text
from .icon import Icon

# WindowControls bridge commands exposed by ``window.lumiview.window.*``.
_ACTIONS = {"minimize": "minimize", "maximize": "toggleMaximize", "close": "close"}
# Bundled subset reliably provides these neutral window glyphs.  The
# original ligatures either render below the optical centre or fall back
# to text on some WebKitGTK builds.
_ICONS = {
    "minimize": Icon._font("remove"),
    "maximize": Icon._font("crop_square"),
    "close": Icon._font("close"),
}


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
        title: ReactiveText = "",
        *,
        icon: Icon | None = None,
        icon_size: str = "18px",
        icon_styles: Styles | None = None,
        leading: Sequence[Component | DOMElement] | None = None,
        trailing: Sequence[Component | DOMElement] | None = None,
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
        # match the 8px side padding.  The title rides the span so a
        # reactive ``tr`` binding re-renders on language switch.
        self._title_span = Span(
            container=[],
            styles=Styles(
                font_size="13px",
                font_weight="500",
                line_height=calc(f"{self._height} - 16px"),
                color=stub.text_primary,
                white_space="nowrap",
                overflow="hidden",
            ),
        )
        _mount_text(self._title_span, self._title)

        # Optional inline icon for frameless windows: a fixed-size square
        # painted with the image, so it never stretches with the title.
        self._icon_el: Span | None = icon.render(icon_size) if icon is not None else None
        if self._icon_el is not None and icon_styles is not None:
            overrides = {key: getattr(icon_styles, key) for key in icon_styles.model_fields_set}
            self._icon_el.styles = self._icon_el.styles.model_copy(update=overrides)

        leading_children: list[DOMElement] = []
        for child in leading or ():
            mounted = child.build() if isinstance(child, Component) else child
            leading_children.append(mounted)
        trailing_children: list[DOMElement] = []
        for child in trailing or ():
            mounted = child.build() if isinstance(child, Component) else child
            trailing_children.append(mounted)

        # Root: full-width drag region with aggressive frosted glass.
        self._left_side = Div(
            styles=Styles(
                display="flex",
                align_items="center",
                gap="6px",
                flex_grow="1",
                overflow="hidden",
            ),
            container=[self._icon_el, *leading_children, self._title_span]
            if self._icon_el is not None
            else [*leading_children, self._title_span],
        )
        self._right_side = Div(
            styles=Styles(
                display="flex",
                align_items="center",
                gap="4px",
                flex_shrink="0",
            ),
            container=[*trailing_children, self._btn_min, self._btn_max, self._btn_close],
        )
        self._root = Div(
            styles=Styles(
                display="flex",
                flex_direction="row",
                align_items="center",
                height=self._height,
                padding="0 12px",
                background_color=stub.surface_glass_bg,
                backdrop_filter=Filter(blur="20px", saturate=1.2),
                border_bottom=Border(width="1px", color=stub.border_glass),
                flex_shrink="0",
            ),
            container=[self._left_side, self._right_side],
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
        args["data-neony-event-scope"] = ""
        icon = _ICONS[kind].render("14px")
        # The scoped click resolver above owns descendants, including this
        # hit-testable glyph.
        button = _ButtonElem(
            type="button",
            container=[icon],
            styles=styles,
            args=args,
        )
        button.bubble_events = True
        return button

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
        if isinstance(self._title, str):
            return self._title
        return self._title()

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        self._title_span.container = [value]

    @property
    def leading_slot(self) -> DOMElement:
        """The leading side container (icon + custom content + title)."""
        return self._left_side

    @property
    def trailing_slot(self) -> DOMElement:
        """The trailing container for custom content and window buttons."""
        return self._right_side

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
