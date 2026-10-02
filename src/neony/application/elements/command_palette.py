"""CommandPalette — a searchable, keyboard-first command surface."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Self

from neony.application.theme import stub
from neony.dom import Border, Div, DOMElement, DomEvent, Filter, Span, Styles
from neony.dom import Button as _ButtonElem

from ..layers import Layer, LayerHandle, layer_manager
from ._choices import ChoiceItem
from ._overlay import mark_portal
from .base import Component
from .icon import Icon
from .input import Input

_ROOT = Styles(position="fixed", top="0", right="0", bottom="0", left="0", display="none")
_ROOT_OPEN = _ROOT.model_copy(update={"display": "flex", "justify_content": "center", "align_items": "flex-start"})
_SCRIM = Styles(
    position="absolute",
    top="0",
    right="0",
    bottom="0",
    left="0",
    background_color=stub.bg_overlay,
    opacity=0,
)
_SCRIM_OPEN = _SCRIM.model_copy(update={"opacity": 1.0})
_PANEL = Styles(
    position="relative",
    display="flex",
    flex_direction="column",
    gap="8px",
    width="min(620px, calc(100vw - 32px))",
    max_height="min(560px, calc(100vh - 80px))",
    margin_top="8vh",
    padding="12px",
    border_radius="12px",
    border=Border(width="1px", color=stub.border_glass),
    background_color=stub.surface_glass_bg,
    backdrop_filter=Filter(blur="22px", saturate=1.2),
)
_RESULTS = Styles(display="flex", flex_direction="column", gap="3px", overflow_y="auto", min_height="0")
_ROW = Styles(
    display="flex",
    flex_direction="column",
    gap="2px",
    padding="9px 10px",
    border="none",
    border_radius="7px",
    background_color=stub.surface,
    color=stub.text_primary,
    text_align="left",
    cursor="pointer",
)
_ROW_ACTIVE = _ROW.model_copy(update={"background_color": stub.accent_glass_bg})
_ROW_TITLE_LINE = Styles(display="flex", align_items="center", gap="8px", width="100%")
_ROW_LABEL = Styles(flex_grow="1", font_size="14px", font_weight="600")
_ROW_SHORTCUT = Styles(color=stub.text_secondary, font_size="11px", white_space="nowrap")
_ROW_DESC = Styles(color=stub.text_secondary, font_size="12px", line_height="1.3")
_EMPTY = Styles(color=stub.text_secondary, font_size="13px", padding="12px", text_align="center")


class Command(ChoiceItem):
    """One command-palette entry."""

    __slots__ = ("description",)

    def __init__(
        self,
        value: str,
        label: str | None = None,
        *,
        description: str = "",
        keywords: Sequence[str] = (),
        shortcut: str | dict[str, str] | None = None,
        icon: Icon | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            value,
            label,
            keywords=keywords,
            shortcut=shortcut,
            icon=icon,
            disabled=disabled,
        )
        self.description = description


class CommandPalette(Component):
    """A modal command palette with local filtering and keyboard selection."""

    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown", "open", "close"})

    def __init__(
        self,
        *commands: Command,
        hotkey: str | dict[str, str] | None = None,
        placeholder: str = "Search commands…",
        open: bool = False,
    ) -> None:
        super().__init__()
        self._commands: list[Command] = []
        self._filtered: list[Command] = []
        self._rows: list[_ButtonElem] = []
        self._active_index = -1
        self._open = False
        self._hotkey = hotkey
        self._layer_handle: LayerHandle | None = None

        self._input = Input(
            prefix=Icon._font("search"),
            clearable=True,
            placeholder=placeholder,
        )
        self._input.on_input(self._on_query)
        self._results = Div(styles=_RESULTS)
        self._scrim = Div(styles=_SCRIM)
        panel = Div(styles=_PANEL, container=[self._input.build(), self._results])
        self._root = Div(
            styles=_ROOT,
            args={"role": "dialog", "aria-modal": "true", "aria-label": "Command palette"},
            container=[self._scrim, panel],
        )
        mark_portal(self._root)
        self._panel = panel
        self._bind(self._scrim, "click")
        self._bind(self._root, "keydown")
        self.add_command(*commands)
        if open:
            self.open = True

    @property
    def commands(self) -> list[Command]:
        return list(self._commands)

    def add_command(self, *commands: Command) -> Self:
        for command in commands:
            if any(existing.value == command.value for existing in self._commands):
                raise ValueError(f"CommandPalette: duplicate command value {command.value!r}")
            self._commands.append(command)
        self._rebuild()
        return self

    @property
    def query(self) -> str:
        return self._input.value

    @query.setter
    def query(self, value: str) -> None:
        self._input.value = value
        self._rebuild()

    @property
    def open(self) -> bool:
        return self._open

    @open.setter
    def open(self, value: bool) -> None:
        if value == self._open:
            return
        self._open = value
        if value:
            self._root.styles = _ROOT_OPEN
            self._scrim.styles = _SCRIM_OPEN
            self._input.value = ""
            self._rebuild()
            self._layer_handle = layer_manager(self._root).open(
                self._root,
                kind=Layer.MODAL,
                group="command-palette",
                on_close=self._close_from_layer,
                focus_scope="trap",
                initial_focus=self._input.control_element,
            )
        else:
            if self._layer_handle is not None:
                self._layer_handle.close()
                self._layer_handle = None
            self._root.styles = _ROOT
            self._scrim.styles = _SCRIM
        self._dispatch_pseudo("open" if value else "close", self)

    def _close_from_layer(self) -> None:
        self.open = False

    def on_open(self, fn) -> Self:
        return self.on("open", fn)

    def on_close(self, fn) -> Self:
        return self.on("close", fn)

    def shortcuts(self) -> list[tuple[str | dict[str, str], Callable[[], Any]]]:
        if self._hotkey is None:
            return []
        return [(self._hotkey, lambda: setattr(self, "open", True))]

    def _matches(self, command: Command) -> bool:
        query = self.query.strip().lower()
        if not query:
            return True
        label = command.label if isinstance(command.label, str) else command.value
        fields = (command.value, label, command.description, *command.keywords)
        return any(query in field.lower() for field in fields)

    def _rebuild(self) -> None:
        self._filtered = [command for command in self._commands if self._matches(command)]
        self._rows.clear()
        self._results.container = []
        for command in self._filtered:
            row = self._make_row(command)
            self._rows.append(row)
            self._results.container.append(row)
        if not self._filtered:
            self._results.container.append(Span(container=["No commands"], styles=_EMPTY))
        self._active_index = 0 if self._rows else -1
        self._apply_row_styles()

    def _make_row(self, command: Command) -> _ButtonElem:
        title = Span(container=[], styles=_ROW_LABEL)
        if isinstance(command.label, str):
            title.container = [command.label]
        else:
            title.bind_text(command.label)
        title_line: list[DOMElement | str] = []
        if command.icon is not None:
            title_line.append(command.icon.render("15px"))
        title_line.append(title)
        shortcut = command.shortcut if isinstance(command.shortcut, str) else None
        if shortcut:
            title_line.append(Span(container=[shortcut], styles=_ROW_SHORTCUT))
        content: list[DOMElement | str] = [Div(styles=_ROW_TITLE_LINE, container=title_line)]
        if command.description:
            content.append(Span(container=[command.description], styles=_ROW_DESC))
        row = _ButtonElem(
            type="button",
            container=content,
            styles=_ROW,
            disabled=command.disabled,
            args={"role": "option"},
        )
        row.bubble_events = True
        row.on("click", self._make_pick_handler(command))
        row.on("mouseover", self._make_hover_handler(command))
        return row

    def _make_pick_handler(self, command: Command):
        async def handler(event: DomEvent) -> None:
            event.source = "user"
            if command.disabled:
                return
            await self._pick(command, event)

        return handler

    def _make_hover_handler(self, command: Command):
        async def handler(_event: DomEvent) -> None:
            if command.disabled or command not in self._filtered:
                return
            self._active_index = self._filtered.index(command)
            self._apply_row_styles()

        return handler

    def _apply_row_styles(self) -> None:
        for index, row in enumerate(self._rows):
            row.styles = _ROW_ACTIVE if index == self._active_index else _ROW
            row.args = {
                **row.args,
                "aria-selected": "true" if index == self._active_index else "false",
            }

    async def _pick(self, command: Command, event: DomEvent) -> None:
        event.value = command.value
        self.open = False
        await self._dispatch("change", event)

    async def _on_query(self, _event: DomEvent) -> None:
        self._rebuild()

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "click" and event.key == self._scrim.key:
            self.open = False
        elif event_type == "keydown":
            await self._on_keydown(event)
        await self._dispatch(event_type, event)

    async def _on_keydown(self, event: DomEvent) -> None:
        if event.value in ("ArrowDown", "ArrowUp"):
            enabled = [i for i, command in enumerate(self._filtered) if not command.disabled]
            if not enabled:
                return
            if self._active_index not in enabled:
                self._active_index = enabled[0]
            else:
                delta = 1 if event.value == "ArrowDown" else -1
                pos = enabled.index(self._active_index)
                self._active_index = enabled[max(0, min(len(enabled) - 1, pos + delta))]
            self._apply_row_styles()
            event.value = self._filtered[self._active_index].value
        elif event.value in ("Home", "End"):
            enabled = [i for i, command in enumerate(self._filtered) if not command.disabled]
            if enabled:
                self._active_index = enabled[0] if event.value == "Home" else enabled[-1]
                self._apply_row_styles()
                event.value = self._filtered[self._active_index].value
        elif event.value == "Enter":
            if 0 <= self._active_index < len(self._filtered):
                command = self._filtered[self._active_index]
                if not command.disabled:
                    await self._pick(command, event)
        elif event.value == "Escape":
            self.open = False
