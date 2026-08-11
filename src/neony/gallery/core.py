"""Gallery core — the app instance, shared state, and layout helpers.

Everything here is import-time side-effecting on purpose: sections build
their panels at import, so the app and helpers must exist first.  The
heavy construction (NeonApplication) is what makes this package an
opt-in subpackage — ``neony/__init__.py`` deliberately does not import it.
"""

from __future__ import annotations

# Must be the FIRST import: this runs gallery/i18n.py, registering the
# gallery catalog before any tr_now() call below resolves a translation.
# Deliberately out of isort order — the registration ordering is a hard
# constraint (I001 is ignored for this file in pyproject.toml).
from .i18n import tr, tr_now

from neony.application import (
    Config,
    LANGUAGES,
    Language,
    NeonApplication,
    WebViewConfig,
    WindowConfig,
    set_language,
)
from neony.application.elements import Button, Component, Dropdown, Heading, HStack, Separator, Spacer, Text, VStack
from neony.application.elements.base import ReactiveText
from neony.application.theme import stub
from neony.dom import Computed, Div, DOMElement, DomEvent, Signal, Styles

app = NeonApplication(
    Config(
        window=WindowConfig(
            title=tr_now(tr.shell.window_title),
            width=1000,
            height=640,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

_BACKGROUND_URL = "https://harcic.is-a.dev/resource/backgrounds/8.webp"
_ICON_URL = "https://harcic.is-a.dev/resource/favicon.svg"

_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

# Shared across tabs: bumped in the Reactive tab, observed in Forms.
heat = Signal(30)


def CodeBlock(code: str) -> DOMElement:
    """Render *code* as a monospace, surface-toned block."""
    return Div(
        styles=Styles(
            background_color=stub.surface,
            border_radius="8px",
            padding="12px 16px",
            border="1px solid var(--color-border)",
            font_family=_MONO,
            font_size="12px",
            line_height="1.6",
            white_space="pre",
            overflow="auto",
            color=stub.text_secondary,
        ),
        container=[code],
    )


def Section(title: ReactiveText, blurb: ReactiveText, code: str, *demos: Component | DOMElement) -> VStack:
    """One gallery section: heading, description, code sample, live demo.

    The code sample is reference material and is never translated.
    """
    return VStack(
        Heading(title, level=3),
        Text(blurb, role="secondary"),
        CodeBlock(code),
        Separator(),
        *demos,
        gap="12px",
        align="stretch",
    )


def StatusChip(label: ReactiveText) -> tuple[HStack, Div]:
    """A small label + status-dot pair, updated by event handlers.
    Returns ``(chip, dot)`` so handlers can light the dot up."""
    dot = Div(
        styles=Styles(
            width="10px",
            height="10px",
            border_radius="50%",
            background_color=stub.border,
            flex_shrink="0",
        )
    )
    chip = HStack(
        dot,
        Text(label, size="12px", role="secondary"),
        gap="6px",
        align="center",
    )
    return chip, dot


def set_dot(dot: Div, active: bool) -> None:
    """Light (or dim) a status dot."""
    dot.styles.background_color = stub.accent if active else stub.border


def Mono(size: str = "13px") -> Div:
    """A monospace, muted single-line readout; update via ``container``."""
    return Div(
        styles=Styles(
            font_family=_MONO,
            font_size=size,
            color=stub.text_secondary,
        )
    )


# ── header (shared across tabs) ──────────────────────────────────

# The active theme-mode rides a Signal so the theme button's label is a
# live binding (a plain imperative set would overwrite the reactive text
# and freeze the label on the startup language).
theme_mode = Signal("light")


def _mode_label_ref(mode: str) -> Computed[str]:
    if mode == "light":
        return tr.shell.light_mode
    if mode == "dark":
        return tr.shell.dark_mode
    return tr.shell.deep_blue_mode


theme_btn = Button(Computed(lambda: _mode_label_ref(theme_mode())()), variant="ghost")


async def on_theme_click(_event: DomEvent) -> None:
    nxt = app.theme.next()
    await app.set_theme(nxt)
    theme_mode.set(nxt.mode)


theme_btn.on_click(on_theme_click)

# Language switcher — endonym items (each language shown in its own
# name), so the picker is readable in any active language.
_LANGUAGE_DISPLAY = {
    Language.EN: "English",
    Language.ZH: "中文",
    Language.JA: "日本語",
    Language.FR: "Français",
    Language.DE: "Deutsch",
    Language.ES: "Español",
    Language.PT: "Português",
    Language.RU: "Русский",
}
_LANGUAGE_ITEMS = [(lang.value, _LANGUAGE_DISPLAY[lang]) for lang in LANGUAGES]

lang_dropdown = Dropdown(tr.shell.language, items=_LANGUAGE_ITEMS, width="140px")


async def on_language_change(event: DomEvent) -> None:
    set_language(event.value)


lang_dropdown.on_change(on_language_change)

header = VStack(
    Heading(tr.shell.h1, level=1),
    Text(tr.shell.tagline, role="secondary"),
    HStack(Spacer(), lang_dropdown, theme_btn, gap="8px"),
    Separator(),
    gap="12px",
)
