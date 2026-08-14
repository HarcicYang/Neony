# Components

> [中文版本](components.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

All inherit `Component` — fluent `on_*` chaining, state properties,
source-aware events. Import from `neony.application.elements`.

## Form controls

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

## Text & tabs

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
title string and raises `ValueError` for unknown titles. `active`
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

## Overlays & feedback

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

## Content

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

## Drag & reorder

### `Reorder` component

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
  horizontally (within a row) and vertically (into another row). The
  grid wraps at the board's width — pin `max_width` to force the wrap.
- Cards are not limited to text: `add()` / the constructor accept any
  content — a plain or reactive string, a whole `Component` (it mounts
  inside the card), or a raw `DOMElement`. **Bare content needs no
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
  target's). Card keys must be globally unique across the boards you
  let exchange cards.
- `on_drop` fires with `event.value` = the ordered card keys of the
  board that received the drop.

For the low-level drag primitive (`drag_payload`, `dataTransfer`),
see the [DOM & CSS → Drag & reorder](dom-css.en.md) section.
