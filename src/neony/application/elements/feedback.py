"""Loading, skeleton and empty-state feedback components."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from neony.application.theme import stub
from neony.dom import Animation, Color, Div, DOMElement, Span, Styles

from .base import Component, ReactiveText, _mount_text
from .icon import Icon

_Role = Literal["accent", "success", "danger", "neutral"]


def _role_color(role: _Role) -> Color:
    return {
        "accent": stub.accent,
        "success": stub.success,
        "danger": stub.danger,
        "neutral": stub.text_secondary,
    }[role]


class Spinner(Component):
    """An animated activity ring with an optional live label."""

    def __init__(self, label: ReactiveText = "", *, size: str = "20px", role: _Role = "accent") -> None:
        if role not in ("accent", "success", "danger", "neutral"):
            raise ValueError(f"Spinner: unknown role {role!r}")
        super().__init__()
        self._label: ReactiveText = label
        self._size = size
        self._role: _Role = role
        self._ring = Div(styles=self._ring_styles())
        self._label_span = Span(container=[], styles=Styles(font_size="14px", color=stub.text_secondary))
        if label:
            _mount_text(self._label_span, label)
        parts: list[DOMElement] = [self._ring]
        if label or not isinstance(label, str):
            parts.append(self._label_span)
        self._root = Div(
            styles=Styles(display="inline-flex", align_items="center", gap="8px"),
            args={"role": "status", "aria-live": "polite"},
            container=parts,
        )

    @property
    def label(self) -> str:
        if isinstance(self._label, str):
            return self._label
        return self._label()

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._label_span._unbind_text()
        self._label_span.container = [] if value == "" else [value]
        self._sync_label_presence()

    @property
    def size(self) -> str:
        return self._size

    @size.setter
    def size(self, value: str) -> None:
        self._size = value
        self._ring.styles = self._ring_styles()

    @property
    def role(self) -> _Role:
        return self._role

    @role.setter
    def role(self, value: _Role) -> None:
        if value not in ("accent", "success", "danger", "neutral"):
            raise ValueError(f"Spinner.role: unknown role {value!r}")
        self._role = value
        self._ring.styles = self._ring_styles()

    def _ring_styles(self) -> Styles:
        return Styles(
            width=self._size,
            height=self._size,
            border="2px solid var(--color-border)",
            border_top=f"2px solid {_role_color(self._role)}",
            border_radius="50%",
            animation=Animation(
                name="neony-spin",
                duration="0.8s",
                timing="linear",
                iteration_count="infinite",
            ),
            flex_shrink="0",
        )

    def _sync_label_presence(self) -> None:
        has_label = bool(self.label)
        if has_label and self._label_span not in self._root.container:
            self._root.container.append(self._label_span)
        elif not has_label and self._label_span in self._root.container:
            self._root.container.remove(self._label_span)


class Skeleton(Component):
    """Non-interactive loading placeholders."""

    def __init__(
        self,
        variant: Literal["text", "rect", "circle"] = "text",
        *,
        lines: int = 1,
        width: str | None = None,
        height: str | None = None,
        radius: str | None = None,
        animation: bool = True,
    ) -> None:
        if lines <= 0:
            raise ValueError(f"Skeleton: lines must be positive, got {lines!r}")
        super().__init__()
        self._variant = variant
        self._lines = lines
        self._width = width
        self._height = height
        self._radius = radius
        self._animation = animation
        self._root = Div(
            styles=Styles(display="flex", flex_direction="column", gap="8px", width="100%"),
            args={"aria-hidden": "true"},
        )
        self._rebuild()

    @property
    def variant(self) -> Literal["text", "rect", "circle"]:
        return self._variant

    @variant.setter
    def variant(self, value: Literal["text", "rect", "circle"]) -> None:
        if value not in ("text", "rect", "circle"):
            raise ValueError(f"Skeleton.variant: unknown variant {value!r}")
        self._variant = value
        self._rebuild()

    @property
    def lines(self) -> int:
        return self._lines

    @lines.setter
    def lines(self, value: int) -> None:
        if value <= 0:
            raise ValueError(f"Skeleton.lines: expected a positive value, got {value!r}")
        self._lines = value
        self._rebuild()

    @property
    def width(self) -> str | None:
        return self._width

    @width.setter
    def width(self, value: str | None) -> None:
        self._width = value
        self._rebuild()

    @property
    def height(self) -> str | None:
        return self._height

    @height.setter
    def height(self, value: str | None) -> None:
        self._height = value
        self._rebuild()

    @property
    def animation(self) -> bool:
        return self._animation

    @animation.setter
    def animation(self, value: bool) -> None:
        self._animation = value
        self._rebuild()

    def _line_styles(self) -> Styles:
        height = self._height
        radius = self._radius
        if self._variant == "circle":
            width = self._width or height or "40px"
            height = height or width
            radius = radius or "50%"
        elif self._variant == "rect":
            width = self._width or "100%"
            height = height or "80px"
            radius = radius or "8px"
        else:
            width = self._width or "100%"
            height = height or "12px"
            radius = radius or "6px"
        animation = (
            Animation(
                name="neony-skeleton-pulse",
                duration="1.4s",
                timing="ease-in-out",
                iteration_count="infinite",
            )
            if self._animation
            else None
        )
        return Styles(
            width=width,
            height=height,
            border_radius=radius,
            background_color=stub.surface_raised,
            animation=animation,
            flex_shrink="0",
        )

    def _rebuild(self) -> None:
        count = 1 if self._variant in ("rect", "circle") else self._lines
        self._root.container[:] = [Div(styles=self._line_styles()) for _ in range(count)]


class EmptyState(Component):
    """Centered empty-state guidance with an optional icon and actions."""

    def __init__(
        self,
        title: ReactiveText,
        *,
        description: ReactiveText = "",
        icon: Icon | None = None,
        actions: Sequence[Component | DOMElement] = (),
    ) -> None:
        super().__init__()
        self._title: ReactiveText = title
        self._description: ReactiveText = description
        self._icon = icon
        self._actions = list(actions)
        self._title_span = Span(
            container=[],
            styles=Styles(font_size="16px", font_weight="600", color=stub.text_primary),
        )
        self._description_span = Span(
            container=[],
            styles=Styles(font_size="13px", line_height="1.5", color=stub.text_secondary),
        )
        _mount_text(self._title_span, title)
        _mount_text(self._description_span, description)
        self._actions_row: Div | None = None
        if self._actions:
            action_nodes = [action.build() if isinstance(action, Component) else action for action in self._actions]
            self._actions_row = Div(
                styles=Styles(display="flex", gap="8px", flex_wrap="wrap", margin_top="6px"),
                container=action_nodes,
            )
        self._root = Div(
            styles=Styles(
                display="flex",
                flex_direction="column",
                align_items="center",
                justify_content="center",
                gap="10px",
                width="100%",
                padding="32px 24px",
                text_align="center",
            ),
            args={"role": "status"},
        )
        self._rebuild()

    @property
    def title(self) -> str:
        if isinstance(self._title, str):
            return self._title
        return self._title()

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        self._title_span._unbind_text()
        self._title_span.container = [value]

    @property
    def description(self) -> str:
        if isinstance(self._description, str):
            return self._description
        return self._description()

    @description.setter
    def description(self, value: str) -> None:
        self._description = value
        self._description_span._unbind_text()
        self._description_span.container = [] if value == "" else [value]
        self._rebuild()

    @property
    def icon(self) -> Icon | None:
        return self._icon

    @icon.setter
    def icon(self, value: Icon | None) -> None:
        self._icon = value
        self._rebuild()

    @property
    def actions(self) -> list[Component | DOMElement]:
        return list(self._actions)

    def _rebuild(self) -> None:
        parts: list[DOMElement] = []
        if self._icon is not None:
            rendered = self._icon.render("48px")
            rendered.styles = rendered.styles.model_copy(update={"color": stub.text_secondary})
            parts.append(rendered)
        parts.append(self._title_span)
        if self.description or not isinstance(self._description, str):
            parts.append(self._description_span)
        if self._actions_row is not None:
            parts.append(self._actions_row)
        self._root.container[:] = parts
