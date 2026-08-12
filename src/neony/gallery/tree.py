"""Navigation tree — categories → component leaves, from the panels."""

from __future__ import annotations

from neony.application.elements import Icon, Tree, TreeNode

from .i18n import tr
from .sections import PANELS

gallery_tree = Tree(width="220px").children(
    TreeNode(tr.nav.home, key="home", icon=Icon.glyph("🏠")).panel(PANELS["home"]),
    TreeNode(tr.nav.buttons, key="buttons", shortcut="Ctrl+1").panel(PANELS["buttons"]),
    TreeNode(tr.nav.inputs_forms, key="inputs-forms", expanded=True).children(
        TreeNode(tr.nav.inputs, key="inputs", shortcut="Ctrl+2").panel(PANELS["inputs"]),
        TreeNode(tr.nav.checks, key="checks", shortcut="Ctrl+3").panel(PANELS["checks"]),
        TreeNode(tr.nav.forms, key="forms", shortcut="Ctrl+4").panel(PANELS["forms"]),
    ),
    TreeNode(tr.nav.layout_type, key="layout-type").children(
        TreeNode(tr.nav.layout, key="layout").panel(PANELS["layout"]),
        TreeNode(tr.nav.type, key="type").panel(PANELS["type"]),
    ),
    TreeNode(tr.nav.glass_content, key="glass-content").children(
        TreeNode(tr.nav.glass, key="glass").panel(PANELS["glass"]),
        TreeNode(tr.nav.content, key="content").panel(PANELS["content"]),
        TreeNode(tr.nav.icon, key="icon").panel(PANELS["icon"]),
    ),
    TreeNode(tr.nav.interaction, key="interaction").children(
        TreeNode(tr.nav.events, key="events").panel(PANELS["events"]),
        TreeNode(tr.nav.drop, key="drop").panel(PANELS["drop"]),
        TreeNode(tr.nav.clipboard, key="clipboard").panel(PANELS["clipboard"]),
        TreeNode(tr.nav.shortcuts, key="shortcuts").panel(PANELS["shortcuts"]),
        TreeNode(tr.nav.overlays, key="overlays").panel(PANELS["overlays"]),
    ),
    TreeNode(tr.nav.data_views, key="data-views").children(
        TreeNode(tr.nav.list, key="list").panel(PANELS["list"]),
        TreeNode(tr.nav.datatable, key="datatable").panel(PANELS["datatable"]),
        TreeNode(tr.nav.reorder, key="reorder").panel(PANELS["reorder"]),
    ),
    TreeNode(tr.nav.notify_chat, key="notify-chat").children(
        TreeNode(tr.nav.notifications, key="notifications").panel(PANELS["notifications"]),
        TreeNode(tr.nav.chat, key="chat").panel(PANELS["chat"]),
    ),
    TreeNode(tr.nav.system, key="system").children(
        TreeNode(tr.nav.animations, key="animations").panel(PANELS["animations"]),
        TreeNode(tr.nav.reactive, key="reactive").panel(PANELS["reactive"]),
        TreeNode(tr.nav.sidebar, key="sidebar").panel(PANELS["sidebar"]),
        TreeNode(tr.nav.tabs, key="tabs").panel(PANELS["tabs"]),
        TreeNode(tr.nav.window, key="window").panel(PANELS["window"]),
        TreeNode(tr.nav.dialogs, key="dialogs").panel(PANELS["dialogs"]),
    ),
)
gallery_tree.selected_key = "home"
