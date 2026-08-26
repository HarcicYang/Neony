# Roadmap

Neony is a reactive desktop UI framework for Python. This page records
the capabilities that already exist and the work still planned, from an
application developer's point of view.

## Current state

### Reactivity and rendering

- Reactive primitives: `Signal`, `Computed`, `Effect`, `batch()`, and
  cross-window `SharedSignal` writes.
- Declarative bindings: `bind_text()`, `bind_style()`, `bind_attr()`,
  `bind_visible()` on elements and components.
- Coalesced renders: fast typing, hover, and scroll updates do not
  force one synchronous re-render per event.
- Large trees are handled in bounded chunks, and `List` virtualizes
  collections past 200 rows so only the visible window is rendered.

### Events and input

- Delegated events: mouse, wheel with deltas, scroll position,
  `pointermove` with movement deltas and pointer type, clipboard
  (`paste` / `copy` / `cut`), file drop, and in-app drag lifecycle
  events.
- Rich `DomEvent` payloads: modifier keys, pointer coordinates,
  wheel deltas, scroll position, clipboard text/HTML, drag payloads,
  and dropped files.
- In-app shortcuts: `Page.on_shortcut("Ctrl+S", fn)`, including
  per-platform key dictionaries; window-level `on_keydown` /
  `on_keyup`.

### Lifecycle and window control

- `page.on_close()`, `app.close_handler`, `page.on_focus()` /
  `on_blur()`, navigation / new-window / download policies with per-page
  overrides.
- `show()` / `hide()` / `focus()` / `set_bounds()`, startup and runtime
  window icons, and frameless `TitleBar` chrome.
- Clipboard API: `clipboard_write()` / `clipboard_read()`.

### Components

- Form controls: Radio / RadioGroup, Switch, Select, ComboBox, Slider,
  Progress.
- Overlays: Dialog, Tooltip, Dropdown, Menu / MenuBranch,
  CascadingDropdown, NoticeBubble.
- Data views: DataTable, List, Tree.
- Content: Card, Avatar, Badge, Image.
- Layout: Accordion / Collapsible, ScrollArea, StickToBottom,
  Reorder / ReorderContent.
- Media: managed Video / Audio players with custom transport, local
  `neony://` sources, and HEVC transcode fallback.
- Rich text: `RichText` with text and inline images, caret/selection
  API, IME-safe editing, and image/file paste.
- Chat and notifications: Toast, MessageBubble, NoticeBubble.
- Navigation: Sidebar with sections and panes, Tabs, unified Icon.

### Animation and styling

- Typed CSS models: `Styles`, `Color`, `Border`, `Filter`, `Transform`,
  `BoxShadow`, `Transition`, keyframes, and animation presets.
- Motion tokens and helpers: `motion.stub`, `transition()`,
  `popup_animation()`, `submenu_animation()`.
- Delegated animation events: `transitionend`, `animationstart`,
  `animationend`.

### Theming and i18n

- Eight built-in themed presets across four visual families: Nightglow,
  Planet Plaza, Ember Zone, Cyberangel (dark/light each).
- `DARK`, `LIGHT`, and `DEEP_BLUE` remain aliases; `Theme` is immutable,
  and custom themes register alongside the built-ins.
- Framework i18n with typed catalogs and reactive language switches.

### Platform integration

- Native file dialogs: `open_file()`, `open_files()`, `save_file()`,
  `select_folder()` using the platform picker (zenity/OS native; the
  dialog opens asynchronously).
- File and data URLs: `file_url()`, `data_url()`, and custom
  `neony://` protocol handlers served by Python.
- System tray with native menus and close-to-tray behavior. Linux
  requires `libayatana-appindicator`; tray icon support depends on
  LumiView.
- File drag-and-drop, scroll indicators, smooth horizontal wheel
  scrolling, transparent-window blur on Wayland, and an app name shown
  in the taskbar.

## Priorities

- **List/table virtualization** — extend virtualized rendering to very
  large tables and other collection views.
- **Built-in animated containers** — ready-made animated panels,
  drawers, and slide-in regions.
- **macOS (WKWebView) verification** — the platform is not yet a
  verified target; HiDPI / mixed-DPI scaling also needs verification.
- **Native installers and packaging** — evaluate a packaging path
  (for example Briefcase) if MSI / AppImage / .app installers are
  wanted.

## Non-goals for now

- X11 is not a supported Linux target: test on Wayland.
- Raw HTML/JS/CSS are not part of the public API; the framework exposes
  typed Python objects only.
