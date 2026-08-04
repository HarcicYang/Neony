"""Page — the top-level container for a Neony application."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Self

from neony.dom import Color, Div, DOMElement, Styles

from .elements import Component

_Direction = Literal["row", "row-reverse", "column", "column-reverse"]
_Align = Literal["stretch", "center", "flex-start", "flex-end", "baseline"]
_Justify = Literal["flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"]


class Page:
    """Top-level page container (flex column by default).

    Usage::

        page = Page(gap="16px", padding="24px")
        page.add(Button("OK"))
        app.run(page)  # build() called internally
    """

    def __init__(
        self,
        *,
        direction: _Direction = "column",
        gap: str = "16px",
        padding: str = "24px",
        align: _Align = "stretch",
        justify: _Justify = "flex-start",
        width: str = "100%",
        max_width: str = "600px",
        glass: bool = False,
        fill: bool = False,
        radius: str | None = None,
    ) -> None:
        self._children: list[Component | DOMElement] = []
        self._close_handlers: list[Callable] = []
        self._focus_handlers: list[Callable] = []
        self._blur_handlers: list[Callable] = []
        self._navigation_handler: Callable[[str], bool] | None = None
        self._new_window_handler: Callable[[str], str] | None = None
        self._download_started_handler: Callable[[str, str], bool | str] | None = None
        self._download_completed_handlers: list[Callable] = []
        self._direction = direction
        self._gap = gap
        self._padding = padding
        self._align = align
        self._justify = justify
        self._width = width
        self._max_width = max_width
        self._glass = glass
        self._fill = fill
        self._radius = radius

    # ---- public API ----

    def add(self, child: Component | DOMElement) -> Page:
        """Append a component or raw DOMElement to the page."""
        self._children.append(child)
        return self

    def on_close(self, fn: Callable) -> Self:
        """Register *fn* — sync or async — called when this page's window is
        closing.  Multiple handlers stack and all run; exceptions are logged
        but never prevent the window from closing.  Chainable.

        The framework wires this to the native ``CloseRequested`` event
        internally — the window index and lifecycle stay out of user code.
        """
        self._close_handlers.append(fn)
        return self

    def on_focus(self, fn: Callable) -> Self:
        """Register *fn* — sync or async — called when this page's window
        gains keyboard focus.  Multiple handlers stack; exceptions are
        logged.  Chainable.

        Wired to the native ``Focused`` window event internally.
        """
        self._focus_handlers.append(fn)
        return self

    def on_blur(self, fn: Callable) -> Self:
        """Register *fn* — sync or async — called when this page's window
        loses keyboard focus.  Multiple handlers stack; exceptions are
        logged.  Chainable.

        Wired to the native ``Unfocused`` window event internally.
        """
        self._blur_handlers.append(fn)
        return self

    # ---- navigation & download policies ----

    def on_navigation(self, fn: Callable[[str], bool]) -> Self:
        """Set the navigation policy: *fn(url)* returns ``True`` to allow
        the page to navigate or ``False`` to block it.  Calling again
        replaces the previous handler — the last one wins (a policy is a
        single decision, not a listener list).  Chainable.

        Default (no handler): every navigation is blocked, so the app UI
        can never be navigated away by an in-page link or redirect.
        """
        self._navigation_handler = fn
        return self

    def on_new_window(self, fn: Callable[[str], str]) -> Self:
        """Set the new-window policy: *fn(url)* returns ``"allow"`` or
        ``"deny"`` for ``target="_blank"`` links and ``window.open()``.
        Calling again replaces the previous handler.  Chainable.

        Default (no handler): every new-window request is denied.
        """
        self._new_window_handler = fn
        return self

    def on_download_started(self, fn: Callable[[str, str], bool | str]) -> Self:
        """Set the download policy: *fn(url, suggested_path)* returns
        ``True`` to allow, ``False`` to cancel, or a path string to
        redirect the download.  Calling again replaces the previous
        handler.  Chainable.

        Default (no handler): every download is cancelled.
        """
        self._download_started_handler = fn
        return self

    def on_download_completed(self, fn: Callable) -> Self:
        """Register *fn(url, path, success)* — called when a download
        finishes.  Multiple handlers stack; exceptions are logged.
        Chainable.  Only fires for downloads the download policy allowed.
        """
        self._download_completed_handlers.append(fn)
        return self

    # ---- build ----

    def build(self) -> DOMElement:
        """Render the page root DOMElement: an outer full-screen backdrop
        (transparent, so the body theme/background shows through) and an
        inner width-constrained, centered content column."""
        outer = Styles(
            min_height="100vh",
            width="100%",
            color=Color(var="--color-text-primary"),
            font_family="system-ui, -apple-system, sans-serif",
        )

        inner = Styles(
            display="flex",
            flex_direction=self._direction,
            align_items=self._align,
            justify_content=self._justify,
            gap=self._gap,
            padding=self._padding,
            width=self._width,
            max_width=self._max_width,
            margin="0 auto",
        )

        if self._fill:
            # fill=True: stretch to the full window height (via the
            # html/body/#neony-root height:100% chain) so chrome layouts
            # cover the whole window.
            outer = outer.model_copy(update={"display": "flex", "height": "100%", "min_height": None})
            inner = inner.model_copy(update={"flex_grow": "1"})

        if self._radius is not None:
            # Window-level rounded corners: the outer layer clips the
            # chrome stack.
            outer = outer.model_copy(update={"border_radius": self._radius, "overflow": "hidden"})

        container: list[DOMElement | str] = []
        for child in self._children:
            container.append(child.build() if isinstance(child, Component) else child)

        return Div(styles=outer, container=[Div(styles=inner, container=container)])
