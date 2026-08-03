"""NeonApplication — a complete LumiView wrapper with reactive DOM.

Wraps App creation, Window setup, the Neony bridge, handler collection
from the DOM tree, auto-render, theme injection, and a user-facing
state namespace.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from lumiview import App, Bridge, Window

from neony.application.config import Config
from neony.application.page import Page
from neony.application.theme import Theme
from neony.dom import DOMElement, DomEvent
from neony.dom.bridge import Neony

_INITIAL_HTML = "<html><body><div id='neony-root'></div></body></html>"


class NeonApplication:
    """Reactive desktop application built on LumiView + Neony DOM.

    Example::

        from neony.application import Config, NeonApplication, WindowConfig
        from neony.application.elements import Button

        app = NeonApplication(Config(window=WindowConfig(title="Demo")))

        counter = Button("Click me")

        async def clicked(event: DomEvent):
            counter.label = "Clicked!"

        counter.on_click(clicked)

        app.run(Page().add(counter))
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._neony = Neony(name="neony", mount_selector=self.config.mount_selector)
        self._tree: DOMElement | None = None
        self._window: Window | None = None
        self.state: SimpleNamespace = SimpleNamespace()
        self.theme: Theme = Theme()

    # ---- lifecycle ----

    def run(self, page: Page | DOMElement) -> None:
        """Blocking entry point.

        Accepts a :class:`~neony.application.Page` (built internally) or
        a raw :class:`DOMElement` tree. Walks the tree, collects all
        fluent-event handlers, injects the theme, then starts LumiView.
        """
        self._tree = page.build() if isinstance(page, Page) else page
        self._collect_handlers(self._tree)
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
        await self.sync_theme()
        await self.render()

    # ---- theme ----

    async def sync_theme(self) -> None:
        """Inject the current theme's ``:root`` CSS variables into the page.

        Switching ``app.theme.mode`` and calling this re-injects the
        block — every ``var(--color-*)`` redraws with zero DOM diff.
        """
        if self._window is None:
            return
        css = self.theme.to_css()
        await self._window.eval_js(
            f"(() => {{ const el = document.getElementById('neony-theme'); "
            f"if (el) el.textContent = {css!r}; else {{ const s = document.createElement('style'); "
            f"s.id = 'neony-theme'; s.textContent = {css!r}; document.head.appendChild(s); }} }})()"
        )

    # ---- rendering ----

    async def render(self) -> None:
        """Render (or update) the DOM tree in the browser.

        The first call mounts the full tree; subsequent calls diff
        against the previous snapshot and send minimal patches.
        """
        if self._tree is None:
            raise RuntimeError("NeonApplication: run() must be called first")
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


def launch(page: Page | DOMElement, **config_kwargs: Any) -> None:
    """Convenience: build a Config from kwargs and run *page*.

    Example::

        launch(page, title="Demo", width=480, height=640, devtools=True)

    Recognised kwargs mirror :class:`WindowConfig` / :class:`WebViewConfig`
    fields plus ``mount_selector`` and ``auto_render``.
    """
    from neony.application.config import WebViewConfig, WindowConfig

    window_cfg = {k: v for k, v in config_kwargs.items() if k in WindowConfig.model_fields}
    webview_cfg = {k: v for k, v in config_kwargs.items() if k in WebViewConfig.model_fields}
    top_cfg = {k: v for k, v in config_kwargs.items() if k in ("mount_selector", "auto_render")}

    config = Config(
        window=WindowConfig(**window_cfg),
        webview=WebViewConfig(**webview_cfg),
        **top_cfg,
    )
    NeonApplication(config).run(page)
