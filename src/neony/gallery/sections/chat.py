"""Notifications and Chat sections.

Exports ``PAGE_HOOKS`` to mount the Toast overlay layer at the page root.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from neony.application import icons
from neony.application.elements import (
    Avatar,
    Button,
    Component,
    Dropdown,
    HStack,
    ImageSegment,
    MessageBubble,
    NoticeBubble,
    RichText,
    ScrollArea,
    Spacer,
    StickToBottom,
    Text,
    TextSegment,
    Toast,
    VStack,
)
from neony.dom import Div, DOMElement, DomEvent, Styles

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
    actions=[("copy", tr.chat.copy_text), icons.favorite],
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

chat_section = Section(
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

# ── RichText editor ─────────────────────────────────────────────

rich_text = RichText(
    segments=[
        TextSegment(text="Try typing here, "),
        ImageSegment(src="https://harcic.is-a.dev/resource/favicon.svg", alt="icon"),
        TextSegment(text=" then keep going."),
    ]
)
rich_text_echo = Text("", role="secondary")


def on_rich_text_change(event: DomEvent) -> None:
    rich_text_echo.text = f"segments: {len(event.value)}"


rich_text.on_change(on_rich_text_change)

rich_text_section = Section(
    tr.chat.rich_text_title,
    tr.chat.rich_text_blurb,
    """editor = RichText(segments=["你好", ImageSegment(src="x.png"), "世界"])
editor.insert_image("y.png", at_caret=True)   # lands at the caret
editor.on_change(lambda e: print(e.value))     # ordered segments
editor.on_submit(lambda e: send())             # Enter (IME-safe)
segments = editor.content()                    # [TextSegment, ImageSegment, ...]""",
    VStack(
        Text(tr.chat.right_click_hint, role="secondary"),
        rich_text,
        rich_text_echo,
        gap="8px",
        align="stretch",
    ),
)

# ── ScrollArea & StickToBottom ───────────────────────────────────


def make_scroll_rows() -> VStack:
    return VStack(
        *[Text(f"message {i}", role="secondary") for i in range(1, 9)],
        gap="8px",
        align="stretch",
    )


def scroll_host(child: Component | DOMElement) -> Div:
    return Div(
        styles=Styles(height="200px", display="flex", flex_direction="column"),
        container=[child],
    )


scroll_section = Section(
    tr.chat.scroll_title,
    tr.chat.scroll_blurb,
    """area = ScrollArea(message_list)              # pure Python scroll API
await area.scroll_to_bottom()                 # top / scroll_to(top)
stick = StickToBottom(message_list)           # chat-stream auto-pin
await stick.scroll_to_bottom(force=True)      # force regardless of pin""",
    VStack(
        scroll_host(ScrollArea(make_scroll_rows()).build()),
        scroll_host(StickToBottom(make_scroll_rows()).build()),
        gap="12px",
        align="stretch",
    ),
)

# ── Streaming text into bubbles ──────────────────────────────────

_STREAM_PLAIN = (
    "Streaming is incremental: each token arrives, the text grows, and only "
    "the new chunk crosses the bridge — the diff detects a pure extension of "
    "the text the browser already shows and sends an append patch. "
)

_STREAM_MD = (
    "## Streaming Markdown\n\n"
    "Rendered **in the webview** while the source streams from Python.\n\n"
    "- headings, lists and tables\n"
    "- `inline code` and fenced blocks\n\n"
    "```python\n"
    "async for token in llm.reply(prompt):\n"
    "    bubble.append_text(token)\n"
    "```\n\n"
    "| path | ships |\n| --- | --- |\n| plain | the chunk |\n| markdown | the source |\n"
)


async def stream_tokens(text: str, *, size: int = 4, delay: float = 0.03):
    """Slice *text* into small chunks with a token-like cadence."""
    for start in range(0, len(text), size):
        yield text[start : start + size]
        await asyncio.sleep(delay)


stream_bubbles = VStack(gap="10px", align="stretch")
stream_status = Text("", role="secondary")
stream_tasks: list[asyncio.Task[None]] = []

# The bubbles live in a definite-height scroll host; without a scrolling
# container the growing stream overflows the fixed box and paints over
# the sections below.  StickToBottom also keeps the newest text in view
# while the user is near the bottom.
stream_host = Div(
    styles=Styles(height="280px", display="flex", flex_direction="column"),
    container=[StickToBottom(stream_bubbles).build()],
)


def _stop_stream_tasks() -> None:
    for task in stream_tasks:
        task.cancel()
    stream_tasks.clear()


async def start_chat_stream(_event: DomEvent | None = None) -> None:
    _stop_stream_tasks()
    stream_bubbles._root.container.clear()
    stream_status.text = ""
    question = MessageBubble(tr_now(tr.chat.streaming_hint), from_me=True)
    stream_bubbles._root.container.append(question.build())

    async def run(plain: bool) -> None:
        bubble = MessageBubble("", name="markdown" if not plain else "plain", markdown=not plain)
        stream_bubbles._root.container.append(bubble.build())
        await bubble.stream(stream_tokens(_STREAM_PLAIN if plain else _STREAM_MD))
        stream_status.text = "done"

    stream_tasks[:] = [asyncio.create_task(run(True)), asyncio.create_task(run(False))]


stream_start_btn = Button(tr.chat.stream_start)
stream_start_btn.on_click(start_chat_stream)
stream_stop_btn = Button(tr.chat.stream_stop, variant="danger")
stream_stop_btn.on_click(lambda _e: _stop_stream_tasks())

stream_section = Section(
    tr.chat.streaming_title,
    tr.chat.streaming_blurb,
    """bubble = MessageBubble("", markdown=True)
async for token in llm.reply(prompt):
    bubble.append_text(token)    # or: await bubble.stream(tokens)
bubble.stop_stream()             # cancel mid-stream""",
    VStack(
        HStack(stream_start_btn, stream_stop_btn, stream_status, gap="8px"),
        stream_host,
        gap="10px",
        align="stretch",
    ),
)

chat_panel = VStack(chat_section, stream_section, rich_text_section, scroll_section, gap="24px", align="stretch")

PANELS = {"notifications": notifications_panel, "chat": chat_panel}


def _wire_toast(page: Page) -> None:
    # Toast is a full-viewport fixed layer (z-index 1100, pointer-events
    # none) — mount it at the page root so no ancestor transform can
    # hijack `position: fixed` in WebKit.
    page.add(toast)


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire_toast]
