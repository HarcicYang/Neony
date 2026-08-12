"""Native file dialogs — ``app.open_file`` & co. via a one-shot tkinter
subprocess with a typed ``multiprocessing.Pipe`` protocol.

Every test is mocked — no real subprocess is spawned and no dialog ever
shows (CI is headless).  The pipe protocol is exercised end-to-end with
fake connections/process objects standing in for the ``multiprocessing``
machinery; the child-side dispatch is tested as a pure function.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, ClassVar

import pytest

from neony import _dialog_worker as worker
from neony._dialog_worker import _dispatch
from neony.application import Config, NeonApplication, dialogs


class _FakeConn:
    def __init__(self, reply: Any) -> None:
        self._reply = reply
        self.raised: BaseException | None = None
        self.closed = False

    def recv(self) -> Any:
        if self.raised is not None:
            raise self.raised
        return self._reply

    def close(self) -> None:
        self.closed = True


class _FakeProc:
    def __init__(self) -> None:
        self.started = False
        self.joined = 0

    def start(self) -> None:
        self.started = True

    def join(self, timeout: float | None = None) -> None:
        self.joined += 1


class _FakeCtx:
    """multiprocessing context stand-in: returns fake connections + a
    recorded fake process, so ``show_dialog`` never touches real pipes."""

    def __init__(self, reply: Any) -> None:
        self.parent = _FakeConn(reply)
        self.child = _FakeConn(None)
        self.proc = _FakeProc()
        self.request: dict[str, Any] | None = None

    def Pipe(self, duplex: bool):
        assert not duplex
        return self.parent, self.child

    def Process(self, *, target: Any, args: tuple[Any, ...], daemon: bool):
        self.target = target
        self.args = args
        self.daemon = daemon
        return self.proc


def _run(monkeypatch: pytest.MonkeyPatch, reply: Any, *, kind: str = "open") -> tuple[Any, _FakeCtx]:
    ctx = _FakeCtx(reply)
    monkeypatch.setattr(dialogs, "_ctx", lambda: ctx)
    return asyncio.run(dialogs.show_dialog(kind)), ctx


# ── request building ──────────────────────────────────────────────


class TestRequest:
    def test_kind_only_when_nothing_given(self):
        assert dialogs._request("open") == {"kind": "open"}

    def test_none_fields_dropped(self):
        assert dialogs._request("open", title=None, default_dir=None, filetypes=None) == {"kind": "open"}

    def test_fields_mapped_to_tkinter_names(self):
        req = dialogs._request(
            "save",
            title="Save as",
            default_dir="/tmp",
            default_name="out.txt",
            filetypes=[("Text", "*.txt")],
        )
        assert req == {
            "kind": "save",
            "title": "Save as",
            "initialdir": "/tmp",
            "initialfile": "out.txt",
            "filetypes": [("Text", "*.txt")],
        }

    def test_filetypes_passthrough(self):
        ft = [("Images", "*.png *.jpg"), ("All files", "*.*")]
        assert dialogs._filetypes(ft) == ft


# ── result normalization ──────────────────────────────────────────


class TestNormalize:
    def test_open_path(self):
        assert dialogs._normalize("open", "/a/b.txt") == "/a/b.txt"

    def test_open_cancel_empty_to_none(self):
        assert dialogs._normalize("open", "") is None

    def test_open_many_paths(self):
        assert dialogs._normalize("open-many", ("a.txt", "b.txt")) == ["a.txt", "b.txt"]

    def test_open_many_cancel_empty_to_list(self):
        assert dialogs._normalize("open-many", ()) == []

    def test_save_and_folder_cancel_to_none(self):
        assert dialogs._normalize("save", "") is None
        assert dialogs._normalize("folder", "") is None


# ── child-side dispatch (pure) ────────────────────────────────────


class _RecordDialog:
    """Construction records the routed kind/options; ``result`` is the
    fake's canned return."""

    instances: ClassVar[list[_RecordDialog]] = []

    def __init__(self, root: Any, kind: str, options: dict[str, Any], result: Any) -> None:
        self.root = root
        self.kind = kind
        self.options = options
        self.result = result
        _RecordDialog.instances.append(self)


def _fake_dialog_cls(result: Any):
    def _build(root: Any, kind: str, options: dict[str, Any]) -> _RecordDialog:
        return _RecordDialog(root, kind, options, result)

    return _build


class TestDispatch:
    def test_open_routes_and_forwards_options(self):
        dialog = _fake_dialog_cls("/a/b.png")
        result = _dispatch(None, {"kind": "open", "title": "Open", "filetypes": [("PNG", "*.png")]}, dialog_cls=dialog)
        assert result == "/a/b.png"
        assert _RecordDialog.instances[-1].kind == "open"
        assert _RecordDialog.instances[-1].options == {"title": "Open", "filetypes": [("PNG", "*.png")]}

    def test_none_options_dropped(self):
        dialog = _fake_dialog_cls("")
        _dispatch(None, {"kind": "save", "title": None, "initialfile": "out.txt"}, dialog_cls=dialog)
        assert _RecordDialog.instances[-1].options == {"initialfile": "out.txt"}

    def test_open_many_routes(self):
        dialog = _fake_dialog_cls(("a", "b"))
        assert _dispatch(None, {"kind": "open-many"}, dialog_cls=dialog) == ("a", "b")
        assert _RecordDialog.instances[-1].kind == "open-many"

    def test_folder_routes(self):
        dialog = _fake_dialog_cls("/home/user")
        assert _dispatch(None, {"kind": "folder"}, dialog_cls=dialog) == "/home/user"
        assert _RecordDialog.instances[-1].kind == "folder"

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="unknown dialog kind"):
            _dispatch(None, {"kind": "nope"})


# ── worker helpers (pure) ─────────────────────────────────────────


class TestWorkerHelpers:
    def test_matches_globs(self):
        assert worker._matches("photo.png", ["*.png", "*.jpg"])
        assert worker._matches("photo.JPG", ["*.png", "*.jpg"])  # case-insensitive
        assert not worker._matches("notes.txt", ["*.png", "*.jpg"])

    def test_matches_none_matches_everything(self):
        assert worker._matches("anything.txt", None)
        assert worker._matches("anything.txt", [])

    def test_size_formatting(self):
        assert worker._fmt_size(0) == "0 B"
        assert worker._fmt_size(512) == "512 B"
        assert worker._fmt_size(1536) == "1.5 KB"
        assert worker._fmt_size(3 * 1024 * 1024) == "3.0 MB"

    def test_time_formatting(self):
        assert worker._fmt_time(0) == time.strftime("%Y-%m-%d %H:%M", time.localtime(0))

    def test_list_entries_sorts_dirs_first(self, tmp_path):
        (tmp_path / "zeta.txt").write_text("z")
        (tmp_path / "Alpha.txt").write_text("a")
        (tmp_path / "beta").mkdir()
        entries = worker._list_entries(str(tmp_path), ["*.txt"])
        assert entries == [("beta", True), ("Alpha.txt", False), ("zeta.txt", False)]

    def test_list_entries_filters_files_keeps_dirs(self, tmp_path):
        (tmp_path / "keep.png").write_text("k")
        (tmp_path / "skip.txt").write_text("s")
        (tmp_path / "folder").mkdir()
        assert worker._list_entries(str(tmp_path), ["*.png"]) == [("folder", True), ("keep.png", False)]

    def test_list_entries_dirs_only_hides_files(self, tmp_path):
        (tmp_path / "file.txt").write_text("f")
        assert worker._list_entries(str(tmp_path), None, dirs_only=True) == []

    def test_list_entries_unreadable_raises(self, tmp_path):
        with pytest.raises(OSError):
            worker._list_entries(str(tmp_path / "missing"), None)


# ── parent-side pipe protocol (mocked) ────────────────────────────


class TestShowDialogProtocol:
    def test_ok_reply_returns_normalized_result(self, monkeypatch: pytest.MonkeyPatch):
        result, ctx = _run(monkeypatch, ("ok", "/a/b.txt"))
        assert result == "/a/b.txt"
        # The subprocess was launched with the child pipe end + request.
        assert ctx.proc.started
        assert ctx.args == (ctx.child, {"kind": "open"})
        assert ctx.daemon is True
        assert ctx.parent.closed  # read end closed after the reply

    def test_error_reply_returns_none_and_logs(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        with caplog.at_level("ERROR", logger="neony.dialogs"):
            result, _ctx = _run(monkeypatch, ("error", "TclError: no display"))
        assert result is None
        assert "no display" in caplog.text

    def test_child_died_returns_none(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        ctx = _FakeCtx(None)
        ctx.parent.raised = EOFError()
        monkeypatch.setattr(dialogs, "_ctx", lambda: ctx)
        with caplog.at_level("ERROR", logger="neony.dialogs"):
            result = asyncio.run(dialogs.show_dialog("open"))
        assert result is None
        assert "died before replying" in caplog.text

    def test_open_many_empty_reply_is_empty_list(self, monkeypatch: pytest.MonkeyPatch):
        result, _ = _run(monkeypatch, ("ok", ()), kind="open-many")
        assert result == []

    def test_unknown_kind_rejected_before_subprocess(self, monkeypatch: pytest.MonkeyPatch):
        with pytest.raises(ValueError, match="unknown dialog kind"):
            asyncio.run(dialogs.show_dialog("nope"))


# ── NeonApplication convenience methods ───────────────────────────


class TestAppMethods:
    def test_open_file_forwards(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/a/b.png"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        result = asyncio.run(app.open_file(title="Pick", default_dir="/home", filetypes=[("PNG", "*.png")]))

        assert result == "/a/b.png"
        assert calls == [("open", {"title": "Pick", "default_dir": "/home", "filetypes": [("PNG", "*.png")]})]

    def test_open_files_returns_list(self, monkeypatch: pytest.MonkeyPatch):
        async def fake_show(kind: str, **kwargs: Any) -> Any:
            return ["a.txt", "b.txt"]

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        assert asyncio.run(app.open_files()) == ["a.txt", "b.txt"]

    def test_open_files_cancel_is_empty(self, monkeypatch: pytest.MonkeyPatch):
        async def fake_show(kind: str, **kwargs: Any) -> Any:
            return []

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        assert asyncio.run(app.open_files()) == []

    def test_save_file_forwards_default_name(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/tmp/out.txt"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        result = asyncio.run(app.save_file(default_dir="/tmp", default_name="out.txt"))

        assert result == "/tmp/out.txt"
        assert calls == [("save", {"title": None, "default_dir": "/tmp", "default_name": "out.txt", "filetypes": None})]

    def test_save_file_cancel_is_none(self, monkeypatch: pytest.MonkeyPatch):
        async def fake_show(kind: str, **kwargs: Any) -> Any:
            return None

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        assert asyncio.run(app.save_file()) is None

    def test_select_folder_forwards(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/home/user/docs"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = NeonApplication(Config())

        result = asyncio.run(app.select_folder(default_dir="/home/user"))

        assert result == "/home/user/docs"
        assert calls == [("folder", {"title": None, "default_dir": "/home/user"})]
