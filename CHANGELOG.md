# Changelog

## Unreleased

### Added

- **Pointer-driven in-app drags** — elements with `drag_payload` no
  longer use HTML5 drag-and-drop: WebKitGTK's native drag image
  positions randomly on Wayland (sometimes grab-relative, sometimes
  absolute), so the user aims at a wrongly-placed image and the drop
  (hit-tested at the REAL pointer) reorders only sometimes.  A mousedown
  arms the drag; past a 4px threshold the engine dispatches a synthetic
  dragstart (sync setData, exactly like the native flow), a self-drawn
  ghost tracks the pointer locally (one rAF per frame, zero IPC), and
  dragover/drop/dragend are hit-tested with `elementFromPoint` — the
  ghost and the drop target are ALWAYS consistent.  Synthetic events
  flow through the same pipeline, so the Python API is unchanged.  The
  element's `draggable` attribute is stripped on mousedown so the
  browser never starts its own misbehaving drag.
- **Dragover throttle** — `dragover` fires on every pointer motion
  during a drag; each forward was a full Python round-trip and the
  events queued up BEHIND the drop, delaying it (drag felt broken even
  though the events worked).  Forwarding is now throttled to ~8/s per
  key — enough for drop-zone highlighting, and the drop itself still
  carries everything a handler needs (`drag_payload`, coordinates).  The
  map resets on drop/dragend.
- **Native file dialogs** — `app.open_file()` / `open_files()` /
  `save_file()` / `select_folder()` show a self-drawn, dark-themed file
  picker in a one-shot tkinter subprocess. The request dict rides the
  `Process` args (pickled) and the result returns on a one-way
  `multiprocessing` pipe as a typed `("ok", result)` / `("error", msg)`
  tuple — no stdout/JSON parsing. Cancelling returns `None` (`[]` for
  multi-select); a dialog that can't be shown also returns `None`. The
  parent awaits with `asyncio.to_thread`, so the event loop stays
  responsive. Linux/macOS use `fork`, Windows `spawn`; the subprocess
  entry lives in a stdlib-only module.
- **In-app drag reorder primitives** — the full drag lifecycle is
  delegated (`dragstart` / `dragenter` / `dragover` / `dragleave` /
  `drop` / `dragend`); a new `DOMElement.drag_payload` field makes an
  element draggable and declares the payload the engine hands to
  `dataTransfer.setData` on dragstart (synchronously). `drop` reads it
  back via `DomEvent.drag_payload`; `on_dragstart` / `on_dragend` /
  `on_dragenter` on elements and components. Reordering a container is
  a plain `container[:] = new_order` — the diff engine emits a
  `ReorderPatch` on its own.
- **Drag position-shift preview** — during an in-app drag the dragged
  card becomes its own ghost (leaves the flow; a card-sized dashed
  "landing slot" travels to the insertion point as the cursor crosses
  cards, showing exactly where the card will land; all Neony-injected
  inline styles preserved).  No element is ever resized: siblings only
  shift position, FLIP-animated.  On drop the list settles into its
  final order with a matching FLIP (the ghost glides from the cursor
  into the slot), and the drop targets the committed insertion so the
  preview and the result always agree.  Purely local in the engine (no
  IPC); everything clears on drop/cancel.
- **Bidirectional drag reorder** — the engine detects the container's
  `flex-direction` and reorders along either axis: the cursor half is
  judged by `offset_y` for a `column` (top/bottom) and `offset_x` for a
  `row` (left/right), the landing slot is sized along the main axis, and
  the drop encodes the side on the matching field.
- **`Reorder` component** — the drag-reorder primitive wrapped as a
  proper component: a flex board of draggable cards that owns the reorder
  internally (`on_drop` reports the new order via `event.value`).  A
  `direction="row"` board with `wrap=True` forms a grid, so a card can be
  dragged both horizontally (within a row) and vertically (into another
  row).
- **Cross-board drag reorder** — a card dragged onto a card of ANOTHER
  `Reorder` re-homes the dashed landing slot into that board (the engine
  re-homes the placeholder across containers, gated on `data-neony-drag`,
  and sizes it to the target board's cards), and the drop moves the card
  between boards (removed from the source's `order`, inserted into the
  target's at the previewed side; the drop settles in the source board
  and the Python handler moves the model + re-renders).  Card keys must
  be globally unique across boards that exchange cards.
- **`MovePatch` — cross-parent moves re-parent the SAME element** —
  the diff engine now emits `op: "move"` (key → new parent + index)
  when a key exists under different parents in both trees, instead of
  remove+create: a card dragged between Reorder boards keeps its DOM
  node (no flash, no blank slot), the settle glide lands it in the
  target board's slot, and the follow-up move is a no-op.
- **Any content as a card** — `Reorder` / `ReorderItem` accept plain or
  reactive strings, whole components (they mount inside the card) or raw
  DOM elements; the key resolves from the item, a keyed DOM element's own
  key, or a plain-string label.  `max_width` pins the board's width so a
  wrapping grid wraps predictably; boards auto-key their root so the
  engine's "cursor inside this container" check works without user keys.
  The gallery demo now shows a `max_width`-pinned 4×2 grid plus a second
  tray board that exchanges cards with it (cross-board).
- **Generic `Reorder`** — `Reorder[T]` and `ReorderItem[T]` are typed by
  the card content, so any content type (a `Component`, a `DOMElement`,
  reactive text) can stand exactly where `ReorderItem` used to; `items`
  yields `ReorderItem[T]` for typed access.
- **Bare content in `Reorder`** — `Reorder(Card(...), Card(...))` works:
  cards no longer need a `ReorderItem` wrapper or an explicit key.  A
  plain-string label is the key, a keyed DOM element keeps its own key,
  and everything else (components, unkeyed DOM) gets an auto-generated
  `reorder-card-N` key, so any component can be dropped into a board.
  The gallery adds a third board of three bare `Card`s.
- **Delegated `scroll` events** — `on_scroll()` on elements and
  components; `DomEvent.scroll_top` / `scroll_left` carry the scrolled
  element's position (read from the actual scroller, dispatched to the
  nearest keyed ancestor). High-frequency — scroll rides the deferred
  render path, coalescing a scroll burst into one render per frame; a
  document-level scroll routes through the engine root.
- **Sidebar owns its content panes** — `Sidebar` accepts `Pane`
  models (or `(label, panel)` tuples) and swaps the visible pane
  internally, exactly like `Tabs`; pane roots are cached and reused
  (build-once absorbed). Per-pane optional `shortcut` combos are
  collected via `Sidebar.shortcuts()` for `Page.on_shortcut` wiring.
- **`SidebarGroup`** — titled sidebar sections; consecutive `Pane`s
  sharing a `section` auto-group under one small uppercase label.
  `SidebarGroup.add` works after attachment (items wired automatically).
- **Object-level selection** — `Sidebar.selected` binds the registered
  `Pane`/`SidebarItem` object; `Tabs.selected_panel` binds the panel;
  `selected_key`/`selected_title` select by string. `RadioGroup` gains
  a `selected_key` alias of `value`.
- **`bind_selected()`** — two-way `Signal` binding on selection
  components (Sidebar, Tabs), mirroring `bind_value`.
- **Constructor children** — `Tabs(*panes)` and `Page.add(*children)`.
- **`Styles` fields** — `text_transform`, `letter_spacing` (used by the
  `SidebarGroup` label).
- **Selection and value bindings** — `Switch` and `Dropdown` now support
  two-way `bind_value`; `ComboBox` writes through both `input` and `change`
  channels; `Tabs` exposes `selected_key`.
- **Theme mode metadata** — `Theme.modes` and `Theme.mode_label()` expose
  the toggle order without duplicating mode labels in applications.
- **`Accordion` / `Collapsible`** — expandable groups in a single scroll
  column; fluent `.section()` chaining, multiple simultaneous groups,
  `expanded_keys`, `on_change`.
- **`Tree` navigation** — accordion-styled tree rail with `TreeNode`
  branches/leaves, `.panel()` content mounting, `expanded_branches`,
  `active_key`, keyboard navigation, and per-leaf `shortcut` combos.
- **Unified icon type** — one `Icon` (image or glyph) across Tree,
  Sidebar, Tabs and Menu.
- **Form controls** — `Radio` / `RadioGroup`, `Switch`, `Select`,
  `ComboBox`, `Slider` and `Progress`, each with two-way `bind_value`
  and theme-matched styling.
- **Overlays** — `Dialog` (modal, `open()`/`close()`, outside-click and
  Esc to close), `Tooltip`, `Dropdown` and `Menu` (popup panel with
  outside-click dismissal and keyboard navigation).
- **Content components** — `Card`, `Avatar`, `Badge` and `Image`.
- **`PromptDialog`** — a modal single-line text input with
  confirm/cancel; `PromptDialog.prompt(...)` returns the entered value.
- **System tray** — `Tray` with a native menu and close-to-tray
  behaviour (via LumiView .dev4).
- **Typed animation models** — `Transition` (property/duration/timing/
  delay), `KeyFrame` (chainable builder), `Props` and `Animation`;
  `@keyframes` injection via `app.register_keyframe()`, with built-in
  `neony-rise-in`, `neony-fade-in` and `neony-drop-in` (the downward
  slide-in entrance used by Dropdown/Select/ComboBox popups and
  Accordion/Treeview expands).
- **`pointermove` event** — `DomEvent.movement_x`/`movement_y` deltas
  and `pointer_type`; new `on_pointermove()` on elements and components.
- **`Styles.accent_color`** — native accent colour field plus
  `progress`/`datalist`/`option` elements and the `input` `list` attr.
- **Wayland blur for transparent windows** — Linux compositors with
  `ext-background-effect-v1` blur the desktop behind transparent windows
  (Hyprland detected and skipped; failures logged, never fatal).
- **Clipboard backend** — `clipboard_read()`/`write()` use the platform
  clipboard implementation (pyclip) instead of in-page JS.
- **Scroll indicator** — native scrollbars are hidden (WebKitGTK hover
  growth is unsuppressable), so every scroll surface gets a JS-built
  indicator instead: a draggable custom thumb + dynamic edge fade,
  marker-driven via `data-neony-scroll` and auto-derived from `overflow`
  at serialization (`DOMElement.scroll_indicator`). The overlay is a
  JS-created sibling of the scroller — invisible to the Python patch
  engine, zero IPC during drag. Thumb presets: `silent` (hidden until
  hover/scroll), `lighten` (faint thin at rest), `normal` (faint thin →
  solid wide on hover, default), `active` (solid wide always). The edge
  fade is dynamic — it collapses at whichever end is flush with the
  content — and is skipped entirely on backdrop-filtered surfaces
  (glass sidebar, popups) which get the thumb only.
- **Smooth horizontal wheel scroll** — `data-neony-wheel-x` zones
  translate a plain vertical wheel into eased sideways scrolling
  (rAF loop), since WebKitGTK does not do this natively.
- **Tabs demo in the gallery** — basic switching with `bind_selected`
  + status readout, and a 10-tab strip exercising horizontal overflow
  with the edge fade.
- **Typed CSS value models** — `Border`, `Filter`, `Transform`
  (with `translate`/`rotate`/`scale` factories) and `BoxShadow` +
  `Shadow`, plus length helpers `px()` / `pct()` / `calc()`; raw
  strings still accepted as escape hatches. `dom/css` is now a
  subpackage (`_values` / `_animation` / `_styles`) with a stable
  re-export surface.
- **Immutable theme presets** — `Theme` is frozen and self-registers
  by mode; lookup via `Theme.get(name)`, toggle order via
  `Theme.modes()`, rotation via `theme.next()`, and `app.set_theme()`
  swaps the active preset. New `on_accent` token (text/icon colour on
  accent surfaces, e.g. accent buttons).

### Changed

- **Progress constructor order** — `Progress(label, *, value=..., max=...)`
  puts the human-readable label first; existing keyword calls are unchanged.
- **Reactive examples use two complementary paths** — simple state echoes use
  `Signal` and `bind_*`, while event handlers remain the supported choice for
  asynchronous work, event context, branching, and multiple side effects.

- **`Tabs.active_key` now returns the tab title** — it previously
  returned an opaque element id. `active`/`active_key` are deprecated
  aliases of `selected_panel`/`selected_title`.
- **Unknown selection keys raise** — `Sidebar.selected_key` /
  `Tabs.selected_title` raise `ValueError` for unknown keys (previously
  a silent no-op); `Tabs.selected_panel` raises for unregistered panels.
- **`Pane.key` defaults to a random id** — labels never collide (even
  when duplicated or non-ASCII); pass an explicit `key` for a readable
  identifier. `SidebarItem.key` keeps its lowercased-label default.
- **`Tabs.on_change` carries the tab title** — `event.value` was
  previously `None`; shortcuts dispatch with `source == "user"`.
- **`edge_fade` now toggles the scroll indicator** — the static Python
  edge-fade masks on Tabs/Sidebar/Treeview are gone; the JS engine owns
  the (dynamic) fade. `edge_fade=False` suppresses the whole indicator.
  Tabs uses the `silent` preset (a compact strip has no room for a
  resting gutter); content panes (`_PanelHost`) are suppressed.
- **Component consistency audit** — demos and handlers modernized to
  idiomatic bindings and event patterns; selection APIs unified
  (`selected_*` everywhere); layout/event plumbing aligned across
  components.
- **Theme API** — `Theme.set_mode()` / `toggle()` removed in favour of
  `app.set_theme(theme)` / `theme.next()`; presets are immutable
  (mutating a `Theme` field now raises).

### Deprecated

- `Sidebar.active_key`, `Tabs.active` / `Tabs.active_key` — use the
  `selected_*` API.

### Fixed

- **`Tabs.active_key` fix** — the documented "key of active panel"
  returned a random element id; it now returns the tab title.
- **Reactive primitives** (`neony.dom`) — `Signal`, `Computed`, `Effect`,
  `batch()`, `untrack()`, `SharedSignal`. Automatic dependency tracking,
  cached derived values, coalesced re-runs. A crashing effect inside a
  flush is isolated — the rest of the batch still runs.
- **Declarative bindings** — `bind_text()`, `bind_style()`, `bind_attr()`,
  `bind_visible()`, `unbind()` on `DOMElement` and `Component`. A bound
  signal write marks the element dirty and schedules a render — no
  manual refresh calls. Bindings accept `Signal | Computed`.
- **Dirty-subtree tracking** — mutations mark the element (and every
  ancestor via parent pointers) dirty; rendering re-serializes only dirty
  elements. Unchanged subtrees reuse cached snapshots — zero patches.
  In-place `container` mutations participate through a parent-aware list
  proxy.
- **Cross-window reactivity** — a write to a `SharedSignal` updates every
  window whose tree binds it, each through its own render request.
- **Style direct-patch** — pure style/attr changes (hover, focus, press)
  bypass tree serialization and the diff engine: mutations are
  classified per element (`styles`/`args` → patchable in place), and the
  render emits `update_styles`/`update_attrs` straight from the snapshot
  cache. Structural changes fall through to the full serialization + diff
  path; rev continuity is preserved.
- **Typed app state** — `NeonApplication` is generic: `state=` accepts any
  object (dataclass, pydantic model, plain class) for typed attribute
  access; the default stays a bare `SimpleNamespace`. `launch(...,
  state=...)` forwards it.
- **Typed CSS models** — `Transition` (property / duration / timing / delay),
  `KeyFrame` (chainable builder), `Props` (animatable CSS subset), and
  `Animation` (shorthand referencing a registered keyframe). Raw strings
  still accepted as escape hatches.
- **`@keyframes` injection** — `app.register_keyframe(kf)` injects CSS
  into every window; built-in `neony-rise-in` and `neony-fade-in` are
  always available. `Tabs` and `Sidebar` use default animations.
- **`pointermove` event** — `DomEvent.movement_x` / `movement_y` carry the
  delta since the last event; `pointer_type` is `"mouse"`, `"pen"`, or
  `"touch"`. New `on_pointermove()` on elements and components.
- **Wayland blur for transparent windows** — Linux compositors supporting
  `ext-background-effect-v1` (KWin, DDE) blur the desktop behind
  transparent windows. Hyprland (detected via env vars and registry
  globals) keeps its own default blur. Failures are logged, never fatal.
- **Scrollbars hidden** — WebKitGTK's native hover-grow is
  unsuppressable, so native scrollbars are hidden entirely
  (`::-webkit-scrollbar` zero-size + Firefox `scrollbar-width:none`);
  the custom scroll indicator (above) takes their place.
- **Colour-matched glow** — focus rings (3px halo via
  `Theme.focus_glow(role)`) and hover glows tinted with each element's
  semantic colour: `Button` (per variant), `Input`, `Checkbox`, and
  `GlassPanel`.
- **`Theme.focus_glow(role)`** — returns a focus-ring box-shadow value
  referencing the role's glass token.
- **Linux app name (WM_CLASS)** — `g_set_prgname` via ctypes so the
  taskbar/dock shows the app name instead of `python3`.
- **Lifecycle hooks** — `app.close_handler` runs once after all windows
  close (before the event loop stops). `Page.on_close(fn)` registers
  per-window close callbacks (sync or async, multiple stack, exceptions
  never block the close).
- **Element reuse defense** — mounting the same `DOMElement` into two
  containers now raises a clear `RuntimeError` instead of silently
  corrupting parent pointers.
- **Window focus tracking** — `Page.on_focus(fn)` / `Page.on_blur(fn)`
  fire on the native `Focused` / `Unfocused` window events.
- **Navigation & download policies** — safe defaults on every window (all
  navigation blocked, new-window denied, downloads cancelled).
  `Page.on_navigation()` / `on_new_window()` / `on_download_started()`
  override the defaults; `on_download_completed()` stacks notifications.
- **Window-level key events** — `Page.on_keydown(fn)` / `Page.on_keyup(fn)`
  fire wherever keys land — typed in any input or pressed on the bare
  page.
- **In-app shortcuts** — `Page.on_shortcut("Ctrl+S", fn)` registers
  window-level keybindings that fire even while an input has focus;
  accepts a per-platform dict (`{"darwin": "Meta+S", "default":
  "Ctrl+S"}`).
- **`NeonApplication.set_icon()`** — runtime window icon swap (file path
  or raw RGBA data).
- **Window state control** — `show()` / `hide()` / `focus()` /
  `set_bounds(x, y, w, h)`.
- **Rich event payload** — `DomEvent` gains modifier keys, mouse
  coordinates (viewport + element-relative), wheel deltas (with
  `delta_mode`), and clipboard data.
- **Clipboard API** — `clipboard_write(text)` / `clipboard_read()` via
  pyclip backend. On Linux, `clipboard_read()` falls back to `wl-paste` /
  `xclip` when the in-page read is rejected.
- **Clipboard events** — `paste` / `copy` / `cut` delegated to elements;
  paste carries plain-text and HTML. `on_paste()` / `on_copy()` /
  `on_cut()` convenience methods.
- **File drag-and-drop** — `drop` / `dragover` / `dragleave` delegated;
  `DomEvent.drop_files` carries `name`/`path`/`size`/`type` per file.
  Native takeover on WebKitGTK (where `File.path` was removed ≥ 2.52).
- **Local resource URLs** — `file_url(path)` and `data_url(path)`, exported
  from `neony.application`.
- **`Styles.user_select`** — text-selection control with `-webkit-` and
  `-moz-` prefixed variants.
- **Opt-in event bubbling** — `bubble_events` property: events on
  handler-less children route to the nearest opted-in ancestor.
- **Event API completion** — `on_mousedown()`, `on_mouseup()`,
  `on_contextmenu()`, `on_wheel()`, `on_pointermove()`,
  `on_transitionend()`, `on_animationstart()`, `on_animationend()`, plus
  clipboard and drag-drop methods on elements and components.
- **`GlassPanel` per-corner radii** — `border_top_left_radius` & friends
  override parts of `radius`.
- **JavaScript unit tests** — vitest + jsdom covering the browser runtime;
  wired into CI via `npm ci && npm test`.
- **Python test suites** — `test_reactive.py`, `test_dirty_tracking.py`,
  `test_binding.py`, `test_cross_window.py`, `test_effect.py`,
  `test_keyframe.py`, and more.

### Changed

- **LumiView 0.1.0.dev3** — migrated to the event-based API; `Neony`
  subclasses the explicit `Plugin` lifecycle class.
- **Startup sequencing** — the fixed `asyncio.sleep(0.5)` is replaced with
  a `PageLoadFinishedEvent` wait (5s timeout); the DOM mounts the moment
  the page is ready.
- **Render coalescing** — `mouseover`/`mouseout`/`focus`/`blur`/`input`/
  `dragover`/`dragleave`/`pointermove` deferred by one frame (~16ms), so
  a burst of style-only events coalesces into a single render.
- **Component event wiring** — `Component.on()` lazily wires DOM event
  types its internals don't bind, so `component.on_keydown(...)` actually
  fires.
- **`set_bounds` resilience** — a `set_outer_position` failure (Wayland)
  is logged but never blocks the resize.
- **Internal module split** — `dom/base.py` split into `dom/css.py` (CSS
  models), `dom/events.py` (`DomEvent`), `dom/nodes.py`
  (`NodeDescriptor`); `application/app.py` helpers moved to
  `application/_helpers.py`. Public APIs unchanged.

### Fixed

- **Keys dropped when no element was focused** — keyboard events now fall
  back to the engine root, so body-focused keys reach `Page.on_keydown`,
  `Page.on_keyup` and `Page.on_shortcut`.
- **In-place style mutations never rendered** — `el.styles.foo = X`
  bypassed the dirty tracker. `Styles` now carries an owner hook: any
  field mutation marks the element dirty.
- **Events never bubbled past a handler** — events now always bubble to
  the nearest `_bubble_events` ancestor with a matching handler.
- **Sync event handlers crashed** — `_make_wrapper` now awaits only
  coroutines, matching `_run_handler`.
- **`eval_js` results are JSON-encoded** — new `_js_result_value()`
  decodes quoted results; both clipboard methods parse through it.
- **Native file-drop on WebKitGTK** — installing `drag_drop_handler`
  makes the webview deliver empty `dataTransfer.files`. The handler now
  re-dispatches the file list from Python via `elementFromPoint`
  hit-testing.
- **Dropped-file paths empty on WebKitGTK ≥ 2.52** — `File.path` was
  removed; the engine falls back to `text/uri-list` parsing.
- **Wheel payload lacked delta units** — `delta_mode` (0=pixels, 1=lines,
  2=pages) is now forwarded.
- **Mouse events dead after rich payload** — lumiview converts command
  payloads with strict type matching; numeric fields are now `Any`
  (validated by pydantic).
- **Wayland blur hardening** — pointer wrap, 3-layer Hyprland detection,
  rollback on partial application.
- **`PageLoadFinished` handler crash** — the event carries the loaded URL
  as an argument; the lambda now absorbs `*_args`.
- **`captureValue` (JS)** — forwarded `value: ""` for `<button>` instead
  of `null`; lost the pressed key for `keydown`/`keyup` on inputs.
- **Tree height jank** — switching branches or expanding panes could
  shift the rows; the tree root now pins its height via
  `flex-grow + flex-basis:0 + min-height:0` so the rail scrolls
  internally instead of growing the page.

### Docs

- `readme.md` / `readme.zh.md` — new features, theming section; the
  roadmap was split into a standalone `ROADMAP.md`.
- `docs/api.en.md` / `docs/api.zh.md` — new Reactivity chapter (Signal,
  Computed, Effect, bindings, dirty-subtree tracking) and Lifecycle
  section.

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
  height using a percentage height chain — works correctly under tiling
  window managers.
- **Per-corner border radii** on `Styles`: `border_top_left_radius`,
  `border_top_right_radius`, `border_bottom_left_radius`,
  `border_bottom_right_radius`.
- **`GlassPanel(grow=True)`**: fills the parent content region.
- **`surface_panel_glass_bg` token**: denser glass (0.85 alpha) for
  content panels, distinct from chrome glass (0.60 alpha).
- **`box-sizing: border-box` global reset**: prevents `width:100% +
  padding` overflow.

### Changed

- **Glass tokens per-theme**: dark mode glass is neutral charcoal;
  deep-blue glass is blue-tinted; light unchanged. Chrome stays
  aggressively transparent; content panels use the denser
  `surface_panel_glass_bg`.
- **`text_secondary` values**: dark `#707088`, deep-blue `#8080a0` —
  balanced for readability on glass backdrops.
- **TitleBar styling**: aggressive blur (20px + saturate), padding
  balanced on all four sides, close button turns danger-red on hover with
  full restore on mouseout.
- **`sync_theme()`**: skips body background for transparent windows.
- **Gallery overhaul**: each tab now has a description, code sample, and
  live demo; window is frameless with a glass `TitleBar`.
- **`Flex` / `VStack` / `HStack`**: `min-height: 0` flex fix prevents
  overflow clipping; `grow` parameter for filling parent space.

### Fixed

- JS event routing: `data-window-action` only fires on `click` events,
  not on `mouseover`/`mouseout`.
- TitleBar hover state machine: `_apply_hover()` now restores base
  colours on mouseout instead of freezing the hover style.
- `set_background()`: background sits on a dedicated `#neony-bg` layer
  instead of `body` (transparent windows skip body-background painting).
  Tint uses `var(--color-bg)` — follows theme switches automatically.
- `render()`: silently drops patches when the WebView is no longer
  initialized (window closing/closed).
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
