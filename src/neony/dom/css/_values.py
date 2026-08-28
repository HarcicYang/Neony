"""Leaf CSS value models — typed descriptors for individual style values.

``Color`` is the original typed value; later phases add ``Length`` /
``Shadow`` / ``BoxShadow`` / ``Transform`` / ``Border`` / ``Filter``. Each
serialises to CSS text via ``@model_serializer`` (consumed by the render
loop's ``model_dump()``) and via ``__str__`` / ``__repr__`` delegating to
``model_dump()`` so f-string / ``str()`` interpolation also yields CSS text.
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, model_serializer, model_validator
from pydantic.fields import Field


def px(v: int | float | str) -> str:
    """Bare number → ``"Npx"`` (0 stays bare ``0``); strings pass through."""
    if isinstance(v, (int, float)):
        return "0" if v == 0 else f"{v}px"
    return v


def pct(v: int | float | str) -> str:
    """Number or bare string → ``"N%"`` (idempotent: a ``%``-suffixed
    string passes through)."""
    s = f"{v}" if not isinstance(v, str) else v
    return s if s.endswith("%") else f"{s}%"


def calc(expr: str) -> str:
    """Wrap an expression as ``calc(...)``."""
    return f"calc({expr})"


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
    (already a CSS length / compound) pass through verbatim."""
    return px(v)


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
        parts += [px(self.x), px(self.y)]
        if self.blur is not None:
            parts.append(px(self.blur))
        if self.spread is not None:
            parts.append(px(self.spread))
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


_BorderStyle = Literal["none", "solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"]


class Border(BaseModel):
    """CSS border shorthand — ``width style color``.

    ``style="none"`` renders just ``none`` (the width/color are ignored).
    ``width`` is a CSS length string (use :func:`px` for bare numbers);
    ``color`` is a typed :class:`Color` (commonly a ``var(--color-*)``
    token reference).
    """

    width: str | None = None
    style: _BorderStyle = "solid"
    color: Color | None = None

    @model_serializer
    def to_css(self) -> str:
        if self.style == "none":
            return "none"
        parts = []
        if self.width is not None:
            parts.append(self.width)
        parts.append(self.style)
        if self.color is not None:
            parts.append(cast(str, self.color.model_dump()))
        return " ".join(parts)

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())


class Filter(BaseModel):
    """CSS filter chain — ``blur(...)`` / ``saturate(...)`` compose
    space-joined; anything else goes through the raw ``str`` escape hatch
    on ``Styles.backdrop_filter`` / ``Styles.filter``."""

    blur: str | None = None
    saturate: float | str | None = None

    @model_serializer
    def to_css(self) -> str:
        parts = []
        if self.blur is not None:
            parts.append(f"blur({self.blur})")
        if self.saturate is not None:
            parts.append(f"saturate({self.saturate})")
        return " ".join(parts)

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())


class Transform(BaseModel):
    """CSS transform — ordered transform-function list, chainable.

    ``Transform.translate(x=50, y="-50%")`` builds the common translate
    helpers (bare numbers become ``px``); anything more exotic goes
    through :meth:`func` or a raw ``str`` on ``Styles.transform``.
    """

    funcs: list[str]

    @classmethod
    def translate(cls, x: int | float | str | None = None, y: int | float | str | None = None) -> Transform:
        """``translateX(...)`` / ``translateY(...)`` / ``translate(x, y)``."""
        if x is not None and y is not None:
            return cls(funcs=[f"translate({px(x)}, {px(y)})"])
        if y is not None:
            return cls(funcs=[f"translateY({px(y)})"])
        if x is not None:
            return cls(funcs=[f"translateX({px(x)})"])
        return cls(funcs=[])

    @classmethod
    def rotate(cls, deg: int | float | str) -> Transform:
        """``rotate(Ndeg)`` — a bare number becomes degrees."""
        return cls(funcs=[f"rotate({deg}deg)" if isinstance(deg, (int, float)) else f"rotate({deg})"])

    @classmethod
    def scale(cls, s: int | float | str) -> Transform:
        """``scale(N)``."""
        return cls(funcs=[f"scale({s})"])

    @classmethod
    def func(cls, *funcs: str) -> Transform:
        """Raw-function escape hatch — ``Transform.func("skewX(10deg)")``."""
        return cls(funcs=list(funcs))

    @model_serializer
    def to_css(self) -> str:
        return " ".join(self.funcs)

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())


class Columns(BaseModel):
    """Typed ``grid-template-columns`` — column tracks for a CSS grid.

    Exactly one of ``repeat`` (``repeat(N, 1fr)``), ``min_width``
    (``repeat(auto-fill|auto-fit, minmax(..., 1fr))``) or ``tracks`` (an
    explicit track listing) may be set; ``fit`` only applies together
    with ``min_width``.  Bare numbers for ``min_width`` become ``px``.
    Convenience constructors: :meth:`fixed` and :meth:`responsive` —
    explicit track listings go through the ``tracks`` field directly.

    There is deliberately no raw-CSS escape hatch: grid layout goes
    through this model so column definitions stay inspectable and
    comparable.

    Note: the ``repeat`` field name is load-bearing — pydantic serialises
    union members duck-typed, and a field named ``count`` would silently
    resolve to ``str.count`` when a plain string rides a
    ``Columns | str`` style field.
    """

    repeat: int | None = None
    min_width: int | float | str | None = None
    fit: bool = False
    tracks: tuple[str, ...] | None = None

    @classmethod
    def fixed(cls, n: int) -> Columns:
        """``repeat(n, 1fr)`` — exactly *n* evenly split columns."""
        return cls(repeat=n)

    @classmethod
    def responsive(cls, min_width: int | float | str, *, fit: bool = False) -> Columns:
        """``repeat(auto-fill|auto-fit, minmax(min_width, 1fr))`` — as many
        columns as fit the container, each at least *min_width* wide.

        ``fit=True`` selects ``auto-fit``: empty tracks collapse so few
        items stretch across the full row (``auto-fill`` keeps them
        reserved)."""
        return cls(min_width=min_width, fit=fit)

    @model_validator(mode="after")
    def _check_exclusive(self) -> Columns:
        set_fields = [name for name in ("repeat", "min_width", "tracks") if getattr(self, name) is not None]
        if len(set_fields) != 1:
            raise ValueError("Columns takes exactly one of repeat=, min_width=, or tracks=")
        if self.fit and self.min_width is None:
            raise ValueError("Columns(fit=True) requires min_width=")
        return self

    @model_serializer
    def to_css(self) -> str:
        if self.repeat is not None:
            return f"repeat({self.repeat}, 1fr)"
        if self.min_width is not None:
            mode = "auto-fit" if self.fit else "auto-fill"
            return f"repeat({mode}, minmax({px(self.min_width)}, 1fr))"
        return " ".join(self.tracks or ())

    def __str__(self) -> str:
        return cast(str, self.model_dump())

    def __repr__(self) -> str:
        return cast(str, self.model_dump())
