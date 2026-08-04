# Changelog

## Unreleased

### Added

- **Theme-matched scrollbars** — scrollbars follow the active theme via
  `--color-*` tokens (`Theme.to_css()` emits WebKit `::-webkit-scrollbar`
  rules + Firefox `scrollbar-color`/`scrollbar-width`).
- **Colour-matched glow** — focus rings (3px halo via
  `Theme.focus_glow(role)`) and hover glows tinted with each element's
  semantic colour: `Button` (per variant), `Input`, `Checkbox`, and
  `GlassPanel` (persistent per-role glow).
- **`Theme.focus_glow(role)`** helper — returns a focus-ring box-shadow
  value referencing the role's glass token.
- **Linux app name (WM_CLASS)** — `g_set_prgname` via ctypes so the
  taskbar/dock shows the app name instead of `python3`.
- **Reactive primitives** (`neony.dom`) — `Signal`, `Computed`, `Effect`,
  plus `batch()`, `untrack()` and `SharedSignal` for cross-window state.
  Automatic dependency tracking, cached derived values, and coalesced
  re-runs (`loop.call_soon` with a running loop, `batch()` synchronously).
  A crashing effect inside a flush is isolated — the rest of the batch
  still runs.
- **Declarative bindings** — `bind_text()`, `bind_style()`, `bind_attr()`,
  `bind_visible()` and `unbind()` on `DOMElement` and `Component`. A bound
  signal write marks the element dirty and schedules a render for its
  window (armed per-tree by `NeonApplication`) — no manual refresh calls.
- **Dirty-subtree tracking** — mutations mark the element (and, via
  parent pointers, every ancestor) dirty; rendering re-serializes only
  dirty elements. Unchanged subtrees reuse cached snapshots, which the
  diff engine sees as identical — zero patches. In-place `container`
  mutations participate through a parent-aware list proxy.
- **Cross-window reactivity** — a write to a `SharedSignal` updates every
  window whose tree binds it, each through its own render request.
- **JavaScript unit tests** — vitest + jsdom covering the browser runtime
  (event delegation, patch engine, DOM builder); wired into CI via
  `npm ci && npm test` (replacing the `node --check` syntax-only step).
- **Python test suites** — `tests/test_reactive.py` (primitives),
  `tests/test_dirty_tracking.py`, `tests/test_binding.py`,
  `tests/test_cross_window.py`, `tests/test_effect.py`.

### Changed

- **Render path** — `Neony.render()` serializes through a per-key snapshot
  cache; only dirty subtrees are re-walked. `test_reactive.py` rewritten
  around the signal API (declarative bindings instead of manual refresh).

- **LumiView `0.1.0.dev1` → `0.1.0.dev2`** — `Neony` now subclasses the
  explicit `Plugin` lifecycle class (duck-typed `on_init`/`on_ready`
  hooks are ignored in dev2); `uv.lock` regenerated.
- **Startup sequencing** — the fixed `asyncio.sleep(0.5)` after
  `Window.create` is replaced with a `WindowHookEvent.PageLoadFinished`
  wait (5s timeout guard); the window's DOM mounts the moment the page
  is actually ready.
- **Render coalescing (hover de-noise)** — `Neony.render()` gains an
  `immediate` flag; `mouseover`/`mouseout`/`focus`/`blur` render deferred
  by one frame (~16ms), so a burst of style-only events coalesces into a
  single full-tree render. `NeonApplication.render()` forwards it.

### Fixed

- `PageLoadFinished` handler crash: the event carries the loaded URL as
  an argument, which overwrote the default-bound event; the lambda now
  absorbs `*_args`.
- `captureValue` (JavaScript) forwarded `value: ""` for `<button>`
  elements instead of `null` — a button's default `value` IDL property
  shadowed the null fallback.
- `captureValue` (JavaScript) lost the pressed key for `keydown`/`keyup`
  on inputs — the element's `value` was captured before `event.key`.

### Docs

- `readme.md` / `readme.zh.md` — new features, theming section, roadmap
  checkboxes; roadmap marks dirty-subtree diffing / snapshot reuse done
  and adds a Reactivity section.
- `docs/api.en.md` / `docs/api.zh.md` — new Reactivity chapter (Signal,
  Computed, Effect, batch, untrack, SharedSignal, bindings, dirty-subtree
  tracking); the standalone bilingual `docs.md` was split into the two
  per-language files and removed.

---

## 0.1.0 — 2026-08-03

### Added

- **Multi-window**: `run(*pages)` opens one window per page, all sharing
  one event loop and `app.state`; `launch([page1, page2], ...)` accepts a
  list too. Window control methods take `window_index` (default 0).
- **Window control API** on `NeonApplication`: `set_title()`, `set_size()`,
  `minimize()`, `toggle_maximize()`, `is_maximized()`, `set_fullscreen()`,
  `start_dragging()`, `close()`, `apply_blur()`, `apply_acrylic()`,
  `apply_mica()`, `clear_effect()`, `eval_js()`.
- **`TitleBar` component**: custom window chrome for frameless windows
  (`decorations=False`). Zero-config drag + minimize/maximize/close;
  `on_close(fn)` for extra callbacks; `override_close(fn)` for full
  takeover. `WindowControls` bridge scope loads automatically.
- **`Sidebar` + `SidebarItem` components**: vertical navigation rail,
  glass-matched to the `TitleBar`. Active item with accent border;
  `on_change` event with item key; programmatic `active_key` switching.
- **Frame rounding**: `Page(radius="12px")` clips the chrome stack to a
  rounded window frame; `GlassPanel(radius=...)` for content panels.
- **`Page(fill=True)`**: stretches the content column to the full window
  height using a percentage height chain (`html → body → #neony-root →
  Page`) — works correctly under tiling window managers.
- **Per-corner border radii** on `Styles`: `border_top_left_radius`,
  `border_top_right_radius`, `border_bottom_left_radius`,
  `border_bottom_right_radius`.
- **`GlassPanel(grow=True)`**: fills the parent content region.
- **`surface_panel_glass_bg` token**: denser glass (0.85 alpha) for
  content panels, distinct from chrome glass (0.60 alpha).
- **`box-sizing: border-box` global reset**: prevents `width:100% +
  padding` overflow.

### Changed

- **Glass tokens per-theme**: dark mode glass is neutral charcoal
  (`rgba(40,40,44,0.60)`); deep-blue glass is blue-tinted
  (`rgba(34,34,74,0.60)`); light unchanged. Chrome stays aggressively
  transparent; content panels use the denser `surface_panel_glass_bg`.
- **`text_secondary` values**: dark `#707088`, deep-blue `#8080a0` —
  balanced for readability on glass backdrops.
- **TitleBar styling**: aggressive blur (20px + saturate), padding
  balanced on all four sides (`line-height` match), close button turns
  danger-red on hover with full restore on mouseout.
- **`sync_theme()`**: skips body background for transparent windows.
- **Gallery overhaul**: each tab now has a description, code sample
  (`CodeBlock` util), and live demo; window is frameless with a glass
  `TitleBar`.
- **`Flex` / `VStack` / `HStack`**: `min-height: 0` flex fix prevents
  overflow clipping; `grow` parameter for filling parent space.

### Fixed

- JS event routing: `data-window-action` only fires on `click` events,
  not on `mouseover`/`mouseout` (hover on the close button no longer
  closes the window).
- TitleBar hover state machine: `_apply_hover()` now restores base
  colours on mouseout instead of freezing the hover style.
- `set_background()`: background sits on a dedicated `#neony-bg` layer
  instead of `body` (transparent windows skip body-background painting
  in WebKitGTK). Tint uses `var(--color-bg)` via CSS custom property —
  follows theme switches automatically.
- `render()`: silently drops patches when the WebView is no longer
  initialized (window closing/closed), preventing RuntimeError from
  in-flight events.
- Content area vertical scrolling: `min-height: 0` on flex containers
  lets `overflow: auto` actually engage.

### Docs

- `readme.md` (English) + `readme.zh.md` (Chinese)
- `docs/api.en.md` (API reference, English) + `docs/api.zh.md` (API 参考, 中文)
- `CHANGELOG.md` (this file)

---

## 0.0.1 — 2026-08-02

### Added

- Initial release.
- `NeonApplication` with `launch()` convenience entry point.
- Reactive DOM bridge: full-tree mount + incremental patch diffing.
- Component library: `Button`, `Checkbox`, `Input`, `Heading`, `Text`,
  `Tabs`, `Flex`, `VStack`, `HStack`, `Spacer`, `Separator`, `GlassPanel`.
- 3 theme presets: `DARK`, `LIGHT`, `DEEP_BLUE`.
- Theme CSS custom property injection via `sync_theme()`.
- `Page` container with width-constrained centered column.
- `Config` / `WindowConfig` / `WebViewConfig` Pydantic models.
- Event delegation: 14 DOM event types forwarded via LumiView bridge.
- `Color`, `Styles`, `DomEvent`, `NodeDescriptor` primitives.
- 53 HTML element classes (`Div`, `Span`, `H1`–`H6`, `Input`, `Form`, …).
- `test_gallery.py` component showcase.
