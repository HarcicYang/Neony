"""PromptDialog component — a modal that asks the user for a single line of text.

A thin specialisation of :class:`Dialog`: a themed scrim + centered glass
panel with a message, a single :class:`Input` field, and a confirm /
cancel button row.  Confirm (the primary button or pressing ``Enter`` while
the field has focus) fires :meth:`on_submit` with the current value;
cancel (the ghost button, ``Escape``, scrim click, or click-away) closes
without firing it.

Like :class:`Dialog`, this is a ``position: fixed`` layer — mount it at the
page root (or any non-filtered, non-transformed container), not inside a
component whose ancestor carries ``backdrop-filter`` / ``transform``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Self

from neony.dom import Color, Div, DomEvent, Span, Styles

from .dialog import Dialog  # reuses its module-level panel/scrim styles
from .input import Input


class PromptDialog(Dialog):
    """A modal prompt — ask the user for one text value.

    - ``prompt`` — the question shown above the field (first positional arg).
    - ``value`` — the field's initial text (also settable to pre-fill /
      reset before opening).
    - ``placeholder`` — the field's placeholder.
    - ``confirm_label`` / ``cancel_label`` — the action button labels.
    - ``dialog.open`` reads / sets the visible state.
    - ``on_submit(fn)`` — fires on confirm with the field's value (sync or
      async); ``fn`` is called with the value string.
    - ``on_open`` / ``on_close`` — inherited from :class:`Dialog`.
    """

    def __init__(
        self,
        prompt: str = "",
        *,
        value: str = "",
        placeholder: str = "",
        title: str = "",
        confirm_label: str = "OK",
        cancel_label: str = "Cancel",
        open: bool = False,
        width: str = "420px",
    ) -> None:
        # The field lives between the title and the action row.
        self._field = Input(placeholder=placeholder, value=value)

        message = Span(container=[prompt]) if prompt else None
        content_parts: list[Any] = []
        if message is not None:
            content_parts.append(
                Div(
                    styles=Styles(color=Color(var="--color-text-secondary"), margin="0 0 12px 0"),
                    container=[message],
                )
            )
        content_parts.append(self._field.build())
        content = Div(styles=Styles(display="flex", flex_direction="column", gap="4px"), container=content_parts)

        # Defer wiring submit until after super().__init__ builds the panel,
        # so the field is already mounted and its key is registered.
        self._submit_callbacks: list[Callable[[str], Any]] = []

        super().__init__(
            title=title,
            content=content,
            open=open,
            width=width,
            actions=(),  # we build our own button row below
        )

        # Replace the (empty) action bar with our confirm/cancel row.
        confirm_btn = self._make_action_button(confirm_label, "primary", self._on_confirm)
        cancel_btn = self._make_action_button(cancel_label, "ghost", lambda _e: self.close())
        action_bar = Div(
            styles=Styles(display="flex", justify_content="flex-end", gap="8px", margin_top="16px"),
            container=[cancel_btn.build(), confirm_btn.build()],
        )
        # The panel children are [header, content, action_bar?]; append ours.
        self._panel.container.append(action_bar)

        # Enter in the field submits; the keydown bubbles to the dialog root
        # (Dialog sets bubble_events=True), but we bind the field directly so
        # the intent is local and unambiguous.
        self._field.on_keydown(self._on_field_keydown)
        self._prompt = prompt

    # ---- state ----

    @property
    def value(self) -> str:
        return self._field.value

    @value.setter
    def value(self, value: str) -> None:
        self._field.value = value

    @property
    def prompt(self) -> str:
        """The question text shown above the field."""
        return self._prompt

    def close(self) -> None:
        """Hide the dialog (alias of ``open = False``)."""
        self.open = False

    # ---- callback registration ----

    def on_submit(self, fn: Callable[[str], Any]) -> Self:
        """Register a callback fired when the user confirms (primary button
        or Enter) with the field's current value. Sync or async."""
        self._submit_callbacks.append(fn)
        return self

    # ---- internals ----

    def _make_action_button(self, label: str, variant: str, handler: Callable[[DomEvent], Any]):
        from .button import Button

        btn = Button(label, variant=variant)  # type: ignore[arg-type]
        btn.on_click(handler)
        return btn

    async def _on_field_keydown(self, event: DomEvent) -> None:
        if event.value == "Enter":
            await self._on_confirm(event)

    async def _on_confirm(self, _event: DomEvent) -> None:
        value = self._field.value
        self.open = False  # close first so callbacks see the closed state
        # Fire-and-forget like the base pseudo-event path: async submit
        # callbacks must not block the synchronous close.
        for fn in self._submit_callbacks:
            result = fn(value)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                self._pseudo_tasks.add(task)
                task.add_done_callback(self._pseudo_tasks.discard)
