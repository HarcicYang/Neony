#!/usr/bin/env python3
"""Multi-window demo — two windows sharing one app state.

Both windows run in the same LumiView event loop and share a
``SharedSignal``: a write in the counter window propagates to every
window whose tree binds it, each through its own render request — no
manual refresh calls anywhere.  State stays a plain dataclass here
(``NeonApplication`` accepts any object via ``state=``), carrying the
non-reactive bits.

Usage:
    python demo_multi_window.py
"""

from dataclasses import dataclass

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import Button, Heading, HStack, Text, VStack
from neony.dom import SharedSignal


@dataclass
class AppState:
    """Typed non-reactive state — shared by reference across windows."""

    name: str = "neony"


app = NeonApplication(
    Config(
        window=WindowConfig(title="Neony — Multi Window", width=360, height=240),
        webview=WebViewConfig(devtools=True),
    ),
    state=AppState(),
)

# One signal for the whole app: both windows bind to it, so a write
# anywhere re-renders every window that displays it.
count = SharedSignal(0)

# ── window 0: counter ────────────────────────────────────────────

count_label = Text("0", weight="600")
count_label.bind_text(count)

plus_btn = Button("+1")
minus_btn = Button("-1", variant="ghost")

# The +1 button also writes the typed state — signals and dataclass
# state happily coexist.
plus_btn.on_click(lambda _e: count.update(lambda c: c + 1))
minus_btn.on_click(lambda _e: count.update(lambda c: c - 1))

page_one = Page(gap="16px").add(
    VStack(
        Heading(f"Counter ({app.state.name})", level=2),
        count_label,
        HStack(plus_btn, minus_btn, gap="8px"),
        gap="12px",
    )
)

# ── window 1: display — auto-syncs, no refresh button ─────────────

display = Text("0", size="28px", weight="700")
display.bind_text(count)

page_two = Page(gap="16px").add(
    VStack(
        Heading("Display", level=2),
        Text("Cross-window SharedSignal — updates land automatically:", role="secondary"),
        display,
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
