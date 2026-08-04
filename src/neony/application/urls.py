"""Filesystem path → URL helpers for local resources.

WebViews can't load ``C:\\path\\to\\file`` or ``/home/user/My File.png``
directly — the CSS ``url()`` and HTML ``src`` attributes need a proper
URL.  These two helpers cover the common cases: a ``file://`` URL for
paths the webview can read from disk, and a ``data:`` URL that embeds
the bytes directly (works everywhere, but doubles the transfer size for
binary data).
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path


def file_url(path: str | Path) -> str:
    """Convert a filesystem path to a ``file://`` URL.

    Handles Windows drive letters, spaces, and non-ASCII characters::

        >>> file_url("/home/user/img.png")
        'file:///home/user/img.png'
        >>> file_url("C:\\\\Users\\\\user\\\\my file.png")
        'file:///C:/Users/user/my%20file.png'

    The path is resolved to an absolute one first, so relative paths
    behave deterministically.
    """
    return Path(path).resolve().as_uri()


def data_url(path: str | Path, mime_type: str | None = None) -> str:
    """Convert a file to a base64 ``data:`` URL.

    *mime_type* is guessed from the file extension when omitted
    (``image/png``, ``image/svg+xml``, ...), falling back to
    ``application/octet-stream``::

        >>> data_url("icon.svg")
        'data:image/svg+xml;base64,PHN2Zy...'

    Useful for local images in ``GlassPanel(background=...)``,
    ``TitleBar(icon=...)`` and other URL-backed styles — the bytes are
    embedded, so there is no ``file://`` access to worry about.
    """
    p = Path(path)
    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(str(p))
        mime_type = mime_type or "application/octet-stream"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"
