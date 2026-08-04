"""Component base class.

A Component *encapsulates* a :class:`DOMElement` tree (never inherits).
It owns its state, proxies the fluent event API, and produces a
:class:`DOMElement` via :meth:`build` that plugs into a Page or any
other component's tree.

Event semantics: user-driven DOM events reach the component's internal
elements with ``DomEvent.source == "user"`` and notify registered
callbacks. Programmatic state changes (e.g. ``checkbox.checked = True``)
update state and the DOM tree immediately but never fire callbacks.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Self

from neony.dom import DOMElement, DomEvent, Signal, Styles


class Component:
    """Base class for all Neony UI components.

    Subclasses build their internal DOMElement tree in ``__init__``
    (stored as ``self._root``), own their state, and expose chainable
    ``on_*`` methods. Bind internal elements to events with
    :meth:`_bind`; override :meth:`_on_event` to sync state before
    user callbacks run.
    """

    def __init__(self) -> None:
        self._root: DOMElement
        self._callbacks: dict[str, list[Callable[..., Any]]] = {}

    # ---- build ----

    def build(self) -> DOMElement:
        """Return the internal DOMElement tree for insertion into a Page."""
        return self._root

    # ---- styling ----

    def reset_styles(self, styles: Styles) -> Self:
        """Completely replace the component's root styles (chainable).

        Later calls overwrite earlier ones — no merging.
        """
        self._root.styles = styles
        return self

    # ---- signal bindings (proxy to the root element) ----

    def bind_text(self, signal: Signal[Any], fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to the component's text content (see DOMElement.bind_text)."""
        self._root.bind_text(signal, fmt)
        return self

    def bind_style(self, signal: Signal[Any], prop: str, fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to a root style property (see DOMElement.bind_style)."""
        self._root.bind_style(signal, prop, fmt)
        return self

    def bind_attr(self, signal: Signal[Any], name: str, fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to a root HTML attribute (see DOMElement.bind_attr)."""
        self._root.bind_attr(signal, name, fmt)
        return self

    def bind_visible(self, signal: Signal[Any]) -> Self:
        """Bind *signal* to the root's visibility (see DOMElement.bind_visible)."""
        self._root.bind_visible(signal)
        return self

    def unbind(self) -> Self:
        """Dispose every signal binding on the root element."""
        self._root.unbind()
        return self

    # ---- event API ----

    def on(self, event_type: str, fn: Callable[..., Any]) -> Self:
        """Register a callback for *event_type* on this component (chainable).

        The callback receives a :class:`DomEvent` with ``source == "user"``.
        Programmatic state changes do not fire callbacks.
        """
        self._callbacks.setdefault(event_type, []).append(fn)
        return self

    def on_click(self, fn: Callable[..., Any]) -> Self:
        return self.on("click", fn)

    def on_dblclick(self, fn: Callable[..., Any]) -> Self:
        return self.on("dblclick", fn)

    def on_input(self, fn: Callable[..., Any]) -> Self:
        return self.on("input", fn)

    def on_change(self, fn: Callable[..., Any]) -> Self:
        return self.on("change", fn)

    def on_focus(self, fn: Callable[..., Any]) -> Self:
        return self.on("focus", fn)

    def on_blur(self, fn: Callable[..., Any]) -> Self:
        return self.on("blur", fn)

    def on_keydown(self, fn: Callable[..., Any]) -> Self:
        return self.on("keydown", fn)

    def on_keyup(self, fn: Callable[..., Any]) -> Self:
        return self.on("keyup", fn)

    # ---- internals ----

    def _bind(self, element: DOMElement, event_type: str) -> None:
        """Attach the source-aware dispatcher to an internal element."""
        element.on(event_type, self._make_handler(event_type))

    def _make_handler(self, event_type: str) -> Callable[..., Any]:
        """Create the raw DOMElement handler for *event_type*."""

        async def handler(event: DomEvent) -> None:
            event.source = "user"
            try:
                await self._on_event(event_type, event)
            finally:
                event.source = "program"

        return handler

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        """Subclass hook: sync state from *event*, then notify callbacks."""
        await self._dispatch(event_type, event)

    async def _dispatch(self, event_type: str, event: DomEvent) -> None:
        """Notify user callbacks registered for *event_type*.

        Supports both sync and async callbacks; awaitables are awaited.
        """
        for fn in self._callbacks.get(event_type, []):
            result = fn(event)
            if asyncio.iscoroutine(result):
                await result
