"""Subprocess entry for file dialogs — stdlib only.

Kept separate from :mod:`neony.application.dialogs` so a spawn child
(Windows) imports just this module instead of the whole webview stack,
and a fork child (Linux/macOS) needs no import at all.  The child builds
a bare Tk root and shows a *self-drawn* file picker — the platform
``tkinter.filedialog`` is dated (especially on Linux) and cannot be
restyled, and a subprocess has no access to the host app's chrome.  The
result travels back over a one-way ``multiprocessing`` pipe as a typed
``("ok", result)`` / ``("error", "Type: message")`` tuple — no stdout
parsing anywhere.
"""

from __future__ import annotations

import contextlib
import fnmatch
import os
import time
import tkinter as tk
from tkinter import ttk
from typing import Any

_TITLES = {"open": "Open", "open-many": "Open Files", "save": "Save As", "folder": "Select Folder"}
_OK_TEXT = {"open": "Open", "open-many": "Open", "save": "Save", "folder": "Select Folder"}

_P = {
    "bg": "#1e1f22",
    "surface": "#26272b",
    "hover": "#33343a",
    "border": "#3a3b40",
    "text": "#e6e7ea",
    "text_secondary": "#9a9ba3",
    "accent": "#6c8cff",
    "accent_hover": "#7d9aff",
    "accent_pressed": "#5a78e8",
    "selection": "#3a4470",
}


def _fmt_size(size: int) -> str:
    """Human-readable file size (``0 B`` / ``1.5 KB`` / ``3.0 MB`` ...)."""
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} PB"


def _fmt_time(timestamp: float) -> str:
    """File mtime as ``YYYY-MM-DD HH:MM`` (local time)."""
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))


def _matches(name: str, patterns: list[str] | None) -> bool:
    """True when *name* matches any glob in *patterns* (None / empty
    matches everything — the "All files" filter).  Case-insensitive, so
    ``*.jpg`` also shows ``.JPG`` (macOS/Windows filesystems don't
    distinguish)."""
    if not patterns:
        return True
    folded = name.casefold()
    return any(fnmatch.fnmatch(folded, pattern.casefold()) for pattern in patterns)


def _list_entries(path: str, patterns: list[str] | None, *, dirs_only: bool = False) -> list[tuple[str, bool]]:
    """``(name, is_dir)`` entries of *path*: folders first, then files,
    each case-insensitively sorted.  *patterns* filter the files (never
    the folders); *dirs_only* hides files entirely (folder picker).
    Raises ``OSError`` for unreadable paths — callers surface that."""
    names = os.listdir(path)
    dirs: list[str] = []
    files: list[str] = []
    for name in names:
        if os.path.isdir(os.path.join(path, name)):
            dirs.append(name)
        elif not dirs_only and _matches(name, patterns):
            files.append(name)
    key = str.casefold
    return [(name, True) for name in sorted(dirs, key=key)] + [(name, False) for name in sorted(files, key=key)]


class _FileDialog:
    """Self-drawn modal file picker running on a bare Tk root.

    ``result`` keeps the old sentinels so the parent-side normalization
    is untouched: ``""`` on cancel, a ``str`` path for a single pick, a
    ``tuple[str, ...]`` for multi-pick (possibly empty).  Construction
    blocks until the user picks or cancels (grab + wait_window).
    """

    def __init__(self, root: tk.Tk, kind: str, options: dict[str, Any]) -> None:
        self.root = root
        self.kind = kind
        self.options = options
        self.result: str | tuple[str, ...] = ""
        self._rows: list[tuple[str, bool]] = []

        self._cwd = os.path.abspath(os.path.expanduser(options.get("initialdir") or os.getcwd()))
        self._filetypes = list(options.get("filetypes") or [])
        self._filter_names = ["All files (*.*)"] + [label for label, _ in self._filetypes]
        if self._filetypes:
            self._patterns = self._filetypes[0][1].split()
        else:
            self._patterns = []

        root.configure(bg=_P["bg"])
        root.title(str(options.get("title") or _TITLES[kind]))
        root.geometry("660x460")
        root.minsize(480, 320)
        root.protocol("WM_DELETE_WINDOW", self._cancel)
        root.bind("<Escape>", self._cancel)

        self._style()
        self._build()
        self._refresh()
        if kind == "save":
            self._name.focus_set()
        else:
            self._tree.focus_set()
        self._modal()

    # ---- construction ----

    @staticmethod
    def _style() -> None:
        """Dark theme on the clam base (shipped with Tk everywhere)."""
        p = _P
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=p["bg"], foreground=p["text"])
        style.configure("TFrame", background=p["bg"])
        style.configure("TLabel", background=p["bg"], foreground=p["text"])
        style.configure("Secondary.TLabel", background=p["bg"], foreground=p["text_secondary"])
        style.configure(
            "TButton",
            background=p["surface"],
            foreground=p["text"],
            bordercolor=p["border"],
            borderwidth=1,
            padding=(14, 7),
            relief="flat",
        )
        style.map("TButton", background=[("pressed", p["hover"]), ("active", p["hover"])])
        style.configure(
            "Accent.TButton",
            background=p["accent"],
            foreground="#ffffff",
            bordercolor=p["accent"],
            borderwidth=1,
            padding=(14, 7),
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", p["accent_pressed"]), ("active", p["accent_hover"])],
        )
        style.configure(
            "Treeview",
            background=p["surface"],
            fieldbackground=p["surface"],
            foreground=p["text"],
            bordercolor=p["border"],
            rowheight=28,
        )
        style.map("Treeview", background=[("selected", p["selection"])])
        style.configure(
            "Treeview.Heading",
            background=p["bg"],
            foreground=p["text_secondary"],
            bordercolor=p["border"],
            relief="flat",
            padding=(6, 4),
        )
        style.map("Treeview.Heading", background=[("active", p["surface"])])
        style.configure(
            "TEntry",
            fieldbackground=p["surface"],
            foreground=p["text"],
            bordercolor=p["border"],
            insertcolor=p["text"],
            padding=(6, 4),
        )
        style.configure(
            "TCombobox",
            fieldbackground=p["surface"],
            background=p["surface"],
            foreground=p["text"],
            bordercolor=p["border"],
            arrowcolor=p["text_secondary"],
            padding=(6, 4),
        )
        style.map("TCombobox", fieldbackground=[("readonly", p["surface"])])
        style.configure(
            "Vertical.TScrollbar",
            background=p["surface"],
            troughcolor=p["bg"],
            bordercolor=p["bg"],
            arrowcolor=p["text_secondary"],
        )

    def _build(self) -> None:
        bar = ttk.Frame(self.root, padding=(12, 12, 12, 0))
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        ttk.Button(bar, text="↑", width=3, command=self._up).grid(row=0, column=0)
        self._path_var = tk.StringVar(value=self._cwd)
        path = ttk.Entry(bar, textvariable=self._path_var)
        path.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        path.bind("<Return>", self._on_path_enter)

        body = ttk.Frame(self.root, padding=(12, 8, 12, 0))
        body.grid(row=1, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            body,
            columns=("name", "size", "modified"),
            show="headings",
            selectmode="extended" if self.kind == "open-many" else "browse",
        )
        for col, text, anchor, width in (
            ("name", "Name", "w", 300),
            ("size", "Size", "e", 90),
            ("modified", "Modified", "w", 140),
        ):
            self._tree.heading(col, text=text, anchor=anchor)
            self._tree.column(col, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<Double-1>", self._on_double)
        self._tree.bind("<Return>", self._on_tree_enter)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        bottom = ttk.Frame(self.root, padding=(12, 8, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(1, weight=1)

        row = 0
        if self.kind != "folder":
            ttk.Label(bottom, text="Filter", style="Secondary.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 8))
            self._filter_var = tk.StringVar(value=self._filter_names[1] if self._filetypes else self._filter_names[0])
            self._filter = ttk.Combobox(
                bottom, textvariable=self._filter_var, values=self._filter_names, state="readonly", width=26
            )
            self._filter.grid(row=row, column=1, sticky="w")
            self._filter.bind("<<ComboboxSelected>>", self._on_filter)
            row += 1

        if self.kind != "folder":
            ttk.Label(bottom, text="Name", style="Secondary.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 8))
            self._name_var = tk.StringVar(value=self.options.get("initialfile") or "")
            self._name = ttk.Entry(bottom, textvariable=self._name_var)
            self._name.grid(row=row, column=1, sticky="ew")
            self._name.bind("<Return>", self._on_name_enter)
            row += 1

        self._status_var = tk.StringVar()
        self._status = ttk.Label(bottom, textvariable=self._status_var, style="Secondary.TLabel")
        self._status.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        row += 1

        buttons = ttk.Frame(bottom)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right", padx=(8, 0))
        self._ok = ttk.Button(buttons, text=_OK_TEXT[self.kind], style="Accent.TButton", command=self._accept)
        self._ok.pack(side="right")

    # ---- navigation ----

    def _cd(self, path: str) -> None:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            self._status_var.set("not a folder")
            return
        self._cwd = path
        self._refresh()

    def _up(self) -> None:
        parent = os.path.dirname(self._cwd)
        if parent != self._cwd:
            self._cd(parent)

    def _on_path_enter(self, _event=None) -> None:
        self._cd(self._path_var.get().strip() or self._cwd)

    def _on_filter(self, _event=None) -> None:
        label = self._filter_var.get()
        self._patterns = []
        for ft_label, patterns in self._filetypes:
            if ft_label == label:
                self._patterns = patterns.split()
                break
        self._refresh()

    def _refresh(self) -> None:
        self._path_var.set(self._cwd)
        self._tree.delete(*self._tree.get_children())
        try:
            self._rows = _list_entries(self._cwd, self._patterns, dirs_only=self.kind == "folder")
        except OSError:
            self._status_var.set("cannot read this folder")
            self._rows = []
        for i, (name, is_dir) in enumerate(self._rows):
            full = os.path.join(self._cwd, name)
            size, modified = "", ""
            if not is_dir:
                try:
                    stat = os.stat(full)
                    size, modified = _fmt_size(stat.st_size), _fmt_time(stat.st_mtime)
                except OSError:
                    pass
            self._tree.insert("", "end", iid=str(i), values=(f"{name}/" if is_dir else name, size, modified))
        self._status_var.set("")

    # ---- picking ----

    def _accept(self) -> None:
        if self.kind == "folder":
            self.result = self._cwd
            self.root.destroy()
            return
        if self.kind == "save":
            name = self._name_var.get().strip()
            if not name:
                self._status_var.set("enter a file name")
                return
            full = os.path.join(self._cwd, name)
            if os.path.isdir(full):
                self._cd(full)
                return
            self.result = full
            self.root.destroy()
            return
        # open / open-many
        selection = self._tree.selection()
        if not selection:
            self._status_var.set("select a file")
            return
        if self.kind == "open-many":
            picked = tuple(
                os.path.join(self._cwd, self._rows[int(iid)][0]) for iid in selection if not self._rows[int(iid)][1]
            )
            if not picked:
                self._status_var.set("select at least one file")
                return
            self.result = picked
            self.root.destroy()
            return
        name, is_dir = self._rows[int(selection[0])]
        if is_dir:
            self._cd(os.path.join(self._cwd, name))
        else:
            self.result = os.path.join(self._cwd, name)
            self.root.destroy()

    def _cancel(self, _event=None) -> None:
        self.result = ""
        self.root.destroy()

    def _on_double(self, _event) -> None:
        iid = self._tree.focus()
        if not iid:
            return
        name, is_dir = self._rows[int(iid)]
        if is_dir:
            self._cd(os.path.join(self._cwd, name))
        else:
            self.result = os.path.join(self._cwd, name)
            self.root.destroy()

    def _on_tree_enter(self, _event=None) -> None:
        if self.kind == "save":
            self._accept()
            return
        selection = self._tree.selection()
        if not selection:
            return
        if self.kind == "open-many":
            self._accept()
            return
        name, is_dir = self._rows[int(selection[0])]
        if is_dir:
            self._cd(os.path.join(self._cwd, name))
        else:
            self._accept()

    def _on_select(self, _event=None) -> None:
        if self.kind != "open":
            return
        selection = self._tree.selection()
        if not selection:
            return
        name, is_dir = self._rows[int(selection[0])]
        self._name_var.set("" if is_dir else name)

    def _on_name_enter(self, _event=None) -> None:
        if self.kind == "save":
            self._accept()
            return
        name = self._name_var.get().strip()
        if not name:
            return
        full = os.path.join(self._cwd, name)
        if os.path.isdir(full):
            self._cd(full)
        elif os.path.isfile(full):
            self.result = full
            self.root.destroy()
        else:
            self._status_var.set("no such file or folder")

    def _modal(self) -> None:
        self.root.deiconify()
        self.root.lift()
        with contextlib.suppress(tk.TclError):
            self.root.grab_set()
        self.root.wait_window()


def _dispatch(root: Any, request: dict[str, Any], *, dialog_cls: Any = _FileDialog) -> str | tuple[str, ...]:
    """Route *request* to the file picker and return its result.

    Pure — *root* may be a fake and *dialog_cls* a stand-in, so tests can
    exercise the routing without a display.
    """
    kind = request["kind"]
    if kind not in _TITLES:
        raise ValueError(f"unknown dialog kind: {kind!r}")
    options = {key: value for key, value in request.items() if key != "kind" and value is not None}
    return dialog_cls(root, kind, options).result


def dialog_main(conn: Any, request: dict[str, Any]) -> None:
    """Child-process entry point.

    *conn* is the child's end of a one-way ``Pipe(duplex=False)``;
    *request* is the typed request dict (kind + optional options)
    delivered by ``multiprocessing`` pickling.  Always replies exactly
    once — ``("ok", result)`` or ``("error", "Type: message")`` — then
    closes the pipe.
    """
    try:
        root = tk.Tk()
        try:
            root.withdraw()
            result = _dispatch(root, request)
        finally:
            root.destroy()
        conn.send(("ok", result))
    except Exception as exc:
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        with contextlib.suppress(Exception):
            conn.close()
