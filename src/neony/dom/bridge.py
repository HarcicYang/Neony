"""Patch protocol, diff engine, and the reactive DOM bridge."""

from __future__ import annotations

import asyncio
import logging
import re
import webbrowser
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Annotated, Any, Literal

from lumiview.scope import BridgeContext, InitContext, Plugin
from pydantic import BaseModel, Field

from neony.dom.base import DOMElement
from neony.dom.nodes import NodeDescriptor

if TYPE_CHECKING:
    from lumiview.window import Window

# ---- patch operation models ----


class CreatePatch(BaseModel):
    """Insert a full subtree into *parent* at *index*."""

    op: Literal["create"] = "create"
    key: str
    node: NodeDescriptor
    parent: str | None = None
    index: int | None = None


class RemovePatch(BaseModel):
    """Remove the subtree rooted at *key*."""

    op: Literal["remove"] = "remove"
    key: str


class ReplacePatch(BaseModel):
    """Replace the element *key* with a new subtree (same key, new tag/node)."""

    op: Literal["replace"] = "replace"
    key: str
    node: NodeDescriptor


class ReorderPatch(BaseModel):
    """Reorder children of *parent* to match *ordered_keys*."""

    op: Literal["reorder"] = "reorder"
    parent: str
    ordered_keys: list[str]


class MovePatch(BaseModel):
    """Move element *key* to a new parent / index.

    Cross-parent moves (e.g. a card dragged between two Reorder boards)
    re-parent the SAME element — remove+create would build a fresh node
    that a trailing remove then deletes (blank slot / double render)."""

    op: Literal["move"] = "move"
    key: str
    to_parent: str
    to_index: int | None = None


class UpdateAttrsPatch(BaseModel):
    """Merge attribute changes: set values and/or remove attribute names."""

    op: Literal["update_attrs"] = "update_attrs"
    key: str
    set: dict[str, str] = Field(default_factory=dict)
    remove: list[str] = Field(default_factory=list)


class UpdateStylesPatch(BaseModel):
    """Merge style changes: set CSS properties and/or remove property names."""

    op: Literal["update_styles"] = "update_styles"
    key: str
    set: dict[str, str] = Field(default_factory=dict)
    remove: list[str] = Field(default_factory=list)


class SetTextPatch(BaseModel):
    """Set the text content of an element."""

    op: Literal["set_text"] = "set_text"
    key: str
    text: str


class AppendTextPatch(BaseModel):
    """Append a text chunk to an element's existing text content.

    Emitted when new text is a pure extension of the old text — a
    streaming append only ships the delta instead of the whole string.
    """

    op: Literal["append_text"] = "append_text"
    key: str
    text: str


# ---- discriminated union ----


Patch = Annotated[
    (
        CreatePatch
        | RemovePatch
        | ReplacePatch
        | ReorderPatch
        | MovePatch
        | UpdateAttrsPatch
        | UpdateStylesPatch
        | SetTextPatch
        | AppendTextPatch
    ),
    Field(discriminator="op"),
]


class PatchMessage(BaseModel):
    """One render cycle's worth of DOM changes.

    *rev* is a monotonic counter used by the JS engine to detect
    gaps (missed messages) and request a full resync.  A render with many
    ops is split into *chunks* messages sharing one *rev* and *batch* id;
    the JS engine buffers them and applies the whole batch atomically.
    """

    rev: int = 0
    ops: list[Patch] = Field(default_factory=list)
    batch: str | None = None
    chunk: int = 0
    chunks: int = 1


# ---- diff engine ----


class DiffEngine:
    """Compute a minimal list of :class:`Patch` objects between two DOM trees.

    Trees are compared via their :class:`NodeDescriptor` snapshots so the
    engine never depends on live :class:`DOMElement` instances.
    """

    @staticmethod
    def diff(old: NodeDescriptor | None, new: NodeDescriptor) -> list[Patch]:
        """Compare *old* (``None`` on first render) with *new*, returning
        ordered patches that transform the old DOM into the new one."""
        if old is None:
            return [CreatePatch(key=new.key, node=new)]

        moved = DiffEngine._moved_keys(old, new)
        patches = DiffEngine._diff_node(old, new, moved)
        new_positions = DiffEngine._position_map(new, {}) if moved else {}
        for key in sorted(moved):
            where = new_positions.get(key)
            if where is not None:
                patches.append(MovePatch(key=key, to_parent=where[0], to_index=where[1]))
        # A card moving between boards would otherwise emit CreatePatch
        # (target board, earlier in the tree walk) before RemovePatch
        # (source board); the engine's _create re-registers the key only
        # for the FOLLOWING _remove to delete that fresh element — the
        # card vanishes (direction-dependent).  Removes lead, then moves
        # (which re-parent the SAME element — no flash, no blank slot),
        # then everything else.
        removes = [p for p in patches if isinstance(p, RemovePatch)]
        moves = [p for p in patches if isinstance(p, MovePatch)]
        if removes or moves:
            others = [p for p in patches if not isinstance(p, (RemovePatch, MovePatch))]
            return removes + moves + others
        return patches

    @staticmethod
    def _moved_keys(old: NodeDescriptor, new: NodeDescriptor) -> frozenset[str]:
        """Keys present in BOTH trees under DIFFERENT parents — these are
        cross-container moves (re-parent the same element, never
        remove+create)."""
        old_parents = DiffEngine._parent_map(old, {})
        new_parents = DiffEngine._parent_map(new, {})
        return frozenset(k for k in old_parents if k in new_parents and old_parents[k] != new_parents[k])

    @staticmethod
    def _parent_map(node: NodeDescriptor, acc: dict[str, str]) -> dict[str, str]:
        for c in node.children:
            acc[c.key] = node.key
            DiffEngine._parent_map(c, acc)
        return acc

    @staticmethod
    def _position_map(node: NodeDescriptor, acc: dict[str, tuple[str, int]]) -> dict[str, tuple[str, int]]:
        """Map every key to its ``(parent_key, child_index)`` in one walk."""
        for i, c in enumerate(node.children):
            acc[c.key] = (node.key, i)
            DiffEngine._position_map(c, acc)
        return acc

    @staticmethod
    def _diff_node(
        old: NodeDescriptor,
        new: NodeDescriptor,
        moved: frozenset[str] = frozenset(),
    ) -> list[Patch]:
        patches: list[Patch] = []

        if old.tag != new.tag:
            patches.append(ReplacePatch(key=new.key, node=new))
            return patches

        if old.text != new.text:
            # Pure extension of the previous text (the old state was
            # text-only, so appending is equivalent to replacing) — ship
            # only the delta so streaming appends stay O(chunk).
            if old.text is not None and new.text and new.text.startswith(old.text):
                patches.append(AppendTextPatch(key=new.key, text=new.text[len(old.text) :]))
            else:
                patches.append(SetTextPatch(key=new.key, text=new.text or ""))

        attr_patch = DiffEngine._diff_dict(old.attrs, new.attrs)
        if attr_patch:
            patches.append(UpdateAttrsPatch(key=new.key, set=attr_patch["set"], remove=attr_patch["remove"]))

        style_patch = DiffEngine._diff_dict(old.styles, new.styles)
        if style_patch:
            patches.append(UpdateStylesPatch(key=new.key, set=style_patch["set"], remove=style_patch["remove"]))

        child_patches = DiffEngine._diff_children(old.children, new.children, parent_key=new.key, moved=moved)
        patches.extend(child_patches)

        return patches

    @staticmethod
    def _diff_dict(old_dict: dict[str, str], new_dict: dict[str, str]) -> dict | None:
        """Return ``{"set": {...}, "remove": [...]}`` or ``None`` if identical."""
        set_vals: dict[str, str] = {}
        remove_vals: list[str] = []

        for k, new_v in new_dict.items():
            old_v = old_dict.get(k)
            if old_v != new_v:
                set_vals[k] = new_v

        for k in old_dict:
            if k not in new_dict:
                remove_vals.append(k)

        if not set_vals and not remove_vals:
            return None

        return {"set": set_vals, "remove": remove_vals}

    @staticmethod
    def _diff_children(
        old_children: list[NodeDescriptor],
        new_children: list[NodeDescriptor],
        parent_key: str,
        moved: frozenset[str] = frozenset(),
    ) -> list[Patch]:
        patches: list[Patch] = []

        old_map: dict[str, NodeDescriptor] = {c.key: c for c in old_children}
        new_map: dict[str, NodeDescriptor] = {c.key: c for c in new_children}

        old_keys = [c.key for c in old_children]
        new_keys = [c.key for c in new_children]
        new_index = {k: i for i, k in enumerate(new_keys)}

        # Common keys keep their identity across the diff — the relative
        # order check decides whether a ReorderPatch must follow.
        old_common = [k for k in old_keys if k in new_map]
        new_common = [k for k in new_keys if k in old_map]

        for k in old_keys:
            if k not in new_map and k not in moved:
                patches.append(RemovePatch(key=k))

        for c in new_children:
            if c.key not in old_map and c.key not in moved:
                # Insert at the final position when the common order
                # already matches (pure insert — no ReorderPatch follows);
                # index=None otherwise, letting the trailing ReorderPatch
                # fix the order (avoids index misalignment when the DOM
                # still contains elements that will be removed).
                if old_common == new_common:
                    patches.append(
                        CreatePatch(
                            key=c.key,
                            node=c,
                            parent=parent_key,
                            index=new_index[c.key],
                        )
                    )
                else:
                    patches.append(CreatePatch(key=c.key, node=c, parent=parent_key, index=None))
            elif c.key not in moved:
                patches.extend(DiffEngine._diff_node(old_map[c.key], c, moved))

        # Reorder only when the relative order of common elements changes.
        # Pure append/remove (no reorder) skips this for efficiency.
        if old_common != new_common:
            patches.append(ReorderPatch(parent=parent_key, ordered_keys=new_keys))

        return patches


# ---- dropped-file path backfill ----


def _basename(name: str) -> str:
    """Last path segment, handling both ``/`` and ``\\`` separators
    (WebView2 aliases paths as ``C:\\fakepath\\...``)."""
    return name.replace("\\", "/").rsplit("/", 1)[-1]


def _backfill_drop_paths(
    files: Iterable[dict[str, Any]],
    native_paths: list[str],
) -> list[dict[str, Any]]:
    """Fill empty ``path`` entries in a drop's file list from the paths
    captured by the window's native drag-drop handler.

    ``File.path`` is empty on WebKitGTK ≥ 2.52 and on WKWebView; the
    native handler (tao's ``drag_drop_handler``) is the reliable path
    source there.  Files are matched by base name first; when *no* name
    matched and the counts agree, paths are filled positionally.
    """
    files = [dict(f) for f in files]
    missing = [f for f in files if not (f.get("path") or "").strip()]
    if not missing or not native_paths:
        return files
    remaining = list(native_paths)
    for f in missing:
        for i, p in enumerate(remaining):
            if _basename(p) == _basename(f.get("name") or ""):
                f["path"] = remaining.pop(i)
                break
    if len(files) == len(native_paths) and not any(f.get("path") for f in missing):
        # No base-name match at all (e.g. aliased names) — same counts,
        # fill in drop order.
        for f, p in zip(files, native_paths, strict=True):
            f["path"] = p
    return files


# ---- reactive bridge ----


class Neony(Plugin):
    """Reactive DOM bridge for a LumiView window: serialises the tree,
    diffs against the previous snapshot, and pushes patches to the JS
    engine.  Include via ``Bridge(includes=[neony])``; commands register
    at construction and the engine injects via ``on_init``."""

    def __init__(
        self,
        *,
        name: str = "neony",
        mount_selector: str = "body",
    ) -> None:
        super().__init__(name=name)
        self._mount_selector = mount_selector
        self._win: Window | None = None
        self._snapshot: NodeDescriptor | None = None
        self._last_tree: DOMElement | None = None
        # Per-key snapshot cache: unchanged elements reuse their snapshot (see to_node).
        self._snapshots: dict[str, NodeDescriptor] = {}
        self._rev: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()
        self._handlers: dict[tuple[str | None, str], list[Callable[..., Any]]] = {}
        # key → element, for opt-in bubbling to handler-less descendants.
        self._key_map: dict[str, DOMElement] = {}
        # (key, event_type) pairs pruned from ``_handlers`` by the last
        # structural render; NeonApplication drains this so its idempotent
        # registration set does not keep stale entries either.
        self._discarded_registrations: set[tuple[str, str]] = set()
        # Large render cycles are split into several patch messages so one
        # WebView eval never has to parse a multi-megabyte JSON blob.
        self._patch_chunk_size: int = 1000
        # First mounts bigger than this many nodes are streamed: the root
        # skeleton mounts first, then child subtrees arrive as chunked
        # create patches.
        self._mount_chunk_size: int = 1000
        # Pending deferred render (``render(immediate=False)``), cancelled
        # and replaced on each new request.
        self._render_task: asyncio.Task | None = None
        self._render_debounce: float = 0.016  # ~1 frame at 60fps
        # Real file paths from the window's native drag-drop handler,
        # filled in by ``NeonApplication`` (see ``_make_drag_drop_handler``).
        # Mutated in place on every drag-enter/drop; ``_on_event`` uses it
        # to backfill ``drop_files`` entries whose ``path`` is empty.
        self.native_drop_paths: list[str] = []
        # Protocol handlers (URL authority → handler), assigned by
        # ``NeonApplication.run`` after collection — commands register at
        # construction, but the declarations resolve later.  ``media_read``
        # routes through the same dispatch as webview scheme requests.
        self._protocol_handlers: dict[str, Callable[..., Any]] | None = None

        # Register JS→Python IPC commands on this scope
        self.command(self._on_event, name="event")
        self.command(self._on_resync, name="resync")
        self.command(self._on_ready_ack, name="ready")
        self.command(self._on_paste_files, name="paste_files")
        self.command(self._on_media_read, name="media_read")
        self.command(self._on_open_external, name="open_external")

    # ---- Plugin lifecycle hooks ----

    def on_init(self, ctx: InitContext) -> InitContext:
        """Inject the Neony JavaScript engine into every page."""
        from neony.javascript import ENGINE_SOURCE

        ctx.inject_script += "\n" + ENGINE_SOURCE
        return ctx

    def on_ready(self, window: Window) -> None:
        """Called once per window using this bridge."""
        self._win = window

    # ---- JS → Python commands (called via lumiview.invoke) ----

    async def _on_event(
        self,
        ctx: BridgeContext,
        key: str,
        event_type: str,
        value: Any = None,
        *,
        # Rich payload fields.  Declared explicitly, not via **kwargs:
        # lumiview commands reject varargs/varkwargs at registration and
        # stray payload keys are rejected in strict mode, so every field
        # the JS can send must be a named parameter here.  Forwarded to
        # the registered handlers as DomEvent fields.
        #
        # Numeric fields are ``Any``: lumiview converts payload values
        # with strict type matching (``type(value) is typ``, no unions),
        # and browser coordinates arrive as JSON integers
        # (``clientX: 123``) — ``float`` would reject every mouse event.
        # ``DomEvent``'s pydantic ``float`` fields are the typed surface
        # and coerce ints themselves.
        ctrl_key: bool = False,
        shift_key: bool = False,
        alt_key: bool = False,
        meta_key: bool = False,
        x: Any = None,
        y: Any = None,
        offset_x: Any = None,
        offset_y: Any = None,
        movement_x: Any = None,
        movement_y: Any = None,
        pointer_type: str | None = None,
        # mouseover/mouseout only: the key of the keyed element the
        # pointer moved from/to (None when it came from off-page or an
        # unkeyed part) — components detect enter/leave boundaries.
        related_key: str | None = None,
        # CSS transition / animation events.
        transition_property: str | None = None,
        elapsed_time: Any = None,
        animation_name: str | None = None,
        delta_x: Any = None,
        delta_y: Any = None,
        delta_mode: Any = None,
        # Scroll position (scroll event only).
        scroll_top: Any = None,
        scroll_left: Any = None,
        clipboard_text: str | None = None,
        clipboard_html: str | None = None,
        # IME composition (compositionstart / compositionupdate /
        # compositionend) and ``is_composing`` on input events.
        composition_data: str | None = None,
        is_composing: bool = False,
        # Scroll geometry (scroll event only) — full content size and
        # visible size, so "near bottom" decisions stay in Python.
        scroll_height: Any = None,
        client_height: Any = None,
        scroll_width: Any = None,
        client_width: Any = None,
        # Pasted files (paste event only): list of {name, size, type}.
        # ``Any`` for the same strict-conversion reasons as the numeric
        # fields; DomEvent.paste_files is the typed surface.
        paste_files: Any = None,
        # RichText editor fields (events targeting [data-neony-rich-text]):
        # flat caret position, and image info when the target is an inline
        # image (image_index is a flat position too).
        caret_position: Any = None,
        selection_end: Any = None,
        image_index: Any = None,
        image_src: str | None = None,
        image_alt: str | None = None,
        # In-app drag payload (dragstart / drop only) — the string the
        # source element declared via ``drag_payload``.
        drag_payload: str | None = None,
        # Dropped files: list of {name, path, size, type} dicts from the
        # drop event.  ``Any`` for the same strict-conversion reasons as
        # the numeric fields; DomEvent.drop_files is the typed surface.
        drop_files: Any = None,
        # Media elements (direct-wired Video/Audio events).  Numeric
        # fields are ``Any`` for the same reason as coordinates above —
        # JSON integers must not be rejected by strict float matching.
        media_time: Any = None,
        media_duration: Any = None,
        media_volume: Any = None,
        media_muted: Any = None,
        media_paused: Any = None,
        media_error: Any = None,
    ) -> None:
        """Handle a DOM event from JavaScript.  The event dispatches to
        its own element's handlers, then bubbles to the nearest
        ``bubble_events`` ancestor with a matching handler — even when
        the target handled it, so window-level listeners (page key
        handlers, shortcuts) see keys typed in any input.  Each handler
        runs independently — one raising must not break the chain."""
        # ``File.path`` is empty on WebKitGTK ≥ 2.52 — backfill the
        # native handler's paths (matched by base name) before dispatch.
        if event_type == "drop" and drop_files:
            drop_files = _backfill_drop_paths(drop_files, self.native_drop_paths)
        extra: dict[str, Any] = {
            "ctrl_key": ctrl_key,
            "shift_key": shift_key,
            "alt_key": alt_key,
            "meta_key": meta_key,
            "x": x,
            "y": y,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "movement_x": movement_x,
            "movement_y": movement_y,
            "pointer_type": pointer_type,
            "related_key": related_key,
            "transition_property": transition_property,
            "elapsed_time": elapsed_time,
            "animation_name": animation_name,
            "delta_x": delta_x,
            "delta_y": delta_y,
            "delta_mode": delta_mode,
            "scroll_top": scroll_top,
            "scroll_left": scroll_left,
            "clipboard_text": clipboard_text,
            "clipboard_html": clipboard_html,
            "composition_data": composition_data,
            "is_composing": is_composing,
            "scroll_height": scroll_height,
            "client_height": client_height,
            "scroll_width": scroll_width,
            "client_width": client_width,
            "paste_files": paste_files,
            "caret_position": caret_position,
            "selection_end": selection_end,
            "image_index": image_index,
            "image_src": image_src,
            "image_alt": image_alt,
            "drag_payload": drag_payload,
            "drop_files": drop_files,
            "media_time": media_time,
            "media_duration": media_duration,
            "media_volume": media_volume,
            "media_muted": media_muted,
            "media_paused": media_paused,
            "media_error": media_error,
        }
        # Snapshot: a handler may render, and the render registers
        # handlers for elements created since the last sweep — mutating
        # _handlers mid-iteration would raise.
        await self._dispatch_event(key, event_type, value, extra)

    async def _dispatch_event(
        self,
        key: str,
        event_type: str,
        value: Any,
        extra: dict[str, Any],
    ) -> None:
        """Dispatch one event to exact-key handlers, then to the nearest
        ``bubble_events`` ancestor with a matching handler.

        Shared by ``_on_event`` (DOM events from JS) and synthetic events
        such as ``paste_files`` (delivered asynchronously after a paste).
        """
        import logging

        from lumiview.task import run_async as _run_async

        log = logging.getLogger("neony.bridge")
        # Exact and global handlers are indexed by (key, event type), so
        # dispatch cost depends on the handlers that can actually run rather
        # than every handler registered in the window.
        direct = list(self._handlers.get((key, event_type), ()))
        global_handlers = list(self._handlers.get((None, event_type), ()))
        for fn in direct + global_handlers:
            try:
                await _run_async(fn, key=key, event_type=event_type, value=value, **extra)
            except Exception:
                log.exception(f"Event handler for {event_type} on {key} failed")

        # Bubble to the nearest bubble_events ancestor with a matching
        # handler — regardless of whether the target handled the event,
        # so window-level listeners see keys typed in inputs.  The first
        # matching ancestor wins (real DOM bubbling, opt-in per element).
        el = self._key_map.get(key)
        while el is not None and el._parent is not None:
            el = el._parent
            if not el.bubble_events:
                continue
            fns = list(self._handlers.get((el.key, event_type), ()))
            if fns:
                for fn in fns:
                    try:
                        await _run_async(fn, key=key, event_type=event_type, value=value, **extra)
                    except Exception:
                        log.exception(f"Event handler for {event_type} on {key} failed")
                return

    async def _on_paste_files(
        self,
        ctx: BridgeContext,
        key: str,
        files: Any = None,
    ) -> None:
        """Deliver file contents read from a paste event.

        JS reads ``clipboardData.files`` as data URLs after the paste
        (``FileReader`` is async) and invokes this command; it dispatches
        a synthetic ``paste_files`` event so components receive actual
        bytes without going through the pyclip-based clipboard API.
        """
        await self._dispatch_event(
            key=key,
            event_type="paste_files",
            value=None,
            extra={"paste_files": files},
        )

    async def _on_media_read(
        self,
        ctx: BridgeContext,
        url: str,
        offset: Any = None,
        chunk: Any = None,
    ) -> dict[str, Any]:
        """Read a ``neony://`` resource for JS-side media hydration.

        WebKitGTK's ``fetch()`` only implements CORS semantics for
        HTTP(S) — a custom-scheme fetch is rejected before the request is
        even issued ("Cross origin requests are only supported for
        HTTP"), so the media adapter cannot pull protocol bytes itself.
        This command is the bridge transport: it routes the URL through
        the same registered protocol handlers as native scheme requests
        (identical permission surface as <img> subresources) and returns
        base64-encoded body bytes for the JS side to wrap in a Blob.

        With ``offset`` (and optional ``chunk`` size) the read is served
        through the handler's HTTP Range support and only that slice is
        returned — JS pulls large files piecewise so neither the asyncio
        loop (one giant ``json.dumps``) nor the WebView main thread (one
        giant ``eval_js`` parse) stalls for the whole file.  A handler
        that ignores Range answers ``200`` with the full body; the reply
        is flagged ``complete`` so JS can fall back to single-shot.

        Raises:
            BridgeError: non-``neony://`` URL, unknown protocol key, or
                an upstream error status (4xx/5xx other than 206).
        """
        import base64
        from urllib.parse import unquote, urlparse

        from lumiview.bridge import BridgeError
        from lumiview.task import run_async

        parsed = urlparse(url)
        if parsed.scheme != "neony":
            raise BridgeError("bad_url", f"media_read only serves neony:// URLs, got {parsed.scheme!r}")
        key = parsed.netloc.lower()
        handler = (self._protocol_handlers or {}).get(key)
        if handler is None:
            raise BridgeError("not_found", f"No protocol handler for neony://{key}")

        from neony.application.protocols.base import Request

        headers: dict[str, str] = {}
        if offset is not None:
            start = int(offset)
            length = int(chunk) if chunk else 1 << 20
            headers["Range"] = f"bytes={start}-{start + length - 1}"

        request = Request(
            key=key,
            path=unquote(parsed.path or "/"),
            method="GET",
            url=url,
            query=parsed.query or "",
            headers=headers,
        )

        # run_async keeps the shared scheduling contract: sync handlers on
        # the app thread pool, async handlers awaited on the loop.
        result = await run_async(handler, request)
        if result.status >= 400:
            raise BridgeError("upstream_error", f"Protocol {key!r} answered {result.status}")

        content_type = ""
        content_range = ""
        for header_name, header_value in result.headers.items():
            lowered = header_name.lower()
            if lowered == "content-type":
                content_type = header_value
            elif lowered == "content-range":
                content_range = header_value

        total = None
        if content_range:
            tail = content_range.rsplit("/", 1)[-1].strip()
            if tail.isdigit():
                total = int(tail)
        complete = result.status == 200 or (total is not None and total == len(result.body))
        if result.status == 200:
            total = len(result.body)

        return {
            "status": result.status,
            "content_type": content_type,
            "data_b64": base64.b64encode(result.body).decode("ascii"),
            "total": total,
            "complete": complete,
        }

    async def _on_resync(self, ctx: BridgeContext, rev: int) -> None:
        """JS detected a revision gap — re-send the full mount."""
        if self._last_tree is not None:
            self._snapshot = None  # force full mount
            await self.render(self._last_tree)

    async def _on_ready_ack(self, ctx: BridgeContext, rev: int) -> None:
        """JS engine has mounted and is ready."""
        pass

    async def _on_open_external(self, ctx: BridgeContext, url: str) -> None:
        """Open a link (markdown content) in the system browser.  The
        webview's navigation policy denies in-page navigation by default,
        so in-app content routes external links here.  Scheme-allowlisted:
        anything else (``file:``, custom handlers) is dropped."""
        if not re.match(r"^https?://|^mailto:", url):
            logging.getLogger("neony.bridge").warning("open_external: blocked %r", url)
            return
        await asyncio.to_thread(webbrowser.open, url)

    # ---- public API ----

    def on(self, event_type: str, *, key: str | None = None):
        """Register a DOM event handler (decorator), called with *key*,
        *event_type*, *value*.  A ``None`` *key* matches any element."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._handlers.setdefault((key, event_type), []).append(fn)
            return fn

        return decorator

    def off(self, event_type: str, fn: Callable[..., Any], *, key: str | None = None) -> None:
        """Remove a previously registered event handler."""
        handlers = self._handlers.get((key, event_type), [])
        if fn in handlers:
            handlers.remove(fn)

    async def render(self, element: DOMElement, *, immediate: bool = True) -> PatchMessage | None:
        """Render (or update) a DOM tree.  First call mounts; later calls
        diff and emit patches.  ``immediate=False`` defers one frame so
        style-only event bursts coalesce.  *rev* increments only when a
        message is sent — an empty re-render must not gap the JS engine's
        ``lastRev``.  Returns the sent :class:`PatchMessage` or ``None``.
        """
        async with self._lock:
            if self._win is None:
                raise RuntimeError(
                    "Neony: window not ready — the bridge must be included "
                    "in a LumiView Bridge and the window must be created."
                )

            if self._render_task is not None:
                self._render_task.cancel()
                self._render_task = None

            # Immediate: first mount or important events.  Deferred:
            # style-only / high-frequency events that can wait a frame.
            if immediate or self._snapshot is None:
                return await self._do_render(element)

            loop = asyncio.get_event_loop()
            self._render_task = loop.create_task(self._deferred_render(element))
            return None

    def take_discarded_registrations(self) -> set[tuple[str, str]]:
        """Return and clear handler registrations pruned since the last call."""
        discarded = self._discarded_registrations
        self._discarded_registrations = set()
        return discarded

    @staticmethod
    def _collect_keys(node: NodeDescriptor, acc: set[str]) -> set[str]:
        acc.add(node.key)
        for child in node.children:
            Neony._collect_keys(child, acc)
        return acc

    @staticmethod
    def _subtree_sizes(node: NodeDescriptor, acc: dict[str, int]) -> dict[str, int]:
        """Map every key to its subtree node count in one post-order walk."""
        size = 1
        for child in node.children:
            size += Neony._subtree_sizes(child, acc)[child.key]
        acc[node.key] = size
        return acc

    @staticmethod
    def _flatten_mount_creates(
        node: NodeDescriptor,
        parent_key: str,
        index: int,
        threshold: int,
        sizes: dict[str, int],
        acc: list[Patch],
    ) -> None:
        """Append create patches for *node*; subtrees larger than *threshold*
        are shallow-created first and their children streamed afterwards.

        Pre-order guarantees a parent exists in the registry before any of
        its children arrive.
        """
        if sizes[node.key] <= threshold:
            acc.append(CreatePatch(key=node.key, node=node, parent=parent_key, index=index))
            return

        shallow = NodeDescriptor(
            key=node.key,
            tag=node.tag,
            attrs=node.attrs,
            styles=node.styles,
            text=node.text,
            children=[],
        )
        acc.append(CreatePatch(key=node.key, node=shallow, parent=parent_key, index=index))
        for child_index, child in enumerate(node.children):
            Neony._flatten_mount_creates(child, node.key, child_index, threshold, sizes, acc)

    def _discard_stale_state(self, live_node: NodeDescriptor) -> None:
        """Drop caches and registrations for keys that are no longer in
        the live tree.

        Removed/replaced subtrees otherwise leave stale entries behind in
        ``_snapshots``, ``_key_map`` and ``_handlers`` — memory grows and
        event dispatch keeps scanning dead handlers on every event.
        """
        live_keys = Neony._collect_keys(live_node, set())
        # Only the latest render's removals are relevant; app render drains
        # this set immediately after the bridge returns.
        self._discarded_registrations = set()

        for key in [k for k in self._snapshots if k not in live_keys]:
            del self._snapshots[key]

        for key in [k for k in self._key_map if k not in live_keys]:
            del self._key_map[key]

        for handler_key in [k for k in self._handlers if k[0] is not None and k[0] not in live_keys]:
            key, event_type = handler_key
            if key is None:
                continue
            del self._handlers[handler_key]
            self._discarded_registrations.add((key, event_type))

    async def _deferred_render(self, element: DOMElement) -> PatchMessage | None:
        """Sleep one frame, then render (cancelled by newer requests)."""
        await asyncio.sleep(self._render_debounce)
        async with self._lock:
            # A newer request superseded us — bail instead of racing.
            if self._render_task is not asyncio.current_task():
                return None
            self._render_task = None
            return await self._do_render(element)

    # ---- direct-patch fast path ----

    def _direct_patch_elements(self, root: DOMElement) -> list[DOMElement] | None:
        """Return the root workset when every mutation is style/attr-only.

        ``None`` selects structural serialization. Detached stale entries are
        ignored unless they still belong to this root.
        """
        elements: list[DOMElement] = []
        for element in root._dirty_elements.values():
            node = element
            while node._parent is not None:
                node = node._parent
            if node is not root or not element._dirty:
                continue
            if element._dirty_type & DOMElement._DIRTY_STRUCTURAL:
                return None
            if element.key not in self._snapshots:
                return None
            elements.append(element)
        return elements

    async def _emit_patch_ops(self, ops: list[Patch]) -> PatchMessage | None:
        """Increment *rev* once and emit *ops*, splitting huge batches.

        Chunked messages share one ``rev`` and ``batch``; the JS engine
        buffers them until every chunk arrives, then applies them in order.
        """
        if not ops:
            return None

        self._rev += 1
        rev = self._rev
        chunk_size = max(1, self._patch_chunk_size)
        if len(ops) <= chunk_size:
            msg = PatchMessage(rev=rev, ops=ops)
            assert self._win is not None
            await self._win.emit("neony:patch", msg.model_dump(mode="json"))
            return msg

        chunks = [ops[i : i + chunk_size] for i in range(0, len(ops), chunk_size)]
        batch = f"render:{rev}"
        last: PatchMessage | None = None
        assert self._win is not None
        for index, chunk_ops in enumerate(chunks):
            msg = PatchMessage(rev=rev, ops=chunk_ops, batch=batch, chunk=index, chunks=len(chunks))
            last = msg
            await self._win.emit("neony:patch", msg.model_dump(mode="json"))
        return last

    def _collect_direct_patches(self, root: DOMElement, elements: list[DOMElement]) -> list[Patch]:
        """Generate patches only for directly mutated workset elements."""
        patches: list[Patch] = []
        # Collect every directly mutated element before clearing anything.
        # A dirty child may precede a dirty ancestor in the root workset;
        # clearing its ancestor chain inline would erase the ancestor's own
        # _dirty_type and silently drop its patch (nested popup close: branch
        # hides, but the outer panel's display:none never reaches the DOM).
        for element in elements:
            self._collect_direct_patch(element, patches)
        for element in elements:
            node: DOMElement | None = element
            while node is not None:
                node._dirty = False
                node._dirty_type = 0
                node = node._parent
        root._dirty_elements.clear()
        return patches

    def _collect_direct_patch(self, element: DOMElement, patches: list[Patch]) -> None:
        cached = self._snapshots.get(element.key)
        if cached is not None:
            if element._dirty_type & DOMElement._DIRTY_STYLES:
                new_styles = element._serialize_styles()
                diff = DiffEngine._diff_dict(cached.styles, new_styles)
                if diff:
                    patches.append(UpdateStylesPatch(key=element.key, set=diff["set"], remove=diff["remove"]))
                    # Snapshot dictionaries may alias an element's serialized
                    # style cache from the initial mount. Mutating them in place
                    # corrupts reusable Styles constants (closed → open), so a
                    # later close serializes the stale open value and emits no
                    # hiding patch. Always detach the snapshot copy.
                    cached.styles = dict(new_styles)
            if element._dirty_type & DOMElement._DIRTY_ATTRS:
                new_attrs = element._serialize_attrs()
                diff = DiffEngine._diff_dict(cached.attrs, new_attrs)
                if diff:
                    patches.append(UpdateAttrsPatch(key=element.key, set=diff["set"], remove=diff["remove"]))
                    # Attribute serialization is cached as well; keep bridge
                    # snapshots detached from the live element cache.
                    cached.attrs = dict(new_attrs)
        element._dirty = False
        element._dirty_type = 0

    async def _do_render(self, element: DOMElement) -> PatchMessage | None:
        """Serialize (via the snapshot cache — only dirty subtrees are
        re-walked), diff, and emit patches.  Pure style/attr changes take
        the direct-patch fast path, skipping serialization and the diff
        engine entirely."""
        if self._win is None:
            raise RuntimeError(
                "Neony: window not ready — the bridge must be included "
                "in a LumiView Bridge and the window must be created."
            )

        direct_elements = self._direct_patch_elements(element) if self._snapshot is not None else None
        if direct_elements is not None:
            # Fast path: style/attr-only changes bypass serialization + diff.
            ops = self._collect_direct_patches(element, direct_elements)
            msg = await self._emit_patch_ops(ops)
            self._last_tree = element
            return msg

        new_node = element.to_node(snapshot_cache=self._snapshots)
        msg: PatchMessage | None = None

        if self._snapshot is None:
            # First render: mount the root, then stream child subtrees as
            # chunked create patches when the tree is too large for one
            # WebView eval.
            self._rev += 1
            rev = self._rev
            mount_sizes = Neony._subtree_sizes(new_node, {})
            if mount_sizes[new_node.key] <= self._mount_chunk_size:
                msg = PatchMessage(
                    rev=rev,
                    ops=[CreatePatch(key=new_node.key, node=new_node)],
                )
                await self._win.eval_js(f"window.neony.mount({msg.model_dump_json()})")
            else:
                mount_node = NodeDescriptor(
                    key=new_node.key,
                    tag=new_node.tag,
                    attrs=new_node.attrs,
                    styles=new_node.styles,
                    text=new_node.text,
                    children=[],
                )
                mount_msg = PatchMessage(
                    rev=rev,
                    ops=[CreatePatch(key=new_node.key, node=mount_node)],
                )
                await self._win.eval_js(f"window.neony.mount({mount_msg.model_dump_json()})")

                creates: list[Patch] = []
                for index, child in enumerate(new_node.children):
                    Neony._flatten_mount_creates(
                        child,
                        new_node.key,
                        index,
                        self._mount_chunk_size,
                        mount_sizes,
                        creates,
                    )
                msg = await self._emit_patch_ops(creates)
        else:
            ops = DiffEngine.diff(self._snapshot, new_node)
            msg = await self._emit_patch_ops(ops)

        self._discard_stale_state(new_node)
        self._snapshot = new_node
        self._last_tree = element
        return msg
