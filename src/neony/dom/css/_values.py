"""Leaf CSS value models — typed descriptors for individual style values.

``Color`` is the original typed value; later phases add ``Length`` /
``Shadow`` / ``BoxShadow`` / ``Transform`` / ``Border`` / ``Filter``. Each
serialises to CSS text via ``@model_serializer`` (consumed by the render
loop's ``model_dump()``) and via ``__str__`` / ``__repr__`` delegating to
``model_dump()`` so f-string / ``str()`` interpolation also yields CSS text.
"""

from __future__ import annotations

from typing import cast

from pydantic import BaseModel, model_serializer
from pydantic.fields import Field


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

    def __str__(self) -> str:
        # ``model_dump()`` returns the serializer's CSS text at runtime,
        # but pydantic's static stub types it as ``dict[str, Any]``.
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())


def _coerce_len(v: int | float | str) -> str:
    """Bare number → px; zero stays bare ``0`` (matches the pre-refactor
    box-shadow literals like ``"0 8px 32px ..."`` byte-for-byte); strings
    (already a CSS length / compound) pass through verbatim.

    Minimal today (Length model arrives in a later phase); keeps Shadow/BoxShadow
    usable now without depending on Length.
    """
    if isinstance(v, (int, float)):
        return "0" if v == 0 else f"{v}px"
    return v


class Shadow(BaseModel):
    """One CSS ``box-shadow`` layer.

    Layers compose via :class:`BoxShadow`. Coordinates accept a bare number
    (auto-``px``) or any CSS length string; ``color`` is a typed
    :class:`Color` (commonly a ``var(--color-*)`` token reference).
    """

    x: int | float | str = 0
    y: int | float | str = 0
    blur: int | float | str | None = None
    spread: int | float | str | None = None
    color: Color | None = None
    inset: bool = False

    @model_serializer
    def to_css(self) -> str:
        parts: list[str] = []
        if self.inset:
            parts.append("inset")
        parts += [_coerce_len(self.x), _coerce_len(self.y)]
        if self.blur is not None:
            parts.append(_coerce_len(self.blur))
        if self.spread is not None:
            parts.append(_coerce_len(self.spread))
        if self.color is not None:
            parts.append(cast(str, self.color.model_dump()))
        return " ".join(parts)

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())


class BoxShadow(BaseModel):
    """One or more ``box-shadow`` layers; serialises comma-joined.

    A single :class:`Shadow` is the common case — ``BoxShadow(layers=[s])``
    wraps it; ``Styles.box_shadow`` accepts either, plus a raw ``str``
    escape hatch for ad-hoc values.
    """

    layers: list[Shadow]

    @model_serializer
    def to_css(self) -> str:
        return ", ".join(cast(str, layer.model_dump()) for layer in self.layers)

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())
