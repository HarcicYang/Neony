"""Layout components — flexbox wrappers: ``Flex`` (full control),
``VStack``/``HStack`` (thin wrappers), ``Spacer``, ``Separator``."""

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
        for child in children:
            if isinstance(child, Component):
                self._track_component(child)
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
                # Without this, min-height:auto stretches the container
                # to its content and overflow:auto never engages.
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
    """Subtle divider line (border-weakening aesthetic)."""

    def __init__(
        self, *, width: str = "100%", thickness: str = "1px", type: Literal["horizontal", "vertical"] = "horizontal"
    ) -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                width=width if type == "horizontal" else thickness,
                height=thickness if type == "horizontal" else width,
                background_color=Color(var="--color-border"),
                margin="8px 0" if type == "horizontal" else "0 8px",
            ),
        )


class GlassPanel(Component):
    """Explicit frosted-glass container.

    Wraps children in a translucent surface with backdrop blur and a
    highlight border tinted with the semantic *role* (``"accent"``,
    ``"danger"``, ``"success"``, ``"neutral"``).  ``background=url``
    paints an image inside (the frosted effect stays local); with a
    background the panel is two layers — a plain backdrop carries the
    image, since WebKitGTK's ``backdrop-filter`` can swallow an
    element's own background.

    ``grow=True`` stretches the panel to the full height its flex
    parent allocates (a transparent sizing wrapper carries the
    ``flex-grow + flex-basis:0 + min-height:0`` chain).  The parent
    must have a *definite* height — a bare block container with auto
    height gives the panel nothing to grow into, and a scroll child
    (e.g. a Tree rail) inside it pushes the page open instead of
    scrolling internally.
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
        # Per-corner radii override parts of *radius* — for joining
        # rounded chrome pieces (e.g. the titlebar seam).
        border_top_left_radius: str | None = None,
        border_top_right_radius: str | None = None,
        border_bottom_left_radius: str | None = None,
        border_bottom_right_radius: str | None = None,
    ) -> None:
        super().__init__()
        from neony.application.theme import Theme

        # Default 12px; pass "0px" (or any radius) to override.
        radius = radius if radius is not None else "12px"
        # Semantic roles add a colour-matched outer glow; neutral keeps the plain shadow.
        shadow = "0 8px 32px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.04)"
        if role != "neutral":
            shadow = f"0 0 24px {Theme.glass_border(role)}, " + shadow
        glass_styles = Styles(
            position="relative",
            display="flex",
            flex_direction="column",
            gap=gap,
            padding=padding,
            border_radius=radius,
            border=f"1px solid {Theme.glass_border(role)}",
            # Denser glass (0.85) keeps text readable over the background.
            background_color=Color(var="--color-surface-panel-glass-bg"),
            backdrop_filter="blur(16px)",
            box_shadow=shadow,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        for child in children:
            if isinstance(child, Component):
                self._track_component(child)
        children_el = Flex._build_children(children)
        if grow:
            # Stretch to the full available height.  A transparent,
            # styleless wrapper carries the sizing chain (flex-grow +
            # flex-basis:0 + min-height:0) and the glass face fills it as
            # a flex item (same triple) — so a scroll child (e.g. a Tree
            # rail) shrinks and scrolls inside instead of growing the
            # panel past the window.  flex-basis:0 pins the height to the
            # parent's allocation (not the intrinsic content), so a pane
            # swap can't grow the panel.  No height:100% on the face:
            # a flex item with both flex-grow and height would total
            # more than the wrapper (100% basis + grown space) and
            # overlap its siblings.
            face = Div(
                styles=glass_styles.model_copy(
                    update={"flex_grow": "1", "flex_basis": "0", "min_height": "0"}
                ),
                container=children_el,
            )
            if background:
                # Image layer below, frosted glass above (backdrop-filter
                # would swallow the image's own background).  The glass
                # face drops from the dense 0.85 panel fill to the
                # lighter 0.60 surface fill so the image shows through.
                glass_face = Div(
                    styles=Styles(
                        position="relative",
                        display="flex",
                        flex_direction="column",
                        flex_grow="1",
                        flex_basis="0",
                        min_height="0",
                    ),
                    container=[
                        Div(
                            styles=Styles(
                                position="absolute",
                                top="0",
                                left="0",
                                right="0",
                                bottom="0",
                                border_radius=radius,
                                background_image=(
                                    "linear-gradient(var(--color-bg-overlay), var(--color-bg-overlay)), "
                                    f"url('{background}')"
                                ),
                                background_size="cover, cover",
                                background_position="center center, center center",
                                background_repeat="no-repeat, no-repeat",
                            )
                        ),
                        face,
                    ],
                )
            else:
                # The glass face itself fills the wrapper.
                glass_face = face
            self._root = Div(
                styles=Styles(
                    display="flex",
                    flex_direction="column",
                    flex_grow="1",
                    flex_basis="0",
                    min_height="0",
                    # Transparent, styleless sizing wrapper — no paint.
                ),
                container=[glass_face],
            )
        elif background:
            # Image layer below, frosted glass above (backdrop-filter
            # would swallow the image's own background).  The glass face
            # drops from the dense 0.85 panel fill to the lighter 0.60
            # surface fill so the image shows through (0.85 + the 0.7
            # overlay underneath leave only ~4% of the image visible).
            glass_styles = glass_styles.model_copy(update={"background_color": Color(var="--color-surface-glass-bg")})
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
            self._root = Div(
                styles=Styles(position="relative", display="flex", flex_direction="column"),
                container=[backdrop, Div(styles=glass_styles, container=children_el)],
            )
        else:
            self._root = Div(styles=glass_styles, container=children_el)
