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
        "active",
        "group",
        "kind",
        "on_close",
        "order",
        "parent",
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
    ) -> None:
        self._manager = manager
        self._element_ref = weakref.ref(element)
        self.kind = kind
        self.group = group
        self.order = order
        self.stack_order = stack_order
        self.parent = parent
        self.on_close = on_close
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

    def open(
        self,
        element: DOMElement,
        *,
        kind: Layer,
        group: str,
        exclusive: bool = False,
        owner: DOMElement | None = None,
        on_close: Callable[[], None] | None = None,
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
                return self.bring_to_front(handle)

        if kind == Layer.MODAL:
            self._close_lower(kind)
        if exclusive:
            for handle in tuple(self._handles):
                if handle.active and handle.group == group:
                    self._close_through_callback(handle)

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
        )
        self._handles.append(handle)
        self._apply(handle)
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

    def close(self, handle: LayerHandle) -> None:
        """Remove *handle* without invoking its close callback."""
        if not handle.active or handle not in self._handles:
            return
        for child in tuple(self._handles):
            if child.active and child.parent is handle:
                self._close_through_callback(child)
        handle.active = False
        self._handles.remove(handle)
        self._clear(handle)
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

    def _close_lower(self, kind: Layer) -> None:
        for handle in tuple(self._handles):
            if handle.active and handle.kind < kind:
                self._close_through_callback(handle)

    def _close_through_callback(self, handle: LayerHandle) -> None:
        if handle.on_close is not None:
            handle.on_close()
        if handle.active:
            self.close(handle)

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
