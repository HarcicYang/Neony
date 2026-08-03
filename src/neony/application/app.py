"""NeonApplication — a complete LumiView wrapper with reactive DOM.

Wraps App creation, Window setup, the Neony bridge, handler collection
from the DOM tree, auto-render, theme injection, and a user-facing
state namespace.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

from lumiview import App, Bridge, Window, WindowEffect

from neony.application.config import Config
from neony.application.page import Page
from neony.application.theme import Theme
from neony.dom import DOMElement, DomEvent
from neony.dom.bridge import Neony

# margin:0 — the browser default 8px body margin would leave a white
# ring around the page since our themed root sits inside the body.
#
# height:100% chain — the window's viewport (and thus ``vh`` units)
# can lag behind the actual window size when a tiling WM stretches the
# window after creation (e.g. hyprland).  Percentage heights follow the
# element's real height instead, so ``Page(fill=True)`` chrome layouts
# always match the window edge precisely.
#
# box-sizing:border-box — elements styled width:100% + padding (e.g. the
# Tabs panels) would otherwise measure *content* width and overflow the
# window's right edge by the padding amount.
_INITIAL_HTML = (
    "<html><head><style>*,*::before,*::after{box-sizing:border-box}"
    "html,body{height:100%;margin:0;padding:0}"
    "#neony-root{height:100%}</style></head>"
    "<body><div id='neony-root'></div></body></html>"
)


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
        self.ready_handler: Any = None  # optional async callable, run after window ready

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
        # Frameless windows get the WindowControls scope: it injects the
        # ``lumiview.window.*`` JS API plus drag/resize region handlers
        # (all Bridge commands, no raw JS in user code).
        includes: list = [self._neony]
        if not self.config.window.decorations:
            from lumiview.plugins.window_controls import WindowControls

            includes.append(WindowControls())
        self._window = await Window.create(
            title=kwargs.pop("title", "Neony"),
            html=_INITIAL_HTML,
            bridge=Bridge(includes=includes),
            **kwargs,
        )
        # Give the WebView a moment to settle before mounting
        await asyncio.sleep(0.5)
        await self.sync_theme()
        await self.render()
        if self.ready_handler is not None:
            await self.ready_handler()

    # ---- theme ----

    async def sync_theme(self) -> None:
        """Inject the current theme's ``:root`` CSS variables into the page.

        Switching ``app.theme.mode`` and calling this re-injects the
        block — every ``var(--color-*)`` redraws with zero DOM diff.

        The ``<body>`` background is set to the theme colour so the page
        stays themed even with a transparent Page root.  The background
        image's tint layer (from :meth:`set_background`) references
        ``var(--color-bg)`` too, so it re-tints on the same injection.
        """
        if self._window is None:
            return
        css = self.theme.to_css()
        # NOTE: the trailing ``})()`` closes the IIFE — a stray extra
        # brace here makes the whole script a SyntaxError and kills
        # theme injection entirely.
        # Transparent windows keep the body transparent so the native
        # background (or blur effect) shows through — painting the theme
        # colour here would make the window opaque.
        body_bg = (
            "document.body.style.backgroundColor = 'var(--color-bg)';" if not self.config.window.transparent else ""
        )
        js = (
            f"(() => {{ const el = document.getElementById('neony-theme'); "
            f"if (el) el.textContent = {css!r}; else {{ const s = document.createElement('style'); "
            f"s.id = 'neony-theme'; s.textContent = {css!r}; document.head.appendChild(s); }} "
            f"{body_bg} }})()"
        )
        # The background tint layer references var(--color-bg) directly —
        # the injection above re-tints it; no extra JS needed here.
        await self._window.eval_js(js)

    # ---- background image ----

    _background_url: str | None = None

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert ``#rrggbb`` to ``rgba(r, g, b, a)``."""
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"

    def _background_js(self) -> str:
        """JS that paints the background image under a theme-coloured tint.

        Two fixed layers (image on ``#neony-bg`` at z-index -2, tint on
        ``#neony-bg-tint`` at z-index -1).  The tint's ``background-color``
        references ``var(--color-bg)`` at 0.55 opacity, so it follows the
        theme through the CSS custom property — the exact mechanism that
        repaints every component on a theme switch.  A hard-coded rgba
        gradient was unreliable here: WebKitGTK caches the composited
        layer and never redraws it when the Python-side colour changes.

        The layers live on normal elements, not ``<body>``: transparent
        windows skip body-background painting, but an element always
        composites.  The image layer is only re-styled (never rebuilt) so
        the remote image isn't re-fetched.
        """
        url = self._background_url
        assert url is not None
        return (
            "(() => {"
            "let img = document.getElementById('neony-bg');"
            "if (!img) {"
            "img = document.createElement('div'); img.id = 'neony-bg';"
            "document.body.insertBefore(img, document.body.firstChild);"
            "}"
            "if (!document.getElementById('neony-bg-tint')) {"
            "const tint = document.createElement('div'); tint.id = 'neony-bg-tint';"
            "tint.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;"
            "z-index:-1;background-color:var(--color-bg);opacity:0.55;';"
            "document.body.insertBefore(tint, document.body.firstChild);"
            "}"
            f"img.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;"
            f"z-index:-2;background-image:url({url});background-size:cover;"
            "background-position:center center;background-repeat:no-repeat;';"
            "})()"
        )

    async def set_background(self, url: str) -> None:
        """Set a full-screen background image behind the glass UI.

        The image sits on a fixed ``#neony-bg`` layer under a
        ``var(--color-bg)`` tint layer; components with ``glass=True``
        (or :class:`~neony.application.elements.GlassPanel`) blur it
        through their translucent surfaces. The tint follows theme
        switches automatically — no re-injection needed.
        """
        if self._window is None:
            return
        self._background_url = url
        await self._window.eval_js(self._background_js())

    # ---- rendering ----

    async def render(self) -> None:
        """Render (or update) the DOM tree in the browser.

        The first call mounts the full tree; subsequent calls diff
        against the previous snapshot and send minimal patches.

        Once the window starts closing (minimize/maximize/close racing
        with in-flight events, or an actual close), WebKitGTK tears down
        the WebView and ``emit`` raises "WebView is not initialized" —
        those patches are dropped silently.
        """
        if self._tree is None:
            raise RuntimeError("NeonApplication: run() must be called first")
        try:
            await self._neony.render(self._tree)
        except RuntimeError as exc:
            if "WebView is not initialized" in str(exc):
                return  # window closing — drop the patch
            raise

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

    # ---- window control ----

    def _require_window(self) -> Window:
        if self._window is None:
            raise RuntimeError("NeonApplication: window not created yet")
        return self._window

    async def set_title(self, title: str) -> None:
        """Change the window title (OS taskbar/dock label)."""
        if self._window is None:
            raise RuntimeError("NeonApplication: window not created yet")
        self.config.window.title = title
        if self._window._tao is not None:
            await App.get().call_on_main(self._window._tao.set_title, title)
        await self._window.eval_js(f"document.title = {title!r}")

    async def set_size(self, width: int, height: int) -> None:
        """Resize the window."""
        await App.get().call_on_main(self._require_window().set_size, float(width), float(height))

    async def minimize(self) -> None:
        """Minimize the window."""
        await App.get().call_on_main(self._require_window().minimize)

    async def toggle_maximize(self) -> bool:
        """Toggle maximize state; returns the new state."""
        # pyrefly doesn't unwrap lumiview's Task[T] via __await__; cast
        # restores the declared type.
        return cast(bool, await App.get().call_on_main(self._require_window().toggle_maximize))

    async def is_maximized(self) -> bool:
        """True when the window is currently maximized."""
        return cast(bool, await App.get().call_on_main(self._require_window().is_maximized))

    async def set_fullscreen(self, fullscreen: bool) -> None:
        """Enter (or exit) fullscreen mode."""
        await App.get().call_on_main(self._require_window().set_fullscreen, fullscreen)

    async def start_dragging(self) -> None:
        """Begin an interactive window drag (custom titlebars)."""
        await App.get().call_on_main(self._require_window().start_dragging)

    async def close(self) -> None:
        """Request window close, honouring the configured close behavior."""
        await App.get().call_on_main(self._require_window().request_close)

    async def apply_blur(self, color: tuple[int, int, int, int] | None = None) -> None:
        """Apply a native blur material behind the window (macOS/Windows)."""
        await App.get().call_on_main(self._require_window().apply_effect, WindowEffect.Blur, color)

    async def apply_acrylic(self, color: tuple[int, int, int, int] | None = None) -> None:
        """Apply the acrylic material (Windows 11 frosted look)."""
        await App.get().call_on_main(self._require_window().apply_effect, WindowEffect.Acrylic, color)

    async def apply_mica(self) -> None:
        """Apply the mica material (Windows 11)."""
        await App.get().call_on_main(self._require_window().apply_effect, WindowEffect.Mica, None)

    async def clear_effect(self, effect: WindowEffect) -> None:
        """Remove a native material previously applied."""
        await App.get().call_on_main(self._require_window().clear_effect, effect)

    async def eval_js(self, script: str) -> str:
        """Execute *script* in the page; returns the result string."""
        return await self._require_window().eval_js(script)


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
