"""Text component — body copy with theme-aware colours."""

from __future__ import annotations

from neony.dom import Color, Span, Styles

from .base import Component


class Text(Component):
    """Inline text with a semantic colour role.

    ``role`` selects a token-based colour:

    - ``"primary"`` — default text
    - ``"secondary"`` — muted / less important
    - ``"danger"`` — error or destructive emphasis
    - ``"success"`` — confirmation emphasis
    """

    def __init__(
        self,
        text: str = "",
        *,
        role: str = "primary",
        size: str | None = None,
        weight: str | None = None,
    ) -> None:
        super().__init__()
        self._text = text
        self._root = Span(
            container=[text],
            styles=Styles(
                color=self._role_color(role),
                font_size=size,
                font_weight=weight,
            ),
        )

    @staticmethod
    def _role_color(role: str) -> Color:
        if role == "secondary":
            return Color(var="--color-text-secondary")
        if role == "danger":
            return Color(var="--color-danger")
        if role == "success":
            return Color(var="--color-success")
        return Color(var="--color-text-primary")

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._root.container = [value]
