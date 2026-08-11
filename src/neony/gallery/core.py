"""Gallery core — the app instance, shared state, and layout helpers.

Everything here is import-time side-effecting on purpose: sections build
their panels at import, so the app and helpers must exist first.  The
heavy construction (NeonApplication) is what makes this package an
opt-in subpackage — ``neony/__init__.py`` deliberately does not import it.
"""

from __future__ import annotations

from neony.application import Config, NeonApplication, Theme, WebViewConfig, WindowConfig
from neony.application.elements import Button, Component, Heading, HStack, Separator, Spacer, Text, VStack
from neony.application.theme import stub
from neony.dom import Div, DOMElement, DomEvent, Signal, Styles

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Component Gallery",
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


def Section(title: str, blurb: str, code: str, *demos: Component | DOMElement) -> VStack:
    """One gallery section: heading, description, code sample, live demo."""
    return VStack(
        Heading(title, level=3),
        Text(blurb, role="secondary"),
        CodeBlock(code),
        Separator(),
        *demos,
        gap="12px",
        align="stretch",
    )


def StatusChip(label: str) -> tuple[HStack, Div]:
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

theme_btn = Button("Light mode", variant="ghost")


async def on_theme_click(_event: DomEvent) -> None:
    await app.set_theme(app.theme.next())
    theme_btn.label = Theme.mode_label(app.theme.mode)


theme_btn.on_click(on_theme_click)

header = VStack(
    Heading("Neony Component Gallery", level=1),
    Text("Every component, one page — with docs and code samples", role="secondary"),
    HStack(Spacer(), theme_btn, gap="8px"),
    Separator(),
    gap="12px",
)
