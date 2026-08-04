# Roadmap

Planned work, roughly in priority order.

## Performance

- [x] **Hover de-noise** — `mouseover`/`mouseout`/`focus`/`blur` render deferred (one frame of coalescing)
- [x] **Input throttling** — `input` joins the deferred render path; typing coalesces into one render per frame
- [x] **Dirty-subtree diffing** — only changed elements re-serialize; mutations mark their ancestors dirty
- [x] **Snapshot reuse** — unchanged subtrees reuse cached snapshots, skipping `to_node()`
- [x] **Style direct-patch** — pure style changes bypass the full diff

## Reactivity

- [x] **Signal primitives** — `Signal` / `Computed` / `Effect` with automatic dependency tracking and `batch()` coalescing
- [x] **Declarative bindings** — `bind_text()` / `bind_style()` / `bind_attr()` / `bind_visible()` on elements and components
- [x] **Cross-window reactivity** — a shared signal write updates every window with a binding
- [x] **JS unit tests** — vitest + jsdom cover the browser runtime (event delegation, patch engine)

## Events

- [x] **Wheel events** — `wheel` in the delegation table, `delta_x` / `delta_y` in the payload (part of the rich event payload batch)
- [ ] **Scroll events** — `scroll` delegation (high-frequency; would ride the deferred render path)
- [ ] **Pointer move events** — `pointermove` / `mousemove` for sliders, drawing, tooltip-follow, drag feedback
- [x] **File drop** — `drop` / `dragover` / `dragleave` delegated; `DomEvent.drop_files` carries `dataTransfer.files` as `[{path, name, size, type}]` (`File.path` works on WebView2 / WebKitGTK, empty on macOS WKWebView); `on_drop()` / `on_dragover()` / `on_dragleave()` on elements and components; the engine `preventDefault()`s dragover/drop so the webview never navigates to the dropped file
- [ ] **In-app drag reorder** — `dragstart` / `dragover` / `drop`; needs a user hook (via `eval_js` or a future API) to call `dataTransfer.setData(...)`, since the delegate can't know the drag payload
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

- [ ] **Form controls** — Radio, Switch, Select/ComboBox, Slider, Progress
- [ ] **Overlays** — Dialog/Modal, Tooltip, Dropdown, Menu (depend on pointer-move events and rich event payload for positioning)
- [ ] **Data views** — DataTable, List, Tree
- [ ] **Content** — Card, Avatar, Badge, Image

## Animation

- [ ] **CSS `transition` support** in `Styles`
- [ ] **Built-in animated containers**
- [ ] **Transition hooks**

## Platform integration

- [ ] **File dialogs** — open/save file via native OS dialog
- [x] **Window icon** — `WindowConfig.icon` at startup; `app.set_icon()` at runtime; `TitleBar(icon=...)` inline for frameless windows
- [ ] **Window state query** — `show()` / `hide()` / `focus()` / `set_bounds()` (screen position via tao `set_outer_position`) are exposed; only the query half (`get_size()` / `get_bounds()`) remains, needs lumiview upstream
- [x] **Clipboard API** — `clipboard_write(text)` / `clipboard_read()` wrap `navigator.clipboard` (text; read needs a user gesture)
- [x] **Local resource URL helper** — `file_url()` / `data_url()` for Windows paths, spaces, non-ASCII filenames
- [ ] **System tray** — tray icon with context menu (tao-supported, needs lumiview upstream)
- [ ] **Global shortcuts** — app-wide keybindings that work even when the window is *not* focused. No JS API can observe keys outside a focused window, so this needs native code: tao 0.9.1+ has `platform::global_shortcut`, needs lumiview upstream. Caveat: the Linux hotkey ecosystem is X11-only — Wayland gets nothing

## Platform verification

- [x] **Windows (WebView2)**
- [ ] **macOS (WKWebView)**
- [x] **Linux desktops (Wayland)**
- [ ] **HiDPI / mixed-DPI scaling**

> NOTE:
> For Linux, we won't test on x11, please do it yourself
> For macOS, we don't have a device to test on, please do it yourself too.
