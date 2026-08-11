#!/usr/bin/env python3
"""TransparentPanel demo — floating glass panel with native blur.

A small, always-on-top, frameless window (540x280) with a fully
transparent background.  ``transparent=True`` automatically applies the
platform's native frosted material behind the window.  The whole panel
is a drag region — drag anywhere to move the window — and the close
button calls the app explicitly.

Usage:
    python demo_transparent_panel.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import Button, GlassPanel, Heading, HStack, Text

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Transparent Panel",
            width=540,
            height=280,
            decorations=False,
            transparent=True,
            always_on_top=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

close_btn = Button("Close Panel", variant="danger").on_click(lambda _event: app.close())

panel = GlassPanel(
    Heading("Floating Panel", level=3),
    Text(
        "Native blur sits behind this window — drag anywhere to move it, or close it with the button.",
        role="secondary",
    ),
    HStack(close_btn, gap="8px"),
    gap="16px",
    padding="20px",
    radius="12px",
    width="540px",  # fixed = window content area
    height="280px",
)
# The whole panel drags the frameless window; the close button opts out
# (same data-lumiview markers the TitleBar uses).
panel._root.args["data-lumiview-drag-region"] = ""
close_btn._root.args["data-lumiview-no-drag"] = ""

page = Page(gap="0px", padding="0px", max_width="100%", radius="12px").add(panel)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
