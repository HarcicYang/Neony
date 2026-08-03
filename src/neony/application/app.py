"""NeonApplication — a complete LumiView wrapper with reactive DOM.

Wraps App creation, Window setup, the Neony bridge, handler collection
from the DOM tree, auto-render, theme injection, and a user-facing
state namespace.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from types import SimpleNamespace
from typing import Any, cast

from lumiview import App, Bridge, Window, WindowEffect, WindowHookEvent

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


class _Entry:
    """Per-window runtime state: bridge scope, window, and DOM tree."""

    __slots__ = ("neony", "tree", "window")

    def __init__(self, neony: Neony, tree: DOMElement) -> None:
        self.neony = neony
        self.window: Window | None = None
        self.tree = tree


# Style-only events that don't need an immediate full-tree render.  They
# render deferred (one frame of coalescing) so a mouse sweeping across the
# UI doesn't trigger a full-tree render per event.  Adding "input" here
# also enables keystroke throttling.
_DEFERRED_EVENTS = frozenset({"mouseover", "mouseout", "focus", "blur"})


def _set_linux_app_name(name: str) -> None:
    """Set the GLib program name so the window manager shows *name*
    instead of ``python3`` in the taskbar / launcher.

    On Linux the WM_CLASS used by taskbars and docks defaults to the
    process name (``argv[0]``).  lumiview's ``App(name=...)`` only
    reaches the titlebar text — it never sets the GTK program name, and
    ``TaoWindowBuilder`` exposes no ``with_class()`` API.  We set
    ``g_set_prgname`` via ctypes: GLib is already linked by tao's GTK
    backend, so the library is guaranteed to be present without adding
    a PyGObject dependency.
    """
    if sys.platform != "linux":
        return
    try:
        import ctypes

        glib = ctypes.CDLL("libglib-2.0.so.0")
        glib.g_set_prgname(name.encode())
    except OSError:
        pass  # should never happen on Linux, but don't crash


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
        self._entries: list[_Entry] = []
        self.state: SimpleNamespace = SimpleNamespace()
        self.theme: Theme = Theme()
        self.ready_handler: Any = None  # optional async callable, run after windows ready

    # ---- lifecycle ----

    def run(self, *pages: Page | DOMElement) -> None:
        """Blocking entry point.

        Each *page* opens its own window. All windows share the same
        LumiView event loop and this app's ``state`` namespace — handlers
        from any window read/write the same ``app.state``.
        """
        for page in pages:
            tree = page.build() if isinstance(page, Page) else page
            neony = Neony(name="neony", mount_selector=self.config.mount_selector)
            idx = len(self._entries)
            self._entries.append(_Entry(neony, tree))
            self._collect_handlers(neony, tree, idx)
        # Linux: make the taskbar/dock show the app name instead of
        # ``python3`` — lumiview's App(name=...) never reaches WM_CLASS.
        _set_linux_app_name(self.config.window.title)
        app = App(name=self.config.window.title.replace(" ", ""))
        app.run(self._main)

    async def _main(self) -> None:
        kwargs = self.config.to_window_kwargs()
        title = kwargs.pop("title", "Neony")
        for i, entry in enumerate(self._entries):
            # Frameless windows get the WindowControls scope: it injects
            # the ``lumiview.window.*`` JS API plus drag/resize region
            # handlers (all Bridge commands, no raw JS in user code).
            includes: list = [entry.neony]
            if not self.config.window.decorations:
                from lumiview.plugins.window_controls import WindowControls

                includes.append(WindowControls())
            entry.window = await Window.create(
                title=title if i == 0 else f"{title} {i + 1}",
                html=_INITIAL_HTML,
                bridge=Bridge(includes=includes),
                **kwargs,
            )
            # Wait for the page (including the injected Bridge JS) to
            # finish loading before mounting — a fixed sleep would either
            # race slow machines or waste time on fast ones.  The 5s
            # timeout only guards against an event never arriving.
            page_loaded = asyncio.Event()
            # PageLoadFinished carries the loaded URL as an argument —
            # ``*_args`` absorbs it so the default-bound event isn't
            # overwritten (lumiview calls the handler with the URL).
            entry.window.on(WindowHookEvent.PageLoadFinished)(
                lambda *_args, _loaded=page_loaded: _loaded.set()
            )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(page_loaded.wait(), timeout=5.0)
            await self._inject_theme(entry)
            await self.render(window_index=i)
        if self.ready_handler is not None:
            await self.ready_handler()

    # ---- theme ----

    async def sync_theme(self) -> None:
        """Inject the current theme's ``:root`` CSS variables into every page.

        Switching ``app.theme.mode`` and calling this re-injects the
        block — every ``var(--color-*)`` redraws with zero DOM diff.

        The ``<body>`` background is set to the theme colour so the page
        stays themed even with a transparent Page root.  The background
        image's tint layer (from :meth:`set_background`) references
        ``var(--color-bg)`` too, so it re-tints on the same injection.
        """
        for entry in self._entries:
            if entry.window is not None:
                await self._inject_theme(entry)

    async def _inject_theme(self, entry: _Entry) -> None:
        """Inject theme CSS variables into one window's page."""
        assert entry.window is not None
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
        await entry.window.eval_js(js)

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
        self._background_url = url
        for entry in self._entries:
            if entry.window is not None:
                await entry.window.eval_js(self._background_js())

    # ---- rendering ----

    async def render(self, window_index: int | None = None, *, immediate: bool = True) -> None:
        """Render (or update) the DOM tree(s) in the browser.

        The first call mounts the full tree; subsequent calls diff
        against the previous snapshot and send minimal patches.

        Without *window_index* every window renders; a specific index
        renders only that window (the auto-render after an event handler
        does this — only the originating window re-renders).

        *immediate* is forwarded to the Neony bridge: ``False`` defers
        the render by one frame so a burst of style-only events
        (hover, focus, blur) coalesces into a single render.

        Once a window starts closing (minimize/maximize/close racing
        with in-flight events, or an actual close), WebKitGTK tears down
        the WebView and ``emit`` raises "WebView is not initialized" —
        those patches are dropped silently.
        """
        if not self._entries:
            raise RuntimeError("NeonApplication: run() must be called first")
        indices = range(len(self._entries)) if window_index is None else (window_index,)
        for i in indices:
            entry = self._entries[i]
            if entry.window is None:
                continue
            try:
                await entry.neony.render(entry.tree, immediate=immediate)
            except RuntimeError as exc:
                if "WebView is not initialized" in str(exc):
                    return  # window closing — drop the patch
                raise

    # ---- handler collection ----

    def _collect_handlers(self, neony: Neony, element: DOMElement, idx: int) -> None:
        """Walk the tree and register element handlers on one window's bridge."""
        for event_type, fns in element._handlers.items():
            for fn in fns:
                neony.on(event_type, key=element.key)(self._make_wrapper(fn, element, idx))
        for child in element.container:
            if isinstance(child, DOMElement):
                self._collect_handlers(neony, child, idx)

    def _make_wrapper(self, fn: Any, element: DOMElement, idx: int) -> Any:
        """Wrap a user handler: build DomEvent, call fn, auto-render
        only the window the event came from.

        Style-only events (hover / focus / blur) render deferred — one
        frame of coalescing — so a mouse sweeping across the UI doesn't
        trigger a full-tree render per event.
        """

        async def wrapper(key: str, event_type: str, value: Any = None) -> None:
            evt = DomEvent(key=key, type=event_type, value=value)
            await fn(evt)
            if self.config.auto_render:
                immediate = event_type not in _DEFERRED_EVENTS
                await self.render(window_index=idx, immediate=immediate)

        return wrapper

    # ---- window control ----

    def _require_window(self, window_index: int = 0) -> Window:
        try:
            window = self._entries[window_index].window
        except IndexError:
            raise RuntimeError("NeonApplication: window not created yet") from None
        if window is None:
            raise RuntimeError("NeonApplication: window not created yet")
        return window

    async def set_title(self, title: str, window_index: int = 0) -> None:
        """Change a window's title (OS taskbar/dock label)."""
        window = self._require_window(window_index)
        self.config.window.title = title
        if window._tao is not None:
            await App.get().call_on_main(window._tao.set_title, title)
        await window.eval_js(f"document.title = {title!r}")

    async def set_size(self, width: int, height: int, window_index: int = 0) -> None:
        """Resize a window."""
        await App.get().call_on_main(self._require_window(window_index).set_size, float(width), float(height))

    async def minimize(self, window_index: int = 0) -> None:
        """Minimize a window."""
        await App.get().call_on_main(self._require_window(window_index).minimize)

    async def toggle_maximize(self, window_index: int = 0) -> bool:
        """Toggle maximize state; returns the new state."""
        # pyrefly doesn't unwrap lumiview's Task[T] via __await__; cast
        # restores the declared type.
        return cast(bool, await App.get().call_on_main(self._require_window(window_index).toggle_maximize))

    async def is_maximized(self, window_index: int = 0) -> bool:
        """True when a window is currently maximized."""
        return cast(bool, await App.get().call_on_main(self._require_window(window_index).is_maximized))

    async def set_fullscreen(self, fullscreen: bool, window_index: int = 0) -> None:
        """Enter (or exit) fullscreen mode."""
        await App.get().call_on_main(self._require_window(window_index).set_fullscreen, fullscreen)

    async def start_dragging(self, window_index: int = 0) -> None:
        """Begin an interactive window drag (custom titlebars)."""
        await App.get().call_on_main(self._require_window(window_index).start_dragging)

    async def close(self, window_index: int = 0) -> None:
        """Request a window close, honouring the configured close behavior."""
        await App.get().call_on_main(self._require_window(window_index).request_close)

    async def apply_blur(self, color: tuple[int, int, int, int] | None = None, window_index: int = 0) -> None:
        """Apply a native blur material behind a window (macOS/Windows)."""
        await App.get().call_on_main(self._require_window(window_index).apply_effect, WindowEffect.Blur, color)

    async def apply_acrylic(self, color: tuple[int, int, int, int] | None = None, window_index: int = 0) -> None:
        """Apply the acrylic material (Windows 11 frosted look)."""
        await App.get().call_on_main(self._require_window(window_index).apply_effect, WindowEffect.Acrylic, color)

    async def apply_mica(self, window_index: int = 0) -> None:
        """Apply the mica material (Windows 11)."""
        await App.get().call_on_main(self._require_window(window_index).apply_effect, WindowEffect.Mica, None)

    async def clear_effect(self, effect: WindowEffect, window_index: int = 0) -> None:
        """Remove a native material previously applied."""
        await App.get().call_on_main(self._require_window(window_index).clear_effect, effect)

    async def eval_js(self, script: str, window_index: int = 0) -> str:
        """Execute *script* in a page; returns the result string."""
        return await self._require_window(window_index).eval_js(script)


def launch(page: Page | DOMElement | list[Page | DOMElement], **config_kwargs: Any) -> None:
    """Convenience: build a Config from kwargs and run *page*.

    Example::

        launch(page, title="Demo", width=480, height=640, devtools=True)
        launch([page_one, page_two], title="Multi", ...)  # two windows

    Pass a list of pages to open multiple windows sharing one app state.
    Recognised kwargs mirror :class:`WindowConfig` / :class:`WebViewConfig`
    fields plus ``mount_selector`` and ``auto_render``.
    """
    from neony.application.config import WebViewConfig, WindowConfig

    pages = page if isinstance(page, list) else [page]

    window_cfg = {k: v for k, v in config_kwargs.items() if k in WindowConfig.model_fields}
    webview_cfg = {k: v for k, v in config_kwargs.items() if k in WebViewConfig.model_fields}
    top_cfg = {k: v for k, v in config_kwargs.items() if k in ("mount_selector", "auto_render")}

    config = Config(
        window=WindowConfig(**window_cfg),
        webview=WebViewConfig(**webview_cfg),
        **top_cfg,
    )
    NeonApplication(config).run(*pages)
