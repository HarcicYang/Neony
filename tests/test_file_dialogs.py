"""System-native file dialogs — zenity / osascript / PowerShell +
tkinter fallback, driven through ``app.open_file`` & co.

Every test is mocked — no real dialog ever shows (CI is headless).
The pure helpers are tested directly; the sync platform functions are
exercised via fake subprocess results; ``show_dialog`` is verified
through a monkeypatched executor; the app-level wrappers are checked
by monkeypatching ``show_dialog``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from neony import _dialog_worker as worker
from neony.application import Config, NeonApplication, dialogs


def _fake_run(result: Any, *, many: bool = False) -> Any:
    """Wrap a fake subprocess ``returncode``/``stdout`` in the shape
    ``_run_zenity`` expects — returns a function that ignores args."""

    class FakeResult:
        returncode = 0
        stdout = result

    def _run(_args: list[str], *, _many: bool = False) -> Any:
        assert _many == many
        return many if result is None else None  # not used

    return _run


class FakeRun:
    """A stand-in for ``subprocess.run`` returning a canned result."""

    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout

    def __call__(self, args: list[str], **kwargs: Any) -> FakeRun:
        self.args = args
        return self


# ── request building ──────────────────────────────────────────────


class TestRequest:
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


# ── worker helpers (pure) ─────────────────────────────────────────


class TestWorkerHelpers:
    def test_filter_args_default_all_files(self):
        assert worker._filter_args(None) == ["--file-filter", "All files|*"]
        assert worker._filter_args([]) == ["--file-filter", "All files|*"]

    def test_filter_args_maps_labels_and_patterns(self):
        args = worker._filter_args([("PNG images", "*.png"), ("All files", "*.*")])
        assert args == [
            "--file-filter",
            "PNG images|*.png",
            "--file-filter",
            "All files|*.*",
        ]

    def test_filter_args_strips_pipe_from_label(self):
        args = worker._filter_args([("a|b", "*.png")])
        assert args == ["--file-filter", "a b|*.png"]

    def test_tk_filetypes_default(self):
        assert worker._tk_filetypes(None) == [("All files", ("*",))]
        assert worker._tk_filetypes([]) == [("All files", ("*",))]

    def test_tk_filetypes_splits_patterns(self):
        assert worker._tk_filetypes([("Images", "*.png *.jpg")]) == [("Images", ("*.png", "*.jpg"))]

    def test_default_path_dir_only(self):
        assert worker._default_path("/home/user") == "/home/user/"

    def test_default_path_with_name(self):
        assert worker._default_path("/home/user", "out.txt") == "/home/user/out.txt"
        assert worker._default_path(None, "out.txt") == "out.txt"

    def test_default_path_none(self):
        assert worker._default_path(None) is None
        assert worker._default_path("") is None

    def test_pick_platform_maps(self, monkeypatch: pytest.MonkeyPatch):
        for raw, expected in [("linux", "linux"), ("linux2", "linux"), ("darwin", "darwin"), ("win32", "win32")]:
            monkeypatch.setattr(worker.sys, "platform", raw)
            assert worker._pick_platform() == expected

    def test_split_many_pipe_and_newline(self):
        assert worker._split_many("a.txt|b.txt") == ("a.txt", "b.txt")
        assert worker._split_many("a.txt\nb.txt") == ("a.txt", "b.txt")


# ── zenity branch (Linux) ─────────────────────────────────────────


class TestZenity:
    @pytest.fixture(autouse=True)
    def _force_zenity_branch(self, monkeypatch: pytest.MonkeyPatch):
        # CI has no zenity installed; without this, _open_sync falls into
        # the tkinter branch (absent there too — uv's Python has no Tk).
        # Pin the branch to zenity so these tests exercise zenity itself.
        monkeypatch.setattr(worker.sys, "platform", "linux")
        monkeypatch.setattr(worker.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

    def test_open_picks_path(self, monkeypatch: pytest.MonkeyPatch):
        fake = FakeRun(0, "/home/user/a.png\n")
        monkeypatch.setattr(worker.subprocess, "run", fake)
        assert worker._open_sync("open", title="Open", default_dir="/home/user", filetypes=[("PNG", "*.png")]) == (
            "/home/user/a.png"
        )
        assert "--file-selection" in fake.args
        assert fake.args[fake.args.index("--title") + 1] == "Open"
        assert fake.args[fake.args.index("--file-filter") + 1] == "PNG|*.png"

    def test_open_cancel_returns_empty(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.subprocess, "run", FakeRun(1, ""))
        assert worker._open_sync("open", title="Open") == ""

    def test_open_many_splits_paths(self, monkeypatch: pytest.MonkeyPatch):
        fake = FakeRun(0, "/a/x.png|/b/y.png\n")
        monkeypatch.setattr(worker.subprocess, "run", fake)
        assert worker._open_sync("open-many", title="Open") == ("/a/x.png", "/b/y.png")
        assert "--multiple" in fake.args

    def test_open_many_cancel_empty_tuple(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.subprocess, "run", FakeRun(1, ""))
        assert worker._open_sync("open-many", title="Open") == ()

    def test_save_confirms_overwrite(self, monkeypatch: pytest.MonkeyPatch):
        fake = FakeRun(0, "/home/user/out.txt\n")
        monkeypatch.setattr(worker.subprocess, "run", fake)
        result = worker._save_sync(title="Save", default_dir="/home/user", default_name="out.txt", filetypes=None)
        assert result == "/home/user/out.txt"
        assert "--save" in fake.args
        assert "--confirm-overwrite" in fake.args
        assert fake.args[fake.args.index("--filename") + 1] == "/home/user/out.txt"

    def test_folder(self, monkeypatch: pytest.MonkeyPatch):
        fake = FakeRun(0, "/home/user/docs\n")
        monkeypatch.setattr(worker.subprocess, "run", fake)
        assert worker._folder_sync(title="Pick", default_dir="/home/user") == "/home/user/docs"
        assert "--directory" in fake.args

    def test_oserror_cancels(self, monkeypatch: pytest.MonkeyPatch):
        def boom(_args: list[str], **kwargs: Any) -> None:
            raise OSError("no zenity")

        monkeypatch.setattr(worker.subprocess, "run", boom)
        assert worker._open_sync("open", title="Open") == ""
        assert worker._open_sync("open-many", title="Open") == ()


# ── platform dispatch ─────────────────────────────────────────────


class TestDispatch:
    def test_linux_without_zenity_falls_back_to_tk(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.sys, "platform", "linux")
        monkeypatch.setattr(worker.shutil, "which", lambda _cmd: None)
        calls: list[tuple] = []

        def fake_tk(title: str, default_dir: str | None, filetypes: Any, *, many: bool) -> Any:
            calls.append(("tk", title, many))
            return "/fallback/path"

        monkeypatch.setattr(worker, "_tk_open", fake_tk)
        assert worker._open_sync("open", title="Open") == "/fallback/path"
        assert calls == [("tk", "Open", False)]

    def test_linux_with_zenity_prefers_it(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.sys, "platform", "linux")
        monkeypatch.setattr(worker.shutil, "which", lambda _cmd: "/usr/bin/zenity")
        monkeypatch.setattr(worker.subprocess, "run", FakeRun(0, "/p\n"))
        assert worker._open_sync("open", title="Open") == "/p"

    def test_macos_uses_osascript(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.sys, "platform", "darwin")
        fake = FakeRun(0, "/Users/u/a.png\n")
        monkeypatch.setattr(worker.subprocess, "run", fake)
        assert worker._open_sync("open", title="Open") == "/Users/u/a.png"
        assert "choose file" in fake.args[2]

        fake_many = FakeRun(0, "/Users/u/a.png\n/Users/u/b.png\n")
        monkeypatch.setattr(worker.subprocess, "run", fake_many)
        assert worker._open_sync("open-many", title="Open") == ("/Users/u/a.png", "/Users/u/b.png")

    def test_windows_uses_powershell(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.sys, "platform", "win32")
        monkeypatch.setattr(worker.subprocess, "run", FakeRun(0, "C:\\u\\a.png\n"))
        assert worker._open_sync("open", title="Open") == "C:\\u\\a.png"

    def test_unknown_platform_uses_tk(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(worker.sys, "platform", "plan9")
        calls: list[tuple] = []

        def fake_tk(title: str, default_dir: str | None, filetypes: Any, *, many: bool) -> Any:
            calls.append(("tk", title))
            return "/x"

        monkeypatch.setattr(worker, "_tk_open", fake_tk)
        assert worker._open_sync("open", title="Open") == "/x"
        assert calls == [("tk", "Open")]

    def test_tk_missing_import_reads_as_cancel(self, monkeypatch: pytest.MonkeyPatch):
        """uv's standalone Python has no Tk — the tkinter fallback must
        read as a cancelled dialog, never raise."""
        monkeypatch.setattr(worker.sys, "platform", "linux")
        monkeypatch.setattr(worker.shutil, "which", lambda _cmd: None)
        import builtins

        real_import = builtins.__import__

        def no_tk(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "tkinter":
                raise ImportError("no tkinter")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_tk)
        assert worker._open_sync("open", title="Open") == ""
        assert worker._open_sync("open-many", title="Open") == ()
        assert worker._save_sync(title="S", default_dir=None, default_name=None, filetypes=None) == ""
        assert worker._folder_sync(title="F", default_dir=None) == ""


# ── show_dialog (executor + normalize) ────────────────────────────


class TestShowDialog:
    def test_open_returns_normalized_path(self, monkeypatch: pytest.MonkeyPatch):
        async def scenario() -> None:
            monkeypatch.setattr(worker, "_open_sync", lambda *a, **k: "/picked/file.txt")
            assert await dialogs.show_dialog("open", title="T") == "/picked/file.txt"

        asyncio.run(scenario())

    def test_open_cancel_normalizes_to_none(self, monkeypatch: pytest.MonkeyPatch):
        async def scenario() -> None:
            monkeypatch.setattr(worker, "_open_sync", lambda *a, **k: "")
            assert await dialogs.show_dialog("open", title="T") is None

        asyncio.run(scenario())

    def test_open_many_normalizes_to_list(self, monkeypatch: pytest.MonkeyPatch):
        async def scenario() -> None:
            monkeypatch.setattr(worker, "_open_sync", lambda *a, **k: ("/a", "/b"))
            assert await dialogs.show_dialog("open-many", title="T") == ["/a", "/b"]

        asyncio.run(scenario())

    def test_open_many_cancel_normalizes_to_empty_list(self, monkeypatch: pytest.MonkeyPatch):
        async def scenario() -> None:
            monkeypatch.setattr(worker, "_open_sync", lambda *a, **k: ())
            assert await dialogs.show_dialog("open-many", title="T") == []

        asyncio.run(scenario())

    def test_save_dispatches_save_sync(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple] = []

        async def scenario() -> None:
            def fake_save(*args: Any, **kwargs: Any) -> str:
                calls.append((args, kwargs))
                return "/out.txt"

            monkeypatch.setattr(worker, "_save_sync", fake_save)
            assert (
                await dialogs.show_dialog(
                    "save", title="S", default_dir="/tmp", default_name="x.txt", filetypes=[("T", "*.txt")]
                )
                == "/out.txt"
            )
            assert calls and calls[0][1]["default_name"] == "x.txt"

        asyncio.run(scenario())

    def test_folder_dispatches_folder_sync(self, monkeypatch: pytest.MonkeyPatch):
        async def scenario() -> None:
            monkeypatch.setattr(worker, "_folder_sync", lambda *a, **k: "/docs")
            assert await dialogs.show_dialog("folder", title="F") == "/docs"

        asyncio.run(scenario())

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError, match="unknown dialog kind"):
            dialogs._validate_kind("nope")


# ── NeonApplication convenience methods ───────────────────────────


class TestAppMethods:
    def _app(self) -> NeonApplication:
        return NeonApplication(Config())

    async def _show(self, kind: str, **kwargs: Any) -> Any:
        return f"/result/{kind}"

    def test_open_file_forwards(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/a/b.png"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = self._app()

        result = asyncio.run(app.open_file(title="Pick", default_dir="/home", filetypes=[("PNG", "*.png")]))

        assert result == "/a/b.png"
        assert calls[0][0] == "open"
        assert calls[0][1]["title"] == "Pick"
        assert calls[0][1]["default_dir"] == "/home"
        assert calls[0][1]["filetypes"] == [("PNG", "*.png")]

    def test_open_file_cancel_is_none(self, monkeypatch: pytest.MonkeyPatch):
        async def fake_show(kind: str, **kwargs: Any) -> Any:
            return None

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        assert asyncio.run(self._app().open_file()) is None

    def test_open_files_returns_list(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return ["a.txt", "b.txt"]

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = self._app()

        assert asyncio.run(app.open_files()) == ["a.txt", "b.txt"]
        assert calls[0][0] == "open-many"

    def test_save_file_forwards_default_name(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/tmp/out.txt"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = self._app()

        result = asyncio.run(app.save_file(default_dir="/tmp", default_name="out.txt"))

        assert result == "/tmp/out.txt"
        assert calls[0][0] == "save"
        assert calls[0][1]["default_name"] == "out.txt"

    def test_save_file_cancel_is_none(self, monkeypatch: pytest.MonkeyPatch):
        async def fake_show(kind: str, **kwargs: Any) -> Any:
            return None

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        assert asyncio.run(self._app().save_file()) is None

    def test_select_folder_forwards(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, dict[str, Any]]] = []

        async def fake_show(kind: str, **kwargs: Any) -> Any:
            calls.append((kind, kwargs))
            return "/home/user/docs"

        monkeypatch.setattr(dialogs, "show_dialog", fake_show)
        app = self._app()

        result = asyncio.run(app.select_folder(default_dir="/home/user"))

        assert result == "/home/user/docs"
        assert calls[0][0] == "folder"
        assert calls[0][1]["default_dir"] == "/home/user"
