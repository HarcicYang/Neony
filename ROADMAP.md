# Roadmap

Planned work, roughly in priority order.

## Performance

- [x] **Hover de-noise** — `mouseover`/`mouseout`/`focus`/`blur` render deferred (one frame of coalescing)
- [x] **Input throttling** — `input` joins the deferred render path; typing coalesces into one render per frame
- [x] **Dirty-subtree diffing** — only changed elements re-serialize; mutations mark their ancestors dirty
- [x] **Snapshot reuse** — unchanged subtrees reuse cached snapshots, skipping `to_node()`
- [x] **Style direct-patch** — pure style changes bypass the full diff
- [x] **Fast DOM construction** — pydantic private-attr factories no longer dominate large-tree builds
- [x] **Serialization caches** — `Styles` / attrs cache their rendered dicts; per-class html-attr metadata is precomputed
- [x] **Linear diff paths** — moved-key positions and insert indices use maps instead of quadratic tree/list scans
- [x] **Key lifecycle cleanup** — removed subtrees are pruned from snapshots, key map and handler registries
- [x] **Chunked patch delivery** — large renders and first mounts stream in bounded message sizes
- [ ] **List/table virtualization** — render only the visible window for very large collections

## Reactivity

- [x] **Signal primitives** — `Signal` / `Computed` / `Effect` with automatic dependency tracking and `batch()` coalescing
- [x] **Declarative bindings** — `bind_text()` / `bind_style()` / `bind_attr()` / `bind_visible()` on elements and components
- [x] **Cross-window reactivity** — a shared signal write updates every window with a binding
- [x] **JS unit tests** — vitest + jsdom cover the browser runtime (event delegation, patch engine)

## Events

- [x] **Wheel events** — `wheel` in the delegation table, `delta_x` / `delta_y` in the payload (part of the rich event payload batch)
- [x] **Scroll events** — `scroll` delegated; `DomEvent.scroll_top` / `scroll_left` carry the position (from the actual scroller, dispatched to the nearest keyed ancestor); document scroll routes through the engine root; rides the deferred render path
- [x] **Pointer move events** — `pointermove` delegated; `event.movement_x` / `event.movement_y` carry the delta since the last event, `event.pointer_type` distinguishes mouse / pen / touch; rides the deferred render path
- [x] **File drop** — `drop` / `dragover` / `dragleave` delegated; `DomEvent.drop_files` carries `dataTransfer.files` as `[{path, name, size, type}]` (`File.path` works on WebView2 / WebKitGTK, empty on macOS WKWebView); `on_drop()` / `on_dragover()` / `on_dragleave()` on elements and components; the engine `preventDefault()`s dragover/drop so the webview never navigates to the dropped file
- [x] **In-app drag reorder** — `dragstart` / `dragenter` / `dragend` delegated alongside `dragover` / `dragleave` / `drop`; `DOMElement.drag_payload` declares the payload the engine hands to `dataTransfer.setData` synchronously on dragstart (read back via `DomEvent.drag_payload` on drop); reorder is a `container[:] = new_order` diff on the Python side
- [x] **Clipboard events** — `paste` / `copy` / `cut` delegated; paste carries `clipboard_text` / `clipboard_html`, copy/cut are notifications
- [x] **Rich event payload** — `DomEvent` carries modifier keys (`ctrl_key` / `shift_key` / `alt_key` / `meta_key`), mouse coordinates (`x` / `y` / `offset_x` / `offset_y`), and wheel delta (`delta_x` / `delta_y`) — shortcut keys, right-click menus, and scroll-aware UIs work without `eval_js`
- [x] **In-app shortcuts** — `Page.on_shortcut("Ctrl+S", fn)` (per-platform dict supported), fires while typing in any input via bubbling keydown

## Lifecycle

- [x] **Page close hook** — `page.on_close(fn)`, wired to the native `CloseRequested` event internally
- [x] **App shutdown hook** — `app.close_handler`, runs after all windows close
- [x] **Element reuse defense** — mounting the same element twice raises a clear `RuntimeError`
- [x] **Window focus/blur events** — `page.on_focus(fn)` / `on_blur(fn)`, wired to the native `Focused` / `Unfocused` events
- [x] **Window navigation control** — safe defaults (block navigation, deny new windows, cancel downloads) installed on every window; `page.on_navigation` / `on_new_window` / `on_download_started` / `on_download_completed` override them

## Components

- [x] **Form controls** — Radio/RadioGroup, Switch, Select, ComboBox, Slider, Progress
- [x] **Overlays** — Dialog (fixed scrim + centered glass panel; scrim/Escape/✕/outsideclick close), Tooltip (anchor-relative, placement + delay, zero measurement), Dropdown (Select's popup pattern, full keyboard nav), Menu / MenuBranch (cascading branches; `open_at(x, y)` from contextmenu coords), CascadingDropdown (multi-level trigger popup)
- [x] **Data views** — DataTable (sticky-header grid, click-to-sort, single/multi row selection), List (scrollable single-select data list), Tree (navigation rail + content host)
- [x] **Content** — Card (titled content panel; actions/footer; optional glass), Avatar (image/initial/placeholder + optional corner badge), Badge (pill or corner count; dot; 99+ clamp; zero hides), Image (rounded overflow-hidden frame; `src` is any URL)
- [x] **Reveal & scroll layout** — Accordion / Collapsible (stacked expandable sections, fluent `.section()`), ScrollArea (programmatic scroll API), StickToBottom (chat-stream auto-scroll), Reorder / ReorderContent (drag reorder with or without a board frame)
- [x] **Media players** — managed Video / Audio: custom transport, `neony://` source hydration, WebAudio audio engine, HEVC transcode fallback via `imageio-ffmpeg`
- [x] **Rich text editing** — RichText managed `contenteditable`: text + inline images, caret/selection API, insert at caret, ordered `content()` export, IME-safe, paste image files
- [x] **Notifications & Chat** — Toast (6 placements, success/info/error, placement-tied directional enter/exit animations), MessageBubble (QQ/Telegram style: from_me alignment/colors, optional avatar + name, built-in right-click menu, hover quick actions), NoticeBubble (centered system pill)

## Flaza (QQ client) requirements

> Driven by the Flaza QQ desktop client. Public APIs stay pure Python;
> internals may use `contenteditable` / native selection semantics.

### Already available

- [x] **Paste text / HTML** — `paste` is delegated; `DomEvent.clipboard_text`
  and `DomEvent.clipboard_html` are already populated from the clipboard.
- [x] **Scroll position reads** — `scroll` is delegated; `DomEvent.scroll_top`
  and `DomEvent.scroll_left` already carry the scrolled position.
- [x] **Stable-key in-place patching** — diff and direct-patch update
  existing DOM nodes via `update_attrs` / `update_styles` / `set_text`;
  stable keys are never remove/create'd.  This is the foundation for
  editor focus stability, but the editor itself still needs to be built.
- [x] **Drop files** — `drop` already carries `DomEvent.drop_files`
  (name / path / size / type).

### Partially available

- [x] **Mixed inline content** — the editor now uses a dedicated
  contenteditable path (`RichText` managed subtree, frozen by the diff
  engine).  General `to_node()` mixed string/element children remain
  unsupported by design; display-side rendering keeps wrapping text runs
  in keyed `Span` elements.
- [x] **Image deletion & selection inputs** — `keydown` (Backspace /
  Delete) and `click` are delegated; `RichText` interprets the caret /
  selection and syncs image deletion and selection back to Python.
- [x] **IME composition** — `compositionstart` / `compositionupdate` /
  `compositionend` are delegated and carry `composition_data` /
  `is_composing`; the managed editor subtree is not patched during
  composition.

### To implement

- [x] **RichText editor component** — a Python-driven editable region
  (`contenteditable` internally) that allows text and `img` inline
  elements to coexist.
- [x] **Caret / Selection API** — Python reads `caret_position()` /
  `selection_range()` and writes `set_caret(position)` / `focus()`.
- [x] **Insert at caret** — `insert_text(..., at_caret=True)` and
  `insert_image(..., at_caret=True)` land at the current caret.
- [x] **Ordered content export** — `editor.content()` returns an ordered
  model of `[TextSegment, ImageSegment, ...]`; Flaza maps it to
  `MessageElement` in order.
- [x] **Editor render stability** — the bridge freezes diffing under the
  editor's managed subtree; inserting an image keeps focus at the
  original caret.
- [x] **Inline image deletion & selection** — `Backspace` / `Delete` remove
  inline images; clicking an image reports the correct caret / selection
  to Python.
- [x] **IME composition events** — `compositionstart` /
  `compositionupdate` / `compositionend` are delegated; editor rendering
  does not interrupt Chinese input.
- [x] **Paste files / images** — `on_paste_image` / `on_paste_files`
  deliver pasted bytes as temp file paths, removing the need for Flaza
  to read the whole clipboard through pyclip.
- [x] **Python scroll API** — `ScrollArea.scroll_to_bottom()` /
  `scroll_to_top()` / `scroll_to({top, behavior})` replace `eval_js`
  scroll hacks.  The API lives on the component (a region, not the whole
  window); all JS is internal.
- [x] **StickToBottom / AutoScroll container** — auto-sticks while new
  content arrives; pauses when the user scrolls up; resumes near the
  bottom. This is the chat-stream scroll model.

## Animation

- [x] **CSS `transition` support** in `Styles` — typed `Transition` descriptor (`property`/`duration`/`timing`/`delay`) or raw shorthand string; also `transform` and `outline` fields.  Existing components' transitions now actually reach the DOM.
- [x] **Transition hooks** — `transitionend` / `animationstart` / `animationend` delegated events with `transition_property` / `animation_name` / `elapsed_time` payloads.
- [x] **Typed `@keyframes`** — chainable `KeyFrame(name).set(...)` / `Props` / `Animation` models; `app.register_keyframe()` injects into a global `<style id="neony-keyframes">` (built-in `neony-rise-in` / `neony-fade-in` always injected for components).
- [x] **Motion tokens** — `Motion.DEFAULT` injects the `--motion-*` variables; helpers `transition()` / `popup_animation()` / `submenu_animation()` cover popup and submenu timing; components reference `motion.stub`
- [ ] **Built-in animated containers**

## Theming

- [x] **Preset themes** — four visual families (Nightglow / Planet Plaza / Ember Zone / Cyberangel) with dark/light variants, ten presets total; `DARK` / `LIGHT` / `DEEP_BLUE` remain aliases; `Theme` is immutable and requires the full token set

## Platform integration

- [x] **File dialogs** — `app.open_file` / `open_files` / `save_file` / `select_folder` delegate to platform-native pickers (zenity on Linux, osascript on macOS, PowerShell on Windows, tkinter fallback) in an executor thread; cancel or failure → `None` / `[]`
- [x] **Window icon** — `WindowConfig.icon` at startup; `app.set_icon()` at runtime; `TitleBar(icon=...)` inline for frameless windows
- [ ] **Window state query** — `show()` / `hide()` / `focus()` / `set_bounds()` (screen position via tao `set_outer_position`) are exposed; only the query half (`get_size()` / `get_bounds()`) remains, needs lumiview upstream
- [x] **Clipboard API** — `clipboard_write(text)` / `clipboard_read()` wrap `navigator.clipboard` (text; read needs a user gesture)
- [x] **Local resource URL helper** — `file_url()` / `data_url()` for Windows paths, spaces, non-ASCII filenames
- [x] **System tray** — `Tray` / `TrayItem`: native menu (muda) + tray icon via lumiview .dev4; `close_to_tray` hides the app on window close (macOS Dock click restores); Linux needs libayatana-appindicator

## Platform verification

- [x] **Windows (WebView2)**
- [ ] **macOS (WKWebView)**
- [x] **Linux desktops (Wayland)**
- [ ] **HiDPI / mixed-DPI scaling**

> NOTE:
> For Linux, we won't test on x11, please do it yourself
> For macOS, we don't have a device to test on, please do it yourself too.

## Distribution

- [x] **Demo smoke test** — every `demo_*.py`, plus the `neony.gallery`
  package, spawns under `xvfb-run` in CI (`tests/smoke_demos.py`); a demo
  that fails to reach the event loop fails the build
- [x] **Executable packaging workflow** — `packaging.yml` builds the
  gallery (`neony.gallery.__main__`) as a one-file executable on Linux /
  Windows / macOS with **Nuitka** (`workflow_dispatch` for test builds,
  `v*` tags for releases, artifacts named
  `<os>_<arch>_<version>_nuitka[.exe]`); Windows and macOS are fully
  self-contained, Linux needs `libwebkit2gtk-4.1`
- [ ] **Briefcase** — if native installers (MSI / AppImage / .app) are
  wanted later, re-evaluate BeeWare as an alternative to the current
  Nuitka packaging
