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

**Attributes:** `config`, `state`, `theme`, `ready_handler`

**Window methods** (all async):
`set_title(title)`, `set_size(w, h)`, `minimize()`, `toggle_maximize()`,
`is_maximized()`, `set_fullscreen(f)`, `start_dragging()`, `close()`,
`apply_blur(color?)`, `apply_acrylic(color?)`, `apply_mica()`,
`clear_effect(effect)`, `eval_js(script)`

**Theme / rendering:**
`sync_theme()`, `set_background(url)`, `render()`

### `launch()`

One-liner entry point — builds a `Config` from keyword arguments.

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

Accepts all `WindowConfig` / `WebViewConfig` fields plus
`mount_selector` and `auto_render`.

### `Config`, `WindowConfig`, `WebViewConfig`

Pydantic config models. `WindowConfig` covers geometry and appearance
(`title`, `width`, `height`, `decorations`, `transparent`,
`always_on_top`, `resizable`, …). `WebViewConfig` covers runtime
options (`devtools`, `incognito`, `user_agent`, `javascript`, …).

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

**Methods:** `add(child)` (chainable), `build()` → DOMElement

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
tabs = Tabs(glass=True)
tabs.add("One", panel_one)
tabs.add("Two", panel_two)
tabs.active = 1  # programmatic switch
tabs.active_key  # key of active panel
```

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

**Options:** `title`, `show_minimize`, `show_maximize`, `show_close`, `height`

The bar is a drag region (double-click maximizes); control buttons carry
internal `data-window-action` attributes routed through the
WindowControls bridge — an implementation detail users never see.

### `Sidebar` & `SidebarItem`

Vertical navigation, glass-matched to `TitleBar`.

```python
sidebar = Sidebar(
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    active_key="home",
)
sidebar.on_change(lambda e: switch(e.value))  # value = item key
sidebar.active_key = "settings"  # programmatic, no callback
```

**Options:** `Sidebar(width, glass, corner_radius)`,
`SidebarItem(label, key, icon, active)`

Clicks anywhere on an item — including the icon or label — count:
item-level events bubble up from its children.

---

## Theming

Three presets — `DARK`, `LIGHT`, `DEEP_BLUE` — as CSS custom properties.

```python
app.theme.set_mode("dark")  # dark | light | deep-blue
app.theme.toggle()  # cycle
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

All four are also available on `Component` (they proxy to the component's
root element). A binding write marks the element dirty and schedules a
render for its window, so a signal changed from anywhere — an event
handler, a timer, another window — reaches the screen without an explicit
`render()` call.

### Dirty-subtree tracking

Every mutation marks the element dirty and propagates up to the root.
Rendering re-serializes only dirty elements; unchanged subtrees reuse
their cached snapshots (which the diff engine sees as identical, so zero
patches are emitted). This is automatic — `container.append()` and
property assignment both participate.
