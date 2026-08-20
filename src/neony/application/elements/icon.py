"""Unified icon value type for the component library.

An :class:`Icon` is either an image, an explicit custom text glyph, or a
private built-in font glyph supplied through :data:`neony.application.icons`.
Never pass a raw string to a component's ``icon`` parameter.
"""

from __future__ import annotations

from typing import Literal

from neony.dom import Span, Styles

_IconKind = Literal["image", "glyph", "font"]
_FONT_FAMILY = "Neony Material Symbols Rounded"
_FONT_VARIATIONS = "'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24"


class Icon:
    """A single image, custom glyph, or built-in font icon.

    Application code normally uses ``from neony.application import icons`` and
    ``icons.home``.  ``image()`` remains suitable for logos, and ``glyph()``
    remains suitable for deliberate custom text/emoji content.
    """

    __slots__ = ("kind", "src")

    def __init__(self, src: str, *, kind: _IconKind) -> None:
        self.src = src
        self.kind = kind

    @classmethod
    def image(cls, url_or_path: str) -> Icon:
        """Build an image icon painted into a fixed-size square."""
        return cls(url_or_path, kind="image")

    @classmethod
    def glyph(cls, text: str) -> Icon:
        """Build an explicit custom text glyph (emoji or installed font)."""
        return cls(text, kind="glyph")

    @classmethod
    def _font(cls, ligature: str) -> Icon:
        """Build a bundled font icon; private to the :mod:`icons` catalog."""
        return cls(ligature, kind="font")

    def render(self, size: str = "16px") -> Span:
        """Render this icon as a non-shrinking square-like inline span."""
        if self.kind == "image":
            return Span(
                styles=Styles(
                    width=size,
                    height=size,
                    flex_shrink="0",
                    background_image=f"url({self.src})",
                    background_size="contain",
                    background_position="center",
                    background_repeat="no-repeat",
                ),
            )
        styles = Styles(
            display="inline-flex",
            width=size,
            height=size,
            flex_shrink="0",
            align_items="center",
            justify_content="center",
            font_size=size,
            line_height="1",
            text_align="center",
            white_space="nowrap",
        )
        if self.kind == "font":
            styles = styles.model_copy(
                update={
                    "font_family": _FONT_FAMILY,
                    "font_variation_settings": _FONT_VARIATIONS,
                }
            )
        return Span(container=[self.src], styles=styles)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Icon.{self.kind}({self.src!r})"
