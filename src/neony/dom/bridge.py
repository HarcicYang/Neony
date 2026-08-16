"""Patch protocol, diff engine, and the reactive DOM bridge."""

from __future__ import annotations

import asyncio
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

        # Register JS→Python IPC commands on this scope
        self.command(self._on_event, name="event")
        self.command(self._on_resync, name="resync")
        self.command(self._on_ready_ack, name="ready")

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
        # In-app drag payload (dragstart / drop only) — the string the
        # source element declared via ``drag_payload``.
        drag_payload: str | None = None,
        # Dropped files: list of {name, path, size, type} dicts from the
        # drop event.  ``Any`` for the same strict-conversion reasons as
        # the numeric fields; DomEvent.drop_files is the typed surface.
        drop_files: Any = None,
    ) -> None:
        """Handle a DOM event from JavaScript.  The event dispatches to
        its own element's handlers, then bubbles to the nearest
        ``bubble_events`` ancestor with a matching handler — even when
        the target handled it, so window-level listeners (page key
        handlers, shortcuts) see keys typed in any input.  Each handler
        runs independently — one raising must not break the chain."""
        import logging

        from lumiview.task import run_async as _run_async

        log = logging.getLogger("neony.bridge")
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
            "drag_payload": drag_payload,
            "drop_files": drop_files,
        }
        # Snapshot: a handler may render, and the render registers
        # handlers for elements created since the last sweep — mutating
        # _handlers mid-iteration would raise.
        for (ekey, etype), fns in list(self._handlers.items()):
            if etype == event_type and (ekey is None or ekey == key):
                for fn in fns:
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
            for (ekey, etype), fns in list(self._handlers.items()):
                if etype == event_type and ekey == el.key:
                    for fn in fns:
                        try:
                            await _run_async(fn, key=key, event_type=event_type, value=value, **extra)
                        except Exception:
                            log.exception(f"Event handler for {event_type} on {key} failed")
                    return

    async def _on_resync(self, ctx: BridgeContext, rev: int) -> None:
        """JS detected a revision gap — re-send the full mount."""
        if self._last_tree is not None:
            self._snapshot = None  # force full mount
            await self.render(self._last_tree)

    async def _on_ready_ack(self, ctx: BridgeContext, rev: int) -> None:
        """JS engine has mounted and is ready."""
        pass

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

    def _can_direct_patch(self, element: DOMElement) -> bool:
        """True when every dirty element only has style/attr changes, so
        the render can bypass full serialization and the diff engine."""
        if element._dirty:
            if element._dirty_type & DOMElement._DIRTY_STRUCTURAL:
                return False
            if (element._dirty_type & (DOMElement._DIRTY_STYLES | DOMElement._DIRTY_ATTRS)) and (
                element.key not in self._snapshots
            ):
                # A changed element must have a snapshot to diff against.
                return False
        else:
            return True  # clean subtree — nothing changed below
        for child in element.container:
            if isinstance(child, DOMElement) and not self._can_direct_patch(child):
                return False
        return True

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

    def _collect_direct_patches(self, element: DOMElement) -> list[Patch]:
        """Generate style/attr patches for dirty elements, updating the
        snapshot cache in place and clearing their dirty flags."""
        patches: list[Patch] = []
        self._collect_direct_patches_impl(element, patches)
        return patches

    def _collect_direct_patches_impl(self, element: DOMElement, patches: list[Patch]) -> None:
        if not element._dirty:
            return
        cached = self._snapshots.get(element.key)
        if cached is not None:
            if element._dirty_type & DOMElement._DIRTY_STYLES:
                new_styles = element._serialize_styles()
                diff = DiffEngine._diff_dict(cached.styles, new_styles)
                if diff:
                    patches.append(UpdateStylesPatch(key=element.key, set=diff["set"], remove=diff["remove"]))
                    cached.styles.clear()
                    cached.styles.update(new_styles)
            if element._dirty_type & DOMElement._DIRTY_ATTRS:
                new_attrs = element._serialize_attrs()
                diff = DiffEngine._diff_dict(cached.attrs, new_attrs)
                if diff:
                    patches.append(UpdateAttrsPatch(key=element.key, set=diff["set"], remove=diff["remove"]))
                    cached.attrs.clear()
                    cached.attrs.update(new_attrs)
        element._dirty = False
        element._dirty_type = 0
        for child in element.container:
            if isinstance(child, DOMElement):
                self._collect_direct_patches_impl(child, patches)

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

        if self._snapshot is not None and self._can_direct_patch(element):
            # Fast path: style/attr-only changes bypass serialization + diff.
            ops = self._collect_direct_patches(element)
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
