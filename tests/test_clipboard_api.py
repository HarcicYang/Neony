"""``NeonApplication.clipboard_write`` / ``clipboard_read`` — clipboard
access that works across backends.

Write uses the synchronous ``execCommand('copy')`` path (hidden
textarea) plus a fire-and-forget ``navigator.clipboard.writeText()``;
read runs the async read in-page into a global and polls it from
Python, since the webview bridge may not await JS promises.
"""

import asyncio
from typing import Any, cast

import pytest

from neony.application import Config, NeonApplication
from neony.application.app import _Entry
from neony.dom import Div
from neony.dom.bridge import Neony


class FakeWindow:
    """Fake lumiview Window: records eval_js scripts and serves canned
    responses — the poll script returns the next queue item ('' while
    the async read hasn't landed); ``err_result`` simulates a bridge
    returning a failure."""

    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.poll_queue: list[str] = []
        self.err_result: str | None = None

    async def eval_js(self, script: str) -> str:
        self.scripts.append(script)
        if self.err_result is not None:
            return self.err_result
        # Only the short poll script hits the queue — the starter script
        # (which also mentions the global) returns 'started'.
        if script == "window.__neony_clip_read || ''":
            return self.poll_queue.pop(0) if self.poll_queue else ""
        if "execCommand" in script:
            return "ok"
        return "started"


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


class TestJsResultValue:
    """eval_js results arrive JSON-encoded (WebKitGTK: '"pong"' with
    quotes and ``\\u0001``-style escapes) — _js_result_value decodes them."""

    @staticmethod
    def _decode(raw: str) -> str:
        from neony.application.app import _js_result_value

        return _js_result_value(raw)

    def test_quoted_string_decoded(self):
        assert self._decode('"hello"') == "hello"

    def test_escaped_separator_survives(self):
        # The \x01 separator round-trips as \\u0001 inside the JSON string.
        assert self._decode('"OK\\u0001hello"') == "OK\x01hello"

    def test_error_payload_decoded(self):
        assert self._decode('"ERR\\u0001clipboard API unavailable"') == "ERR\x01clipboard API unavailable"

    def test_raw_string_passes_through(self):
        assert self._decode("pong") == "pong"

    def test_empty_result(self):
        assert self._decode('""') == ""


class TestClipboardAPI:
    def test_write_uses_sync_execcommand_path(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)

        _run(app, monkeypatch, "clipboard_write", 'say "hi"\n\x00')

        script = cast_any(app._entries[0].window).scripts[0]
        # The text is JSON-escaped into both the writeText attempt and
        # the textarea; the synchronous execCommand('copy') decides.
        assert "execCommand('copy')" in script
        assert '"say \\"hi\\"\\n\\u0000"' in script
        assert "navigator.clipboard.writeText" in script

    def test_write_raises_on_rejected_copy(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)
        # Simulate the bridge returning the execCommand result 'ERR:…'
        cast_any(app._entries[0].window).err_result = "ERR:execCommand copy rejected"

        with pytest.raises(RuntimeError, match="clipboard_write failed"):
            asyncio.run(app.clipboard_write("x"))

    def test_read_polls_the_inpage_result(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)
        win = cast_any(app._entries[0].window)
        # First poll: the async read hasn't landed yet (''); second: OK.
        win.poll_queue = ["", "OK\x01hello"]

        _wins, result = _run(app, monkeypatch, "clipboard_read")

        assert result == "hello"
        assert "readText" in win.scripts[0]

    def test_read_raises_on_backend_error(self, monkeypatch: pytest.MonkeyPatch):
        from neony.application import app as app_module

        app = _app_with_window(1)
        cast_any(app._entries[0].window).poll_queue = ["ERR\x01NotAllowedError"]
        # The Linux fallback must not mask the error in this test.
        monkeypatch.setattr(app_module, "_os_clipboard_read", lambda: None)

        with pytest.raises(RuntimeError, match="NotAllowedError"):
            asyncio.run(app.clipboard_read())

    def test_read_times_out_without_result(self, monkeypatch: pytest.MonkeyPatch):
        app = _app_with_window(1)
        # Every poll returns '' — the async read never lands.
        cast_any(app._entries[0].window).poll_queue = []

        async def no_sleep(_delay: float) -> None:
            return None

        monkeypatch.setattr("neony.application.app.asyncio.sleep", no_sleep)

        with pytest.raises(RuntimeError, match="timed out"):
            asyncio.run(app.clipboard_read())

    def test_write_requires_created_window(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        monkeypatch.setattr(
            "neony.application.app.App.get",
            classmethod(lambda cls: type("Fake", (), {"call_on_main": None})),
        )

        with pytest.raises(RuntimeError, match="window not created yet"):
            asyncio.run(app.clipboard_write("x"))


class TestOsClipboardFallback:
    """Linux fallback in clipboard_read: the OS clipboard tool
    (wl-paste on Wayland, xclip on X11) replaces the missing
    navigator.clipboard.readText on WebKitGTK."""

    def test_read_falls_back_to_os_tool(self, monkeypatch: pytest.MonkeyPatch):
        from neony.application import app as app_module

        app = _app_with_window(1)
        cast_any(app._entries[0].window).poll_queue = ["ERR\x01clipboard API unavailable"]
        monkeypatch.setattr(app_module, "_os_clipboard_read", lambda: "from-wl-paste")

        _wins, result = _run(app, monkeypatch, "clipboard_read")

        assert result == "from-wl-paste"

    def test_read_keeps_error_when_os_tool_missing(self, monkeypatch: pytest.MonkeyPatch):
        from neony.application import app as app_module

        app = _app_with_window(1)
        cast_any(app._entries[0].window).poll_queue = ["ERR\x01clipboard API unavailable"]
        monkeypatch.setattr(app_module, "_os_clipboard_read", lambda: None)

        with pytest.raises(RuntimeError, match="clipboard API unavailable"):
            _run(app, monkeypatch, "clipboard_read")

    def test_os_read_uses_wl_paste_on_wayland(self, monkeypatch: pytest.MonkeyPatch):
        from types import SimpleNamespace

        from neony.application import app as app_module

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setattr("shutil.which", lambda tool: f"/usr/bin/{tool}")
        calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs) -> SimpleNamespace:
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout=b"hello")

        monkeypatch.setattr("subprocess.run", fake_run)

        assert app_module._os_clipboard_read() == "hello"
        assert calls == [["wl-paste", "--no-newline"]]

    def test_os_read_uses_xclip_on_x11(self, monkeypatch: pytest.MonkeyPatch):
        from types import SimpleNamespace

        from neony.application import app as app_module

        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr("shutil.which", lambda tool: f"/usr/bin/{tool}")
        calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs) -> SimpleNamespace:
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout=b"hello")

        monkeypatch.setattr("subprocess.run", fake_run)

        assert app_module._os_clipboard_read() == "hello"
        assert calls == [["xclip", "-selection", "clipboard", "-o"]]

    def test_os_read_returns_none_when_tool_fails(self, monkeypatch: pytest.MonkeyPatch):
        import subprocess

        from neony.application import app as app_module

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.setattr("shutil.which", lambda tool: f"/usr/bin/{tool}")

        def fake_run(args: list[str], **kwargs):
            raise subprocess.TimeoutExpired(args, 2.0)

        monkeypatch.setattr("subprocess.run", fake_run)

        assert app_module._os_clipboard_read() is None
