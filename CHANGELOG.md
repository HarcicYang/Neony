# Changelog

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
