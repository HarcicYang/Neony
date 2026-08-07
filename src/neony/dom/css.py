"""Typed CSS value models — colors, transitions, animation keyframes,
and the element ``Styles`` surface.

These are the building blocks every :class:`~neony.dom.base.DOMElement`
serializes into CSS text: ``Color`` / ``Transition`` / ``Animation``
appear as individual style values, ``Props`` + ``KeyFrame`` describe
``@keyframes`` rules, and ``Styles`` is the full style-surface model
attached to each element (with dirty-marking back to its owner).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import BaseModel, PrivateAttr, model_serializer
from pydantic.fields import Field

if TYPE_CHECKING:
    from neony.dom.base import DOMElement


class Color(BaseModel):
    """A CSS color value: keyword ``name``, ``hex`` string, ``rgb``/``rgba``
    channels, or a ``var(--color-*)`` custom-property reference."""

    name: str | None = Field(default=None)
    rgb: tuple[int, int, int] | None = Field(default=None)
    rgba: tuple[int, int, int, float] | None = Field(default=None)
    hex: str | None = Field(default=None)
    var: str | None = Field(default=None)

    @model_serializer
    def to_text(self) -> str:
        if self.var:
            return f"var({self.var})"
        elif self.name:
            return self.name
        elif self.rgb:
            r, g, b = self.rgb
            return f"rgb({r}, {g}, {b})"
        elif self.rgba:
            r, g, b, a = self.rgba
            return f"rgba({r}, {g}, {b}, {a})"
        elif self.hex:
            return self.hex
        else:
            raise NotImplementedError("At least one of name, rgb, rgba, hex, or var must be set")


class Transition(BaseModel):
    """A single CSS transition descriptor — the typed alternative to a
    raw ``transition`` CSS string.  Serialises to
    ``property duration timing delay``.

    The 99 % case is one uniform transition; for different durations per
    property a raw ``str`` can still be passed directly.  ``property``
    and ``timing`` also accept ``str`` for properties not listed and for
    ``cubic-bezier(...)`` / ``steps(...)`` timing functions.
    """

    property: (
        Literal[
            "all",
            "none",
            "opacity",
            "transform",
            "color",
            "background-color",
            "border-color",
            "box-shadow",
            "width",
            "height",
            "max-width",
            "max-height",
            "margin",
            "padding",
            "left",
            "right",
            "top",
            "bottom",
            "filter",
            "backdrop-filter",
            "outline-color",
        ]
        | str
    ) = "all"
    duration: str = "0.3s"
    timing: (
        Literal[
            "ease",
            "ease-in",
            "ease-out",
            "ease-in-out",
            "linear",
            "step-start",
            "step-end",
        ]
        | str
    ) = "ease"
    delay: str = "0s"

    @model_serializer
    def to_css(self) -> str:
        parts = [self.property, self.duration, self.timing]
        if self.delay and self.delay != "0s":
            parts.append(self.delay)
        return " ".join(parts)


class Props(BaseModel):
    """CSS properties at one keyframe stop — the animatable subset.

    Every field is optional; an all-None ``Props()`` renders an empty
    declaration block (usually a mistake, but not a type error).  Nested
    :class:`Color` values are flattened to CSS text by their own
    serializer during ``model_dump()``.
    """

    opacity: float | None = None
    transform: str | None = None
    color: Color | None = None
    background_color: Color | None = None
    border_color: Color | None = None
    box_shadow: str | None = None
    width: str | None = None
    height: str | None = None
    filter: str | None = None
    backdrop_filter: str | None = None

    def to_css(self) -> str:
        """Render the set properties as ``prop: value;`` declarations."""
        parts = []
        for k, v in self.model_dump().items():
            if v is not None:
                parts.append(f"{k.replace('_', '-')}: {v}")
        return "; ".join(parts)


class KeyFrameStop(BaseModel):
    """One stop in a ``@keyframes`` rule."""

    percent: str  # "0%", "50%", "100%", "from", "to"
    props: Props = Field(default_factory=Props)


class KeyFrame(BaseModel):
    """A named ``@keyframes`` definition — chainable builder.

    Usage::

        spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)"))
                               .set("100%", Props(transform="rotate(360deg)"))
        app.register_keyframe(spin)

    Registering a second KeyFrame with the same name replaces the first
    (later-wins).
    """

    name: str
    stops: list[KeyFrameStop] = Field(default_factory=list)

    def __init__(self, name: str, **data: Any) -> None:
        """Accept the keyframe *name* positionally (chainable-builder
        style); every other field is keyword-only."""
        super().__init__(name=name, **data)

    def set(self, percent: str, props: Props) -> Self:
        """Append a stop and return self for chaining."""
        self.stops.append(KeyFrameStop(percent=percent, props=props))
        return self

    def to_css(self) -> str:
        """Render the full ``@keyframes`` block."""
        body = "\n".join(f"  {stop.percent} {{ {stop.props.to_css()} }}" for stop in self.stops)
        return f"@keyframes {self.name} {{\n{body}\n}}"


class Animation(BaseModel):
    """CSS animation shorthand referencing a registered :class:`KeyFrame`
    by name.  Serialises to ``name duration timing [delay] [count]
    [direction] [fill-mode] [play-state]``, omitting default values."""

    name: str
    duration: str = "1s"
    timing: (
        Literal[
            "ease",
            "ease-in",
            "ease-out",
            "ease-in-out",
            "linear",
            "step-start",
            "step-end",
        ]
        | str
    ) = "ease"
    delay: str = "0s"
    iteration_count: str | int = 1
    direction: (
        Literal[
            "normal",
            "reverse",
            "alternate",
            "alternate-reverse",
        ]
        | str
    ) = "normal"
    fill_mode: Literal["none", "forwards", "backwards", "both"] | str = "none"
    play_state: Literal["running", "paused"] | str = "running"

    @model_serializer
    def to_css(self) -> str:
        parts = [self.name, self.duration, self.timing]
        if self.delay and self.delay != "0s":
            parts.append(self.delay)
        if self.iteration_count != 1:
            parts.append(str(self.iteration_count))
        if self.direction != "normal":
            parts.append(self.direction)
        if self.fill_mode != "none":
            parts.append(self.fill_mode)
        if self.play_state != "running":
            parts.append(self.play_state)
        return " ".join(parts)


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
    flex_grow: str | None = Field(default=None)
    flex_shrink: str | None = Field(default=None)
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

    # --- Borders ---
    border: str | None = Field(default=None)
    border_radius: str | None = Field(default=None)
    border_top: str | None = Field(default=None)
    border_right: str | None = Field(default=None)
    border_bottom: str | None = Field(default=None)
    border_left: str | None = Field(default=None)
    # Corner-specific radii (for joining rounded chrome pieces).
    border_top_left_radius: str | None = Field(default=None)
    border_top_right_radius: str | None = Field(default=None)
    border_bottom_left_radius: str | None = Field(default=None)
    border_bottom_right_radius: str | None = Field(default=None)

    # --- Visual ---
    opacity: float | None = Field(default=None)
    box_shadow: str | None = Field(default=None)
    # CSS transition — a typed descriptor or a raw shorthand string.
    transition: Transition | str | None = Field(default=None)
    # CSS animation — a typed descriptor referencing a registered
    # KeyFrame name, or a raw shorthand string.
    animation: Animation | str | None = Field(default=None)
    # Transform functions (e.g. "translateX(10px) scale(1.2)").
    transform: str | None = Field(default=None)
    # Focus-ring outline (commonly "none"; input.py relies on this).
    outline: str | None = Field(default=None)
    # Frosted glass; also emitted with the -webkit- prefix (WebKitGTK).
    backdrop_filter: str | None = Field(default=None)
    # Native control appearance reset (e.g. custom-styled checkboxes).
    appearance: str | None = Field(default=None)
    background_image: str | None = Field(default=None)
    background_size: str | None = Field(default=None)
    background_position: str | None = Field(default=None)
    background_repeat: str | None = Field(default=None)
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
