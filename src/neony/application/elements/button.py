"""Button component — themed, glass-tinted, chainable events."""

from __future__ import annotations

from typing import Literal

from neony.application.theme import Theme, stub
from neony.dom import BoxShadow, Color, DOMElement, DomEvent, Shadow, Span, Styles, Transition
from neony.dom import Button as _ButtonElem

from .base import Component, ReactiveText, _mount_text


class Button(Component):
    #: Event types wired internally (via _bind / custom handlers) —
    #: Component.on() must not wire these again.
    _bound_events: frozenset[str] = frozenset(
        {"click", "mouseover", "mouseout", "mousedown", "mouseup", "focus", "blur"}
    )

    """A themed push button with hover / press feedback.

    ``variant`` selects a token-based palette: ``"primary"`` (accent bg),
    ``"ghost"`` (transparent, bordered), ``"danger"`` (danger accent).
    Hovering lifts the button; pressing dims and compresses it.
    """

    def __init__(
        self,
        label: ReactiveText = "",
        *,
        variant: Literal["primary", "ghost", "danger"] = "primary",
        glass: bool = False,
        disabled: bool = False,
        icon: str | None = None,
    ) -> None:
        super().__init__()
        self._label = label
        self._icon = icon
        self._disabled = disabled
        self._variant = variant
        self._glass = glass
        self._hover = False
        self._pressed = False
        self._focused = False
        self._custom_styles: Styles | None = None

        # Semantic role for glow colouring (ghost → surface, subtle).
        self._role = {"primary": "accent", "ghost": "surface"}.get(variant, variant)

        # The label (and icon) are child spans: reactive labels bind to
        # the label span (a raw string child can't subscribe), and
        # ``bubble_events`` lets clicks/hovers on those spans reach the
        # button's own handlers.
        self._icon_span: Span | None = Span(container=[icon]) if icon else None
        self._label_span = Span(container=[])
        _mount_text(self._label_span, label)

        self._btn = _ButtonElem(
            type="button",
            container=self._text_content(),
            styles=self._variant_styles(variant, glass),
            disabled=disabled,
        )
        self._btn.bubble_events = True

        self._root = self._btn
        self._bind(self._btn, "click")
        self._bind(self._btn, "mouseover")
        self._bind(self._btn, "mouseout")
        self._bind(self._btn, "mousedown")
        self._bind(self._btn, "mouseup")
        self._bind(self._btn, "focus")
        self._bind(self._btn, "blur")

    def reset_styles(self, styles: Styles) -> Button:
        """Replace the base styles; hover/press effects still apply on top."""
        self._custom_styles = styles
        self._apply_state()
        return self

    # ---- internals ----

    def _text_content(self) -> list[DOMElement | str]:
        parts: list[DOMElement | str] = []
        if self._icon_span is not None:
            parts.append(self._icon_span)
        parts.append(self._label_span)
        return parts

    @staticmethod
    def _variant_styles(variant: str, glass: bool = False) -> Styles:
        # border: none kills WebKitGTK's default 2px outset border.
        base = Styles(
            padding="10px 20px",
            border_radius="8px",
            border="none",
            font_size="14px",
            font_weight="500",
            cursor="pointer",
            transition=Transition(duration="0.15s", timing="ease"),
            color=stub.text_primary,
        )

        if glass:
            # Frosted version of the variant's own colour.
            role = {"primary": "accent", "ghost": "surface"}.get(variant, variant)
            # Saturated roles need their contrasting on-* text colour; the
            # neutral ghost sits on a surface and keeps the body text colour.
            fg = Color(var=f"--color-on-{role}") if role in ("accent", "danger") else stub.text_primary
            return base.model_copy(
                update={
                    "background_color": Color(var=f"--color-{role}-glass-bg"),
                    "color": fg,
                    "backdrop_filter": "blur(12px)",
                    "border": f"1px solid {Theme.glass_border(role)}",
                    "box_shadow": ("0 2px 12px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.04)"),
                }
            )

        if variant == "ghost":
            return base.model_copy(
                update={
                    "background_color": stub.surface,
                    "border": "1px solid var(--color-border)",
                }
            )
        if variant == "danger":
            return base.model_copy(
                update={
                    "background_color": stub.danger,
                    "color": stub.on_danger,
                }
            )
        return base.model_copy(
            update={
                "background_color": stub.accent,
                "color": stub.on_accent,
            }
        )

    def _apply_state(self) -> None:
        """Recompute the button styles from variant + hover + pressed + focus."""
        base = (
            self._custom_styles if self._custom_styles is not None else self._variant_styles(self._variant, self._glass)
        )
        styles = base.model_copy()
        if self._pressed:
            styles = styles.model_copy(
                update={
                    "opacity": 0.8,
                    "box_shadow": BoxShadow(
                        layers=[Shadow(inset=True, y=2, blur=6, color=Color(rgba=(0, 0, 0, 0.25)))]
                    ),
                }
            )
        else:
            update: dict[str, object] = {}
            layers: list[Shadow] = []
            if self._focused:
                # Focus ring first so it renders on top.
                layers.append(Theme.focus_glow(self._role).layers[0])
            if self._hover:
                update["opacity"] = 0.92
                layers.append(Shadow(x=0, y=4, blur=16, color=stub.shadow))
                # Colour-matched glow — the lift reads as the element's
                # own colour.
                glow = {
                    "accent": stub.accent_glass,
                    "danger": stub.danger_glass,
                    "success": stub.success_glass,
                }.get(self._role, stub.border_glass)
                layers.append(Shadow(x=0, y=0, blur=20, color=glow))
            if layers:
                update["box_shadow"] = BoxShadow(layers=layers)
                styles = styles.model_copy(update=update)
        if self._disabled:
            styles = styles.model_copy(update={"opacity": 0.5})
        self._btn.styles = styles

    # ---- state ----

    @property
    def label(self) -> str:
        if isinstance(self._label, str):
            return self._label
        return self._label()

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._label_span.container = [value]

    @property
    def icon(self) -> str | None:
        return self._icon

    @icon.setter
    def icon(self, value: str | None) -> None:
        self._icon = value
        if self._icon_span is not None:
            if value:
                self._icon_span.container = [value]
            else:
                self._icon_span = None
                self._btn.container = self._text_content()
        elif value:
            self._icon_span = Span(container=[value])
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
        elif event_type == "focus":
            self._focused = True
            self._apply_state()
        elif event_type == "blur":
            self._focused = False
            self._apply_state()
        await self._dispatch(event_type, event)
