# Screenshot showcase

> [中文版本](showcase.zh.md) · [Documentation home](README.en.md)

These screenshots come from the real `neony.gallery` application running in a
native window. They are not mockups or separately rendered web pages. Each
image uses a different built-in theme family to show how the same components
respond to theme tokens.

Run the same application from a repository checkout:

```bash
uv run gallery
```

## Overlay lifecycle

![Modal dialog over the component gallery](assets/screenshots/gallery-overlays.png)

Cyberangel Dark. Dialogs, menus, dropdowns, tooltips, and toasts share the
window's layer manager. An overlay opened from another overlay gets its own
logical stack position, so Escape and outside-click actions reach the correct
component.

## Feedback and forms

![Multiline input, validation, alerts, spinner, and skeleton](assets/screenshots/gallery-feedback.png)

Ember Zone Light. The feedback page combines `Textarea`, `FormField`, `Alert`,
`Spinner`, and `Skeleton`. Labels, help text, errors, and invalid state are
connected to the control with explicit accessibility relationships.

## Virtualized data

![Selectable DataTable with sticky header](assets/screenshots/gallery-datatable.png)

Nightglow Dark. `DataTable` keeps its sticky header, sorting, row identity, and
selection semantics while rendering a bounded window for large collections.

## Managed media

![Audio player with transport controls](assets/screenshots/gallery-media.png)

Planet Plaza Light. `Audio` and `Video` provide themed transport controls,
local `neony://` sources, seeking, volume, and playback events without exposing
raw HTML media elements to application code.
