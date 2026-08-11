"""Notifications and Chat sections.

Exports ``PAGE_HOOKS`` to mount the Toast overlay layer at the page root.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from neony.application.elements import (
    Avatar,
    Button,
    Dropdown,
    HStack,
    Icon,
    MessageBubble,
    NoticeBubble,
    Spacer,
    Text,
    Toast,
    VStack,
)
from neony.dom import DomEvent

from ..core import Section

if TYPE_CHECKING:
    from neony.application import Page

# ── Notifications: Toast ─────────────────────────────────────────

toast = Toast(placement="top-right", duration=2.5, max_toasts=4, top_offset="40px")  # clear the 40px TitleBar

toast_placement = Dropdown(
    "top-right",
    items=[
        ("top-left", "top-left"),
        ("top-center", "top-center"),
        ("top-right", "top-right"),
        ("bottom-left", "bottom-left"),
        ("bottom-center", "bottom-center"),
        ("bottom-right", "bottom-right"),
    ],
)
toast_placement.on_change(lambda e: setattr(toast, "placement", e.value))

toast_echo = Text("", role="secondary")


def show_success(_event: DomEvent) -> None:
    toast.show("File saved successfully", type="success", on_click=lambda: setattr(toast_echo, "text", "toast clicked"))


toast_ok = Button("Success")
toast_ok.on_click(show_success)
toast_info = Button("Info", variant="ghost")
toast_info.on_click(lambda _e: toast.show("Update available", type="info"))
toast_err = Button("Error", variant="danger")
toast_err.on_click(lambda _e: toast.show("Connection lost — retrying…", type="error"))
toast_clear = Button("Clear", variant="ghost")
toast_clear.on_click(lambda _e: toast.clear())

notifications_panel = Section(
    "Notifications",
    "Transient in-app notifications stacked at a screen edge. The host "
    "sits at the page root as a full-viewport layer (z-index 1100, "
    "pointer-events none); cards enter and leave with an animation "
    "tied to their placement — top ones drop in, bottom ones rise up, "
    "corners slide diagonally — and auto-dismiss after `duration`. "
    "A card is clickable when `on_click` is passed (the ✕ never fires it).",
    """toast = Toast(placement="top-right", duration=3.0, top_offset="40px")
page.add(toast)                              # mount once at the page root
toast.show("File saved", type="success")     # success / info / error
toast.show("Update available", type="info", duration=5.0,
           on_click=fn)                      # click the card (✕ excluded)
toast.placement = "bottom-left"              # relocate the stack live
toast.clear()                                # remove everything""",
    HStack(Text("Placement", weight="600"), Spacer(), toast_placement, gap="8px"),
    HStack(toast_ok, toast_info, toast_err, toast_clear, gap="8px"),
    toast_echo,
)

# ── Chat: MessageBubble / NoticeBubble ───────────────────────────

chat_echo = Text("", role="secondary")


def on_chat_menu(e: DomEvent) -> None:
    chat_echo.text = f"menu: {e.value}"


def on_chat_action(value: str) -> None:
    chat_echo.text = f"action: {value}"


other_msg = MessageBubble(
    "Hey! Have you seen the new gallery?",
    avatar=Avatar(name="Ada"),
    name="Ada",
    actions=[("copy", "Copy"), Icon.glyph("😊")],
)
other_msg.on_change(on_chat_menu)
other_msg.on_action(on_chat_action)

me_msg = MessageBubble(
    "Just shipped it — three new components.",
    from_me=True,
    actions=[("copy", "Copy")],
)
me_msg.on_change(on_chat_menu)
me_msg.on_action(on_chat_action)

chat_panel = Section(
    "Chat",
    "QQ/Telegram-style message bubbles and the centered system notice. "
    "`from_me` flips alignment (right, accent fill) vs. others (left, "
    "raised surface); an optional avatar sits on the message's side. "
    "Right-click a bubble for its built-in menu, hover it for quick "
    "actions.",
    """other = MessageBubble("Hey!", avatar=Avatar(name="Ada"), name="Ada",
                        actions=[("reply", "Reply")])
me    = MessageBubble("Hi!", from_me=True)    # right-aligned accent bubble
notice = NoticeBubble("You joined the group") # centered system pill
other.on_change(lambda e: ...)   # right-click menu selection (e.value)
other.on_action(lambda v: ...)   # quick action click (v)""",
    VStack(
        Text("Right-click a bubble for its menu; hover for quick actions.", role="secondary"),
        other_msg,
        me_msg,
        NoticeBubble("You joined the group"),
        chat_echo,
        gap="8px",
        align="stretch",
    ),
)

PANELS = {"notifications": notifications_panel, "chat": chat_panel}


def _wire_toast(page: Page) -> None:
    # Toast is a full-viewport fixed layer (z-index 1100, pointer-events
    # none) — mount it at the page root so no ancestor transform can
    # hijack `position: fixed` in WebKit.
    page.add(toast)


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire_toast]
