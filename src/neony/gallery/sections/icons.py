"""Built-in icon catalog gallery section."""

from __future__ import annotations

from neony.application import icons
from neony.application.elements import Card, Icon, Text, VStack
from neony.dom import Div, DOMElement, Styles

from ..core import Section
from ..i18n import tr


def _public_icon_names() -> tuple[str, ...]:
    """Return every public Icon declared by the typed stub, in declaration order."""
    return tuple(
        name for name, value in vars(type(icons)).items() if not name.startswith("_") and isinstance(value, Icon)
    )


_ICON_NAMES = _public_icon_names()


def _tile(name: str) -> Card:
    """One fixed-size icon specimen with its public stub path."""
    return Card(
        VStack(
            getattr(icons, name).render("24px"),
            Text(f"icons.{name}", size="11px", role="secondary"),
            gap="6px",
            align="center",
        ),
        padding="12px 8px",
        radius="10px",
    )


def _icon_grid(names: tuple[str, ...]) -> DOMElement:
    """Responsive GridView-style catalog built from every public stub entry."""
    return Div(
        styles=Styles(
            display="grid",
            grid_template_columns="repeat(auto-fit, minmax(116px, 1fr))",
            gap="8px",
            width="100%",
        ),
        container=[_tile(name).build() for name in names],
    )


icons_panel = Section(
    tr.icons.title,
    tr.icons.blurb,
    """from neony.application import icons
from neony.application.elements import Button, SidebarItem

Button("Save", icon=icons.check)
SidebarItem("Home", icon=icons.home)

# The gallery grid is generated from every public icons stub entry.
# The semantic catalog keeps one bundled font, fixed geometry, and the
# component's current theme colour. Use Icon.image(...) or Icon.glyph(...)
# only for explicit custom content.""",
    _icon_grid(_ICON_NAMES),
)

PANELS = {"icons": icons_panel}
