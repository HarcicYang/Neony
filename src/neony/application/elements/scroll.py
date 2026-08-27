"""Scrollable containers with a pure Python scrolling API.

The actual DOM scrolling happens through internal JS commands
(``window.neony.scrollTo*``); user code never sees JavaScript.
"""

from __future__ import annotations

import json
from typing import Literal, Self

from neony.dom import Div, DOMElement, Styles

from .base import Component

Behavior = Literal["auto", "smooth"]

# Mounting contract (CONTRIBUTING.md): scroll-bearing components must be
# mounted in a definite-height flex parent.  ``flex_grow + flex-basis:0 +
# min-height:0`` makes the container fill its parent without pushing the
# page open; an auto-height parent would break scrolling.
_SCROLL_AREA = Styles(
    flex_grow="1",
    flex_basis="0",
    min_height="0",
    overflow_y="auto",
    overflow_x="hidden",
)


class ScrollArea(Component):
    """A scrollable vertical region.

    Mount contract: place inside a definite-height flex parent (see the
    module docstring).  Children are components or DOM elements.
    """

    def __init__(self, *children: Component | DOMElement) -> None:
        super().__init__()
        self._root = Div(styles=_SCROLL_AREA, container=[self._mount(child) for child in children])

    @staticmethod
    def _mount(child: Component | DOMElement) -> DOMElement:
        return child.build() if isinstance(child, Component) else child

    def _key(self) -> str:
        return json.dumps(self._root.key)

    async def _call(self, script: str) -> None:
        coro = self._call_js(script)
        if coro is not None:
            await coro

    async def scroll_to_bottom(self, *, behavior: Behavior = "auto") -> Self:
        """Scroll the region to the bottom."""
        await self._call(f"window.neony.scrollToBottom({self._key()}, {json.dumps(behavior)})")
        return self

    async def scroll_to_top(self, *, behavior: Behavior = "auto") -> Self:
        """Scroll the region to the top."""
        await self._call(f"window.neony.scrollToTop({self._key()}, {json.dumps(behavior)})")
        return self

    async def scroll_to(self, top: float, *, behavior: Behavior = "auto") -> Self:
        """Scroll the region to a pixel offset."""
        await self._call(f"window.neony.scrollTo({self._key()}, {top}, {json.dumps(behavior)})")
        return self


class StickToBottom(Component):
    """A scrollable region that auto-sticks to the bottom as content
    arrives.

    The chat-stream model: new content keeps the view pinned while the
    user is near the bottom; scrolling up pauses the pin; scrolling back
    near the bottom resumes it.  The internal JS engine owns this
    behavior (``data-neony-autostick``) — Python only provides the
    container and ``scroll_to_bottom(force=True)``.

    Mount contract: definite-height flex parent, same as
    :class:`ScrollArea`.
    """

    def __init__(self, *children: Component | DOMElement) -> None:
        super().__init__()
        self._root = Div(
            styles=_SCROLL_AREA,
            args={"data-neony-autostick": "true"},
            container=[self._mount(child) for child in children],
        )

    @staticmethod
    def _mount(child: Component | DOMElement) -> DOMElement:
        return child.build() if isinstance(child, Component) else child

    def _key(self) -> str:
        return json.dumps(self._root.key)

    async def scroll_to_bottom(self, *, force: bool = True, behavior: Behavior = "auto") -> Self:
        """Scroll to the bottom.

        ``force=False`` leaves the auto-stick state untouched (the
        internal observer already pins when appropriate); ``force=True``
        scrolls regardless of the current pin state.
        """
        if force:
            coro = self._call_js(f"window.neony.scrollToBottom({self._key()}, {json.dumps(behavior)})")
            if coro is not None:
                await coro
        return self

    async def scroll_to(self, top: float, *, behavior: Behavior = "auto") -> Self:
        """Scroll the region to a pixel offset."""
        coro = self._call_js(f"window.neony.scrollTo({self._key()}, {top}, {json.dumps(behavior)})")
        if coro is not None:
            await coro
        return self
