"""Data views sections — List and DataTable."""

from __future__ import annotations

from neony.application.elements import Button, Column, DataTable, Icon, List, ListItem, Separator, Text
from neony.dom import Div, DomEvent, Signal, Styles

from ..core import Section

# ── tab: list ────────────────────────────────────────────────────

fruits = List(
    "Apple",
    "Banana",
    ListItem("Cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.children(ListItem("Durian"), "Elderberry")  # chainable append
fruits_sig = Signal("Apple")
fruits.bind_selected(fruits_sig)  # two-way: clicks AND selected_key write the signal
list_echo = Text("", role="secondary")
list_echo.bind_text(fruits_sig, fmt=lambda key: f"selected: {key}")


def on_pick_durian(_event: DomEvent) -> None:
    fruits.selected_key = "Durian"  # programmatic — mirrors into fruits_sig


durian_btn = Button("Select 'Durian'").on_click(on_pick_durian)

list_panel = Section(
    "List",
    "A scrollable, single-select data list — the listbox model. Arrow "
    "keys move the selection directly (each move fires change), Home/End "
    "jump to the ends, Enter/Space select, and a click selects. The "
    "selection is two-way reactive via bind_selected — user clicks write "
    "the signal, and programmatic selected_key writes mirror into it.",
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

table_picked = Signal("selected: Ada")
table_echo = Text("", role="secondary")
table_echo.bind_text(table_picked)

people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Role", key="role"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", sortable=True, align="right", width="70px", format=lambda v: f"{v}%"),
    ],
    rows=[
        {"name": "Ada", "role": "Engineer", "age": 38, "score": 92},
        {"name": "Bob", "role": "Designer", "age": 24, "score": 77},
        {"name": "Cleo", "role": "Manager", "age": 31, "score": 85},
        {"name": "Dmitri", "role": "Engineer", "age": 29, "score": 64},
        {"name": "Ella", "role": "PM", "age": 34, "score": 90},
    ],
    row_key=lambda r: r["name"],
    active_key="Ada",
)
people.on_change(lambda e: table_picked.set(f"selected: {e.value}"))
people.bind_selected(Signal("Ada"))


def on_age_sort(_event: DomEvent) -> None:
    people.sort_by = ("age", "desc")


age_btn = Button("Sort by age ↓").on_click(on_age_sort)

multi_picked = Signal("selected: web")
multi_echo = Text("", role="secondary")
multi_echo.bind_text(multi_picked)

multi = DataTable(
    columns=[
        Column("Service", key="service"),
        Column("Status", key="status", align="center"),
    ],
    rows=[
        {"service": "web", "status": "ok"},
        {"service": "db", "status": "degraded"},
        {"service": "cache", "status": "ok"},
    ],
    row_key=lambda r: r["service"],
    selection="multi",
)
multi.selected_keys = {"web"}


def on_multi_change(_event: DomEvent) -> None:
    picked = ", ".join(sorted(multi.selected_keys)) or "none"
    multi_picked.set(f"selected: {picked}")


multi.on_change(on_multi_change)

datatable_panel = Section(
    "DataTable",
    "Column config + data rows with a sticky header, click-to-sort "
    "columns, and row selection. Columns lay out with CSS grid "
    "(width tracks like '2fr' / '80px'), the header sticks while the "
    "body scrolls, and sorting is numeric-aware (or via a per-column "
    "sort_key). Selection is single by default or multi at construction.",
    """people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", align="right", format=lambda v: f"{v}%"),
    ],
    rows=[{"name": "Ada", "age": 38, "score": 92}, ...],
    row_key=lambda r: r["name"],     # default: row index
    active_key="Ada",
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

PANELS = {"list": list_panel, "datatable": datatable_panel}
