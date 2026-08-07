#!/usr/bin/env python3
"""Close-to-tray demo — system tray with a native menu (lumiview .dev4).

- Close the window → the app hides to the tray instead of quitting.
- Right-click the tray icon for the menu (Show / Quit); left-click
  toggles the window (``menu_on_left_click=False`` frees the left
  button for ``on_left_click``).
- Restore from the tray menu, a left click, or (on macOS) a Dock click.

Linux needs libayatana-appindicator; the tooltip is unsupported there.

Usage:
    python demo_tray.py
"""

from neony.application import Config, NeonApplication, Page, Tray, TrayItem, WebViewConfig, WindowConfig
from neony.application.elements import Button, Text, VStack
from neony.dom import Signal

app = NeonApplication(
    Config(
        window=WindowConfig(title="Neony — Tray Demo", width=420, height=260),
        webview=WebViewConfig(devtools=True),
    )
)

status = Text("", role="secondary")
message = Signal("Close the window — the app hides to the tray.")
status.bind_text(message)
hidden = Signal(True)


async def on_show(_event) -> None:
    await app.show()
    await app.focus()
    hidden.set(False)
    message.set("Shown from the tray menu")


async def on_quit(_event) -> None:
    # close() would be intercepted by close_to_tray (hide); exit() is
    # the real way out.
    app.exit()


def make_icon() -> tuple[bytes, int, int]:
    """32x32 RGBA icon: a filled accent-ish circle on transparent —
    no asset file needed.  Keeping this zero-asset form avoids adding a
    binary file solely for a demo icon.
    """
    size, cx, cy, r = 32, 15.5, 15.5, 13
    rgba = bytearray()
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                rgba += bytes((90, 130, 210, 255))
            else:
                rgba += bytes((0, 0, 0, 0))
    return bytes(rgba), size, size


async def on_tray_left_click(_event) -> None:
    """Left-click toggles the window (menu_on_left_click=False)."""
    if hidden():
        await app.show()
        await app.focus()
        hidden.set(False)
        message.set("Shown from the tray (left click)")
    else:
        await app.hide()
        hidden.set(True)
        message.set("Hidden to tray (left click)")


tray = Tray(
    icon=make_icon(),
    tooltip="Neony Tray Demo",
    items=[
        TrayItem("Show Window", id="show", on_activate=on_show),
        TrayItem.separator(),
        TrayItem("Quit", id="quit", accelerator="CmdOrCtrl+Q", on_activate=on_quit),
    ],
    menu_on_left_click=False,
    on_left_click=on_tray_left_click,
    close_to_tray=True,
)
app.tray = tray

page = Page(gap="16px", padding="24px", max_width="100%").add(
    VStack(
        Text("Tray Demo", weight="700", size="18px"),
        status,
        Button("Hide to tray", variant="ghost").on_click(on_tray_left_click),
        gap="12px",
    )
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
