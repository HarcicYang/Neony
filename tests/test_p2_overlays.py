"""P2 portal overlays: Popover and Drawer."""

from neony.application import Page
from neony.application.elements import Button, Command, CommandPalette, Drawer, Popover, Text
from neony.dom import DOMElement, DomEvent


def _walk(node: DOMElement):
    yield node
    for child in node.container:
        if isinstance(child, DOMElement):
            yield from _walk(child)


def test_popover_opens_through_layer_manager_and_portals_panel():
    opened: list[Popover] = []
    popover = Popover(Button("Filters"), Text("Filter panel"))
    popover.on_open(opened.append)
    page = Page().add(popover, Text("Content"))
    popover.open = True
    root = page.build()
    host = next(node for node in _walk(root) if node.args.get("data-neony-overlay-host") == "true")

    assert popover.open is True
    assert popover._panel in host.container
    assert popover._panel.args["data-neony-popover-anchor"] == popover._anchor.key
    assert popover._panel.args["data-neony-outside"] == "true"
    assert popover._layer_handle is not None
    assert opened == [popover]

    popover.open = False
    assert popover.open is False
    assert "data-neony-outside" not in popover._panel.args


def test_drawer_uses_modal_focus_contract_and_scrim_close():
    drawer = Drawer(Text("Details"), title="Details", side="right", width="320px")
    assert drawer._root.args["data-neony-portal"] == "true"

    drawer.open = True
    assert drawer._root.styles.display == "flex"
    assert drawer._root.args["data-neony-focus-scope"] == "trap"
    assert drawer._panel.styles.right == "0"
    assert drawer._panel.styles.width == "320px"

    import asyncio

    asyncio.run(
        drawer._on_event(
            "click",
            DomEvent(key=drawer._scrim.key, type="click", source="user"),
        )
    )
    assert drawer.open is False


def test_popover_outsideclick_closes():
    import asyncio

    popover = Popover(Button("Open"), Text("Body"))
    popover.open = True
    asyncio.run(
        popover._on_event(
            "outsideclick",
            DomEvent(key=popover._panel.key, type="outsideclick", source="user"),
        )
    )
    assert popover.open is False


def test_command_palette_filters_keyboard_selects_and_exposes_hotkey():
    changed: list[str] = []
    palette = CommandPalette(
        Command("open", "Open file", keywords=("document",), shortcut="Ctrl+O"),
        Command("theme", "Change theme"),
        Command("delete", "Delete file", disabled=True),
        hotkey="Ctrl+K",
    )
    palette.on_change(lambda event: changed.append(event.value))
    page = Page().add(palette)
    root = page.build()
    host = next(node for node in _walk(root) if node.args.get("data-neony-overlay-host") == "true")

    assert palette._root in host.container
    assert palette.shortcuts()[0][0] == "Ctrl+K"

    palette.open = True
    palette.query = "theme"
    assert [command.value for command in palette._filtered] == ["theme"]

    import asyncio

    asyncio.run(palette._on_keydown(DomEvent(key=palette._input.control_element.key, type="keydown", value="Enter")))
    assert changed == ["theme"]
    assert palette.open is False
