# Layout & chrome

> [中文版本](layout-chrome.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

Flex containers, frosted panels, and the navigation / chrome components —
`TitleBar`, `Sidebar`, `Tree`, `List`, `DataTable`. Import both layout
primitives and chrome components from `neony.application.elements`.

## Flex containers

```python
VStack(a, b, gap="12px", align="stretch")  # column
HStack(a, Spacer(), b, gap="8px")  # row, spacer fills
Flex(*items, direction="row", wrap="wrap", gap="8px")  # full control
Separator()  # divider (type="horizontal" default, or "vertical")
GlassPanel(Heading("Frosted"), background=url, grow=True)  # frosted stage
```

- `VStack` / `HStack` / `Flex` accept `grow` to fill remaining space.
- `GlassPanel`: translucent surface + backdrop blur; `background=url`
  paints an image inside; `grow=True` fills the parent; `radius`
  overrides the default 12px corner radius; `width` / `height` fix the
  panel to a definite size (pair with the default non-`grow` mode).

## `TitleBar`

Custom window chrome for frameless windows. Requires
`WindowConfig(decorations=False)`.

```python
titlebar = TitleBar("My App")
titlebar.on_close(lambda e: print("bye"))  # extra callback
titlebar.override_close(confirm_close)  # take over close
titlebar.leading_slot.container.append(custom_element)
```

**Options:** `title`, `icon`, `show_minimize`, `show_maximize`,
`icon_size`, `icon_styles`, `leading`, `trailing`, `show_minimize`,
`show_maximize`, `show_close`, `height`

`icon` is an `Icon` — `Icon.image(url_or_path)` paints a small image
left of the title (a fixed-size square that never stretches), the
frameless counterpart of `WindowConfig.icon`, since a frameless window
has no OS chrome to carry it.

The bar is a drag region (double-click maximizes); the control buttons
are wired to the window automatically.
`leading_slot` / `trailing_slot` are read-only slots: the former holds
the icon, leading content, and title; the latter holds trailing content
and window controls.

## `Sidebar` & `SidebarItem`

Vertical navigation, glass-matched to `TitleBar`. The sidebar can own
its content panes — with `Pane` children, clicking an entry (or
pressing its shortcut) switches the visible pane.

```python
sidebar = Sidebar(
    Pane("Home", panel=home_panel, icon=Icon.glyph("🏠"), section="General", shortcut="Ctrl+1"),
    Pane("Settings", panel=settings_panel, icon=Icon.glyph("⚙️"), section="General"),
    Pane("Stats", panel=stats_panel, icon=Icon.glyph("📊"), section="Data", shortcut="Ctrl+3"),
)
sidebar.on_change(lambda e: print(e.value))  # value = pane key
sidebar.selected_key = "settings"  # programmatic, no callback
sidebar.selected  # the selected Pane (or SidebarItem) object
for combo, fn in sidebar.shortcuts():
    page.on_shortcut(combo, fn)  # wire the panes' shortcuts
```

Bare-rail mode — only `SidebarItem`s, content switching stays the
user's job:

```python
sidebar = Sidebar(
    SidebarItem("Home", icon=Icon.glyph("🏠")),
    SidebarItem("Settings", icon=Icon.glyph("⚙️")),
    active_key="home",  # deprecated → selected_key
)
```

**Options:** `Sidebar(*children, width, glass, corner_radius, edge_fade=True)`,
`SidebarItem(label, key, icon, active)` — `*children` are
`SidebarItem` / `SidebarGroup` / `Pane` / `(label, panel)` tuples.

`edge_fade` toggles the scroll indicator on the rail — set `False` to
suppress. On a glass sidebar the thumb still shows but the edge fade is
skipped (mask-image conflicts with backdrop blur in WebKitGTK).

`Pane.key` defaults to a random id — labels never collide, even when
duplicated or non-ASCII; pass an explicit `key` when you want a
readable identifier. `shortcut` accepts the same combo forms as
`Page.on_shortcut`; a shortcut switch fires `change` like a click.

`selected_key` raises `ValueError` for unknown keys; setting `None`
clears the selection. Clicks anywhere on an item — including the icon
or label — count: item-level events bubble up from its children.

### `Pane`

One selectable `Sidebar` entry and its content panel.

```python
pane = Pane("Home", panel=home_panel, icon=Icon.glyph("🏠"), section="General", shortcut="Ctrl+1")
```

**Options:** `Pane(label, panel, key, icon, section, shortcut)` —
`label` is the entry text (first positional argument); `panel` is the
component (or element) shown while active, built exactly once when the
pane is registered (a panel component cannot be reused in two
sidebars); `key` defaults to a random id; `section` groups consecutive
panes under one small uppercase sidebar label; `shortcut` is a
window-level combo (`"Ctrl+1"` or a per-platform dict like
`{"darwin": "Meta+2", "default": "Ctrl+2"}`).

### `SidebarGroup`

A titled section of a `Sidebar` — a small uppercase label above its
items.

```python
sidebar.add(SidebarGroup("Menu", SidebarItem("Open"), SidebarItem("Save")))
```

`SidebarGroup.add` is chainable and also works after the group is
attached to a sidebar (new items are wired automatically). Groups are
purely visual: selection, `items`, and `change` all operate on the flat
entry list in DOM order. Consecutive panes sharing a `section` render
as one group; the same section reappearing later starts a new group.

## `Tree` & `TreeNode`

A collapsible navigation tree (left rail) owning a content host (right).

Arbitrary depth: a branch (a node with `children`) only expands /
collapses; a leaf (a node with a `panel`) selects into the host. The
tree is single-select, so `selected_key` / `bind_selected` behave like
`Sidebar`.

```python
tree = Tree(
    TreeNode("Home", key="home", icon=Icon.glyph("🏠")).panel(home_panel),
    TreeNode("Forms", expanded=True).children(
        TreeNode("Inputs", key="inputs", shortcut="Ctrl+1").panel(inputs_panel),
        TreeNode("Checks", key="checks").panel(checks_panel),
    ),
    active_key="home",  # or tree.selected_key = "home"
)
tree.on_change(lambda e: print(e.value))  # value = leaf key
for combo, fn in tree.shortcuts():
    page.on_shortcut(combo, fn)  # leaf shortcuts, like Sidebar
```

**Options:** `Tree(*nodes, width, expanded_branches, active_key, edge_fade=True)` —
`width` is the rail width (the host adapts to the rest);
`expanded_branches=True` starts top-level branches open. `edge_fade`
toggles the scroll indicator on the rail — set `False` to suppress.

Rows mirror the `Accordion` header styling — rounded, transparent, no
chrome around them — and the rail is bounded by the stage, scrolling
inside the stage instead of growing the page.

`TreeNode(label, key, icon, panel, expanded, children, shortcut)` — a
node cannot carry both a `panel` and `children` (raises). Fluent
builders: `.panel(panel)` attaches a leaf's content, `.children(*nodes)`
attaches a branch's children, `.key_(key)` sets the key — all chainable.

`key` defaults to a random id; `selected_key` raises `ValueError` for
unknown keys. Branches carry `aria-expanded`, leaves `aria-selected`;
rows are keyboard-navigable (arrows move the focus ring, Enter / Space
activate, ← / → collapse / expand branches).

## `List` & `ListItem`

A scrollable, single-select data list (the listbox model). Exactly one
entry is selected at a time; `selected_key` / `bind_selected` /
`on_change` behave like `Sidebar`.

```python
fruits = List(
    "Apple",
    "Banana",
    ListItem("Cherry", key="cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.on_change(lambda e: print(e.value))  # value = selected key
fruits.selected_key = "cherry"  # programmatic, no callback
fruits.children("Durian", "Elderberry")  # chainable append
fruits.bind_selected(signal)  # two-way reactive selection
```

**Options:** `List(*items, active_key=None, edge_fade=True)` — items are
strings or `ListItem(label, key=None, icon=None)`. A string item's key
is its label; pass an explicit `key` when labels collide (duplicate keys
raise). Rows are `role="option"` inside a `role="listbox"` container;
keyboard: Arrow Up/Down move the selection (clamped at the ends, each
move fires `change`), Home/End jump to the ends, Enter/Space select,
and a click selects. The accent focus ring appears during arrow
navigation and clears on click. `edge_fade` toggles the scroll
indicator.

Mount in a *definite-height* flex parent (e.g. `VStack(..., grow=1)` or
`GlassPanel(grow=True)`); the list scrolls its rows inside the parent
instead of growing the page.

## `DataTable` & `Column`

A tabular data view — column config plus a list of row dicts, with a
sticky header, click-to-sort columns, and row selection (single by
default, or multi at construction).

```python
people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", align="right", format=lambda v: f"{v}%"),
    ],
    rows=[
        {"name": "Ada", "age": 38, "score": 92},
        {"name": "Bob", "age": 24, "score": 77},
    ],
    row_key=lambda r: r["name"],  # default: row index
    active_key="Ada",
)
people.on_change(lambda e: print(e.value))  # selected row key
people.sort_by = ("age", "desc")  # header clicks sort too
people.bind_selected(signal)  # two-way reactive selection
```

Columns and rows can also be appended chainably:
`DataTable().column("Name").row({"name": "Ada"})`.

**Options:** `DataTable(columns=None, rows=None, *, row_key=None,
selection="single", active_key=None, selected_keys=None, edge_fade=True)`.

`Column(title, key=None, width=None, sortable=False, align=None,
format=None, sort_key=None)` — `key` defaults to the lowercased title;
`width` is a CSS grid track (`"1fr"` / `"80px"`); `align` is
`left|center|right`; `format` maps a cell value to text; `sort_key`
extracts a custom sort value from a row.

`row_key` derives each row's identity (default: row index) and must be
unique. Header cells with `sortable=True` sort on click (asc → desc,
switching columns starts asc); sorting is numeric-aware (or via
`sort_key`), keeps the selection, and is observable through `sort_by`.

The header is `position: sticky` inside the scroll container, so header
and rows stay aligned under horizontal scroll.

**Selection.** `selection="single"` (default) exposes `selected_key`
(programmatic writes never fire callbacks); `selection="multi"` exposes
`selected_keys` (accepts a `set`/`frozenset`/`list`/`None`) and a click
toggles membership — `change` carries the toggled key, read
`selected_keys` for the full set. `bind_selected` works only in single
mode (raises otherwise); the wrong-mode property raises
`NotImplementedError`.

Keyboard: single mode arrows move the selection (firing `change`);
multi mode arrows move a focus ring and Space toggles it. Home/End
jump; Enter/Space select or toggle.

Mount in a *definite-height* flex parent; the table scrolls on both
axes inside the parent. `edge_fade` toggles the scroll indicator.

## `Icon`

Built-in UI icons are exposed through the `icons` namespace; the catalog
class is private and is not part of the public API:

```python
from neony.application import icons
from neony.application.elements import Button

Button("Save", icon=icons.check)
SidebarItem("Home", icon=icons.home)
```

The built-in catalog uses one bundled Material Symbols Rounded font. Icons
inherit the component's `color` token, use fixed square geometry, and keep the
same weight/fill/grade/optical-size settings.

`Icon.image(url_or_path)` is used for logos and native image resources, while
`Icon.glyph(text)` is used for deliberate custom text or emoji content. Both
return `Icon` values and are accepted by component `icon` parameters,
including `Button.icon: Icon | None`.
