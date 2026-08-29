#!/usr/bin/env python3
"""Streaming demo — token-by-token text into chat bubbles.

Two delivery paths, both cheap on the bridge:

- a plain ``MessageBubble`` fed with ``append_text`` — the diff ships
  only the appended chunk (an ``append_text`` patch), never the whole
  accumulated string;
- a ``MessageBubble(markdown=True)`` fed through ``stream()`` — the raw
  source travels to the webview, which renders Markdown (headings, code
  highlighting, tables) in place.

Both bubbles live inside a ``StickToBottom`` scroll container, so the
view follows the growing text while the user is near the bottom.  Run:

    python demo_streaming.py
"""

import asyncio
import itertools

from neony.application import Page, launch
from neony.application.elements import Button, HStack, MessageBubble, StickToBottom, Text, VStack

PLAIN_ANSWER = (
    "Sure — streaming is incremental by nature. Each token arrives, the text "
    "grows, and only the new chunk crosses the bridge: the framework detects "
    "that the message is a pure extension of what the browser already shows "
    "and sends an append patch instead of the full string. "
)

MARKDOWN_ANSWER = (
    "## Streaming Markdown\n\n"
    "Rendered **in the webview** while the source streams from Python.\n\n"
    "- headings, lists and tables\n"
    "- `inline code` and fenced blocks\n\n"
    "```python\n"
    "async for token in llm.reply(prompt):\n"
    "    bubble.append_text(token)\n"
    "```\n\n"
    "| path | ships |\n| --- | --- |\n| plain text | the chunk |\n| markdown | the source |\n\n"
    "Links stay clickable: [Neony docs](https://harcic.me/neony) open in the "
    "system browser.\n"
)


async def tokens(text: str, *, size: int = 3, delay: float = 0.04):
    """Slice *text* into small chunks with a human-ish cadence."""
    counter = itertools.count()
    for start in range(0, len(text), size):
        yield text[start : start + size]
        await asyncio.sleep(delay * (6 if next(counter) % 7 == 0 else 1))


bubbles = VStack(gap="12px", width="100%")
chat = StickToBottom(bubbles)
status_text = Text("Press Stream to start.", role="secondary")
stream_tasks: list[asyncio.Task[None]] = []


def stop_stream() -> None:
    for task in stream_tasks:
        task.cancel()
    stream_tasks.clear()


async def start_stream(_event=None) -> None:
    stop_stream()
    bubbles._root.container.clear()
    question = MessageBubble("Compare plain text and Markdown streaming.", name="You", from_me=True)
    bubbles._root.container.append(question.build())
    status_text.text = "Streaming…"

    async def run_plain() -> None:
        bubble = MessageBubble("", name="Assistant (plain)")
        bubbles._root.container.append(bubble.build())
        await bubble.stream(tokens(PLAIN_ANSWER))
        status_text.text = "Plain stream done."

    async def run_markdown() -> None:
        bubble = MessageBubble("", name="Assistant (markdown)", markdown=True)
        bubbles._root.container.append(bubble.build())
        await bubble.stream(tokens(MARKDOWN_ANSWER, size=5))
        status_text.text = "Markdown stream done."

    stream_tasks[:] = [asyncio.create_task(run_plain()), asyncio.create_task(run_markdown())]


def on_stop(_event=None) -> None:
    stop_stream()
    status_text.text = "Stopped."


page = Page(fill=True, gap="12px", padding="16px").add(
    Text("Token streaming into chat bubbles", size="17px", weight="bold"),
    chat,
    HStack(
        Button("Stream").on_click(start_stream),
        Button("Stop", variant="danger").on_click(on_stop),
        status_text,
        gap="12px",
        align="center",
    ),
)

launch(page, title="Neony Streaming", width=760, height=560, devtools=True)
