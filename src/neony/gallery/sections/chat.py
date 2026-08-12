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
from ..i18n import tr, tr_now

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
    toast.show(
        tr_now(tr.chat.toast_saved),
        type="success",
        on_click=lambda: setattr(toast_echo, "text", tr_now(tr.chat.toast_clicked)),
    )


toast_ok = Button(tr.chat.toast_success)
toast_ok.on_click(show_success)
toast_info = Button(tr.chat.toast_info, variant="ghost")
toast_info.on_click(lambda _e: toast.show(tr_now(tr.chat.toast_update), type="info"))
toast_err = Button(tr.chat.toast_error, variant="danger")
toast_err.on_click(lambda _e: toast.show(tr_now(tr.chat.toast_connection), type="error"))
toast_clear = Button(tr.chat.toast_clear, variant="ghost")
toast_clear.on_click(lambda _e: toast.clear())

notifications_panel = Section(
    tr.chat.notifications_title,
    tr.chat.notifications_blurb,
    """toast = Toast(placement="top-right", duration=3.0, top_offset="40px")
page.add(toast)                              # mount once at the page root
toast.show("File saved", type="success")     # success / info / error
toast.show("Update available", type="info", duration=5.0,
           on_click=fn)                      # click the card (✕ excluded)
toast.placement = "bottom-left"              # relocate the stack live
toast.clear()                                # remove everything""",
    HStack(Text(tr.chat.placement, weight="600"), Spacer(), toast_placement, gap="8px"),
    HStack(toast_ok, toast_info, toast_err, toast_clear, gap="8px"),
    toast_echo,
)

# ── Chat: MessageBubble / NoticeBubble ───────────────────────────

chat_echo = Text("", role="secondary")


def on_chat_menu(e: DomEvent) -> None:
    chat_echo.text = tr_now(tr.chat.menu_fmt).format(value=e.value)


def on_chat_action(value: str) -> None:
    chat_echo.text = tr_now(tr.chat.action_fmt).format(value=value)


other_msg = MessageBubble(
    tr.chat.other_msg,
    avatar=Avatar(name="Sherry"),
    name="Sherry",
    actions=[("copy", tr.chat.copy_text), Icon.glyph("😊")],
)
other_msg.on_change(on_chat_menu)
other_msg.on_action(on_chat_action)

me_msg = MessageBubble(
    tr.chat.me_msg,
    from_me=True,
    actions=[("copy", tr.chat.copy_text)],
)
me_msg.on_change(on_chat_menu)
me_msg.on_action(on_chat_action)

chat_panel = Section(
    tr.chat.chat_title,
    tr.chat.chat_blurb,
    """other = MessageBubble("Hey!", avatar=Avatar(name="Sherry"), name="Sherry",
                        actions=[("reply", "Reply")])
me    = MessageBubble("Hi!", from_me=True)    # right-aligned accent bubble
notice = NoticeBubble("You joined the group") # centered system pill
other.on_change(lambda e: ...)   # right-click menu selection (e.value)
other.on_action(lambda v: ...)   # quick action click (v)""",
    VStack(
        Text(tr.chat.right_click_hint, role="secondary"),
        other_msg,
        me_msg,
        NoticeBubble(tr.chat.you_joined),
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
