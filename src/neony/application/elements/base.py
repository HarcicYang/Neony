"""Component base class.

A Component encapsulates a DOMElement tree (never inherits): it owns
its state, proxies the fluent event API, and produces a DOMElement via
:meth:`build`.  User-driven events reach callbacks with ``source ==
"user"``; programmatic state changes never fire callbacks — except
lifecycle pseudo-events (:meth:`_dispatch_pseudo`, e.g. Dialog's
``open``/``close``), which fire on programmatic writes by design.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from typing import Any, Self

from neony.dom import DOMElement, DomEvent, Signal, Styles
from neony.dom.reactive import Computed, Effect, effect

# Every event type the JS engine delegates (mirrors DELEGATED_EVENTS in
# src/neony/javascript/index.js).  Component.on() lazily wires these to
# the root element so unbound types (keydown, wheel, paste, drop, ...)
# reach component callbacks; non-DOM pseudo-events like TitleBar's
# "close" / "minimize" are excluded.
_DOM_EVENTS = frozenset(
    {
        "click",
        "dblclick",
        "outsideclick",
        "input",
        "change",
        "submit",
        "keydown",
        "keyup",
        "focus",
        "blur",
        "contextmenu",
        "mouseover",
        "mouseout",
        "mousedown",
        "mouseup",
        "pointermove",
        "transitionend",
        "animationstart",
        "animationend",
        "wheel",
        "paste",
        "copy",
        "cut",
        "dragover",
        "dragleave",
        "drop",
    }
)


class Component:
    """Base class for all Neony UI components.  Subclasses build their
    internal DOMElement tree in ``__init__`` (stored as ``self._root``),
    sync state in :meth:`_on_event`, and expose chainable ``on_*``
    methods (via :meth:`_bind`)."""

    #: Event types the subclass wires itself (via :meth:`_bind` or
    #: custom raw handlers); :meth:`on` must not wire these again or
    #: callbacks would double-fire.
    _bound_events: frozenset[str] = frozenset()

    #: Name of the attribute :meth:`bind_value` reads / writes
    #: (``"value"`` on most inputs; Checkbox overrides to ``"checked"``).
    _value_prop: str = "value"
    #: Event that carries the component's value on user change; ``None``
    #: means no user channel — :meth:`bind_value` writes only (Progress).
    _value_event: str | None = None
    #: Multi-channel override of :attr:`_value_event` — when set,
    #: :meth:`bind_value` subscribes the write-back to every listed event
    #: (ComboBox: ``("input", "change")`` — keystrokes AND picks).
    _value_events: tuple[str, ...] | None = None

    @property
    def selected_key(self) -> str | None:
        """The selected entry's key — the string identity of the current
        selection, dispatched to ``on_change`` callbacks via
        ``event.value``.  Selection components (Sidebar, Tabs,
        RadioGroup) override this; the base raises."""
        raise NotImplementedError(f"{type(self).__name__} does not support selection")

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support selection")

    def __init__(self) -> None:
        self._root: DOMElement
        self._callbacks: dict[str, list[Callable[..., Any]]] = {}
        self._raw_wired: set[str] = set()
        self._built = False
        self._component_children: list[Component] = []
        # Pseudo-event tasks kept alive so they aren't GC'd mid-run.
        self._pseudo_tasks: set[Any] = set()
        # bind_value state — disposed/removed by unbind().
        self._value_effect: Effect | None = None
        self._value_writers: dict[str, Callable[[DomEvent], Any]] = {}
        # The bound Signal — programmatic value/checked writes mirror into
        # it (set by bind_value, cleared by unbind_value).
        self._value_signal: Signal[Any] | None = None
        # bind_selected state — disposed/removed by unbind().
        self._selected_effect: Effect | None = None
        self._selected_writer: Callable[[DomEvent], Any] | None = None
        self._selected_event_bound: str | None = None
        # The bound Signal — programmatic selected_key writes mirror into
        # it (set by bind_selected, cleared by unbind_selected).
        self._selected_signal: Signal[Any] | None = None

    def _track_component(self, child: Component) -> None:
        """Register a child Component so Page.build can walk the tree
        (e.g. to auto-collect child ``shortcuts()``)."""
        self._component_children.append(child)

    def iter_components(self) -> Iterator[Component]:
        """Depth-first walk of this component and its registered children."""
        yield self
        for child in self._component_children:
            yield from child.iter_components()

    def shortcuts(self) -> list[tuple[str | dict[str, str], Callable[[], Any]]]:
        """Window-level ``(combo, handler)`` pairs this component (or its
        children) exposes; Page.build auto-registers these via
        ``Page.on_shortcut``.  Subclasses with shortcuts override this."""
        return []

    # ---- build ----

    def build(self) -> DOMElement:
        """Return the internal DOMElement tree for insertion into a Page.

        A component owns exactly one root and one mount: the second call
        raises, because the same element cannot live in two trees.
        """
        if self._built:
            raise RuntimeError(
                f"{type(self).__name__}.build() can only be called once. Create a new instance for each page/window."
            )
        self._built = True
        return self._root

    # ---- styling ----

    def reset_styles(self, styles: Styles) -> Self:
        """Completely replace the root styles (chainable) — later calls
        overwrite earlier ones."""
        self._root.styles = styles
        return self

    # ---- signal bindings (proxy to the root element) ----

    def bind_text(self, signal: Signal[Any] | Computed[Any], fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to the component's text content (see DOMElement.bind_text)."""
        self._root.bind_text(signal, fmt)
        return self

    def bind_style(self, signal: Signal[Any] | Computed[Any], prop: str, fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to a root style property (see DOMElement.bind_style)."""
        self._root.bind_style(signal, prop, fmt)
        return self

    def bind_attr(
        self, signal: Signal[Any] | Computed[Any], name: str, fmt: Callable[[Any], Any] | None = None
    ) -> Self:
        """Bind *signal* to a root HTML attribute (see DOMElement.bind_attr).

        The default formatter passes bools through (True → bare
        attribute, False/None → removed) — a stringified ``"False"``
        would leave the attribute present, e.g. a permanently disabled
        button."""
        self._root.bind_attr(signal, name, fmt)
        return self

    def bind_visible(self, signal: Signal[Any] | Computed[Any]) -> Self:
        """Bind *signal* to the root's visibility (see DOMElement.bind_visible)."""
        self._root.bind_visible(signal)
        return self

    def bind_value(self, signal: Signal[Any] | Computed[Any]) -> Self:
        """Bind *signal* to the component's value, both ways.

        Signal writes update the component value immediately and on
        every change; user value changes write back to the signal
        (:class:`Computed` is read-only — no write-back).  The user
        channels are the component's ``_value_event`` (or the
        ``_value_events`` tuple) — ``input`` on Input/Slider, ``change``
        on Select/Checkbox/Switch/Dropdown, both on ComboBox — carrying
        the value on ``_value_prop``; Checkbox binds ``checked``,
        Progress has no user channel and binds write-only.  Programmatic
        value writes mirror into the signal (equal values are a no-op,
        so the signal → component effect never loops) but never fire
        user ``on_*`` callbacks.
        """
        self.unbind_value()
        prop = type(self)._value_prop

        def write() -> None:
            setattr(self, prop, signal())

        self._value_effect = effect(write)
        if isinstance(signal, Signal):
            self._value_signal = signal
        events = type(self)._value_events
        if events is None:
            single = type(self)._value_event
            events = (single,) if single is not None else ()
        if events and isinstance(signal, Signal):
            for event_type in events:
                writer = self._make_value_writer(signal)
                self._value_writers[event_type] = writer
                self.on(event_type, writer)
        return self

    def unbind_value(self) -> Self:
        """Dispose the :meth:`bind_value` binding (signal → component
        effect and the user-event write-backs), keeping other bindings."""
        if self._value_effect is not None:
            self._value_effect.dispose()
            self._value_effect = None
        for event_type, writer in self._value_writers.items():
            callbacks = self._callbacks.get(event_type, [])
            if writer in callbacks:
                callbacks.remove(writer)
        self._value_writers.clear()
        self._value_signal = None
        return self

    def _mirror_value(self, value: Any) -> None:
        """Programmatic value/checked writes mirror into the bound
        signal (set by :meth:`bind_value`) — equal values are a no-op."""
        if self._value_signal is not None:
            self._value_signal.set(value)

    def bind_selected(self, signal: Signal[Any] | Computed[Any]) -> Self:
        """Bind *signal* to the component's selected key, both ways.

        Components with a ``selected_key`` property (Sidebar, Tabs,
        RadioGroup) expose the selection to the reactive system: signal writes
        select the entry; user selection writes the key back to the
        signal.  :class:`Computed` is read-only — no write-back.  The
        user channel is the component's ``change`` event, carrying the
        key on ``event.value`` (pseudo-events like shortcuts dispatch
        with ``source == "user"`` too).  Programmatic ``selected_key``
        writes mirror into the signal (equal values are a no-op, so the
        signal → component effect never loops) but never fire user
        ``on_*`` callbacks.
        """
        self.unbind_selected()

        def write() -> None:
            self.selected_key = signal()

        self._selected_effect = effect(write)
        if isinstance(signal, Signal):
            self._selected_signal = signal

            def writer(event: DomEvent) -> None:
                signal.set(event.value)

            self._selected_writer = writer
            self._selected_event_bound = "change"
            self.on("change", writer)
        return self

    def unbind_selected(self) -> Self:
        """Dispose the :meth:`bind_selected` binding (signal → selection
        effect and the user-event write-back), keeping other bindings."""
        if self._selected_effect is not None:
            self._selected_effect.dispose()
            self._selected_effect = None
        if self._selected_writer is not None and self._selected_event_bound is not None:
            callbacks = self._callbacks.get(self._selected_event_bound, [])
            if self._selected_writer in callbacks:
                callbacks.remove(self._selected_writer)
        self._selected_writer = None
        self._selected_event_bound = None
        self._selected_signal = None
        return self

    def _mirror_selected(self, value: Any) -> None:
        """Programmatic ``selected_key`` writes mirror into the bound
        signal (set by :meth:`bind_selected`) — equal values are a
        no-op."""
        if self._selected_signal is not None:
            self._selected_signal.set(value)

    def unbind(self) -> Self:
        """Dispose every signal binding on the root element (DOM
        bindings and the :meth:`bind_value` / :meth:`bind_selected`
        bindings)."""
        self.unbind_value()
        self.unbind_selected()
        self._root.unbind()
        return self

    def _make_value_writer(self, signal: Signal[Any]) -> Callable[[DomEvent], Any]:
        """Write a user value change back into *signal*."""

        def writer(event: DomEvent) -> None:
            signal.set(event.value)

        return writer

    # ---- event API ----

    def on(self, event_type: str, fn: Callable[..., Any]) -> Self:
        """Register a callback for *event_type* (chainable), called with
        a :class:`DomEvent` with ``source == "user"``.

        DOM event types the component doesn't bind itself (keydown,
        wheel, paste, drop, ...) are lazily wired to the root element
        on first registration — so ``component.on_keydown(...)`` works
        even though the component only wires its own events.
        """
        self._callbacks.setdefault(event_type, []).append(fn)
        if event_type in _DOM_EVENTS and event_type not in type(self)._bound_events:
            self._wire_root(event_type)
        return self

    def _wire_root(self, event_type: str) -> None:
        """Attach the source-aware dispatcher to the root element, once
        per type — DOM events targeting the root (or bubbling to it via
        ``bubble_events``) then reach the component's callbacks."""
        if event_type not in self._raw_wired:
            self._raw_wired.add(event_type)
            self._root.on(event_type, self._make_handler(event_type))

    def on_click(self, fn: Callable[..., Any]) -> Self:
        return self.on("click", fn)

    def on_outsideclick(self, fn: Callable[..., Any]) -> Self:
        """Register for the synthetic ``outsideclick`` — fires when a
        click lands outside the component's root while it carries the
        ``data-neony-outside`` marker (see the JS engine)."""
        return self.on("outsideclick", fn)

    def on_dblclick(self, fn: Callable[..., Any]) -> Self:
        return self.on("dblclick", fn)

    def on_input(self, fn: Callable[..., Any]) -> Self:
        return self.on("input", fn)

    def on_change(self, fn: Callable[..., Any]) -> Self:
        return self.on("change", fn)

    def on_focus(self, fn: Callable[..., Any]) -> Self:
        return self.on("focus", fn)

    def on_blur(self, fn: Callable[..., Any]) -> Self:
        return self.on("blur", fn)

    def on_keydown(self, fn: Callable[..., Any]) -> Self:
        return self.on("keydown", fn)

    def on_keyup(self, fn: Callable[..., Any]) -> Self:
        return self.on("keyup", fn)

    def on_mousedown(self, fn: Callable[..., Any]) -> Self:
        return self.on("mousedown", fn)

    def on_mouseup(self, fn: Callable[..., Any]) -> Self:
        return self.on("mouseup", fn)

    def on_pointermove(self, fn: Callable[..., Any]) -> Self:
        return self.on("pointermove", fn)

    def on_transitionend(self, fn: Callable[..., Any]) -> Self:
        return self.on("transitionend", fn)

    def on_animationstart(self, fn: Callable[..., Any]) -> Self:
        return self.on("animationstart", fn)

    def on_animationend(self, fn: Callable[..., Any]) -> Self:
        return self.on("animationend", fn)

    def on_contextmenu(self, fn: Callable[..., Any]) -> Self:
        return self.on("contextmenu", fn)

    def on_wheel(self, fn: Callable[..., Any]) -> Self:
        return self.on("wheel", fn)

    def on_paste(self, fn: Callable[..., Any]) -> Self:
        return self.on("paste", fn)

    def on_copy(self, fn: Callable[..., Any]) -> Self:
        return self.on("copy", fn)

    def on_cut(self, fn: Callable[..., Any]) -> Self:
        return self.on("cut", fn)

    def on_drop(self, fn: Callable[..., Any]) -> Self:
        return self.on("drop", fn)

    def on_dragover(self, fn: Callable[..., Any]) -> Self:
        return self.on("dragover", fn)

    def on_dragleave(self, fn: Callable[..., Any]) -> Self:
        return self.on("dragleave", fn)

    # ---- internals ----

    def _bind(self, element: DOMElement, event_type: str) -> None:
        """Attach the source-aware dispatcher to an internal element."""
        element.on(event_type, self._make_handler(event_type))

    def _make_handler(self, event_type: str) -> Callable[..., Any]:
        """Create the raw DOMElement handler for *event_type*."""

        async def handler(event: DomEvent) -> None:
            event.source = "user"
            try:
                await self._on_event(event_type, event)
            finally:
                event.source = "program"

        return handler

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        """Subclass hook: sync state from *event*, then notify callbacks."""
        await self._dispatch(event_type, event)

    async def _dispatch(self, event_type: str, event: DomEvent) -> None:
        """Notify user callbacks registered for *event_type*.

        Supports both sync and async callbacks; awaitables are awaited.
        """
        for fn in self._callbacks.get(event_type, []):
            result = fn(event)
            if asyncio.iscoroutine(result):
                await result

    def _dispatch_pseudo(self, event_type: str, arg: Any) -> None:
        """Fire a pseudo-event (open/close/submit) to callbacks that
        receive *arg* (the component itself or a value) instead of a
        DomEvent.  Async callbacks run as fire-and-forget tasks — the
        state change is synchronous and must not block on them."""
        for fn in self._callbacks.get(event_type, []):
            result = fn(arg)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                # Keep a reference so the task isn't GC'd mid-run.
                self._pseudo_tasks.add(task)
                task.add_done_callback(self._pseudo_tasks.discard)
