"""Concrete HTML element classes — one class per tag; void elements
have ``_void = True``.  Typed HTML attributes use
``json_schema_extra={"html_attr": True}``; anything else goes through
the generic ``args`` dict."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import DOMElement

# ---- document structure ----


class Html(DOMElement):
    _tag: str = "html"


class Head(DOMElement):
    _tag: str = "head"


class Title(DOMElement):
    _tag: str = "title"


class Body(DOMElement):
    _tag: str = "body"


# ---- content grouping ----


class Div(DOMElement):
    _tag: str = "div"


class Span(DOMElement):
    _tag: str = "span"


class Paragraph(DOMElement):
    _tag: str = "p"


class Pre(DOMElement):
    _tag: str = "pre"


class Blockquote(DOMElement):
    _tag: str = "blockquote"


# ---- headings ----


class H1(DOMElement):
    _tag: str = "h1"


class H2(DOMElement):
    _tag: str = "h2"


class H3(DOMElement):
    _tag: str = "h3"


class H4(DOMElement):
    _tag: str = "h4"


class H5(DOMElement):
    _tag: str = "h5"


class H6(DOMElement):
    _tag: str = "h6"


# ---- inline text semantics ----


class Anchor(DOMElement):
    """Hyperlink with typed ``href`` / ``target`` / ``rel`` attributes."""

    _tag: str = "a"

    href: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    target: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    rel: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    download: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    hreflang: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    referrerpolicy: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Strong(DOMElement):
    _tag: str = "strong"


class Em(DOMElement):
    _tag: str = "em"


class Bold(DOMElement):
    _tag: str = "b"


class Italic(DOMElement):
    _tag: str = "i"


class Underline(DOMElement):
    _tag: str = "u"


class Small(DOMElement):
    _tag: str = "small"


class Mark(DOMElement):
    _tag: str = "mark"


class Code(DOMElement):
    _tag: str = "code"


class Sub(DOMElement):
    _tag: str = "sub"


class Sup(DOMElement):
    _tag: str = "sup"


# ---- lists ----


class UnorderedList(DOMElement):
    _tag: str = "ul"


class OrderedList(DOMElement):
    _tag: str = "ol"


class ListItem(DOMElement):
    _tag: str = "li"


# ---- tables ----


class Table(DOMElement):
    _tag: str = "table"


class TableHead(DOMElement):
    _tag: str = "thead"


class TableBody(DOMElement):
    _tag: str = "tbody"


class TableFoot(DOMElement):
    _tag: str = "tfoot"


class TableRow(DOMElement):
    _tag: str = "tr"


class TableHeader(DOMElement):
    _tag: str = "th"


class TableData(DOMElement):
    _tag: str = "td"


# ---- forms ----


class Form(DOMElement):
    _tag: str = "form"

    action: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    method: Literal["get", "post", "dialog"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    enctype: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    target: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    novalidate: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autocomplete: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Label(DOMElement):
    _tag: str = "label"

    for_: str | None = Field(default=None, alias="for", json_schema_extra={"html_attr": True})


class Button(DOMElement):
    _tag: str = "button"

    type: Literal["submit", "reset", "button"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    value: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autofocus: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    form: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    formaction: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Select(DOMElement):
    _tag: str = "select"

    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    multiple: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    size: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    required: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autofocus: bool | None = Field(default=None, json_schema_extra={"html_attr": True})


class Option(DOMElement):
    _tag: str = "option"

    value: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    label: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    selected: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})


class Textarea(DOMElement):
    """Multiline text input.  ``value`` is a Python-side record only —
    content renders via ``container``, and the live value is read back
    through events.  Deliberately NOT an HTML attribute."""

    _tag: str = "textarea"

    value: str | None = Field(default=None)
    placeholder: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    rows: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    cols: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    maxlength: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    readonly: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    required: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autofocus: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    spellcheck: bool | None = Field(default=None, json_schema_extra={"html_attr": True})


class Fieldset(DOMElement):
    _tag: str = "fieldset"

    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    form: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Legend(DOMElement):
    _tag: str = "legend"


# ---- semantic sections ----


class Header(DOMElement):
    _tag: str = "header"


class Footer(DOMElement):
    _tag: str = "footer"


class Main(DOMElement):
    _tag: str = "main"


class Nav(DOMElement):
    _tag: str = "nav"


class Section(DOMElement):
    _tag: str = "section"


class Article(DOMElement):
    _tag: str = "article"


class Aside(DOMElement):
    _tag: str = "aside"


class Figure(DOMElement):
    _tag: str = "figure"


class Figcaption(DOMElement):
    _tag: str = "figcaption"


class Details(DOMElement):
    _tag: str = "details"

    open: bool | None = Field(default=None, json_schema_extra={"html_attr": True})


class Summary(DOMElement):
    _tag: str = "summary"


# ---- void (self-closing) elements ----


class Br(DOMElement):
    _tag: str = "br"
    _void: bool = True


class Hr(DOMElement):
    _tag: str = "hr"
    _void: bool = True


class Img(DOMElement):
    """Image with typed ``src`` / ``alt`` / ``width`` / ``height``."""

    _tag: str = "img"
    _void: bool = True

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    alt: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    width: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})
    height: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})
    loading: Literal["lazy", "eager"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    decoding: Literal["sync", "async", "auto"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    crossorigin: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    referrerpolicy: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Input(DOMElement):
    """Form input; boolean attrs render bare when ``True``, omitted when
    ``False``/``None``."""

    _tag: str = "input"
    _void: bool = True

    type: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    placeholder: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    value: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    checked: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    disabled: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    readonly: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    required: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autofocus: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autocomplete: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    maxlength: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    min: str | int | float | None = Field(default=None, json_schema_extra={"html_attr": True})
    max: str | int | float | None = Field(default=None, json_schema_extra={"html_attr": True})
    step: str | int | float | None = Field(default=None, json_schema_extra={"html_attr": True})
    accept: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    form: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Link(DOMElement):
    _tag: str = "link"
    _void: bool = True

    rel: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    href: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    type: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    media: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    sizes: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    integrity: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    crossorigin: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Meta(DOMElement):
    _tag: str = "meta"
    _void: bool = True

    charset: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    name: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    content: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    http_equiv: str | None = Field(default=None, alias="http-equiv", json_schema_extra={"html_attr": True})


class Source(DOMElement):
    _tag: str = "source"
    _void: bool = True

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    srcset: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    type: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    media: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    sizes: str | None = Field(default=None, json_schema_extra={"html_attr": True})


# ---- other ----


class IFrame(DOMElement):
    _tag: str = "iframe"

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    width: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})
    height: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})
    title: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    allow: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    sandbox: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    loading: Literal["lazy", "eager"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    allowfullscreen: bool | None = Field(default=None, json_schema_extra={"html_attr": True})


class Video(DOMElement):
    _tag: str = "video"

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    poster: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    controls: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autoplay: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    loop: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    muted: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    preload: Literal["none", "metadata", "auto"] | None = Field(default=None, json_schema_extra={"html_attr": True})
    width: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})
    height: int | str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Audio(DOMElement):
    _tag: str = "audio"

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    controls: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    autoplay: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    loop: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    muted: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    preload: Literal["none", "metadata", "auto"] | None = Field(default=None, json_schema_extra={"html_attr": True})


class Canvas(DOMElement):
    _tag: str = "canvas"

    width: int | None = Field(default=None, json_schema_extra={"html_attr": True})
    height: int | None = Field(default=None, json_schema_extra={"html_attr": True})


class Script(DOMElement):
    _tag: str = "script"

    src: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    type: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    defer: bool | None = Field(default=None, json_schema_extra={"html_attr": True})
    async_: bool | None = Field(default=None, alias="async", json_schema_extra={"html_attr": True})
    integrity: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    crossorigin: str | None = Field(default=None, json_schema_extra={"html_attr": True})


class Style(DOMElement):
    _tag: str = "style"

    media: str | None = Field(default=None, json_schema_extra={"html_attr": True})
    type: str | None = Field(default=None, json_schema_extra={"html_attr": True})
