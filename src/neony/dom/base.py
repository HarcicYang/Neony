from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, PrivateAttr, model_serializer
from pydantic.fields import Field


def _new_key() -> str:
    """Generate a unique hex key for DOM element identity tracking."""
    return uuid.uuid4().hex


class Color(BaseModel):
    """Represent a CSS color value in one of several formats.

    Serializes to the appropriate CSS string representation.

    - ``name`` — CSS keyword (``"red"``, ``"white"``, ...)
    - ``hex`` — ``#RRGGBB`` / ``#RRGGBBAA`` string only
    - ``rgb`` / ``rgba`` — numeric channels
    - ``var`` — a CSS custom property reference (``"--color-surface"``),
      serialized as ``var(--color-surface)`` for themed styling
    """

    name: str | None = Field(default=None)
    rgb: tuple[int, int, int] | None = Field(default=None)
    rgba: tuple[int, int, int, float] | None = Field(default=None)
    hex: str | None = Field(default=None)
    var: str | None = Field(default=None)

    @model_serializer
    def to_text(self) -> str:
        if self.var:
            return f"var({self.var})"
        elif self.name:
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
            raise NotImplementedError("At least one of name, rgb, rgba, hex, or var must be set")


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
    top: str | None = Field(default=None)
    left: str | None = Field(default=None)
    right: str | None = Field(default=None)
    bottom: str | None = Field(default=None)

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
    flex_grow: str | None = Field(default=None)
    flex_shrink: str | None = Field(default=None)
    flex_basis: str | None = Field(default=None)
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
    # Corner-specific radii (for joining rounded chrome pieces).
    border_top_left_radius: str | None = Field(default=None)
    border_top_right_radius: str | None = Field(default=None)
    border_bottom_left_radius: str | None = Field(default=None)
    border_bottom_right_radius: str | None = Field(default=None)

    # --- Visual ---
    opacity: float | None = Field(default=None)
    box_shadow: str | None = Field(default=None)
    # Frosted-glass effect. Rendered as both backdrop-filter and
    # -webkit-backdrop-filter for WebKitGTK compatibility.
    backdrop_filter: str | None = Field(default=None)
    # Native control appearance reset (e.g. appearance: none for
    # custom-styled checkboxes) plus background layers.
    appearance: str | None = Field(default=None)
    background_image: str | None = Field(default=None)
    background_size: str | None = Field(default=None)
    background_position: str | None = Field(default=None)
    background_repeat: str | None = Field(default=None)
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


class DomEvent(BaseModel):
    """Event payload forwarded from JavaScript to a Python handler.

    *key* is the identity of the element that received the event,
    *type* is the DOM event name (``"click"``, ``"input"``, ...),
    and *value* is element-specific data (``el.value`` for inputs,
    ``el.checked`` for checkboxes, ``None`` otherwise).

    *source* distinguishes real user interaction (``"user"``) from
    programmatic value changes (``"program"``) — the latter must not
    fire user callbacks.
    """

    key: str
    type: str
    value: Any = None
    source: Literal["user", "program"] = "program"


class NodeDescriptor(BaseModel):
    """JSON-safe snapshot of one DOM element for diffing and transmission.

    Used by the reactive bridge to serialize DOM state, compute patches,
    and send tree descriptions to the JavaScript engine.
    """

    key: str
    tag: str
    attrs: dict[str, str] = Field(default_factory=dict)
    styles: dict[str, str] = Field(default_factory=dict)
    text: str | None = None
    children: list[NodeDescriptor] = Field(default_factory=list)


class DOMElement(BaseModel):
    """Base class for all DOM elements.

    Subclasses set ``_tag`` to the HTML tag name.
    Set ``_void = True`` for self-closing elements like ``<img />``.
    """

    model_config = {"populate_by_name": True}

    _tag: str = ""
    _void: bool = False

    # Stable identity for diff tracking — auto-generated once per instance.
    # Pass explicitly to preserve an element across rebuilt trees.
    key: str = Field(default_factory=_new_key)

    # Convenience attributes for the most common HTML attributes.
    # Subclasses declare more with Field(json_schema_extra={"html_attr": True}).
    id_: str | None = Field(default=None, alias="id", json_schema_extra={"html_attr": True})
    class_: str | None = Field(default=None, alias="class", json_schema_extra={"html_attr": True})

    container: list[DOMElement | str] = Field(default_factory=list)
    styles: Styles = Field(default_factory=Styles)
    args: dict[str, Any] = Field(default_factory=dict)

    # Handlers attached via the fluent .on_xxx() API. Stored as a
    # PrivateAttr so callables are never serialized.
    _handlers: dict[str, list[Callable[..., Any]]] = PrivateAttr(default_factory=dict)

    # ---- fluent event API ----

    def on(self, event_type: str, fn: Callable[..., Any]) -> DOMElement:
        """Register *fn* for *event_type* and return self for chaining.

        The handler is called with a :class:`DomEvent` when the element
        receives a matching DOM event. Collect handlers are wired up by
        :class:`~neony.application.NeonApplication`.
        """
        self._handlers.setdefault(event_type, []).append(fn)
        return self

    def on_click(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("click", fn)

    def on_dblclick(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("dblclick", fn)

    def on_input(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("input", fn)

    def on_change(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("change", fn)

    def on_submit(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("submit", fn)

    def on_keydown(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("keydown", fn)

    def on_keyup(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("keyup", fn)

    def on_focus(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("focus", fn)

    def on_blur(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("blur", fn)

    def on_mouseover(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mouseover", fn)

    def on_mouseout(self, fn: Callable[..., Any]) -> DOMElement:
        return self.on("mouseout", fn)

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
                # WebKitGTK needs the prefixed variant of backdrop-filter
                if css_property == "backdrop-filter":
                    declarations.append(f"-webkit-backdrop-filter: {v}")

        if not declarations:
            return ""
        return 'style="' + "; ".join(declarations) + '"'

    def _collect_attr_items(self) -> list[tuple[str, Any]]:
        """Collect all HTML attributes as ``(html_name, value)`` pairs.

        Typed fields declared with ``json_schema_extra={"html_attr": True}``
        come first (in declaration order), then raw ``args`` — so ``args``
        can still override a typed field if the user really wants to.
        """
        items: list[tuple[str, Any]] = []
        for name, field in type(self).model_fields.items():
            extra = field.json_schema_extra
            if isinstance(extra, dict) and extra.get("html_attr"):
                value = getattr(self, name)
                if value is not None:
                    html_name = field.alias or name
                    items.append((html_name, value))
        for k, v in self.args.items():
            items.append((k, v))
        return items

    def _build_attrs(self) -> list[str]:
        """Collect all HTML attribute segments into a list.

        Returns a list of ``key="value"`` (or bare ``key`` for boolean True) strings.
        """
        attrs: list[str] = []

        # data-neony-key for DOM identity (always rendered)
        attrs.append(f'data-neony-key="{self.key}"')

        for name, value in self._collect_attr_items():
            if isinstance(value, bool):
                if value:
                    attrs.append(name)  # bare boolean attribute
            else:
                attrs.append(f'{name}="{value}"')

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

    # ---- serialization for reactive bridge ----

    def to_node(self) -> NodeDescriptor:
        """Serialize this element and all descendants to a JSON-safe NodeDescriptor.

        Raises ValueError if duplicate keys are found anywhere in the tree,
        or if ``container`` mixes strings and elements.
        """
        seen_keys: set[str] = set()
        node = self._to_node_impl(seen_keys)
        return node

    def _to_node_impl(self, seen_keys: set[str]) -> NodeDescriptor:
        if self.key in seen_keys:
            raise ValueError(f"Duplicate key {self.key!r} in DOM tree. Each element must have a unique key.")
        seen_keys.add(self.key)

        # Styles: kebab-case keys, string values, skip None
        styles: dict[str, str] = {}
        for k, v in self.styles.model_dump().items():
            if v is not None:
                css_property = self._to_kebab(k)
                styles[css_property] = str(v)
                # WebKitGTK needs the prefixed variant of backdrop-filter
                if css_property == "backdrop-filter":
                    styles["-webkit-backdrop-filter"] = str(v)

        # Attrs: same precedence as _build_attrs (typed fields, then args)
        attrs: dict[str, str] = {}
        for name, value in self._collect_attr_items():
            if isinstance(value, bool):
                if value:
                    attrs[name] = ""  # boolean attribute presence
            else:
                attrs[name] = str(value)

        # Children: recurse, handle text-vs-element rules
        text: str | None = None
        children: list[NodeDescriptor] = []

        has_strings = False
        has_elements = False
        for item in self.container:
            if isinstance(item, DOMElement):
                has_elements = True
            else:
                has_strings = True

        if has_strings and has_elements:
            raise ValueError(
                f"Element {self.key!r} ({self._tag}): mixed string and element "
                f"children are not supported in reactive mode. "
                f"Use text-only or element-only children."
            )

        if self._void:
            # Void elements have no children
            pass
        elif has_strings:
            text = "".join(str(item) for item in self.container)
        else:
            for item in self.container:
                if isinstance(item, DOMElement):
                    children.append(item._to_node_impl(seen_keys))

        return NodeDescriptor(
            key=self.key,
            tag=self._tag,
            attrs=attrs,
            styles=styles,
            text=text,
            children=children,
        )
