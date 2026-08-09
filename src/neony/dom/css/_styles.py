"""The ``Styles`` surface — the full per-element style model.

Attached to each :class:`~neony.dom.base.DOMElement`, it carries every CSS
property as a typed field (only non-None values render). In-place field
writes mark the owner element dirty so the change actually renders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, PrivateAttr
from pydantic.fields import Field

from ._animation import Animation, Transition
from ._values import Border, BoxShadow, Color, Filter, Shadow, Transform

if TYPE_CHECKING:
    from neony.dom.base import DOMElement


class Styles(BaseModel):
    """CSS style properties for a DOM element.

    Only non-None values are rendered into the style attribute.
    """

    # The owning element, hooked on assignment — in-place field
    # mutations (`el.styles.foo = X`) must mark it dirty, or the change
    # never renders (the snapshot cache would be reused as-is).
    _owner: DOMElement | None = PrivateAttr(default=None)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name.startswith("_"):
            return
        try:
            owner = object.__getattribute__(self, "_owner")
        except AttributeError:
            return  # still under construction — the element hooks us later
        if owner is not None:
            owner._dirty_type |= owner._DIRTY_STYLES
            owner._mark_dirty()

    # --- Colors ---
    color: Color | None = Field(default=None)
    background_color: Color | None = Field(default=None)
    # Native control tint (range sliders, progress bars, checkboxes) —
    # the only pseudo-element-free way to theme WebKitGTK controls.
    accent_color: Color | None = Field(default=None)

    # --- Dimensions ---
    width: str | None = Field(default=None)
    height: str | None = Field(default=None)
    min_width: str | None = Field(default=None)
    min_height: str | None = Field(default=None)
    max_width: str | None = Field(default=None)
    max_height: str | None = Field(default=None)
    # How a replaced element's content (e.g. an <img>) fits its box.
    object_fit: Literal["cover", "contain", "fill", "none", "scale-down"] | None = Field(default=None)

    # --- Display & Layout ---
    display: Literal["block", "inline", "inline-block", "flex", "grid", "inline-flex", "none"] | None = Field(
        default=None
    )
    position: Literal["static", "relative", "absolute", "fixed", "sticky"] | None = Field(default=None)
    top: str | None = Field(default=None)
    left: str | None = Field(default=None)
    right: str | None = Field(default=None)
    bottom: str | None = Field(default=None)

    # --- Flexbox ---
    justify_content: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "space-between",
            "space-around",
            "space-evenly",
        ]
        | None
    ) = Field(default=None)
    align_items: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "stretch",
            "baseline",
        ]
        | None
    ) = Field(default=None)
    align_self: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "stretch",
            "baseline",
            "auto",
        ]
        | None
    ) = Field(default=None)
    flex_direction: (
        Literal[
            "row",
            "row-reverse",
            "column",
            "column-reverse",
        ]
        | None
    ) = Field(default=None)
    flex_wrap: Literal["nowrap", "wrap", "wrap-reverse"] | None = Field(default=None)
    # Unitless flex factors — bare numbers render as-is (str() of an int).
    flex_grow: int | float | str | None = Field(default=None)
    flex_shrink: int | float | str | None = Field(default=None)
    flex_basis: str | None = Field(default=None)
    gap: str | None = Field(default=None)

    # --- Spacing ---
    padding: str | None = Field(default=None)
    padding_top: str | None = Field(default=None)
    padding_right: str | None = Field(default=None)
    padding_bottom: str | None = Field(default=None)
    padding_left: str | None = Field(default=None)
    margin: str | None = Field(default=None)
    margin_top: str | None = Field(default=None)
    margin_right: str | None = Field(default=None)
    margin_bottom: str | None = Field(default=None)
    margin_left: str | None = Field(default=None)

    # --- Typography ---
    font_size: str | None = Field(default=None)
    font_weight: (
        Literal[
            "100",
            "200",
            "300",
            "400",
            "500",
            "600",
            "700",
            "800",
            "900",
            "normal",
            "bold",
            "bolder",
            "lighter",
        ]
        | str
        | None
    ) = Field(default=None)
    font_family: str | None = Field(default=None)
    line_height: str | None = Field(default=None)
    text_align: (
        Literal[
            "left",
            "center",
            "right",
            "justify",
        ]
        | None
    ) = Field(default=None)
    text_decoration: (
        Literal[
            "none",
            "underline",
            "overline",
            "line-through",
        ]
        | None
    ) = Field(default=None)
    white_space: (
        Literal[
            "normal",
            "nowrap",
            "pre",
            "pre-wrap",
            "pre-line",
        ]
        | None
    ) = Field(default=None)
    word_break: (
        Literal[
            "normal",
            "break-all",
            "keep-all",
            "break-word",
        ]
        | None
    ) = Field(default=None)
    text_transform: (
        Literal[
            "none",
            "uppercase",
            "lowercase",
            "capitalize",
            "full-width",
        ]
        | None
    ) = Field(default=None)
    letter_spacing: str | None = Field(default=None)

    # --- Borders ---
    border: Border | str | None = Field(default=None)
    border_radius: str | None = Field(default=None)
    border_top: Border | str | None = Field(default=None)
    border_right: Border | str | None = Field(default=None)
    border_bottom: Border | str | None = Field(default=None)
    border_left: Border | str | None = Field(default=None)
    # Corner-specific radii (for joining rounded chrome pieces).
    border_top_left_radius: str | None = Field(default=None)
    border_top_right_radius: str | None = Field(default=None)
    border_bottom_left_radius: str | None = Field(default=None)
    border_bottom_right_radius: str | None = Field(default=None)

    # --- Visual ---
    opacity: float | None = Field(default=None)
    box_shadow: BoxShadow | Shadow | str | None = Field(default=None)
    # CSS transition — a typed descriptor or a raw shorthand string.
    transition: Transition | str | None = Field(default=None)
    # CSS animation — a typed descriptor referencing a registered
    # KeyFrame name, or a raw shorthand string.
    animation: Animation | str | None = Field(default=None)
    # CSS filter (regular) — symmetric with backdrop_filter.
    filter: Filter | str | None = Field(default=None)
    # Transform functions (e.g. "translateX(10px) scale(1.2)").
    transform: Transform | str | None = Field(default=None)
    # Focus-ring outline (commonly "none"; input.py relies on this).
    outline: Border | str | None = Field(default=None)
    # Frosted glass; also emitted with the -webkit- prefix (WebKitGTK).
    backdrop_filter: Filter | str | None = Field(default=None)
    # Native control appearance reset (e.g. custom-styled checkboxes).
    appearance: str | None = Field(default=None)
    background_image: str | None = Field(default=None)
    background_size: str | None = Field(default=None)
    background_position: str | None = Field(default=None)
    background_repeat: str | None = Field(default=None)
    # Edge fade for scroll surfaces — also emitted with the -webkit-
    # prefix (WebKitGTK).  A linear-gradient mask fades overflow content
    # at the edges; scrolling brings it back into view.
    mask_image: str | None = Field(default=None)
    mask_size: str | None = Field(default=None)
    overflow: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    overflow_x: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    overflow_y: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    cursor: (
        Literal[
            "auto",
            "default",
            "pointer",
            "wait",
            "text",
            "move",
            "not-allowed",
            "grab",
            "grabbing",
        ]
        | None
    ) = Field(default=None)
    user_select: (
        Literal[
            "none",
            "auto",
            "text",
            "contain",
            "all",
        ]
        | None
    ) = Field(default=None)
    z_index: int | None = Field(default=None)
