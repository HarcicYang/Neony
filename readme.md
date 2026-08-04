# Neony

Reactive desktop UI framework for Python, built on [LumiView](https://lumiview.dev).

[![License: LGPL-3.0](https://img.shields.io/badge/license-LGPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)

> [中文文档](readme.zh.md) · [API Reference (EN)](docs/api.en.md) · [API 参考 (中文)](docs/api.zh.md) · [Contributing](CONTRIBUTING.md)

---

## Overview

> **Status: alpha** — the API is still settling. Feedback and
> contributions are welcome.

Neony renders a reactive DOM in a native window. You compose your UI from
Python objects — components, layouts, styles — and Neony diff-updates the
browser DOM automatically. No HTML, no JavaScript.

It builds on [LumiView](https://lumiview.dev), which uses the same Rust
`tao`/`wry` webview stack as [Tauri](https://tauri.app).

- **Pure Python API** — components, layouts and events, no need for non-python codes
- **Fine-grained reactivity** — `Signal` / `Computed` / `Effect` primitives with declarative bindings
- **Dirty-subtree diffing** — only changed elements re-serialize; unchanged subtrees reuse cached snapshots
- **Style direct-patch** — pure style/attr changes (hover, focus, press) patch straight from the snapshot cache, skipping serialization and diff
- **Same stack as Tauri** — Rust `tao`/`wry` webviews via LumiView
- **3 theme presets** — dark / light / deep-blue via CSS custom properties
- **(Optional) Frosted glass** — translucent surfaces with backdrop blur
- **Colour-matched glow** — focus rings and hover glows tinted with each element's semantic colour
- **Theme-matched scrollbars** — scrollbars follow the active theme (WebKit + Firefox)
- **Custom window chrome** — frameless, transparent, custom TitleBar
- **(Supported platform only) Native window effects** — blur / acrylic / mica materials

---

## Installation

```bash
pip install neony
```

Requires Python 3.11+ and the platform WebView stack (WebKitGTK on Linux,
WebView2 on Windows, WKWebView on macOS). X11 is not supported — see the
[Roadmap](#roadmap).

---

## Quick Start

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

---

## Components

Import from `neony.application.elements`.

| Component                 | Description                                                                    |
| ------------------------- | ------------------------------------------------------------------------------ |
| `Button`                  | Themed push button — primary / ghost / danger variants, hover & press feedback |
| `Checkbox`                | Custom-styled checkbox with label and `change` event                           |
| `Input`                   | Single-line text field — text / password / email / number…                     |
| `Heading`                 | Themed heading (h1–h6) with automatic sizing                                   |
| `Text`                    | Inline body copy with semantic roles (primary / secondary / danger / success)  |
| `Tabs`                    | Tab bar + panels, exactly one visible at a time                                |
| `Flex`                    | Generic flex container with full control                                       |
| `VStack` / `HStack`       | Vertical / horizontal flex stacks                                              |
| `Spacer`                  | Flexible empty space that absorbs leftover room                                |
| `Separator`               | Subtle horizontal divider                                                      |
| `GlassPanel`              | Frosted-glass container with optional background image                         |
| `TitleBar`                | Custom window chrome for frameless windows — drag, minimize / maximize / close |
| `Sidebar` / `SidebarItem` | Vertical navigation rail, glass-matched to the TitleBar                        |

All components share a fluent, chainable API — see the
[API reference](docs/api.en.md) for usage.

---

## Window Features

- **Frameless custom titlebar** — set `decorations=False`, add a
  `TitleBar`, and drag / minimize / maximize / close all work
  automatically. See [`docs/api.en.md`](docs/api.en.md) and the
  [`test_custom_window.py`](test_custom_window.py) demo.
- **Transparent windows & native effects** — `transparent=True` plus
  `apply_blur()`, `apply_acrylic()`, `apply_mica()`. See
  [`test_transparent_panel.py`](test_transparent_panel.py).
- **Programmatic window control** — `set_title()`, `set_size()`,
  `minimize()`, `toggle_maximize()`, `close()`, … all on
  `NeonApplication`, with `window_index=0` for multi-window apps.
- **Multi-window** — `run(*pages)` opens one window per page, all
  sharing one event loop and `app.state`. `launch([...])` accepts a list.
  See [`test_multi_window.py`](test_multi_window.py).

---

## Theming

Three built-in presets — `DARK` (default), `LIGHT`, `DEEP_BLUE` — exposed as
CSS custom properties on `:root`, so a theme switch redraws the whole UI with
zero DOM diff. Scrollbars and interaction glows (focus rings, hover halos)
reference the same `--color-*` tokens, so they follow theme switches too.
See the [API reference](docs/api.en.md) for switching and custom themes.

---

## Demos

Run from the repository root:

| File                        | Shows                                                            |
| --------------------------- | ---------------------------------------------------------------- |
| `test_gallery.py`           | Component gallery with docs & code samples, glass TitleBar       |
| `test_custom_window.py`     | Frameless window: TitleBar + Sidebar chrome                      |
| `test_transparent_panel.py` | Floating transparent panel with native blur                      |
| `test_multi_window.py`      | Two windows sharing one app state                                |
| `test_reactive.py`          | Signal-based API: declarative bindings instead of manual refresh |
| `test_builder.py`           | Raw DOM builder without the app layer                            |

```bash
uv run test_gallery.py
```

---

## Roadmap

Planned work, roughly in priority order.

### Performance

- [x] **Hover de-noise** — `mouseover`/`mouseout`/`focus`/`blur` render deferred (one frame of coalescing)
- [~] **Input throttling** — coalescing render pipeline in place; `on_input` still renders per keystroke, hooking it into the deferred path is a one-line change
- [x] **Dirty-subtree diffing** — only changed elements re-serialize; mutations mark their ancestors dirty
- [x] **Snapshot reuse** — unchanged subtrees reuse cached snapshots, skipping `to_node()`
- [x] **Style direct-patch** — pure style changes bypass the full diff

### Reactivity

- [x] **Signal primitives** — `Signal` / `Computed` / `Effect` with automatic dependency tracking and `batch()` coalescing
- [x] **Declarative bindings** — `bind_text()` / `bind_style()` / `bind_attr()` / `bind_visible()` on elements and components
- [x] **Cross-window reactivity** — a shared signal write updates every window with a binding
- [x] **JS unit tests** — vitest + jsdom cover the browser runtime (event delegation, patch engine)

### Components

- [ ] **Form controls** — Radio, Switch, Select/ComboBox, Slider, Progress
- [ ] **Overlays** — Dialog/Modal, Tooltip, Dropdown, Menu
- [ ] **Data views** — DataTable, List, Tree
- [ ] **Content** — Card, Avatar, Badge, Image

### Animation

- [ ] **CSS `transition` support** in `Styles`
- [ ] **Built-in animated containers**
- [ ] **Transition hooks**

### Platform verification

- [x] **Windows (WebView2)**
- [ ] **macOS (WKWebView)**
- [x] **Linux desktops (Wayland)**
- [ ] **HiDPI / mixed-DPI scaling**

> NOTE:
> For Linux, we won't test on x11, please do it yourself
> For macOS, we don't have a device to test on, please do it yourself too.

---

## Development

This project uses [uv](https://docs.astral.sh/uv/) as the environment
manager and runner.

```bash
uv sync --group dev   # install dependencies (incl. dev tools)
npm ci                # install JS dev dependencies (vitest, jsdom)

uv run test_gallery.py            # run a demo
uv run pytest -q                  # run the Python test suite
uv run ruff check .               # lint
uv run ruff format --check .      # format check
uv run pyrefly check              # type check
npm test                          # run the JS test suite (vitest)
```

---

## License

[LGPL-3.0-or-later](LICENSE) © HarcicYang
