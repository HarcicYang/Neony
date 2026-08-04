"""``NeonApplication.clipboard_write`` / ``clipboard_read`` — thin
``eval_js`` wrappers around ``navigator.clipboard``."""

import asyncio
from typing import Any, cast

import pytest

from neony.application import Config, NeonApplication
from neony.application.app import _Entry
from neony.dom import Div
from neony.dom.bridge import Neony


class FakeWindow:
    """Fake lumiview Window recording eval_js calls and returning canned
    results for clipboard_read."""

    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.read_result = ""

    async def eval_js(self, script: str) -> str:
        self.scripts.append(script)
        if "readText" in script:
            return self.read_result
        return ""


def _app_with_window(window_index: int = 1) -> NeonApplication:
    app = NeonApplication(Config())
    for _ in range(window_index):
        entry = _Entry(Neony(name="neony"), Div())
        entry.window = cast(Any, FakeWindow())
        app._entries.append(entry)
    return app


def _run(app: NeonApplication, monkeypatch: pytest.MonkeyPatch, method: str, *args) -> tuple[list[FakeWindow], Any]:
    monkeypatch.setattr(
        "neony.application.app.App.get",
        classmethod(lambda cls: type("Fake", (), {"call_on_main": None})),
    )
    result = asyncio.run(getattr(app, method)(*args))
    return [cast_any(e.window) for e in app._entries], result


def cast_any(win: object) -> FakeWindow:
    return cast(FakeWindow, win)


class TestClipboardAPI:
    def test_write_escapes_text_into_writeText(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        wins, _result = _run(app, monkeypatch, "clipboard_write", 'say "hi"\n\x00')

        assert wins[0].scripts == ['navigator.clipboard.writeText("say \\"hi\\"\\n\\u0000")']

    def test_read_returns_clipboard_text(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)
        cast_any(app._entries[0].window).read_result = "hello"

        wins, result = _run(app, monkeypatch, "clipboard_read")

        assert wins[0].scripts == ["navigator.clipboard.readText()"]
        assert result == "hello"

    def test_read_targets_window_index(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(2)
        cast_any(app._entries[1].window).read_result = "second"

        wins, result = _run(app, monkeypatch, "clipboard_read", 1)

        assert wins[0].scripts == []
        assert wins[1].scripts == ["navigator.clipboard.readText()"]
        assert result == "second"

    def test_write_requires_created_window(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        monkeypatch.setattr(
            "neony.application.app.App.get",
            classmethod(lambda cls: type("Fake", (), {"call_on_main": None})),
        )

        with pytest.raises(RuntimeError, match="window not created yet"):
            asyncio.run(app.clipboard_write("x"))
