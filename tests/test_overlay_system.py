"""P2 overlay-host contracts."""

from neony.application import Page
from neony.application.elements import Dialog, Menu, Text, Toast
from neony.dom import DOMElement


def _walk(node: DOMElement):
    yield node
    for child in node.container:
        if isinstance(child, DOMElement):
            yield from _walk(child)


def test_page_moves_global_overlays_into_internal_host():
    dialog = Dialog(content=Text("Body"))
    menu = Menu("Rename")
    toast = Toast()
    page = Page()
    page.add(dialog, menu, toast, Text("Content"))

    root = page.build()
    host = next(node for node in _walk(root) if node.args.get("data-neony-overlay-host") == "true")
    content = root.container[0]
    assert isinstance(content, DOMElement)

    assert dialog._root in host.container
    assert menu._root in host.container
    assert toast._root in host.container
    assert dialog._root not in content.container
    assert menu._root not in content.container
    assert toast._root not in content.container


def test_nested_portals_become_host_siblings_for_clipping_safety():
    menu = Menu("Rename")
    dialog = Dialog(content=menu)
    page = Page().add(dialog)

    root = page.build()
    host = next(node for node in _walk(root) if node.args.get("data-neony-overlay-host") == "true")

    assert dialog._root in host.container
    assert menu._root in host.container
    assert menu._root._parent is host
