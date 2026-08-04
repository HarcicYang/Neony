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
- **`Styles.user_select`** — text-selection control (`none` / `auto` /
  `text` / `contain` / `all`); one Python field emits `user-select`
  plus the `-webkit-` and `-moz-` prefixed variants (same treatment as
  `backdrop-filter`, across Python serialization and the JS engine).
- **Opt-in event bubbling** — components mark a root element with
  `_bubble_events` so events on handler-less children (e.g. `SidebarItem`'s
  icon/label spans) route to it. Layout containers keep strict
  per-element routing unless they opt in.
- **Style direct-patch** — pure style/attr changes (hover, focus, press
  states) bypass tree serialization and the diff engine: mutations are
  classified per element (`styles`/`args` → patchable in place; anything
  else → structural), and the render emits `update_styles`/`update_attrs`
  straight from the snapshot cache, updating it in place. Any structural
  change falls through to the full serialization + diff path; rev
  continuity is preserved.
- **Typed app state** — `NeonApplication` is now generic: `state=`
  accepts any object (dataclass, pydantic model, plain class) for typed
  attribute access and IDE completion, while the default stays a bare
  `SimpleNamespace`. `launch(..., state=...)` forwards it. All windows
  share the same instance, exactly as before.
- **Lifecycle hooks** — `app.close_handler` runs once after all windows
  close (before the event loop stops), symmetric with `ready_handler`.
  `Page.on_close(fn)` registers per-window close callbacks (sync or
  async, multiple stack, exceptions never block the close); the
  framework wires them to the native `CloseRequested` event internally.
- **Element reuse defense** — mounting the same `DOMElement` into two
  containers (or calling `Component.build()` twice) now raises a clear
  `RuntimeError` instead of silently corrupting parent pointers, dirty
  propagation, and event bubbling.
- **Window focus tracking** — `Page.on_focus(fn)` / `Page.on_blur(fn)`
  (sync or async, chainable, multiple handlers stack) fire on the native
  `Focused` / `Unfocused` window events — know which window is active in
  multi-window apps.
- **Navigation & download policies** — safe defaults are installed on
  every window (all navigation blocked, new-window requests denied,
  downloads cancelled) so an in-page link can never navigate the UI
  away. `Page.on_navigation(fn)` / `on_new_window(fn)` /
  `on_download_started(fn)` override the defaults (single decision, last
  one wins); `on_download_completed(fn)` stacks notifications.
- **`NeonApplication.set_icon()`** — runtime window icon swap (file path
  or raw RGBA data), the post-creation counterpart to `WindowConfig.icon`
  (which already worked at startup but was undocumented).
- **`TitleBar(icon=...)`** — inline icon for frameless windows, painted
  left of the title (the frameless counterpart of `WindowConfig.icon`,
  which only shows in OS window chrome).
- **Input throttling** — `input` joins the deferred render path: typing
  coalesces into one render per frame instead of one per keystroke
  (same one-frame debounce as hover/focus).
- **Rich event payload** — `DomEvent` gains modifier keys (`ctrl_key` /
  `shift_key` / `alt_key` / `meta_key`), mouse coordinates (`x` / `y`
  viewport, `offset_x` / `offset_y` element-relative), wheel deltas
  (`delta_x` / `delta_y`), and clipboard data (`clipboard_text` /
  `clipboard_html`); `wheel` joins the delegated event table.
- **Clipboard events** — `paste` / `copy` / `cut` delegated to elements;
  paste carries the clipboard's plain-text and HTML forms (the
  synchronous `getData` window), copy/cut are notifications. New
  `on_paste()` / `on_copy()` / `on_cut()` convenience methods.
- **In-app shortcuts** — `Page.on_shortcut("Ctrl+S", fn)` registers
  window-level keybindings that fire even while an input has focus
  (bubbling keydown); accepts a per-platform dict
  (`{"darwin": "Meta+S", "default": "Ctrl+S"}`). Modifiers must match
  exactly; the key matches case-insensitively.
- **Window state control** — `NeonApplication.show()` / `hide()` /
  `focus()` / `set_bounds(x, y, w, h)`; `set_bounds` positions the
  window on screen via tao's `set_outer_position` (lumiview's own
  `set_bounds` only moves the webview child) and resizes via `set_size`.
- **Clipboard API** — `NeonApplication.clipboard_write(text)` /
  `clipboard_read()` wrap `navigator.clipboard` (read requires a user
  gesture, like the browser).
- **Local resource URLs** — `file_url(path)` → `file://` URL (Windows
  paths, spaces, non-ASCII all handled) and `data_url(path)` → base64
  `data:` URL with MIME guess, exported from `neony.application` for
  local images in `GlassPanel(background=...)`, `TitleBar(icon=...)`, ...
- **File drag-and-drop** — `drop` / `dragover` / `dragleave` join the
  delegated events; `DomEvent.drop_files` carries one dict per dropped
  file (`name`, `path`, `size`, `type` — `File.path` is exposed by
  WebView2 / WebKitGTK, empty on WKWebView). New `on_drop()` /
  `on_dragover()` / `on_dragleave()` on elements and components. The
  engine `preventDefault()`s dragover/drop, so dropping a file never
  navigates the webview to it; `dragover`/`dragleave` ride the deferred
  render path (they fire continuously while dragging).
- **Event API completion** — the missing `on_*` convenience methods on
  elements and components: `on_mousedown()`, `on_mouseup()`,
  `on_contextmenu()`, `on_wheel()` (plus `on_paste()` / `on_copy()` /
  `on_cut()` / `on_drop()` / `on_dragover()` / `on_dragleave()` on
  components) — every delegated event now has a fluent method.
- **`GlassPanel` per-corner radii** — `border_top_left_radius` &
  friends on `GlassPanel` override parts of `radius`, for joining
  rounded chrome pieces.

### Changed

- **Native file-drop path channel** — every window now installs a native
  `drag_drop_handler` (tao's OS-level handler, which receives real file
  paths).  It is a pure observer — always returns `False`, because wry
  documents that `True` *blocks the OS' default behavior* (on WebKitGTK
  that is delivering the drop to the web process, so `True` kills the
  JS `drop` event — verified in the real environment).  Captured paths
  are matched back into `drop_files` by base name in the bridge,
  fixing empty paths on WebKitGTK ≥ 2.52 (where `File.path` was
  removed) without touching the WebView2 path.
- **Bindings accept `Computed`** — `bind_text()` / `bind_style()` /
  `bind_attr()` / `bind_visible()` take `Signal | Computed` on both
  elements and components, so derived values bind directly.
- **Component event wiring** — `Component.on()` lazily wires DOM event
  types its internals don't bind (keydown, wheel, paste, drop, ...) to
  the root element, so `component.on_keydown(...)` actually fires;
  `_bound_events` per component prevents double-dispatch of natively
  wired types.
- **Clipboard API internals** — `clipboard_write()` uses the synchronous
  `execCommand('copy')` path (hidden textarea) with a fire-and-forget
  `navigator.clipboard.writeText()` attempt, and verifies the result;
  `clipboard_read()` runs the async read in-page into a global and
  polls it from Python, because the webview bridge may not await JS
  promises.  Both raise `RuntimeError` with the backend's reason when
  rejected (e.g. WebKitGTK denying clipboard-read permission).
- **`set_bounds` resilience** — a `set_outer_position` failure (Wayland
  forbids client-side positioning) is logged but never blocks the
  resize half of the call.
- **Window-level key events** — `Page.on_keydown(fn)` / `Page.on_keyup(fn)`
  register window-wide listeners (sync or async, called with the
  `DomEvent`) that fire wherever keys land — typed in any input or
  pressed on the bare page — thanks to the bubbling fix below.
- **Clipboard read OS fallback** — on Linux, when the in-page read is
  rejected (WebKitGTK has no `navigator.clipboard.readText`),
  `clipboard_read()` falls back to the platform clipboard tool
  (`wl-paste` on Wayland, `xclip` on X11, 2s timeout), so reads work
  from a click handler (the window is focused, which Wayland requires).

### Fixed

- **Keys dropped when no element was focused** — the JS delegate traced
  every event to its nearest `data-neony-key` ancestor and discarded the
  event when none existed.  With focus on the page body (the normal
  state after clicking anywhere that isn't an input), every `keydown` /
  `keyup` was dropped, so window-level listeners (page key handlers,
  shortcuts) only ever fired while an input was focused — or never, for
  shortcuts pressed on the bare page.  Keyboard events now fall back to
  the engine root, so body-focused keys reach `Page.on_keydown`,
  `Page.on_keyup` and `Page.on_shortcut`.
- **In-place styles mutations never rendered** — `el.styles.foo = X` (a
  field write on the existing `Styles` model) bypassed the dirty
  tracker, which only saw whole-`styles` reassignment; the snapshot
  cache served the stale style forever.  The gallery's status dots
  (`set_dot`) used exactly this pattern, so every indicator light was
  dead.  `Styles` now carries an owner hook: any field mutation marks
  the element (and ancestors) dirty, on the initial instance and after
  `model_copy` reassignment alike.
- **Events never bubbled past an element that handled them** — `_on_event`
  returned after dispatching to the target, so window-level listeners
  (page shortcuts, key handlers) never saw keys typed into an input
  with handlers of its own — contradicting the documented "shortcuts
  fire even while an input has focus".  Events now always bubble to the
  nearest `_bubble_events` ancestor with a matching handler, after the
  target's own handlers.
- **Sync event handlers crashed every event** — `_make_wrapper` awaited
  `fn(evt)` directly; a plain (sync) handler returned `None` →
  `TypeError`, and because the crash happened *before* the auto-render
  call, the UI never refreshed (the gallery/probe appeared dead: no
  console output, drop-zone text stuck, modifier lights frozen).  The
  wrapper now awaits only coroutines, exactly like `_run_handler`.
- **`eval_js` results are JSON-encoded** — wryview passes the WebKitGTK
  result through JSON (a JS string arrives quoted, `'"pong"'`, with
  ``-style escapes), so `clipboard_read`'s `partition("\x01")`
  never matched and every read failed as "unknown error" — even
  `navigator.clipboard.readText`'s real rejection reason was invisible.
  New `_js_result_value()` decodes quoted results; both clipboard
  methods parse through it.  The probe confirmed
  `navigator.clipboard.readText` is absent on WebKitGTK 2.52, so reads
  keep failing *by design* there — with the true reason now surfaced
  ("clipboard API unavailable") plus the paste-event workaround.
- **File drops natively taken over on WebKitGTK** — installing wry's
  `drag_drop_handler` (even as an observer) makes the webview deliver
  the JS `drop` event with an *empty* `dataTransfer.files` (verified:
  `drop_files` empty while the native handler received the real path).
  The handler now returns `True` on `Drop` (blocking the useless empty
  drop — wry's documented semantics) and re-dispatches the file list
  from Python: `name`/`path`/`size`/`type` built from the real paths
  (`_file_info`), the element under the pointer resolved via
  `elementFromPoint` hit-testing, and the drop delivered through the
  bridge — so `DomEvent.drop_files` finally carries real paths on
  WebKitGTK ≥ 2.52.  `dragover`/`dragleave` still reach the page.
- **Dropped-file paths empty on WebKitGTK ≥ 2.52** — `File.path` was
  removed there (and never existed on WKWebView); the engine now falls
  back to parsing the drag's `text/uri-list`, matched to each file by
  base name (still the fallback behind the native takeover).
- **Wheel payload lacked the delta units** — `delta_mode` (0 = pixels,
  1 = lines, 2 = pages) is now forwarded.  On WebKitGTK 2.52 mouse
  wheels deliver one event per notch in pixel mode (mode=0) with a
  constant delta (±94.5 at the probe's scale) — consumers must convert
  line/page modes by 16/256, not assume line deltas.

- **Real-environment verification (probe v3/v4, Wayland + hyprland +
  WebKitGTK 2.52.5)** — native drop takeover delivers real paths end to
  end (incl. non-ASCII filenames); keyboard events reach the page *and*
  the bridge (JS-side counter == Python log lines) and page-root
  shortcuts fire (`Ctrl+K`); clipboard reads surface the real "clipboard
  API unavailable" reason; hide/show round-trips with the page alive.
  `set_bounds`/`set_size` resize requests are a no-op while the window
  is tiled (GTK treats tiled windows as fixed-size; Wayland resizes are
  compositor-best-effort) and position is impossible on Wayland by
  protocol; window focus/blur page hooks were not observed firing on
  this stack (tao GTK focus emission — follow-up).

- **Render path** — `Neony.render()` serializes through a per-key snapshot
  cache; only dirty subtrees are re-walked. `demo_reactive.py` rewritten
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
- **Mouse events dead after the rich payload landed** — browser
  coordinates arrive as JSON integers (`clientX: 123`), but lumiview
  converts command payloads with strict type matching (no unions), so a
  `float` annotation rejected every `neony.event` call carrying
  coordinates — clicks went silently missing.  The bridge's numeric
  fields are now `Any` (validated/coerced by `DomEvent`'s pydantic
  fields), with a regression test exercising the real binding path.

### Docs

- `readme.md` / `readme.zh.md` — new features, theming section; the
  roadmap was split into a standalone `ROADMAP.md` (with new Events,
  Lifecycle and Platform integration categories).
- `docs/api.en.md` / `docs/api.zh.md` — new Reactivity chapter (Signal,
  Computed, Effect, batch, untrack, SharedSignal, bindings, dirty-subtree
  tracking) and a Lifecycle section (close_handler, page.on_close); the
  standalone bilingual `docs.md` was split into the two per-language
  files and removed.

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
