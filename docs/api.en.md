# Neony API Reference

> [中文参考](api.zh.md)

---

## Core

### `NeonApplication`

The application object — owns the window, the bridge, the theme, and
shared state. Construct with a `Config`, build a `Page`, then `run()`.

```python
from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # shared mutable state
app.theme.set_mode("light")  # switch theme


def main() -> None:
    app.run(page)
```

**Typed state:** `state` defaults to a bare `SimpleNamespace`. Pass any
object — a `dataclass`, pydantic model, or plain class — via the `state=`
argument to get typed attribute access and IDE completion:

```python
from dataclasses import dataclass


@dataclass
class AppState:
    count: int = 0
    user_name: str = ""


app = NeonApplication(Config(...), state=AppState())
app.state.count += 1  # typed as int
app.state.user_name = "Ada"
```

All windows share the same `state` object, so this is the imperative
counterpart to [`SharedSignal`](#sharedsignal) for cross-window data.

**Attributes:** `config`, `state`, `theme`, `ready_handler`, `close_handler`

**Window methods** (all async):
`set_title(title)`, `set_size(w, h)`, `minimize()`, `toggle_maximize()`,
`is_maximized()`, `set_fullscreen(f)`, `start_dragging()`, `close()`,
`apply_blur(color?)`, `apply_acrylic(color?)`, `apply_mica()`,
`clear_effect(effect)`, `eval_js(script)`, `set_icon(icon)`

**App methods:** `exit(code=0)` — graceful app shutdown (sync). With
`close_to_tray=True` window closes hide the app instead of quitting, so
`exit()` is the way out — e.g. a tray "Quit" menu item.

**Theme / rendering:**
`sync_theme()`, `set_background(url)`, `render()`

### `launch()`

One-liner entry point — builds a `Config` from keyword arguments.

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

Accepts all `WindowConfig` / `WebViewConfig` fields plus
`mount_selector`, `auto_render`, and `state` (a custom state object —
see [`NeonApplication`](#neonapplication)).

### `Config`, `WindowConfig`, `WebViewConfig`

Pydantic config models. `WindowConfig` covers geometry and appearance
(`title`, `width`, `height`, `decorations`, `transparent`,
`always_on_top`, `resizable`, `icon`, …). `WebViewConfig` covers runtime
options (`devtools`, `incognito`, `user_agent`, `javascript`, …).

**`WindowConfig.icon`** — file path (PNG, ICO, …) or raw RGBA data
`(bytes, width, height)`, shown in the OS window chrome of *decorated*
windows. Frameless windows have no OS chrome — see the
[`TitleBar`](#titlebar) `icon` parameter for inline icons, and
[`set_icon()`](#neonapplication) to swap at runtime.

**`WebViewConfig.default_context_menus`** — off by default: the app
draws its own menus (the `Menu` component, `contextmenu` events) and
the webview's native right-click menu would cover them. Set `True` for
the platform default menu.

### `Page`

Top-level flex-column container. Two layers: a full-viewport backdrop
and a width-constrained, centered content column.

```python
Page(gap="16px", padding="24px", max_width="720px")
Page(fill=True, radius="12px")  # chrome layouts
```

**Options:** `direction`, `gap`, `padding`, `align`, `justify`,
`width`, `max_width`, `glass`, `fill`, `radius`

`fill=True` stretches to the full window height. `radius` rounds the
window frame (for transparent frameless windows).

**Methods:** `add(child)` (chainable), `on_close(fn)` (chainable —
see [Lifecycle](#lifecycle)), `build()` → DOMElement

### Multi-window

`run()` accepts several pages — each opens its own window. All windows
share one event loop and the app's `state` namespace; an event handler
only re-renders the window it came from.

```python
app = NeonApplication(Config(...))
app.run(page_one, page_two)


async def on_ready() -> None:
    await app.set_title("Counter", window_index=0)
    await app.set_title("Display", window_index=1)


app.ready_handler = on_ready
```

Every window-control method takes `window_index` (default 0).
`launch([page_one, page_two], ...)` accepts a list too.

### Lifecycle

Startup and teardown are declared as plain attributes — the framework
owns the wiring to the native window events.

```python
async def on_ready() -> None:
    print("windows are up")


async def on_shutdown() -> None:
    save_state(app.state)  # runs after all windows close


app.ready_handler = on_ready
app.close_handler = on_shutdown
```

`close_handler` runs exactly once, after the last window closes and
before the event loop stops — the last chance for async cleanup.

**Per-window close** — `Page.on_close(fn)` (sync or async, chainable,
multiple handlers stack). Fires when that page's window is closing,
before it actually closes; exceptions are logged and never block the
close. For a confirm-before-close dialog, take over the titlebar close
button instead — see [`TitleBar.override_close`](#titlebar).

```python
page = Page()
page.on_close(lambda: print("window closing"))
```

**Focus tracking** — `Page.on_focus(fn)` / `Page.on_blur(fn)` (sync or
async, chainable, multiple handlers stack) fire when the page's window
gains / loses keyboard focus — useful for pausing timers, updating a
status bar, or knowing which window is active in a multi-window app.

```python
page = Page()
page.on_focus(lambda: print("active"))
page.on_blur(lambda: print("inactive"))
```

### `Tray` & `TrayItem` — system tray (native menu)

A tray icon with a native context menu, backed by lumiview .dev4
(muda menus + TrayIcon). Assign `app.tray` before `run()`; the icon
materializes once the app is up.

```python
from neony.application import Tray, TrayItem

app.tray = Tray(
    icon="tray.png",  # file path or raw RGBA (bytes, width, height)
    tooltip="My App",
    items=[
        TrayItem("Show Window", id="show", on_activate=show_handler),
        TrayItem.separator(),
        TrayItem("Quit", id="quit", accelerator="CmdOrCtrl+Q", on_activate=quit_handler),
    ],
    menu_on_left_click=False,  # free the left button for on_left_click
    on_left_click=toggle_handler,  # sync or async
    close_to_tray=True,  # close hides the app instead of quitting
)
```

- `TrayItem` — `text`, optional `id` (carried by activation
  callbacks), `accelerator` (muda syntax; Windows may not fire it from
  the keyboard), `on_activate` (sync or async, run on the asyncio
  loop), `checked=True` for a check item; `TrayItem.separator()` for a
  divider.
- `close_to_tray=True` — every window's close request is prevented and
  the app hides (restore from the menu / tray click; on macOS a Dock
  click via `ReopenEvent`). `Page.on_close` handlers still run.
- `on_left_click` — fires on a released left click when
  `menu_on_left_click=False` (typical use: toggle the window).
- Platform notes: **Linux needs libayatana-appindicator**; the tooltip
  is unsupported there and the menu cannot be replaced after creation.
  See [`demo_tray.py`](../../demo_tray.py).

---

## Navigation policies

A link or redirect inside the page would otherwise navigate the webview
away from your UI. Neony installs safe defaults on every window —
navigation blocked, new-window requests denied, downloads cancelled —
so nothing can escape without your say-so. Override them per-page.

**Decision policies** — a single handler, the last one registered wins
(a decision can't be merged):

```python
# Allow only your own site; everything else is blocked.
page.on_navigation(lambda url: url.startswith("https://myapp.example"))

# target="_blank" links and window.open(): "allow" or "deny".
page.on_new_window(lambda url: "deny")

# Return True to allow, False to cancel, or a path to redirect the
# download to a custom location.
page.on_download_started(lambda url, path: "/downloads/")
```

**Notifications** — multiple handlers stack, all run:

```python
# url, final path (or None if cancelled), success flag.
page.on_download_completed(lambda url, path, ok: print(f"downloaded {path}"))
```

---

## Components

All inherit `Component` — fluent `on_*` chaining, state properties,
source-aware events. Import from `neony.application.elements`.

### `Button`

```python
Button("Primary")  # accent bg
Button("Ghost", variant="ghost")  # bordered surface
Button("Delete", variant="danger")  # danger color
Button("Glass", glass=True)  # frosted variant
Button("Ok", disabled=True)  # dimmed
button.on_click(handler)  # click event
```

### `Checkbox`

```python
cb = Checkbox("Pizza")
cb.checked = True  # programmatic — no callback
cb.on_change(lambda e: print(e.value))  # value = checked bool
```

### `Input`

```python
inp = Input(placeholder="Your name…", type="text")  # text | password | email | number …
inp.on_input(lambda e: print(e.value))  # live value
```

### `Heading` & `Text`

```python
Heading("Title", level=1)  # h1–h6
Text("Body copy")  # primary
Text("Muted", role="secondary")  # muted
Text("Error", role="danger")  # danger
Text("OK", role="success")  # success
```

### `Tabs`

```python
tabs = Tabs(("One", panel_one), ("Two", panel_two))  # or tabs.add("One", panel_one)
tabs.selected_panel = panel_two  # programmatic switch (component or element)
tabs.selected_title  # title of the active tab
tabs.selected_key = "Two"  # title-as-key selection
tabs.bind_selected(active)  # Signal[str] ↔ selected tab
tabs.on_change(lambda e: print(e.value))  # value = tab title
```

**Options:** `Tabs(*panes, glass)` — `*panes` are `(title, panel)` pairs,
equivalent to chained `add()` calls.

`selected_panel` binds the visible panel (the Component or its built
root — matched by identity, never rebuilt); `selected_title` selects by
title string and raises `ValueError` for unknown titles.  `active`
(index) and `active_key` are deprecated aliases — `active_key` returns
the tab title (it used to return an opaque element id).

### `Pane` & `SidebarGroup`

See the `Sidebar` section below — `Pane` is the selectable entry the
sidebar owns, `SidebarGroup` the titled section that groups entries.

### `Radio` & `RadioGroup`

```python
group = RadioGroup(Radio("Pizza"), Radio("Tacos"))
group.value  # selected value (defaults to lowercased label)
group.on_change(lambda e: print(e.value))  # value = selected value string
group.value = "tacos"  # programmatic — no callback
```

Exactly one option is checked at a time; the group assigns a shared
`name` so screen readers treat it as one control. A `Radio` used alone
is a plain toggle with `on_change` carrying the bool.

### `Switch`

```python
sw = Switch("Wi-Fi")
sw.bind_value(flag)  # two-way: binds checked
sw.checked = True  # programmatic — no callback
sw.on_change(lambda e: print(e.value))  # value = checked bool
```

Use `bind_value` when the switch only mirrors application state. Keep a
named handler when a change must perform work beyond synchronization:

```python
async def on_wifi_change(event: DomEvent) -> None:
    await persist_setting(bool(event.value))
    status.set("saved")


sw.on_change(on_wifi_change)
```

A native checkbox styled as a track + thumb (38×22px, `glass=True` for
a frosted track).

### `Select`

```python
sel = Select("Size", options=[("s", "Small"), ("m", "Medium")], placeholder="Pick…")
sel.value  # selected option value ("m")
sel.on_change(lambda e: print(e.value))  # value = selected option value
```

Options are `str` (value == label) or `(value, label)` tuples. The
popup is drawn by the component — a themed glass panel of rows — since
WebKitGTK's native popup ignores option `background-color`. Keyboard:
Enter/Space opens, ArrowDown/Up highlights, Enter picks, Escape/Tab
closes; click-away closes via the engine's `outsideclick` event.

### `ComboBox`

```python
box = ComboBox("Tag", options=["work", "personal"], placeholder="Type or pick…")
tag = Signal("")
box.bind_value(tag)  # typing and suggestion picks both write tag
```

For simple echoes, the binding is enough. For validation, persistence, or
other asynchronous work, use the event stream instead (or use both):

```python
async def on_tag_change(event: DomEvent) -> None:
    await save_tag(event.value)
    audit_log.append(event.value)


box.on_change(on_tag_change)  # event.value is the committed text
```

Editable text with a themed suggestion popup (the native `<datalist>`
popup cannot be themed). The popup opens on focus — a single click
shows every option; suggestions filter by prefix as you type.
ArrowDown/Up highlights, **Tab or Enter auto-completes** the
highlighted suggestion, **PageUp/PageDown pick the first/last
suggestion in one keypress**, Escape / click-away closes. Value
semantics match `Input`: `on_input` records state only, `on_change`
fires on a pick or blur.

### `Slider`

```python
sl = Slider("Volume", min=0, max=100, step=5, value=40)
sl = Slider("Volume", min=0, max=100, step="any")  # stepless
sl.value  # 40.0 — clamped to [min, max]
sl.on_input(lambda e: print(e.value))  # float, while dragging
sl.on_change(lambda e: print(e.value))  # float, on release
```

The visible track, accent fill and knob are drawn by the component
(the native range input on top is invisible and owns drag / keyboard).
The fill follows the thumb instantly while dragging and glides over
0.2s on programmatic sets. `step="any"` reaches every float.
PageUp/PageDown move by a page step (10× step, or 10% of the range
when stepless) — the component corrects the native range input's
reversed page direction (WebKit spec quirk).

### `Progress`

```python
bar = Progress("Downloading…", value=35, max=100)
bar.value = 50  # clamped to [0, max]; the fill glides over 0.3s
Progress("Scanning…", indeterminate=True)  # sliding sweep animation
```

A rounded track with an accent fill that transitions on value changes
(`indeterminate=True` plays the built-in `neony-indeterminate` sweep).
ARIA `role="progressbar"` + `aria-valuenow/min/max` are carried on the
bar.

### `Dialog`

```python
dlg = Dialog(
    title="Confirm",
    content=Text("..."),
    width="380px",
    actions=[
        DialogAction("确认", on_click=confirm_handler),  # runs, then closes
        DialogAction("取消", variant="ghost"),
        DialogAction("关闭", close_on_click=False),  # runs, stays open
    ],
)
dlg.open = True  # or read the property
dlg.on_close(lambda d: print("closed"))  # called with the dialog
```

A fixed full-page scrim (`--color-bg-overlay`, theme-following) with a
centered panel. Close paths: scrim click, Escape (while focus is
inside), or click-away (`outsideclick`). `closable=False` disables only
the scrim. `actions` render as a row of themed buttons — `DialogAction`
takes a label (positional), a `variant` (`primary`/`ghost`/`danger`),
an `on_click` callback (called with the dialog, sync or async) and
`close_on_click` (default True). NOTE: any `backdrop-filter` /
`transform` ancestor becomes the containing block for
`position: fixed` — mount the dialog at the page root or in a
non-filtered container.

### `PromptDialog`

```python
ask = PromptDialog(
    "What's your name?",  # the question above the field
    title="Identify",
    value="Ada",  # pre-fill; also resettable via ask.value
    placeholder="Type…",
)
ask.open = True  # or read the property
ask.on_submit(lambda v: print(f"got {v}"))  # confirm / Enter, with the value
ask.on_close(lambda d: print("closed"))  # inherited from Dialog
```

A `Dialog` specialised for a single text value: a themed scrim + centered
panel with a message, one `Input` field, and a confirm / cancel row.
Confirming (the primary button, or pressing `Enter` while the field has
focus) fires `on_submit` with the field's current value, then closes;
cancelling (the ghost button, `Escape`, scrim click, or click-away)
closes without firing it. `value` is the field's text — set it before
opening to pre-fill, read it after submit. `prompt`, `confirm_label`,
`cancel_label`, and `placeholder` are configurable. Same `position:
fixed` caveat as `Dialog` — mount at the page root.

### `Tooltip`

```python
tip = Tooltip("hint", anchor=Button("Hover"), placement="top", delay=0.4)
```

Wraps its anchor (a component is built on construction; a string is
wrapped in a Span) and shows a bubble after `delay` seconds of hover,
anchored per `placement` (`top` / `bottom` / `left` / `right`) — pure
CSS offsets, no measurement. The wrapper bubbles hover events from the
anchor; clicking the anchor (focus) shows the bubble immediately, blur
hides it.

### `Dropdown`

```python
dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light")])
choice = Signal("")
dd.bind_value(choice)  # two-way: selection writes choice
dd.value  # selected value
```

Use a named `on_change` handler when selection triggers more than a state
write, such as an asynchronous reload or several related updates:

```python
async def on_theme_change(event: DomEvent) -> None:
    await reload_theme(event.value)
    status.set(f"loaded: {event.value}")


dd.on_change(on_theme_change)
```

A trigger with a themed glass popup of native button rows (the same
pattern as `Select`). Full keyboard nav (Enter/Space opens, arrows
clamp at the ends, PageUp/PageDown jump to first/last, Enter picks,
Escape/Tab and click-away close). `items` is settable.

### `Menu`

```python
menu = Menu(("rename", "Rename"), ("delete", "Delete"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # cursor position
menu.on_change(lambda e: print(e.value))
```

A fixed popup positioned with `open_at(x, y)` — typically a
`contextmenu` event's viewport coordinates, so no measurement is
needed. Same keyboard nav as `Dropdown`; closes on selection, Escape,
or click-away. The panel pops upward — its bottom edge anchors 8px
above the cursor — and clamps to the viewport via `calc()` max
width/height, so it never overflows an edge.

---

### `Image`

```python
from neony.application.urls import file_url, data_url

img = Image(file_url("cover.png"), width=120, height=120, fit="cover", radius="12px")
img.src = data_url("other.svg")  # any URL string
```

A themed frame around a single `<img>`. `src` is an **already-built URL**
— pass it `file_url(path)` for a local file, `data_url(path)` to embed the
bytes, or any `https://` URL; the component does no path conversion itself
(keeping that boundary in the caller's hands). A rounded, overflow-hidden
frame wraps the image so `object-fit` can crop to the radius and a
placeholder tint shows before the bytes arrive. `width`/`height` accept
`str` (`"40%"`) or `int` (→ `"40px"`). `fit` is `object-fit`
(`cover`/`contain`/`fill`/`none`/`scale-down`); pass `radius="50%"` for a
circle. `src` and `alt` are settable after construction.

### `Avatar`

```python
av = Avatar("https://…/me.png", name="Ada Lovelace", size="56px")
letter = Avatar(name="Ada", size="40px")  # → "A" on an accent disc
unknown = Avatar()  # → "?" placeholder
inbox = Avatar(src, name="Inbox", badge=Badge(3, position="top-right"))
```

A user avatar — image, letter initial, or placeholder. With `src` the
image is shown (cropped by `object-fit: cover`); with only `name` it
falls back to the first character (uppercased) on an accent disc; with
neither it shows a `?` placeholder. `shape` is `circle` (default) or
`square`; `radius` overrides the shape's corner radius. `alt` overrides
the image alt text (otherwise `name` is used). An optional `badge` (a
corner `Badge`) is overlaid — the avatar wraps itself in a relative
inline-flex container so the badge can anchor to a corner. `src`, `name`,
and `size` are settable after construction.

### `Badge`

```python
Badge("New", variant="accent")  # inline pill
Badge(150)  # → "99+" (default max=99)
Badge(0)  # hidden (display:none); Badge(0, show_zero=True) shows
Badge(dot=True)  # status dot, no text
Badge(3, position="top-right")  # corner count — needs a position:relative parent
```

A small status label or corner count — one class, two shapes.
`position="inline"` (default) is a pill that flows with text, tinted by
`variant` (`neutral` default, `accent`, `danger`, `success`). Any other
`position` (`top-right`, `top-left`, `bottom-right`, `bottom-left`)
absolutely positions the badge as a corner count — **the component assumes
a `position: relative` parent** (an `Avatar` with `badge=`, or a wrapper
`Div`); `overlap=True` pushes it further out (`-12px`) to overlap the
parent's edge. Integer content gets two conveniences: counts above `max`
(default 99) collapse to `"99+"`, and a zero count hides the badge unless
`show_zero=True` (the node stays mounted so it can toggle back).
`dot=True` drops the text for a bare status dot. `content`, `variant`, and
`dot` are settable after construction.

### `Card`

```python
card = Card(
    Text("The body holds any children."),
    title="My card",
    subtitle="Optional subtitle",
    actions=[Button("Edit")],
    footer=[Button("Cancel"), Button("OK")],
    glass=True,
    role="accent",
)
card.title = "Renamed"
```

A titled content panel. `*body` is the panel body (Components, DOMElements,
or strings). `title` / `subtitle` auto-build a header (a `Heading` + an
optional secondary `Text`); a custom `header=` slot replaces the title row
entirely (and takes precedence over `title`/`subtitle`/`actions`).
`actions` are buttons shown right-aligned in the header row; `footer` is a
button list (right-aligned, above a separator) or any content node.
`glass=True` swaps the solid surface for a frosted-glass panel tinted by
`role` (`neutral` default, `accent`, `danger`, `success` — the glow follows
the theme). `clickable=True` turns the card into a clickable surface
(`cursor: pointer` + `on_click`). `title` and `subtitle` are settable
after construction. Card keeps its own compact style constants (it does
not wrap `GlassPanel`), so it stays light by default.

---

## Layout

```python
VStack(a, b, gap="12px", align="stretch")  # column
HStack(a, Spacer(), b, gap="8px")  # row, spacer fills
Flex(*items, direction="row", wrap="wrap", gap="8px")  # full control
Separator()  # divider
GlassPanel(Heading("Frosted"), background=url, grow=True)  # frosted stage
```

- `VStack` / `HStack` / `Flex` accept `grow` to fill remaining space.
- `GlassPanel`: translucent surface + backdrop blur; `background=url`
  paints an image inside; `grow=True` fills the parent; `radius`
  overrides the default 12px corner radius.

---

## Chrome

### `TitleBar`

Custom window chrome for frameless windows. Requires
`WindowConfig(decorations=False)`.

```python
titlebar = TitleBar("My App")
titlebar.on_close(lambda e: print("bye"))  # extra callback
titlebar.override_close(confirm_close)  # take over close
```

**Options:** `title`, `icon`, `show_minimize`, `show_maximize`,
`show_close`, `height`

`icon` paints a small image (URL or file path) left of the title — the
frameless counterpart of `WindowConfig.icon`, since a frameless window
has no OS chrome to carry it.

The bar is a drag region (double-click maximizes); control buttons carry
internal `data-window-action` attributes routed through the
WindowControls bridge — an implementation detail users never see.

### `Sidebar` & `SidebarItem`

Vertical navigation, glass-matched to `TitleBar`.  The sidebar can own
its content panes — with `Pane` children, clicking an entry (or
pressing its shortcut) swaps the visible pane internally.

```python
sidebar = Sidebar(
    Pane("Home", panel=home_panel, icon="🏠", section="General", shortcut="Ctrl+1"),
    Pane("Settings", panel=settings_panel, icon="⚙️", section="General"),
    Pane("Stats", panel=stats_panel, icon="📊", section="Data", shortcut="Ctrl+3"),
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
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    active_key="home",  # deprecated → selected_key
)
```

**Options:** `Sidebar(*children, width, glass, corner_radius)`,
`SidebarItem(label, key, icon, active)` — `*children` are
`SidebarItem` / `SidebarGroup` / `Pane` / `(label, panel)` tuples.

`Pane.key` defaults to a random id — labels never collide, even when
duplicated or non-ASCII; pass an explicit `key` when you want a
readable identifier.  `shortcut` accepts the same combo forms as
`Page.on_shortcut`; a shortcut switch fires `change` like a click.
`selected_key` raises `ValueError` for unknown keys; setting `None`
clears the selection.  Clicks anywhere on an item — including the icon
or label — count: item-level events bubble up from its children.

### `Pane`

One selectable `Sidebar` entry and its content panel.

```python
pane = Pane("Home", panel=home_panel, icon="🏠", section="General", shortcut="Ctrl+1")
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
attached to a sidebar (new items are wired automatically).  Groups are
purely visual: selection, `items`, and `change` all operate on the flat
entry list in DOM order.  Consecutive panes sharing a `section` render
as one group; the same section reappearing later starts a new group.

---

## Theming

Three presets — `DARK`, `LIGHT`, `DEEP_BLUE` — as CSS custom properties.

```python
app.theme.set_mode("dark")  # dark | light | deep-blue
app.theme.toggle()  # cycle
Theme.modes  # ("dark", "light", "deep-blue")
Theme.mode_label("dark")  # "Light mode" — the next mode
await app.sync_theme()  # re-inject variables
```

Token families: `--color-bg`, `--color-surface`,
`--color-text-primary` / `--color-text-secondary`, `--color-accent`,
`--color-danger`, `--color-success`, `--color-border`, `--color-shadow`,
`--color-*-glass*` (frosted variants).

Components reference tokens via `Color(var="--color-*")` so theme
switches redraw with zero DOM diff.

Custom themes:

```python
from neony.application import Theme
my_theme = Theme(mode="dark", bg="#0a0a0f", accent="#7c4dff", ...)
app.theme = my_theme
await app.sync_theme()
```

---

## DOM Primitives

Import from `neony.dom`.

### `Color`

```python
Color(name="white")
Color(hex="#ff6b6b")
Color(rgb=(255, 107, 107))
Color(rgba=(255, 107, 107, 0.5))
Color(var="--color-accent")  # theme token
```

### `Styles`

Typed CSS properties — colors, dimensions, flexbox, spacing, typography,
borders (incl. per-corner radii), backdrop-filter, etc.

```python
Styles(
    display="flex",
    flex_direction="column",
    gap="12px",
    padding="24px",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(16px)",
    border_radius="12px",
    border_top_right_radius="12px",
    user_select="none",  # emits user-select + -webkit/-moz prefixes
)
```

Properties needing browser prefixes (`backdrop-filter`, `user-select`) are
emitted with their prefixed variants automatically — one Python field, all
engine spellings.

### `DomEvent`

Event payload forwarded from JavaScript:

```python
async def handler(event: DomEvent) -> None:
    event.key  # element identity
    event.type  # "click" | "input" | ...
    event.value  # element-specific data
    event.source  # "user" | "program"
```

### Raw elements

Every HTML element is a class: `Div`, `Span`, `Body`, `H1`–`H6`,
`Input`, `Button`, `Form`, `Table`, … They share the fluent event API
and support `build()` (HTML string) and `to_node()` (reactive snapshot).

```python
from neony.dom import Color, Div, Styles

card = Div(
    styles=Styles(padding="24px", background_color=Color(var="--color-surface")),
    container=["Hello"],
)
```

## Reactivity

Import from `neony.dom`. The V-DOM diff engine reacts to whole-tree
mutations; these primitives react to individual state changes.

### `Signal`

A single reactive value. Read with `signal()` (inside an effect/computed
this records a dependency); write with `set()` / `update()`.

```python
from neony.dom import Signal

count = Signal(0)
count.get()  # 0
count()  # same — call = read
count.set(5)
count.update(lambda c: c + 1)  # 6 — mutate in place
```

Writing an equal value (`==`) notifies nothing.

### `Computed`

A lazily evaluated, cached derived value. Recomputes only when a
dependency changed; computeds may depend on other computeds.

```python
from neony.dom import Computed, Signal

count = Signal(2)
double = Computed(lambda: count() * 2)
double()  # 4 (cached until count changes)
```

### `effect()` / `Effect`

Runs `fn` immediately, then re-runs it whenever any Signal it read
changes. Returns a disposable `Effect`.

```python
from neony.dom import Signal, effect

name = Signal("Neony")
stop = effect(lambda: print(f"hello {name()}"))  # prints immediately
name.set("world")  # re-runs
stop.dispose()  # unsubscribes everything
```

Re-runs are coalesced: with a running event loop they are deferred to
`loop.call_soon`; use `batch()` to coalesce synchronously.

```python
from neony.dom import batch, Signal

count = Signal(0)
effect(lambda: print(count()))  # prints 0
with batch():
    count.set(1)
    count.set(2)  # one re-run, prints 2
```

### `untrack()`

Run a function without recording dependency reads.

```python
from neony.dom import Signal, untrack

log = Signal(0)
effect(lambda: untrack(lambda: print(log())))  # reads but never subscribes
```

### `SharedSignal`

A `Signal` meant to be shared across every window — a write updates all
windows with a binding (each window schedules its own render).

```python
from neony.dom import SharedSignal

count = SharedSignal(0)
label_a.bind_text(count)  # window A
label_b.bind_text(count)  # window B
count.set(1)  # both windows update
```

### Declarative bindings

Bind a signal to an element (or component) so the DOM follows it
automatically — no manual refresh calls.

```python
from neony.dom import Signal

count = Signal(0)
label.bind_text(count, fmt=str)  # text content
bar.bind_style(count, "opacity", fmt=lambda v: v / 100)  # CSS property
img.bind_attr(count, "src")  # HTML attribute
panel.bind_visible(count)  # display: none when falsy
```

- `bind_text(signal, fmt=str)` — replaces the element's children with a
  single text string
- `bind_style(signal, prop, fmt=None)` — `prop` is a `Styles` field name
  (snake_case); a `None` signal value removes the property
- `bind_attr(signal, name, fmt=str)` — writes into the raw attribute bag
- `bind_visible(signal)` — hides (`display: none`) when falsy, restores
  the pre-binding display value when truthy
- `unbind()` — dispose every binding on the element

All five are also available on `Component` (the first four proxy to the
component's root element). A binding write marks the element dirty and
schedules a render for its window, so a signal changed from anywhere —
an event handler, a timer, another window — reaches the screen without
an explicit `render()` call.

### `Component.bind_value` — two-way value binding

`bind_value(signal)` binds a signal to a component's *value*, both
ways. Use it for direct state synchronization; it does not replace event
handlers for workflows that need event context, branching, asynchronous
side effects, or multiple state updates:

```python
name = Signal("")
inp = Input()
inp.bind_value(name)  # typing → name.set(); name.set() → field

vol = Signal(40)
slider.bind_value(vol)  # drags write back (floats)
bar = Progress()
bar.bind_value(vol)  # write-only follower

flag = Signal(False)
cb = Checkbox("x")
cb.bind_value(flag)  # binds `checked`, not `value`
```

- signal writes update the component value immediately and on change;
  user value changes write back to the signal
- `Computed` binds read-only (no write-back)
- the user channel is the component's `_value_event` (`input` on
  Input/Slider, `change` on Select/Checkbox/Switch/Dropdown); ComboBox
  binds both `input` and `change` so typing and suggestion picks are
  covered; Progress has no user channel and binds write-only
- `unbind_value()` / `unbind()` dispose the binding; programmatic value
  writes never fire callbacks, so the loop closes (user → signal →
  write-back re-applies the same value without re-dispatching)

For complex behavior, keep a named event handler alongside the binding:

```python
flag = Signal(False)
switch = Switch("Sync")
switch.bind_value(flag)  # simple state synchronization


async def on_sync_change(event: DomEvent) -> None:
    await sync_remote(bool(event.value))
    status.set("synced")


switch.on_change(on_sync_change)
```

### Dirty-subtree tracking

Every mutation marks the element dirty and propagates up to the root.
Rendering re-serializes only dirty elements; unchanged subtrees reuse
their cached snapshots (which the diff engine sees as identical, so zero
patches are emitted). This is automatic — `container.append()` and
property assignment both participate.
