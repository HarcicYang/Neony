"""Test fixtures for Neony test suite."""

import pytest

from neony.dom import (
    Body,
    Color,
    Div,
    Html,
    NodeDescriptor,
    Span,
    Styles,
)


@pytest.fixture
def empty_div():
    """A bare Div with no attributes."""
    return Div()


@pytest.fixture
def styled_div():
    """A Div with inline styles."""
    return Div(
        key="styled",
        styles=Styles(
            color=Color(name="red"),
            font_size="16px",
            display="flex",
        ),
    )


@pytest.fixture
def nested_tree():
    """Html > Body > Div > Span('Hello')."""
    return Html(
        key="html",
        container=[
            Body(
                key="body",
                container=[
                    Div(
                        key="card",
                        class_="container",
                        container=[
                            Span(key="text", container=["Hello, World!"]),
                        ],
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def simple_node():
    """A simple NodeDescriptor for diff tests."""
    return NodeDescriptor(key="root", tag="div")


@pytest.fixture
def node_with_text():
    """NodeDescriptor with text content."""
    return NodeDescriptor(key="t", tag="span", text="hello")


@pytest.fixture
def node_with_children():
    """NodeDescriptor with two children."""
    return NodeDescriptor(
        key="parent",
        tag="ul",
        children=[
            NodeDescriptor(key="a", tag="li", text="A"),
            NodeDescriptor(key="b", tag="li", text="B"),
        ],
    )


@pytest.fixture
def node_with_styles():
    """NodeDescriptor with styles."""
    return NodeDescriptor(key="s", tag="div", styles={"color": "red", "font-size": "16px"})


@pytest.fixture
def node_with_attrs():
    """NodeDescriptor with attributes."""
    return NodeDescriptor(key="a", tag="input", attrs={"type": "text", "disabled": ""})
