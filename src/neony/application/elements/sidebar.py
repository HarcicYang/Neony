"""Sidebar component — vertical navigation, glass-matched to TitleBar."""

from __future__ import annotations

from typing import Self

from neony.dom import Color, Div, DOMElement, DomEvent, Span, Styles

from .base import Component

_ITEM_BASE = Styles(
    display="flex",
    align_items="center",
    gap="10px",
    padding="10px 12px",
    border_radius="8px",
    font_size="14px",
    font_weight="500",
    cursor="pointer",
    background_color=Color(name="transparent"),
    color=Color(var="--color-text-secondary"),
    # Always-present left border avoids a layout shift on activation.
    border_left="3px solid transparent",
)

_ITEM_ACTIVE = _ITEM_BASE.model_copy(
    update={
        # Frosted like the rest of the chrome, not a flat fill.
        "background_color": Color(var="--color-surface-glass-bg"),
        "backdrop_filter": "blur(20px) saturate(1.2)",
        "color": Color(var="--color-text-primary"),
        "border_left": "3px solid var(--color-accent)",
    }
)

_GLASS = Styles(
    display="flex",
    flex_direction="column",
    gap="4px",
    padding="10px 8px",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(20px) saturate(1.2)",
    border_right="1px solid var(--color-border-glass)",
)

_SOLID = Styles(
    display="flex",
    flex_direction="column",
    gap="4px",
    padding="10px 8px",
    background_color=Color(var="--color-surface"),
    border_right="1px solid var(--color-border)",
)


class SidebarItem(Component):
    """One clickable entry in a :class:`Sidebar`; ``key`` defaults to the
    lowercased label, ``icon`` is an optional glyph shown first."""

    def __init__(
        self,
        label: str,
        *,
        key: str | None = None,
        icon: str | None = None,
        active: bool = False,
    ) -> None:
        super().__init__()
        self._label = label
        self._key = key or label.lower()
        self._icon = icon
        self._active = active
        self._hover = False

        self._root = Div(
            styles=_ITEM_ACTIVE if active else _ITEM_BASE,
            container=self._text_content(),
        )
        # Clicks land on the icon/label spans — bubble them to this item.
        self._root._bubble_events = True
        self._bind(self._root, "click")
        self._bind(self._root, "mouseover")
        self._bind(self._root, "mouseout")

    # ---- internals ----

    def _text_content(self) -> list[DOMElement | str]:
        # Element-only children (reactive mode forbids mixing).
        parts: list[DOMElement | str] = []
        if self._icon:
            parts.append(
                Span(
                    container=[self._icon],
                    styles=Styles(font_size="16px", width="20px", text_align="center"),
                )
            )
        if self._label:
            parts.append(
                Span(
                    container=[self._label],
                    styles=Styles(font_size="14px"),
                )
            )
        return parts

    def _apply_styles(self) -> None:
        styles = _ITEM_ACTIVE if self._active else _ITEM_BASE
        if self._hover and not self._active:
            styles = styles.model_copy(update={"background_color": Color(var="--color-surface")})
        self._root.styles = styles

    # ---- state ----

    @property
    def key(self) -> str:
        return self._key

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._root.container = self._text_content()

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self._apply_styles()

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "mouseover":
            self._hover = True
            self._apply_styles()
        elif event_type == "mouseout":
            self._hover = False
            self._apply_styles()
        await self._dispatch(event_type, event)


class Sidebar(Component):
    """Vertical navigation rail; exactly one item is active at a time.

    Usage::

        sidebar = Sidebar(
            SidebarItem("Home", icon="🏠"),
            SidebarItem("Settings", icon="⚙️"),
        )
        sidebar.on_change(lambda e: switch_content(e.value))  # key string
    """

    def __init__(
        self,
        *items: SidebarItem,
        width: str = "200px",
        active_key: str | None = None,
        glass: bool = True,
        corner_radius: str | None = None,
    ) -> None:
        super().__init__()
        self._width = width
        self._glass = glass
        self._corner_radius = corner_radius
        self._items: list[SidebarItem] = []
        self._active_key: str | None = None

        self._root = Div(
            styles=_GLASS if glass else _SOLID,
            container=[],
        )
        # Stretch to the full height of the chrome row it lives in.
        self._root.styles = self._root.styles.model_copy(update={"width": width, "flex_shrink": "0"})
        if corner_radius is not None:
            # Rounds the corner where the sidebar meets the titlebar.
            self._root.styles = self._root.styles.model_copy(update={"border_top_right_radius": corner_radius})

        for item in items:
            self.add(item)
        if active_key is not None:
            self.active_key = active_key

    # ---- public API ----

    def add(self, item: SidebarItem) -> Self:
        """Append an item (chainable)."""
        el = item.build()
        el.on_click(self._make_item_handler(item))
        self._items.append(item)
        self._root.container.append(el)
        if self._active_key is None:
            # First item starts active unless a key was given.
            item.active = True
            self._active_key = item.key
        else:
            item.active = item.key == self._active_key
        return self

    @property
    def items(self) -> list[SidebarItem]:
        return list(self._items)

    @property
    def active_key(self) -> str | None:
        return self._active_key

    @active_key.setter
    def active_key(self, key: str | None) -> None:
        self._active_key = key
        for item in self._items:
            item.active = item.key == key

    # ---- internals ----

    def _make_item_handler(self, item: SidebarItem):
        async def handler(event: DomEvent) -> None:
            self.active_key = item.key
            event.value = item.key
            await self._dispatch("change", event)

        return handler
