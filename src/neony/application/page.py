"""Page — top-level container for a Neony application.

A Page replaces bare Div usage at the root: it owns the page-level
flex layout, applies the theme background, and collects components.
``app.run(page)`` calls :meth:`build` internally.
"""

from __future__ import annotations

from typing import Literal

from neony.dom import Color, Div, DOMElement, Styles

from .elements import Component

_Direction = Literal["row", "row-reverse", "column", "column-reverse"]
_Align = Literal["stretch", "center", "flex-start", "flex-end", "baseline"]
_Justify = Literal["flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"]


class Page:
    """Top-level page container (flex column by default).

    Usage::

        page = Page(gap="16px", padding="24px")
        page.add(Heading("Hello"))
        page.add(Button("OK"))

        app.run(page)   # build() called internally
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
    ) -> None:
        self._children: list[Component | DOMElement] = []
        self._direction = direction
        self._gap = gap
        self._padding = padding
        self._align = align
        self._justify = justify
        self._width = width
        self._max_width = max_width
        self._glass = glass

    # ---- public API ----

    def add(self, child: Component | DOMElement) -> Page:
        """Append a component or raw DOMElement to the page."""
        self._children.append(child)
        return self

    # ---- build ----

    def build(self) -> DOMElement:
        """Render the page root DOMElement.

        Two layers:
        - outer Div: full-screen background + base typography
        - inner Div: the width-constrained, centered content column
        """
        outer = Styles(
            min_height="100vh",
            width="100%",
            background_color=Color(var="--color-bg"),
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

        container: list[DOMElement | str] = []
        for child in self._children:
            container.append(child.build() if isinstance(child, Component) else child)

        return Div(styles=outer, container=[Div(styles=inner, container=container)])
