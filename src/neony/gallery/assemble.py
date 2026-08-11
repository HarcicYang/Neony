"""Page assembly — create the page, apply section hooks, build the chrome."""

from __future__ import annotations

from neony.application import Page
from neony.application.elements import Icon, TitleBar, VStack
from neony.application.theme import stub
from neony.dom import Div, Styles

from .core import _ICON_URL, app, header
from .sections import PAGE_HOOKS
from .tree import gallery_tree

# Window-level lifecycle + key events and the overlays mounted at the
# page root are wired by section PAGE_HOOKS (each section owns its
# handlers); assembly only creates the bare page.
page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
for hook in PAGE_HOOKS:
    hook(page)

titlebar = TitleBar("Neony — Component Gallery", icon=Icon.image(_ICON_URL))

# The content stage uses the plain theme background — only the titlebar
# above it stays transparent, so the desktop shows through the chrome
# while the docs/text get a solid, readable backdrop.  Must be a flex
# column: a bare block Div ignores flex-grow, so its height = content
# height and the tree pushes the whole page open (no bounded stage, no
# internal tree scroll).
content = Div(
    styles=Styles(
        display="flex",
        flex_direction="column",
        flex_grow="1",
        min_height="0",
        overflow="auto",
        background_color=stub.bg,
    ),
    # grow=1: the header + tree column must be a flex item with the
    # tree's allocated height (the tree self-bounds via flex-grow +
    # min-height:0, but an auto-height parent gives it nothing to grow
    # into — without grow=1 the tree pushes the stage open).
    container=[VStack(header, gallery_tree, gap="16px", padding="24px", grow=1).build()],
)

# grow=1 makes the chrome stack fill the window; the content stage then
# grows to fill the space below the titlebar.
page.add(VStack(titlebar, content, gap="0px", grow=1))


def main() -> None:
    app.run(page)
