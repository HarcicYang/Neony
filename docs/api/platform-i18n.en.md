# Platform & i18n

> [中文版本](platform-i18n.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

Internationalization, theming, and the platform-native surfaces — window
controls, native file dialogs, and system tray. The application object
that owns these is [`NeonApplication`](core.en.md#neonapplication).

## Internationalization

Reactive, framework-wide i18n. The active language is a `Signal`; every
`tr` reference is a `Computed[str]`, so bound text updates live on
`set_language()` without losing widget state.

**Catalogs are typed, not dicts.** `Catalog` is a frozen pydantic model —
each field is a translation key with an English default; one instance per
language. Subclass it to add app keys (flat `str` fields or nested
sub-model groups); pydantic class defaults give per-key English fallback.

```python
from neony.application import Catalog, Common, Language, register_catalog, set_language, tr, tr_now


class FilesCatalog(Catalog):
    count: str = "{n} files"


class AppCatalog(Catalog):
    save: str = "Save"  # → tr.save
    files: FilesCatalog = FilesCatalog()  # → tr.files.count


register_catalog(Language.EN, AppCatalog())
register_catalog(
    Language.ZH,
    AppCatalog(
        save="保存",
        files=FilesCatalog(count="{n} 个文件"),
        common=Common(copy_text="复制", delete="删除", ok="确定", cancel="取消", close="关闭"),
    ),
)

tr.common.copy_text  # Computed[str] → "Copy" (updates live on switch)
tr.files.count.format(n=5)  # interpolation → "5 files"
tr_now(tr.common.copy_text)  # immediate read, no subscription (display-time)
set_language(Language.ZH)  # all tr.* bindings re-resolve
app.set_language(Language.ZH) / app.language  # app-level convenience
```

- **`Language`** — a `StrEnum` of the built-in languages
  (`EN/ZH/JA/FR/DE/ES/PT/RU`); `set_language` rejects unknown codes with
  `ValueError`. A valid language with no registered catalog falls back to
  English.
- **`Catalog` / `Common`** — frozen pydantic models
  (`extra="forbid"` catches key typos). `Common` carries the
  framework-owned labels (`copy_text`, `delete`, `ok`, `cancel`, `close`).
- **`tr`** — a chainable proxy. `tr.<key>` and `tr.<group>.<key>` each
  return a reactive `Computed[str]`; pass them to any component that
  accepts reactive text (`Text`, `Button`). `tr.<key>.get()` reads the
  current value.
- **`tr_now(tr.xx.xxx)`** — the current value without subscribing; for
  component defaults and menus resolved at display time. Safe inside
  effects (no dependency leak).
- **Reserved key names** — keys that collide with `Computed`'s API
  (`get`, `format`) or start with `_` cannot be referenced through the
  `tr` chain.
- Framework defaults (MessageBubble's built-in right-click menu,
  `PromptDialog`'s confirm/cancel) resolve through the catalog.

## Theming

Eight built-in presets across four visual families — Nightglow, Planet
Plaza, Ember Zone, and Cyberangel — each with paired light and dark
material. They are exposed as CSS custom properties; the historical
names `DARK` (default), `LIGHT`, and `DEEP_BLUE` remain as aliases for
`NIGHTGLOW_DARK`, `NIGHTGLOW_LIGHT`, and `PLANET_PLAZA_DARK`. Each
preset is an **immutable** `Theme` instance; constructing any `Theme`
auto-registers it under its `mode`.

```python
from neony.application import NIGHTGLOW_LIGHT, Theme

app.theme  # the active preset (defaults to DARK → NIGHTGLOW_DARK)
Theme.get("nightglow-light")  # single-shot lookup of a registered preset by mode name
app.theme.next()  # the preset that follows the active one in toggle order
Theme.modes()  # registered mode names, in preset-construction order
Theme.mode_label("nightglow-dark")  # "Nightglow Light mode" — the display label for this mode
await app.set_theme(NIGHTGLOW_LIGHT)  # swap the active preset and re-inject variables
```

Token families: `--color-bg`, `--color-surface`,
`--color-text-primary` / `--color-text-secondary`, `--color-accent`,
`--color-on-accent` / `--color-on-danger` (text colour on a saturated accent /
danger fill), `--color-danger`, `--color-success`, `--color-border`,
`--color-shadow`, `--color-*-glass*` (frosted variants).

Components reference tokens via `Color(var="--color-*")` so a theme
switch only replaces the `:root` variable block, and the browser
recolors every `var(--color-*)`.

Custom themes:

```python
from neony.application import Theme
from neony.dom import BoxShadow, Color, Shadow

# Theme has no defaults — a custom preset must supply the full token set.
my_theme = Theme(
    mode="sepia",
    bg=Color(hex="#f4efe6"),
    surface=Color(hex="#fffaf0"),
    surface_raised=Color(hex="#efe7d8"),
    text_primary=Color(hex="#2b2118"),
    text_secondary=Color(hex="#756a5b"),
    accent=Color(hex="#b3652d"),
    accent_dim=Color(hex="#8e4c1f"),
    danger=Color(hex="#b95758"),
    success=Color(hex="#27875f"),
    border=Color(rgba=(62, 52, 34, 0.16)),
    shadow=BoxShadow(layers=[Shadow(x=0, y=20, blur=54, color=Color(rgba=(70, 57, 32, 0.18)))]),
    on_accent=Color(hex="#fffaf0"),
    on_danger=Color(hex="#ffffff"),
    bg_overlay=Color(rgba=(244, 239, 230, 0.74)),
    surface_glass=Color(rgba=(249, 245, 237, 0.82)),
    surface_raised_glass=Color(rgba=(255, 250, 240, 0.92)),
    border_glass=Color(rgba=(62, 52, 34, 0.18)),
    accent_glass=Color(rgba=(179, 101, 45, 0.18)),
    danger_glass=Color(rgba=(185, 87, 88, 0.18)),
    success_glass=Color(rgba=(39, 135, 95, 0.16)),
    surface_glass_bg=Color(rgba=(249, 245, 237, 0.72)),
    surface_panel_glass_bg=Color(rgba=(255, 250, 240, 0.92)),
    accent_glass_bg=Color(rgba=(179, 101, 45, 0.54)),
    danger_glass_bg=Color(rgba=(185, 87, 88, 0.54)),
)
await app.set_theme(my_theme)
Theme.get("sepia") is my_theme  # True
```

## Motion tokens

Durations and easing behind popups, transitions, and component
animations are tokenized in parallel with themes. `Motion` is an
immutable, registered preset; `DEFAULT` is the built-in preset.

```python
from neony.application.motion import Motion, popup_animation, stub, transition

Motion.get("default").fast  # "0.12s" — the concrete default preset
stub.fast  # "var(--motion-fast)" — the token used by component styles
transition(
    "background-color"
)  # Transition(property=..., duration=var(--motion-normal), timing=var(--motion-ease-standard))
popup_animation()  # Animation(name="neony-drop-in", duration=var(--motion-normal), timing=var(--motion-ease-enter))
```

Injected variables: `--motion-fast`, `--motion-normal`, `--motion-slow`,
`--motion-ease-standard`, `--motion-ease-enter`, `--motion-ease-exit`,
`--motion-popup-animation`, `--motion-submenu-animation`.

## Platform-native surfaces

### Window controls

All async on [`NeonApplication`](core.en.md#neonapplication):
`set_title`, `set_size`, `minimize`, `toggle_maximize`, `is_maximized`,
`set_fullscreen`, `start_dragging`, `close`, `set_icon`, plus the native
blur / acrylic / mica effects (`apply_blur`, `apply_acrylic`,
`apply_mica`, `clear_effect`). `transparent=True` already applies the
platform material automatically (Wayland blur on Linux where supported,
Acrylic on Windows, Blur on macOS). The `apply_*` methods are manual
overrides and platform-limited: `apply_blur` is macOS/Windows; acrylic /
mica are Windows 11. Every window-control method takes an optional
`window_index` (default 0) for multi-window apps.

### Native file dialogs

The public async methods are `open_file`, `open_files`, `save_file`, and
`select_folder` (see [`NeonApplication`](core.en.md#neonapplication) for
signatures). The platform implementation is selected automatically:

```text
Linux   → zenity when available, otherwise tkinter
macOS   → osascript
Windows → PowerShell
Other   → tkinter fallback
```

The picker opens asynchronously, so the app keeps responding while it is
up. A cancelled
single-selection call returns `None`; a cancelled multi-selection call
returns `[]`. File filters are passed as `(label, pattern)` pairs, for
example `[("PNG images", "*.png"), ("All files", "*.*")]`. If a platform
command or fallback cannot open, the public API normalizes the usual
failure/cancel result to the same empty shape — never an exception. Test
picker behavior on the platform where the application will ship.

See the [Installation and platforms](../guides/installation-platforms.en.md)
guide for the runtime dependencies behind these surfaces and the
troubleshooting table.

### System tray

The native tray is configured before `run()` via `app.tray = Tray(...)`.

See `Tray` & `TrayItem` in the [Core chapter](core.en.md) for the full
API. Platform note: Linux needs `libayatana-appindicator`, the tooltip
is unsupported there, and the menu cannot be replaced after creation.
