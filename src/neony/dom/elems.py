"""Concrete HTML element classes.

Each class maps to an HTML tag.  Void (self-closing) elements like ``<img>``
have ``_void = True`` and render as ``<img ... />``.
"""

from .base import DOMElement

# ---- Document structure ----


class Html(DOMElement):
    _tag: str = "html"


class Head(DOMElement):
    _tag: str = "head"


class Title(DOMElement):
    _tag: str = "title"


class Body(DOMElement):
    _tag: str = "body"


# ---- Content grouping ----


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


# ---- Headings ----


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


# ---- Inline text semantics ----


class Anchor(DOMElement):
    _tag: str = "a"


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


# ---- Lists ----


class UnorderedList(DOMElement):
    _tag: str = "ul"


class OrderedList(DOMElement):
    _tag: str = "ol"


class ListItem(DOMElement):
    _tag: str = "li"


# ---- Tables ----


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


# ---- Forms ----


class Form(DOMElement):
    _tag: str = "form"


class Label(DOMElement):
    _tag: str = "label"


class Button(DOMElement):
    _tag: str = "button"


class Select(DOMElement):
    _tag: str = "select"


class Option(DOMElement):
    _tag: str = "option"


class Textarea(DOMElement):
    _tag: str = "textarea"


class Fieldset(DOMElement):
    _tag: str = "fieldset"


class Legend(DOMElement):
    _tag: str = "legend"


# ---- Semantic sections ----


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


class Summary(DOMElement):
    _tag: str = "summary"


# ---- Void (self-closing) elements ----


class Br(DOMElement):
    _tag: str = "br"
    _void: bool = True


class Hr(DOMElement):
    _tag: str = "hr"
    _void: bool = True


class Img(DOMElement):
    _tag: str = "img"
    _void: bool = True


class Input(DOMElement):
    _tag: str = "input"
    _void: bool = True


class Link(DOMElement):
    _tag: str = "link"
    _void: bool = True


class Meta(DOMElement):
    _tag: str = "meta"
    _void: bool = True


class Source(DOMElement):
    _tag: str = "source"
    _void: bool = True


# ---- Other ----


class IFrame(DOMElement):
    _tag: str = "iframe"


class Video(DOMElement):
    _tag: str = "video"


class Audio(DOMElement):
    _tag: str = "audio"


class Canvas(DOMElement):
    _tag: str = "canvas"


class Script(DOMElement):
    _tag: str = "script"


class Style(DOMElement):
    _tag: str = "style"
