#!/usr/bin/env python3
"""Builder demo — a small app built from a Page and components.

The page container centers its child, and the fluent ``add`` API assembles
all content without exposing the native window or document builders.
"""

from neony.application import Page, launch
from neony.application.elements import Heading, Text
from neony.application.theme import stub
from neony.dom import Div, Styles

disc = Div(
    container=["Hello!"],
    styles=Styles(
        color=stub.text_primary,
        background_color=stub.accent,
        width="100px",
        height="100px",
        display="flex",
        justify_content="center",
        align_items="center",
        border_radius="50px",
    ),
)

page = Page(fill=True, justify="center", align="center", max_width="100%").add(
    Heading("Hello, Neony", level=1), Text("Built with Page and components.", role="secondary")
)

launch(page, title="Hello Neony!", width=900, height=640, devtools=True)
