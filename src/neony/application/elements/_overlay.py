"""Internal portal host for global floating layers."""

from __future__ import annotations

from neony.dom import Div, DOMElement, Styles

PORTAL_ATTR = "data-neony-portal"


def mark_portal(element: DOMElement) -> DOMElement:
    element.args = {**element.args, PORTAL_ATTR: "true"}
    return element


class OverlayHost:
    """A per-page DOM host outside transformed or clipped content."""

    def __init__(self) -> None:
        self.root = Div(
            styles=Styles(position="relative", width="100%"),
            args={"data-neony-overlay-host": "true"},
        )

    def attach(self, element: DOMElement) -> None:
        self.root.container.append(element)


def extract_portals(node: DOMElement, host: OverlayHost) -> None:
    """Move marked portal roots from *node* into *host* recursively."""
    for child in tuple(node.container):
        if not isinstance(child, DOMElement):
            continue
        if child.args.get(PORTAL_ATTR) == "true":
            node.container.remove(child)
            host.attach(child)
        extract_portals(child, host)
