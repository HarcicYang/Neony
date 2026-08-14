# DOM & CSS

> [中文版本](dom-css.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

The typed DOM layer underneath the components — raw HTML elements,
`Styles`, `Color`, the `DomEvent` payload, and the low-level drag
primitive. Import from `neony.dom`.

## `Color`

```python
Color(name="white")
Color(hex="#ff6b6b")
Color(rgb=(255, 107, 107))
Color(rgba=(255, 107, 107, 0.5))
Color(var="--color-accent")  # theme token
```

## `Styles`

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

## `DomEvent`

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

## Raw elements

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

## Drag & reorder

Beneath the [`Reorder`](components.en.md#reorder-component) component, the
engine delegates the full drag lifecycle — `dragstart` / `dragenter` /
`dragover` / `dragleave` / `drop` / `dragend` — and a drop payload rides
through `dataTransfer`. Set `drag_payload` on an element to make it
draggable and declare the payload the engine hands to
`dataTransfer.setData` on dragstart (it must be synchronous — a Python
round-trip in `dragstart` would be too late):

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
  settles into the final order with a matching animation. Purely local in
  the engine — no IPC, no resizing.
