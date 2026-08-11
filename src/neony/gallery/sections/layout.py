"""Layout and Typography sections."""

from __future__ import annotations

from neony.application.elements import Button, Flex, Heading, HStack, Spacer, Text
from neony.dom import Div, Styles

from ..core import Section

# ── tab: layout ──────────────────────────────────────────────────

# HStack: row layout with a Spacer pushing the button to the right
row_example = HStack(
    Text("Title", weight="600"),
    Spacer(),
    Button("Edit", variant="ghost"),
    gap="8px",
)

# Flex: full control (wrap demo)
wrap_example = Flex(
    *[Button(f"Item {i}", variant="ghost") for i in range(6)],
    direction="row",
    wrap="wrap",
    gap="8px",
)

layout_panel = Section(
    "Layout",
    "HStack rows with Spacer pushing content; Flex gives full control, "
    "including wrapping. VStack stacks vertically, Separator divides, "
    "GlassPanel frosts.",
    """HStack(Text("Title"), Spacer(), Button("Edit"), gap="8px")
Flex(*items, direction="row", wrap="wrap", gap="8px")
VStack(a, b, gap="12px")
Separator()
GlassPanel("Frosted", role="accent")""",
    row_example,
    wrap_example,
)

# ── tab: typography ──────────────────────────────────────────────

# user_select demo: text that cannot be selected, next to normal text.
noselect = Div(
    styles=Styles(user_select="none", opacity="0.7"),
    container=[Text("Locked copy — user_select='none' blocks selection.", role="secondary").build()],
)

typography_panel = Section(
    "Typography",
    "Six heading levels plus semantic text roles that follow the theme. "
    "user_select controls text selection: the first row below cannot be "
    "highlighted, the second can.",
    """Heading("Title", level=1)   # level 1-6
Text("Body copy")
Text("Muted copy", role="secondary")
Text("Danger", role="danger")
Text("OK", role="success")
Div(styles=Styles(user_select="none"), ...)""",
    Heading("Heading 1", level=1),
    Heading("Heading 2", level=2),
    Heading("Heading 3", level=3),
    Heading("Heading 4", level=4),
    Heading("Heading 5", level=5),
    Heading("Heading 6", level=6),
    Text("Primary text — the default body copy."),
    Text("Secondary text — muted, less important.", role="secondary"),
    Text("Danger text — errors and destructive emphasis.", role="danger"),
    Text("Success text — confirmations.", role="success"),
    noselect,
    Text("Selectable copy — the normal default."),
)

PANELS = {"layout": layout_panel, "type": typography_panel}
