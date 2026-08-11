"""Home panel — shown until a tree leaf is selected."""

from __future__ import annotations

from neony.application.elements import Heading, Text, VStack

home_panel = VStack(
    Heading("Welcome", level=3),
    Text(
        "This gallery is organized as a tree: pick a category on the "
        "left, expand it, and select a component to see its docs and "
        "live demos here. Every section pairs a demo with the Python "
        "snippet that produced it, so the gallery doubles as a reference.",
        role="secondary",
    ),
    gap="12px",
)

PANELS = {"home": home_panel}
