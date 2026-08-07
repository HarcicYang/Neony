#!/usr/bin/env python3
"""Tree demo — collapsible navigation tree + content host.

A frameless, transparent window (760x560) with a glass TitleBar.  The
Tree lives in a frosted GlassPanel stage: the tree rail on the left,
its content host on the right.  Clicking a leaf shows its panel there
(Home is selected by default); branches expand / collapse.

Usage:
    python demo_tree.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    GlassPanel,
    Heading,
    Icon,
    Text,
    TitleBar,
    Tree,
    TreeNode,
    VStack,
)

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Tree",
            width=760,
            height=560,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)


def _leaf_panel(title: str, blurb: str) -> GlassPanel:
    return GlassPanel(Heading(title, level=3), Text(blurb, role="secondary"), grow=True)


home_panel = _leaf_panel("Home", "Pick a component from the tree on the left.")
inputs_panel = _leaf_panel("Inputs", "Text, password and email fields.")
checks_panel = _leaf_panel("Checks", "Checkboxes, switches, radio groups.")
forms_panel = _leaf_panel("Forms", "Selects, combo boxes, sliders.")
layout_panel = _leaf_panel("Layout", "HStack / VStack / Flex / Separator.")
type_panel = _leaf_panel("Type", "Headings and text roles.")

tree = Tree(width="200px").children(
    TreeNode("Home", key="home", icon=Icon.glyph("🏠")).panel(home_panel),
    TreeNode("Forms", key="forms", expanded=True).children(
        TreeNode("Inputs", key="inputs", shortcut="Ctrl+1").panel(inputs_panel),
        TreeNode("Checks", key="checks", shortcut="Ctrl+2").panel(checks_panel),
        TreeNode("Forms", key="forms-sub", shortcut="Ctrl+3").panel(forms_panel),
    ),
    TreeNode("Layout & Type", key="layout-type").children(
        TreeNode("Layout", key="layout").panel(layout_panel),
        TreeNode("Type", key="type").panel(type_panel),
    ),
)
tree.selected_key = "home"

selection_text = Text(f"selected: {tree.selected_key}", role="secondary")
tree.on_change(lambda e: setattr(selection_text, "text", f"selected: {e.value}"))

titlebar = TitleBar("Neony — Tree")
stage = GlassPanel(
    VStack(tree, selection_text, gap="8px", align="stretch", grow=1),
    gap="0px",
    padding="16px",
    radius="0px",
    grow=True,
)
page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px").add(
    VStack(titlebar, stage, gap="0px", align="stretch", grow=1)
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
