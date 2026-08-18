"""RichText — a Python-driven inline rich-text editor.

The editor is a ``contenteditable`` region managed by the internal JS
engine (``window.neony.richText``), so the Python diff never rewrites its
DOM while the user is typing, composing IME text, or moving the caret.
Python holds the ordered segment model and syncs it from the DOM on
``input`` / ``compositionend`` / paste events.

Public API stays pure Python: :class:`TextSegment` and
:class:`ImageSegment` are the content model, ``content()`` returns the
ordered segments, and ``insert_image()`` / ``insert_text()`` land at the
current caret.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel

from neony.application.theme import stub
from neony.dom import Border, Div, DomEvent, Img, Span, Styles

from .base import Component


class TextSegment(BaseModel):
    """A run of plain text in a rich-text editor."""

    kind: Literal["text"] = "text"
    text: str = ""


class ImageSegment(BaseModel):
    """An inline image in a rich-text editor.

    ``src`` is any URL the WebView can load (``data:``, ``file:``,
    ``https:``).  ``alt`` is the image's fallback text.
    """

    kind: Literal["image"] = "image"
    src: str
    alt: str = ""
    width: int | str | None = None
    height: int | str | None = None


RichSegment = TextSegment | ImageSegment

_EDITOR = Styles(
    display="block",
    width="100%",
    min_height="42px",
    padding="6px 8px",
    border=Border(width="1px", color=stub.border),
    border_radius="8px",
    background_color=stub.surface,
    color=stub.text_primary,
    font_size="15px",
    line_height="1.5",
    outline="none",
    white_space="pre-wrap",
    word_break="break-word",
    cursor="text",
)

_TEXT = Styles(white_space="pre-wrap", word_break="break-word")

_IMAGE = Styles(
    display="inline-block",
    width="40px",
    height="40px",
    border_radius="5px",
    object_fit="cover",
    vertical_align="middle",
    cursor="pointer",
    user_select="none",
)


def _data_url_to_tempfile(data_url: str, name: str) -> str | None:
    """Decode a ``data:`` URL to a temp file; return its path or ``None``."""
    if not data_url.startswith("data:"):
        return None
    try:
        _header, payload = data_url.split(",", 1)
        content = base64.b64decode(payload)
    except (ValueError, binascii.Error):
        return None
    suffix = Path(name).suffix or _suffix_for_bytes(content)
    descriptor, path = tempfile.mkstemp(prefix="neony-paste-", suffix=suffix)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            Path(path).unlink()
        raise
    return path


def _suffix_for_bytes(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return ".gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


class RichText(Component):
    """Inline rich-text editor with text and image segments.

    Mount contract: the editor grows with its parent; place it in a
    definite-width flex/block parent.  Events (``input``, ``click``,
    ``keydown``, ``submit`` on Enter, ``paste_files``, ``paste_image``)
    are delivered through the usual ``on_*`` API.

    ``change`` is a pseudo-event: the callback receives a
    :class:`DomEvent` whose ``value`` is the current
    ``list[TextSegment | ImageSegment]``.  ``on_paste_image`` receives a
    ``DomEvent`` whose ``value`` is a list of temp file paths written
    from pasted image bytes; ``on_paste_files`` receives the raw
    ``paste_files`` event.
    """

    _bound_events: frozenset[str] = frozenset(
        {
            "input",
            "click",
            "keydown",
            "keyup",
            "focus",
            "blur",
            "compositionstart",
            "compositionupdate",
            "compositionend",
            "paste_files",
        }
    )

    def __init__(
        self,
        placeholder: str = "",
        segments: Sequence[RichSegment | str] = (),
    ) -> None:
        super().__init__()
        self._placeholder = placeholder
        self._segments: list[RichSegment] = [self._coerce(seg) for seg in segments]
        self._caret = self._flat_length()
        self._selection_end = self._caret
        self._selected_image_index: int | None = None

        args: dict[str, Any] = {
            "contenteditable": "true",
            "data-neony-rich-text": "true",
            "role": "textbox",
            "spellcheck": "true",
        }
        if placeholder:
            args["data-placeholder"] = placeholder
        self._root = Div(styles=_EDITOR, args=args)
        # Managed content: the bridge freezes diffing under this node and
        # the JS engine owns the live DOM.  bubble_events lets events on
        # keyed child spans/images reach this root's handlers.
        self._root._managed_content = True
        self._root.bubble_events = True
        self._root.container = [self._build_segment_element(seg) for seg in self._segments]

        for event_type in self._bound_events:
            self._bind(self._root, event_type)

    # ---- segment model helpers ----

    @staticmethod
    def _coerce(segment: RichSegment | str) -> RichSegment:
        if isinstance(segment, (TextSegment, ImageSegment)):
            return segment
        return TextSegment(text=str(segment))

    @staticmethod
    def _build_segment_element(segment: RichSegment) -> Div | Span | Img:
        if isinstance(segment, ImageSegment):
            return Img(
                src=segment.src,
                alt=segment.alt,
                styles=_IMAGE,
                args={"data-neony-rich-image": "true", "draggable": "false"},
            )
        return Span(container=[segment.text], styles=_TEXT)

    @staticmethod
    def _segment_to_js(segment: RichSegment) -> dict[str, Any]:
        if isinstance(segment, ImageSegment):
            return {"kind": "image", "src": segment.src, "alt": segment.alt}
        return {"kind": "text", "text": segment.text}

    @staticmethod
    def _segment_from_js(item: dict[str, Any]) -> RichSegment:
        if item.get("kind") == "image":
            return ImageSegment(src=str(item.get("src", "")), alt=str(item.get("alt", "")))
        return TextSegment(text=str(item.get("text", "")))

    def _flat_length(self) -> int:
        total = 0
        for segment in self._segments:
            total += len(segment.text) if isinstance(segment, TextSegment) else 1
        return total

    def _normalize_segments(self) -> None:
        """Merge adjacent text segments into single runs."""
        merged: list[RichSegment] = []
        for segment in self._segments:
            if merged and isinstance(merged[-1], TextSegment) and isinstance(segment, TextSegment):
                merged[-1] = TextSegment(text=merged[-1].text + segment.text)
            else:
                merged.append(segment)
        self._segments = merged

    def _insert_segment_at(self, pos: int, segment: RichSegment) -> None:
        """Insert *segment* into the model at flat position *pos*."""
        flat = 0
        for index, current in enumerate(self._segments):
            length = len(current.text) if isinstance(current, TextSegment) else 1
            if pos <= flat:
                self._segments.insert(index, segment)
                return
            if pos < flat + length:
                if isinstance(current, TextSegment):
                    offset = pos - flat
                    self._segments[index] = TextSegment(text=current.text[:offset])
                    self._segments.insert(index + 1, segment)
                    if offset < len(current.text):
                        self._segments.insert(index + 2, TextSegment(text=current.text[offset:]))
                else:
                    self._segments.insert(index + 1, segment)
                return
            flat += length
        self._segments.append(segment)

    def _json_key(self) -> str:
        return json.dumps(self._root.key)

    def _sync_dom(self, caret: int | None = None) -> None:
        """Rebuild the live DOM from the Python model and restore *caret*."""
        segments = json.dumps([self._segment_to_js(seg) for seg in self._segments])
        script = f"window.neony.richText.loadContent({self._json_key()}, {segments})"
        if caret is not None:
            script += f";window.neony.richText.setCaret({self._json_key()}, {caret})"
        self._schedule_js(script)

    def _fire_change(self, source: Literal["user", "program"]) -> None:
        """Notify ``change`` callbacks fire-and-forget (sync callers)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        task = asyncio.create_task(self._notify_change(source))
        self._js_tasks.add(task)
        task.add_done_callback(self._js_tasks.discard)

    async def _notify_change(self, source: Literal["user", "program"]) -> None:
        event = DomEvent(key=self._root.key, type="change", value=self.content(), source=source)
        await self._dispatch("change", event)

    async def _sync_segments_from_js(self) -> None:
        """Re-export the live DOM into the Python segment model."""
        coro = self._call_js(f"JSON.stringify(window.neony.richText.exportContent({self._json_key()}))")
        if coro is None:
            return
        raw = await coro
        try:
            items = json.loads(raw)
        except (TypeError, ValueError):
            return
        if not isinstance(items, list):
            return
        segments = [self._segment_from_js(item) for item in items]
        old = self._segments
        self._segments = segments
        self._normalize_segments()
        if self._segments != old:
            await self._notify_change("user")

    async def _handle_paste_files(self, event: DomEvent) -> None:
        """Write pasted file bytes to temp files and dispatch paste_image."""
        files = event.paste_files or []
        image_paths: list[str] = []
        for file in files:
            data_url = str(file.get("data_url", ""))
            if not data_url.startswith("data:"):
                continue
            path = await asyncio.to_thread(_data_url_to_tempfile, data_url, str(file.get("name", "")))
            if path is None:
                continue
            if str(file.get("type", "")).startswith("image/"):
                image_paths.append(path)
        if image_paths:
            await self._dispatch(
                "paste_image",
                DomEvent(key=self._root.key, type="paste_image", value=image_paths, source="user"),
            )

    # ---- public API ----

    def content(self) -> list[RichSegment]:
        """Return the ordered content segments (text and inline images)."""
        return [segment.model_copy(deep=True) for segment in self._segments]

    def set_content(self, segments: Sequence[RichSegment | str]) -> Self:
        """Replace the editor content (programmatic; no user callbacks)."""
        self._segments = [self._coerce(seg) for seg in segments]
        self._normalize_segments()
        self._root.container = [self._build_segment_element(seg) for seg in self._segments]
        self._caret = 0
        self._selection_end = 0
        self._sync_dom(self._caret)
        self._fire_change("program")
        return self

    def insert_text(self, text: str, *, at_caret: bool = True) -> Self:
        """Insert a text segment; by default at the current caret."""
        pos = self._caret if at_caret else self._flat_length()
        self._insert_segment_at(pos, TextSegment(text=text))
        self._normalize_segments()
        self._caret = pos + len(text)
        self._selection_end = self._caret
        self._sync_dom(self._caret)
        self._fire_change("program")
        return self

    def insert_image(
        self,
        src: str,
        *,
        at_caret: bool = True,
        alt: str = "",
        width: int | str | None = None,
        height: int | str | None = None,
    ) -> Self:
        """Insert an inline image; by default at the current caret."""
        pos = self._caret if at_caret else self._flat_length()
        segment = ImageSegment(src=src, alt=alt, width=width, height=height)
        self._insert_segment_at(pos, segment)
        self._normalize_segments()
        self._caret = pos + 1
        self._selection_end = self._caret
        script = f"window.neony.richText.insertImage({self._json_key()}, {json.dumps(src)}, {json.dumps(alt)}, {pos})"
        self._schedule_js(script)
        self._fire_change("program")
        return self

    def caret_position(self) -> int:
        """The flat caret position (text chars + 1 per inline image)."""
        return self._caret

    def selection_range(self) -> tuple[int, int]:
        """The flat selection range ``(start, end)``."""
        return (self._caret, self._selection_end)

    def set_caret(self, position: int) -> Self:
        """Move the caret to a flat position."""
        pos = max(0, min(position, self._flat_length()))
        self._caret = pos
        self._selection_end = pos
        self._schedule_js(f"window.neony.richText.setCaret({self._json_key()}, {pos})")
        return self

    def focus(self) -> Self:
        """Focus the editor."""
        self._schedule_js(f"window.neony.richText.focus({self._json_key()})")
        return self

    # ---- event API ----

    def on_change(self, fn: Callable[[DomEvent], Any]) -> Self:
        """Register for segment changes; ``event.value`` is the segment list."""
        self._callbacks.setdefault("change", []).append(fn)
        return self

    def on_paste_image(self, fn: Callable[[DomEvent], Any]) -> Self:
        """Register for pasted image bytes; ``event.value`` is a list of
        temp file paths (one per pasted image)."""
        self._callbacks.setdefault("paste_image", []).append(fn)
        return self

    def on_paste_files(self, fn: Callable[[DomEvent], Any]) -> Self:
        """Register for the raw synthetic ``paste_files`` event."""
        return self.on("paste_files", fn)

    def on_submit(self, fn: Callable[[DomEvent], Any]) -> Self:
        """Register for Enter in the editor (IME-safe)."""
        return self.on("submit", fn)

    # ---- component event handling ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event.caret_position is not None:
            self._caret = event.caret_position
        if event.selection_end is not None:
            self._selection_end = event.selection_end

        if (event_type == "input" and not event.is_composing) or event_type == "compositionend":
            await self._sync_segments_from_js()
        elif event_type == "click":
            self._selected_image_index = event.image_index
        elif event_type == "keydown":
            if event.value == "Enter" and not event.is_composing:
                # The JS engine prevents the default newline; surface the
                # chat-send action as a submit pseudo-event.
                await self._dispatch("submit", event)
        elif event_type == "paste_files":
            await self._handle_paste_files(event)

        await self._dispatch(event_type, event)
