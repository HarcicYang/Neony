"""Native file dialogs — one-shot tkinter subprocess, typed pipe protocol.

Each call spawns a short-lived subprocess that shows a *self-drawn* file
picker (ttk dark theme — the platform ``tkinter.filedialog`` is dated and
can't be restyled), so the app never touches a second UI toolkit's main
loop and never blocks on the modal.  The channel is a typed
``multiprocessing`` pipe — no stdout/JSON parsing:

* the request dict rides the ``Process`` ``args`` (pickled);
* the result returns on a one-way ``Pipe(duplex=False)`` as
  ``("ok", result)`` or ``("error", "Type: message")``.

The parent awaits the reply with ``asyncio.to_thread`` so the event loop
stays responsive while the dialog is up.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import multiprocessing
import sys
from typing import Any

from neony._dialog_worker import dialog_main as _dialog_main

_log = logging.getLogger("neony.dialogs")

_KINDS = ("open", "open-many", "save", "folder")


def _ctx() -> Any:
    """Process context: fork where available (fast, no ``__main__``
    re-import, so guard-less demo scripts keep working), spawn on
    Windows (the only option there)."""
    return multiprocessing.get_context("fork" if sys.platform != "win32" else "spawn")


def _filetypes(filetypes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Pass a user ``filetypes`` list through in tkinter's exact shape
    (``(label, "*.png *.jpg")``) — the seam where future normalization
    would live."""
    return [(label, patterns) for label, patterns in filetypes]


def _request(
    kind: str,
    *,
    title: str | None = None,
    default_dir: str | None = None,
    default_name: str | None = None,
    filetypes: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the pickled request dict — None fields are dropped."""
    request: dict[str, Any] = {"kind": kind}
    if title is not None:
        request["title"] = title
    if default_dir is not None:
        request["initialdir"] = default_dir
    if default_name is not None:
        request["initialfile"] = default_name
    if filetypes:
        request["filetypes"] = _filetypes(filetypes)
    return request


def _normalize(kind: str, payload: Any) -> str | list[str] | None:
    """Map tkinter's cancel sentinels (``""`` / empty tuple) to Neony's
    ``None`` / ``[]``."""
    if kind == "open-many":
        return list(payload) if payload else []
    return payload or None  # "" (cancel) → None


async def _run(request: dict[str, Any]) -> str | list[str] | None:
    """Launch one subprocess, await its reply, and map it to a Neony
    result.  Every failure mode returns ``None``/``[]`` deterministically
    (cancel, child error, child crash, start failure)."""
    ctx = _ctx()
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_dialog_main, args=(child_conn, request), daemon=True)
    try:
        proc.start()
    except Exception:
        _log.exception("file dialog subprocess failed to start")
        parent_conn.close()
        return None
    # The parent's copy of the write end must close after fork/spawn, or
    # the read end would only see EOF after the parent exits (the child's
    # close alone isn't enough while this handle stays open).
    with contextlib.suppress(Exception):
        child_conn.close()
    try:
        try:
            status, payload = await asyncio.to_thread(parent_conn.recv)
        except (EOFError, OSError) as exc:
            _log.error("file dialog subprocess died before replying: %s", exc)
            return None
    finally:
        parent_conn.close()
    if status == "error":
        _log.error("file dialog failed: %s", payload)
        return None
    return _normalize(request["kind"], payload)


async def show_dialog(
    kind: str,
    *,
    title: str | None = None,
    default_dir: str | None = None,
    default_name: str | None = None,
    filetypes: list[tuple[str, str]] | None = None,
) -> str | list[str] | None:
    """Show a native file dialog in a one-shot subprocess.

    *kind* is one of ``"open"`` (single file → ``str``), ``"open-many"``
    (multiple files → ``list[str]``), ``"save"`` or ``"folder"``.
    Returns the chosen path(s); ``None`` on cancel or failure, ``[]`` for
    a cancelled multi-select.  *default_dir* seeds the starting folder,
    *default_name* pre-fills the save field, *filetypes* filters the
    picker like ``[("PNG images", "*.png"), ("All files", "*.*")]``.
    """
    if kind not in _KINDS:
        raise ValueError(f"unknown dialog kind: {kind!r} (expected one of {_KINDS})")
    return await _run(
        _request(kind, title=title, default_dir=default_dir, default_name=default_name, filetypes=filetypes)
    )
