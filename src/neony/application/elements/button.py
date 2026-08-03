"""Button component — themed, glass-tinted, chainable events."""

from __future__ import annotations

from typing import Literal

from neony.dom import Button as _ButtonElem
from neony.dom import Color, DOMElement, DomEvent, Styles

from .base import Component


class Button(Component):
    """A themed push button with hover / press feedback.

    ``variant`` selects a token-based palette:

    - ``"primary"`` — accent background
    - ``"ghost"`` — transparent with border (boundary weakening)
    - ``"danger"`` — danger accent

    Hovering lifts the button (shadow); pressing dims and compresses it.
    """

    def __init__(
        self,
        label: str = "",
        *,
        variant: Literal["primary", "ghost", "danger"] = "primary",
        disabled: bool = False,
        icon: str | None = None,
    ) -> None:
        super().__init__()
        self._label = label
        self._icon = icon
        self._disabled = disabled
        self._variant = variant
        self._hover = False
        self._pressed = False
        self._custom_styles: Styles | None = None

        self._btn = _ButtonElem(
            type="button",
            container=self._text_content(),
            styles=self._variant_styles(variant),
            disabled=disabled,
        )

        self._root = self._btn
        self._bind(self._btn, "click")
        self._bind(self._btn, "mouseover")
        self._bind(self._btn, "mouseout")
        self._bind(self._btn, "mousedown")
        self._bind(self._btn, "mouseup")

    def reset_styles(self, styles: Styles) -> Button:
        """Replace the base styles; hover/press effects still apply on top."""
        self._custom_styles = styles
        self._apply_state()
        return self

    # ---- internals ----

    def _text_content(self) -> list[DOMElement | str]:
        parts: list[DOMElement | str] = []
        if self._icon:
            parts.append(self._icon)
        if self._label:
            parts.append(self._label)
        return parts

    @staticmethod
    def _variant_styles(variant: str) -> Styles:
        # border: none kills the WebKitGTK default 2px outset border;
        # ghost re-adds its own hairline border.
        base = Styles(
            padding="10px 20px",
            border_radius="8px",
            border="none",
            font_size="14px",
            font_weight="500",
            cursor="pointer",
            transition="all 0.15s ease",
            color=Color(var="--color-text-primary"),
        )
        if variant == "ghost":
            return base.model_copy(
                update={
                    "background_color": Color(var="--color-surface"),
                    "border": "1px solid var(--color-border)",
                }
            )
        if variant == "danger":
            return base.model_copy(update={"background_color": Color(var="--color-danger")})
        return base.model_copy(update={"background_color": Color(var="--color-accent")})

    def _apply_state(self) -> None:
        """Recompute the button styles from variant + hover + pressed."""
        base = self._custom_styles if self._custom_styles is not None else self._variant_styles(self._variant)
        styles = base.model_copy()
        if self._pressed:
            styles = styles.model_copy(
                update={
                    "opacity": 0.8,
                    "box_shadow": "inset 0 2px 6px rgba(0, 0, 0, 0.25)",
                }
            )
        elif self._hover:
            styles = styles.model_copy(
                update={
                    "box_shadow": "0 4px 16px var(--color-shadow)",
                    "opacity": 0.92,
                }
            )
        if self._disabled:
            styles = styles.model_copy(update={"opacity": 0.5})
        self._btn.styles = styles

    # ---- state ----

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._btn.container = self._text_content()

    @property
    def icon(self) -> str | None:
        return self._icon

    @icon.setter
    def icon(self, value: str | None) -> None:
        self._icon = value
        self._btn.container = self._text_content()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._btn.disabled = value
        self._apply_state()

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            self._hover = True
            self._apply_state()
        elif event_type == "mouseout":
            self._hover = False
            self._pressed = False
            self._apply_state()
        elif event_type == "mousedown":
            self._pressed = True
            self._apply_state()
        elif event_type == "mouseup":
            self._pressed = False
            self._apply_state()
        await self._dispatch(event_type, event)
