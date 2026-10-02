"""Shared rich-choice model for menus and selection popups."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from neony.application.theme import stub
from neony.dom import DOMElement, Span, Styles

from .base import ReactiveText
from .icon import Icon


class MenuSeparator:
    """A non-selectable separator row inside a menu or choice popup."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "MenuSeparator()"


class ChoiceItem:
    """A rich string-valued choice shared by menu and selection components.

    ``str`` and ``(value, label)`` continue to be accepted by component
    constructors. Menu renders a persistent check slot when ``checked`` is
    not ``None``. ``shortcut`` is display metadata only.
    """

    __slots__ = (
        "checked",
        "danger",
        "disabled",
        "icon",
        "keywords",
        "label",
        "shortcut",
        "value",
    )

    def __init__(
        self,
        value: str,
        label: ReactiveText | None = None,
        *,
        icon: Icon | None = None,
        disabled: bool = False,
        danger: bool = False,
        shortcut: str | dict[str, str] | None = None,
        checked: bool | None = None,
        keywords: Sequence[str] = (),
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(f"ChoiceItem.value must be str, got {type(value).__name__}")
        self.value = value
        self.label = value if label is None else label
        self.icon = icon
        self.disabled = disabled
        self.danger = danger
        self.shortcut = shortcut
        self.checked = checked
        self.keywords = tuple(keywords)

    def __repr__(self) -> str:
        return (
            f"ChoiceItem({self.value!r}, {self.label!r}, disabled={self.disabled!r}, "
            f"danger={self.danger!r}, checked={self.checked!r})"
        )


ChoiceItemLike = str | tuple[str, ReactiveText] | ChoiceItem


def coerce_choice_item(entry: ChoiceItemLike) -> ChoiceItem:
    """Normalize the legacy public forms into :class:`ChoiceItem`."""
    if isinstance(entry, ChoiceItem):
        return entry
    if isinstance(entry, str):
        return ChoiceItem(entry)
    if isinstance(entry, tuple) and len(entry) == 2:
        value, label = entry
        return ChoiceItem(value, label)
    raise TypeError("choice item must be a string, (value, label) tuple, or ChoiceItem")


def resolved_shortcut(shortcut: str | dict[str, str] | None) -> str | None:
    if isinstance(shortcut, str):
        return shortcut
    if not shortcut:
        return None
    platform = "darwin" if sys.platform == "darwin" else "default"
    return shortcut.get(platform) or shortcut.get("default")


def choice_content(
    item: ChoiceItem,
    *,
    icon_size: str = "14px",
    show_shortcut: bool = False,
    show_checked: bool = False,
) -> tuple[list[DOMElement | str], Span]:
    """Build the shared leading content and return its label span."""
    content: list[DOMElement | str] = []
    if show_checked and item.checked is not None:
        check = Icon._font("check").render(icon_size)
        check.styles = check.styles.model_copy(
            update={"visibility": "visible" if item.checked else "hidden", "color": stub.text_secondary}
        )
        content.append(check)
    if item.icon is not None:
        content.append(item.icon.render(icon_size))

    label = Span(container=[], styles=Styles(flex_grow="1"))
    if isinstance(item.label, str):
        label.container = [item.label]
    else:
        label.bind_text(item.label)
    content.append(label)

    if show_shortcut:
        shortcut = resolved_shortcut(item.shortcut)
        if shortcut:
            content.append(
                Span(
                    container=[shortcut],
                    styles=Styles(
                        color=stub.text_secondary,
                        font_size="12px",
                        line_height="1",
                        margin_left="auto",
                        white_space="nowrap",
                    ),
                )
            )
    return content, label


__all__ = [
    "ChoiceItem",
    "ChoiceItemLike",
    "MenuSeparator",
    "choice_content",
    "coerce_choice_item",
    "resolved_shortcut",
]
