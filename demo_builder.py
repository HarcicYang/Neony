#!/usr/bin/env python3
"""Builder demo — a small app built from a Page and components.

The page container centers its child, and the fluent ``add`` API assembles
all content without exposing the native window or document builders.
"""

from neony.application import Page, launch
from neony.application.elements import Heading, Text, VStack
from neony.dom import Color, Div, Styles

disc = Div(
    container=["Hello!"],
    styles=Styles(
        color=Color(var="--color-text-primary"),
        background_color=Color(var="--color-accent"),
        width="100px",
        height="100px",
        display="flex",
        justify_content="center",
        align_items="center",
        border_radius="50px",
    ),
)

page = Page(fill=True, justify="center", align="center", max_width="100%").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("Built with Page and components.", role="secondary"),
        disc,
        gap="16px",
        align="center",
    )
)

launch(page, title="Hello Neony!", width=900, height=640, devtools=True)
