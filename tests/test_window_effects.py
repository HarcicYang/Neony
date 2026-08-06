"""Automatic platform materials for transparent windows.

``WindowConfig.transparent=True`` gets the platform's native frosted
effect applied at window creation: Acrylic on Windows, Blur on macOS,
and on Linux a compositor blur via the Wayland
``ext-background-effect-v1`` protocol (KWin).  Failures are logged,
never fatal.
"""

import asyncio
from typing import Any, cast

import pytest
from lumiview import WindowEffect

from neony.application import Config, NeonApplication, WindowConfig
from neony.application import app as app_module
from neony.application._helpers import _Entry
from neony.dom import Div
from neony.dom.bridge import Neony


class FakeLumiApp:
    """Runs the callable instead of hopping to a real event loop."""

    async def call_on_main(self, fn, *args):
        result = fn(*args)
        if asyncio.iscoroutine(result):
            await result
        return result


class FakeWindow:
    """Records the applied effect."""

    def __init__(self) -> None:
        self.effects: list[tuple[WindowEffect, tuple | None]] = []

    def apply_effect(self, effect: WindowEffect, color: tuple | None = None) -> None:
        self.effects.append((effect, color))


def _apply(monkeypatch: pytest.MonkeyPatch, platform: str, *, transparent: bool = True) -> FakeWindow:
    """Build an app with a fake window and run the effect application."""
    app = NeonApplication(Config(window=WindowConfig(transparent=transparent)))
    entry = _Entry(Neony(name="neony"), Div())
    entry.window = cast(Any, FakeWindow())
    app._entries.append(entry)
    monkeypatch.setattr(app_module.sys, "platform", platform)
    monkeypatch.setattr(
        "neony.application.app.App.get",
        classmethod(lambda cls: FakeLumiApp()),
    )
    win = cast(Any, entry.window)
    asyncio.run(app._apply_transparent_effect(win))
    return cast(FakeWindow, win)


class TestTransparentEffects:
    def test_windows_transparent_applies_acrylic(self, monkeypatch: pytest.MonkeyPatch):
        win = _apply(monkeypatch, "win32")
        assert win.effects == [(WindowEffect.Acrylic, None)]

    def test_macos_transparent_applies_blur(self, monkeypatch: pytest.MonkeyPatch):
        win = _apply(monkeypatch, "darwin")
        assert win.effects == [(WindowEffect.Blur, None)]

    def test_linux_transparent_requests_wayland_blur(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[object] = []
        monkeypatch.setattr(
            "neony.application._linux_blur.apply_wayland_blur",
            lambda window: calls.append(window) or True,
        )

        win = _apply(monkeypatch, "linux")

        # The compositor blur path is used; no lumiview effect is applied.
        assert calls == [win]
        assert win.effects == []

    def test_linux_blur_failure_is_not_fatal(self, monkeypatch: pytest.MonkeyPatch):
        def boom(_window: object) -> bool:
            raise RuntimeError("no compositor")

        monkeypatch.setattr("neony.application._linux_blur.apply_wayland_blur", boom)

        # Must not raise — the window keeps working without the blur.
        win = _apply(monkeypatch, "linux")
        assert win.effects == []

    def test_opaque_window_applies_nothing(self, monkeypatch: pytest.MonkeyPatch):
        win = _apply(monkeypatch, "win32", transparent=False)
        assert win.effects == []

    def test_effect_failure_is_not_fatal(self, monkeypatch: pytest.MonkeyPatch):
        class BrokenWindow:
            def apply_effect(self, effect, color=None) -> None:
                raise RuntimeError("material not supported")

        app = NeonApplication(Config(window=WindowConfig(transparent=True)))
        entry = _Entry(Neony(name="neony"), Div())
        entry.window = cast(Any, BrokenWindow())
        app._entries.append(entry)
        monkeypatch.setattr(app_module.sys, "platform", "win32")
        monkeypatch.setattr(
            "neony.application.app.App.get",
            classmethod(lambda cls: FakeLumiApp()),
        )

        # Must not raise — the window keeps working without the effect.
        asyncio.run(app._apply_transparent_effect(cast(Any, BrokenWindow())))


def test_platform_map_has_no_other_entries() -> None:
    # Only the two platforms with native materials — a third entry would
    # silently change behaviour for some other platform.
    assert set(app_module._TRANSPARENT_EFFECTS) == {"win32", "darwin"}
