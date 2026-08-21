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
import re
from pathlib import Path
from urllib.parse import quote

# Same shape as the protocol key check in neony.application.protocols —
# the key becomes the neony:// URL authority, which is lowercase-normalized.
_KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")


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


def protocol_url(key: str, value: str) -> str:
    """Build a ``neony://<key>/<value>`` URL for a custom protocol.

    The *key* must match ``^[a-z][a-z0-9-]*$`` (it becomes the URL
    authority, which browsers lowercase); a leading ``/`` on *value* is
    dropped so the payload always lands in the path component::

        >>> protocol_url("qr", "u/123456")
        'neony://qr/u/123456'

    Spaces and non-ASCII characters are percent-encoded; the handler
    receives them decoded via :attr:`Request.path <neony.application.protocols.Request.path>`.
    """
    if not _KEY_RE.match(key or ""):
        raise ValueError(f"Invalid protocol key: {key!r} — must match ^[a-z][a-z0-9-]*$")
    return f"neony://{key}/{quote(value.lstrip('/'), safe='/')}"


def local_url(path: str | Path) -> str:
    """Convert a filesystem path to a ``neony://local/`` URL.

    The custom-scheme twin of :func:`file_url`: same input (absolute
    path, ``~`` expansion, relative paths resolved against the CWD) and
    identical percent-encoding, but served through Neony's built-in
    ``local_files`` protocol instead of ``file://`` — which WebKit
    blocks for subresources when the page is not itself a ``file://``
    document.  This is what makes local media playback work::

        >>> local_url("/home/user/song.mp3")
        'neony://local/home/user/song.mp3'

    Requires ``local_files`` to be registered:
    ``launch(page, protocols=[local_files])``.
    """
    p = Path(path).expanduser().resolve()
    # as_uri() → "file:///home/u/x" / "file:///C:/Users/x"; keep the
    # percent-encoding, swap the scheme+authority for "neony://local".
    return f"neony://local/{p.as_uri()[len('file:///') :]}"
