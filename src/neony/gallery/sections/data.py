"""Data views sections — List and DataTable."""

from __future__ import annotations

from neony.application.elements import Button, Column, DataTable, Icon, List, ListItem, Separator, Text
from neony.dom import Div, DomEvent, Signal, Styles

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
        {"key": "Kiana", "name": tr.data.kiana, "role": tr.data.engineer, "age": 38, "score": 92},
        {"key": "Mei", "name": tr.data.mei, "role": tr.data.designer, "age": 24, "score": 77},
        {"key": "Bronya", "name": tr.data.bronya, "role": tr.data.manager, "age": 31, "score": 85},
        {"key": "Elysia", "name": tr.data.elysia, "role": tr.data.engineer, "age": 29, "score": 64},
        {"key": "Eden", "name": tr.data.eden, "role": tr.data.pm, "age": 34, "score": 90},
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

PANELS = {"list": list_panel, "datatable": datatable_panel}
