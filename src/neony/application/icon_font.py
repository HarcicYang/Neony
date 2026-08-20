"""Self-hosted CSS for Neony's built-in icon font."""

from __future__ import annotations

import base64
from functools import cache
from importlib.resources import files

_FONT_FAMILY = "Neony Material Symbols Rounded"
_FONT_RESOURCE = "assets/icons/material-symbols-rounded.woff2"


@cache
def css() -> str:
    """Return the bundled icon ``@font-face`` rule as a portable data URL.

    The WebView may not have permission to load files from an installed wheel's
    location. Embedding the WOFF2 data avoids that platform difference and is
    injected once per window by :class:`NeonApplication`.
    """
    payload = files("neony").joinpath(_FONT_RESOURCE).read_bytes()
    encoded = base64.b64encode(payload).decode("ascii")
    return (
        "@font-face{font-family:'Neony Material Symbols Rounded';"
        "font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{encoded}) format('woff2');"
        "font-display:block;}"
    )
