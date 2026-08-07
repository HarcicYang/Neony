"""Unified icon type for the component library.

An :class:`Icon` is one small decorative glyph shown before a label —
either an **image** (a URL or file path, painted as a fixed-size square
the way :class:`TitleBar` paints its icon) or a **glyph** (an emoji /
Nerd Font text character).  Construct one with :meth:`Icon.image` or
:meth:`Icon.glyph`; never pass a raw string to a component's ``icon``
parameter — the two kinds are explicit so there is nothing to guess.

Used by :class:`TitleBar`, :class:`SidebarItem`, :class:`Pane`,
:class:`Tabs` and :class:`TreeNode`.
"""

from __future__ import annotations

from typing import Literal

from neony.dom import Span, Styles

_IconKind = Literal["image", "glyph"]


class Icon:
    """A single icon — an image URL/path or a text glyph.

    Examples::

        Icon.image("https://example.com/logo.svg")   # fixed-size square
        Icon.image("assets/logo.png")
        Icon.glyph("🏠")                              # emoji / Nerd Font char
    """

    __slots__ = ("kind", "src")

    def __init__(self, src: str, *, kind: _IconKind) -> None:
        self.src = src
        self.kind = kind

    @classmethod
    def image(cls, url_or_path: str) -> Icon:
        """An image icon — a URL or file path painted into a fixed-size
        square (``background-size: contain``, never stretched)."""
        return cls(url_or_path, kind="image")

    @classmethod
    def glyph(cls, text: str) -> Icon:
        """A text-glyph icon — an emoji or a single Nerd Font character."""
        return cls(text, kind="glyph")

    def render(self, size: str = "16px") -> Span:
        """Render this icon as a :class:`Span` at *size* (a CSS length)."""
        if self.kind == "image":
            # Mirrors TitleBar's inline icon (titlebar.py): a fixed-size
            # square painted with the image so it never stretches.
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
        # Glyph: centered text at the requested size.
        return Span(
            container=[self.src],
            styles=Styles(font_size=size, text_align="center"),
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Icon.{self.kind}({self.src!r})"
