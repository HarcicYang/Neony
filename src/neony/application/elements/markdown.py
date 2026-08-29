"""Markdown component — frontend-rendered markdown content.

The Python side owns the raw markdown *source*; parsing, HTML rendering
and syntax highlighting happen in the webview (``markdown-it`` +
``highlight.js``, concatenated into the injected runtime).  The root is
a managed subtree (``DOMElement._managed_content``), so the bridge never
diffs the rendered content — Python pushes the source text through
internal JS commands, which keeps streaming appends cheap regardless of
how large the rendered structure grows.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterable, Iterable
from typing import Self

from neony.dom import Computed, Div, DOMElement, Signal, Styles
from neony.dom.reactive import Effect

from .base import Component, ReactiveText


class Markdown(Component):
    """Rendered markdown text (headings, lists, code blocks, tables...).

    ``text`` accepts a plain string or a reactive Signal/Computed whose
    string value is the markdown source.  The live HTML is produced in
    the webview — updates re-render only in the browser, so streaming
    appends (:meth:`append_text` / :meth:`stream`) stay O(chunk) on the
    bridge.  Raw HTML inside the source is escaped; links open in the
    system browser.
    """

    def __init__(self, text: ReactiveText = "", *, width: str | None = None) -> None:
        super().__init__()
        self._text = text
        self._source_effect: Effect | None = None
        self._root = Div(styles=Styles(display="block", width=width), args={"data-neony-markdown": "true"})
        # The rendered DOM is JS-owned: freeze the Python snapshot.  The
        # provider makes the first snapshot (mount / resync re-mount)
        # carry the current source, so rebuilds restore the full content.
        self._root._managed_content = True
        self._root._managed_source = self._current_source
        # The container holds the initial source for the mount patch.
        self._root.container = [self._current_source()]
        if isinstance(text, (Signal, Computed)):
            self._source_effect = self._root._bind(lambda: self._push())

    # ---- source ----

    def _current_source(self) -> str:
        """The current markdown source (reactive values read untracked)."""
        value = self._text
        if isinstance(value, (Signal, Computed)):
            return str(value())
        return value

    def _json_key(self) -> str:
        return json.dumps(self._root.key)

    def _push(self) -> None:
        """Send the full current source to the JS renderer (no-op before
        the window is ready)."""
        self._schedule_js(f"window.neony.markdown.set({self._json_key()}, {json.dumps(self._current_source())})")

    # ---- state ----

    @property
    def text(self) -> str:
        """The current markdown source."""
        return self._current_source()

    @text.setter
    def text(self, value: ReactiveText) -> None:
        if self._source_effect is not None:
            self._source_effect.dispose()
            self._source_effect = None
        self._text = value
        self._root.container = [self._current_source()]
        if isinstance(value, (Signal, Computed)):
            self._source_effect = self._root._bind(lambda: self._push())
        else:
            self._push()

    def append_text(self, text: str) -> Self:
        """Append *text* to the markdown source (chainable).

        The source grows locally; a JS command re-renders the element.
        If this Markdown was created with a Signal/Computed, the reactive
        subscription is disposed and the component switches to
        imperative ownership.
        """
        current = self.text
        if self._source_effect is not None:
            self._source_effect.dispose()
            self._source_effect = None
        self._text = current + text
        self._push()
        return self

    def stream(self, chunks: AsyncIterable[str] | Iterable[str]) -> asyncio.Task[None]:
        """Consume *chunks* (sync iterable or async iterator) into this
        Markdown at frame cadence (~60fps); returns the running task —
        cancel it (or call :meth:`stop_stream`) to stop mid-stream.
        Requires a running event loop (the app provides one).  While the
        stream runs, a blinking caret trails the rendered content.
        """
        return self._start_stream(self.append_text, chunks, target=self._root)

    # ---- dom ----

    @property
    def root_element(self) -> DOMElement:
        """The managed root (exposed for tests and advanced composition)."""
        return self._root
