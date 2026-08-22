"""The event payload model forwarded from the JavaScript engine."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class DomEvent(BaseModel):
    """Event payload forwarded from JavaScript: ``key`` (element identity),
    ``type`` (DOM event name), ``value`` (``el.value`` for inputs,
    ``el.checked`` for checkboxes, else ``None``).  ``source`` tells real
    user interaction ("user") from programmatic changes ("program"),
    which must not fire user callbacks.

    Rich fields: modifier keys (``ctrl_key`` ... — ``True`` only when
    pressed), mouse coordinates (``x``/``y`` viewport-relative,
    ``offset_x``/``offset_y`` element-relative), wheel delta
    (``delta_x``/``delta_y``), and clipboard data (``clipboard_text`` /
    ``clipboard_html`` — paste events only).  Absent on events that
    don't carry them.
    """

    key: str
    type: str
    value: Any = None
    source: Literal["user", "program"] = "program"

    # Modifier keys.
    ctrl_key: bool = False
    shift_key: bool = False
    alt_key: bool = False
    meta_key: bool = False

    # Mouse coordinates (MouseEvent / WheelEvent).
    x: float | None = None
    y: float | None = None
    offset_x: float | None = None
    offset_y: float | None = None

    # Pointer movement delta (PointerEvent) — change in coordinates
    # since the last pointermove; useful for drag tracking without
    # manual deltas.
    movement_x: float | None = None
    movement_y: float | None = None

    # Pointer type: "mouse", "pen", or "touch" (PointerEvent only).
    pointer_type: str | None = None

    # mouseover/mouseout only: the key of the keyed element the pointer
    # moved from/to (None when it came from off-page or an unkeyed
    # part).  Enter/leave detection — a component's subtree boundary is
    # crossed exactly when this key is not one of its own descendants.
    related_key: str | None = None

    # Wheel delta (WheelEvent).  delta_mode: 0 = pixels, 1 = lines,
    # 2 = pages (WebKitGTK mouse wheels deliver line deltas).
    delta_x: float | None = None
    delta_y: float | None = None
    delta_mode: int | None = None

    # Scroll position (scroll event only, pixels) — the scrolled
    # element's scrollTop / scrollLeft at dispatch time.
    scroll_top: int | None = None
    scroll_left: int | None = None

    # CSS transition end (TransitionEvent) — which property finished
    # and how long it took.
    transition_property: str | None = None
    elapsed_time: float | None = None

    # CSS animation start / end (AnimationEvent) — the animation name.
    animation_name: str | None = None

    # Clipboard data (paste events only).
    clipboard_text: str | None = None
    clipboard_html: str | None = None

    # Composition events (compositionstart / compositionupdate /
    # compositionend).  ``composition_data`` carries ``event.data``
    # (the composed text on end, the new text on update, empty on
    # start); ``is_composing`` is True while an IME session is active
    # (also carried on ``input`` during composition).
    composition_data: str | None = None
    is_composing: bool = False

    # Scroll geometry (scroll events only): the scrolled element's
    # full content size and visible size, so components can decide
    # "near bottom" without eval_js hacks.
    scroll_height: int | None = None
    client_height: int | None = None
    scroll_width: int | None = None
    client_width: int | None = None

    # Pasted files (paste events only): one dict per file with keys
    # ``name``, ``size``, ``type``.  A follow-up synthetic ``paste_files``
    # event delivers the same entries plus a ``data_url`` containing the
    # file bytes.
    paste_files: list[dict[str, Any]] | None = None

    # RichText editor fields (events targeting a ``[data-neony-rich-text]``
    # subtree): the flat caret position (text chars + 1 per inline image),
    # and — when the target is an inline image — the image's flat index,
    # src and alt.
    caret_position: int | None = None
    selection_end: int | None = None
    image_index: int | None = None
    image_src: str | None = None
    image_alt: str | None = None

    # In-app drag payload (dragstart / drop only): the string declared on
    # the source element via ``DOMElement.drag_payload`` and carried
    # through ``dataTransfer`` — lets a drop handler identify what was
    # dragged without a Python-side registry.
    drag_payload: str | None = None

    # Dropped files (drop events only): one dict per file with keys
    # ``name``, ``path`` (empty string on WKWebView), ``size``, ``type``.
    drop_files: list[dict[str, Any]] | None = None

    # Media elements (direct-wired neony Video/Audio events): playback
    # position, clip duration, volume level, mute state, paused flag and
    # the MediaError code on ``error``.  Absent on other events.
    media_time: float | None = None
    media_duration: float | None = None
    media_volume: float | None = None
    media_muted: bool | None = None
    media_paused: bool | None = None
    media_error: int | None = None
