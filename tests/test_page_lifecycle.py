"""Window focus/blur events and navigation/download policies.

``page.on_focus`` / ``on_blur`` stack like ``on_close`` and are wired to
the native ``Focused`` / ``Unfocused`` window events.  The navigation /
new-window / download-started policies are single decisions (the last
handler wins) with safe defaults installed for every window; download-
completed is a stacking notification.
"""

import asyncio
from typing import Any, cast

import pytest
from lumiview import WindowHookEvent

from neony.application import Config, NeonApplication, Page
from neony.application.app import _Entry
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


class FakeLumiApp:
    """Minimal lumiview App stand-in: ``call_on_main`` runs the callable."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def call_on_main(self, fn, *args):
        result = fn(*args)
        if asyncio.iscoroutine(result):
            await result
        return result

    def on(self, event):
        def decorator(fn):
            return fn

        return decorator


class FakeWindow(HookWindow):
    """Fake lumiview Window with the policy setters recording handlers."""

    def __init__(self) -> None:
        super().__init__()
        self.policies: dict[str, Any] = {}

    def set_on_navigation(self, handler):
        self.policies["navigation"] = handler

    def set_on_new_window(self, handler):
        self.policies["new_window"] = handler

    def set_on_download_started(self, handler):
        self.policies["download_started"] = handler

    def set_on_download_completed(self, handler):
        self.policies["download_completed"] = handler


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


def _fire(win: HookWindow, event: WindowHookEvent) -> None:
    asyncio.run(win.hooks[event][0]())


class TestFocusBlur:
    def test_on_focus_fires(self):
        calls: list[str] = []
        page = Page().on_focus(lambda: calls.append("focused"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowHookEvent.Focused)
        assert calls == ["focused"]

    def test_on_focus_handlers_stack(self):
        calls: list[str] = []
        page = Page()
        page.on_focus(lambda: calls.append("first"))
        page.on_focus(lambda: calls.append("second"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowHookEvent.Focused)
        assert calls == ["first", "second"]

    def test_on_blur_fires(self):
        calls: list[str] = []
        page = Page().on_blur(lambda: calls.append("unfocused"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowHookEvent.Unfocused)
        assert calls == ["unfocused"]

    def test_async_handler_awaited(self):
        calls: list[str] = []
        page = Page()

        async def handler() -> None:
            await asyncio.sleep(0)
            calls.append("async")

        page.on_focus(handler)

        _win = _wire_focus(page)[1]

        _fire(_win, WindowHookEvent.Focused)
        assert calls == ["async"]

    def test_exception_in_handler_isolated(self):
        calls: list[str] = []
        page = Page()
        page.on_focus(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        page.on_focus(lambda: calls.append("survivor"))

        _win = _wire_focus(page)[1]

        _fire(_win, WindowHookEvent.Focused)  # must not raise
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


def _wire_policies(
    page: Page | None, monkeypatch: pytest.MonkeyPatch
) -> tuple[NeonApplication, FakeLumiApp, FakeWindow]:
    """Wire (default + page) policies onto a fake window/app."""
    app = NeonApplication(Config())
    win = FakeWindow()
    # _wire_navigation_policy needs an _Entry; build one around the page
    # (or a bare tree when no Page is involved).
    if page is not None:
        entry = _entry(page)
    else:
        from neony.dom import Div

        entry = _Entry(Neony(name="neony"), Div(), None)
    fake = FakeLumiApp()
    monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))
    asyncio.run(app._wire_navigation_policy(entry, cast_any(win)))
    return app, fake, win


class TestNavigationPolicies:
    def test_defaults_block_everything_without_page(self, monkeypatch: pytest.MonkeyPatch):
        """No Page → safe defaults: block navigation, deny windows, cancel downloads."""
        _app, _fake, win = _wire_policies(None, monkeypatch)

        assert win.policies["navigation"]("https://evil.example") is False
        assert win.policies["new_window"]("https://evil.example") == "deny"
        assert win.policies["download_started"]("https://evil.example", "/tmp/a.bin") is False

    def test_defaults_block_with_page_but_no_handlers(self, monkeypatch: pytest.MonkeyPatch):
        _app, _fake, win = _wire_policies(Page(), monkeypatch)

        assert win.policies["navigation"]("https://x.example") is False
        assert win.policies["new_window"]("https://x.example") == "deny"
        assert win.policies["download_started"]("https://x.example", "/tmp/x") is False

    def test_on_navigation_replaces_and_fires(self, monkeypatch: pytest.MonkeyPatch):
        """Last handler wins — policy is a single decision."""
        page = Page().on_navigation(lambda url: url.startswith("https://app.example"))

        _app, _fake, win = _wire_policies(page, monkeypatch)

        assert win.policies["navigation"]("https://app.example/page") is True
        assert win.policies["navigation"]("https://evil.example") is False

    def test_on_navigation_second_call_replaces(self, monkeypatch: pytest.MonkeyPatch):
        page = Page()
        page.on_navigation(lambda url: True)
        page.on_navigation(lambda url: False)  # replaces

        _app, _fake, win = _wire_policies(page, monkeypatch)

        assert win.policies["navigation"]("https://x.example") is False

    def test_on_new_window_policy(self, monkeypatch: pytest.MonkeyPatch):
        page = Page().on_new_window(lambda url: "allow" if url.startswith("https://app.example") else "deny")

        _app, _fake, win = _wire_policies(page, monkeypatch)

        assert win.policies["new_window"]("https://app.example") == "allow"
        assert win.policies["new_window"]("https://evil.example") == "deny"

    def test_on_download_started_policy(self, monkeypatch: pytest.MonkeyPatch):
        page = Page().on_download_started(lambda url, path: "/custom/" if "report" in url else False)

        _app, _fake, win = _wire_policies(page, monkeypatch)

        assert win.policies["download_started"]("https://x/report.pdf", "/tmp/x") == "/custom/"
        assert win.policies["download_started"]("https://x/song.mp3", "/tmp/x") is False

    def test_on_download_completed_stacks(self, monkeypatch: pytest.MonkeyPatch):
        """Notification semantics — handlers stack, all fire."""
        calls: list[tuple] = []
        page = Page()
        page.on_download_completed(lambda url, path, ok: calls.append(("a", url, ok)))
        page.on_download_completed(lambda url, path, ok: calls.append(("b", path)))

        _app, _fake, win = _wire_policies(page, monkeypatch)

        handler = win.policies["download_completed"]
        handler("https://x/file.bin", "/tmp/file.bin", True)  # sync (native callback)
        assert calls == [("a", "https://x/file.bin", True), ("b", "/tmp/file.bin")]

    def test_on_download_completed_exception_isolated(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[str] = []
        page = Page()
        page.on_download_completed(lambda url, path, ok: (_ for _ in ()).throw(RuntimeError("boom")))
        page.on_download_completed(lambda url, path, ok: calls.append("survivor"))

        _app, _fake, win = _wire_policies(page, monkeypatch)

        handler = win.policies["download_completed"]
        handler("u", "p", True)  # must not raise
        assert calls == ["survivor"]

    def test_policy_methods_chainable(self):
        page = Page()
        assert page.on_navigation(lambda url: True) is page
        assert page.on_new_window(lambda url: "allow") is page
        assert page.on_download_started(lambda url, path: True) is page
        assert page.on_download_completed(lambda url, path, ok: None) is page
