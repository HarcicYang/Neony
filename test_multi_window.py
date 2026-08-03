#!/usr/bin/env python3
"""Multi-window demo — two windows sharing one app state.

Both windows run in the same LumiView event loop and reference the same
``app.state`` namespace. Buttons in the counter window bump the count;
the display window shows it. Any window's event handler mutates shared
state, and only the originating window re-renders.

Usage:
    python test_multi_window.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import Button, Heading, HStack, Text, VStack
from neony.dom import DomEvent

app = NeonApplication(
    Config(
        window=WindowConfig(title="Neony — Multi Window", width=360, height=240),
        webview=WebViewConfig(devtools=True),
    )
)

app.state.count = 0

# ── window 0: counter ────────────────────────────────────────────

count_label = Text("0", weight="600")


def refresh() -> None:
    count_label.text = str(app.state.count)


plus_btn = Button("+1")
minus_btn = Button("-1", variant="ghost")


async def on_plus(event: DomEvent) -> None:
    app.state.count += 1
    refresh()


async def on_minus(event: DomEvent) -> None:
    app.state.count -= 1
    refresh()


plus_btn.on_click(on_plus)
minus_btn.on_click(on_minus)

page_one = Page(gap="16px").add(
    VStack(
        Heading("Counter", level=2),
        count_label,
        HStack(plus_btn, minus_btn, gap="8px"),
        gap="12px",
    )
)

# ── window 1: display ────────────────────────────────────────────

display = Text("0", size="28px", weight="700")


async def refresh_display(event: DomEvent) -> None:
    display.text = str(app.state.count)


refresh_btn = Button("Refresh", variant="ghost")
refresh_btn.on_click(refresh_display)

page_two = Page(gap="16px").add(
    VStack(
        Heading("Display", level=2),
        Text("Count (shared state):", role="secondary"),
        display,
        refresh_btn,
        gap="12px",
    )
)

# ── ready: give the second window its own title ──────────────────


async def on_ready() -> None:
    await app.set_title("Neony — Counter", window_index=0)
    await app.set_title("Neony — Display", window_index=1)


app.ready_handler = on_ready


def main() -> None:
    app.run(page_one, page_two)


if __name__ == "__main__":
    main()
