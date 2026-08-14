# Neony Documentation

> [中文文档](README.zh.md)

Neony is a pre-beta reactive desktop UI framework for Python. This directory is
organized by task: start with the tutorial, use guides for common application
features, and use the API reference when you need an exact signature.

## Start here

- [Getting started](getting-started.en.md) — install Neony and build a small
  reactive window step by step.
- [Installation and platforms](guides/installation-platforms.en.md) — system
  dependencies, platform limits, native dialogs, and troubleshooting.
- [Examples index](../readme.md#demos) — the current runnable demos in the
  repository root.

## Guides

The tutorial is the recommended path for a new user; the guides cover
common application features.

- [Installation and platforms](guides/installation-platforms.en.md)
- [Contributing](../CONTRIBUTING.md)
- [Roadmap](../ROADMAP.md)
- [Changelog](../CHANGELOG.md)

## API reference

The reference is split into paired chapters — each covers one area with
short signatures, parameters, return values, edge cases, and a small
example.

- [API index](api/README.en.md) — the full chapter list.
- [Core](api/core.en.md) — application, entry points, lifecycle, tray.
- [Components](api/components.en.md) — form controls, overlays, content.
- [Layout & chrome](api/layout-chrome.en.md) — flex panels, sidebar, tree,
  list, table.
- [DOM & CSS](api/dom-css.en.md) — `Color`, `Styles`, `DomEvent`, drag.
- [Reactivity](api/reactive.en.md) — `Signal`, `Computed`, bindings.
- [Platform & i18n](api/platform-i18n.en.md) — theming, i18n, native
  surfaces.

The previous monolithic [`api.en.md`](api.en.md) is retained as a
stable link target and redirects to the chapters above. API symbols,
import paths, commands, and example filenames remain in English in both
language versions so code can be copied directly.

## Language and scope

English and Chinese documents are separate files with matching links. New
features should update both languages. Tutorial explanations belong in guides;
short signatures, parameters, return values, and edge cases belong in the API
reference. The root README remains the project overview and shortest entry
point.

Return to the [English README](../readme.md) or read the
[中文 README](../readme.zh.md).
