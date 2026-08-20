"""Built-in semantic icon namespace.

Use the public :data:`stub`; the catalog implementation deliberately
remains private.  Every built-in icon is rendered by Neony's self-hosted
Material Symbols Rounded font, so it is offline and visually consistent on
all supported platforms.
"""

from __future__ import annotations

from typing import ClassVar

from neony.application.elements.icon import Icon


def _font_icon(name: str) -> Icon:
    """Build one private, themed font-icon descriptor.

    Material Symbols uses standard OpenType ligatures: the semantic name is
    the text payload and the bundled font resolves it to the matching glyph.
    """
    return Icon._font(name)


class _IconsStub:
    """Typed public namespace for Neony's built-in icons.

    This is intentionally a stub, like :mod:`neony.application.theme`'s
    ``stub``: it exposes immutable, prebuilt descriptors and not a mutable
    catalog class.  User code imports :data:`stub` (or the application-level
    ``icons`` alias) only.
    """

    # Navigation / application
    home: ClassVar[Icon] = _font_icon("home")
    settings: ClassVar[Icon] = _font_icon("settings")
    person: ClassVar[Icon] = _font_icon("person")
    search: ClassVar[Icon] = _font_icon("search")
    menu: ClassVar[Icon] = _font_icon("menu")
    close: ClassVar[Icon] = _font_icon("close")

    # Actions
    add: ClassVar[Icon] = _font_icon("add")
    check: ClassVar[Icon] = _font_icon("check")
    edit: ClassVar[Icon] = _font_icon("edit")
    delete: ClassVar[Icon] = _font_icon("delete")
    content_copy: ClassVar[Icon] = _font_icon("content_copy")
    refresh: ClassVar[Icon] = _font_icon("refresh")
    star: ClassVar[Icon] = _font_icon("star")

    # Direction / disclosure
    chevron_left: ClassVar[Icon] = _font_icon("chevron_left")
    chevron_right: ClassVar[Icon] = _font_icon("chevron_right")
    expand_more: ClassVar[Icon] = _font_icon("expand_more")
    expand_less: ClassVar[Icon] = _font_icon("expand_less")
    arrow_upward: ClassVar[Icon] = _font_icon("arrow_upward")
    arrow_downward: ClassVar[Icon] = _font_icon("arrow_downward")
    unfold_more: ClassVar[Icon] = _font_icon("unfold_more")

    # Status / content
    info: ClassVar[Icon] = _font_icon("info")
    warning: ClassVar[Icon] = _font_icon("warning")
    error: ClassVar[Icon] = _font_icon("error")
    favorite: ClassVar[Icon] = _font_icon("favorite")
    chat: ClassVar[Icon] = _font_icon("chat")


#: Public semantic icon namespace.  Do not import its private implementation.
stub = _IconsStub()

__all__ = ["stub"]
