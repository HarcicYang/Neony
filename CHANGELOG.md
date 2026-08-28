# Changelog

## Unreleased

### Added

- **`GridView`** — a responsive CSS-grid container for card walls and
  catalogs. Columns are defined with the typed `Columns` model
  (`Columns.fixed(n)`, `Columns.responsive(min_width, fit=)`,
  `Columns(tracks=...)`) — no raw CSS strings. `uniform=True` (default)
  keeps every tile in a row as tall as its tallest neighbour;
  `uniform=False` keeps natural heights, top-aligned. Long labels wrap
  inside their tile instead of overflowing. The gallery's icon catalog
  now uses it; both sizing modes are demoed on the Layout tab.

### Dependencies

- Upgraded `lumiview` from `0.1.0.dev5` to `0.1.0` (stable). The only
  breaking upstream change — `run_async` no longer takes a `pool=`
  parameter — is absorbed internally; behavior is unchanged.
- Protocol requests and `media_read` no longer touch LumiView private
  internals (`App._async_loop` / `App._threadpool`): scheduling now goes
  through the public `lumiview.task.task()` / `run_async()` APIs. As a
  side effect, a protocol request arriving while the app is shutting
  down now answers `500` immediately instead of potentially hanging.
- On macOS, the default application menu now includes a Close Window
  item, so <kbd>Cmd+W</kbd> closes the focused window (routed through
  the normal `CloseRequested` chain — close-to-tray apps keep their
  behavior). To be confirmed on macOS hardware.
- Upgraded `lumiview` from `0.1.0` to `0.1.1`. The release adds a
  `sync_visibility` window option — the webview is hidden alongside a
  minimized / hidden window so the platform can throttle it — and is
  now exposed as **`WindowConfig.sync_visibility`** (default `True`;
  set `False` if a tray-style app must keep rendering while hidden).
  No breaking upstream changes.
- Protocol requests and `media_read` no longer touch LumiView private
  internals (`App._async_loop` / `App._threadpool`): scheduling now goes
  through the public `lumiview.task.task()` / `run_async()` APIs. As a
  side effect, a protocol request arriving while the app is shutting
  down now answers `500` immediately instead of potentially hanging.
- On macOS, the default application menu now includes a Close Window
  item, so <kbd>Cmd+W</kbd> closes the focused window (routed through
  the normal `CloseRequested` chain — close-to-tray apps keep their
  behavior). To be confirmed on macOS hardware.

## 0.3.0 — 2026-08-25

### Added

- **Managed `Video` / `Audio` components** in
  `neony.application.elements`. Native controls are never shown;
  playback runs through a built-in transport row (play/pause, scrubbing
  position slider, time labels, mute, volume) built from regular Neony
  widgets and updated reactively. Commands: `play()`, `pause()`,
  `seek()`, `set_muted()`, `toggle_muted()`, `set_volume()`. Events:
  `on_play`, `on_pause`, `on_ended`, `on_timeupdate`, `on_error`.
  Reactive reads: `playing`, `position`, `duration`, `muted`, `volume`.
  Use `bind_src(signal)` for declarative sources. `neony://` local
  sources load automatically; `https://` and `data:` URLs use the native
  path; switching between the two at runtime is handled.
- **HEVC transcode fallback** — when a managed media player loads a
  local MP4 whose codec (`hvc1` / `hev1`) the webview cannot decode, the
  runtime transparently converts it to H.264 via `imageio-ffmpeg` and
  caches the result next to the original.
- **Custom protocol handlers** — serve Python-generated content to the
  page through `neony://<key>/…` URLs. Register a handler with
  `@protocol("key")`, pass `protocols=` to `launch()` /
  `NeonApplication()`, and build URLs with `local_url(path)` /
  `protocol_url(key, value)`.
- **Built-in `local_files` protocol** — serves any absolute filesystem
  path over `neony://local/…` with HTTP Range support, HEAD, MIME
  guessing, and cache headers, so local media and subresources work
  even where `file://` is blocked.
- **Redesigned theme system** — eight built-in presets across four
  visual families: Nightglow, Planet Plaza, Ember Zone, Cyberangel
  (dark/light each). `Theme` is immutable and self-registers; custom
  themes supply the full token set and join the same registry.
  `DARK`, `LIGHT`, and `DEEP_BLUE` remain aliases.
- **Motion tokens** — `Motion` provides `--motion-*` variables plus
  `transition()`, `popup_animation()`, and `submenu_animation()`
  helpers for consistent component motion.
- **Cascading menus** — `MenuBranch(label, items)` and
  `CascadingDropdown` add recursively nested option branches to `Menu`
  and `Dropdown`, with full keyboard navigation and click-away
  dismissal.
- **`RichText`** — a managed inline editor with text and image
  segments, caret / selection / insertion APIs, IME-safe editing,
  ordered content export, and image/file paste.
- **Scroll containers** — `ScrollArea` (programmatic scrolling) and
  `StickToBottom` (chat-stream auto-scroll with user-scroll pause).
- **Built-in semantic icons** — a public `icons` namespace with an
  embedded Material Symbols font, so glyph icons work offline and
  consistently across platforms.

### Performance

- Element construction is significantly faster for large bare DOM
  trees (`Div()`, `Span()`, …).
- `List` now virtualizes collections past 200 rows: only the visible
  window plus overscan is rendered, and selection / keyboard
  navigation materializes the target row on demand.
- Large renders and first mounts are delivered in bounded chunks.
- Signal-heavy updates coalesce into one render per window per turn,
  and style-only hover/focus/press changes skip the full render path.

### Breaking changes

- Raw `<audio>` / `<video>` DOM elements no longer load `neony://`
  sources automatically. Use the managed `Video` / `Audio` components
  for local media.

### Changed

- `Page` content is now a `VStack` by default, so scroll components
  behave consistently inside pages; `Page.add(*children)` remains
  chainable.
- Built-in theme constants use family/mode names
  (`NIGHTGLOW_DARK`, `PLANET_PLAZA_LIGHT`, …); the historical
  `DARK` / `LIGHT` / `DEEP_BLUE` names remain importable aliases.

### Fixed

- Switching a managed media source starts from a clean state, large
  local media loads without stalling the app, and the transport shows a
  loading strip while a source is being prepared.
- Overlay click-away now closes reliably, including nested and
  cascading menus.
- Context menus and `MessageBubble` quick actions are exclusive per
  page/window; opening one closes the previous tree without affecting
  other popup components.
- Dialog close plays its exit animation before hiding, and reopening
  cancels an in-flight close.
- `RichText` pasted images carry real clipboard bytes and stay within
  the display/container size caps.

### Docs

- API reference split into `docs/api/*` chapters (core, components,
  reactive, dom-css, layout-chrome, platform-i18n) with an index.
- Bilingual getting-started and platform installation guides updated
  for components, protocols, theming, and media APIs.

---

## 0.2.4.post1 — 2026-08-24

### Fixed

- `MessageBubble.container` assignments now keep the bubble correctly
  wired, so media, clipboard, and scroll actions inside the
  bubble keep working.
- Initial media loading is deferred until nodes are attached to the
  live page, avoiding a video stuck in an unstarted state.
- Local MP4 files whose codec the host cannot decode are detected and
  transparently transcoded to H.264, with the result cached next to the
  original.

---

## 0.2.0 — 2026-08-13

### Added

- **Reactivity core** — `Signal` / `Computed` / `Effect` / `batch()` /
  `untrack()` / `SharedSignal` with automatic dependency tracking;
  declarative `bind_text()`, `bind_style()`, `bind_attr()`,
  `bind_visible()` bindings; cross-window updates.
- **Pointer-driven in-app drag reorder** — self-drawn drag ghost,
  animated landing slot, row/column/grid reordering, cross-board drags
  between multiple `Reorder` boards, and any component or plain string
  as a card without a wrapper.
- **System-native file dialogs** — `app.open_file()` / `open_files()` /
  `save_file()` / `select_folder()` use the platform picker (zenity on
  Linux, `osascript` on macOS, PowerShell on Windows, tkinter fallback)
  and keep the app responsive while open. Cancel returns `None` /
  `[]`.
- **Framework i18n** — chainable `tr` proxy with typed catalogs,
  reactive text that updates live on language switch, and a fully
  translated gallery.
- **Component expansion** — form controls (Radio/RadioGroup, Switch,
  Select, ComboBox, Slider, Progress), overlays (Dialog, Tooltip,
  Dropdown, Menu, NoticeBubble), content (Card, Avatar, Badge, Image),
  data views (DataTable, List), navigation (Sidebar + SidebarGroup,
  Tree, Tabs), chat (Toast, MessageBubble), PromptDialog, and a unified
  Icon.
- **System tray** — `Tray` with native menu and close-to-tray behavior
  (Linux needs `libayatana-appindicator`).
- **Scroll UX** — custom draggable scroll indicator with edge fade and
  smooth horizontal wheel scrolling where the webview lacks native
  support.
- **Events** — delegated scroll and `pointermove` events, window-level
  `on_keydown` / `on_keyup`, in-app shortcuts via
  `Page.on_shortcut()`, clipboard API plus paste/copy/cut events,
  native file drop, opt-in event bubbling, and rich `DomEvent`
  payloads (modifiers, coordinates, wheel units).
- **Window features** — transparent-window Wayland blur, runtime
  `set_icon()`, `show()` / `hide()` / `focus()` / `set_bounds()`,
  lifecycle hooks, and navigation/download policy defaults.
- **Typed styles and animation** — `Styles`, `Color`, `Border`,
  `Filter`, `Transform`, `BoxShadow`, `Transition`, `KeyFrame`,
  `Props`, and `Animation` models plus length helpers.
- **Typed app state** — `NeonApplication` accepts a dataclass, pydantic
  model, or plain class via `state=`.

### Changed

- Selection APIs unified: `Sidebar.selected` /
  `Tabs.selected_panel` bind objects/panels; `selected_key` /
  `selected_title` select by string. Old `Sidebar.active_key`, `Tabs.active`,
  and `Tabs.active_key` are deprecated aliases.
- Theme API consolidated: `Theme.set_mode()` / `toggle()` removed in
  favor of `app.set_theme(theme)` / `theme.next()`; presets are
  immutable.
- Unknown selection keys now raise `ValueError` instead of silently
  doing nothing; `Pane.key` defaults to a random id for label
  uniqueness.
- `edge_fade` now controls the whole scroll indicator; `Progress` puts
  the human-readable label first in its constructor.

### Fixed

- Reactive primitives, cross-window bindings, style mutations, and
  event bubbling edge cases.
- `Tabs.active_key` now returns the tab title instead of an element id.
- Raw event handlers no longer crash the synchronous path; keyboard
  events reach `Page` handlers even without a focused element.
- Dropped-file paths and clipboard reads work on WebKitGTK where
  browser APIs differ.
- Tree height and scrolling button behavior under dynamic panel swaps.
- Wayland blur fails gracefully on unsupported compositors.

---

## 0.1.0 — 2026-08-03

### Added

- **Multi-window** — `run(*pages)` opens one window per page, sharing
  one event loop and app state; `launch([...])` accepts a list.
- **Window control API** — `set_title()`, `set_size()`, `minimize()`,
  `toggle_maximize()`, `is_maximized()`, `set_fullscreen()`,
  `start_dragging()`, `close()`, blur/acrylic/mica effects,
  `eval_js()`.
- **`TitleBar`** — custom frameless window chrome with drag,
  minimize/maximize/close, and close overrides.
- **`Sidebar` + `SidebarItem`** — vertical navigation rail with accent
  border, active state, and programmatic switching.
- **Framed pages** — `Page(radius=...)` clips to a rounded window frame;
  `GlassPanel` content panels; `Page(fill=True)` works under tiling
  window managers.
- **Theme tokens** — per-theme glass backgrounds, new secondary text
  values, `surface_panel_glass_bg`, and an updated `sync_theme()`.

### Fixed

- `TitleBar` controls respond to clicks only and restore hover state
  correctly.
- Transparent windows follow theme switches correctly.
- Flex containers scroll correctly when content overflows; constructor
  children and component event routing edge cases are fixed.

---

## 0.0.1 — 2026-08-02

### Added

- Initial release.
- `NeonApplication` with `launch()` convenience entry point and a
  reactive DOM layer.
- Component library: `Button`, `Checkbox`, `Input`, `Heading`, `Text`,
  `Tabs`, `Flex`, `VStack`, `HStack`, `Spacer`, `Separator`,
  `GlassPanel`.
- Three theme presets: `DARK`, `LIGHT`, `DEEP_BLUE`.
- `Page` container, `Config` / `WindowConfig` / `WebViewConfig`
  models, `Color`, `Styles`, `DomEvent`, and 53 HTML element classes.
