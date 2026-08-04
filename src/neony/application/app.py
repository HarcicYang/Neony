"""NeonApplication — LumiView wrapper: windows, the Neony bridge,
handler collection, auto-render, theme injection, and app state."""

from __future__ import annotations

import asyncio
import contextlib
import sys
from types import SimpleNamespace
from typing import Any, Generic, TypeVar, cast

from lumiview import App, Bridge, Window, WindowEffect, WindowHookEvent

from neony.application.config import Config
from neony.application.page import Page
from neony.application.theme import Theme
from neony.dom import DOMElement, DomEvent
from neony.dom.bridge import Neony

# margin:0 — the browser default 8px body margin would leave a white
# ring around the page.  height:100% chain — vh units lag the real
# window size under tiling WMs (e.g. hyprland), percentages follow it.
# box-sizing:border-box — width:100% + padding would overflow the
# window's right edge.
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


# Style-only events: deferred one frame of coalescing so a mouse sweep
# doesn't trigger a full-tree render per event.
_DEFERRED_EVENTS = frozenset({"mouseover", "mouseout", "focus", "blur"})

# User state type: inferred from the ``state=`` constructor argument
# (dataclass, pydantic model, ...).  Falls back to SimpleNamespace.
_S = TypeVar("_S")


def _set_linux_app_name(name: str) -> None:
    """Set the GLib program name so the taskbar shows *name* instead of
    ``python3`` (WM_CLASS defaults to ``argv[0]``; lumiview's
    ``App(name=...)`` never reaches it).  ctypes is safe — GLib is
    already linked by tao's GTK backend."""
    if sys.platform != "linux":
        return
    try:
        import ctypes

        glib = ctypes.CDLL("libglib-2.0.so.0")
        glib.g_set_prgname(name.encode())
    except OSError:
        pass  # should never happen on Linux, but don't crash


class NeonApplication(Generic[_S]):
    """Reactive desktop application built on LumiView + Neony DOM.

    ``state`` defaults to a bare ``SimpleNamespace``; pass your own
    dataclass / pydantic model via the ``state=`` argument for typed
    attributes::

        app = NeonApplication(Config(window=WindowConfig(title="Demo")))
        counter = Button("Click me")
        counter.on_click(lambda e: setattr(counter, "label", "Clicked!"))
        app.run(Page().add(counter))
    """

    def __init__(self, config: Config | None = None, *, state: _S | None = None) -> None:
        self.config = config or Config()
        self._entries: list[_Entry] = []
        # Fire-and-forget render tasks scheduled by signal bindings.
        self._render_tasks: set[asyncio.Task] = set()
        self.state: _S = state if state is not None else cast(_S, SimpleNamespace())
        self.theme: Theme = Theme()
        self.ready_handler: Any = None  # optional async callable, run after windows ready

    # ---- lifecycle ----

    def run(self, *pages: Page | DOMElement) -> None:
        """Blocking entry point — one window per *page*, all sharing one
        event loop and the app's ``state`` namespace."""
        for page in pages:
            tree = page.build() if isinstance(page, Page) else page
            neony = Neony(name="neony", mount_selector=self.config.mount_selector)
            idx = len(self._entries)
            self._entries.append(_Entry(neony, tree))
            self._collect_handlers(neony, tree, idx)
            self._arm_render_request(tree, idx)
        # Linux: taskbar/dock shows the app name, not ``python3``.
        _set_linux_app_name(self.config.window.title)
        app = App(name=self.config.window.title.replace(" ", ""))
        app.run(self._main)

    async def _main(self) -> None:
        kwargs = self.config.to_window_kwargs()
        title = kwargs.pop("title", "Neony")
        for i, entry in enumerate(self._entries):
            # Frameless windows get the WindowControls scope
            # (``lumiview.window.*`` bridge commands).
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
            # Wait for the page (Bridge JS included) before mounting —
            # a fixed sleep would race slow machines.  5s guards against
            # the event never arriving.
            page_loaded = asyncio.Event()
            # PageLoadFinished passes the loaded URL as an argument —
            # ``*_args`` absorbs it.
            entry.window.on(WindowHookEvent.PageLoadFinished)(lambda *_args, _loaded=page_loaded: _loaded.set())
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(page_loaded.wait(), timeout=5.0)
            await self._inject_theme(entry)
            await self.render(window_index=i)
        if self.ready_handler is not None:
            await self.ready_handler()

    # ---- theme ----

    async def sync_theme(self) -> None:
        """Re-inject the theme's ``:root`` CSS variables into every page —
        every ``var(--color-*)`` redraws with zero DOM diff."""
        for entry in self._entries:
            if entry.window is not None:
                await self._inject_theme(entry)

    async def _inject_theme(self, entry: _Entry) -> None:
        """Inject theme CSS variables into one window's page."""
        assert entry.window is not None
        css = self.theme.to_css()
        # NOTE: ``})()`` closes the IIFE — a stray brace makes the whole
        # script a SyntaxError.
        # Transparent windows keep the body transparent so the native
        # background (or blur) shows through.
        body_bg = (
            "document.body.style.backgroundColor = 'var(--color-bg)';" if not self.config.window.transparent else ""
        )
        js = (
            f"(() => {{ const el = document.getElementById('neony-theme'); "
            f"if (el) el.textContent = {css!r}; else {{ const s = document.createElement('style'); "
            f"s.id = 'neony-theme'; s.textContent = {css!r}; document.head.appendChild(s); }} "
            f"{body_bg} }})()"
        )
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
        """JS painting the background image under a theme-coloured tint.

        Two fixed layers: the image on ``#neony-bg`` (z-index -2) and a
        ``var(--color-bg)`` tint on ``#neony-bg-tint`` (z-index -1), so
        the tint follows theme switches via the CSS variable.  Layers sit
        on elements, not ``<body>`` (transparent windows skip
        body-background painting).  The image layer is only re-styled,
        never rebuilt, so the remote image isn't re-fetched.
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
        """Full-screen background image behind the glass UI; the tint
        follows theme switches automatically."""
        self._background_url = url
        for entry in self._entries:
            if entry.window is not None:
                await entry.window.eval_js(self._background_js())

    # ---- rendering ----

    async def render(self, window_index: int | None = None, *, immediate: bool = True) -> None:
        """Render (or update) the DOM tree(s).  First call mounts; later
        calls diff and send minimal patches.  Without *window_index* every
        window renders; a specific index renders only that window.

        *immediate=False* defers by one frame so hover/focus/blur bursts
        coalesce.  Patches are dropped silently once a closing window's
        WebView tears down ("WebView is not initialized").
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

    def _arm_render_request(self, tree: DOMElement, idx: int) -> None:
        """Wire the tree root so bound-signal writes can schedule renders
        (dropped outside a running event loop — the next event-driven
        render picks the change up anyway)."""

        def request() -> None:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return
            # Held in a set so the task isn't garbage-collected mid-run.
            self._render_tasks.add(asyncio.create_task(self.render(window_index=idx)))

        tree._render_request = request

    def _collect_handlers(self, neony: Neony, element: DOMElement, idx: int) -> None:
        """Register element handlers on one window's bridge; every element
        also lands in the key map so opt-in bubbling can walk the parent
        chain from any handler-less key."""
        neony._key_map[element.key] = element
        for event_type, fns in element._handlers.items():
            for fn in fns:
                neony.on(event_type, key=element.key)(self._make_wrapper(fn, element, idx))
        for child in element.container:
            if isinstance(child, DOMElement):
                self._collect_handlers(neony, child, idx)

    def _make_wrapper(self, fn: Any, element: DOMElement, idx: int) -> Any:
        """Wrap a user handler: build a DomEvent, call *fn*, auto-render
        only the originating window (style-only events deferred)."""

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


def launch(
    page: Page | DOMElement | list[Page | DOMElement],
    *,
    state: Any = None,
    **config_kwargs: Any,
) -> None:
    """Build a Config from kwargs and run *page* (a list opens multiple
    windows sharing one app state).  Kwargs mirror :class:`WindowConfig` /
    :class:`WebViewConfig` plus ``mount_selector`` and ``auto_render``.
    *state* replaces the default ``SimpleNamespace`` (see
    :class:`NeonApplication`)."""
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
    NeonApplication(config, state=state).run(*pages)
