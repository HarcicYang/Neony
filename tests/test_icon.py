"""``NeonApplication.set_icon()`` — runtime window icon swap, dispatched
through the same ``_require_window`` → ``call_on_main`` path as every
other window-control method."""

import asyncio
from typing import Any, cast

import pytest

from neony.application import Config, NeonApplication
from neony.application._helpers import _Entry
from neony.dom import Div
from neony.dom.bridge import Neony


class FakeLumiApp:
    """Minimal lumiview App: ``call_on_main`` records and runs the callable."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def call_on_main(self, fn, *args):
        self.calls.append((fn, args))
        return fn(*args)


class FakeWindow:
    """Fake lumiview Window recording the icon it receives."""

    def __init__(self) -> None:
        self.icon: object = None

    def set_icon(self, icon: object) -> None:
        self.icon = icon


def _app_with_window(window_index: int = 1):
    """NeonApplication with *window_index* fake windows; App.get() faked."""
    app = NeonApplication(Config())
    for _ in range(window_index):
        entry = _Entry(Neony(name="neony"), Div())
        entry.window = cast(Any, FakeWindow())
        app._entries.append(entry)
    return app


def _run(app: NeonApplication, monkeypatch: pytest.MonkeyPatch, *args) -> tuple[FakeLumiApp, list[FakeWindow]]:
    fake = FakeLumiApp()
    monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))
    asyncio.run(app.set_icon(*args))
    return fake, [cast_any(e.window) for e in app._entries]


def cast_any(win: object) -> FakeWindow:
    """Typing shim — _Entry.window is typed as lumiview's Window."""
    return cast(FakeWindow, win)


class TestSetIcon:
    def test_set_icon_dispatches_to_window_0(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        _fake, wins = _run(app, monkeypatch, "icon.png")

        assert wins[0].icon == "icon.png"

    def test_set_icon_targets_window_index(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(2)

        _fake, wins = _run(app, monkeypatch, (b"\x00\x00\x00\x00" * 16, 4, 4), 1)

        assert wins[0].icon is None
        assert wins[1].icon == (b"\x00\x00\x00\x00" * 16, 4, 4)

    def test_set_icon_requires_created_window(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = FakeLumiApp()
        monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))

        with pytest.raises(RuntimeError, match="window not created yet"):
            asyncio.run(app.set_icon("icon.png"))
