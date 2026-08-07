"""Card component — a titled content panel.

A card stacks an optional header (a title + subtitle, or a custom header
slot, with an optional right-aligned action row), a body of arbitrary
children, and an optional footer (commonly a right-aligned button row
above a separator).  ``glass=True`` swaps the solid surface for a
frosted-glass panel tinted by ``role``; ``clickable=True`` turns the whole
card into a clickable surface.

Card does **not** reuse :class:`GlassPanel` internally — it keeps its own
compact style constants and stays light by default (a plain surface with
a border and a soft shadow), reaching for the glass tokens only when asked.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from neony.application.theme import Theme
from neony.dom import Div, DOMElement, DomEvent, Styles

from .base import Component
from .button import Button
from .heading import Heading
from .layout import HStack, Separator, Spacer, VStack
from .text import Text

_Role = Literal["neutral", "accent", "danger", "success"]


def _build_child(item: Component | DOMElement) -> DOMElement:
    return item.build() if isinstance(item, Component) else item


_SOLID = Styles(
    display="flex",
    flex_direction="column",
    gap="16px",
    padding="20px",
    border_radius="12px",
    background_color=None,  # set below — needs a Color var
    border="1px solid var(--color-border)",
    box_shadow="0 2px 8px var(--color-shadow)",
)

_BODY = Styles(display="flex", flex_direction="column", gap="16px")


class Card(Component):
    """A titled content panel.

    - ``*body`` — the panel body (Components, DOMElements, or strings).
    - ``title`` / ``subtitle`` — auto-build a header (a Heading + optional
      secondary Text).  Ignored when ``header`` is given.
    - ``header`` — a custom header slot that replaces the title row entirely.
    - ``actions`` — buttons shown right-aligned in the header row.
    - ``footer`` — a button list (right-aligned, above a separator) or any
      content node.
    - ``glass`` — frosted-glass surface instead of the solid default.
    - ``role`` — semantic accent for the glass glow (``glass=True`` only).
    - ``clickable`` — make the card a clickable surface (``cursor: pointer``
      + click events).
    """

    #: Wired internally when ``clickable`` — ``on()`` must not wire it again.
    _bound_events: frozenset[str] = frozenset({"click"})

    def __init__(
        self,
        *body: Component | DOMElement | str,
        title: str | None = None,
        subtitle: str | None = None,
        header: Component | DOMElement | None = None,
        actions: Sequence[Button] | None = None,
        footer: Component | DOMElement | Sequence[Button] | None = None,
        glass: bool = False,
        role: _Role = "neutral",
        width: str | None = None,
        padding: str = "20px",
        gap: str = "16px",
        radius: str = "12px",
        clickable: bool = False,
    ) -> None:
        super().__init__()
        self._clickable = clickable

        # --- styles ---
        from neony.dom import Color

        card_styles = _SOLID.model_copy(
            update={
                "background_color": (
                    Color(var="--color-surface-panel-glass-bg") if glass else Color(var="--color-surface")
                ),
                "padding": padding,
                "gap": gap,
                "border_radius": radius,
            }
        )
        if glass:
            card_styles = card_styles.model_copy(
                update={
                    "backdrop_filter": "blur(16px)",
                    "border": f"1px solid {Theme.glass_border(role)}",
                }
            )
            if role != "neutral":
                card_styles = card_styles.model_copy(
                    update={"box_shadow": f"0 0 24px {Theme.glass_border(role)}, " + (card_styles.box_shadow or "")}
                )
        if width is not None:
            card_styles = card_styles.model_copy(update={"width": width})
        if clickable:
            card_styles = card_styles.model_copy(update={"cursor": "pointer"})

        # --- header ---
        header_el: DOMElement | None = None
        self._title_heading: Heading | None = None
        if header is not None:
            header_el = _build_child(header)
        elif title is not None:
            self._title_heading = Heading(title, level=4)
            title_children: list[DOMElement] = [self._title_heading.build()]
            self._subtitle_text: Text | None = None
            if subtitle is not None:
                self._subtitle_text = Text(subtitle, role="secondary")
                title_children.append(self._subtitle_text.build())
            title_block = VStack(*title_children, gap="4px").build()
            if actions:
                action_row = HStack(*actions, gap="8px")
                header_el = HStack(title_block, Spacer(), action_row, align="center", gap="12px").build()
            else:
                header_el = title_block

        # --- body ---
        body_children = [c.build() if isinstance(c, Component) else c for c in body]
        self._body = Div(styles=_BODY.model_copy(update={"gap": gap}), container=body_children)

        # --- footer ---
        footer_el: DOMElement | None = None
        if footer is not None:
            if isinstance(footer, (list, tuple)):
                footer_el = HStack(Spacer(), *footer, gap="8px").build()
            elif isinstance(footer, Component):
                footer_el = footer.build()
            elif isinstance(footer, DOMElement):
                footer_el = footer

        # --- assemble ---
        parts: list[DOMElement | str] = []
        if header_el is not None:
            parts.append(header_el)
        parts.append(self._body)
        self._separator: Separator | None = None
        if footer_el is not None:
            self._separator = Separator()
            parts.append(self._separator.build())
            parts.append(footer_el)

        self._root = Div(styles=card_styles, container=parts)
        if clickable:
            self._bind(self._root, "click")

    # ---- state ----

    @property
    def title(self) -> str | None:
        return self._title_heading.text if self._title_heading is not None else None

    @title.setter
    def title(self, value: str | None) -> None:
        if self._title_heading is not None and value is not None:
            self._title_heading.text = value

    @property
    def subtitle(self) -> str | None:
        return self._subtitle_text.text if self._subtitle_text is not None else None

    @subtitle.setter
    def subtitle(self, value: str | None) -> None:
        if self._subtitle_text is not None and value is not None:
            self._subtitle_text.text = value

    # ---- events ----

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        # No internal state to sync for a click — pass straight through.
        await self._dispatch(event_type, event)
