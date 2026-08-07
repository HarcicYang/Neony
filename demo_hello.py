#!/usr/bin/env python3
"""Hello demo — the smallest reactive Neony application."""

from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack
from neony.dom import Signal

clicks = Signal(0)
# The rendered label is driven by the signal; this demo never reads back
# Button.label, so bind_text is the appropriate concise presentation API.
counter = Button("Click me")
counter.bind_text(clicks, fmt=lambda count: f"Clicked {count} times!" if count else "Click me")
counter.on_click(lambda _event: clicks.update(lambda count: count + 1))

page = Page(gap="16px").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("Build desktop UI in pure Python.", role="secondary"),
        counter,
        gap="12px",
    )
)

launch(page, title="My App", width=480, height=360, devtools=True)
