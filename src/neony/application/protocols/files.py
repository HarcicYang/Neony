"""Built-in local file protocol — ``neony://local/<absolute-path>``.

A transparent file server: the URL path *is* the filesystem path, and
the handler reads exactly what the webview asked for.  There is no path
policy (no root allow-list, no dotfile rules) — a Neony page is trusted
application content, the same trust level as the app itself.

What it does provide is the serving semantics media playback needs:

- **Range** requests (``bytes=a-b`` / ``bytes=a-`` / ``bytes=-n``) with
  ``206 Partial Content`` — seeking in ``<video>``/``<audio>`` depends
  on this; unsatisfiable ranges get ``416``, syntactically invalid or
  multi-range requests are ignored (tolerated as a full ``200``).
- **HEAD** — same headers, empty body.
- **MIME** guessing with an ``application/octet-stream`` fallback.
- **Caching hints** — ``ETag``, ``Last-Modified``, ``Accept-Ranges``.

Build URLs for it with :func:`neony.application.urls.local_url`.
"""

from __future__ import annotations

import email.utils
import mimetypes
import stat as stat_module
from pathlib import Path
from typing import Any

from neony.application.protocols.base import Request, Response, protocol

mimetypes.init()

# Sentinel: a syntactically valid Range that can never be satisfied.
_UNSATISFIABLE = object()


def _strip_drive_slash(path: str) -> str:
    """Drop the slash urlparse keeps before a Windows drive letter.

    ``neony://local/C:/x.mp3`` parses to path ``"/C:/x.mp3"``; ``Path``
    needs ``"C:/x.mp3"``.  POSIX paths never match the shape.
    """
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        return path[1:]
    return path


def _parse_range(value: str, size: int) -> tuple[int, int] | Any:
    """Resolve a ``Range`` header against a body of *size* bytes.

    Returns an inclusive ``(start, end)``, :data:`_UNSATISFIABLE` for a
    valid-but-impossible range (→ 416), or ``None`` when the header is
    absent / unsupported / malformed (→ serve the full body with 200).
    """
    if not value:
        return None
    value = value.strip()
    if not value.startswith("bytes="):
        return None
    spec = value[len("bytes=") :].strip()
    if "," in spec:  # multi-range: not supported → tolerant full response
        return None
    first, sep, last = spec.partition("-")
    first, last = first.strip(), last.strip()
    if not sep:
        return None
    if first == "":  # suffix form: the final N bytes
        if not last.isdigit():
            return None
        n = int(last)
        if n == 0 or size == 0:
            return _UNSATISFIABLE
        return max(0, size - n), size - 1
    if not first.isdigit():
        return None
    start = int(first)
    if start >= size:
        return _UNSATISFIABLE
    if last == "":
        end = size - 1
    elif last.isdigit():
        end = min(int(last), size - 1)
        if end < start:
            return None
    else:
        return None
    return start, end


@protocol("local")
def local_files(request: Request) -> Response:
    """Serve the file named by ``request.path``.

    The path is used verbatim (it is absolute by construction — see
    :func:`neony.application.urls.local_url`).  Missing files and
    directories answer ``404``; reads happen on the thread pool, so
    large media never blocks the UI loop.
    """
    target = Path(_strip_drive_slash(request.path))
    try:
        st = target.stat()
    except OSError:
        return Response(status=404)
    if not stat_module.S_ISREG(st.st_mode):
        return Response(status=404)

    size = st.st_size
    mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    headers: dict[str, str] = {
        "Content-Type": mime,
        "ETag": f'"{st.st_mtime_ns:x}-{size:x}"',
        "Last-Modified": email.utils.formatdate(st.st_mtime, usegmt=True),
        "Accept-Ranges": "bytes",
    }

    parsed = _parse_range(request.header("Range"), size)
    if parsed is _UNSATISFIABLE:
        return Response(
            status=416,
            headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"},
        )
    if parsed is None:
        start, end, status = 0, size - 1, 200
    else:
        start, end = parsed
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    length = end - start + 1
    try:
        with target.open("rb") as fh:
            fh.seek(start)
            data = fh.read(length)
    except OSError:
        return Response(status=404)
    if len(data) < length:  # file shrank between stat() and read()
        headers["Content-Range"] = f"bytes {start}-{start + len(data) - 1}/{len(data)}"

    headers["Content-Length"] = str(len(data))
    return Response(status=status, headers=headers, body=b"" if request.method == "HEAD" else data)
