# Getting started

> [中文版本](getting-started.zh.md) · [Documentation home](README.en.md)

This tutorial takes you from an empty Python file to a small reactive desktop
window. It uses the same public imports and patterns as
[`demo_hello.py`](../demo_hello.py).

## 1. Install the prerequisites

Neony requires Python 3.11 or newer and the native WebView runtime for your
platform. For a normal application install the package with:

```bash
python -m pip install neony
```

If you are working from this repository, install the development environment
with:

```bash
uv sync --group dev
```

Platform-specific dependencies are covered in
[Installation and platforms](guides/installation-platforms.en.md).

## 2. Build the first window

Create `hello.py` with the following code:

```python
from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack
from neony.dom import Signal

clicks = Signal(0)
counter = Button("Click me")

counter.bind_text(
    clicks,
    fmt=lambda count: f"Clicked {count} times!" if count else "Click me",
)
counter.on_click(lambda _event: clicks.update(lambda count: count + 1))

page = Page(gap="16px").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("Build desktop UI in pure Python.", role="secondary"),
        counter,
        gap="12px",
    )
)

launch(page, title="My App", width=480, height=360)
```

Run it from the directory containing the file:

```bash
python hello.py
```

The same example is maintained as
[`demo_hello.py`](../demo_hello.py); use that file when you want to compare the
tutorial with the repository's tested example.

## 3. Understand the tree

`Page` is the top-level container. Its `.add()` method is chainable and accepts
components or raw DOM elements. `VStack` and `HStack` are convenient flex
containers; `Flex` is available when you need all flex options explicitly.

Common layout controls are:

- `gap` for spacing between children;
- `padding` for space inside a container;
- `max_width` for a readable centered page;
- `fill=True` for chrome or layouts that should occupy the window height;
- `grow` on a flex component when it should consume remaining space.

The [`demo_builder.py`](../demo_builder.py) example shows a centered page with a
raw styled `Div` alongside framework components.

## 4. Handle user events

`on_click()` receives a `DomEvent`. For a simple counter, the handler only needs
to update the Signal. Use a named synchronous or asynchronous handler when you
need event fields, multiple steps, I/O, or error handling:

```python
async def save(event) -> None:
    print(event.type, event.value)


button.on_click(save)
```

Programmatic state changes update the UI but do not pretend to be user events.

Component callbacks for actual DOM interaction receive an event whose
`source` is `"user"`. The [Core API](api/core.en.md) covers the complete
event surface, including keyboard and shortcut handling.

## 5. Add reactive presentation

A Signal is read by calling it and written with `.set()` or `.update()`:

```python
name = Signal("")
label = Text("")
label.bind_text(name, fmt=lambda value: f"Hello, {value}!" if value else "")
```

Other useful bindings are:

```python
element.bind_style(signal, "width", fmt=lambda value: f"{value}%")
element.bind_attr(signal, "aria-label")
element.bind_visible(signal)
```

Use `Computed` for derived values and `effect()` for side effects. Use an
ordinary `on_*` handler when you need event context or multi-step behavior.

[`demo_reactive.py`](../demo_reactive.py) demonstrates Signal, Computed, Effect,
`bind_value`, `bind_style`, and `bind_visible` together.

## 6. Style the application

Components use typed `Styles` and semantic theme tokens rather than requiring
raw CSS for common cases:

```python
from neony.application.theme import stub
from neony.dom import Div, Styles

surface = Div(
    styles=Styles(
        padding="16px",
        border_radius="8px",
        background_color=stub.surface,
        color=stub.text_primary,
    )
)
```

Ten built-in presets span four visual families (`DARK`, `LIGHT`, and
`DEEP_BLUE` remain as aliases). See [Theming](api/platform-i18n.en.md)
for custom tokens, motion, transitions, or keyframes.

## 7. Choose the next guide

- Need installation help? Read [Installation and platforms](guides/installation-platforms.en.md).
- Need state synchronization? Read [Reactivity](api/reactive.en.md) and
  start with [`demo_reactive.py`](../demo_reactive.py).
- Need frameless windows? Read the API's `Page`, `WindowConfig`, and `TitleBar`
  sections, then run [`demo_custom_window.py`](../demo_custom_window.py).
- Need two windows? Run [`demo_multi_window.py`](../demo_multi_window.py).
- Need the component gallery? Run:

  ```bash
  uv run gallery
  ```

For exact signatures, use the [API index](api/README.en.md). For repository
changes, read [Contributing](../CONTRIBUTING.md).
