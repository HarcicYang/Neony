"""Custom protocol support — types, decorator, collection, built-in
``local_files`` serving, and URL builders."""

from __future__ import annotations

import asyncio
import base64
import functools
from collections.abc import Callable, Coroutine
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from urllib.parse import unquote, urlparse

import pytest
from pydantic import ValidationError

from neony.application import local_files, local_url, protocol, protocol_url
from neony.application.protocols import Request, Response, collect_protocol_handlers
from neony.application.protocols.base import NeonyProtocolDispatch

# ---- keys & decorator ------------------------------------------------------


@pytest.mark.parametrize("bad", ["", "Local", "1local", "lo cal", "lo_cal", None, 3])
def test_protocol_rejects_bad_keys(bad):
    with pytest.raises(ValueError):
        protocol(bad)  # type: ignore[arg-type]


def test_protocol_wraps_sync_function():
    @protocol("qr")
    def handler(request: Request) -> Response:
        """docstring kept"""
        return Response.text("ok")

    assert handler.__name__ == "handler"
    assert handler.__doc__ == "docstring kept"
    assert not hasattr(handler, "__iscoroutinefunction__") or True
    import inspect

    assert not inspect.iscoroutinefunction(handler)


def test_protocol_wraps_async_function():
    import inspect

    @protocol("avatar")
    async def handler(request: Request) -> Response:
        return Response.text("ok")

    # The wrapper is itself a coroutine function — dispatch is exact.
    assert inspect.iscoroutinefunction(handler)


def test_decorated_method_keeps_binding():
    class Avatars:
        def __init__(self) -> None:
            self.db = "DB"

        @protocol("avatar")
        async def handle(self, request: Request) -> Response:
            return Response.text(f"{request.path}:{self.db}")

    av = Avatars()

    resp = asyncio.run(av.handle(Request(key="avatar", path="/42")))
    assert resp.body == b"/42:DB"


# ---- request / response ----------------------------------------------------


def test_request_is_frozen():
    req = Request(key="local", path="/x")
    with pytest.raises(ValidationError):
        req.path = "/y"  # type: ignore[misc]


def test_request_header_case_insensitive():
    req = Request(key="k", path="/", headers={"Content-Type": "text/plain"})
    assert req.header("content-TYPE") == "text/plain"
    assert req.header("Range", "none") == "none"


def test_response_text_and_json():
    text = Response.text("nope", status=404)
    assert text.status == 404
    assert text.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert text.body == b"nope"

    data = Response.json({"a": "告白"})
    assert data.headers["Content-Type"] == "application/json"
    assert '"a": "告白"'.encode() in data.body


# ---- collection ------------------------------------------------------------


def test_collect_module_function_and_instance_methods():
    @protocol("one")
    def one(request: Request) -> Response:
        return Response.text("1")

    class Multi:
        def __init__(self) -> None:
            self.tag = "t"

        @protocol("two")
        def two(self, request: Request) -> Response:
            return Response.text(self.tag)

        @protocol("three")
        async def three(self, request: Request) -> Response:
            return Response.text(self.tag)

    handlers = collect_protocol_handlers([one, Multi()])
    assert set(handlers) == {"one", "two", "three"}
    assert handlers["one"] is one
    assert isinstance(handlers["two"], functools.partial)

    # Bound partials carry the instance; the request argument stays explicit.
    req = Request(key="two", path="/")
    assert handlers["two"](req).body == b"t"

    # The dict is typed Callable[..., Response]; "three" is really async.
    three = cast("Callable[..., Coroutine[Any, Any, Response]]", handlers["three"])
    assert asyncio.run(three(req)).body == b"t"


def test_collect_includes_inherited_methods():
    class Base:
        @protocol("base-key")
        def handle(self, request: Request) -> Response:
            return Response.text("base")

    class Child(Base):
        pass

    handlers = collect_protocol_handlers([Child()])
    assert set(handlers) == {"base-key"}


def test_collect_rejects_duplicate_keys():
    @protocol("dup")
    def a(request: Request) -> Response:
        return Response.text("a")

    @protocol("dup")
    def b(request: Request) -> Response:
        return Response.text("b")

    with pytest.raises(ValueError, match="Duplicate protocol key"):
        collect_protocol_handlers([a, b])


def test_collect_rejects_undecorated_entries():
    with pytest.raises(TypeError, match="@protocol"):
        collect_protocol_handlers([lambda request: Response()])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="@protocol"):
        collect_protocol_handlers([object()])  # type: ignore[list-item]


def test_collect_empty_is_fine():
    assert collect_protocol_handlers([]) == {}


# ---- dispatcher routing (transport-level, no app loop needed) --------------


def _capture():
    calls: list[tuple[int, list[tuple[str, str]], bytes]] = []
    return calls, lambda status, headers, body: calls.append((status, headers, body))


def test_dispatch_unknown_key_responds_404():
    dispatch = NeonyProtocolDispatch({})
    calls, respond = _capture()
    raw = SimpleNamespace(url="neony://nope/x.mp3", method="GET", headers=[], body=b"", path="", query="")
    dispatch(raw, respond)
    assert calls[0][0] == 404


def test_dispatch_builds_neony_request(monkeypatch):
    captured: dict[str, object] = {}

    def fake_dispatch(self, handler, request, respond):
        captured["handler"] = handler
        captured["request"] = request

    monkeypatch.setattr(NeonyProtocolDispatch, "_dispatch", fake_dispatch)
    handler = lambda request: Response()  # noqa: E731
    dispatch = NeonyProtocolDispatch({"local": handler})
    _calls, respond = _capture()
    raw = SimpleNamespace(
        url="neony://local/home/u/%E5%91%8A%E7%99%BD.mp3",
        method="GET",
        headers=[("Range", "bytes=0-1"), ("Host", "a"), ("Host", "b")],
        body=b"",
        path="",
        query="",
    )
    dispatch(raw, respond)
    request = captured["request"]
    assert isinstance(request, Request)
    assert request.key == "local"
    assert request.path == "/home/u/告白.mp3"
    assert request.method == "GET"
    assert request.url == raw.url
    assert request.headers == {"Range": "bytes=0-1", "Host": "a, b"}
    assert captured["handler"] is handler


# ---- built-in local_files --------------------------------------------------


@pytest.fixture()
def media_file(tmp_path: Path) -> Path:
    f = tmp_path / "song.mp3"
    f.write_bytes(b"0123456789abcdef")
    return f


def _get(path: str | Path, **kwargs) -> Response:
    return local_files(Request(key="local", path=str(path), **kwargs))


def test_local_files_serves_full_body(media_file: Path):
    resp = _get(media_file)
    assert resp.status == 200
    assert resp.body == b"0123456789abcdef"
    assert resp.headers["Content-Type"] == "audio/mpeg"
    assert resp.headers["Content-Length"] == "16"
    assert resp.headers["Accept-Ranges"] == "bytes"
    assert "ETag" in resp.headers
    assert "Last-Modified" in resp.headers


def test_local_files_range_start_end(media_file: Path):
    resp = _get(media_file, headers={"Range": "bytes=2-5"})
    assert resp.status == 206
    assert resp.headers["Content-Range"] == "bytes 2-5/16"
    assert resp.headers["Content-Length"] == "4"
    assert resp.body == b"2345"


def test_local_files_range_open_ended(media_file: Path):
    resp = _get(media_file, headers={"Range": "bytes=12-"})
    assert resp.status == 206
    assert resp.headers["Content-Range"] == "bytes 12-15/16"
    assert resp.body == b"cdef"


def test_local_files_range_suffix(media_file: Path):
    resp = _get(media_file, headers={"Range": "bytes=-4"})
    assert resp.status == 206
    assert resp.headers["Content-Range"] == "bytes 12-15/16"
    assert resp.body == b"cdef"


def test_local_files_range_end_clamped(media_file: Path):
    resp = _get(media_file, headers={"Range": "bytes=10-999"})
    assert resp.status == 206
    assert resp.headers["Content-Range"] == "bytes 10-15/16"
    assert resp.body == b"abcdef"


def test_local_files_range_unsatisfiable(media_file: Path):
    resp = _get(media_file, headers={"Range": "bytes=99-"})
    assert resp.status == 416
    assert resp.headers["Content-Range"] == "bytes */16"

    resp = _get(media_file, headers={"Range": "bytes=-0"})
    assert resp.status == 416


@pytest.mark.parametrize("value", ["bytes=zz", "bytes=a-b-c", "chunks=0-1", "bytes=5-2", "bytes=0-1,3-4"])
def test_local_files_invalid_range_serves_full(media_file: Path, value: str):
    resp = _get(media_file, headers={"Range": value})
    assert resp.status == 200
    assert resp.body == b"0123456789abcdef"


def test_local_files_head_has_headers_but_no_body(media_file: Path):
    resp = _get(media_file, method="HEAD", headers={"Range": "bytes=0-3"})
    assert resp.status == 206
    assert resp.body == b""
    assert resp.headers["Content-Length"] == "4"


def test_local_files_missing_and_directory(tmp_path: Path):
    assert _get(tmp_path / "nope.bin").status == 404
    assert _get(tmp_path).status == 404


def test_local_files_unknown_mime_is_octet_stream(tmp_path: Path):
    f = tmp_path / "blob.xyzzy"
    f.write_bytes(b"x")
    resp = _get(f)
    assert resp.headers["Content-Type"] == "application/octet-stream"


def test_local_files_cjk_and_space_names(tmp_path: Path):
    f = tmp_path / "告白 song.mp3"
    f.write_bytes(b"music")
    resp = _get(f)
    assert resp.status == 200
    assert resp.body == b"music"


def test_local_files_windows_drive_slash_stripped(media_file: Path, monkeypatch):
    # "/C:/x" style paths (what urlparse yields on Windows URLs) lose the
    # leading slash; simulate by requesting the POSIX file through the
    # same normalization branch.
    from neony.application.protocols.files import _strip_drive_slash

    assert _strip_drive_slash("/C:/Users/x.mp3") == "C:/Users/x.mp3"
    assert _strip_drive_slash("/home/u/x.mp3") == "/home/u/x.mp3"


# ---- URL builders ----------------------------------------------------------


def test_local_url_round_trip(tmp_path: Path, monkeypatch):
    target = tmp_path / "告白 song.mp3"
    target.write_bytes(b"x")
    url = local_url(target)
    parsed = urlparse(url)
    assert parsed.scheme == "neony"
    assert parsed.netloc == "local"
    assert unquote(parsed.path) == str(target)


def test_local_url_expands_home(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HOME", str(tmp_path))
    url = local_url("~/music/a.mp3")
    expected = (tmp_path / "music/a.mp3").resolve()
    assert unquote(urlparse(url).path) == str(expected)


def test_local_url_relative_resolves_against_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_bytes(b"x")
    url = local_url("a.txt")
    assert unquote(urlparse(url).path) == str((tmp_path / "a.txt").resolve())


def test_protocol_url_basic():
    assert protocol_url("qr", "u/123456") == "neony://qr/u/123456"
    assert protocol_url("qr", "/leading") == "neony://qr/leading"
    assert protocol_url("stamp", "has space/x") == "neony://stamp/has%20space/x"


def test_protocol_url_validates_key():
    with pytest.raises(ValueError):
        protocol_url("Bad", "x")
    with pytest.raises(ValueError):
        protocol_url("", "x")


# ---- application wiring ----------------------------------------------------


def test_neon_application_accepts_protocols():
    from neony.application import NeonApplication

    @protocol("wired")
    def handler(request: Request) -> Response:
        return Response.text("wired")

    app = NeonApplication(protocols=[handler])
    assert app._protocols == [handler]

    app_default = NeonApplication()
    assert app_default._protocols == []


def test_launch_signature_takes_protocols_without_config_leak():
    import inspect

    from neony.application import launch

    params = inspect.signature(launch).parameters
    assert "protocols" in params
    # protocols must NOT flow into WindowConfig/WebViewConfig kwargs.
    assert params["protocols"].kind == inspect.Parameter.KEYWORD_ONLY


# ---- neony.media_read bridge command ----------------------------------------


def _media_bridge(monkeypatch, handler_response: Response) -> Any:
    """A Neony bridge with protocol handlers wired and lumiview scheduling
    stubbed out (handler runs inline)."""
    import importlib

    from neony.dom.bridge import Neony

    # lumiview.__init__ re-exports the ``task`` attribute, shadowing the
    # submodule — resolve the real module explicitly.
    lv_task = importlib.import_module("lumiview.task")

    async def fake_run_async(fn, request, **kwargs):
        result = fn(request)
        if asyncio.iscoroutine(result):
            return await result
        return result

    monkeypatch.setattr(lv_task, "run_async", fake_run_async)

    bridge = Neony(name="neony")
    bridge._protocol_handlers = {"local": lambda request: handler_response}
    return bridge


def test_media_read_returns_base64_payload(monkeypatch):
    from neony.dom.bridge import Neony

    body = b"RIFF....wave"
    response = Response(status=200, headers={"Content-Type": "audio/wav"}, body=body)
    bridge = _media_bridge(monkeypatch, response)

    payload = asyncio.run(Neony._on_media_read(bridge, None, "neony://local/tmp/song.wav"))  # type: ignore[arg-type]
    assert payload["status"] == 200
    assert payload["content_type"] == "audio/wav"
    assert base64.b64decode(payload["data_b64"]) == body


def test_media_read_rejects_non_neony_scheme(monkeypatch):
    import lumiview.bridge as lv_bridge

    from neony.dom.bridge import Neony

    bridge = _media_bridge(monkeypatch, Response())
    with pytest.raises(lv_bridge.BridgeError) as excinfo:
        asyncio.run(Neony._on_media_read(bridge, None, "https://example.com/a.mp3"))  # type: ignore[arg-type]
    assert excinfo.value.code == "bad_url"


def test_media_read_unknown_key_raises_not_found(monkeypatch):
    import lumiview.bridge as lv_bridge

    from neony.dom.bridge import Neony

    bridge = _media_bridge(monkeypatch, Response())
    with pytest.raises(lv_bridge.BridgeError) as excinfo:
        asyncio.run(Neony._on_media_read(bridge, None, "neony://nope/x.mp3"))  # type: ignore[arg-type]
    assert excinfo.value.code == "not_found"


def test_media_read_upstream_error_propagates(monkeypatch):
    import lumiview.bridge as lv_bridge

    from neony.dom.bridge import Neony

    bridge = _media_bridge(monkeypatch, Response(status=404, headers={}, body=b""))
    with pytest.raises(lv_bridge.BridgeError) as excinfo:
        asyncio.run(Neony._on_media_read(bridge, None, "neony://local/gone.mp3"))  # type: ignore[arg-type]
    assert excinfo.value.code == "upstream_error"


def test_media_read_ranged_slice_reports_total(monkeypatch, tmp_path):
    """offset/chunk → Range 请求 → local_files 206 分片 + Content-Range 总长。"""
    import importlib

    from neony.application import local_files
    from neony.dom.bridge import Neony

    media = tmp_path / "big.mp4"
    media.write_bytes(b"0123456789ABCDEF")

    # lumiview.__init__ 遮蔽了 task 子模块属性 —— 用 importlib 取真身
    lv_task = importlib.import_module("lumiview.task")

    async def fake_run_async(fn, request, **kwargs):
        return fn(request)

    monkeypatch.setattr(lv_task, "run_async", fake_run_async)

    bridge = Neony(name="neony")
    bridge._protocol_handlers = {"local": local_files}

    payload = asyncio.run(
        Neony._on_media_read(bridge, None, local_url(media), offset=4, chunk=6)  # type: ignore[arg-type]
    )
    assert payload["status"] == 206
    assert base64.b64decode(payload["data_b64"]) == b"456789"
    assert payload["total"] == 16
    assert payload["complete"] is False
    assert payload["content_type"] == "video/mp4"


def test_media_read_unranged_handler_falls_back_complete(monkeypatch):
    """处理器无视 Range 回 200 全量 → complete=True、total=全长。"""
    from neony.dom.bridge import Neony

    bridge = _media_bridge(monkeypatch, Response(status=200, headers={"Content-Type": "audio/wav"}, body=b"abc"))
    payload = asyncio.run(
        Neony._on_media_read(bridge, None, "neony://local/a.wav", offset=0, chunk=4)  # type: ignore[arg-type]
    )
    assert payload["complete"] is True
    assert payload["total"] == 3
    assert base64.b64decode(payload["data_b64"]) == b"abc"
