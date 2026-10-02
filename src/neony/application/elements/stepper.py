"""Stepper — guided, single-select navigation with persistent panels."""

from __future__ import annotations

from typing import Literal, Self

from neony.application.theme import stub
from neony.dom import Button as _ButtonElem
from neony.dom import Color, Div, DOMElement, DomEvent, Span, Styles

from ._panels import _PanelHost
from .base import Component, ReactiveText, _mount_text
from .icon import Icon

_ROOT = Styles(display="flex", flex_direction="column", gap="14px", width="100%")
_BAR = Styles(display="flex", align_items="center", gap="8px", flex_wrap="wrap")
_BAR_VERTICAL = _BAR.model_copy(update={"flex_direction": "column", "align_items": "stretch", "flex_wrap": "nowrap"})
_STEP = Styles(
    display="flex",
    align_items="center",
    gap="8px",
    min_width="0",
    padding="7px 8px",
    border="none",
    border_radius="7px",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    text_align="left",
    cursor="pointer",
)
_STEP_ACTIVE = _STEP.model_copy(update={"background_color": stub.accent_glass_bg, "color": stub.text_primary})
_STEP_DISABLED = _STEP.model_copy(update={"cursor": "default", "opacity": 0.45})
_CIRCLE = Styles(
    display="inline-flex",
    align_items="center",
    justify_content="center",
    width="22px",
    height="22px",
    min_width="22px",
    border_radius="50%",
    background_color=stub.surface_raised,
    color=stub.text_secondary,
    font_size="11px",
    font_weight="600",
)
_CIRCLE_ACTIVE = _CIRCLE.model_copy(update={"background_color": stub.accent, "color": stub.on_accent})
_CIRCLE_DONE = _CIRCLE.model_copy(update={"background_color": stub.success, "color": Color(name="white")})
_TITLE = Styles(font_size="13px", font_weight="600", white_space="nowrap")
_DESC = Styles(font_size="11px", color=stub.text_secondary, line_height="1.25")
_CONNECTOR = Styles(width="24px", height="1px", background_color=stub.border, flex_shrink="0")
_CONNECTOR_VERTICAL = _CONNECTOR.model_copy(update={"width": "1px", "height": "12px", "margin_left": "18px"})


class Step:
    """One step in a :class:`Stepper`."""

    __slots__ = ("content", "description", "disabled", "icon", "key", "title")

    def __init__(
        self,
        title: ReactiveText,
        content: Component | DOMElement,
        *,
        key: str | None = None,
        description: ReactiveText | None = None,
        icon: Icon | None = None,
        disabled: bool = False,
    ) -> None:
        if key is None:
            if not isinstance(title, str):
                raise ValueError("Step: a reactive title needs an explicit key")
            key = title
        self.title = title
        self.content = content
        self.key = key
        self.description = description
        self.icon = icon
        self.disabled = disabled


class Stepper(Component):
    """A guided sequence of steps sharing one persistent content host."""

    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown"})

    def __init__(
        self,
        *steps: Step,
        active_key: str | None = None,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        linear: bool = False,
    ) -> None:
        super().__init__()
        self._steps: list[Step] = []
        self._rows: list[_ButtonElem] = []
        self._selected_key: str | None = None
        self._visited: set[str] = set()
        self._orientation = orientation
        self._linear = linear
        self._host = _PanelHost()
        self._bar = Div(styles=_BAR_VERTICAL if orientation == "vertical" else _BAR, container=[])
        self._bar.bubble_events = True
        self._root = Div(styles=_ROOT, container=[self._bar, self._host.root])
        self._bind(self._bar, "keydown")
        for step in steps:
            self.add(step)
        if active_key is not None:
            self.selected_key = active_key
        elif steps:
            self.selected_key = steps[0].key

    @property
    def steps(self) -> list[Step]:
        return list(self._steps)

    @property
    def selected_key(self) -> str | None:
        return self._selected_key

    @selected_key.setter
    def selected_key(self, value: str | None) -> None:
        if value is None:
            raise ValueError("Stepper: a step must remain selected")
        index = self._index_of(value)
        if index < 0:
            raise ValueError(f"Stepper: unknown step key {value!r}")
        self._activate(index, user=False)
        self._mirror_selected(value)

    @property
    def active_key(self) -> str | None:
        return self._selected_key

    @active_key.setter
    def active_key(self, value: str | None) -> None:
        self.selected_key = value

    @property
    def linear(self) -> bool:
        return self._linear

    @linear.setter
    def linear(self, value: bool) -> None:
        self._linear = value

    def add(self, step: Step) -> Self:
        if any(existing.key == step.key for existing in self._steps):
            raise ValueError(f"Stepper: duplicate step key {step.key!r}")
        self._steps.append(step)
        content = step.content.build() if isinstance(step.content, Component) else step.content
        self._host.add(content)
        row = self._make_row(step, len(self._steps) - 1)
        if len(self._steps) > 1:
            self._bar.container.append(
                Div(styles=_CONNECTOR_VERTICAL if self._orientation == "vertical" else _CONNECTOR)
            )
        self._bar.container.append(row)
        self._rows.append(row)
        if self._selected_key is None:
            first_enabled = next((i for i, candidate in enumerate(self._steps) if not candidate.disabled), None)
            if first_enabled is not None:
                self._activate(first_enabled, user=False)
        return self

    def _make_row(self, step: Step, index: int) -> _ButtonElem:
        title = Span(container=[], styles=_TITLE)
        _mount_text(title, step.title)
        body: list[DOMElement | str] = [self._circle(step, index), title]
        if step.description is not None:
            desc = Span(container=[], styles=_DESC)
            _mount_text(desc, step.description)
            body.append(desc)
        row = _ButtonElem(
            type="button",
            container=body,
            styles=_STEP,
            disabled=step.disabled,
            args={"role": "tab", "aria-selected": "false"},
        )
        row.bubble_events = True
        row.on("click", self._make_click_handler(index))
        return row

    def _circle(self, step: Step, index: int) -> Span:
        if step.icon is not None:
            return Span(container=[step.icon.render("14px")], styles=_CIRCLE)
        return Span(container=[str(index + 1)], styles=_CIRCLE)

    def _make_click_handler(self, index: int):
        async def handler(event: DomEvent) -> None:
            event.source = "user"
            if not self._activate(index, user=True):
                return
            event.value = self._steps[index].key
            await self._dispatch("change", event)

        return handler

    def _index_of(self, key: str) -> int:
        return next((i for i, step in enumerate(self._steps) if step.key == key), -1)

    def _activate(self, index: int, *, user: bool) -> bool:
        step = self._steps[index]
        if step.disabled:
            return False
        if user and self._linear:
            highest_visited = max((self._index_of(key) for key in self._visited), default=0)
            if index > highest_visited + 1:
                return False
        self._selected_key = step.key
        self._visited.add(step.key)
        self._host.set_active(index)
        self._apply_rows(index)
        return True

    def _apply_rows(self, active_index: int) -> None:
        active_pos = self._index_of(self._selected_key or "")
        for index, (step, row) in enumerate(zip(self._steps, self._rows, strict=True)):
            enabled = not step.disabled
            if index == active_index:
                row.styles = _STEP_ACTIVE
            elif enabled:
                row.styles = _STEP
            else:
                row.styles = _STEP_DISABLED
            row.args = {
                **row.args,
                "aria-selected": "true" if index == active_index else "false",
                "aria-disabled": "true" if step.disabled else "false",
            }
            circle = row.container[0]
            if isinstance(circle, Span):
                if index < active_pos or (step.key in self._visited and index != active_index):
                    circle.styles = _CIRCLE_DONE
                    circle.container = [Icon._font("check").render("13px")]
                elif index == active_index:
                    circle.styles = _CIRCLE_ACTIVE
                else:
                    circle.styles = _CIRCLE

    def next(self) -> bool:
        index = self._index_of(self._selected_key or "")
        for candidate in range(index + 1, len(self._steps)):
            if not self._steps[candidate].disabled:
                return self._activate(candidate, user=False)
        return False

    def previous(self) -> bool:
        index = self._index_of(self._selected_key or "")
        for candidate in range(index - 1, -1, -1):
            if not self._steps[candidate].disabled:
                return self._activate(candidate, user=False)
        return False

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "keydown":
            if event.value in ("ArrowRight", "ArrowDown"):
                await self._key_move(1, event)
            elif event.value in ("ArrowLeft", "ArrowUp"):
                await self._key_move(-1, event)
        await self._dispatch(event_type, event)

    async def _key_move(self, delta: int, event: DomEvent) -> None:
        key = event.value
        index = self._index_of(self._selected_key or "")
        candidate = index + delta
        if not 0 <= candidate < len(self._steps):
            return
        if not self._activate(candidate, user=True):
            return
        event.value = self._steps[candidate].key
        await self._dispatch("change", event)
        event.value = key
