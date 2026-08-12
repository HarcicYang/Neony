# Neony API Reference

> [中文参考](api.zh.md)

---

## Core

### `NeonApplication`

The application object — owns the window, the bridge, the theme, and
shared state. Construct with a `Config`, build a `Page`, then `run()`.

```python
from neony.application import Config, NeonApplication, Page, Theme, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # shared mutable state
app.theme = Theme.get("light")  # pick the initial preset before run()


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
`set_theme(theme)`, `sync_theme()`, `set_background(url)`, `render()`

**File dialogs** (all async — via a one-shot tkinter subprocess):
`open_file(...) -> str | None`, `open_files(...) -> list[str]`,
`save_file(...) -> str | None`, `select_folder(...) -> str | None`.
Cancelling returns `None` (or `[]` for the multi-select); a dialog that
can't be shown (no display, tkinter missing) also returns `None` —
never an exception.

```python
path = await app.open_file(
    title="Open image", default_dir="~/Pictures", filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
)
if path is None:
    return  # cancelled
paths = await app.open_files(...)  # [] on cancel
dest = await app.save_file(default_name="out.txt")  # str | None
folder = await app.select_folder()  # str | None
```

Each call spawns a short-lived subprocess that shows a self-drawn,
dark-themed file picker (the platform `tkinter.filedialog` is dated and
can't be restyled); the request dict is delivered by `multiprocessing`
pickling and the result returns on a one-way `Pipe` as a typed
`("ok", result)` / `("error", msg)` tuple — no stdout/JSON parsing. The
parent awaits the reply with `asyncio.to_thread`, so the event loop stays
responsive while the modal is up. Linux/macOS use `fork` (fast, no
`__main__` re-import), Windows `spawn`.

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

## Internationalization

Reactive, framework-wide i18n. The active language is a `Signal`; every
`tr` reference is a `Computed[str]`, so bound text updates live on
`set_language()` without losing widget state.

**Catalogs are typed, not dicts.** `Catalog` is a frozen pydantic model —
each field is a translation key with an English default; one instance per
language. Subclass it to add app keys (flat `str` fields or nested
sub-model groups); pydantic class defaults give per-key English fallback.

```python
from neony.application import Catalog, Common, Language, register_catalog, set_language, tr, tr_now


class FilesCatalog(Catalog):
    count: str = "{n} files"


class AppCatalog(Catalog):
    save: str = "Save"  # → tr.save
    files: FilesCatalog = FilesCatalog()  # → tr.files.count


register_catalog(Language.EN, AppCatalog())
register_catalog(
    Language.ZH,
    AppCatalog(
        save="保存",
        files=FilesCatalog(count="{n} 个文件"),
        common=Common(copy_text="复制", delete="删除", ok="确定", cancel="取消", close="关闭"),
    ),
)

tr.common.copy_text  # Computed[str] → "Copy" (updates live on switch)
tr.files.count.format(n=5)  # interpolation → "5 files"
tr_now(tr.common.copy_text)  # immediate read, no subscription (display-time)
set_language(Language.ZH)  # all tr.* bindings re-resolve
app.set_language(Language.ZH) / app.language  # app-level convenience
```

- **`Language`** — a `StrEnum` of the built-in languages
  (`EN/ZH/JA/FR/DE/ES/PT/RU`); `set_language` rejects unknown codes with
  `ValueError`. A valid language with no registered catalog falls back to
  English.
- **`Catalog` / `Common`** — frozen pydantic models
  (`extra="forbid"` catches key typos). `Common` carries the
  framework-owned labels (`copy_text`, `delete`, `ok`, `cancel`, `close`).
- **`tr`** — a chainable proxy. `tr.<key>` and `tr.<group>.<key>` each
  return a reactive `Computed[str]`; pass them to any component that
  accepts reactive text (`Text`, `Button` — and the shared
  `_mount_text` helper lets any component adopt it). `tr.<key>.get()`
  reads the current value.
- **`tr_now(tr.xx.xxx)`** — the current value without subscribing; for
  component defaults and menus resolved at display time. Safe inside
  effects (no dependency leak).
- **Reserved key names** — keys that collide with `Computed`'s API
  (`get`, `format`) or start with `_` cannot be referenced through the
  `tr` chain.
- Framework defaults (MessageBubble's built-in right-click menu,
  `PromptDialog`'s confirm/cancel) resolve through the catalog.

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

**Options:** `Tabs(*panes, glass, edge_fade=True)` — `*panes` are
`(title, panel)` pairs, equivalent to chained `add()` calls.
`edge_fade` toggles the scroll indicator (floating thumb + dynamic edge
fade) on the tab strip — set `False` to suppress it.

`selected_panel` binds the visible panel (the Component or its built
root — matched by identity, never rebuilt); `selected_title` selects by
title string and raises `ValueError` for unknown titles.  `active`
(index) and `active_key` are deprecated aliases — `active_key` returns
the tab title (it used to return an opaque element id).

### `Accordion` & `Collapsible`

```python
accordion = (
    Accordion(multiple=True)
    .section("Inputs & Forms", inputs_panel, checks_panel)
    .section("Layout", layout_panel, expanded=True)
)
accordion.on_change(lambda e: print(e.value))  # value = key of toggled section
accordion.expanded_keys = ["inputs & forms"]  # programmatic — no callback
accordion.expanded_keys  # list[str], the open sections
```

A `Collapsible` is one titled row that toggles a content panel between
hidden and visible; an `Accordion` stacks them in a single scroll flow.
With `multiple=True` (the default) several sections can stay open; with
`multiple=False` opening one closes the others. Only the `display`
property switches — expanding replays the built-in `neony-rise-in`
entrance animation, so no JS layer is involved.

`Collapsible(title, *content, expanded=False, key=None)` builds a single
section (also accepted positionally by `Accordion`); `key` defaults to
the lowercased title and identifies the section in `change` payloads.
`.section(title, *content, ...)` is the fluent shorthand that builds a
`Collapsible` and appends it in one call.

Listen with `on_change` (`event.value` is the key of the section the
user just toggled) and read the full open set with `expanded_keys`.
`Accordion` does **not** implement `selected_key` / `bind_selected` —
its selection is multi-valued, which does not fit the single-value
selection protocol.

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

### `Toast`

```python
toast = Toast(placement="top-right", duration=3.0, top_offset="40px")
page.add(toast)  # mount once at the page root
toast.show("File saved", type="success")  # success / info / error
toast.show("Update available", type="info", duration=5.0)
toast.show("New message", on_click=open_it)  # click the card (✕ excluded)
toast.placement = "bottom-left"  # relocate the stack live
toast.clear()  # remove everything
```

A host component stacking transient notifications at one of six screen
edges (`top-left` / `top-center` / `top-right` / `bottom-left` /
`bottom-center` / `bottom-right`). `show(text, type=...)` pushes a
card — `success` / `info` / `error` pick the accent dot colour;
`duration` overrides the host default per call, and `0` sticks until
the ✕ is clicked. `on_click` (sync or async) fires when the card is
clicked — the ✕ never fires it — and the card shows a pointer cursor
when it's clickable. `max_toasts` evicts the oldest card beyond the cap.
`top_offset` drops the top placements below window chrome (a `TitleBar`
height); bottom placements always hug the window edge. Each card enters
with a placement-specific directional animation (top placements drop
in, bottom ones rise up, corners slide diagonally) and leaves by
replaying the same keyframe reversed toward that edge. The host is a
full-viewport `position: fixed` layer at z-index 1100 with
`pointer-events: none` (clicks pass through to the page) — mount it at
the page root, away from `backdrop-filter` / `transform` ancestors.

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

### `MessageBubble`

```python
other = MessageBubble(
    "Hey! Have you seen the new gallery?",
    avatar=Avatar(name="Ada"),
    name="Ada",
    actions=[("reply", "Reply"), Icon.glyph("😊")],
)
me = MessageBubble("Hi!", from_me=True)
other.on_change(lambda e: print(e.value))  # right-click menu selection
other.on_action(lambda v: print(v))  # quick action click
```

A single chat message in the QQ/Telegram style. `from_me` flips the
row's alignment (self → right, others → left) and the bubble fill
(self → accent with white text, others → raised surface); the corner
toward the avatar is squared off. `avatar` is an optional `Avatar` on
the message's own side (built on construction), `name` an optional
sender label above the bubble. `actions` renders quick buttons below
the bubble that appear on hover — a `(value, label)` pair or `str`
becomes a text button, an `Icon` an icon button; clicking fires
`on_action(value)`. The action row is absolutely positioned below the
bubble, so showing it overlays the message beneath instead of shifting
the row's height. `menu_items` configures the built-in right-click
`Menu` (default Copy / Delete; `[]` disables it — `on_contextmenu`
still fires) and selections dispatch to `on_change` with the value.
NOTE: the menu is a `position: fixed` element inside the bubble; keep
chat panes away from `backdrop-filter` / `transform` ancestors.

### `NoticeBubble`

```python
NoticeBubble("You joined the group")
```

The centered system message — a muted pill that centers itself in a
flex message column (`align-self: center`) with a translucent
background. `text` is the message, or pass `content` for a custom
element; `text` is settable.

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
  overrides the default 12px corner radius; `width` / `height` fix the
  panel to a definite size (pair with the default non-`grow` mode).

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

`icon` is an `Icon` — `Icon.image(url_or_path)` paints a small image
left of the title (a fixed-size square that never stretches), the
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
suppress.  On a glass sidebar the thumb still shows but the edge fade is
skipped (mask-image conflicts with backdrop blur in WebKitGTK).

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
attached to a sidebar (new items are wired automatically).  Groups are
purely visual: selection, `items`, and `change` all operate on the flat
entry list in DOM order.  Consecutive panes sharing a `section` render
as one group; the same section reappearing later starts a new group.

### `Tree` & `TreeNode`

A collapsible navigation tree (left rail) owning a content host (right).
Arbitrary depth: a branch (a node with `children`) only expands /
collapses; a leaf (a node with a `panel`) selects into the host.  The
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
`expanded_branches=True` starts top-level branches open.  `edge_fade`
toggles the scroll indicator on the rail — set `False` to suppress.
Rows mirror the `Accordion` header styling — rounded, transparent, no
chrome around them — and the rail is bounded by the stage, scrolling
internally instead of growing the page.

`TreeNode(label, key, icon, panel, expanded, children, shortcut)` — a
node cannot carry both a `panel` and `children` (raises).  Fluent
builders: `.panel(panel)` attaches a leaf's content, `.children(*nodes)`
attaches a branch's children, `.key_(key)` sets the key — all chainable.

`key` defaults to a random id; `selected_key` raises `ValueError` for
unknown keys.  Branches carry `aria-expanded`, leaves `aria-selected`;
rows are keyboard-navigable (arrows move the focus ring, Enter / Space
activate, ← / → collapse / expand branches).

### `List` & `ListItem`

A scrollable, single-select data list (the listbox model).  Exactly one
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
strings or `ListItem(label, key=None, icon=None)`.  A string item's key
is its label; pass an explicit `key` when labels collide (duplicate keys
raise).  Rows are `role="option"` inside a `role="listbox"` container;
keyboard: Arrow Up/Down move the selection (clamped at the ends, each
move fires `change`), Home/End jump to the ends, Enter/Space select,
and a click selects.  The accent focus ring appears during arrow
navigation and clears on click.  `edge_fade` toggles the scroll
indicator.

Mounting contract: mount in a *definite-height* flex parent (e.g.
`VStack(..., grow=1)` or `GlassPanel(grow=True)`); the list scrolls its
rows internally instead of growing the page.

### `DataTable` & `Column`

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
unique.  Header cells with `sortable=True` sort on click (asc → desc,
switching columns starts asc); sorting is numeric-aware (or via
`sort_key`), keeps the selection, and is observable through `sort_by`.
The header is `position: sticky` inside the scroll container, so header
and rows stay aligned under horizontal scroll.

**Selection.** `selection="single"` (default) exposes `selected_key`
(programmatic writes never fire callbacks); `selection="multi"` exposes
`selected_keys` (accepts a `set`/`frozenset`/`list`/`None`) and a click
toggles membership — `change` carries the toggled key, read
`selected_keys` for the full set.  `bind_selected` works only in single
mode (raises otherwise); the wrong-mode property raises
`NotImplementedError`.

Keyboard: single mode arrows move the selection (firing `change`);
multi mode arrows move a focus ring and Space toggles it.  Home/End
jump; Enter/Space select or toggle.

Mounting contract: mount in a *definite-height* flex parent; the table
scrolls (both axes) internally.  `edge_fade` toggles the scroll
indicator.

### `Icon`

One icon used by `TitleBar`, `Sidebar`/`Pane`/`SidebarItem`, `Tabs` and
`TreeNode` — either an image or a text glyph, explicitly:

```python
Icon.image("https://example.com/logo.svg")  # fixed-size square (TitleBar-style)
Icon.image("assets/logo.png")
Icon.glyph("🏠")  # emoji / Nerd Font char
```

**Options:** `Icon(src, kind)` — constructed via `Icon.image(url_or_path)`
or `Icon.glyph(text)`; `render(size)` produces the element (the image
form paints a fixed-size square via `background-image: url(...)`,
contain/center/no-repeat, so it never stretches).

---

## Theming

Three built-in presets — `DARK`, `LIGHT`, `DEEP_BLUE` — exposed as CSS custom
properties. Each preset is an **immutable** `Theme` instance; constructing any
`Theme` auto-registers it under its `mode`.

```python
app.theme  # the active preset (defaults to DARK)
Theme.get("light")  # single-shot lookup of a registered preset by mode name
app.theme.next()  # the preset that follows the active one in toggle order
Theme.modes()  # registered mode names, in preset-construction order
Theme.mode_label("dark")  # "Light mode" — the label of the next mode
await app.set_theme(LIGHT)  # swap the active preset and re-inject variables
```

`Theme.set_mode` / `Theme.toggle` were removed — switching swaps the active
reference via `App.set_theme` rather than mutating an instance in place.

Token families: `--color-bg`, `--color-surface`,
`--color-text-primary` / `--color-text-secondary`, `--color-accent`,
`--color-on-accent` / `--color-on-danger` (text colour on a saturated accent /
danger fill), `--color-danger`, `--color-success`, `--color-border`,
`--color-shadow`, `--color-*-glass*` (frosted variants).

Components reference tokens via `Color(var="--color-*")` so theme
switches redraw with zero DOM diff.

Custom themes:

```python
from neony.application import Theme
my_theme = Theme(mode="sepia", bg="#1a1a2e", accent="#4a90d9", on_accent="#ffffff", ...)
# Construction auto-registers it; supply every token — Theme has no defaults.
await app.set_theme(my_theme)
Theme.get("sepia") is my_theme  # True
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
    event.type  # "click" | "input" | "scroll" | ...
    event.value  # element-specific data
    event.source  # "user" | "program"
```

Rich fields ride along on the events that carry them: modifier keys
(`ctrl_key` / `shift_key` / `alt_key` / `meta_key`), mouse coordinates
(`x` / `y` / `offset_x` / `offset_y`), pointer deltas
(`movement_x` / `movement_y` / `pointer_type`), wheel deltas
(`delta_x` / `delta_y` / `delta_mode`), scroll position
(`scroll_top` / `scroll_left` — the scrolled element's position,
dispatched to the nearest keyed ancestor, high-frequency so renders
are deferred), clipboard data (`clipboard_text` / `clipboard_html`),
in-app drag payloads (`drag_payload`), and dropped files
(`drop_files`).

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

### In-app drag & reorder

#### `Reorder` component

The ready-made way to reorder a collection is the `Reorder` board — a
flex container of draggable cards that owns the reorder internally:

```python
from neony.application.elements import Reorder, ReorderItem

board = Reorder(
    ReorderItem("First", key="a"),
    ReorderItem("Second", key="b"),
    "Third",  # plain strings become cards (key = label)
    direction="row",  # "row" or "column"
    wrap=True,  # row + wrap = a grid (both axes)
    size="76px",  # card size along the main axis
    max_width="336px",  # optional — pin 4 cards/row to force the wrap
)
board.on_drop(lambda e: e.value)  # ordered keys after a drag
board.order  # current keys in render order
```

- Cards are pre-marked draggable (the payload is declared up front — a
  Python round-trip in `dragstart` would be too late) and `drop` reorders
  the board itself; the diff engine emits a `ReorderPatch` for free.
- Both axes work: the engine detects the container's `flex-direction` and
  judges the insertion side by the cursor's half — `offset_x` for a `row`
  (first half inserts before, second after), `offset_y` for a `column`.
  A wrapping `row` board forms a grid, so a card can be dragged both
  horizontally (within a row) and vertically (into another row).  The
  grid wraps at the board's width — pin `max_width` to force the wrap.
- Cards are not limited to text: `add()` / the constructor accept any
  content — a plain or reactive string, a whole `Component` (it mounts
  inside the card), or a raw `DOMElement`.  **Bare content needs no
  wrapper and no explicit key**: plain strings use the label as the key,
  keyed DOM elements keep their own key, and everything else (a stack of
  `Card`s, …) gets an auto-generated `reorder-card-N` key.
- **Generic over card content** — `Reorder[T]` and `ReorderItem[T]` are
  typed by what the cards contain, so any component (or any other
  content type) can stand in exactly where `ReorderItem` used to, and
  `items` yields `ReorderItem[T]`:

  ```python
  from neony.application.elements import Card, Text

  board: Reorder[Card] = Reorder(Card(title="One"), Card(title="Two"))
  cards = board.items  # list[ReorderItem[Card]] — content typed as Card
  ```
- Boards exchange cards: dragging a card onto a card of another `Reorder`
  re-homes the landing slot into that board and the drop moves the card
  (it is removed from the source board's `order` and inserted into the
  target's).  Card keys must be globally unique across the boards you
  let exchange cards.
- `on_drop` fires with `event.value` = the ordered card keys of the
  board that received the drop.

#### Low-level primitive

Underneath the component, the engine delegates the full drag lifecycle —
`dragstart` / `dragenter` / `dragover` / `dragleave` / `drop` /
`dragend` — and a drop payload rides through `dataTransfer`.  Set
`drag_payload` on an element to make it draggable and declare the payload
the engine hands to `dataTransfer.setData` on dragstart:

```python
item = Div(key="row-1", drag_payload="row-1")  # draggable + declared payload
item.on_dragstart(lambda e: print("dragging", e.drag_payload))
item.on_dragend(lambda e: print("drag finished"))

drop_zone.on_drop(lambda e: reorder(e.drag_payload, e.key, e.offset_y))  # payload back
```

- `drag_payload` serializes to `draggable="true"` + `data-neony-drag`; the
  engine calls `setData("application/x-neony", payload)` in the dragstart
  handler and reads it back into `DomEvent.drag_payload` on `drop`.
- `dragover`/`drop` are already `preventDefault()`ed by the engine, so
  every keyed element is a valid drop target (and the webview never
  navigates to a dropped file).
- While dragging, the engine shows a dashed landing slot at the insertion
  point (cards shift position-only, FLIP-animated), and on drop everything
  settles into the final order with a matching animation.  Purely local in
  the engine — no IPC, no resizing.

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
