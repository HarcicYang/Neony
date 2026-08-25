# Neony API reference

> [中文版本](README.zh.md) · [Documentation home](../README.en.md)

The reference is split into paired chapters. Each chapter covers one
area with short signatures, parameters, return values, edge cases, and a
small example; long-form explanations live in the guides. API symbols,
import paths, commands, and example filenames stay in English in both
language versions so code can be copied directly.

## Chapters

- [Core](core.en.md) — `NeonApplication`, `launch`, `Config` /
  `WindowConfig` / `WebViewConfig`, `Page`, lifecycle, multi-window,
  navigation policies, `Tray`.
- [Components](components.en.md) — form controls, text & tabs, overlays
  & feedback, content components, cascading `Menu` / `MenuBranch` /
  `CascadingDropdown`, and the `Reorder` drag-and-reorder component.
- [Layout & chrome](layout-chrome.en.md) — `VStack` / `HStack` / `Flex` /
  `Separator` / `GlassPanel`, `TitleBar`, `Sidebar` / `Pane` /
  `SidebarGroup`, `Tree`, `List`, `DataTable`, `Icon`.
- [DOM & CSS](dom-css.en.md) — `Color`, `Styles`, `DomEvent`, raw HTML
  elements, and the low-level drag primitive.
- [Reactivity](reactive.en.md) — `Signal`, `Computed`, `effect` / `Effect`,
  `untrack`, `SharedSignal`, declarative bindings, `bind_value`,
  dirty-subtree tracking.
- [Platform & i18n](platform-i18n.en.md) — internationalization,
  theming, motion tokens, and the platform-native surfaces (window
  controls, native file dialogs, system tray).

## Stability

Neony is pre-beta. Some names still carry deprecated aliases (e.g.
`active_key` → `selected_key`); the chapters note them inline. See the
project's [CHANGELOG](../../CHANGELOG.md) for the per-version story.

The previous monolithic entry is retained at
[`api.en.md`](../api.en.md) as a stable link target that redirects to
these chapters; new content lives in the split chapters above.
