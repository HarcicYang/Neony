from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_serializer
from pydantic.fields import Field


class Color(BaseModel):
    """Represent a CSS color value in one of several formats.

    Serializes to the appropriate CSS string representation.
    """

    name: str | None = Field(default=None)
    rgb: tuple[int, int, int] | None = Field(default=None)
    rgba: tuple[int, int, int, float] | None = Field(default=None)
    hex: str | None = Field(default=None)

    @model_serializer
    def to_text(self) -> str:
        if self.name:
            return self.name
        elif self.rgb:
            r, g, b = self.rgb
            return f"rgb({r}, {g}, {b})"
        elif self.rgba:
            r, g, b, a = self.rgba
            return f"rgba({r}, {g}, {b}, {a})"
        elif self.hex:
            return self.hex
        else:
            raise NotImplementedError("At least one of name, rgb, rgba, or hex must be set")


class Styles(BaseModel):
    """CSS style properties for a DOM element.

    Only non-None values are rendered into the style attribute.
    """

    # --- Colors ---
    color: Color | None = Field(default=None)
    background_color: Color | None = Field(default=None)

    # --- Dimensions ---
    width: str | None = Field(default=None)
    height: str | None = Field(default=None)
    min_width: str | None = Field(default=None)
    min_height: str | None = Field(default=None)
    max_width: str | None = Field(default=None)
    max_height: str | None = Field(default=None)

    # --- Display & Layout ---
    display: Literal["block", "inline", "inline-block", "flex", "grid", "inline-flex", "none"] | None = Field(
        default=None
    )
    position: Literal["static", "relative", "absolute", "fixed", "sticky"] | None = Field(default=None)

    # --- Flexbox ---
    justify_content: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "space-between",
            "space-around",
            "space-evenly",
        ]
        | None
    ) = Field(default=None)
    align_items: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "stretch",
            "baseline",
        ]
        | None
    ) = Field(default=None)
    align_self: (
        Literal[
            "center",
            "flex-start",
            "flex-end",
            "stretch",
            "baseline",
            "auto",
        ]
        | None
    ) = Field(default=None)
    flex_direction: (
        Literal[
            "row",
            "row-reverse",
            "column",
            "column-reverse",
        ]
        | None
    ) = Field(default=None)
    flex_wrap: Literal["nowrap", "wrap", "wrap-reverse"] | None = Field(default=None)
    gap: str | None = Field(default=None)

    # --- Spacing ---
    padding: str | None = Field(default=None)
    padding_top: str | None = Field(default=None)
    padding_right: str | None = Field(default=None)
    padding_bottom: str | None = Field(default=None)
    padding_left: str | None = Field(default=None)
    margin: str | None = Field(default=None)
    margin_top: str | None = Field(default=None)
    margin_right: str | None = Field(default=None)
    margin_bottom: str | None = Field(default=None)
    margin_left: str | None = Field(default=None)

    # --- Typography ---
    font_size: str | None = Field(default=None)
    font_weight: (
        Literal[
            "100",
            "200",
            "300",
            "400",
            "500",
            "600",
            "700",
            "800",
            "900",
            "normal",
            "bold",
            "bolder",
            "lighter",
        ]
        | str
        | None
    ) = Field(default=None)
    font_family: str | None = Field(default=None)
    line_height: str | None = Field(default=None)
    text_align: (
        Literal[
            "left",
            "center",
            "right",
            "justify",
        ]
        | None
    ) = Field(default=None)
    text_decoration: (
        Literal[
            "none",
            "underline",
            "overline",
            "line-through",
        ]
        | None
    ) = Field(default=None)
    white_space: (
        Literal[
            "normal",
            "nowrap",
            "pre",
            "pre-wrap",
            "pre-line",
        ]
        | None
    ) = Field(default=None)
    word_break: (
        Literal[
            "normal",
            "break-all",
            "keep-all",
            "break-word",
        ]
        | None
    ) = Field(default=None)

    # --- Borders ---
    border: str | None = Field(default=None)
    border_radius: str | None = Field(default=None)
    border_top: str | None = Field(default=None)
    border_right: str | None = Field(default=None)
    border_bottom: str | None = Field(default=None)
    border_left: str | None = Field(default=None)

    # --- Visual ---
    opacity: float | None = Field(default=None)
    box_shadow: str | None = Field(default=None)
    overflow: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    overflow_x: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    overflow_y: (
        Literal[
            "visible",
            "hidden",
            "scroll",
            "auto",
        ]
        | None
    ) = Field(default=None)
    cursor: (
        Literal[
            "auto",
            "default",
            "pointer",
            "wait",
            "text",
            "move",
            "not-allowed",
            "grab",
            "grabbing",
        ]
        | None
    ) = Field(default=None)
    z_index: int | None = Field(default=None)


class DOMElement(BaseModel):
    """Base class for all DOM elements.

    Subclasses set ``_tag`` to the HTML tag name.
    Set ``_void = True`` for self-closing elements like ``<img />``.
    """

    model_config = {"populate_by_name": True}

    _tag: str = ""
    _void: bool = False

    # Convenience attributes for the most common HTML attributes
    id_: str | None = Field(default=None, alias="id")
    class_: str | None = Field(default=None, alias="class")

    container: list[DOMElement | str] = Field(default_factory=list)
    styles: Styles = Field(default_factory=Styles)
    args: dict[str, Any] = Field(default_factory=dict)

    # ---- internal helpers ----

    @staticmethod
    def _to_kebab(snake: str) -> str:
        """Convert ``snake_case`` to ``kebab-case``."""
        return snake.replace("_", "-")

    def _build_styles(self) -> str:
        """Build the ``style="..."`` attribute string."""
        declarations: list[str] = []
        for k, v in self.styles.model_dump().items():
            if v is not None:
                css_property = self._to_kebab(k)
                declarations.append(f"{css_property}: {v}")

        if not declarations:
            return ""
        return 'style="' + "; ".join(declarations) + '"'

    def _build_attrs(self) -> list[str]:
        """Collect all HTML attribute segments into a list.

        Returns a list of ``key="value"`` (or bare ``key`` for boolean True) strings.
        """
        attrs: list[str] = []

        # id / class convenience fields (rendered before args so args can
        # override them if the user really wants to)
        if self.id_ is not None:
            attrs.append(f'id="{self.id_}"')
        if self.class_ is not None:
            attrs.append(f'class="{self.class_}"')

        for k, v in self.args.items():
            if isinstance(v, bool):
                if v:
                    attrs.append(k)  # bare boolean attribute
            else:
                attrs.append(f'{k}="{v}"')

        return attrs

    # ---- public API ----

    def build(self) -> str:
        """Render this element and all descendants to an HTML string."""
        # Render children
        children: list[str] = []
        for item in self.container:
            if isinstance(item, DOMElement):
                children.append(item.build())
            else:
                children.append(item)

        # Build the opening tag: <tagname [style] [attrs]>
        parts: list[str] = [self._tag]

        style_str = self._build_styles()
        if style_str:
            parts.append(style_str)

        attrs = self._build_attrs()
        if attrs:
            parts.extend(attrs)

        opening = " ".join(parts)

        if self._void:
            return f"<{opening} />"

        return f"<{opening}>{''.join(children)}</{self._tag}>"
