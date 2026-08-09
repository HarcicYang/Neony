"""Avatar component — a circular or square user thumbnail.

With ``src`` the avatar shows the image (cropped by ``object-fit``); with
only ``name`` it falls back to a one-letter initial on an accent disc; with
neither it shows an empty placeholder.  An optional ``badge`` (a corner
:class:`Badge`) is overlaid — the avatar wraps itself in a relative
inline-flex container so the badge can anchor to a corner.
"""

from __future__ import annotations

from typing import Literal

from neony.application.theme import stub
from neony.dom import Border, Color, Div, Img, Span, Styles
from neony.dom.base import DOMElement

from .badge import Badge
from .base import Component

_Shape = Literal["circle", "square"]


def _initial(name: str | None) -> str:
    """The single-character avatar mark — first non-space char, uppercased;
    ``"?"`` when there's nothing to show."""
    text = (name or "").strip()
    if not text:
        return "?"
    return text[0].upper()


class Avatar(Component):
    """A user avatar — image, initial, or placeholder.

    - ``src`` — an image URL (pass it ``file_url()`` / ``data_url()`` /
      ``https://``); falls back to the ``name`` initial when ``None``.
    - ``name`` — used for the fallback initial and (when ``alt`` is unset)
      the image alt text.
    - ``size`` — width and height (``"40px"`` default).
    - ``shape`` — ``"circle"`` (default) / ``"square"``.
    - ``radius`` — override the shape's corner radius.
    - ``alt`` — override the image alt text.
    - ``border`` — a 1px theme border around the avatar (default True).
    - ``badge`` — a corner :class:`Badge` overlaid on the avatar.
    """

    def __init__(
        self,
        src: str | None = None,
        *,
        name: str | None = None,
        size: str = "40px",
        shape: _Shape = "circle",
        radius: str | None = None,
        alt: str | None = None,
        border: bool = True,
        badge: Badge | None = None,
    ) -> None:
        super().__init__()
        self._src = src
        self._name = name
        self._size = size
        self._shape = shape
        self._radius = radius if radius is not None else ("50%" if shape == "circle" else "8px")
        self._alt = alt
        self._border = border
        self._badge = badge
        self._has_badge = badge is not None

        # The inner avatar disc — built once, re-rendered on src/name change.
        self._inner = Div()
        self._apply_inner()
        if self._has_badge:
            self._root = Div(
                styles=Styles(
                    position="relative",
                    display="inline-flex",
                    flex_shrink="0",
                ),
                container=[self._inner, badge.build() if isinstance(badge, Badge) else badge],
            )
        else:
            # The inner disc is itself the root when there's no badge.
            self._root = self._inner

    # ---- state ----

    @property
    def src(self) -> str | None:
        return self._src

    @src.setter
    def src(self, value: str | None) -> None:
        self._src = value
        self._apply_inner()

    @property
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        self._name = value
        self._apply_inner()

    @property
    def size(self) -> str:
        return self._size

    @size.setter
    def size(self, value: str) -> None:
        self._size = value
        self._apply_inner()

    # ---- internals ----

    def _base_styles(self) -> Styles:
        return Styles(
            position="relative",
            display="inline-flex",
            flex_shrink="0",
            overflow="hidden",
            width=self._size,
            height=self._size,
            border_radius=self._radius,
            border=Border(width="1px", color=stub.border) if self._border else None,
        )

    def _apply_inner(self) -> None:
        """Re-derive the inner disc's styles + children from state."""
        if self._src:
            styles = self._base_styles()
            self._inner.styles = styles
            self._inner.container = [
                Img(
                    src=self._src,
                    alt=self._alt if self._alt is not None else (self._name or ""),
                    styles=Styles(width="100%", height="100%", object_fit="cover", display="block"),
                )
            ]
        else:
            # Initial disc — centred letter on an accent background.
            styles = self._base_styles().model_copy(
                update={
                    "align_items": "center",
                    "justify_content": "center",
                    "background_color": stub.accent,
                }
            )
            self._inner.styles = styles
            self._inner.container = [
                Span(
                    container=[_initial(self._name)],
                    styles=Styles(
                        color=Color(name="white"),
                        font_size="16px",
                        font_weight="600",
                        line_height="1",
                    ),
                )
            ]

    @property
    def _avatar(self) -> DOMElement:
        """The inner avatar disc (also the root when there's no badge)."""
        return self._inner
