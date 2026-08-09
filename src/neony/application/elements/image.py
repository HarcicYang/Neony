"""Image component — a themed frame around a single ``<img>``.

The component accepts an already-built URL string (``file_url(path)``,
``data_url(path)``, an ``https://`` URL, …) and never converts paths
itself — keeping that boundary in the caller's hands.  A rounded,
overflow-hidden frame wraps the image so ``object-fit`` can crop to the
radius and a placeholder tint shows before the bytes arrive.
"""

from __future__ import annotations

from typing import Literal

from neony.application.theme import stub
from neony.dom import Color, Div, Img, Styles
from neony.dom.base import DOMElement

from .base import Component

_Fit = Literal["cover", "contain", "fill", "none", "scale-down"]


def _dim(value: str | int | None) -> str | None:
    """Coerce a dimension argument to a CSS string — ints become ``"Npx"``,
    strings (``"40%"``, ``"auto"``, ``"120px"``) pass through, ``None``
    stays ``None``."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"{value}px"
    return value


class Image(Component):
    """A themed image in a rounded, overflow-hidden frame.

    - ``src`` — an already-built URL string (pass it ``file_url(path)``,
      ``data_url(path)`` or an ``https://`` URL); the component does no
      path conversion.
    - ``alt`` — alternative text (also the fallback when the image fails).
    - ``width`` / ``height`` — ``str`` (``"40%"``) or ``int`` (→ ``"40px"``).
    - ``fit`` — ``object-fit``: ``"cover"`` (default), ``"contain"``,
      ``"fill"``, ``"none"``, ``"scale-down"``.
    - ``radius`` — corner radius (pass ``"50%"`` for a circle); ``"0px"``
      to square it off.
    - ``loading`` — ``"lazy"`` (default) / ``"eager"``.
    - ``placeholder`` — a frame background shown until the image paints.
    """

    def __init__(
        self,
        src: str,
        *,
        alt: str = "",
        width: str | int | None = None,
        height: str | int | None = None,
        fit: _Fit = "cover",
        radius: str = "8px",
        loading: Literal["lazy", "eager"] = "lazy",
        placeholder: str | None = None,
    ) -> None:
        super().__init__()
        self._src = src
        self._alt = alt

        self._img = Img(
            src=src,
            alt=alt,
            loading=loading,
            styles=Styles(
                width="100%",
                height="100%",
                object_fit=fit,
                display="block",
            ),
        )
        # The frame gives us the rounded crop (overflow:hidden) and a
        # placeholder tint layer below the image.
        placeholder_color: Color | None
        if placeholder is None:
            placeholder_color = stub.surface_raised
        elif placeholder.startswith("var("):
            # Already a CSS var() expression → take the token name.
            token = placeholder[4:].rstrip(")").strip()
            placeholder_color = Color(var=token)
        elif placeholder.startswith("#"):
            placeholder_color = Color(hex=placeholder)
        else:
            # A named CSS colour ("transparent", "red", …) or a token name.
            placeholder_color = Color(name=placeholder)
        frame_styles = Styles(
            border_radius=radius,
            width=_dim(width),
            height=_dim(height),
            overflow="hidden",
            background_color=placeholder_color,
        )
        self._root = Div(styles=frame_styles, container=[self._img])

    # ---- state ----

    @property
    def src(self) -> str:
        return self._src

    @src.setter
    def src(self, value: str) -> None:
        self._src = value
        self._img.src = value

    @property
    def alt(self) -> str:
        return self._alt

    @alt.setter
    def alt(self, value: str) -> None:
        self._alt = value
        self._img.alt = value

    # ---- internals ----

    @property
    def _frame(self) -> DOMElement:
        return self._root
