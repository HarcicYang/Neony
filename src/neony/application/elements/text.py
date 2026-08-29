"""Text component — body copy with theme-aware colours."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, Iterable
from typing import Self

from neony.application.theme import stub
from neony.dom import Color, Computed, Signal, Span, Styles

from .base import Component, ReactiveText, _mount_text


class Text(Component):
    """Inline text with a semantic colour role.

    ``role`` selects a token-based colour:

    - ``"primary"`` — default text
    - ``"secondary"`` — muted / less important
    - ``"danger"`` — error or destructive emphasis
    - ``"success"`` — confirmation emphasis
    """

    def __init__(
        self,
        text: ReactiveText = "",
        *,
        role: str = "primary",
        size: str | None = None,
        weight: str | None = None,
    ) -> None:
        super().__init__()
        self._text = text
        self._root = Span(
            container=[],
            styles=Styles(
                color=self._role_color(role),
                font_size=size,
                font_weight=weight,
            ),
        )
        # Reactive text (a Signal/Computed, e.g. ``tr.common.copy``) binds
        # so language switches update live; plain strings are set directly.
        _mount_text(self._root, text)

    @staticmethod
    def _role_color(role: str) -> Color:
        if role == "secondary":
            return stub.text_secondary
        if role == "danger":
            return stub.danger
        if role == "success":
            return stub.success
        return stub.text_primary

    @property
    def text(self) -> str:
        if isinstance(self._text, str):
            return self._text
        return self._text()

    @text.setter
    def text(self, value: str) -> None:
        # A plain string takes over from any reactive binding — dispose it
        # or a stale effect would overwrite future writes on signal change.
        self._root._unbind_text()
        self._text = value
        self._root.container = [value]

    def append_text(self, text: str) -> Self:
        """Append *text* to the current content (chainable).

        Streams efficiently: the diff ships only the appended chunk when
        the browser already shows the previous text.  If this Text was
        created with a Signal/Computed, the reactive binding is disposed
        and the component switches to imperative ownership.
        """
        current = self.text
        if isinstance(self._text, (Signal, Computed)):
            self._root._unbind_text()
        self._text = current + text
        self._root._append_text(text)
        return self

    def stream(self, chunks: AsyncIterable[str] | Iterable[str]) -> asyncio.Task[None]:
        """Consume *chunks* (sync iterable or async iterator) into this
        Text at frame cadence (~60fps); returns the running task — cancel
        it (or call :meth:`stop_stream`) to stop mid-stream.  Requires a
        running event loop (the app provides one).  While the stream
        runs, a blinking caret trails the text and each chunk fades in.
        """
        return self._start_stream(self.append_text, chunks, target=self._root)
