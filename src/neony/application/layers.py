"""Centralized z-index management for cross-component floating layers.

Global stacking order is stateful: the newest open layer wins within its
band, exclusive groups close their previous member, and modal layers stack
in open order.  Components should never assign global z-index numbers
themselves.

``LocalLayer`` covers stacking that is intentionally scoped to one
component's own stacking context.  Those values must never be compared
with ``Layer`` values.
"""

from __future__ import annotations

import asyncio
import json
import weakref
from collections.abc import Callable
from enum import IntEnum

from neony.dom import DOMElement


class Layer(IntEnum):
    """Global, per-window layer bands.

    The gaps between bands leave room for every currently open layer in a
    band to receive a unique order without colliding with the next band.
    """

    BACKGROUND = -2
    BACKGROUND_TINT = -1
    TOOLTIP = 1_000
    POPOVER = 2_000
    MENU = 3_000
    MODAL = 4_000
    TOAST = 5_000
    DRAG_GHOST = 6_000


class LocalLayer(IntEnum):
    """z-index values scoped to a single component stacking context."""

    CONTENT = 1
    STICKY = 2
    DECORATION = 3
    INDICATOR = 4
    NESTED_POPUP = 5


def layers_css() -> str:
    """Return the CSS variables shared by Python and the JS runtime."""
    values: dict[str, int] = {}
    for layer in Layer:
        values[f"--neony-layer-{layer.name.lower().replace('_', '-')}"] = int(layer)
    for layer in LocalLayer:
        values[f"--neony-layer-local-{layer.name.lower().replace('_', '-')}"] = int(layer)
    return ":root { " + " ".join(f"{name}: {value};" for name, value in values.items()) + " }"


class LayerHandle:
    """One active registration in a :class:`LayerManager`."""

    __slots__ = (
        "_element_ref",
        "_manager",
        "_suppress_restore",
        "active",
        "focus_token",
        "group",
        "kind",
        "on_close",
        "order",
        "parent",
        "restore_focus",
        "stack_order",
    )

    def __init__(
        self,
        manager: LayerManager,
        element: DOMElement,
        *,
        kind: Layer,
        group: str,
        order: int,
        stack_order: int,
        parent: LayerHandle | None,
        on_close: Callable[[], None] | None,
        restore_focus: bool,
    ) -> None:
        self._manager = manager
        self._element_ref = weakref.ref(element)
        self._suppress_restore = False
        self.kind = kind
        self.group = group
        self.order = order
        self.stack_order = stack_order
        self.parent = parent
        self.on_close = on_close
        self.restore_focus = restore_focus
        self.focus_token = element.key
        self.active = True

    @property
    def element(self) -> DOMElement:
        element = self._element_ref()
        if element is None:
            raise RuntimeError("LayerHandle: its DOMElement is no longer alive")
        return element

    @property
    def z_index(self) -> int:
        base = max(int(self.kind), self.parent.z_index + 1) if self.parent is not None else int(self.kind)
        return base + self.order

    def close(self) -> None:
        """Close this registration idempotently."""
        self._manager.close(self)


class LayerManager:
    """Order floating layers within one mounted DOM tree."""

    def __init__(self) -> None:
        self._handles: list[LayerHandle] = []
        self._orders: dict[Layer, int] = {}
        self._stack_order = 0
        self._js_tasks: set[asyncio.Task[object]] = set()

    def open(
        self,
        element: DOMElement,
        *,
        kind: Layer,
        group: str,
        exclusive: bool = False,
        owner: DOMElement | None = None,
        on_close: Callable[[], None] | None = None,
        restore_focus: bool = True,
    ) -> LayerHandle:
        """Register *element* as open and return its managed handle.

        Reopening the same element is idempotent and brings its existing
        registration to the front.  ``exclusive`` closes the previous
        member of *group* through its ``on_close`` callback so component
        state and DOM visibility stay in sync with the layer stack.
        """
        for handle in tuple(self._handles):
            if handle.active and handle.element is element:
                if on_close is not None:
                    handle.on_close = on_close
                handle.restore_focus = restore_focus
                return self.bring_to_front(handle)

        if kind == Layer.MODAL:
            self._close_lower(kind, restore_focus=False)
        if exclusive:
            for handle in tuple(self._handles):
                if handle.active and handle.group == group:
                    self._close_through_callback(handle, restore_focus=False)

        parent = self._containing_handle(owner) if owner is not None else None
        order = self._orders.get(kind, 0)
        self._orders[kind] = order + 1
        self._stack_order += 1
        handle = LayerHandle(
            self,
            element,
            kind=kind,
            group=group,
            order=order,
            stack_order=self._stack_order,
            parent=parent,
            on_close=on_close,
            restore_focus=restore_focus,
        )
        self._handles.append(handle)
        self._apply(handle)
        if restore_focus:
            self._capture_focus(handle)
        return handle

    def bring_to_front(self, handle: LayerHandle) -> LayerHandle:
        """Give *handle* the newest order within its layer band."""
        if not handle.active or handle not in self._handles:
            return handle
        order = self._orders.get(handle.kind, 0)
        self._orders[handle.kind] = order + 1
        handle.order = order
        self._stack_order += 1
        handle.stack_order = self._stack_order
        self._apply(handle)
        return handle

    def close(self, handle: LayerHandle, *, restore_focus: bool = True) -> None:
        """Remove *handle* without invoking its close callback."""
        if not handle.active or handle not in self._handles:
            return
        for child in tuple(self._handles):
            if child.active and child.parent is handle:
                self._close_through_callback(child, restore_focus=False)
        should_restore = restore_focus and handle.restore_focus and not handle._suppress_restore
        handle.active = False
        self._handles.remove(handle)
        self._clear(handle)
        if should_restore:
            self._restore_focus(handle)
        if not any(candidate.kind == handle.kind for candidate in self._handles):
            self._orders[handle.kind] = 0
        if not self._handles:
            self._stack_order = 0

    def topmost(self, group: str | None = None) -> LayerHandle | None:
        """Return the highest active handle, optionally within *group*."""
        candidates = [handle for handle in self._handles if handle.active and (group is None or handle.group == group)]
        return max(candidates, key=lambda handle: handle.stack_order, default=None)

    def close_group(self, group: str) -> None:
        """Close every active member of *group* through component callbacks."""
        for handle in tuple(self._handles):
            if handle.active and handle.group == group:
                self._close_through_callback(handle)

    def handle_escape(self, element: DOMElement | None = None) -> bool:
        """Close the logical topmost layer, optionally scoped to *element*.

        A component routes Escape here instead of closing itself so an
        overlay nested inside it gets the first chance to dismiss.  When
        *element* is supplied, the topmost layer must be that element or
        one of its descendants; unrelated layers are left alone.
        """
        top = self.topmost()
        if top is None:
            return False
        if element is not None:
            scope = next(
                (handle for handle in self._handles if handle.active and handle.element is element),
                None,
            )
            allowed = self._contains(element, top.element) or (scope is not None and self._handle_contains(scope, top))
            if not allowed:
                return False
        self._close_through_callback(top)
        return True

    def _close_lower(self, kind: Layer, *, restore_focus: bool = True) -> None:
        for handle in tuple(self._handles):
            if handle.active and handle.kind < kind:
                self._close_through_callback(handle, restore_focus=restore_focus)

    def _close_through_callback(self, handle: LayerHandle, *, restore_focus: bool = True) -> None:
        handle._suppress_restore = not restore_focus
        try:
            if handle.on_close is not None:
                handle.on_close()
            if handle.active:
                self.close(handle, restore_focus=restore_focus)
        finally:
            handle._suppress_restore = False

    def _containing_handle(self, element: DOMElement) -> LayerHandle | None:
        """Return the newest active layer whose element contains *element*."""
        candidates: list[LayerHandle] = []
        for handle in self._handles:
            if not handle.active:
                continue
            current: DOMElement | None = element
            while current is not None:
                if current is handle.element:
                    candidates.append(handle)
                    break
                current = current._parent
        return max(candidates, key=lambda handle: handle.stack_order, default=None)

    def _apply(self, handle: LayerHandle) -> None:
        element = handle.element
        element.styles = element.styles.model_copy(update={"z_index": handle.z_index})
        element.args = {
            **element.args,
            "data-neony-layer": handle.kind.name.lower(),
            "data-neony-layer-order": str(handle.stack_order),
            "data-neony-layer-z": str(handle.z_index),
            "data-neony-layer-open": "true",
        }

    @staticmethod
    def _contains(ancestor: DOMElement, element: DOMElement) -> bool:
        current: DOMElement | None = element
        while current is not None:
            if current is ancestor:
                return True
            current = current._parent
        return False

    @staticmethod
    def _handle_contains(ancestor: LayerHandle, handle: LayerHandle) -> bool:
        current: LayerHandle | None = handle
        while current is not None:
            if current is ancestor:
                return True
            current = current.parent
        return False

    def _capture_focus(self, handle: LayerHandle) -> None:
        token = json.dumps(handle.focus_token)
        script = (
            "(() => { const active = document.activeElement; "
            "if (!active || active === document.body || active === document.documentElement) return; "
            "const focus = (window.__neonyLayerFocus = window.__neonyLayerFocus || {}); "
            f"focus[{token}] = active; }})()"
        )
        self._schedule_js(handle.element, script)

    def _restore_focus(self, handle: LayerHandle) -> None:
        token = json.dumps(handle.focus_token)
        script = (
            "(() => { const focus = window.__neonyLayerFocus || {}; "
            f"const target = focus[{token}]; delete focus[{token}]; "
            "if (target && target.isConnected && typeof target.focus === 'function') { "
            "try { target.focus({ preventScroll: true }); } catch (_error) { target.focus(); } } }})()"
        )
        self._schedule_js(handle.element, script)

    def _schedule_js(self, element: DOMElement, script: str) -> None:
        scope = element
        while scope._parent is not None:
            scope = scope._parent
        request = scope._eval_js_request
        if request is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(request(script))
        self._js_tasks.add(task)
        task.add_done_callback(self._js_tasks.discard)

    @staticmethod
    def _clear(handle: LayerHandle) -> None:
        element = handle.element
        element.styles = element.styles.model_copy(update={"z_index": None})
        element.args = {
            key: value
            for key, value in element.args.items()
            if key
            not in {
                "data-neony-layer",
                "data-neony-layer-order",
                "data-neony-layer-z",
                "data-neony-layer-open",
            }
        }


_MANAGERS: dict[int, tuple[weakref.ReferenceType[DOMElement], LayerManager]] = {}


def layer_manager(element: DOMElement) -> LayerManager:
    """Return the manager for *element*'s mounted DOM tree."""
    scope = element
    while scope._parent is not None:
        scope = scope._parent
    key = id(scope)
    entry = _MANAGERS.get(key)
    if entry is not None and entry[0]() is scope:
        return entry[1]
    manager = LayerManager()
    _MANAGERS[key] = (weakref.ref(scope), manager)
    return manager
