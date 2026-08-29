"""Heading component — token-coloured, size-mapped."""

from __future__ import annotations

from typing import Literal

from neony.application.theme import stub
from neony.dom import H1 as _H1
from neony.dom import H2 as _H2
from neony.dom import H3 as _H3
from neony.dom import H4 as _H4
from neony.dom import H5 as _H5
from neony.dom import H6 as _H6
from neony.dom import DOMElement, Span, Styles

from .base import Component, ReactiveText, _mount_text

_LEVELS: dict[int, type[DOMElement]] = {1: _H1, 2: _H2, 3: _H3, 4: _H4, 5: _H5, 6: _H6}
_SIZES = {1: "32px", 2: "26px", 3: "20px", 4: "17px", 5: "15px", 6: "13px"}


class Heading(Component):
    """A themed heading with automatic size per level."""

    def __init__(self, text: ReactiveText = "", *, level: Literal[1, 2, 3, 4, 5, 6] = 1) -> None:
        super().__init__()
        self._text = text
        cls = _LEVELS[level]
        # The text rides a child span so a reactive ``tr`` binding can
        # re-render on language switch (a raw string child can't subscribe).
        self._text_span = Span(container=[])
        _mount_text(self._text_span, text)
        self._root = cls(
            container=[self._text_span],
            styles=Styles(
                font_size=_SIZES[level],
                font_weight="700",
                color=stub.text_primary,
                margin="0",
            ),
        )

    @property
    def text(self) -> str:
        if isinstance(self._text, str):
            return self._text
        return self._text()

    @text.setter
    def text(self, value: str) -> None:
        # A plain string takes over from any reactive binding — dispose it
        # or a stale effect would overwrite future writes on signal change.
        self._text_span._unbind_text()
        self._text = value
        self._text_span.container = [value]
