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

    v1 emits REMOVE + CREATE instead; protocol-ready only."""

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
    gaps (missed messages) and request a full resync.
    """

    rev: int = 0
    ops: list[Patch] = Field(default_factory=list)


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

        return DiffEngine._diff_node(old, new)

    @staticmethod
    def _diff_node(old: NodeDescriptor, new: NodeDescriptor) -> list[Patch]:
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

        child_patches = DiffEngine._diff_children(old.children, new.children, parent_key=new.key)
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
    ) -> list[Patch]:
        patches: list[Patch] = []

        old_map: dict[str, NodeDescriptor] = {c.key: c for c in old_children}
        new_map: dict[str, NodeDescriptor] = {c.key: c for c in new_children}

        old_keys = [c.key for c in old_children]
        new_keys = [c.key for c in new_children]

        for k in old_keys:
            if k not in new_map:
                patches.append(RemovePatch(key=k))

        for c in new_children:
            if c.key not in old_map:
                # index=None: append to end temporarily; ReorderPatch will fix
                # the final order. Avoids index misalignment when DOM still
                # contains elements that will be removed.
                patches.append(CreatePatch(key=c.key, node=c, parent=parent_key, index=None))
            else:
                patches.extend(DiffEngine._diff_node(old_map[c.key], c))

        # Reorder only when the relative order of common elements changes.
        # Pure append/remove (no reorder) skips this for efficiency.
        old_common = [k for k in old_keys if k in new_map]
        new_common = [k for k in new_keys if k in old_map]
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
        # CSS transition / animation events.
        transition_property: str | None = None,
        elapsed_time: Any = None,
        animation_name: str | None = None,
        delta_x: Any = None,
        delta_y: Any = None,
        delta_mode: Any = None,
        clipboard_text: str | None = None,
        clipboard_html: str | None = None,
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
            "transition_property": transition_property,
            "elapsed_time": elapsed_time,
            "animation_name": animation_name,
            "delta_x": delta_x,
            "delta_y": delta_y,
            "delta_mode": delta_mode,
            "clipboard_text": clipboard_text,
            "clipboard_html": clipboard_html,
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
            if ops:
                self._rev += 1
                msg = PatchMessage(rev=self._rev, ops=ops)
                await self._win.emit("neony:patch", msg.model_dump(mode="json"))
                self._last_tree = element
                return msg
            self._last_tree = element
            return None  # empty diff — no rev bump, no message

        new_node = element.to_node(snapshot_cache=self._snapshots)
        msg: PatchMessage | None = None

        if self._snapshot is None:
            # First render: full mount
            self._rev += 1
            msg = PatchMessage(
                rev=self._rev,
                ops=[CreatePatch(key=new_node.key, node=new_node)],
            )
            await self._win.eval_js(f"window.neony.mount({msg.model_dump_json()})")
        else:
            ops = DiffEngine.diff(self._snapshot, new_node)
            if ops:
                self._rev += 1
                msg = PatchMessage(rev=self._rev, ops=ops)
                await self._win.emit("neony:patch", msg.model_dump(mode="json"))

        self._snapshot = new_node
        self._last_tree = element
        return msg
