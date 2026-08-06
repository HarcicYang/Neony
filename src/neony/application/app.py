"""NeonApplication — LumiView wrapper: windows, the Neony bridge,
handler collection, auto-render, theme injection, and app state."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, Generic, Self, TypeVar, cast

from lumiview import App, AppEvent, Bridge, Window, WindowEffect, WindowEvent
from wryview import DragDropEvent

from neony.application._helpers import (
    _BUILTIN_KEYFRAMES,
    _DEFERRED_EVENTS,
    _INITIAL_HTML,
    _TRANSPARENT_EFFECTS,
    _Entry,
    _file_info,
    _js_result_value,
    _set_linux_app_name,
)
from neony.application.config import Config
from neony.application.page import Page
from neony.application.theme import Theme
from neony.dom import DOMElement, DomEvent, KeyFrame
from neony.dom.bridge import Neony

# User state type: inferred from the ``state=`` constructor argument
# (dataclass, pydantic model, ...).  Falls back to SimpleNamespace.
_S = TypeVar("_S")


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
        self.close_handler: Any = None  # optional async callable, run when the app exits

        self._clip: object | None = None  # clipboard (pyclip)
        # Registered @keyframes: name → full CSS text, injected into a
        # <style id="neony-keyframes"> in every window's <head>.
        self._keyframes: dict[str, str] = {}

    # ---- lifecycle ----

    def run(self, *pages: Page | DOMElement) -> None:
        """Blocking entry point — one window per *page*, all sharing one
        event loop and the app's ``state`` namespace."""
        for page in pages:
            tree = page.build() if isinstance(page, Page) else page
            neony = Neony(name="neony", mount_selector=self.config.mount_selector)
            idx = len(self._entries)
            self._entries.append(_Entry(neony, tree, page if isinstance(page, Page) else None))
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
                # The native drag-drop channel: WebKitGTK cannot deliver
                # file data to the page when a handler is installed, so
                # Neony takes over drops (WindowEvent.DragEvent) and
                # re-dispatches them from Python.
                drag_drop=True,
                **kwargs,
            )
            entry.window.on(WindowEvent.DragEvent)(self._make_drag_drop_handler(entry))
            # Wait for the page (Bridge JS included) before mounting —
            # a fixed sleep would race slow machines.  5s guards against
            # the event never arriving.
            page_loaded = asyncio.Event()
            entry.window.on(WindowEvent.PageLoadFinishedEvent)(lambda _event, _loaded=page_loaded: _loaded.set())
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(page_loaded.wait(), timeout=5.0)
            await self._inject_theme(entry)
            await self._inject_keyframes(entry)
            await self._apply_transparent_effect(entry.window)
            await self._wire_close_hook(entry, entry.window)
            await self._wire_focus_hook(entry, entry.window)
            await self._wire_navigation_policy(entry, entry.window)
            await self.render(window_index=i)
        if self.ready_handler is not None:
            await self.ready_handler()
        # App-level teardown: fires once after all windows close, before
        # lumiview stops the asyncio loop (completion awaited, 5s guard).
        await self._wire_close_handler()

    async def _wire_close_hook(self, entry: _Entry, window: Window) -> None:
        """Wire a Page's close handlers to the window's native close event.

        User code declares handlers on the Page; the framework maps
        Page → Window here.  lumiview applies the close default only
        after the handlers finish (exceptions are logged, never blocking
        close).
        """
        if entry.page is None or not entry.page._close_handlers:
            return
        handlers = list(entry.page._close_handlers)

        async def _on_window_close(_event: WindowEvent.CloseRequestedEvent) -> None:
            results = await asyncio.gather(
                *[self._run_handler(h) for h in handlers],
                return_exceptions=True,
            )
            for exc in (r for r in results if isinstance(r, BaseException)):
                logging.getLogger("neony.app").error("Page close handler failed", exc_info=exc)

        window.on(WindowEvent.CloseRequestedEvent)(_on_window_close)

    async def _wire_focus_hook(self, entry: _Entry, window: Window) -> None:
        """Wire a Page's focus/blur handlers to the window's native
        focus events (``FocusedEvent`` / ``UnfocusedEvent``)."""
        if entry.page is None:
            return
        if entry.page._focus_handlers:
            handlers = list(entry.page._focus_handlers)

            async def _on_focused(_event: WindowEvent.FocusedEvent) -> None:
                await asyncio.gather(
                    *[self._run_handler(h) for h in handlers],
                    return_exceptions=True,
                )

            window.on(WindowEvent.FocusedEvent)(_on_focused)
        if entry.page._blur_handlers:
            handlers = list(entry.page._blur_handlers)

            async def _on_unfocused(_event: WindowEvent.UnfocusedEvent) -> None:
                await asyncio.gather(
                    *[self._run_handler(h) for h in handlers],
                    return_exceptions=True,
                )

            window.on(WindowEvent.UnfocusedEvent)(_on_unfocused)

    async def _wire_navigation_policy(self, entry: _Entry, window: Window) -> None:
        """Install navigation / new-window / download policies.

        Safe defaults are always installed — every navigation blocked,
        every new-window request denied (no system-browser open), every
        download cancelled — so an in-page link can never navigate the
        app UI away.  Page-level handlers registered via ``on_navigation``
        & co. replace the default (a policy is a single decision; the
        last handler wins).  ``prevent()`` cancels the native default;
        ``save_to()`` / ``open_in()`` redirect it.
        """
        nav_fn = entry.page._navigation_handler if entry.page is not None else None

        def _on_navigation(event: WindowEvent.NavigationRequestedEvent) -> None:
            if nav_fn is None or not nav_fn(event.url):
                event.prevent()

        new_window_fn = entry.page._new_window_handler if entry.page is not None else None

        def _on_new_window(event: WindowEvent.NewWindowRequestedEvent) -> None:
            if new_window_fn is None or new_window_fn(event.url) != "allow":
                # Deny the in-webview window and don't open the system
                # browser (the native default would open it).
                event.prevent()

        download_fn = entry.page._download_started_handler if entry.page is not None else None

        def _on_download_started(event: WindowEvent.DownloadStartedEvent) -> None:
            if download_fn is None:
                event.prevent()  # cancel by default
                return
            decision = download_fn(event.url, event.suggested_path)
            if decision is False:
                event.prevent()
            elif isinstance(decision, str):
                event.save_to(decision)

        window.on(WindowEvent.NavigationRequestedEvent)(_on_navigation)
        window.on(WindowEvent.NewWindowRequestedEvent)(_on_new_window)
        window.on(WindowEvent.DownloadStartedEvent)(_on_download_started)

        if entry.page is not None and entry.page._download_completed_handlers:
            handlers = list(entry.page._download_completed_handlers)

            # Event handlers run on the asyncio loop — async handlers are
            # awaited (unlike the old native callback channel).
            async def _on_download_completed(event: WindowEvent.DownloadCompletedEvent) -> None:
                for fn in handlers:
                    try:
                        result = fn(event.url, event.saved_path, event.success)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as exc:
                        logging.getLogger("neony.app").error("Page download-completed handler failed", exc_info=exc)

            window.on(WindowEvent.DownloadCompletedEvent)(_on_download_completed)

    async def _wire_close_handler(self) -> None:
        """Register the app-level teardown hook on lumiview's
        ``AppCloseEvent`` (fires once after all windows close, before
        the asyncio loop stops; completion is awaited)."""
        if self.close_handler is not None:

            async def _on_app_close(_event: AppEvent.AppCloseEvent) -> None:
                await self._run_handler(self.close_handler)

            App.get().on(AppEvent.AppCloseEvent)(_on_app_close)

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

    def register_keyframe(self, kf: KeyFrame) -> Self:
        """Register a :class:`KeyFrame` for injection into every window
        (chainable).  Registering another KeyFrame with the same name
        replaces the first (later-wins).  Open windows are updated
        immediately; windows created later pick it up on startup.

        Usage::

            spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)"))
                                   .set("100%", Props(transform="rotate(360deg)"))
            app.register_keyframe(spin)
        """
        self._keyframes[kf.name] = kf.to_css()
        for entry in self._entries:
            if entry.window is not None:
                # Held in a set so the task isn't garbage-collected mid-run.
                self._render_tasks.add(asyncio.create_task(self._inject_keyframes(entry)))
        return self

    async def sync_keyframes(self) -> None:
        """Re-inject every registered ``@keyframes`` rule into all open
        windows — call after replacing keyframes at runtime."""
        for entry in self._entries:
            if entry.window is not None:
                await self._inject_keyframes(entry)

    async def _inject_keyframes(self, entry: _Entry) -> None:
        """Inject all ``@keyframes`` CSS into one window's page, creating
        or updating ``<style id="neony-keyframes">``.  Built-ins first,
        then user-registered keyframes (later-wins on name collision)."""
        css_blocks: dict[str, str] = {}
        for kf in _BUILTIN_KEYFRAMES:
            css_blocks[kf.name] = kf.to_css()
        css_blocks.update(self._keyframes)
        if not css_blocks:
            return
        assert entry.window is not None
        css = "\n".join(css_blocks.values())
        js = (
            f"(() => {{ const el = document.getElementById('neony-keyframes'); "
            f"if (el) el.textContent = {css!r}; else {{ const s = document.createElement('style'); "
            f"s.id = 'neony-keyframes'; s.textContent = {css!r}; document.head.appendChild(s); }} }})()"
        )
        await entry.window.eval_js(js)

    async def _apply_transparent_effect(self, window: Window) -> None:
        """Give transparent windows their platform material automatically.

        ``WindowConfig.transparent=True`` requests a see-through window;
        on Windows that reads as black glass without a material, and on
        macOS as plain alpha.  Apply the platform's native effect so the
        transparency actually looks frosted — Acrylic on Windows, Blur
        on macOS (see ``_TRANSPARENT_EFFECTS``).  On Linux the
        compositor blurs the desktop behind the window via the Wayland
        ``ext-background-effect-v1`` protocol where supported (KWin);
        compositors with their own blur for transparent windows
        (Hyprland) keep that default blur untouched.  Elsewhere the
        window stays transparent without a blur.  A failure is logged,
        never fatal: the window keeps working, just without the
        effect.
        """
        if not self.config.window.transparent:
            return
        if sys.platform == "linux":
            from neony.application._linux_blur import apply_wayland_blur

            try:
                await App.get().call_on_main(apply_wayland_blur, window)
            except Exception:
                logging.getLogger("neony.app").exception("Wayland blur failed")
            return
        effect = _TRANSPARENT_EFFECTS.get(sys.platform)
        if effect is not None:
            try:
                await App.get().call_on_main(window.apply_effect, effect, None)
            except Exception:
                logging.getLogger("neony.app").exception(f"apply_effect({effect}) failed on {sys.platform}")

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

    @staticmethod
    async def _run_handler(fn: Any, *args: Any) -> None:
        """Call *fn(*args)*, awaiting it if it's a coroutine (sync/async
        friendly — same pattern as ``Component._dispatch``)."""
        result = fn(*args)
        if asyncio.iscoroutine(result):
            await result

    def _make_wrapper(self, fn: Any, element: DOMElement, idx: int) -> Any:
        """Wrap a user handler: build a DomEvent, call *fn*, auto-render
        only the originating window (style-only events deferred).

        *fn* may be sync or async — a bare ``await fn(evt)`` would raise
        ``TypeError`` on sync handlers and skip the render (regression:
        every event handler crashed and the UI never refreshed).
        """

        async def wrapper(key: str, event_type: str, value: Any = None, **extra: Any) -> None:
            evt = DomEvent(key=key, type=event_type, value=value, **extra)
            result = fn(evt)
            if asyncio.iscoroutine(result):
                await result
            if self.config.auto_render:
                immediate = event_type not in _DEFERRED_EVENTS
                await self.render(window_index=idx, immediate=immediate)

        return wrapper

    # ---- native file drop channel ----

    def _make_drag_drop_handler(self, entry: _Entry) -> Callable[[WindowEvent.DragEvent], Any]:
        """Build the window's native drag-drop listener — a native
        takeover of file drops, because WebKitGTK cannot deliver file
        data to the page when the handler is installed (verified in the
        real environment: the JS ``drop`` event fires with an *empty*
        ``dataTransfer.files``; only the native handler receives the
        real paths — ``File.path`` was removed in WebKitGTK ≥ 2.52
        anyway).

        lumiview forwards the wryview drag-drop callback as a
        :class:`WindowEvent.DragEvent` (requires ``drag_drop=True`` at
        window creation).  On ``Drop`` the file list is re-dispatched
        as a normal Neony ``drop`` event from Python (see
        :meth:`_dispatch_native_drop`), with ``name``/``path``/``size``/
        ``type`` filled from the real paths.  ``dragover``/``dragleave``
        still reach the page (separate signals), so drop-zone
        highlighting keeps working.
        """

        async def handler(event: WindowEvent.DragEvent) -> None:
            if event.kind in (DragDropEvent.Enter, DragDropEvent.Drop):
                entry.neony.native_drop_paths[:] = event.paths
            if event.kind is DragDropEvent.Drop and event.paths:
                files = [_file_info(p) for p in event.paths]
                await self._dispatch_native_drop(entry, files, event.position)

        return handler

    async def _dispatch_native_drop(
        self,
        entry: _Entry,
        files: list[dict[str, Any]],
        position: tuple[int, int],
    ) -> None:
        """Deliver a natively-captured drop to the element under the
        pointer: hit-test the position from Python (``elementFromPoint``),
        then dispatch a regular ``drop`` event through the bridge."""
        if entry.window is None:
            return
        try:
            script = (
                "var el = document.elementFromPoint({}, {});"
                "el = (el && el.closest) ? el.closest('[data-neony-key]') : null;"
                "el ? el.getAttribute('data-neony-key') : ''"
            ).format(*position)
            key = _js_result_value(await entry.window.eval_js(script))
        except Exception:
            logging.getLogger("neony").exception("native drop hit-test failed")
            key = ""
        if key:
            await entry.neony._on_event(cast(Any, None), key=key, event_type="drop", value=None, drop_files=files)

    # ---- window control ----

    def _require_window(self, window_index: int = 0) -> Window:
        try:
            window = self._entries[window_index].window
        except IndexError:
            raise RuntimeError("NeonApplication: window not created yet") from None
        if window is None:
            raise RuntimeError("NeonApplication: window not created yet")
        return window

    def _load_pyclip(self) -> None:
        import pyclip

        self._clip = pyclip

    async def set_title(self, title: str, window_index: int = 0) -> None:
        """Change a window's title (OS taskbar/dock label)."""
        window = self._require_window(window_index)
        self.config.window.title = title
        await App.get().call_on_main(window.set_title, title)
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

    async def show(self, window_index: int = 0) -> None:
        """Show a hidden window (restore from taskbar / dock)."""
        await App.get().call_on_main(self._require_window(window_index).show)

    async def hide(self, window_index: int = 0) -> None:
        """Hide the window (keeps it running, off the taskbar)."""
        await App.get().call_on_main(self._require_window(window_index).hide)

    async def focus(self, window_index: int = 0) -> None:
        """Give the window keyboard focus."""
        await App.get().call_on_main(self._require_window(window_index).focus)

    async def set_bounds(self, x: float, y: float, w: float, h: float, window_index: int = 0) -> None:
        """Move and resize a window: (*x*, *y*) is the top-left screen
        position in logical pixels, (*w*, *h*) the new inner size.

        Position goes through lumiview's ``set_outer_position`` directly
        (``set_bounds`` only positions the webview child inside the
        window); sizing reuses :meth:`set_size`.  Note that Wayland
        forbids client-side positioning — there the window only resizes.
        A positioning failure never blocks the resize.
        """
        window = self._require_window(window_index)
        try:
            await App.get().call_on_main(window.set_outer_position, x, y)
        except Exception:
            logging.getLogger("neony").exception("set_outer_position failed (no-op on Wayland) — resizing anyway")
        await self.set_size(int(w), int(h), window_index=window_index)

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

    async def set_icon(self, icon: str | tuple[bytes, int, int], window_index: int = 0) -> None:
        """Set or replace the window icon (taskbar / window manager).

        *icon* is a file path (PNG, ICO, …) or raw RGBA data
        ``(bytes, width, height)``.  For the startup icon, prefer
        ``WindowConfig.icon`` — set at creation; this method changes it
        at runtime.
        """
        await App.get().call_on_main(self._require_window(window_index).set_icon, icon)

    # ---- clipboard ----

    async def clipboard_write(self, text: str) -> None:
        """
        Write *text* to the system clipboard.
        """
        if self._clip is None:
            self._load_pyclip()

        await asyncio.to_thread(self._clip.copy, text)  # type: ignore

    async def clipboard_read(self) -> bytes | str:
        """
        Read text from the system clipboard and return it.
        """
        if self._clip is None:
            self._load_pyclip()

        return await asyncio.to_thread(self._clip.paste)  # type: ignore


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
