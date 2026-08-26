"""DataTable component — column config, sorting, and row selection.

A :class:`DataTable` renders a tabular data view from a :class:`Column`
configuration and a list of row dicts.  Columns are laid out with CSS
grid (``grid-template-columns`` derived from each column's ``width``);
the header is sticky — it stays put while the body scrolls under it.
A sortable header sorts the table on click; rows are selectable, either
single (``selection="single"``, the default) or multi
(``selection="multi"``).

Usage::

    table = DataTable(
        columns=[
            Column("Name", key="name", sortable=True, width="2fr"),
            Column("Age", key="age", sortable=True, align="right", width="80px"),
            Column("Role", key="role"),
        ],
        rows=[
            {"name": "Alice", "age": 30, "role": "Eng"},
            {"name": "Bob", "age": 24, "role": "Design"},
        ],
        row_key=lambda row: row["name"],   # default: row index
    )
    table.on_change(lambda e: print(e.value))   # selected row key
    table.sort_by = ("age", "desc")
    table.selected_key = "Alice"                 # programmatic, no callback

Columns and rows can also be appended chainably::

    DataTable(selection="multi").column(Column("Name", sortable=True)).row({"name": "Alice"})

Mounting contract: the table is self-bounding — it fills the height its
flex parent allocates and scrolls its rows internally (the header
sticks).  It must be mounted in a flex container with a *definite*
height (e.g. a ``VStack(..., grow=1)`` or ``GlassPanel(grow=True)``); a
bare block parent with auto height gives it nothing to bound against and
the table pushes the page open instead of scrolling.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cmp_to_key
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict

from neony.application.theme import stub
from neony.dom import Border, Color, Div, DOMElement, DomEvent, Signal, Span, Styles, Transition
from neony.dom.reactive import Computed

from .base import Component, ReactiveText, _mount_text
from .icon import Icon

# ---- shared row / cell recipes ----

_ROW_BASE = Styles(
    display="grid",
    align_items="center",
    border_radius="8px",
    cursor="pointer",
    background_color=Color(name="transparent"),
    transition=Transition(property="background-color", duration="0.15s", timing="ease"),
)

_ROW_ACTIVE = _ROW_BASE.model_copy(
    update={
        "background_color": stub.accent,
        "color": stub.on_accent,
    }
)

_CELL = Styles(
    padding="8px 12px",
    font_size="14px",
    color=stub.text_primary,
    white_space="nowrap",
    overflow="hidden",
    text_overflow="ellipsis",
)

_HEADER_CELL = Styles(
    display="flex",
    align_items="center",
    gap="4px",
    padding="10px 12px",
    font_size="12px",
    font_weight="600",
    color=stub.text_secondary,
    white_space="nowrap",
    overflow="hidden",
    text_overflow="ellipsis",
    user_select="none",
)

_HEADER = Styles(
    display="grid",
    align_items="center",
    position="sticky",
    top="0",
    z_index="1",
    background_color=stub.surface_raised,
    border_bottom=Border(width="1px", color=stub.border),
)

_ROOT = Styles(
    display="flex",
    flex_direction="column",
    flex_grow="1",
    flex_basis="0",
    min_height="0",
    overflow="auto",
)

_BODY = Styles(display="flex", flex_direction="column", gap="2px")

_GLYPH = Styles(font_size="10px", color=stub.text_secondary, flex_shrink="0")
_GLYPH_ACTIVE = _GLYPH.model_copy(update={"color": Color(var="--color-accent")})

_ALIGN_JUSTIFY = {"left": "flex-start", "center": "center", "right": "flex-end"}


def _compare(a: Any, b: Any) -> int:
    """Type-aware comparison — numeric values sort numerically, everything
    else by str.  Avoids Python's ``str < int`` TypeError on mixed cells."""
    if (
        isinstance(a, (int, float))
        and isinstance(b, (int, float))
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        return (a > b) - (a < b)
    sa, sb = str(a), str(b)
    return (sa > sb) - (sa < sb)


class Column(BaseModel):
    """One table column.

    - ``title`` — the header text (first positional argument)
    - ``key`` — the row-dict key this column reads; defaults to the
      lowercased title
    - ``width`` — a CSS grid track, e.g. ``"1fr"`` (default) or
      ``"80px"``; fixed widths let the table scroll horizontally
    - ``sortable`` — header click sorts by this column
    - ``align`` — ``left`` / ``center`` / ``right`` cell + header alignment
    - ``format`` — optional ``(value) -> str`` cell formatter
    - ``sort_key`` — optional ``(row) -> value`` override for sorting
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: ReactiveText
    key: str | None = None
    width: str | None = None
    sortable: bool = False
    align: Literal["left", "center", "right"] | None = None
    format: Callable[[Any], str] | None = None
    sort_key: Callable[[dict], Any] | None = None

    def __init__(
        self,
        title: ReactiveText = "",
        *,
        key: str | None = None,
        width: str | None = None,
        sortable: bool = False,
        align: Literal["left", "center", "right"] | None = None,
        format: Callable[[Any], str] | None = None,
        sort_key: Callable[[dict], Any] | None = None,
    ) -> None:
        # Hand-written __init__ so ``title`` is positional, like the
        # component constructors (pydantic v2 only takes keywords).
        super().__init__(
            title=title,
            key=key,
            width=width,
            sortable=sortable,
            align=align,
            format=format,
            sort_key=sort_key,
        )

    @property
    def resolved_key(self) -> str:
        """The key — explicit, else lowercased title (title must be a str)."""
        if self.key is None:
            if not isinstance(self.title, str):
                raise ValueError("Column: a reactive title needs an explicit key")
            self.key = self.title.lower()
        return self.key


class DataTable(Component):
    #: Event types wired internally (via custom per-row handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset({"click", "keydown"})

    def __init__(
        self,
        columns: list[Column] | None = None,
        rows: list[dict] | None = None,
        *,
        row_key: Callable[[dict], str] | None = None,
        selection: Literal["single", "multi"] = "single",
        active_key: str | None = None,
        selected_keys: set[str] | None = None,
        edge_fade: bool = True,
    ) -> None:
        if selection not in ("single", "multi"):
            raise ValueError(f"DataTable: selection must be 'single' or 'multi', got {selection!r}")
        super().__init__()
        self._columns = list(columns) if columns else []
        self._selection = selection
        self._row_key_fn = row_key
        self._data: list[dict] = []
        self._display: list[dict] = []
        self._row_keys: list[str] = []
        self._row_by_key: dict[str, Div] = {}
        self._sort: tuple[str, str] | None = None
        self._selected: set[str] = set()
        self._focus_key: str | None = None
        self._glyphs: dict[str, Span] = {}
        self._header_cells: dict[str, Div] = {}

        self._grid = " ".join(c.width or "1fr" for c in self._columns) or "1fr"
        self._row_base = _ROW_BASE.model_copy(update={"grid_template_columns": self._grid})
        self._row_active = _ROW_ACTIVE.model_copy(update={"grid_template_columns": self._grid})

        # Build header/body first, then construct the root WITH the
        # container — model_post_init wraps it in _Children (which sets
        # each child's _parent).  Reassigning container later with a plain
        # list would drop the parent links and break dirty propagation.
        self._header = self._build_header()
        self._body = Div(styles=_BODY)
        self._root = Div(
            styles=_ROOT,
            scroll_indicator=edge_fade,
            container=[self._header, self._body],
        )

        if rows is not None:
            self._data = list(rows)
        self._rebuild_rows()
        if active_key is not None:
            self.selected_key = active_key
        if selected_keys is not None:
            self.selected_keys = selected_keys

    # ---- public API ----

    @property
    def columns(self) -> list[Column]:
        """The column configuration (read-only)."""
        return list(self._columns)

    def column(self, column: Column | str) -> Self:
        """Append a column (chainable).  Strings are wrapped as
        :class:`Column`.  Adding a column rebuilds the header (grid
        tracks) and every body row."""
        col = column if isinstance(column, Column) else Column(column)
        key = col.resolved_key
        if self._column_by_key(key) is not None:
            raise ValueError(f"DataTable: duplicate column key {key!r}")
        self._columns.append(col)
        self._grid = " ".join(c.width or "1fr" for c in self._columns)
        self._row_base = _ROW_BASE.model_copy(update={"grid_template_columns": self._grid})
        self._row_active = _ROW_ACTIVE.model_copy(update={"grid_template_columns": self._grid})
        self._header = self._build_header()
        # __setitem__ on the _Children proxy replaces the old header and
        # keeps the parent link in sync.
        self._root.container[0] = self._header
        self._rebuild_rows()
        return self

    @property
    def rows(self) -> list[dict]:
        """The data rows in construction order (unaffected by sorting)."""
        return list(self._data)

    @rows.setter
    def rows(self, value: list[dict]) -> None:
        self._data = list(value)
        self._rebuild_rows()

    def row(self, data: dict) -> Self:
        """Append a data row (chainable).  Rebuilds the body to keep the
        sort order and selection."""
        self._data.append(dict(data))
        self._rebuild_rows()
        return self

    @property
    def sort_by(self) -> tuple[str, str] | None:
        """The active sort — ``(column_key, "asc"|"desc")`` or ``None``."""
        return self._sort

    @sort_by.setter
    def sort_by(self, value: tuple[str, str] | None) -> None:
        if value is not None:
            col_key, direction = value
            if direction not in ("asc", "desc"):
                raise ValueError(f"DataTable.sort_by: direction must be 'asc' or 'desc', got {direction!r}")
            col = self._column_by_key(col_key)
            if col is None or not col.sortable:
                raise ValueError(f"DataTable.sort_by: {col_key!r} is not a sortable column")
        self._sort = value
        self._rebuild_rows()
        self._update_sort_glyphs()

    @property
    def selected_key(self) -> str | None:
        """The selected row key (``selection="single"`` only)."""
        if self._selection != "single":
            raise NotImplementedError("DataTable.selected_key: requires selection='single'; use selected_keys")
        return next(iter(self._selected), None)

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if self._selection != "single":
            raise NotImplementedError("DataTable.selected_key: requires selection='single'; use selected_keys")
        if value is not None and value not in self._row_by_key:
            raise ValueError(f"DataTable.selected_key: unknown row key {value!r}")
        previous = self._selected
        self._selected = {value} if value is not None else set()
        self._apply_selection(previous ^ self._selected)
        self._mirror_selected(value)

    @property
    def selected_keys(self) -> frozenset[str]:
        """The selected row keys (``selection="multi"`` only)."""
        if self._selection != "multi":
            raise NotImplementedError("DataTable.selected_keys: requires selection='multi'; use selected_key")
        return frozenset(self._selected)

    @selected_keys.setter
    def selected_keys(self, value: set[str] | frozenset[str] | list[str] | None) -> None:
        if self._selection != "multi":
            raise NotImplementedError("DataTable.selected_keys: requires selection='multi'; use selected_key")
        keys = set(value) if value is not None else set()
        for key in keys:
            if key not in self._row_by_key:
                raise ValueError(f"DataTable.selected_keys: unknown row key {key!r}")
        previous = self._selected
        self._selected = keys
        self._apply_selection(previous ^ self._selected)

    def bind_selected(self, signal: Signal[Any] | Computed[Any]) -> Self:
        """Bind a signal to the selection (``selection="single"`` only) —
        see :meth:`Component.bind_selected`."""
        if self._selection != "single":
            raise ValueError("DataTable.bind_selected: requires selection='single'; read selected_keys instead")
        return super().bind_selected(signal)

    # ---- internals: header ----

    def _build_header(self) -> Div:
        header = Div(styles=_HEADER.model_copy(update={"grid_template_columns": self._grid}))
        self._header_cells = {}
        for col in self._columns:
            styles = _HEADER_CELL
            if col.align:
                styles = styles.model_copy(update={"justify_content": _ALIGN_JUSTIFY[col.align]})
            cell = Div(
                container=self._header_content(col),
                styles=styles,
                args={"role": "columnheader"},
            )
            self._header_cells[col.resolved_key] = cell
            if col.sortable:
                cell.styles = cell.styles.model_copy(update={"cursor": "pointer"})
                # Clicks land on the title / glyph spans — bubble them.
                cell.bubble_events = True
                cell.on_click(self._make_sort_handler(col.resolved_key))
            header.container.append(cell)
        return header

    def _header_content(self, col: Column) -> list[DOMElement | str]:
        title_span = Span()
        _mount_text(title_span, col.title)
        parts: list[DOMElement | str] = [title_span]
        if col.sortable:
            glyph = Span(container=[Icon._font("unfold_more").render("10px")], styles=_GLYPH)
            self._glyphs[col.resolved_key] = glyph
            parts.append(glyph)
        return parts

    def _make_sort_handler(self, col_key: str):
        async def handler(event: DomEvent) -> None:
            self._toggle_sort(col_key)
            event.value = col_key
            event.source = "user"
            await self._dispatch("sort", event)

        return handler

    def _toggle_sort(self, col_key: str) -> None:
        if self._sort is not None and self._sort[0] == col_key:
            direction = "desc" if self._sort[1] == "asc" else "asc"
        else:
            direction = "asc"
        self._sort = (col_key, direction)
        self._rebuild_rows()
        self._update_sort_glyphs()

    def _update_sort_glyphs(self) -> None:
        active_col = self._sort[0] if self._sort is not None else None
        active_dir = self._sort[1] if self._sort is not None else None
        for col_key, glyph in self._glyphs.items():
            if col_key == active_col:
                glyph.container = [
                    Icon._font("arrow_upward" if active_dir == "asc" else "arrow_downward").render("10px")
                ]
                glyph.styles = _GLYPH_ACTIVE
            else:
                glyph.container = [Icon._font("unfold_more").render("10px")]
                glyph.styles = _GLYPH

    # ---- internals: rows ----

    def _rebuild_rows(self) -> None:
        self._display = self._sorted(self._data)
        self._row_keys = []
        self._row_by_key = {}
        self._body.container.clear()
        for index, row in enumerate(self._display):
            key = self._row_key(row, index)
            if key in self._row_by_key:
                raise ValueError(f"DataTable: duplicate row key {key!r}")
            row_el = self._build_row(key, row)
            self._body.container.append(row_el)
            self._row_by_key[key] = row_el
            self._row_keys.append(key)
        # Drop selections whose rows no longer exist (rows replaced).
        self._selected &= set(self._row_keys)
        self._apply_selection(set(self._row_keys))

    def _row_key(self, row: dict, index: int) -> str:
        if self._row_key_fn is not None:
            return self._row_key_fn(row)
        return str(index)

    def _build_row(self, key: str, row: dict) -> Div:
        row_el = Div(
            container=[self._cell(col, row) for col in self._columns],
            styles=self._row_base,
            args={"role": "row", "tabindex": "0", "aria-selected": "false"},
            key=f"row:{key}",
        )
        # Clicks land on the cell divs — bubble them to this row.
        row_el.bubble_events = True
        row_el.on_click(self._make_click_handler(key))
        row_el.on("keydown", self._make_keydown_handler(key))
        return row_el

    def _cell(self, col: Column, row: dict) -> Div:
        value = row.get(col.resolved_key, "")
        if col.format is not None:
            text: ReactiveText = col.format(value)
        elif value is None:
            text = ""
        elif isinstance(value, (Signal, Computed)):
            text = value
        else:
            text = str(value)
        styles = _CELL.model_copy(update={"text_align": col.align or "left"})
        cell = Div(styles=styles, args={"role": "cell"})
        _mount_text(cell, text)
        return cell

    def _column_by_key(self, key: str) -> Column | None:
        for col in self._columns:
            if col.resolved_key == key:
                return col
        return None

    def _sorted(self, data: list[dict]) -> list[dict]:
        if self._sort is None:
            return list(data)
        col_key, direction = self._sort
        col = self._column_by_key(col_key)
        if col is None or not col.sortable:
            return list(data)

        def column_value(row: dict) -> Any:
            if col.sort_key is not None:
                return col.sort_key(row)
            return row.get(col_key, "")

        def row_cmp(a: dict, b: dict) -> int:
            result = _compare(column_value(a), column_value(b))
            return -result if direction == "desc" else result

        return sorted(data, key=cmp_to_key(row_cmp))

    # ---- internals: selection ----

    def _apply_selection(self, keys: set[str]) -> None:
        for key in keys:
            row = self._row_by_key.get(key)
            if row is None:
                continue
            active = key in self._selected
            row.styles = self._row_active if active else self._row_base
            row.args = {**row.args, "aria-selected": "true" if active else "false"}
            # Cell text follows the row fill — on_accent on the filled row,
            # the plain surface text otherwise.
            text = stub.on_accent if active else stub.text_primary
            for cell in row.container:
                if isinstance(cell, DOMElement):
                    cell.styles = cell.styles.model_copy(update={"color": text})

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

    def _toggle_select(self, key: str) -> None:
        previous = set(self._selected)
        if self._selection == "multi":
            if key in self._selected:
                self._selected.discard(key)
            else:
                self._selected.add(key)
        else:
            self._selected = {key}
        self._apply_selection(previous ^ self._selected)
        self._clear_focus()

    def _make_click_handler(self, key: str):
        async def handler(event: DomEvent) -> None:
            self._toggle_select(key)
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
                await self._move_to(len(self._row_keys) - 1, event)

        return handler

    async def _dispatch_change(self, key: str, event: DomEvent) -> None:
        self._toggle_select(key)
        event.value = key
        event.source = "user"
        await self._dispatch("change", event)

    async def _move(self, step: int, from_key: str, event: DomEvent) -> None:
        """Move the keyboard position by *step* rows, clamped at the ends
        (no wrap).  Single mode moves the selection (firing ``change``);
        multi mode moves only the focus ring."""
        try:
            index = self._row_keys.index(from_key)
        except ValueError:
            return
        target = index + step
        if target < 0 or target >= len(self._row_keys):
            return
        new_key = self._row_keys[target]
        if self._selection == "multi":
            self._set_focus(new_key)
            return
        await self._dispatch_change(new_key, event)

    async def _move_to(self, target: int, event: DomEvent) -> None:
        if not self._row_keys:
            return
        new_key = self._row_keys[target]
        if self._selection == "multi":
            self._set_focus(new_key)
            return
        await self._dispatch_change(new_key, event)
