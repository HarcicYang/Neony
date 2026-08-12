"""Native file dialogs — shell out to the platform's own picker.

Neony/lumiview expose no file-picker API, so we delegate to the system
dialogs: ``zenity`` on Linux (present on most desktops), ``osascript``
on macOS, PowerShell on Windows, with a tkinter fallback.  All calls
run in an executor thread (see ``neony.application.dialogs``) so the
asyncio loop never blocks.

Raw sentinel convention: ``""`` for a cancelled single pick, ``()``
for a cancelled multi-pick — ``dialogs._normalize`` maps those to the
public ``None`` / ``[]`` shapes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Literal, overload

_FILTER_SEP = "|"  # zenity's --file-filter name/pattern separator


def _filter_args(filetypes: list[tuple[str, str]] | None) -> list[str]:
    """``[(label, "*.png *.jpg")]`` → zenity ``--file-filter`` args.

    The label must not contain ``|`` (zenity's name/pattern separator) —
    those are stripped.  An empty list means "all files": passed as a
    single catch-all filter.
    """
    if not filetypes:
        return ["--file-filter", f"All files{_FILTER_SEP}*"]
    args: list[str] = []
    for label, patterns in filetypes:
        args.append("--file-filter")
        args.append(f"{label.replace(_FILTER_SEP, ' ')}{_FILTER_SEP}{patterns}")
    return args


def _tk_filetypes(filetypes: list[tuple[str, str]] | None) -> list[tuple[str, tuple[str, ...]]]:
    """Convert Neony filetypes to tkinter's shape (``("*",)`` sentinel)."""
    if not filetypes:
        return [("All files", ("*",))]
    return [(label, tuple(patterns.split())) for label, patterns in filetypes]


def _default_path(default_dir: str | None, default_name: str | None = None) -> str | None:
    """The starting location handed to the dialog, or None (let the
    dialog use its own default — typically the current directory)."""
    if default_name is not None:
        return os.path.join(default_dir or "", default_name)
    if default_dir:
        return default_dir + os.sep
    return None


def _pick_platform() -> str:
    """The branch name for the current platform: "linux" / "darwin" /
    "win32", or the sys.platform string when unrecognized (tkinter
    fallback branch)."""
    system = sys.platform
    if system.startswith("linux"):
        return "linux"
    if system == "darwin":
        return "darwin"
    if system in ("win32", "cygwin"):
        return "win32"
    return system


def _open_sync(
    kind: str,
    *,
    title: str = "Open",
    default_dir: str | None = None,
    filetypes: list[tuple[str, str]] | None = None,
) -> str | tuple[str, ...]:
    """Blocking single/multi open — runs on an executor thread."""
    many = kind == "open-many"
    platform = _pick_platform()
    if platform == "linux" and shutil.which("zenity"):
        args = ["zenity", "--file-selection", "--title", title]
        path = _default_path(default_dir)
        if path is not None:
            args += ["--filename", path]
        args += _filter_args(filetypes)
        if many:
            args.append("--multiple")
        return _run_zenity(args, many=many)
    if platform == "darwin":
        return _osascript_open(title, default_dir, filetypes, many=many)
    if platform == "win32":
        return _powershell_open(title, default_dir, filetypes, many=many)
    return _tk_open(title, default_dir, filetypes, many=many)


def _save_sync(
    *,
    title: str,
    default_dir: str | None,
    default_name: str | None,
    filetypes: list[tuple[str, str]] | None,
) -> str:
    """Blocking save-as — runs on an executor thread."""
    platform = _pick_platform()
    if platform == "linux" and shutil.which("zenity"):
        args = ["zenity", "--file-selection", "--save", "--confirm-overwrite", "--title", title]
        path = _default_path(default_dir, default_name)
        if path is not None:
            args += ["--filename", path]
        args += _filter_args(filetypes)
        return _run_zenity(args)
    if platform == "darwin":
        return _osascript_save(title, default_dir, default_name, filetypes)
    if platform == "win32":
        return _powershell_save(title, default_dir, default_name, filetypes)
    return _tk_save(title, default_dir, default_name, filetypes)


def _folder_sync(*, title: str, default_dir: str | None) -> str:
    """Blocking folder pick — runs on an executor thread."""
    platform = _pick_platform()
    if platform == "linux" and shutil.which("zenity"):
        args = ["zenity", "--file-selection", "--directory", "--title", title]
        path = _default_path(default_dir)
        if path is not None:
            args += ["--filename", path]
        return _run_zenity(args)
    if platform == "darwin":
        return _osascript_folder(title, default_dir)
    if platform == "win32":
        return _powershell_folder(title, default_dir)
    return _tk_folder(title, default_dir)


@overload
def _run_zenity(args: list[str], *, many: Literal[True]) -> tuple[str, ...]: ...
@overload
def _run_zenity(args: list[str], *, many: Literal[False] = False) -> str: ...
def _run_zenity(args: list[str], *, many: bool = False) -> str | tuple[str, ...]:
    """Run one zenity invocation; ``""`` / ``()`` on cancel or failure."""
    try:
        result = subprocess.run(args, capture_output=True, text=True)
    except OSError:
        return () if many else ""
    if result.returncode != 0:  # 1 = cancelled
        return () if many else ""
    stdout = result.stdout.strip()
    if not stdout:
        return () if many else ""
    if many:
        return _split_many(stdout)
    return stdout


def _split_many(stdout: str) -> tuple[str, ...]:
    """Split zenity's multi-file output — ``|``-separated on older
    versions, newline-separated on newer ones (path may contain ``|``,
    so prefer newlines when there is no pipe at all)."""
    if _FILTER_SEP in stdout:
        return tuple(part.strip() for part in stdout.split(_FILTER_SEP))
    return tuple(part.strip() for part in stdout.splitlines())


# ── AppleScript (macOS) ───────────────────────────────────────────


def _as_quote(text: str) -> str:
    """Quote *text* as an AppleScript string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _osascript_open(
    title: str, default_dir: str | None, filetypes: list[tuple[str, str]] | None, *, many: bool
) -> str | tuple[str, ...]:
    script = "set chosen to choose file"
    if default_dir is not None:
        script += f" default location POSIX file {_as_quote(os.path.abspath(default_dir))}"
    script += f" with prompt {_as_quote(title)}"
    if many:
        script += " with multiple selections allowed"
    return _run_osascript(script, many=many)


def _osascript_save(
    title: str, default_dir: str | None, default_name: str | None, filetypes: list[tuple[str, str]] | None
) -> str:
    script = "set chosen to choose file name"
    if default_name is not None:
        script += f" default name {_as_quote(default_name)}"
    if default_dir is not None:
        script += f" default location POSIX file {_as_quote(os.path.abspath(default_dir))}"
    script += f" with prompt {_as_quote(title)}"
    return _run_osascript(script)


def _osascript_folder(title: str, default_dir: str | None) -> str:
    script = "set chosen to choose folder"
    if default_dir is not None:
        script += f" default location POSIX file {_as_quote(os.path.abspath(default_dir))}"
    script += f" with prompt {_as_quote(title)}"
    return _run_osascript(script)


@overload
def _run_osascript(script: str, *, many: Literal[True]) -> tuple[str, ...]: ...
@overload
def _run_osascript(script: str, *, many: Literal[False] = False) -> str: ...
def _run_osascript(script: str, *, many: bool = False) -> str | tuple[str, ...]:
    """Run one osascript invocation; ``""`` / ``()`` on cancel/failure."""
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    except OSError:
        return () if many else ""
    if result.returncode != 0:
        return () if many else ""
    stdout = result.stdout.strip()
    if not stdout:
        return () if many else ""
    if many:
        return tuple(part.strip() for part in stdout.splitlines())
    return stdout


# ── PowerShell (Windows) ──────────────────────────────────────────


def _powershell_open(
    title: str, default_dir: str | None, filetypes: list[tuple[str, str]] | None, *, many: bool
) -> str | tuple[str, ...]:
    script = _powershell_script("OpenFileDialog", title, default_dir, None, filetypes, many=many)
    return _run_powershell(script, many=many)


def _powershell_save(
    title: str, default_dir: str | None, default_name: str | None, filetypes: list[tuple[str, str]] | None
) -> str:
    script = _powershell_script("SaveFileDialog", title, default_dir, default_name, filetypes, many=False)
    return _run_powershell(script)


def _powershell_folder(title: str, default_dir: str | None) -> str:
    script = _powershell_script("FolderBrowserDialog", title, default_dir, None, None, many=False)
    return _run_powershell(script)


def _powershell_script(
    kind: str,
    title: str,
    default_dir: str | None,
    default_name: str | None,
    filetypes: list[tuple[str, str]] | None,
    *,
    many: bool,
) -> str:
    lines = [
        "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null",
        f"$d = New-Object System.Windows.Forms.{kind}",
    ]
    # FolderBrowserDialog prompts via Description, not Title.
    lines.append(f"$d.{'Description' if kind == 'FolderBrowserDialog' else 'Title'} = '{_ps_quote(title)}'")
    initial = os.path.abspath(default_dir) if default_dir else os.getcwd()
    lines.append(f"$d.InitialDirectory = '{_ps_quote(initial)}'")
    if kind == "FolderBrowserDialog":
        lines.append(f"$d.SelectedPath = '{_ps_quote(initial)}'")
    if default_name is not None:
        lines.append(f"$d.FileName = '{_ps_quote(default_name)}'")
    if filetypes:
        filter_text = "|".join(f"{_ps_quote(label)}|{patterns}" for label, patterns in filetypes)
        lines.append(f"$d.Filter = '{_ps_quote(filter_text)}'")
    if many:
        lines.append("$d.Multiselect = $true")
    lines.append("if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {")
    lines.append("  $d.FileNames | ForEach-Object { $_.ToString() }" if many else "  $d.FileName")
    lines.append("}")
    return "; ".join(lines)


def _ps_quote(text: str) -> str:
    """Escape *text* for a PowerShell single-quoted literal."""
    return text.replace("'", "''")


@overload
def _run_powershell(script: str, *, many: Literal[True]) -> tuple[str, ...]: ...
@overload
def _run_powershell(script: str, *, many: Literal[False] = False) -> str: ...
def _run_powershell(script: str, *, many: bool = False) -> str | tuple[str, ...]:
    """Run one PowerShell invocation; ``""`` / ``()`` on cancel/failure."""
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    except OSError:
        return () if many else ""
    if result.returncode != 0:
        return () if many else ""
    stdout = result.stdout.strip()
    if not stdout:
        return () if many else ""
    if many:
        return tuple(part.strip() for part in stdout.splitlines())
    return stdout


# ── tkinter fallback (system python; zenity/osascript/powershell absent) ──


def _tk_open(
    title: str, default_dir: str | None, filetypes: list[tuple[str, str]] | None, *, many: bool
) -> str | tuple[str, ...]:
    """tkinter fallback for open / open-many (runs on an executor thread)."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if many:
            return tuple(
                filedialog.askopenfilenames(
                    title=title, initialdir=default_dir or "", filetypes=_tk_filetypes(filetypes)
                )
            )
        return (
            filedialog.askopenfilename(title=title, initialdir=default_dir or "", filetypes=_tk_filetypes(filetypes))
            or ""
        )
    finally:
        root.destroy()


def _tk_save(
    title: str, default_dir: str | None, default_name: str | None, filetypes: list[tuple[str, str]] | None
) -> str:
    """tkinter fallback for save-as (runs on an executor thread)."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.asksaveasfilename(
            title=title,
            initialdir=default_dir or "",
            initialfile=default_name or "",
            filetypes=_tk_filetypes(filetypes),
        )
        return path or ""
    finally:
        root.destroy()


def _tk_folder(title: str, default_dir: str | None) -> str:
    """tkinter fallback for the folder picker (runs on an executor thread)."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title=title, initialdir=default_dir or "") or ""
    finally:
        root.destroy()
