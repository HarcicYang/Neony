"""Navigation tree — categories → component leaves, from the panels."""

from __future__ import annotations

from neony.application.elements import Icon, Tree, TreeNode

from .sections import PANELS

gallery_tree = Tree(width="220px").children(
    TreeNode("Home", key="home", icon=Icon.glyph("🏠")).panel(PANELS["home"]),
    TreeNode("Buttons", key="buttons", shortcut="Ctrl+1").panel(PANELS["buttons"]),
    TreeNode("Inputs & Forms", key="inputs-forms", expanded=True).children(
        TreeNode("Inputs", key="inputs", shortcut="Ctrl+2").panel(PANELS["inputs"]),
        TreeNode("Checks", key="checks", shortcut="Ctrl+3").panel(PANELS["checks"]),
        TreeNode("Forms", key="forms", shortcut="Ctrl+4").panel(PANELS["forms"]),
    ),
    TreeNode("Layout & Type", key="layout-type").children(
        TreeNode("Layout", key="layout").panel(PANELS["layout"]),
        TreeNode("Type", key="type").panel(PANELS["type"]),
    ),
    TreeNode("Glass & Content", key="glass-content").children(
        TreeNode("Glass", key="glass").panel(PANELS["glass"]),
        TreeNode("Content", key="content").panel(PANELS["content"]),
        TreeNode("Icon", key="icon").panel(PANELS["icon"]),
    ),
    TreeNode("Interaction & Events", key="interaction").children(
        TreeNode("Events", key="events").panel(PANELS["events"]),
        TreeNode("Drop", key="drop").panel(PANELS["drop"]),
        TreeNode("Clipboard", key="clipboard").panel(PANELS["clipboard"]),
        TreeNode("Shortcuts", key="shortcuts").panel(PANELS["shortcuts"]),
        TreeNode("Overlays", key="overlays").panel(PANELS["overlays"]),
    ),
    TreeNode("Data views", key="data-views").children(
        TreeNode("List", key="list").panel(PANELS["list"]),
        TreeNode("DataTable", key="datatable").panel(PANELS["datatable"]),
    ),
    TreeNode("Notifications & Chat", key="notify-chat").children(
        TreeNode("Notifications", key="notifications").panel(PANELS["notifications"]),
        TreeNode("Chat", key="chat").panel(PANELS["chat"]),
    ),
    TreeNode("System & Advanced", key="system").children(
        TreeNode("Animations", key="animations").panel(PANELS["animations"]),
        TreeNode("Reactive", key="reactive").panel(PANELS["reactive"]),
        TreeNode("Sidebar", key="sidebar").panel(PANELS["sidebar"]),
        TreeNode("Tabs", key="tabs").panel(PANELS["tabs"]),
        TreeNode("Window", key="window").panel(PANELS["window"]),
    ),
)
gallery_tree.selected_key = "home"
