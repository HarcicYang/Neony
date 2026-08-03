"""Heading component — token-coloured, size-mapped."""

from __future__ import annotations

from typing import Literal

from neony.dom import H1 as _H1
from neony.dom import H2 as _H2
from neony.dom import H3 as _H3
from neony.dom import H4 as _H4
from neony.dom import H5 as _H5
from neony.dom import H6 as _H6
from neony.dom import Color, DOMElement, Styles

from .base import Component

_LEVELS: dict[int, type[DOMElement]] = {1: _H1, 2: _H2, 3: _H3, 4: _H4, 5: _H5, 6: _H6}
_SIZES = {1: "32px", 2: "26px", 3: "20px", 4: "17px", 5: "15px", 6: "13px"}


class Heading(Component):
    """A themed heading with automatic size per level."""

    def __init__(self, text: str = "", *, level: Literal[1, 2, 3, 4, 5, 6] = 1) -> None:
        super().__init__()
        self._text = text
        cls = _LEVELS[level]
        self._root = cls(
            container=[text],
            styles=Styles(
                font_size=_SIZES[level],
                font_weight="700",
                color=Color(var="--color-text-primary"),
                margin="0",
            ),
        )

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._root.container = [value]
