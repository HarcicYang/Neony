"""``NeonApplication`` window-state methods — show / hide / focus /
set_bounds, dispatched through the same ``_require_window`` →
``call_on_main`` path as every other window-control method.

``set_bounds`` positions the window on screen via lumiview's
``set_outer_position`` (its ``set_bounds`` only wraps the webview-child
bounds) and delegates sizing to ``set_size``.
"""

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
        result = fn(*args)
        if asyncio.iscoroutine(result):
            await result
        return result


class FakeWindow:
    """Fake lumiview Window recording window-state calls."""

    def __init__(self) -> None:
        self.shown = 0
        self.hidden = 0
        self.focused = 0
        self.sizes: list[tuple[float, float]] = []
        self.positions: list[tuple[float, float]] = []

    def show(self) -> None:
        self.shown += 1

    def hide(self) -> None:
        self.hidden += 1

    def focus(self) -> None:
        self.focused += 1

    def set_size(self, width: float, height: float) -> None:
        self.sizes.append((width, height))

    def set_outer_position(self, x: float, y: float) -> None:
        self.positions.append((x, y))


def _app_with_window(window_index: int = 1) -> NeonApplication:
    """NeonApplication with *window_index* fake windows; App.get() faked."""
    app = NeonApplication(Config())
    for _ in range(window_index):
        entry = _Entry(Neony(name="neony"), Div())
        entry.window = cast(Any, FakeWindow())
        app._entries.append(entry)
    return app


def _run(app: NeonApplication, monkeypatch: pytest.MonkeyPatch, method: str, *args) -> list[FakeWindow]:
    fake = FakeLumiApp()
    monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))
    asyncio.run(getattr(app, method)(*args))
    return [cast_any(e.window) for e in app._entries]


def cast_any(win: object) -> FakeWindow:
    """Typing shim — _Entry.window is typed as lumiview's Window."""
    return cast(FakeWindow, win)


class TestWindowState:
    def test_show_dispatches(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        wins = _run(app, monkeypatch, "show")

        assert wins[0].shown == 1
        assert wins[0].hidden == 0

    def test_hide_dispatches(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        wins = _run(app, monkeypatch, "hide")

        assert wins[0].hidden == 1

    def test_focus_dispatches(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        wins = _run(app, monkeypatch, "focus")

        assert wins[0].focused == 1

    def test_methods_target_window_index(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(2)

        wins = _run(app, monkeypatch, "hide", 1)

        assert wins[0].hidden == 0
        assert wins[1].hidden == 1

    def test_set_bounds_positions_and_resizes(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        wins = _run(app, monkeypatch, "set_bounds", 100.0, 200.0, 640.0, 480.0)

        assert wins[0].positions == [(100.0, 200.0)]
        assert wins[0].sizes == [(640.0, 480.0)]

    def test_set_bounds_targets_window_index(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(2)

        wins = _run(app, monkeypatch, "set_bounds", 10.0, 20.0, 300.0, 200.0, 1)

        assert wins[0].positions == []
        assert wins[0].sizes == []
        assert wins[1].positions == [(10.0, 20.0)]
        assert wins[1].sizes == [(300.0, 200.0)]

    def test_set_bounds_position_failure_does_not_block_resize(self, monkeypatch: pytest.MonkeyPatch):
        """A positioning failure (Wayland no-op / backend rejection) must
        never prevent the resize half of set_bounds from applying."""
        app = _app_with_window(1)
        win = cast_any(app._entries[0].window)

        def broken_position(x: float, y: float) -> None:
            raise RuntimeError("positioning not supported here")

        win.set_outer_position = broken_position  # type: ignore[method-assign]

        wins = _run(app, monkeypatch, "set_bounds", 100.0, 200.0, 640.0, 480.0)

        assert wins[0].sizes == [(640.0, 480.0)]

    def test_show_requires_created_window(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = FakeLumiApp()
        monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))

        with pytest.raises(RuntimeError, match="window not created yet"):
            asyncio.run(app.show())

    def test_set_bounds_requires_created_window(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = FakeLumiApp()
        monkeypatch.setattr("neony.application.app.App.get", classmethod(lambda cls: fake))

        with pytest.raises(RuntimeError, match="window not created yet"):
            asyncio.run(app.set_bounds(0, 0, 100, 100))
