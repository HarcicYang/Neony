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
                # Allow the container to shrink below its content height
                # inside a parent flex column — otherwise min-height:auto
                # stretches it to the content and overflow:auto scrolls
                # never engage (content spills out instead).
                min_height="0",
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
        grow: int = 0,
    ) -> None:
        super().__init__(
            *children,
            direction="column",
            gap=gap,
            align=align,
            justify=justify,
            padding=padding,
            width=width,
            grow=grow,
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
        grow: int = 0,
    ) -> None:
        super().__init__(
            *children,
            direction="row",
            gap=gap,
            align=align,
            justify=justify,
            padding=padding,
            width=width,
            grow=grow,
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


class GlassPanel(Component):
    """Explicit frosted-glass container.

    Wraps children in a translucent surface with backdrop blur and a
    highlight border tinted with the given semantic *role* (``"accent"``,
    ``"danger"``, ``"success"``, or ``"neutral"``).

    Pass ``background=url`` to paint an image inside the panel itself
    (under a theme-coloured overlay) — the frosted effect stays local
    to the panel instead of covering the whole page.

    With a background the panel is two layers: a plain backdrop Div
    carries the image (WebKitGTK's ``backdrop-filter`` can swallow an
    element's own background, so the image must live on a layer without
    it), and a frosted layer sits above and blurs it.
    """

    def __init__(
        self,
        *children: Component | DOMElement | str,
        gap: str = "16px",
        padding: str = "24px",
        role: str = "neutral",
        background: str | None = None,
        grow: bool = False,
        radius: str | None = None,
    ) -> None:
        super().__init__()
        from neony.application.theme import Theme

        # Default 12px; pass "0px" (or any radius) to override.
        radius = radius if radius is not None else "12px"
        glass_styles = Styles(
            position="relative",
            display="flex",
            flex_direction="column",
            gap=gap,
            padding=padding,
            border_radius=radius,
            border=f"1px solid {Theme.glass_border(role)}",
            # Content panels use the denser glass token (0.85) — text
            # needs a stable, dark backdrop to stay readable over the
            # background image, unlike the chrome bars which stay
            # aggressively transparent.
            background_color=Color(var="--color-surface-panel-glass-bg"),
            backdrop_filter="blur(16px)",
            box_shadow=("0 8px 32px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.04)"),
        )
        if grow:
            # Fill the parent content region: the panel (and its frosted
            # surface / backdrop) stretches to the full available height.
            glass_styles = glass_styles.model_copy(update={"flex_grow": "1", "height": "100%"})

        children_el = Flex._build_children(children)
        if background:
            # Bottom layer: image + theme overlay, no backdrop-filter —
            # guaranteed to render. Top layer: the frosted glass that
            # blurs it.
            backdrop = Div(
                styles=Styles(
                    position="absolute",
                    top="0",
                    left="0",
                    right="0",
                    bottom="0",
                    border_radius=radius,
                    background_image=(
                        f"linear-gradient(var(--color-bg-overlay), var(--color-bg-overlay)), url('{background}')"
                    ),
                    background_size="cover, cover",
                    background_position="center center, center center",
                    background_repeat="no-repeat, no-repeat",
                )
            )
            root_styles = Styles(position="relative", display="flex", flex_direction="column")
            if grow:
                root_styles = root_styles.model_copy(update={"height": "100%"})
            self._root = Div(
                styles=root_styles,
                container=[backdrop, Div(styles=glass_styles, container=children_el)],
            )
        else:
            self._root = Div(styles=glass_styles, container=children_el)
