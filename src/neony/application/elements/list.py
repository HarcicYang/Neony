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

_ROW_ACTIVE = _ROW_BASE.model_copy(
    update={
        "background_color": stub.surface,
        "color": stub.text_primary,
    }
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
        self._row_by_key: dict[str, Div] = {}
        self._selected_key: str | None = None
        # Keyboard focus ring — only present after arrow navigation;
        # a mouse click selects and clears it (mirrors Tree).
        self._focus_key: str | None = None

        self._root = Div(
            styles=_LIST_ROOT,
            args={"role": "listbox"},
            scroll_indicator=edge_fade,
        )
        for item in items:
            self.add(item)
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
        if key in self._row_by_key:
            raise ValueError(f"List: duplicate item key {key!r}")
        entry.key = key  # persist the resolved identity
        reactive_label = entry.icon is None and not isinstance(entry.label, str)
        row = Div(
            container=[] if reactive_label else self._label_content(entry),
            styles=_ROW_ACTIVE if key == self._selected_key else _ROW_BASE,
            args={"role": "option", "tabindex": "0", "aria-selected": "true" if key == self._selected_key else "false"},
            key=f"row:{key}",
        )
        # A reactive bare label (no icon) binds live via _mount_text.
        if reactive_label:
            _mount_text(row, entry.label)
        # Clicks land on the icon/label spans — bubble them to this row.
        row.bubble_events = True
        row.on_click(self._make_click_handler(key))
        row.on("keydown", self._make_keydown_handler(key))
        self._root.container.append(row)
        self._row_by_key[key] = row
        self._keys.append(key)
        self._items.append(entry)
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
        if value is not None and value not in self._row_by_key:
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
        self._selected_key = key
        for row_key, row in self._row_by_key.items():
            active = row_key == key
            row.styles = _ROW_ACTIVE if active else _ROW_BASE
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
        row = self._row_by_key.get(key)
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
            index = self._keys.index(from_key)
        except ValueError:
            return
        target = index + step
        if target < 0 or target >= len(self._keys):
            return
        await self._dispatch_change(self._keys[target], event)

    async def _move_to(self, target: int, event: DomEvent) -> None:
        if not self._keys:
            return
        await self._dispatch_change(self._keys[target], event)
