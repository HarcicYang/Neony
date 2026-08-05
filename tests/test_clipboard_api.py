"""``NeonApplication.clipboard_write`` / ``clipboard_read`` — clipboard
access via the pyclip backend.

Both methods lazy-load pyclip on first use (``_load_pyclip``) and run
the synchronous ``pyclip.copy`` / ``pyclip.paste`` calls in a worker
thread, so the event loop never blocks on the clipboard.  The tests
fake the clipboard module and never touch the real system clipboard.
"""

import asyncio
import sys
from typing import Any

import pytest

from neony.application import Config, NeonApplication
from neony.application import app as app_module


class _FakeClip:
    """Stand-in for the pyclip module: records calls, serves canned
    results, and can be told to raise on copy/paste."""

    def __init__(self, paste_result: Any = b"") -> None:
        self.copy_calls: list[str] = []
        self.paste_result: Any = paste_result
        self.copy_error: BaseException | None = None
        self.paste_error: BaseException | None = None

    def copy(self, text: str) -> None:
        if self.copy_error is not None:
            raise self.copy_error
        self.copy_calls.append(text)

    def paste(self) -> Any:
        if self.paste_error is not None:
            raise self.paste_error
        return self.paste_result


def _app(clip: _FakeClip | None = None) -> NeonApplication:
    app = NeonApplication(Config())
    if clip is not None:
        app._clip = clip
    return app


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


class TestClipboardBackend:
    """clipboard_write / clipboard_read delegate to pyclip in a worker
    thread — the webview is never involved."""

    def test_write_calls_pyclip_copy_verbatim(self):
        # Text goes to pyclip unchanged: no JS escaping, no injection.
        text = 'say "hi"\n\x00'
        clip = _FakeClip()

        asyncio.run(_app(clip).clipboard_write(text))

        assert clip.copy_calls == [text]

    def test_read_returns_pyclip_paste_result(self):
        clip = _FakeClip(paste_result="hello")

        result = asyncio.run(_app(clip).clipboard_read())

        assert result == "hello"

    def test_read_passes_bytes_through(self):
        # paste may return bytes on some platforms — passed through as-is.
        clip = _FakeClip(paste_result=b"raw bytes")

        result = asyncio.run(_app(clip).clipboard_read())

        assert result == b"raw bytes"

    def test_copy_error_propagates(self):
        clip = _FakeClip()
        clip.copy_error = RuntimeError("clipboard is busy")

        with pytest.raises(RuntimeError, match="clipboard is busy"):
            asyncio.run(_app(clip).clipboard_write("x"))

    def test_paste_error_propagates(self):
        clip = _FakeClip()
        clip.paste_error = OSError("no clipboard available")

        with pytest.raises(OSError, match="no clipboard"):
            asyncio.run(_app(clip).clipboard_read())


class TestLazyPyclipLoad:
    """_clip starts None; the pyclip module is imported on first use and
    cached for subsequent calls."""

    def test_load_pyclip_imports_and_caches(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        assert app._clip is None

        fake = _FakeClip()
        monkeypatch.setitem(sys.modules, "pyclip", fake)

        app._load_pyclip()

        assert app._clip is fake

    def test_first_use_loads_once_and_caches(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = _FakeClip()
        loads: list[int] = []

        def fake_load(self: NeonApplication) -> None:
            loads.append(1)
            self._clip = fake

        monkeypatch.setattr(app_module.NeonApplication, "_load_pyclip", fake_load)

        asyncio.run(app.clipboard_write("first"))
        asyncio.run(app.clipboard_write("second"))

        # Loaded exactly once — the second call found _clip already set.
        assert loads == [1]
        assert fake.copy_calls == ["first", "second"]

    def test_read_lazy_loads_too(self, monkeypatch: pytest.MonkeyPatch):
        app = NeonApplication(Config())
        fake = _FakeClip(paste_result="hi")
        monkeypatch.setattr(app_module.NeonApplication, "_load_pyclip", lambda self: setattr(self, "_clip", fake))

        result = asyncio.run(app.clipboard_read())

        assert result == "hi"
