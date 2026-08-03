# Neony

Reactive desktop UI framework for Python, built on [LumiView](https://lumiview.dev).

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)

> [中文文档](readme.zh.md) · [API Reference (EN)](docs/api.en.md) · [API 参考 (中文)](docs/api.zh.md)

---

## Overview

Neony renders a reactive DOM in a native window. You compose your UI from
Python objects — components, layouts, styles — and Neony diff-updates the
browser DOM automatically. No HTML, no JavaScript, no CSS strings.

- **Pure Python API** — components, layouts and events, no web tech required
- **Reactive engine** — first render mounts the tree, later renders send minimal patches
- **3 theme presets** — dark / light / deep-blue via CSS custom properties
- **Frosted glass** — translucent surfaces with backdrop blur
- **Custom window chrome** — frameless, transparent, custom TitleBar
- **Native window effects** — blur / acrylic / mica materials

---

## Installation

```bash
pip install neony
```

Requires Python 3.11+ and the platform WebView stack (WebKitGTK on Linux,
WebView2 on Windows, WKWebView on macOS).

---

## Quick Start

### The simple way — `launch()`

```python
from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack

counter = Button("Click me")


async def on_click(event) -> None:
    counter.label = "Clicked!"


counter.on_click(on_click)

page = Page(gap="16px").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("Build desktop UI in pure Python.", role="secondary"),
        counter,
        gap="12px",
    )
)

launch(page, title="My App", width=480, height=360, devtools=True)
```

### Full control — `NeonApplication`

```python
from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="My App", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.my_value = "hello"


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
```

---

## Components

Import from `neony.application.elements`.

| Component | Description |
|---|---|
| `Button` | Themed push button — primary / ghost / danger variants, hover & press feedback |
| `Checkbox` | Custom-styled checkbox with label and `change` event |
| `Input` | Single-line text field — text / password / email / number… |
| `Heading` | Themed heading (h1–h6) with automatic sizing |
| `Text` | Inline body copy with semantic roles (primary / secondary / danger / success) |
| `Tabs` | Tab bar + panels, exactly one visible at a time |
| `Flex` | Generic flex container with full control |
| `VStack` / `HStack` | Vertical / horizontal flex stacks |
| `Spacer` | Flexible empty space that absorbs leftover room |
| `Separator` | Subtle horizontal divider |
| `GlassPanel` | Frosted-glass container with optional background image |
| `TitleBar` | Custom window chrome for frameless windows — drag, minimize / maximize / close |
| `Sidebar` / `SidebarItem` | Vertical navigation rail, glass-matched to the TitleBar |

All components share the fluent API:

```python
button.on_click(handler)  # attach events
button.label = "New"  # mutate state (no callback fires)
button.reset_styles(Styles(...))  # replace the base look
```

---

## Window Features

### Frameless custom titlebar

Set `decorations=False` — the `TitleBar` component manages everything:

```python
app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony Studio",
            width=600,
            height=480,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

titlebar = TitleBar("Neony Studio")
titlebar.on_close(lambda e: print("bye"))
titlebar.override_close(confirm_close)  # take over for confirm-before-close

page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
page.add(VStack(titlebar, content, gap="0px", grow=1))
```

- Drag the titlebar to move the window; double-click to maximize.
- `override_close(fn)` disables the built-in action for confirm-before-close flows.

### Transparent windows & native effects

```python
window = WindowConfig(transparent=True, always_on_top=True)
await app.apply_blur()  # native blur behind the window
await app.apply_acrylic()  # Windows 11 acrylic
await app.apply_mica()  # Windows 11 mica
```

### Programmatic window control

`set_title()`, `set_size()`, `minimize()`, `toggle_maximize()`,
`set_fullscreen()`, `start_dragging()`, `close()`, `eval_js()` —
all on `NeonApplication`. Every method takes `window_index=0` for
multi-window apps.

### Multi-window

Pass several pages to `run()` — each opens its own window. All windows
share one LumiView event loop and the app's `state` namespace; an event
handler only re-renders the window it came from.

```python
app.run(page_one, page_two)


async def on_ready() -> None:
    await app.set_title("Counter", window_index=0)
    await app.set_title("Display", window_index=1)


app.ready_handler = on_ready
```

`launch()` accepts a list too:

```python
launch([page_one, page_two], title="Multi", width=360, height=240)
```

---

## Theming

Three built-in presets — `DARK` (default), `LIGHT`, `DEEP_BLUE` — exposed as
CSS custom properties on `:root`, so a theme switch redraws the whole UI with
zero DOM diff.

```python
app.theme.set_mode("light")  # dark | light | deep-blue
app.theme.toggle()  # cycle through presets
await app.sync_theme()  # re-inject the CSS variables
```

### Background image & glass

```python
await app.set_background("https://example.com/bg.webp")
# glass components (glass=True, GlassPanel) blur it through translucent surfaces
```

---

## Demos

Run from the repository root:

| File | Shows |
|---|---|
| `test_gallery.py` | Component gallery with docs & code samples, glass TitleBar |
| `test_custom_window.py` | Frameless window: TitleBar + Sidebar chrome |
| `test_transparent_panel.py` | Floating transparent panel with native blur |
| `test_multi_window.py` | Two windows sharing one app state |
| `test_reactive.py` | Minimal `launch()` app |
| `test_builder.py` | Raw DOM builder without the app layer |

```bash
python test_gallery.py
```

---

## License

[GPL-3.0-or-later](LICENSE) © HarcicYang
