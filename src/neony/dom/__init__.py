"""Neony DOM tree builder.

Build type-safe HTML trees with inline CSS styles, then render them to strings.

Example::

    from neony.dom import Body, Div, Span, Styles, Color

    tree = Body(
        styles=Styles(background_color=Color(hex="#f0f0f0")),
        container=[
            Div(
                class_="card",
                container=[
                    Span(container=["Hello, world!"]),
                ],
            ),
        ],
    )
    print(tree.build())
"""

from .base import Color, DOMElement, Styles
from .elems import (
    # Headings
    H1,
    H2,
    H3,
    H4,
    H5,
    H6,
    # Inline text
    Anchor,
    Article,
    Aside,
    Audio,
    Blockquote,
    Body,
    Bold,
    # Void elements
    Br,
    Button,
    Canvas,
    Code,
    Details,
    # Content grouping
    Div,
    Em,
    Fieldset,
    Figcaption,
    Figure,
    Footer,
    # Forms
    Form,
    Head,
    # Semantic
    Header,
    Hr,
    # Document structure
    Html,
    # Other
    IFrame,
    Img,
    Input,
    Italic,
    Label,
    Legend,
    Link,
    ListItem,
    Main,
    Mark,
    Meta,
    Nav,
    Option,
    OrderedList,
    Paragraph,
    Pre,
    Script,
    Section,
    Select,
    Small,
    Source,
    Span,
    Strong,
    Style,
    Sub,
    Summary,
    Sup,
    # Tables
    Table,
    TableBody,
    TableData,
    TableFoot,
    TableHead,
    TableHeader,
    TableRow,
    Textarea,
    Title,
    Underline,
    # Lists
    UnorderedList,
    Video,
)

__all__ = [
    # Headings
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    # Inline
    "Anchor",
    "Article",
    "Aside",
    "Audio",
    "Blockquote",
    "Body",
    "Bold",
    # Void
    "Br",
    "Button",
    "Canvas",
    "Code",
    # Base
    "Color",
    "DOMElement",
    "Details",
    # Content
    "Div",
    "Em",
    "Fieldset",
    "Figcaption",
    "Figure",
    "Footer",
    # Forms
    "Form",
    "Head",
    # Semantic
    "Header",
    "Hr",
    # Document
    "Html",
    # Other
    "IFrame",
    "Img",
    "Input",
    "Italic",
    "Label",
    "Legend",
    "Link",
    "ListItem",
    "Main",
    "Mark",
    "Meta",
    "Nav",
    "Option",
    "OrderedList",
    "Paragraph",
    "Pre",
    "Script",
    "Section",
    "Select",
    "Small",
    "Source",
    "Span",
    "Strong",
    "Style",
    "Styles",
    "Sub",
    "Summary",
    "Sup",
    # Tables
    "Table",
    "TableBody",
    "TableData",
    "TableFoot",
    "TableHead",
    "TableHeader",
    "TableRow",
    "Textarea",
    "Title",
    "Underline",
    # Lists
    "UnorderedList",
    "Video",
]
