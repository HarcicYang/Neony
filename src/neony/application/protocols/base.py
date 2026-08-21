"""Custom protocol core — types, the ``@protocol`` decorator, and the
internal ``neony://`` dispatcher.

Applications declare handlers with :func:`protocol` and hand them (or
instances of classes with decorated methods) to ``launch(...)`` /
``NeonApplication(...)`` via ``protocols=[...]``.  At ``run()`` time the
collection is resolved into a single ``key → handler`` mapping served
under **one** webview scheme::

    neony://<key>/<path>

The *key* becomes the URL authority (so it must be lowercase — browsers
normalize hosts); the payload travels in the path, percent-decoded
before it reaches the handler as :attr:`Request.path`.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import re
from collections.abc import Callable, Sequence
from typing import Any, TypeVar, cast
from urllib.parse import unquote, urlparse

from lumiview.serve.base import Serve
from pydantic import BaseModel, ConfigDict, Field

log = logging.getLogger("neony.protocols")

_PROTOCOL_KEY = "__neony_protocol_key__"

# The key becomes the neony:// URL authority.  Browsers normalize hosts
# to lowercase, so only lowercase keys are accepted — anything else
# would route unpredictably.
_KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def _check_key(key: str) -> str:
    """Validate a protocol key and return it."""
    if not isinstance(key, str) or not _KEY_RE.match(key):
        raise ValueError(
            f"Invalid protocol key: {key!r} — must match ^[a-z][a-z0-9-]*$ "
            "(the key is the neony:// URL authority, which is normalized "
            "to lowercase)"
        )
    return key


# ---- request / response ----------------------------------------------------


class Request(BaseModel):
    """A request that arrived on a ``neony://<key>/…`` URL.

    Attributes:
        key: The protocol key that matched (the URL authority).
        path: The URL path **after** the key, percent-decoded —
            ``neony://local/home/u/x.mp3`` yields ``"/home/u/x.mp3"``.
        method: HTTP method, usually ``"GET"`` or ``"HEAD"``.
        url: The original, still percent-encoded URL.
        query: Raw query string without the ``?`` (empty if absent).
        headers: Request headers; repeated names are joined with ``", "``.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    path: str
    method: str = "GET"
    url: str = ""
    query: str = ""
    headers: dict[str, str] = Field(default_factory=dict)

    def header(self, name: str, default: str = "") -> str:
        """Case-insensitive header lookup (``request.header("Range")``)."""
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return default


class Response(BaseModel):
    """A handler's reply — status, headers, and a bytes body.

    Handlers return one per request; the framework forwards it to the
    webview exactly once.  Instances are frozen after construction.
    """

    model_config = ConfigDict(frozen=True)

    status: int = 200
    headers: dict[str, str] = Field(default_factory=dict)
    body: bytes = b""

    @classmethod
    def text(cls, s: str, *, status: int = 200) -> Response:
        """A ``text/plain; charset=utf-8`` response."""
        return cls(
            status=status,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=s.encode("utf-8"),
        )

    @classmethod
    def json(cls, obj: Any, *, status: int = 200) -> Response:
        """An ``application/json`` response (UTF-8, non-ASCII kept verbatim)."""
        return cls(
            status=status,
            headers={"Content-Type": "application/json"},
            body=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
        )


# ---- the decorator ---------------------------------------------------------


_F = TypeVar("_F", bound="Callable[..., Any]")


def protocol(key: str) -> Callable[[_F], _F]:
    """Declare a function or method as the handler for ``neony://<key>/…``.

    Returns a transparent ``functools.wraps`` wrapper carrying the key as
    function metadata, so decorating a **method** keeps normal binding —
    ``instance.handle(request)`` works exactly like the undecorated
    method, and state lives in ``self``::

        @protocol("qr")
        def qr_codes(request: Request) -> Response: ...

        class Avatars:
            @protocol("avatar")
            async def handle(self, request: Request) -> Response: ...

        avatars = Avatars(db)                      # state via self
        launch(page, protocols=[qr_codes, avatars])

    Sync handlers run on the app thread pool; ``async def`` handlers run
    on the app event loop.  Keys must match ``^[a-z][a-z0-9-]*$``.
    """
    _check_key(key)

    def deco(fn: _F) -> _F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await fn(*args, **kwargs)

        else:

            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return fn(*args, **kwargs)

        setattr(wrapper, _PROTOCOL_KEY, key)
        # Identity typing: the decorated callable keeps its own signature
        # (async stays awaitable, sync stays sync).
        return cast(_F, wrapper)

    return deco


# ---- collection ------------------------------------------------------------


def collect_protocol_handlers(entries: Sequence[Any]) -> dict[str, Callable[..., Response]]:
    """Resolve ``protocols=[...]`` entries into a ``key → handler`` map.

    Accepted entries:

    - callables decorated with :func:`protocol` (module-level functions,
      bound methods, ``functools.partial`` objects, …);
    - instances of classes with ``@protocol``-decorated methods — every
      decorated method found on the instance's MRO is bound to the
      instance and registered under its key.

    Duplicate keys raise :class:`ValueError`; an entry carrying no
    decoration at all raises :class:`TypeError`.
    """
    handlers: dict[str, Callable[..., Response]] = {}

    def add(key: str, fn: Callable[..., Response]) -> None:
        if key in handlers:
            raise ValueError(f"Duplicate protocol key: {key!r}")
        handlers[key] = fn

    for entry in entries:
        key = getattr(entry, _PROTOCOL_KEY, None)
        if isinstance(key, str):
            add(key, entry)
            continue
        bound_any = False
        for klass in type(entry).__mro__:
            for attr in vars(klass).values():
                marker = getattr(attr, _PROTOCOL_KEY, None)
                if isinstance(marker, str):
                    add(marker, functools.partial(attr, entry))
                    bound_any = True
        if not bound_any:
            raise TypeError(
                f"{entry!r} carries no @protocol declaration — decorate the "
                "callable itself, or pass an instance of a class whose "
                "methods are decorated"
            )
    return handlers


# ---- internal dispatcher ---------------------------------------------------


def _merge_headers(raw: list[tuple[str, str]]) -> dict[str, str]:
    """Collapse repeated header names into comma-joined values."""
    merged: dict[str, str] = {}
    for name, value in raw:
        merged[name] = f"{merged[name]}, {value}" if name in merged else value
    return merged


class NeonyProtocolDispatch(Serve):
    """Internal bridge: one webview scheme (``neony``), routed by authority.

    This is what gets passed to LumiView's ``Window.create(source=…)``.
    It parses ``neony://<key>/<path>``, looks up the handler, converts
    the transport request into a Neony :class:`Request`, and dispatches
    sync handlers to the app thread pool / async handlers to the app
    loop (the same scheduling LumiView uses for its own ``Handler``).
    """

    def __init__(self, handlers: dict[str, Callable[..., Response]]) -> None:
        super().__init__(scheme="neony")
        self._handlers = handlers

    def __call__(self, request: Any, respond: Callable[[int, list[tuple[str, str]], bytes], None]) -> None:
        """Handle one transport request (*request* is LumiView's Request)."""
        parsed = urlparse(request.url)
        key = parsed.netloc.lower()
        handler = self._handlers.get(key)
        if handler is None:
            respond(404, [("Content-Type", "text/plain")], b"Not Found")
            return
        neony_request = Request(
            key=key,
            path=unquote(parsed.path or "/"),
            method=request.method,
            url=request.url,
            query=request.query,
            headers=_merge_headers(list(request.headers)),
            body=request.body,
        )
        self._dispatch(handler, neony_request, respond)

    def _dispatch(
        self,
        handler: Callable[..., Response],
        request: Request,
        respond: Callable[[int, list[tuple[str, str]], bytes], None],
    ) -> None:
        """Schedule *handler* off the webview callback thread."""
        from lumiview.app import App
        from lumiview.task import run_async

        app = App.get()
        loop = app._async_loop
        if loop is None:
            respond(500, [("Content-Type", "text/plain")], b"App not running")
            return

        async def _run() -> None:
            try:
                result = await run_async(handler, request, pool=app._threadpool)
                headers = dict(result.headers)
                # A page loaded from the in-memory document has an opaque
                # origin.  Allow it to fetch protocol resources so the JS
                # media adapter can hand custom-scheme bytes to Blob URLs.
                headers.setdefault("Access-Control-Allow-Origin", "*")
                headers.setdefault("Access-Control-Expose-Headers", "*")
                respond(result.status, list(headers.items()), result.body)
            except Exception:
                log.exception("Protocol handler %r raised", request.key)
                respond(500, [("Content-Type", "text/plain")], b"Internal Server Error")

        asyncio.run_coroutine_threadsafe(_run(), loop)
