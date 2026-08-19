"""DOM element base class, the parent-aware children list, and element keys.

The typed CSS value models (``Color``, ``Transition``, ``Animation``,
keyframes, ``Styles``) live in :mod:`neony.dom.css`, the JS event payload
in :mod:`neony.dom.events`, and the serialized snapshot shape in
:mod:`neony.dom.nodes`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine, Iterable
from typing import Any, ClassVar, Literal, Self, SupportsIndex, cast

from pydantic import BaseModel, PrivateAttr
from pydantic.fields import Field

from neony.dom.css import Styles
from neony.dom.nodes import NodeDescriptor
from neony.dom.reactive import Computed, Effect, Signal, effect


def _new_key() -> str:
    """Generate a unique hex key for DOM element identity tracking."""
    return uuid.uuid4().hex


class _Children(list):
    """The ``container`` list, aware of its owning element.

    A plain ``list`` base (the ``DOMElement | str`` element type lives in
    method annotations only, since ``list[...]`` evaluates before
    DOMElement exists).  Keeps children's ``_parent`` pointers in sync
    and marks the owner dirty on in-place mutations (``append``,
    ``__setitem__``, ...), which never reach the owner's ``__setattr__``.
    """

    __slots__ = ("_owner",)

    def __init__(self, owner: DOMElement, iterable: Iterable[DOMElement | str] = ()) -> None:
        super().__init__()
        self._owner = owner
        for item in iterable:
            self.append(item)

    def _set_parent(self, item: DOMElement | str) -> None:
        if isinstance(item, DOMElement):
            if item._parent is not None:
                raise RuntimeError(
                    f"DOMElement(key={item.key!r}) is already mounted in a tree "
                    f"(parent key={item._parent.key!r}). Elements cannot be shared "
                    f"between containers — create a new instance."
                )
            item._parent = self._owner

    def _unset_parent(self, item: DOMElement | str) -> None:
        if isinstance(item, DOMElement):
            if item._parent is not self._owner:
                raise RuntimeError(
                    f"DOMElement(key={item.key!r}) is not a child of this container "
                    f"(its parent is key={item._parent.key if item._parent else None!r}) "
                    f"— removing it here would corrupt the tree."
                )
            item._parent = None

    def _mark_owner_structural(self) -> None:
        """Container mutations are structural — they force the full diff path."""
        self._owner._dirty_type |= DOMElement._DIRTY_STRUCTURAL
        self._owner._invalidate_attrs_cache()
        self._owner._mark_dirty()

    def append(self, item: DOMElement | str) -> None:
        super().append(item)
        self._set_parent(item)
        self._mark_owner_structural()

    def extend(self, items: Iterable[DOMElement | str]) -> None:
        for item in items:
            super().append(item)
            self._set_parent(item)
        self._mark_owner_structural()

    def insert(self, index: SupportsIndex, item: DOMElement | str) -> None:
        super().insert(index, item)
        self._set_parent(item)
        self._mark_owner_structural()

    def remove(self, item: DOMElement | str) -> None:
        super().remove(item)
        self._unset_parent(item)
        self._mark_owner_structural()

    def pop(self, index: SupportsIndex = -1) -> DOMElement | str:
        item = super().pop(index)
        self._unset_parent(item)
        self._mark_owner_structural()
        return item

    def clear(self) -> None:
        for item in self:
            self._unset_parent(item)
        super().clear()
        self._mark_owner_structural()

    def __setitem__(self, index: SupportsIndex | slice, item: Any) -> None:
        if isinstance(index, slice):
            old = list(self[index])
            super().__setitem__(index, item)
            for o in old:
                self._unset_parent(o)
            if isinstance(item, (list, tuple)):
                for i in item:
                    self._set_parent(i)
            else:
                self._set_parent(item)
        else:
            old = self[index]
            super().__setitem__(index, item)
            self._unset_parent(old)
            self._set_parent(item)
        self._mark_owner_structural()

    def __delitem__(self, index: SupportsIndex | slice) -> None:
        if isinstance(index, slice):
            old = list(self[index])
            super().__delitem__(index)
            for o in old:
                self._unset_parent(o)
        else:
            item = self[index]
            super().__delitem__(index)
            self._unset_parent(item)
        self._mark_owner_structural()


class DOMElement(BaseModel):
    """Base class for all DOM elements.

    Subclasses set ``_tag`` to the HTML tag name.
    Set ``_void = True`` for self-closing elements like ``<img />``.
    """

    model_config = {"populate_by_name": True}

    # Per-class cache of ``(field_name, html_name)`` pairs for typed HTML
    # attributes.  ``_collect_attr_items`` walks this short list instead of
    # re-scanning every pydantic field + json_schema_extra per serialization.
    _HTML_ATTR_FIELDS_CACHE: ClassVar[dict[type, tuple[tuple[str, str], ...]]] = {}

    _tag: str = ""
    _void: bool = False

    # Diff-tracking identity; pass explicitly to preserve across rebuilt trees.
    key: str = Field(default_factory=_new_key)

    # Common HTML attributes; more via Field(json_schema_extra={"html_attr": True}).
    id_: str | None = Field(default=None, alias="id", json_schema_extra={"html_attr": True})
    class_: str | None = Field(default=None, alias="class", json_schema_extra={"html_attr": True})

    container: list[DOMElement | str] = Field(default_factory=list)
    styles: Styles = Field(default_factory=Styles)
    args: dict[str, Any] = Field(default_factory=dict)
    # Scroll indicator control: when enabled (default) and the element's
    # overflow is auto/scroll, serialization auto-injects a
    # ``data-neony-scroll`` marker (x/y/true) that the JS engine turns
    # into a custom thumb + dynamic edge fade.  Not an html_attr — it is
    # a switch, not a rendered attribute of its own name.
    # Accepts a preset name for the thumb's rest/active look:
    #   "silent"  — hidden until hover/scroll, then a thin solid thumb
    #   "lighten" — faint thin thumb at rest, solid thin on hover/scroll
    #   "normal"  — faint thin at rest, solid wide on hover/scroll (default)
    #   "active"  — solid wide thumb always
    #   False     — suppress the indicator entirely
    #   True      — equivalent to "normal"
    scroll_indicator: bool | Literal["silent", "lighten", "normal", "active"] = Field(default=True)

    # In-app drag payload: when set, the element becomes draggable and the
    # engine hands this string to ``dataTransfer.setData`` on dragstart
    # (``application/x-neony``) — the synchronous hook the drag delegate
    # needs, since Python can't call setData in the dragstart event.  A
    # ``drop`` handler reads it back via ``DomEvent.drag_payload``.
    drag_payload: str | None = Field(default=None)

    # Fluent .on_xxx() handlers — PrivateAttr so callables never serialize.
    # Defaults are materialised in model_post_init: PrivateAttr(default_factory=...)
    # makes pydantic re-introspect the factory signature for EVERY element
    # construction, which dominates large-tree build time.
    _handlers: dict[str, list[Callable[..., Any]]] = PrivateAttr(default=cast(Any, None))

    # Dirty-subtree tracking: mutated elements re-serialize; the flag
    # propagates up via _parent so no ancestor reuses a stale snapshot.
    _dirty: bool = PrivateAttr(default=False)
    _parent: DOMElement | None = PrivateAttr(default=None)
    # Root-owned workset of elements directly mutated since the last render.
    # Keys are object ids because pydantic models are intentionally unhashable.
    _dirty_elements: dict[int, DOMElement] = PrivateAttr(default=cast(Any, None))

    # Opt-in event bubbling: events on handler-less descendants route here
    # (SidebarItem's icon/label spans; layout containers keep strict routing).
    _bubble_events: bool = PrivateAttr(default=False)

    @property
    def bubble_events(self) -> bool:
        """Public access to opt-in event bubbling.

        When True, an event dispatched to a handler-less descendant also
        reaches this element if it carries a matching handler — e.g. a
        click on SidebarItem's icon/label span bubbles to the item.
        Layout containers keep strict routing unless opted in.
        """
        return self._bubble_events

    @bubble_events.setter
    def bubble_events(self, value: bool) -> None:
        self._bubble_events = value

    # Mutation classification for the direct-patch fast path: style/attr
    # changes patch in place; structural changes (children, text, key)
    # force the full serialization + diff.  The bitmask only escalates
    # (style → structural) within one render cycle.
    _DIRTY_STYLES: ClassVar[int] = 1
    _DIRTY_ATTRS: ClassVar[int] = 2
    _DIRTY_STRUCTURAL: ClassVar[int] = 4
    _dirty_type: int = PrivateAttr(default=0)

    # Signal bindings, kept alive for unbind() (Signal → Effect → element).
    _bindings: list[Effect] = PrivateAttr(default=cast(Any, None))
    # Cached kebab-case attribute serialization; invalidated on public field
    # writes, raw args writes and Styles mutations.
    _serialized_attrs: dict[str, str] | None = PrivateAttr(default=None)
    # Armed by the app on each tree root so a bound-signal write schedules a render.
    _render_request: Callable[[], None] | None = PrivateAttr(default=None)
    # Armed by the app on each tree root so a component can run internal
    # JS without holding a window reference (scroll commands, caret reads).
    _eval_js_request: Callable[[str], Coroutine[Any, Any, Any]] | None = PrivateAttr(default=None)
    # Managed content: the bridge freezes diffing under this subtree after
    # the initial mount; live content (a contenteditable editor) is owned
    # by the JS engine and updated through internal commands, never by the
    # Python diff.  ``to_node`` always reuses the cached snapshot for a
    # managed root, so its children never generate patches.
    _managed_content: bool = PrivateAttr(default=False)
    # The display value bind_visible restores when the signal turns true.
    _visible_display: Literal["block", "flex", "grid", "inline", "inline-block", "inline-flex", "none"] | None = (
        PrivateAttr(default=None)
    )

    # ---- dirty tracking ----

    def model_post_init(self, __context: Any) -> None:
        """Materialise private collections and replace the plain container list."""
        # Defaults are set here rather than via PrivateAttr(default_factory=...)
        # to avoid pydantic's per-instance default-factory introspection.
        self._handlers = {}
        self._bindings = []
        self._dirty_elements = {}
        # object.__setattr__: the swap itself is not a mutation.
        object.__setattr__(self, "container", _Children(self, self.container))
        # Field-level styles mutations must reach the dirty tracker.
        if self.styles is not None:
            object.__setattr__(self.styles, "_owner", self)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if not name.startswith("_"):
            # Any public field write may change the rendered attributes.
            object.__setattr__(self, "_serialized_attrs", None)
            # Classify the mutation: styles/attrs patch in place; anything
            # else (container, key, ...) is structural and needs the full
            # serialization + diff path.
            if name == "styles":
                self._dirty_type |= self._DIRTY_STYLES
                if isinstance(value, Styles):
                    object.__setattr__(value, "_owner", self)
            elif name == "args":
                self._dirty_type |= self._DIRTY_ATTRS
            else:
                self._dirty_type |= self._DIRTY_STRUCTURAL
            self._mark_dirty()

    def _invalidate_attrs_cache(self) -> None:
        """Drop the cached attribute dict (Styles mutations can change the
        derived ``data-neony-scroll`` marker)."""
        object.__setattr__(self, "_serialized_attrs", None)

    def _mark_dirty(self) -> None:
        """Mark this element and every ancestor dirty and enqueue the
        directly changed element on the tree root's render workset."""
        node: DOMElement = self
        while True:
            node._dirty = True
            if node._parent is None:
                node._dirty_elements[id(self)] = self
                return
            node = node._parent

    def mark_dirty(self) -> None:
        """Explicitly mark this element (and its ancestors) as changed.
        Conservative: counts as structural, so the next render takes the
        full serialization + diff path."""
        self._dirty_type |= self._DIRTY_STRUCTURAL
        self._invalidate_attrs_cache()
        self._mark_dirty()

    # ---- signal bindings ----

    def _bind(self, write: Callable[[], None]) -> Effect:
        """Run *write* now and on dependency change, marking dirty and
        requesting a render through the root's ``_render_request``."""

        def run() -> None:
            write()
            self._mark_dirty()
            self._request_render()

        eff = effect(run)
        self._bindings.append(eff)
        return eff

    def _request_render(self) -> None:
        node: DOMElement | None = self
        while node is not None and node._parent is not None:
            node = node._parent
        if node is not None and node._render_request is not None:
            node._render_request()

    def bind_text(self, signal: Signal[Any] | Computed[Any], fmt: Callable[[Any], str] = str) -> Self:
        """Bind *signal* to this element's text: ``fmt(signal())`` now and
        on every change, replacing the children with a single string."""
        self._bind(lambda: self._set_text(fmt(signal())))
        return self

    def bind_style(
        self,
        signal: Signal[Any] | Computed[Any],
        prop: str,
        fmt: Callable[[Any], Any] | None = None,
    ) -> Self:
        """Bind *signal* to a style property (*prop* is a snake_case
        :class:`Styles` field name); a ``None`` value removes it."""
        apply = fmt if fmt is not None else (lambda v: v)
        self._bind(lambda: self._set_style(prop, apply(signal())))
        return self

    def bind_attr(
        self,
        signal: Signal[Any] | Computed[Any],
        name: str,
        fmt: Callable[[Any], Any] | None = None,
    ) -> Self:
        """Bind *signal* to an HTML attribute (written into ``args``).

        The default formatter passes bools through — ``True`` renders
        as a bare attribute, ``False`` / ``None`` removes it (a bool
        stringified to ``"False"`` would leave the attribute present,
        e.g. a permanently disabled button).  Other values are
        stringified; pass a custom ``fmt`` for anything else."""
        apply = fmt if fmt is not None else (lambda v: v if isinstance(v, bool) or v is None else str(v))
        self._bind(lambda: self._set_attr(name, apply(signal())))
        return self

    def bind_visible(self, signal: Signal[Any] | Computed[Any]) -> Self:
        """Truthy → shown (restoring the pre-binding ``display``),
        falsy → ``display: none``."""
        self._visible_display = self.styles.display
        self._bind(lambda: self._set_visible(bool(signal())))
        return self

    def unbind(self) -> Self:
        """Dispose every signal binding on this element."""
        for eff in self._bindings:
            eff.dispose()
        self._bindings.clear()
        return self

    # ---- binding internals ----

    def _set_text(self, text: str) -> None:
        self.container = [text]

    def _set_style(self, prop: str, value: Any) -> None:
        setattr(self.styles, prop, value if value is not None else None)
        self._dirty_type |= self._DIRTY_STYLES

    def _set_attr(self, name: str, value: Any) -> None:
        if value is None:
            self.args.pop(name, None)  # None removes the attribute
        else:
            self.args[name] = value  # bools render bare via _build_attrs
        self._invalidate_attrs_cache()
        self._dirty_type |= self._DIRTY_ATTRS

    def _set_visible(self, visible: bool) -> None:
        if visible:
            self.styles.display = self._visible_display
        else:
            self.styles.display = "none"
        self._dirty_type |= self._DIRTY_STYLES

    # ---- fluent event API ----

    def on(self, event_type: str, fn: Callable[..., Any]) -> DOMElement:
        """Register *fn* for *event_type* (called with a :class:`DomEvent`);
        returns self for chaining."""
        self._handlers.setdefault(event_type, []).append(fn)
        return self

    def on_click(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("click", fn)

    def on_outsideclick(self, fn: Callable[..., Any]) -> DOMElement:
        """Register for the synthetic ``outsideclick`` — fires when a
        click lands outside this element's subtree while it carries the
        ``data-neony-outside`` marker (see the JS engine)."""
        return self.on("outsideclick", fn)

    def on_dblclick(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("dblclick", fn)

    def on_input(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("input", fn)

    def on_change(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("change", fn)

    def on_submit(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("submit", fn)

    def on_keydown(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("keydown", fn)

    def on_keyup(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("keyup", fn)

    def on_focus(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("focus", fn)

    def on_blur(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("blur", fn)

    def on_mouseover(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mouseover", fn)

    def on_mouseout(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mouseout", fn)

    def on_mousedown(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mousedown", fn)

    def on_mouseup(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mouseup", fn)

    # NOTE: no on_mouseenter / on_mouseleave — native mouseenter/
    # mouseleave do not propagate, so the engine can never delegate
    # them.  Detect enter/leave from on_mouseover / on_mouseout via
    # ``DomEvent.related_key`` (the Tooltip component does this).

    def on_pointermove(self, fn: Callable[..., Any]) -> DOMElement:
        """Pointer movement — ``event.movement_x`` / ``event.movement_y``
        carry the delta since the last event; ``event.pointer_type`` is
        ``"mouse"``, ``"pen"``, or ``"touch"``."""
        return self.on("pointermove", fn)

    def on_transitionend(self, fn: Callable[..., Any]) -> DOMElement:
        """CSS transition finished — ``event.transition_property`` is
        the property that stopped transitioning; ``event.elapsed_time``
        how long it took."""
        return self.on("transitionend", fn)

    def on_animationstart(self, fn: Callable[..., Any]) -> DOMElement:
        """CSS animation started — ``event.animation_name`` is its name."""
        return self.on("animationstart", fn)

    def on_animationend(self, fn: Callable[..., Any]) -> DOMElement:
        """CSS animation finished — ``event.animation_name`` is its name,
        ``event.elapsed_time`` how long it ran."""
        return self.on("animationend", fn)

    def on_contextmenu(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("contextmenu", fn)

    def on_wheel(self, fn: Callable[..., Any]) -> DOMElement:
        """Wheel — ``event.delta_x`` / ``event.delta_y`` carry the deltas."""
        return self.on("wheel", fn)

    def on_scroll(self, fn: Callable[..., Any]) -> DOMElement:
        """Scroll — ``event.scroll_top`` / ``event.scroll_left`` carry the
        scrolled element's position (high-frequency; renders are deferred)."""
        return self.on("scroll", fn)

    def on_dragover(self, fn: Callable[..., Any]) -> DOMElement:
        """Dragover — fires continuously while a drag hovers this
        element; ``preventDefault`` (allowing the drop) is handled by
        the engine."""
        return self.on("dragover", fn)

    def on_dragleave(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("dragleave", fn)

    def on_dragstart(self, fn: Callable[..., Any]) -> DOMElement:
        """Dragstart — fires when a drag begins on a ``drag_payload``
        element (the payload rides in ``event.drag_payload``)."""
        return self.on("dragstart", fn)

    def on_dragend(self, fn: Callable[..., Any]) -> DOMElement:
        """Dragend — fires on the source element when the drag finishes
        (dropped or cancelled); the hook to clear drag state."""
        return self.on("dragend", fn)

    def on_dragenter(self, fn: Callable[..., Any]) -> DOMElement:
        """Dragenter — fires when a drag enters this element."""
        return self.on("dragenter", fn)

    def on_paste(self, fn: Callable[..., Any]) -> DOMElement:
        """Paste — ``event.clipboard_text`` / ``event.clipboard_html``
        carry the clipboard contents."""
        return self.on("paste", fn)

    def on_copy(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("copy", fn)

    def on_cut(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("cut", fn)

    def on_drop(self, fn: Callable[..., Any]) -> DOMElement:
        """Drop — ``event.drop_files`` carries a ``{name, path, size,
        type}`` dict per dropped file (``path`` empty on WKWebView)."""
        return self.on("drop", fn)

    # ---- internal helpers ----

    @staticmethod
    def _to_kebab(snake: str) -> str:
        """Convert ``snake_case`` to ``kebab-case``."""
        return snake.replace("_", "-")

    def _serialize_styles(self) -> dict[str, str]:
        """Serialize ``self.styles`` to a kebab-case dict, skipping None
        values and mirroring the WebKit/moz-prefixed variants.

        ``Styles`` caches its serialized form and invalidates it on field
        writes, so repeated render cycles never re-run ``model_dump()``.
        """
        if self.styles is None:
            return {}
        return self.styles._serialize_css()

    def _serialize_attrs(self) -> dict[str, str]:
        """Serialize HTML attributes to a ``{name: value}`` dict
        (booleans map to "" presence).

        The result is cached and invalidated by public field writes,
        ``_set_attr`` and ``Styles`` mutations.
        """
        cached = self._serialized_attrs
        if cached is not None:
            return cached
        attrs: dict[str, str] = {}
        for name, value in self._collect_attr_items():
            if isinstance(value, bool):
                if value:
                    attrs[name] = ""
            else:
                attrs[name] = str(value)
        object.__setattr__(self, "_serialized_attrs", attrs)
        return attrs

    def _build_styles(self) -> str:
        """Build the ``style="..."`` attribute string."""
        declarations = [f"{k}: {v}" for k, v in self._serialize_styles().items()]
        if not declarations:
            return ""
        return 'style="' + "; ".join(declarations) + '"'

    def _collect_attr_items(self) -> list[tuple[str, Any]]:
        """``(html_name, value)`` pairs: typed ``html_attr`` fields first
        (declaration order), then raw ``args`` (which can override them)."""
        items: list[tuple[str, Any]] = []
        cls = type(self)
        typed_fields = cls._HTML_ATTR_FIELDS_CACHE.get(cls)
        if typed_fields is None:
            fields: list[tuple[str, str]] = []
            for name, field in cls.model_fields.items():
                extra = field.json_schema_extra
                if isinstance(extra, dict) and extra.get("html_attr"):
                    html_name = field.alias or name
                    fields.append((name, html_name))
            typed_fields = tuple(fields)
            cls._HTML_ATTR_FIELDS_CACHE[cls] = typed_fields
        for name, html_name in typed_fields:
            value = getattr(self, name)
            if value is not None:
                items.append((html_name, value))
        for k, v in self.args.items():
            items.append((k, v))
        # Scroll-indicator auto-derivation: when scroll_indicator is on,
        # no explicit data-neony-scroll was given, and an axis is actually
        # scrollable (overflow auto/scroll), inject the marker so the JS
        # engine builds a thumb + dynamic edge fade on this surface.
        # Axis: overflow_y scrollable → "y", overflow_x → "x", both →
        # "true" (JS resolves which way at runtime).  A preset name
        # (silent/lighten/normal/active) rides as a suffix so the JS
        # engine picks the thumb's rest/active look.
        si = self.scroll_indicator
        if si and not any(k == "data-neony-scroll" for k, _ in items):
            # normal is the default preset — no suffix (keeps the marker
            # lean for the common case).
            suffix = "" if si is True or si == "normal" else f"-{si}"
            oy = self.styles.overflow_y or self.styles.overflow
            ox = self.styles.overflow_x or self.styles.overflow
            scrolls_y = oy in ("auto", "scroll")
            scrolls_x = ox in ("auto", "scroll")
            if scrolls_y and scrolls_x:
                items.append(("data-neony-scroll", f"true{suffix}"))
            elif scrolls_y:
                items.append(("data-neony-scroll", f"y{suffix}"))
            elif scrolls_x:
                items.append(("data-neony-scroll", f"x{suffix}"))
        # In-app drag payload: ``drag_payload`` becomes ``draggable="true"``
        # (HTML draggable — what actually starts a drag) plus a
        # ``data-neony-drag`` marker carrying the payload the JS engine
        # passes to ``dataTransfer.setData`` on dragstart.  ``draggable``
        # is an *enumerated* attribute (not a presence boolean like
        # ``checked``): a bare/empty value resolves to "auto" and a plain
        # div stays un-draggable, so the literal "true" is required.
        if self.drag_payload is not None and not any(k == "data-neony-drag" for k, _ in items):
            items.append(("draggable", "true"))
            items.append(("data-neony-drag", self.drag_payload))
        return items

    def _build_attrs(self) -> list[str]:
        """All HTML attribute segments — ``key="value"``, bare ``key`` for True booleans."""
        attrs: list[str] = []

        # data-neony-key for DOM identity (always rendered)
        attrs.append(f'data-neony-key="{self.key}"')

        for name, value in self._collect_attr_items():
            if isinstance(value, bool):
                if value:
                    attrs.append(name)  # bare boolean attribute
            else:
                attrs.append(f'{name}="{value}"')

        return attrs

    # ---- public API ----

    def build(self) -> str:
        """Render this element and all descendants to an HTML string."""
        children: list[str] = []
        for item in self.container:
            if isinstance(item, DOMElement):
                children.append(item.build())
            else:
                children.append(item)

        parts: list[str] = [self._tag]

        style_str = self._build_styles()
        if style_str:
            parts.append(style_str)

        attrs = self._build_attrs()
        if attrs:
            parts.extend(attrs)

        opening = " ".join(parts)

        if self._void:
            return f"<{opening} />"

        return f"<{opening}>{''.join(children)}</{self._tag}>"

    # ---- serialization for reactive bridge ----

    def to_node(self, snapshot_cache: dict[str, NodeDescriptor] | None = None) -> NodeDescriptor:
        """Serialize this element and descendants to a JSON-safe
        :class:`NodeDescriptor`.

        With *snapshot_cache*, clean elements reuse their cached snapshot
        (dirty-subtree tracking); serialized nodes are cached and their
        dirty flag cleared.  Raises ValueError on duplicate keys or mixed
        string/element children.
        """
        seen_keys: set[str] = set()
        node = self._to_node_impl(seen_keys, snapshot_cache)
        self._dirty_elements.clear()
        return node

    def _to_node_impl(
        self,
        seen_keys: set[str],
        snapshot_cache: dict[str, NodeDescriptor] | None = None,
    ) -> NodeDescriptor:
        if self.key in seen_keys:
            raise ValueError(f"Duplicate key {self.key!r} in DOM tree. Each element must have a unique key.")
        seen_keys.add(self.key)

        # Managed subtrees freeze after their first snapshot: the live DOM
        # under them is owned by the JS engine (contenteditable editors),
        # so re-serializing Python-side changes would fight the user's
        # caret / IME / insertion state.  Return the cached node instead.
        if self._managed_content and snapshot_cache is not None:
            cached = snapshot_cache.get(self.key)
            if cached is not None:
                return cached

        # Clean element → reuse the cached snapshot (dirty flags propagate
        # to ancestors, so a clean element implies a clean subtree).
        if snapshot_cache is not None and not self._dirty:
            cached = snapshot_cache.get(self.key)
            if cached is not None:
                return cached

        styles = self._serialize_styles()
        attrs = self._serialize_attrs()

        # Children: recurse, handle text-vs-element rules
        text: str | None = None
        children: list[NodeDescriptor] = []

        has_strings = False
        has_elements = False
        for item in self.container:
            if isinstance(item, DOMElement):
                has_elements = True
            else:
                has_strings = True

        if has_strings and has_elements:
            raise ValueError(
                f"Element {self.key!r} ({self._tag}): mixed string and element "
                f"children are not supported in reactive mode. "
                f"Use text-only or element-only children."
            )

        if self._void:
            pass
        elif has_strings:
            text = "".join(str(item) for item in self.container)
        else:
            for item in self.container:
                if isinstance(item, DOMElement):
                    children.append(item._to_node_impl(seen_keys, snapshot_cache))

        node = NodeDescriptor(
            key=self.key,
            tag=self._tag,
            attrs=attrs,
            styles=styles,
            text=text,
            children=children,
        )
        if snapshot_cache is not None:
            snapshot_cache[self.key] = node
        self._dirty = False
        self._dirty_type = 0
        return node
