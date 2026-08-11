# Neony

Reactive desktop UI framework for Python, built on [LumiView](https://github.com/xiaosuawa/lumiview).

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
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
- **Scroll indicator** — native scrollbars are hidden; scroll surfaces get a theme-matched floating thumb (faint at rest, strengthens on scroll/hover, draggable, click-to-page) plus a dynamic edge fade that only shows where content actually overflows
- **Custom window chrome** — frameless, transparent, custom TitleBar
- **(Supported platform only) Native window effects** — blur / acrylic / mica materials

---

## Installation

```bash
pip install neony
```

Requires Python 3.11+ and the platform WebView stack (WebKitGTK on Linux,
WebView2 on Windows, WKWebView on macOS). X11 is not supported — see the
[Roadmap](ROADMAP.md). The system tray needs
`libayatana-appindicator` on Linux.

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
| `Radio` / `RadioGroup`    | Mutual-exclusion radio options with group `change` carrying the value          |
| `Switch`                  | Track + thumb toggle built on a native checkbox                                |
| `Select`                  | Themed dropdown — `str` or `(value, label)` options                            |
| `ComboBox`                | Editable text with a themed suggestion popup                                   |
| `Slider`                  | Slider with animated accent fill — stepped or stepless (`step="any"`)          |
| `Progress`                | Progress bar with animated fill — determinate or sliding `indeterminate`      |
| `Dialog`                  | Fixed scrim + centered glass panel — scrim / Escape / ✕ / click-away close    |
| `Tooltip`                 | Hover bubble wrapped around an anchor, placement offsets, hover delay        |
| `Dropdown`                | Themed popup under a trigger — full keyboard nav + click-away close          |
| `Menu`                    | Fixed popup positioned at the cursor (`open_at(x, y)` from contextmenu)      |
| `Toast`                   | Transient notifications at a screen edge — 6 placements, success/info/error, placement-tied directional animations |
| `Input`                   | Single-line text field — text / password / email / number…                     |
| `Heading`                 | Themed heading (h1–h6) with automatic sizing                                   |
| `Text`                    | Inline body copy with semantic roles (primary / secondary / danger / success)  |
| `Tabs`                    | Tab bar + panels, exactly one visible at a time — constructor children, `selected_panel` / `selected_title` / `selected_key` |
| `Accordion` / `Collapsible` | Expandable sections in one scroll flow — fluent `.section()`, `multiple` open mode, `expanded_keys`, `on_change` |
| `Tree` / `TreeNode`       | Collapsible navigation tree + content host — arbitrary depth, fluent builders, leaf selection shows its panel on the right |
| `List` / `ListItem`       | Scrollable single-select data list — listbox model, arrow keys move selection, `selected_key` / `bind_selected` |
| `DataTable` / `Column`    | Column config + data rows — sticky header, click-to-sort, single / multi row selection |
| `Icon`                    | One icon — `Icon.image(url)` fixed-size square or `Icon.glyph(text)`, shared by TitleBar / Sidebar / Tabs / Tree |
| `Flex`                    | Generic flex container with full control                                       |
| `VStack` / `HStack`       | Vertical / horizontal flex stacks                                              |
| `Spacer`                  | Flexible empty space that absorbs leftover room                                |
| `Separator`               | Subtle horizontal divider                                                      |
| `GlassPanel`              | Frosted-glass container with optional background image                         |
| `TitleBar`                | Custom window chrome for frameless windows — drag, minimize / maximize / close |
| `Sidebar` / `SidebarItem` | Vertical navigation owning its content panes — `Pane`, `SidebarGroup` sections, per-pane shortcuts; glass-matched to the TitleBar |
| `Pane`                    | Selectable Sidebar entry + content panel — `key`, `icon`, `section`, `shortcut` |
| `SidebarGroup`            | Titled section of a Sidebar — small uppercase label above its items          |
| `Image`                   | Themed image in a rounded, overflow-hidden frame (`src` is any URL)            |
| `Avatar`                  | User avatar — image, letter initial, or placeholder, optional corner `badge`   |
| `Badge`                   | Status pill or corner count — variants, status dot, `99+` clamp, zero hides    |
| `Card`                    | Titled content panel — actions, footer, optional frosted-glass `glass` surface |
| `MessageBubble`           | QQ/Telegram-style chat message — from_me alignment/colors, optional avatar + name, built-in right-click menu, hover quick actions |
| `NoticeBubble`            | Centered system message pill for chat notices                                   |

All components share a fluent, chainable API — see the
[API reference](docs/api.en.md) for usage.

---

## Window Features

- **Frameless custom titlebar** — set `decorations=False`, add a
  `TitleBar`, and drag / minimize / maximize / close all work
  automatically. See [`docs/api.en.md`](docs/api.en.md) and the
  [`demo_custom_window.py`](demo_custom_window.py) demo.
- **Transparent windows & native effects** — `transparent=True` plus
  `apply_blur()`, `apply_acrylic()`, `apply_mica()`. See
  [`demo_transparent_panel.py`](demo_transparent_panel.py).
- **Programmatic window control** — `set_title()`, `set_size()`,
  `minimize()`, `toggle_maximize()`, `close()`, … all on
  `NeonApplication`, with `window_index=0` for multi-window apps.
- **Multi-window** — `run(*pages)` opens one window per page, all
  sharing one event loop and `app.state`. `launch([...])` accepts a list.
  See [`demo_multi_window.py`](demo_multi_window.py).
- **System tray** — `app.tray = Tray(icon, tooltip, items=[...])` adds
  a tray icon with a native context menu; `close_to_tray=True` hides
  the app instead of quitting on close. Linux needs
  `libayatana-appindicator`. See
  [`demo_tray.py`](demo_tray.py).

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

| File                          | Shows                                                            |
| ----------------------------- | ---------------------------------------------------------------- |
| `demo_hello.py`               | Minimal first app (same as the Quick Start example)              |
| `gallery` package (`uv run gallery`) | Component gallery with docs & code samples, glass TitleBar |
| `demo_custom_window.py`       | Frameless window: TitleBar + Sidebar chrome                      |
| `demo_transparent_panel.py`   | Floating transparent panel with native blur                      |
| `demo_multi_window.py`        | Two windows sharing one app state                                |
| `demo_reactive.py`            | Signal-based API: declarative bindings instead of manual refresh |
| `demo_accordion.py`           | Accordion: expandable grouped sections in one scroll flow        |
| `demo_tree.py`                | Tree: collapsible navigation tree + content host                 |
| `demo_tray.py`                | System tray: native menu + close-to-tray pattern                 |
| `demo_builder.py`             | Minimal app built with `Page` + components + `launch()`    |

```bash
uv run gallery
```

---

## Roadmap

Planned work lives in [ROADMAP.md](ROADMAP.md) — performance, events,
lifecycle, components, animation, platform integration and verification.

---

## Development

This project uses [uv](https://docs.astral.sh/uv/) as the environment
manager and runner.

```bash
uv sync --group dev   # install dependencies (incl. dev tools)
npm ci                # install JS dev dependencies (vitest, jsdom)

uv run gallery                  # run the component gallery
uv run pytest -q                  # run the Python test suite
uv run ruff check .               # lint
uv run ruff format --check .      # format check
uv run pyrefly check              # type check
npm test                          # run the JS test suite (vitest)
```

---

## License

[Apache-2.0](LICENSE) © HarcicYang
