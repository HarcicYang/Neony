"""Layout and Typography sections."""

from __future__ import annotations

from neony.application.elements import Button, Flex, Heading, HStack, Spacer, Text
from neony.dom import Div, Styles

from ..core import Section
from ..i18n import tr, tr_now

# ── tab: layout ──────────────────────────────────────────────────

# HStack: row layout with a Spacer pushing the button to the right
row_example = HStack(
    Text(tr.layout.title, weight="600"),
    Spacer(),
    Button(tr.layout.edit, variant="ghost"),
    gap="8px",
)

# Flex: full control (wrap demo)
wrap_example = Flex(
    *[Button(tr_now(tr.layout.item_fmt).format(i=i), variant="ghost") for i in range(6)],
    direction="row",
    wrap="wrap",
    gap="8px",
)

layout_panel = Section(
    tr.layout.layout_title,
    tr.layout.layout_blurb,
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
    container=[Text(tr.layout.locked_copy, role="secondary").build()],
)

typography_panel = Section(
    tr.layout.type_title,
    tr.layout.type_blurb,
    """Heading("Title", level=1)   # level 1-6
Text("Body copy")
Text("Muted copy", role="secondary")
Text("Danger", role="danger")
Text("OK", role="success")
Div(styles=Styles(user_select="none"), ...)""",
    *[Heading(tr_now(tr.layout.heading_n).format(n=n), level=n) for n in range(1, 7)],  # type: ignore[arg-type]
    Text(tr.layout.primary_text),
    Text(tr.layout.secondary_text, role="secondary"),
    Text(tr.layout.danger_text, role="danger"),
    Text(tr.layout.success_text, role="success"),
    noselect,
    Text(tr.layout.selectable_copy),
)

PANELS = {"layout": layout_panel, "type": typography_panel}
