"""Internal helpers for :class:`~neony.application.app.NeonApplication` —
per-window runtime state (``_Entry``), the built-in keyframes injected
into every window, the style-deferred event set, and the small platform
helpers (native file-drop metadata, ``eval_js`` result decoding,
clipboard-read fallback messaging, the Linux WM_CLASS program name).

Kept in a separate module so :mod:`neony.application.app` can focus on
the application lifecycle, theme injection, rendering, and the window
control surface.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from lumiview import Window, WindowEffect

from neony.dom import DOMElement, KeyFrame, Props
from neony.dom.bridge import Neony

if TYPE_CHECKING:
    from neony.application.page import Page

# Transparent windows get their platform's frosted material applied
# automatically — Acrylic on Windows, Blur on macOS (lumiview's native
# window-background materials; see ``apply_effect``).  Linux is handled
# separately in ``_apply_transparent_effect`` via the Wayland
# ``ext-background-effect-v1`` compositor protocol.
_TRANSPARENT_EFFECTS: dict[str, WindowEffect] = {
    "win32": WindowEffect.Acrylic,
    "darwin": WindowEffect.Blur,
}

# margin:0 — the browser default 8px body margin would leave a white
# ring around the page.  height:100% chain — vh units lag the real
# window size under tiling WMs (e.g. hyprland), percentages follow it.
# box-sizing:border-box — width:100% + padding would overflow the
# window's right edge.
_INITIAL_HTML = (
    "<html><head><style>*,*::before,*::after{box-sizing:border-box}"
    "html,body{height:100%;margin:0;padding:0}"
    "#neony-root{height:100%}</style></head>"
    "<body><div id='neony-root'></div></body></html>"
)


class _Entry:
    """Per-window runtime state: bridge scope, window, DOM tree, and the
    originating Page (for its close handlers)."""

    __slots__ = ("neony", "page", "tree", "window")

    def __init__(self, neony: Neony, tree: DOMElement, page: Page | None = None) -> None:
        self.neony = neony
        self.window: Window | None = None
        self.tree = tree
        self.page = page


# Style-only events: deferred one frame of coalescing so a mouse sweep
# doesn't trigger a full-tree render per event.
_DEFERRED_EVENTS = frozenset(
    {"mouseover", "mouseout", "focus", "blur", "input", "dragover", "dragleave", "pointermove"}
)

# Built-in @keyframes injected into every window (like theme variables),
# so standalone components can reference them by convention name —
# ``Animation(name="neony-rise-in", ...)``.  User-registered keyframes
# with the same name override these (later-wins in ``_inject_keyframes``).
_BUILTIN_KEYFRAMES: list[KeyFrame] = [
    KeyFrame("neony-rise-in")
    .set("0%", Props(opacity=0, transform="translateY(8px)"))
    .set("100%", Props(opacity=1, transform="translateY(0)")),
    # Fade + slide-up appearance — the gallery's section enter
    # animation; Dialog panels play it on open and, reversed, on
    # close.  Same stops as neony-rise-in with a longer duration.
    KeyFrame("fade-slide")
    .set("0%", Props(opacity=0, transform="translateY(8px)"))
    .set("100%", Props(opacity=1, transform="translateY(0)")),
    KeyFrame("neony-fade-in").set("0%", Props(opacity=0)).set("100%", Props(opacity=1)),
    # Sweep for indeterminate progress: a 40%-wide fill translates
    # past the track's overflow-hidden edges (-100% → 300% of its own
    # width) for a left-to-right indeterminate slide.
    KeyFrame("neony-indeterminate")
    .set("0%", Props(transform="translateX(-100%)"))
    .set("100%", Props(transform="translateX(300%)")),
]


def _file_info(path: str) -> dict[str, Any]:
    """One ``drop_files`` entry from a real path: name from the basename,
    size from the filesystem (0 when unreadable), MIME by extension."""
    import mimetypes
    import os

    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    mime, _ = mimetypes.guess_type(path)
    return {"name": os.path.basename(path), "path": path, "size": size, "type": mime or ""}


def _js_result_value(raw: str) -> str:
    """Decode an ``eval_js`` result string.

    wryview passes the WebKitGTK evaluation result through JSON-encoded —
    a JS string arrives quoted (``'"pong"'``) with ``\\u0001``-style
    escapes intact, so string parsing (``partition``, ``startswith``)
    against the raw text fails.  Decode it to the actual value; raw
    (unquoted) results pass through unchanged.
    """
    import json

    text = raw.strip()
    if text.startswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return text


def _clipboard_read_hint(reason: str) -> str:
    """Append the actionable workaround to a clipboard-read rejection.

    WebKitGTK rejects ``navigator.clipboard.readText`` outright (the
    promise's rejection is the only way the read can fail here) — the
    paste event is the supported read path on Linux.  On other backends
    a rejection usually means the user gesture was missing.
    """
    if sys.platform == "linux":
        return (
            " — WebKitGTK rejects programmatic clipboard reads and the "
            "wl-paste/xclip fallback failed (install wl-clipboard or "
            "xclip; the window must be focused); the reliable path is the "
            "paste event (on_paste → DomEvent.clipboard_text, Ctrl+V)"
        )
    return " — the read was rejected; clipboard-read needs a user gesture (call it from a click handler)"


def _set_linux_app_name(name: str) -> None:
    """Set the GLib program name so the taskbar shows *name* instead of
    ``python3`` (WM_CLASS defaults to ``argv[0]``; lumiview's
    ``App(name=...)`` never reaches it).  ctypes is safe — GLib is
    already linked by tao's GTK backend."""
    if sys.platform != "linux":
        return
    try:
        import ctypes

        glib = ctypes.CDLL("libglib-2.0.so.0")
        glib.g_set_prgname(name.encode())
    except OSError:
        pass  # should never happen on Linux, but don't crash
