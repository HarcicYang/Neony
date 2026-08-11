"""Home panel — shown until a tree leaf is selected."""

from __future__ import annotations

from neony.application.elements import Heading, Text, VStack

from ..i18n import tr

home_panel = VStack(
    Heading(tr.home.heading, level=3),
    Text(tr.home.body, role="secondary"),
    gap="12px",
)

PANELS = {"home": home_panel}
