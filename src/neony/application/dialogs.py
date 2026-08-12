"""System-native file dialogs — the app-facing seam.

``show_dialog`` shells out to the platform's own picker (zenity on
Linux, osascript on macOS, PowerShell on Windows, tkinter fallback —
see :mod:`neony._dialog_worker`) inside an executor thread so the
asyncio loop never blocks while the dialog is up.  The worker's raw
sentinels (``""`` / empty tuple) are mapped to Neony's public shapes
(``None`` / ``[]``) here.
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any

from neony import _dialog_worker as worker

_KINDS = ("open", "open-many", "save", "folder")


def _filetypes(filetypes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Pass a user ``filetypes`` list through in the exact shape
    (``(label, "*.png *.jpg")``) — the seam where future normalization
    would live."""
    return [(label, patterns) for label, patterns in filetypes]


def _normalize(kind: str, payload: Any) -> str | list[str] | None:
    """Map the picker's raw sentinels (``""`` / empty tuple) to Neony's
    ``None`` / ``[]``."""
    if kind == "open-many":
        return list(payload) if payload else []
    return payload or None  # "" (cancel) → None


def _validate_kind(kind: str) -> None:
    """Reject unknown dialog kinds early (before any dialog opens)."""
    if kind not in _KINDS:
        raise ValueError(f"unknown dialog kind: {kind!r} (expected one of {_KINDS})")


async def show_dialog(
    kind: str,
    *,
    title: str = "Open",
    default_dir: str | None = None,
    default_name: str | None = None,
    filetypes: list[tuple[str, str]] | None = None,
) -> str | list[str] | None:
    """Show the system-native dialog for *kind* and return the result.

    The blocking platform call runs in an executor thread, so the
    event loop keeps serving the rest of the app while the dialog is
    up.  Returns ``None`` on cancel (``[]`` for ``open-many``) and on
    any platform failure — never raises.
    """
    _validate_kind(kind)
    loop = asyncio.get_running_loop()
    if kind in ("open", "open-many"):
        payload = await loop.run_in_executor(
            None,
            partial(worker._open_sync, kind, title=title, default_dir=default_dir, filetypes=filetypes),
        )
    elif kind == "save":
        payload = await loop.run_in_executor(
            None,
            partial(
                worker._save_sync,
                title=title,
                default_dir=default_dir,
                default_name=default_name,
                filetypes=filetypes,
            ),
        )
    else:  # folder
        payload = await loop.run_in_executor(None, partial(worker._folder_sync, title=title, default_dir=default_dir))
    return _normalize(kind, payload)
