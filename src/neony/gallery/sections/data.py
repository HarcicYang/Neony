"""Data views sections — List and DataTable."""

from __future__ import annotations

from typing import Any

from neony.application.elements import (
    Button,
    Card,
    Column,
    DataTable,
    Icon,
    List,
    ListItem,
    Reorder,
    ReorderItem,
    Separator,
    Text,
)
from neony.dom import Computed, Div, DomEvent, Signal, Styles

from ..core import Section
from ..i18n import tr, tr_now

# ── tab: list ────────────────────────────────────────────────────

# List items keep static identity keys while their visible labels follow the
# active catalog language.
fruits = List(
    ListItem(tr.data.apple, key="Apple"),
    ListItem(tr.data.banana, key="Banana"),
    ListItem(tr.data.cherry, key="Cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.children(
    ListItem(tr.data.durian, key="Durian"),
    ListItem(tr.data.elderberry, key="Elderberry"),
)  # chainable append
fruits_sig = Signal("Apple")
fruits.bind_selected(fruits_sig)  # two-way: clicks AND selected_key write the signal
list_echo = Text("", role="secondary")
list_echo.bind_text(fruits_sig, fmt=lambda key: tr.data.selected_fmt.format(key=key).get())


def on_pick_durian(_event: DomEvent) -> None:
    fruits.selected_key = "Durian"  # programmatic — mirrors into fruits_sig


durian_btn = Button(tr.data.select_durian).on_click(on_pick_durian)

list_panel = Section(
    tr.data.list_title,
    tr.data.list_blurb,
    """fruits = List(
    "Apple", "Banana",
    ListItem("Cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.children(ListItem("Durian"), "Elderberry")  # chainable append
sig = Signal("Apple")
fruits.bind_selected(sig)           # two-way: clicks + selected_key write the signal
list_echo.bind_text(sig, fmt=lambda key: f"selected: {key}")
fruits.selected_key = "Durian"      # programmatic — mirrors into sig""",
    Div(styles=Styles(height="220px", display="flex", flex_direction="column"), container=[fruits.build()]),
    list_echo,
    durian_btn,
)

# ── tab: datatable ───────────────────────────────────────────────

table_picked = Signal("selected: Kiana")
table_echo = Text("", role="secondary")
table_echo.bind_text(table_picked)

# Row identity is a stable key (selection, sorting); the displayed name is a
# reactive tr ref so the cell follows the catalog language live.
people = DataTable(
    columns=[
        Column(tr.data.name, key="name", sortable=True, width="2fr", sort_key=lambda r: r["key"]),
        Column(tr.data.role, key="role"),
        Column(tr.data.age, key="age", sortable=True, align="right", width="80px"),
        Column(tr.data.score, key="score", sortable=True, align="right", width="70px", format=lambda v: f"{v}%"),
    ],
    rows=[
        {"key": "Kiana", "name": tr.data.kiana, "role": tr.data.kiana_role, "age": 25, "score": 92},
        {"key": "Mei", "name": tr.data.mei, "role": tr.data.mei_role, "age": 27, "score": 77},
        {"key": "Bronya", "name": tr.data.bronya, "role": tr.data.bronya_role, "age": 23, "score": 85},
        {"key": "Elysia", "name": tr.data.elysia, "role": tr.data.elysia_role, "age": 114514, "score": 64},
        {"key": "Eden", "name": tr.data.eden, "role": tr.data.eden_role, "age": 191981, "score": 90},
    ],
    row_key=lambda r: r["key"],
    active_key="Kiana",
)
people.on_change(lambda e: table_picked.set(tr_now(tr.data.selected_fmt).format(key=e.value)))
people.bind_selected(Signal("Kiana"))


def on_age_sort(_event: DomEvent) -> None:
    people.sort_by = ("age", "desc")


age_btn = Button(tr.data.sort_by_age).on_click(on_age_sort)

multi_picked = Signal("selected: web")
multi_echo = Text("", role="secondary")
multi_echo.bind_text(multi_picked)

multi = DataTable(
    columns=[
        Column(tr.data.service, key="service"),
        Column(tr.data.status, key="status", align="center"),
    ],
    rows=[
        {"service": "web", "status": tr.data.ok},
        {"service": "db", "status": tr.data.degraded},
        {"service": "cache", "status": tr.data.ok},
    ],
    row_key=lambda r: r["service"],
    selection="multi",
)
multi.selected_keys = {"web"}


def on_multi_change(_event: DomEvent) -> None:
    picked = ", ".join(sorted(multi.selected_keys)) or tr_now(tr.data.selected_none)
    multi_picked.set(tr_now(tr.data.selected_fmt).format(key=picked))


multi.on_change(on_multi_change)

datatable_panel = Section(
    tr.data.table_title,
    tr.data.table_blurb,
    """people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", align="right", format=lambda v: f"{v}%"),
    ],
    rows=[{"key": "Kiana", "name": tr.data.kiana, "age": 38, "score": 92}, ...],
    row_key=lambda r: r["key"],      # stable identity; name may be reactive
    active_key="Kiana",
)
people.on_change(lambda e: print(e.value))     # selected row key
people.sort_by = ("age", "desc")               # header clicks sort too
people.bind_selected(sig)                      # two-way reactive selection

multi = DataTable(rows=[...], selection="multi", row_key=...)
multi.selected_keys = {"web"}                  # set / replace / None
multi.on_change(...)  # e.value = toggled key; read multi.selected_keys""",
    Div(styles=Styles(height="260px", display="flex", flex_direction="column"), container=[people.build()]),
    table_echo,
    age_btn,
    Separator(),
    Div(styles=Styles(height="200px", display="flex", flex_direction="column"), container=[multi.build()]),
    multi_echo,
)

# ── tab: drag reorder ────────────────────────────────────────────

# The in-app drag primitive, wrapped as the :class:`Reorder` component:
# cards are pre-marked draggable (the payload is declared up front, since
# a Python round-trip in dragstart would be too late), and a drop
# reorders the board internally — the diff engine emits a ReorderPatch
# for free.  A ``row`` board with ``wrap=True`` forms a grid; pinning
# ``max_width`` to 4 cards per row forces the wrap, so a card can be
# dragged both horizontally (within a row) and vertically (into another
# row).
reorder_board = Reorder(
    ReorderItem(tr.data.reorder_first, key="reorder-1"),
    ReorderItem(tr.data.reorder_second, key="reorder-2"),
    ReorderItem(tr.data.reorder_third, key="reorder-3"),
    ReorderItem(tr.data.reorder_fourth, key="reorder-4"),
    ReorderItem(tr.data.reorder_fifth, key="reorder-5"),
    ReorderItem(tr.data.reorder_sixth, key="reorder-6"),
    ReorderItem(tr.data.reorder_seventh, key="reorder-7"),
    ReorderItem(tr.data.reorder_eighth, key="reorder-8"),
    direction="row",
    wrap=True,
    size="76px",
    max_width="336px",  # 4 cards per row → the grid wraps into two rows
)

# A second board: cards can be dragged between boards (cross-Reorder) —
# the landing slot travels into the hovered board, and the drop moves
# the card.  Card keys must stay unique across the two boards.
reorder_tray = Reorder(
    ReorderItem(tr.data.reorder_tray_a, key="tray-a"),
    ReorderItem(tr.data.reorder_tray_b, key="tray-b"),
    ReorderItem(tr.data.reorder_tray_c, key="tray-c"),
    direction="row",
    wrap=False,
    size="76px",
)
reorder_readout = Text("", role="secondary")


def _reorder_label(item: ReorderItem[Any]) -> str:
    content = item.content
    if isinstance(content, (Signal, Computed)):
        return content.get()
    if isinstance(content, str):
        return content
    return "<component>"  # component/DOM cards aren't rendered in the readout


def _render_reorder(order: list[str]) -> None:
    labels = {
        item.key: _reorder_label(item) for item in reorder_board.items + reorder_tray.items if item.key is not None
    }
    parts = [f"{labels[k]}[{k.split('-')[-1]}]" for k in order if k in labels]
    reorder_readout.text = "order: " + " → ".join(parts)


reorder_board.on_drop(lambda e: _render_reorder(e.value))
reorder_tray.on_drop(lambda e: _render_reorder(e.value))
_render_reorder(reorder_board.order)

# Bare components go straight into a Reorder — no ReorderItem wrapper, no
# explicit key: each Card gets an auto-generated key and is draggable like
# any other card (and can cross boards too).
reorder_cards = Reorder(
    Card(Text(tr.data.reorder_card_one), title=tr.data.reorder_card_one),
    Card(Text(tr.data.reorder_card_two), title=tr.data.reorder_card_two),
    Card(Text(tr.data.reorder_card_three), title=tr.data.reorder_card_three),
    direction="row",
    wrap=False,
    size="120px",
)


def _render_cards(order: list[str]) -> None:
    reorder_readout.text = "cards: " + " → ".join(order)


reorder_cards.on_drop(lambda e: _render_cards(e.value))

reorder_panel = Section(
    tr.data.reorder_title,
    tr.data.reorder_blurb,
    """board = Reorder(ReorderItem("First", key="a"), "Second", ...)  # draggable cards
board.on_drop(lambda e: e.value)   # ordered keys after a drag
# any component / DOM element can be a card; two boards can exchange cards""",
    reorder_board,
    reorder_tray,
    reorder_cards,
    reorder_readout,
)

PANELS = {"list": list_panel, "datatable": datatable_panel, "reorder": reorder_panel}
