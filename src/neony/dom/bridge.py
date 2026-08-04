"""Patch protocol models, diff engine, and reactive DOM bridge for Neony.

Defines the JSON patch operations used to synchronise a Python-side
DOMElement tree with the live DOM inside a LumiView webview.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any, Literal

from lumiview._scope import BridgeContext, InitContext, Plugin
from pydantic import BaseModel, Field

from neony.dom.base import DOMElement, NodeDescriptor

if TYPE_CHECKING:
    from lumiview._window import Window

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

    Note: v1 emits REMOVE + CREATE for cross-parent moves.
    This op is protocol-ready for future use.
    """

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
        """Compare *old* (may be ``None`` for first render) with *new*.

        Returns a list of patches that, when applied in order, transform
        the old DOM state into the new one.
        """
        if old is None:
            return [CreatePatch(key=new.key, node=new)]

        return DiffEngine._diff_node(old, new)

    @staticmethod
    def _diff_node(old: NodeDescriptor, new: NodeDescriptor) -> list[Patch]:
        patches: list[Patch] = []

        # Tag changed → replace the whole element
        if old.tag != new.tag:
            patches.append(ReplacePatch(key=new.key, node=new))
            return patches

        # Text changed
        if old.text != new.text:
            patches.append(SetTextPatch(key=new.key, text=new.text or ""))

        # Attrs diff
        attr_patch = DiffEngine._diff_dict(old.attrs, new.attrs)
        if attr_patch:
            patches.append(UpdateAttrsPatch(key=new.key, set=attr_patch["set"], remove=attr_patch["remove"]))

        # Styles diff
        style_patch = DiffEngine._diff_dict(old.styles, new.styles)
        if style_patch:
            patches.append(UpdateStylesPatch(key=new.key, set=style_patch["set"], remove=style_patch["remove"]))

        # Children diff
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

        # Removed: keys in old but not in new
        for k in old_keys:
            if k not in new_map:
                patches.append(RemovePatch(key=k))

        # Created + recurse: walk new children in order
        for i, c in enumerate(new_children):
            if c.key not in old_map:
                # New element
                patches.append(CreatePatch(key=c.key, node=c, parent=parent_key, index=i))
            else:
                # Existing element — recurse
                patches.extend(DiffEngine._diff_node(old_map[c.key], c))

        # Reorder: keys exist in both but order changed
        if old_keys != new_keys and set(old_keys) == set(new_keys):
            patches.append(ReorderPatch(parent=parent_key, ordered_keys=new_keys))

        return patches


# ---- reactive bridge ----


class Neony(Plugin):
    """Reactive DOM bridge for a LumiView window.

    A :class:`~lumiview.Plugin` that manages the lifecycle of a
    DOMElement tree: serialises it, diffs against the previous snapshot,
    and pushes patches to the JavaScript engine inside the webview.

    Include it in a LumiView Bridge via ``Bridge(includes=[neony])`` —
    commands are registered automatically at construction time and the
    JS engine is injected via ``on_init``.

    Usage::

        neony = Neony()
        app = App(name="Demo")

        async def main():
            win = await Window.create(bridge=Bridge(includes=[neony]), ...)
            tree = Body(container=[Div(container=["Hello"])])
            await neony.render(tree)

            @neony.on("click")
            async def handle_click(key, type, value):
                print(f"Clicked {key}")

        app.run(main)
    """

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
        # Per-key snapshot cache for dirty-subtree tracking: unchanged
        # elements reuse their cached NodeDescriptor (see to_node).
        self._snapshots: dict[str, NodeDescriptor] = {}
        self._rev: int = 0
        self._lock: asyncio.Lock = asyncio.Lock()
        self._handlers: dict[tuple[str | None, str], list[Callable[..., Any]]] = {}
        # Deferred-render coalescing (input throttling / hover de-noise):
        # a pending task scheduled by ``render(immediate=False)``; cancelled
        # and replaced on each new request within the debounce window.
        self._render_task: asyncio.Task | None = None
        self._render_debounce: float = 0.016  # ~1 frame at 60fps

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

    async def _on_event(self, ctx: BridgeContext, key: str, event_type: str, value: Any = None) -> None:
        """Handle a DOM event forwarded from JavaScript.

        One handler raising must not break the rest of the chain —
        each handler runs independently.
        """
        import logging

        from lumiview._task import _run_async

        log = logging.getLogger("neony.bridge")
        for (ekey, etype), fns in self._handlers.items():
            if etype == event_type and (ekey is None or ekey == key):
                for fn in fns:
                    try:
                        await _run_async(fn, key=key, event_type=event_type, value=value)
                    except Exception:
                        log.exception(f"Event handler for {event_type} on {key} failed")

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
        """Register a DOM event handler (decorator).

        The handler receives keyword arguments *key*, *event_type*, and *value*.
        If *key* is ``None`` (the default), the handler matches *event_type*
        on any element.
        """

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
        """Render (or update) a DOM tree in the browser.

        On the first call the entire tree is mounted via ``eval_js``.
        Subsequent calls diff against the previous snapshot and send
        only changed patches via ``emit``.

        With ``immediate=False`` the render is deferred by one frame
        (~16ms): a pending deferred render is cancelled and rescheduled,
        so a burst of style-only events (hover, focus, blur) coalesces
        into a single render.  This is the input-throttling / hover
        de-noise mechanism.

        *rev* increments ONLY when a message is actually sent, so the
        JavaScript engine's ``lastRev`` stays in lockstep with the
        browser — an unchanged re-render (e.g. a ``change`` event after
        the state was already rendered) must not create a revision gap
        that would trigger an unnecessary full resync.

        Returns the :class:`PatchMessage` that was sent, or ``None``
        when there was nothing to send (including a deferred render
        that was cancelled by a newer request).
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

            # Immediate path: first mount, or "important" events (click,
            # change, submit).  Deferred path: style-only / high-frequency
            # events that can wait one frame.
            if immediate or self._snapshot is None:
                return await self._do_render(element)

            loop = asyncio.get_event_loop()
            self._render_task = loop.create_task(self._deferred_render(element))
            return None

    async def _deferred_render(self, element: DOMElement) -> PatchMessage | None:
        """Sleep one frame, then render.  Cancelled when a newer render
        request arrives within the debounce window."""
        await asyncio.sleep(self._render_debounce)
        async with self._lock:
            # Superseded: a newer render request replaced us between the
            # sleep and the lock acquisition (or cancelled us).  Bail out
            # instead of racing _do_render.
            if self._render_task is not asyncio.current_task():
                return None
            self._render_task = None
            return await self._do_render(element)

    async def _do_render(self, element: DOMElement) -> PatchMessage | None:
        """The actual render cycle: serialize, diff, emit patches.

        Serialization passes the per-key snapshot cache: elements that
        did not change since the last render are reused verbatim (their
        dirty flag is clear), so only dirty subtrees are re-walked.
        """
        if self._win is None:
            raise RuntimeError(
                "Neony: window not ready — the bridge must be included "
                "in a LumiView Bridge and the window must be created."
            )
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
