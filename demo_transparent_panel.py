#!/usr/bin/env python3
"""TransparentPanel demo — floating glass panel with native blur.

A small, always-on-top, frameless window (360x280) with a fully
transparent background.  ``transparent=True`` automatically applies the
platform's native frosted material behind the window — Acrylic on
Windows, Blur on macOS (Linux/GTK has none).  The whole panel is a drag
region and the close button uses the built-in window action.

Usage:
    python demo_transparent_panel.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import Button, GlassPanel, Heading, HStack, Text, VStack
from neony.dom import Div, Styles

# ── application: tiny, frameless, transparent, always on top ─────

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Transparent Panel",
            width=360,
            height=280,
            decorations=False,
            transparent=True,
            always_on_top=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

# ── chrome: a drag-handle strip with grip marks ──────────────────

drag_handle = Div(
    styles=Styles(
        height="28px",
        display="flex",
        align_items="center",
        justify_content="center",
        cursor="move",
        border_radius="12px 12px 0 0",
    ),
    container=[Text("⋯", role="secondary", size="12px").build()],
    args={"data-lumiview-drag-region": ""},
)

# ── content ──────────────────────────────────────────────────────

close_btn = Button("Close Panel", variant="danger")
# The button already carries no window action — the user handler calls
# app.close() explicitly (a nice contrast with TitleBar's auto actions).
close_btn.on_click(lambda e: app.close())

panel = VStack(
    GlassPanel(
        Heading("Floating Panel", level=3),
        Text(
            "Native blur sits behind this window — drag the grip bar to move it, or close it with the button.",
            role="secondary",
        ),
        HStack(close_btn, gap="8px"),
        gap="16px",
        padding="20px",
    ),
    gap="0px",
    padding="0px",
)

# ── assemble: drag handle + panel, one rounded glass unit ────────

page = Page(gap="0px", padding="0px", max_width="100%")
page.add(
    Div(
        styles=Styles(
            border_radius="12px",
            overflow="hidden",
            border="1px solid var(--color-border-glass)",
            box_shadow="0 12px 40px rgba(0, 0, 0, 0.35)",
        ),
        container=[drag_handle, panel.build()],
    )
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
