"""Page close hooks — ``page.on_close(fn)`` wired to the native close event.

User code declares handlers on the Page (like ``element.on_click(fn)``);
the framework maps Page → Window and registers them on lumiview's
``CloseRequestedEvent`` internally.  Handlers run before the window
closes; exceptions are logged but never block the close.
"""

import asyncio
from typing import Any

from lumiview import WindowEvent

from neony.application import Config, NeonApplication, Page
from neony.application.app import _Entry
from neony.dom.bridge import Neony


class HookWindow:
    """Fake lumiview Window that records registered hooks."""

    def __init__(self) -> None:
        self.hooks: dict = {}

    def on(self, event):
        def decorator(fn):
            self.hooks.setdefault(event, []).append(fn)
            return fn

        return decorator


def _wire(page: Page) -> tuple[NeonApplication, HookWindow]:
    """Wire a page's close handlers onto a fake window, like ``_main``."""
    app = NeonApplication(Config())
    tree = page.build()
    neony = Neony(name="neony")
    entry = _Entry(neony, tree, page)
    win = HookWindow()
    asyncio.run(app._wire_close_hook(entry, cast_any(win)))
    return app, win


def cast_any(win: HookWindow) -> Any:
    """Typing shim — _wire_close_hook takes lumiview's Window."""
    return win


def _fire(win: HookWindow) -> None:
    asyncio.run(win.hooks[WindowEvent.CloseRequestedEvent][0](WindowEvent.CloseRequestedEvent()))


class TestPageClose:
    def test_single_handler_fires(self):
        calls: list[str] = []
        page = Page().on_close(lambda: calls.append("closed"))

        _win = _wire(page)[1]

        _fire(_win)
        assert calls == ["closed"]

    def test_multiple_handlers_all_run(self):
        calls: list[str] = []
        page = Page()
        page.on_close(lambda: calls.append("first"))
        page.on_close(lambda: calls.append("second"))

        _win = _wire(page)[1]

        _fire(_win)
        assert calls == ["first", "second"]

    def test_exception_in_handler_isolated(self):
        """One handler raising must not stop the others or the close."""
        calls: list[str] = []
        page = Page()
        page.on_close(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        page.on_close(lambda: calls.append("survivor"))

        _win = _wire(page)[1]

        _fire(_win)  # must not raise
        assert calls == ["survivor"]

    def test_async_handler_awaited(self):
        calls: list[str] = []
        page = Page()

        async def handler() -> None:
            await asyncio.sleep(0)
            calls.append("async")

        page.on_close(handler)

        _win = _wire(page)[1]

        _fire(_win)
        assert calls == ["async"]

    def test_on_close_returns_self(self):
        page = Page()
        assert page.on_close(lambda: None) is page

    def test_no_handlers_wires_nothing(self):
        page = Page()

        _app, win = _wire(page)

        assert not win.hooks  # no handlers → no CloseRequested registration
