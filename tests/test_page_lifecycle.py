"""Window focus/blur events and navigation/download policies.

``page.on_focus`` / ``on_blur`` stack like ``on_close`` and are wired to
the native ``Focused`` / ``Unfocused`` window events.  The navigation /
new-window / download-started policies are single decisions (the last
handler wins) with safe defaults installed for every window; download-
completed is a stacking notification.
"""

import asyncio
from collections.abc import Callable
from typing import Any, cast

import pytest
from lumiview import WindowBaseEvent, WindowEvent

from neony.application import Config, NeonApplication, Page
from neony.application._helpers import _Entry
from neony.dom.bridge import Neony


class HookWindow:
    """Fake lumiview Window recording ``on()`` hook registrations."""

    def __init__(self) -> None:
        self.hooks: dict = {}

    def on(self, event):
        def decorator(fn):
            self.hooks.setdefault(event, []).append(fn)
            return fn

        return decorator


class FakeWindow(HookWindow):
    """Fake lumiview Window — the policy handlers register via ``on()``
    like any other event (dev3 dropped the ``set_on_*`` setters)."""


def _entry(page: Page) -> _Entry:
    return _Entry(Neony(name="neony"), page.build(), page)


def _wire_focus(page: Page) -> tuple[NeonApplication, HookWindow]:
    """Wire a page's focus/blur handlers onto a fake window."""
    app = NeonApplication(Config())
    entry = _entry(page)
    win = HookWindow()
    asyncio.run(app._wire_focus_hook(entry, cast_any(win)))
    return app, win


def cast_any(win: HookWindow) -> Any:
    """Typing shim — hook methods take lumiview's Window."""
    return win


def _fire(win: HookWindow, event: type[WindowBaseEvent]) -> None:
    asyncio.run(win.hooks[event][0](event()))


class TestFocusBlur:
    def test_on_focus_fires(self):
        calls: list[str] = []
        page = Page().on_focus(lambda: calls.append("focused"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowEvent.FocusedEvent)
        assert calls == ["focused"]

    def test_on_focus_handlers_stack(self):
        calls: list[str] = []
        page = Page()
        page.on_focus(lambda: calls.append("first"))
        page.on_focus(lambda: calls.append("second"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowEvent.FocusedEvent)
        assert calls == ["first", "second"]

    def test_on_blur_fires(self):
        calls: list[str] = []
        page = Page().on_blur(lambda: calls.append("unfocused"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowEvent.UnfocusedEvent)
        assert calls == ["unfocused"]

    def test_async_handler_awaited(self):
        calls: list[str] = []
        page = Page()

        async def handler() -> None:
            await asyncio.sleep(0)
            calls.append("async")

        page.on_focus(handler)

        _win = _wire_focus(page)[1]

        _fire(_win, WindowEvent.FocusedEvent)
        assert calls == ["async"]

    def test_exception_in_handler_isolated(self):
        calls: list[str] = []
        page = Page()
        page.on_focus(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        page.on_focus(lambda: calls.append("survivor"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowEvent.FocusedEvent)  # must not raise
        assert calls == ["survivor"]

    def test_chainable(self):
        page = Page()
        assert page.on_focus(lambda: None) is page
        assert page.on_blur(lambda: None) is page

    def test_no_handlers_wires_nothing(self):
        page = Page()

        _app, win = _wire_focus(page)

        assert not win.hooks  # no handlers → no registrations


def _fire_event(app: NeonApplication, key: str, event_type: str, value: Any = None, **extra: Any) -> None:
    """Dispatch a DOM event into the bridge (mirrors the JS invoke)."""
    asyncio.run(app._entries[0].neony._on_event(cast(Any, None), key=key, event_type=event_type, value=value, **extra))


class TestShortcuts:
    """Page.on_shortcut — window-level keybindings via bubbling keydown."""

    @staticmethod
    def _make(*combos: str) -> tuple[NeonApplication, str, list[str]]:
        """Page with each combo registered; returns (app, root_key, calls)."""
        from neony.dom import Div

        calls: list[str] = []
        page = Page()
        for i, combo in enumerate(combos):
            page.on_shortcut(combo, lambda name=f"c{i}": calls.append(name))
        inner = Div(key="inner-child")
        page.add(inner)  # keydown from a child exercises the bubble path
        app = NeonApplication(Config())
        entry = _entry(page)
        app._entries.append(entry)
        app._collect_handlers(entry.neony, entry.tree, 0)
        return app, entry.tree.key, calls

    def test_fires_on_matching_combo(self):
        app, root, calls = self._make("Ctrl+K")

        _fire_event(app, root, "keydown", "k", ctrl_key=True)

        assert calls == ["c0"]

    def test_does_not_fire_for_key_alone(self):
        app, root, calls = self._make("Ctrl+K")

        _fire_event(app, root, "keydown", "k")

        assert calls == []

    def test_does_not_fire_with_extra_modifier(self):
        app, root, calls = self._make("Ctrl+K")

        _fire_event(app, root, "keydown", "K", ctrl_key=True, shift_key=True)

        assert calls == []

    def test_case_insensitive_key(self):
        app, root, calls = self._make("Ctrl+Shift+K")

        _fire_event(app, root, "keydown", "K", ctrl_key=True, shift_key=True)

        assert calls == ["c0"]

    def test_bubbles_from_child_element(self):
        """Typing in an inner element (no keydown handler of its own)
        reaches the page root via opt-in bubbling."""
        app, _root, calls = self._make("Ctrl+K")

        _fire_event(app, "inner-child", "keydown", "k", ctrl_key=True)

        assert calls == ["c0"]

    def test_multiple_shortcuts_independent(self):
        app, root, calls = self._make("Ctrl+K", "Ctrl+Shift+S")

        _fire_event(app, root, "keydown", "s", ctrl_key=True, shift_key=True)

        assert calls == ["c1"]

    def test_per_platform_dict_picks_current_platform(self):
        calls: list[str] = []
        page = Page()
        page.on_shortcut({"linux": "Ctrl+L", "default": "Ctrl+K"}, lambda: calls.append("pressed"))
        app = NeonApplication(Config())
        entry = _entry(page)
        app._entries.append(entry)
        app._collect_handlers(entry.neony, entry.tree, 0)

        _fire_event(app, entry.tree.key, "keydown", "l", ctrl_key=True)
        _fire_event(app, entry.tree.key, "keydown", "k", ctrl_key=True)
        # Exactly one combo is bound — the platform-specific one when
        # this platform has an entry, else the "default" fallback.
        assert calls == ["pressed"]

    def test_async_handler_awaited(self):
        import asyncio

        calls: list[str] = []
        page = Page()

        async def handler() -> None:
            await asyncio.sleep(0)
            calls.append("async")

        page.on_shortcut("Ctrl+S", handler)
        app = NeonApplication(Config())
        entry = _entry(page)
        app._entries.append(entry)
        app._collect_handlers(entry.neony, entry.tree, 0)

        _fire_event(app, entry.tree.key, "keydown", "s", ctrl_key=True)

        assert calls == ["async"]

    def test_chainable(self):
        page = Page()
        assert page.on_shortcut("Ctrl+K", lambda: None) is page

    def test_unknown_modifier_raises(self):
        with pytest.raises(ValueError, match="unknown modifier"):
            Page().on_shortcut("Ctr+K", lambda: None)

    def test_missing_modifier_raises(self):
        with pytest.raises(ValueError, match="MODIFIER\\+KEY"):
            Page().on_shortcut("K", lambda: None)

    def test_dict_missing_current_platform_and_default_raises(self):
        with pytest.raises(ValueError, match="'default'"):
            Page().on_shortcut({"darwin": "Meta+K"}, lambda: None)


class TestPageKeyEvents:
    """Page.on_keydown / on_keyup — window-level key listeners that fire
    wherever keys land, even while an input handles its own events."""

    @staticmethod
    def _make() -> tuple[NeonApplication, str, list[str]]:
        from neony.dom import Div

        events: list[str] = []
        page = Page()
        page.on_keydown(lambda e: events.append(f"down:{e.value}"))
        page.on_keyup(lambda e: events.append(f"up:{e.value}"))
        page.add(Div(key="inner-child"))
        app = NeonApplication(Config())
        entry = _entry(page)
        app._entries.append(entry)
        app._collect_handlers(entry.neony, entry.tree, 0)
        return app, entry.tree.key, events

    def test_fires_for_keys_on_the_bare_page(self):
        app, root, events = self._make()

        _fire_event(app, root, "keydown", "x")

        assert events == ["down:x"]

    def test_fires_for_keys_typed_in_an_input(self):
        """A keydown targeting an inner element bubbles to the root —
        window-level listeners see it even though the input handles it."""
        app, _root, events = self._make()

        _fire_event(app, "inner-child", "keydown", "x", ctrl_key=True)

        assert events == ["down:x"]

    def test_keyup_dispatched(self):
        app, root, events = self._make()

        _fire_event(app, root, "keyup", "x")

        assert events == ["up:x"]

    def test_async_handler_awaited(self):
        import asyncio

        from neony.dom import Div

        calls: list[str] = []
        page = Page()

        async def on_key(e) -> None:
            await asyncio.sleep(0)
            calls.append("done")

        page.on_keydown(on_key)
        page.add(Div(key="inner-child"))
        app = NeonApplication(Config())
        entry = _entry(page)
        app._entries.append(entry)
        app._collect_handlers(entry.neony, entry.tree, 0)

        _fire_event(app, entry.tree.key, "keydown", "x")

        assert calls == ["done"]

    def test_chainable(self):
        page = Page()
        result = page.on_keydown(lambda e: None).on_keyup(lambda e: None)
        assert result is page


def _wire_policies(
    page: Page | None,
) -> FakeWindow:
    """Wire (default + page) policies onto a fake window."""
    app = NeonApplication(Config())
    win = FakeWindow()
    # _wire_navigation_policy needs an _Entry; build one around the page
    # (or a bare tree when no Page is involved).
    if page is not None:
        entry = _entry(page)
    else:
        from neony.dom import Div

        entry = _Entry(Neony(name="neony"), Div(), None)
    asyncio.run(app._wire_navigation_policy(entry, cast_any(win)))
    return win


def _policy(win: FakeWindow, event_cls) -> Callable[[Any], None]:
    """The registered policy handler for *event_cls* (dev3: policies are
    plain event handlers; the decision is ``event.prevent()``)."""
    return win.hooks[event_cls][0]


def _run(handler, event_cls, **fields):
    """Build *event_cls(**fields)*, run the handler, return the event."""
    event = event_cls(**fields)
    result = handler(event)
    if asyncio.iscoroutine(result):
        asyncio.run(result)
    return event


class TestNavigationPolicies:
    def test_defaults_block_everything_without_page(self):
        """No Page → safe defaults: block navigation, deny windows, cancel downloads."""
        win = _wire_policies(None)

        nav = _run(
            _policy(win, WindowEvent.NavigationRequestedEvent),
            WindowEvent.NavigationRequestedEvent,
            url="https://evil.example",
        )
        assert nav.prevented is True
        nw = _run(
            _policy(win, WindowEvent.NewWindowRequestedEvent),
            WindowEvent.NewWindowRequestedEvent,
            url="https://evil.example",
        )
        assert nw.prevented is True
        dl = _run(
            _policy(win, WindowEvent.DownloadStartedEvent),
            WindowEvent.DownloadStartedEvent,
            url="https://evil.example",
            suggested_path="/tmp/a.bin",
        )
        assert dl.prevented is True

    def test_defaults_block_with_page_but_no_handlers(self):
        win = _wire_policies(Page())

        nav = _run(
            _policy(win, WindowEvent.NavigationRequestedEvent),
            WindowEvent.NavigationRequestedEvent,
            url="https://x.example",
        )
        assert nav.prevented is True
        dl = _run(
            _policy(win, WindowEvent.DownloadStartedEvent),
            WindowEvent.DownloadStartedEvent,
            url="https://x.example",
            suggested_path="/tmp/x",
        )
        assert dl.prevented is True

    def test_on_navigation_replaces_and_fires(self):
        """Last handler wins — policy is a single decision."""
        page = Page().on_navigation(lambda url: url.startswith("https://app.example"))

        win = _wire_policies(page)

        allowed = _run(
            _policy(win, WindowEvent.NavigationRequestedEvent),
            WindowEvent.NavigationRequestedEvent,
            url="https://app.example/page",
        )
        assert allowed.prevented is False
        blocked = _run(
            _policy(win, WindowEvent.NavigationRequestedEvent),
            WindowEvent.NavigationRequestedEvent,
            url="https://evil.example",
        )
        assert blocked.prevented is True

    def test_on_navigation_second_call_replaces(self):
        page = Page()
        page.on_navigation(lambda url: True)
        page.on_navigation(lambda url: False)  # replaces

        win = _wire_policies(page)

        event = _run(
            _policy(win, WindowEvent.NavigationRequestedEvent),
            WindowEvent.NavigationRequestedEvent,
            url="https://x.example",
        )
        assert event.prevented is True

    def test_on_new_window_policy(self):
        page = Page().on_new_window(lambda url: "allow" if url.startswith("https://app.example") else "deny")

        win = _wire_policies(page)

        allowed = _run(
            _policy(win, WindowEvent.NewWindowRequestedEvent),
            WindowEvent.NewWindowRequestedEvent,
            url="https://app.example",
        )
        assert allowed.prevented is False  # system-browser open (native default)
        denied = _run(
            _policy(win, WindowEvent.NewWindowRequestedEvent),
            WindowEvent.NewWindowRequestedEvent,
            url="https://evil.example",
        )
        assert denied.prevented is True

    def test_on_download_started_policy(self):
        page = Page().on_download_started(lambda url, path: "/custom/" if "report" in url else False)

        win = _wire_policies(page)

        redirected = _run(
            _policy(win, WindowEvent.DownloadStartedEvent),
            WindowEvent.DownloadStartedEvent,
            url="https://x/report.pdf",
            suggested_path="/tmp/x",
        )
        assert redirected._save_path == "/custom/"
        cancelled = _run(
            _policy(win, WindowEvent.DownloadStartedEvent),
            WindowEvent.DownloadStartedEvent,
            url="https://x/song.mp3",
            suggested_path="/tmp/x",
        )
        assert cancelled.prevented is True

    def test_on_download_completed_stacks(self):
        """Notification semantics — handlers stack, all fire; async
        handlers are awaited (event handlers run on the asyncio loop)."""
        calls: list[tuple] = []
        page = Page()
        page.on_download_completed(lambda url, path, ok: calls.append(("a", url, ok)))
        page.on_download_completed(lambda url, path, ok: calls.append(("b", path)))

        win = _wire_policies(page)

        handler = _policy(win, WindowEvent.DownloadCompletedEvent)
        _run(
            handler,
            WindowEvent.DownloadCompletedEvent,
            url="https://x/file.bin",
            saved_path="/tmp/file.bin",
            success=True,
        )
        assert calls == [("a", "https://x/file.bin", True), ("b", "/tmp/file.bin")]

    def test_on_download_completed_exception_isolated(self):
        calls: list[str] = []
        page = Page()
        page.on_download_completed(lambda url, path, ok: (_ for _ in ()).throw(RuntimeError("boom")))
        page.on_download_completed(lambda url, path, ok: calls.append("survivor"))

        win = _wire_policies(page)

        handler = _policy(win, WindowEvent.DownloadCompletedEvent)
        _run(handler, WindowEvent.DownloadCompletedEvent, url="u", saved_path="p", success=True)  # must not raise
        assert calls == ["survivor"]

    def test_policy_methods_chainable(self):
        page = Page()
        assert page.on_navigation(lambda url: True) is page
        assert page.on_new_window(lambda url: "allow") is page
        assert page.on_download_started(lambda url, path: True) is page
        assert page.on_download_completed(lambda url, path, ok: None) is page
