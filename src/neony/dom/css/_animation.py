"""Animation-related CSS models — transitions, animation shorthand,
and ``@keyframes`` rule builders.

``Transition`` / ``Animation`` serialise to their CSS shorthand via
``@model_serializer``; ``Props`` + ``KeyFrame`` / ``KeyFrameStop`` describe
``@keyframes`` rules rendered by ``KeyFrame.to_css()``.
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, model_serializer
from pydantic.fields import Field

from ._values import Color


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
