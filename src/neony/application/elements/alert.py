"""Inline Alert component with semantic variants and dismissal."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Self

from neony.application.theme import stub
from neony.dom import Border, Color, Div, DOMElement, DomEvent, Span, Styles
from neony.dom import Button as _ButtonElem

from .base import Component, ReactiveText, _mount_text
from .icon import Icon

_Variant = Literal["accent", "success", "danger", "neutral"]

_ROOT = Styles(
    display="flex",
    align_items="flex-start",
    gap="12px",
    width="100%",
    padding="14px 16px",
    border_radius="8px",
    background_color=stub.surface_raised,
    color=stub.text_primary,
    border=Border(width="0", color=stub.border),
)
_CONTENT = Styles(display="flex", flex_direction="column", gap="4px", flex_grow="1", min_width="0")
_TITLE = Styles(font_size="14px", font_weight="600", color=stub.text_primary)
_DESCRIPTION = Styles(font_size="13px", line_height="1.5", color=stub.text_secondary)
_ACTIONS = Styles(display="flex", align_items="center", gap="8px", flex_wrap="wrap", margin_top="6px")
_CLOSE = Styles(
    display="flex",
    align_items="center",
    justify_content="center",
    width="28px",
    height="28px",
    padding="0",
    border="none",
    border_radius="6px",
    background_color=Color(name="transparent"),
    color=stub.text_secondary,
    cursor="pointer",
    flex_shrink="0",
)


def _variant_color(variant: _Variant) -> Color:
    return {
        "accent": stub.accent,
        "success": stub.success,
        "danger": stub.danger,
        "neutral": stub.text_secondary,
    }[variant]


def _variant_icon(variant: _Variant) -> Icon:
    return {
        "accent": Icon._font("info"),
        "success": Icon._font("check_circle"),
        "danger": Icon._font("error"),
        "neutral": Icon._font("info"),
    }[variant]


class Alert(Component):
    """A semantic inline message with optional actions and dismissal.

    ``dismiss()`` and ``dismissed = True`` both hide the alert and fire
    the lifecycle ``on_dismiss`` pseudo-event, matching Dialog's
    programmatic lifecycle semantics.
    """

    def __init__(
        self,
        title: ReactiveText = "",
        *,
        description: ReactiveText = "",
        variant: _Variant = "neutral",
        dismissible: bool = False,
        dismiss_label: str = "Dismiss",
        actions: Sequence[Component | DOMElement] = (),
    ) -> None:
        if variant not in ("accent", "success", "danger", "neutral"):
            raise ValueError(f"Alert: unknown variant {variant!r}")
        super().__init__()
        self._title: ReactiveText = title
        self._description: ReactiveText = description
        self._variant: _Variant = variant
        self._dismissible = dismissible
        self._dismiss_label = dismiss_label
        self._dismissed = False

        self._icon_span = Span(
            container=[_variant_icon(variant).render("18px")],
            styles=Styles(color=_variant_color(variant)),
        )
        self._title_span = Span(container=[], styles=_TITLE)
        self._description_span = Span(container=[], styles=_DESCRIPTION)
        _mount_text(self._title_span, title)
        _mount_text(self._description_span, description)
        content_children: list[DOMElement] = [self._title_span, self._description_span]
        action_nodes = [item.build() if isinstance(item, Component) else item for item in actions]
        if action_nodes:
            content_children.append(Div(styles=_ACTIONS, container=action_nodes))
        self._content = Div(styles=_CONTENT, container=content_children)

        parts: list[DOMElement] = [self._icon_span, self._content]
        self._close_button: _ButtonElem | None = None
        if dismissible:
            close_icon = Icon._font("close").render("16px")
            close_icon.bubble_events = True
            self._close_button = _ButtonElem(
                type="button",
                container=[close_icon],
                styles=_CLOSE,
                args={"aria-label": dismiss_label},
            )
            self._close_button.bubble_events = True
            self._bind(self._close_button, "click")
            parts.append(self._close_button)

        self._root = Div(
            styles=self._variant_styles(variant),
            args={"role": "alert"},
            container=parts,
        )

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
        if value:
            self._description_span.container = [value]
        else:
            self._description_span.container = []

    @property
    def variant(self) -> _Variant:
        return self._variant

    @variant.setter
    def variant(self, value: _Variant) -> None:
        if value not in ("accent", "success", "danger", "neutral"):
            raise ValueError(f"Alert.variant: unknown variant {value!r}")
        self._variant = value
        self._root.styles = self._variant_styles(value)
        self._icon_span.container = [_variant_icon(value).render("18px")]
        self._icon_span.styles = Styles(color=_variant_color(value))

    @property
    def dismissed(self) -> bool:
        return self._dismissed

    @dismissed.setter
    def dismissed(self, value: bool) -> None:
        if value == self._dismissed:
            return
        self._dismissed = value
        self._root.styles = self._variant_styles(self._variant, dismissed=value)
        if value:
            self._dispatch_pseudo("dismiss", self)

    def dismiss(self) -> None:
        """Dismiss the alert idempotently."""
        self.dismissed = True

    def on_dismiss(self, fn) -> Self:
        """Register a callback for programmatic or user dismissal."""
        return self.on("dismiss", fn)

    @staticmethod
    def _variant_styles(variant: _Variant, *, dismissed: bool = False) -> Styles:
        return _ROOT.model_copy(
            update={
                "display": "none" if dismissed else "flex",
                "border_left": Border(width="3px", color=_variant_color(variant)),
            }
        )

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        # The handler is attached only to the close button; bubbling can
        # leave event.key pointing at its icon span, so click means close.
        if event_type == "click" and self._close_button is not None:
            self.dismiss()
        await self._dispatch(event_type, event)
