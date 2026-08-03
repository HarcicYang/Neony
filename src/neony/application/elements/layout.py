"""Layout components — flexbox wrappers with sensible defaults.

The default layout is flex column (like a natural document flow).
``VStack`` / ``HStack`` are thin wrappers; ``Flex`` gives full control.
``Spacer`` absorbs leftover space; ``Separator`` draws a subtle divider.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from neony.dom import Color, Div, DOMElement, Styles

from .base import Component

_Direction = Literal["row", "row-reverse", "column", "column-reverse"]
_Align = Literal["stretch", "center", "flex-start", "flex-end", "baseline"]
_Justify = Literal["flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"]
_Wrap = Literal["nowrap", "wrap", "wrap-reverse"]


class Flex(Component):
    """Generic flex container with explicit direction.

    ``children`` may be Components, DOMElements, or plain strings.
    """

    def __init__(
        self,
        *children: Component | DOMElement | str,
        direction: _Direction = "row",
        gap: str = "0px",
        wrap: _Wrap = "nowrap",
        align: _Align = "stretch",
        justify: _Justify = "flex-start",
        padding: str = "0px",
        width: str | None = None,
        grow: int = 0,
    ) -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                display="flex",
                flex_direction=direction,
                gap=gap,
                flex_wrap=wrap,
                align_items=align,
                justify_content=justify,
                padding=padding,
                width=width,
                flex_grow=str(grow),
            ),
            container=self._build_children(children),
        )

    @staticmethod
    def _build_children(children: Iterable[Component | DOMElement | str]) -> list[DOMElement | str]:
        return [c.build() if isinstance(c, Component) else c for c in children]


class VStack(Flex):
    """Vertical (column) flex stack — the default page flow."""

    def __init__(
        self,
        *children: Component | DOMElement | str,
        gap: str = "0px",
        align: _Align = "stretch",
        justify: _Justify = "flex-start",
        padding: str = "0px",
        width: str | None = None,
    ) -> None:
        super().__init__(
            *children,
            direction="column",
            gap=gap,
            align=align,
            justify=justify,
            padding=padding,
            width=width,
        )


class HStack(Flex):
    """Horizontal (row) flex stack."""

    def __init__(
        self,
        *children: Component | DOMElement | str,
        gap: str = "0px",
        align: _Align = "center",
        justify: _Justify = "flex-start",
        padding: str = "0px",
        width: str | None = None,
    ) -> None:
        super().__init__(
            *children,
            direction="row",
            gap=gap,
            align=align,
            justify=justify,
            padding=padding,
            width=width,
        )


class Spacer(Component):
    """Flexible empty space that absorbs leftover layout room."""

    def __init__(self, *, flex: int | None = 1, width: str | None = None, height: str | None = None) -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                flex_grow=str(flex) if flex is not None else None,
                width=width,
                height=height,
            ),
        )


class Separator(Component):
    """Subtle horizontal divider line (border-weakening aesthetic)."""

    def __init__(self, *, width: str = "100%", thickness: str = "1px") -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                width=width,
                height=thickness,
                background_color=Color(var="--color-border"),
                margin="8px 0",
            ),
        )
