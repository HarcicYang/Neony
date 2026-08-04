#!/usr/bin/env python3
"""CustomWindow demo — frameless window with TitleBar + Sidebar chrome.

A decorated-less, transparent window (600x480) whose chrome is drawn by
Neony itself: a glass TitleBar on top and a glass Sidebar on the left,
seamlessly joined into one unit.  Window controls are fully managed by
the TitleBar (``data-window-action`` → WindowControls bridge); the
sidebar switches the content pane; the background image shows through
the frosted surfaces.

Usage:
    python demo_custom_window.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    Button,
    GlassPanel,
    Heading,
    HStack,
    Sidebar,
    SidebarItem,
    Text,
    TitleBar,
    VStack,
)
from neony.dom import Div, DomEvent, Styles

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

sidebar = Sidebar(
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    SidebarItem("Stats", icon="📊"),
    active_key="home",
)

# ── content panes ────────────────────────────────────────────────

theme_btn = Button("Toggle Theme", variant="ghost")

_MODE_LABELS = {"dark": "Light mode", "light": "Deep Blue mode", "deep-blue": "Dark mode"}


async def on_theme_click(event: DomEvent) -> None:
    app.theme.toggle()
    await app.sync_theme()
    theme_btn.label = _MODE_LABELS[app.theme.mode]


theme_btn.on_click(on_theme_click)

# The background image lives inside each pane's GlassPanel — it never
# sits under the titlebar/sidebar chrome, which stay transparent so the
# desktop shows through the frosted frame.
panes = {
    "home": GlassPanel(
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
    ),
    "settings": GlassPanel(
        Heading("Settings", level=2),
        Text("Placeholder for settings — this pane swaps in via Sidebar.on_change.", role="secondary"),
        gap="16px",
        padding="24px",
        background=_BACKGROUND_URL,
        radius="0px",
        grow=True,
    ),
    "stats": GlassPanel(
        Heading("Stats", level=2),
        Text("Placeholder for statistics.", role="secondary"),
        gap="16px",
        padding="24px",
        background=_BACKGROUND_URL,
        radius="0px",
        grow=True,
    ),
}

# Scrolling container for the active pane (the GlassPanel carries its
# own background image). min-height:0 lets it shrink to its allotted
# height so overflow actually scrolls.
content_holder = Div(styles=Styles(flex_grow="1", min_height="0", overflow="auto"))

# build() once per pane — a component's root mounts exactly once, so
# switching reuses the cached root instead of rebuilding it.
pane_roots = {k: p.build() for k, p in panes.items()}


def switch_pane(key: str) -> None:
    content_holder.container = [pane_roots.get(key, pane_roots["home"])]


switch_pane("home")
sidebar.on_change(lambda e: switch_pane(e.value))

# ── assemble: TitleBar / (Sidebar + content) — no gaps, one frame ─
# fill=True stretches the page to the window; the VStack grows to fill
# it, and the inner HStack grows to fill the space below the titlebar —
# only then does the Sidebar (stretched via align="stretch") reach the
# window's bottom edge.

# radius rounds the whole window frame (the chrome stack is clipped to
# it); the sidebar's own corner_radius rounds the inner join.
page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
page.add(
    VStack(
        titlebar,
        HStack(sidebar, content_holder, gap="0px", align="stretch", grow=1),
        gap="0px",
        align="stretch",
        grow=1,
    )
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
