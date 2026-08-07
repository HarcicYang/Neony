#!/usr/bin/env python3
"""Accordion demo — expandable sections in a transparent frameless window.

A frameless, transparent window (480x640) with a glass TitleBar; the
accordion lives in a frosted GlassPanel that fills the stage, so the
desktop shows through the transparent chrome around it.

Usage:
    python demo_accordion.py
"""

from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig
from neony.application.elements import (
    Accordion,
    Button,
    GlassPanel,
    Heading,
    Text,
    TitleBar,
    VStack,
)

app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony — Accordion",
            width=480,
            height=640,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)


def _open_label(keys: list[str]) -> str:
    return ", ".join(keys) if keys else "(none)"


accordion = (
    Accordion(multiple=True)
    .section("Inputs & Forms", Text("Text fields, checkboxes, forms."), expanded=True)
    .section("Layout & Type", Text("Flex stacks, separators, headings."))
    .section("Glass & Content", Text("Cards, avatars, badges, glass panels."), expanded=True)
)

open_text = Text(_open_label(accordion.expanded_keys), role="secondary")
last_text = Text("—", role="secondary")


def _refresh(_event=None) -> None:
    open_text.text = _open_label(accordion.expanded_keys)


def _on_change(event) -> None:
    last_text.text = event.value
    open_text.text = _open_label(accordion.expanded_keys)


accordion.on_change(_on_change)


def _collapse_all(_event=None) -> None:
    accordion.expanded_keys = []
    _refresh()


collapse_btn = Button("Collapse all").on_click(_collapse_all)

footer = VStack(Heading("State", level=4), open_text, last_text, collapse_btn, gap="8px")

stage = GlassPanel(
    accordion,
    footer,
    gap="16px",
    padding="20px",
    radius="0px",
    grow=True,
)

titlebar = TitleBar("Neony — Accordion")
page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px").add(
    VStack(titlebar, stage, gap="0px", align="stretch", grow=1)
)


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
