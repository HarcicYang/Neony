#!/usr/bin/env python3
"""CustomWindow demo — frameless window with TitleBar + Sidebar chrome.

A decorated-less, transparent window (600x480) whose chrome is drawn by
Neony itself: a glass TitleBar on top and a glass Sidebar on the left,
seamlessly joined into one unit.  Window controls are fully managed by
the TitleBar (``data-window-action`` → WindowControls bridge); the
Sidebar owns its content panes — clicking an item, or pressing its
shortcut, swaps the visible pane.  The background image shows through
the frosted surfaces.

Usage:
    python demo_custom_window.py
"""

from neony.application import Config, NeonApplication, Page, Theme, WebViewConfig, WindowConfig
from neony.application.elements import Button, GlassPanel, Heading, HStack, Icon, Pane, Sidebar, Text, TitleBar
from neony.dom import DomEvent

# ── application: frameless + transparent ─────────────────────────

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony Studio",
            width=600,
            height=480,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

_BACKGROUND_URL = "https://harcic.is-a.dev/resource/backgrounds/13.webp"

# ── chrome: TitleBar + Sidebar ───────────────────────────────────

titlebar = TitleBar("Neony Studio")
# Extra callback on top of the built-in window action:
titlebar.on_close(lambda e: print("[titlebar] close requested"))

theme_btn = Button("Toggle Theme", variant="ghost")


async def on_theme_click(event: DomEvent) -> None:
    await app.set_theme(app.theme.next())
    theme_btn.label = Theme.mode_label(app.theme.mode)


theme_btn.on_click(on_theme_click)

# ── content panes ────────────────────────────────────────────────
# The background image lives inside each pane's GlassPanel — it never
# sits under the titlebar/sidebar chrome, which stay transparent so the
# desktop shows through the frosted frame.

home_pane = GlassPanel(
    Heading("Home", level=2),
    Text(
        "A frameless window with a custom glass TitleBar and Sidebar. "
        "Drag the titlebar to move the window; double-click it to maximize. "
        "The chrome is transparent — the desktop shows through the frosted "
        "frame, while the image stays inside this panel.",
        role="secondary",
    ),
    HStack(theme_btn, gap="8px"),
    gap="16px",
    padding="24px",
    background=_BACKGROUND_URL,
    radius="0px",
    grow=True,
)

settings_pane = GlassPanel(
    Heading("Settings", level=2),
    Text("Placeholder for settings — this pane swaps in via the Sidebar.", role="secondary"),
    gap="16px",
    padding="24px",
    background=_BACKGROUND_URL,
    radius="0px",
    grow=True,
)

stats_pane = GlassPanel(
    Heading("Stats", level=2),
    Text("Placeholder for statistics.", role="secondary"),
    gap="16px",
    padding="24px",
    background=_BACKGROUND_URL,
    radius="0px",
    grow=True,
)

# ── chrome + content in one unit ─────────────────────────────────
# The Sidebar owns its panes: selection toggles slot visibility
# internally and cached roots are reused (build-once).  Ctrl+1..3
# switch panes by keyboard; sidebar.shortcuts() yields (combo, handler)
# pairs the Page wires below.

sidebar = Sidebar(
    Pane("Home", panel=home_pane, icon=Icon.glyph("🏠"), shortcut="Ctrl+1"),
    Pane(
        "Settings",
        panel=settings_pane,
        icon=Icon.glyph("⚙️"),
        shortcut={"darwin": "Meta+2", "default": "Ctrl+2"},
    ),
    Pane("Stats", panel=stats_pane, icon=Icon.glyph("📊"), shortcut="Ctrl+3"),
)
sidebar.on_change(lambda e: print(f"[sidebar] pane: {e.value}"))

# ── assemble ─────────────────────────────────────────────────────
# fill=True stretches the page to the window; the VStack grows to fill
# it; the Sidebar (rail + panes, one unit) fills the space below the
# titlebar.  radius rounds the whole window frame.
page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px").add(titlebar, sidebar)
for combo, fn in sidebar.shortcuts():
    page.on_shortcut(combo, fn)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
