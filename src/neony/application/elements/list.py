"""List component — a scrollable, single-select data list.

A :class:`List` renders a flat column of :class:`ListItem` entries in a
scroll container.  Exactly one entry is selected at a time; selection is
the listbox model — arrow keys move the selection directly (each move
fires ``change``), Home/End jump to the ends, Enter/Space select the
focused row, and a click selects.  Rows mirror the :class:`Tree`
/ :class:`Sidebar` row recipe: rounded, transparent, with a themed
``surface`` fill on the active row and an accent focus ring (which
always follows the selection).

Usage::

    items = List("Alice", "Bob", ListItem("Carol", key="carol", icon=Icon.glyph("⭐")), active_key="Bob")
    items.on_change(lambda e: print(e.value))   # selected key
    items.selected_key = "carol"                 # programmatic, no callback
    items.children("Dave", "Eve")                # chainable append

Mounting contract: the list is self-bounding — it fills the height its
flex parent allocates and scrolls its rows internally.  It must be
mounted in a flex container with a *definite* height (e.g. a
``VStack(..., grow=1)`` or ``GlassPanel(grow=True)``); a bare block
parent with auto height gives it nothing to bound against and the list
pushes the page open instead of scrolling.
"""

from __future__ import annotations

from typing import Self

from neony.application.theme import stub
from neony.dom import Color, Div, DOMElement, DomEvent, Span, Styles, Transition

from .base import Component, ReactiveText, _mount_text
from .icon import Icon

_ROW_BASE = Styles(
    display="flex",
    align_items="center",
    gap="8px",
    padding="8px 12px",
    border_radius="8px",
    font_size="14px",
    cursor="pointer",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    white_space="nowrap",
    overflow="hidden",
    text_overflow="ellipsis",
    user_select="none",
    transition=Transition(property="background-color", duration="0.15s", timing="ease"),
)

_ROW_VIRTUAL = _ROW_BASE.model_copy(
    update={"line_height": "16px", "height": "16px", "min_height": "16px", "flex_shrink": "0"}
)

_LIST_ROOT = Styles(
    display="flex",
    flex_direction="column",
    gap="2px",
    padding="8px",
    flex_grow="1",
    flex_basis="0",
    min_height="0",
    overflow_y="auto",
    overflow_x="hidden",
)


class ListItem:
    """One entry in a :class:`List`.

    ``label`` is the entry text (first positional argument); ``key`` is
    the entry's identity for ``selected_key`` / ``change`` payloads and
    defaults to the label (pass an explicit key when labels collide);
    ``icon`` is an optional :class:`Icon` shown before the label.
    """

    __slots__ = ("icon", "key", "label")

    def __init__(self, label: ReactiveText, *, key: str | None = None, icon: Icon | None = None) -> None:
        self.label = label
        self.key = key
        self.icon = icon


class List(Component):
    # Private automatic virtualization policy; public APIs stay unchanged.
    _VIRTUALIZE_THRESHOLD = 200
    _VIRTUAL_ROW_HEIGHT = 34
    _VIRTUAL_OVERSCAN = 8

    #: Event types wired internally (via custom per-row handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click", "keydown"})

    def __init__(
        self,
        *items: str | ListItem,
        active_key: str | None = None,
        edge_fade: bool = True,
    ) -> None:
        super().__init__()
        self._items: list[ListItem] = []
        self._keys: list[str] = []
        self._key_index: dict[str, int] = {}
        self._row_by_key: dict[str, Div] = {}
        self._selected_key: str | None = None
        self._virtualized = False
        self._virtual_start = 0
        self._virtual_end = 0
        self._viewport_height = self._VIRTUAL_ROW_HEIGHT * 10
        self._top_spacer = Div(styles=Styles(height="0px", flex_shrink="0"))
        self._bottom_spacer = Div(styles=Styles(height="0px", flex_shrink="0"))
        self._initializing = True
        # Keyboard focus ring — only present after arrow navigation;
        # a mouse click selects and clears it (mirrors Tree).
        self._focus_key: str | None = None

        self._root = Div(
            styles=_LIST_ROOT,
            args={"role": "listbox"},
            scroll_indicator=edge_fade,
        )
        self._root.on("scroll", self._handle_scroll)
        for item in items:
            self.add(item)
        self._initializing = False
        if self._virtualized:
            self._refresh_window(0, self._viewport_height, force=True)
        if active_key is not None:
            self.selected_key = active_key

    # ---- public API ----

    def add(self, item: str | ListItem) -> Self:
        """Append an entry (chainable).  Strings are wrapped as
        :class:`ListItem` (key = the label)."""
        entry = item if isinstance(item, ListItem) else ListItem(item)
        # A reactive label cannot serve as the entry's identity key — require
        # an explicit key in that case.
        key = entry.key
        if key is None:
            if not isinstance(entry.label, str):
                raise ValueError("List: a reactive label needs an explicit key")
            key = entry.label
        if key in self._key_index:
            raise ValueError(f"List: duplicate item key {key!r}")
        entry.key = key  # persist the resolved identity
        self._key_index[key] = len(self._keys)
        self._keys.append(key)
        self._items.append(entry)

        was_virtualized = self._virtualized
        self._virtualized = len(self._items) > self._VIRTUALIZE_THRESHOLD
        if self._virtualized and not self._initializing:
            self._refresh_window(self._virtual_start * self._VIRTUAL_ROW_HEIGHT, self._viewport_height, force=True)
        elif not was_virtualized:
            row = self._make_row(entry)
            self._root.container.append(row)
            self._row_by_key[key] = row
        return self

    def children(self, *items: str | ListItem) -> Self:
        """Append several entries (chainable) — see :meth:`add`."""
        for item in items:
            self.add(item)
        return self

    @property
    def items(self) -> list[ListItem]:
        """All entries, in render order."""
        return list(self._items)

    @property
    def selected_key(self) -> str | None:
        return self._selected_key

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is not None and value not in self._key_index:
            raise ValueError(f"List.selected_key: unknown key {value!r}")
        self._select(value)
        self._mirror_selected(value)

    @property
    def active_key(self) -> str | None:
        """Deprecated alias of :attr:`selected_key`."""
        return self._selected_key

    @active_key.setter
    def active_key(self, value: str | None) -> None:
        self.selected_key = value

    # ---- internals ----

    def _row_style(self, active: bool) -> Styles:
        base = _ROW_VIRTUAL if self._virtualized else _ROW_BASE
        if not active:
            return base
        return base.model_copy(update={"background_color": stub.surface, "color": stub.text_primary})

    def _make_row(self, entry: ListItem) -> Div:
        key = entry.key
        assert key is not None
        reactive_label = entry.icon is None and not isinstance(entry.label, str)
        row = Div(
            container=[] if reactive_label else self._label_content(entry),
            styles=self._row_style(key == self._selected_key),
            args={"role": "option", "tabindex": "0", "aria-selected": "true" if key == self._selected_key else "false"},
            key=f"row:{key}",
        )
        if reactive_label:
            _mount_text(row, entry.label)
        row.bubble_events = True
        row.on_click(self._make_click_handler(key))
        row.on("keydown", self._make_keydown_handler(key))
        return row

    def _refresh_window(self, scroll_top: int = 0, viewport_height: int | None = None, *, force: bool = False) -> None:
        if not self._virtualized:
            return
        height = max(self._VIRTUAL_ROW_HEIGHT, viewport_height or self._viewport_height)
        self._viewport_height = height
        visible = max(1, (height + self._VIRTUAL_ROW_HEIGHT - 1) // self._VIRTUAL_ROW_HEIGHT)
        window_size = visible + self._VIRTUAL_OVERSCAN * 2
        requested = max(0, scroll_top // self._VIRTUAL_ROW_HEIGHT - self._VIRTUAL_OVERSCAN)
        start = min(requested, max(0, len(self._items) - window_size))
        end = min(len(self._items), start + window_size)
        if not force and start == self._virtual_start and end == self._virtual_end:
            return
        self._virtual_start, self._virtual_end = start, end
        for row in self._row_by_key.values():
            self._dispose_row(row)
        rows = [self._make_row(entry) for entry in self._items[start:end]]
        self._row_by_key = dict(zip(self._keys[start:end], rows, strict=True))
        self._top_spacer.styles = Styles(height=f"{start * self._VIRTUAL_ROW_HEIGHT}px", flex_shrink="0")
        remaining = max(0, len(self._items) - end)
        self._bottom_spacer.styles = Styles(height=f"{remaining * self._VIRTUAL_ROW_HEIGHT}px", flex_shrink="0")
        self._root.container[:] = [self._top_spacer, *rows, self._bottom_spacer]

    def _dispose_row(self, row: DOMElement) -> None:
        row.unbind()
        for child in row.container:
            if isinstance(child, DOMElement):
                self._dispose_row(child)

    def _ensure_materialized(self, key: str) -> Div | None:
        row = self._row_by_key.get(key)
        if row is not None or not self._virtualized:
            return row
        self._refresh_window(self._key_index[key] * self._VIRTUAL_ROW_HEIGHT, self._viewport_height, force=True)
        return self._row_by_key.get(key)

    def _handle_scroll(self, event: DomEvent) -> None:
        if self._virtualized:
            self._refresh_window(event.scroll_top or 0, event.client_height or self._viewport_height)

    def _label_content(self, entry: ListItem) -> list[DOMElement | ReactiveText]:
        # Element-only children when an icon is present (reactive mode
        # forbids mixing); a bare string otherwise.
        if entry.icon is not None:
            span = Span()
            if isinstance(entry.label, str):
                span.container = [entry.label]
            else:
                _mount_text(span, entry.label)
            return [entry.icon.render("14px"), span]
        return [entry.label]

    def _select(self, key: str | None, *, focused: bool = False) -> None:
        previous = self._selected_key
        self._selected_key = key
        for row_key in (previous, key):
            if row_key is None:
                continue
            row = self._row_by_key.get(row_key)
            if row is None:
                continue
            active = row_key == key
            row.styles = self._row_style(active)
            row.args = {**row.args, "aria-selected": "true" if active else "false"}
        if focused and key is not None:
            self._set_focus(key)
        else:
            self._clear_focus()

    def _set_focus(self, key: str) -> None:
        if self._focus_key == key:
            return
        self._clear_focus()
        self._focus_key = key
        if self._virtualized and key not in self._row_by_key:
            top = self._key_index[key] * self._VIRTUAL_ROW_HEIGHT
            self._schedule_js(f"window.neony.scrollTo({self._root.key!r}, {top}, 'auto')")
        row = self._ensure_materialized(key)
        if row is not None:
            row.styles = row.styles.model_copy(update={"box_shadow": "0 0 0 2px var(--color-accent)"})

    def _clear_focus(self) -> None:
        if self._focus_key is None:
            return
        row = self._row_by_key.get(self._focus_key)
        if row is not None:
            row.styles = row.styles.model_copy(update={"box_shadow": None})
        self._focus_key = None

    def _make_click_handler(self, key: str):
        async def handler(event: DomEvent) -> None:
            self._select(key)
            event.value = key
            event.source = "user"
            await self._dispatch("change", event)

        return handler

    def _make_keydown_handler(self, key: str):
        async def handler(event: DomEvent) -> None:
            k = event.value
            if k in ("Enter", " "):
                await self._dispatch_change(key, event)
            elif k == "ArrowDown":
                await self._move(1, key, event)
            elif k == "ArrowUp":
                await self._move(-1, key, event)
            elif k == "Home":
                await self._move_to(0, event)
            elif k == "End":
                await self._move_to(len(self._keys) - 1, event)

        return handler

    async def _dispatch_change(self, key: str, event: DomEvent) -> None:
        self._select(key, focused=True)
        event.value = key
        event.source = "user"
        await self._dispatch("change", event)

    async def _move(self, step: int, from_key: str, event: DomEvent) -> None:
        """Move the selection by *step* rows, clamped at the ends (no
        wrap) — only fires ``change`` when the selection actually moves."""
        try:
            index = self._key_index[from_key]
        except KeyError:
            return
        target = index + step
        if target < 0 or target >= len(self._keys):
            return
        await self._dispatch_change(self._keys[target], event)

    async def _move_to(self, target: int, event: DomEvent) -> None:
        if not self._keys:
            return
        await self._dispatch_change(self._keys[target], event)
