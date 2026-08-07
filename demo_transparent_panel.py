#!/usr/bin/env python3
"""TransparentPanel demo — floating glass panel with native blur.

A small, always-on-top, frameless window (360x280) with a fully
transparent background.  ``transparent=True`` automatically applies the
platform's native frosted material behind the window.  The TitleBar is
the native drag region and the close button calls the app explicitly.

Usage:
    python demo_transparent_panel.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import Button, GlassPanel, Heading, HStack, Text, TitleBar, VStack

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

titlebar = TitleBar("⋯", show_minimize=False, show_maximize=False, show_close=False, height="28px")
close_btn = Button("Close Panel", variant="danger").on_click(lambda _event: app.close())

panel = GlassPanel(
    Heading("Floating Panel", level=3),
    Text(
        "Native blur sits behind this window — drag the grip bar to move it, or close it with the button.",
        role="secondary",
    ),
    HStack(close_btn, gap="8px"),
    gap="16px",
    padding="20px",
    radius="0px",
    border_top_left_radius="0px",
    border_top_right_radius="0px",
    grow=True,
)

page = Page(gap="0px", padding="0px", max_width="100%", radius="12px").add(
    VStack(titlebar, panel, gap="0px", align="stretch", grow=1)
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
