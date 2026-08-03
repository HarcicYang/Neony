"""NeonApplication — a complete LumiView wrapper with reactive DOM.

Wraps App creation, Window setup, the Neony bridge, handler collection
from the DOM tree, auto-render, and a user-facing state namespace.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from lumiview import App, Bridge, Window

from neony.application.config import Config
from neony.dom import DOMElement, DomEvent
from neony.dom.bridge import Neony

_INITIAL_HTML = "<html><body><div id='neony-root'></div></body></html>"


class NeonApplication:
    """Reactive desktop application built on LumiView + Neony DOM.

    Example::

        from neony.application import Config, NeonApplication, WindowConfig
        from neony.dom import Div

        app = NeonApplication(Config(window=WindowConfig(title="Demo")))

        counter = Div(container=["0"])

        async def increment(event: DomEvent):
            counter.container = [str(int(counter.container[0]) + 1)]

        counter.on_click(increment)

        app.run(Div(container=[counter]))
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._neony = Neony(name="neony", mount_selector=self.config.mount_selector)
        self._tree: DOMElement | None = None
        self._window: Window | None = None
        self.state: SimpleNamespace = SimpleNamespace()

    # ---- lifecycle ----

    def run(self, tree: DOMElement) -> None:
        """Blocking entry point.

        Walks the tree, collects all fluent-event handlers, then starts
        the LumiView app and mounts the tree into the window.
        """
        self._tree = tree
        self._collect_handlers(tree)
        app = App(name=self.config.window.title.replace(" ", ""))
        app.run(self._main)

    async def _main(self) -> None:
        kwargs = self.config.to_window_kwargs()
        self._window = await Window.create(
            title=kwargs.pop("title", "Neony"),
            html=_INITIAL_HTML,
            bridge=Bridge(includes=[self._neony]),
            **kwargs,
        )
        # Give the WebView a moment to settle before mounting
        await asyncio.sleep(0.5)
        await self.render()

    # ---- rendering ----

    async def render(self) -> None:
        """Render (or update) the DOM tree in the browser.

        The first call mounts the full tree; subsequent calls diff
        against the previous snapshot and send minimal patches.
        """
        if self._tree is None:
            raise RuntimeError("NeonApplication: run(tree) must be called first")
        await self._neony.render(self._tree)

    # ---- handler collection ----

    def _collect_handlers(self, element: DOMElement) -> None:
        """Walk the tree and register element handlers with the bridge."""
        for event_type, fns in element._handlers.items():
            for fn in fns:
                self._neony.on(event_type, key=element.key)(self._make_wrapper(fn, element))
        for child in element.container:
            if isinstance(child, DOMElement):
                self._collect_handlers(child)

    def _make_wrapper(self, fn: Any, element: DOMElement) -> Any:
        """Wrap a user handler: build DomEvent, call fn, auto-render."""

        async def wrapper(key: str, event_type: str, value: Any = None) -> None:
            evt = DomEvent(key=key, type=event_type, value=value)
            await fn(evt)
            if self.config.auto_render:
                await self.render()

        return wrapper
