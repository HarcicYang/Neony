"""Test DOMElement.to_node() serialization."""

import pytest

from neony.dom import (
    Br,
    Color,
    Div,
    Img,
    NodeDescriptor,
    Span,
    Styles,
)


class TestBasicSerialization:
    """Basic NodeDescriptor output."""

    def test_empty_div(self, empty_div):
        node = empty_div.to_node()
        assert isinstance(node, NodeDescriptor)
        assert node.tag == "div"
        assert node.styles == {}
        assert node.attrs == {}
        assert node.text is None
        assert node.children == []

    def test_key_is_preserved(self):
        d = Div(key="mykey")
        node = d.to_node()
        assert node.key == "mykey"


class TestStyleSerialization:
    """Styles → kebab-case dict."""

    def test_color_style(self):
        d = Div(styles=Styles(color=Color(name="red")))
        node = d.to_node()
        assert node.styles["color"] == "red"

    def test_kebab_case_conversion(self):
        d = Div(styles=Styles(background_color=Color(hex="#fff"), font_size="16px"))
        node = d.to_node()
        assert node.styles["background-color"] == "#fff"
        assert node.styles["font-size"] == "16px"

    def test_grid_template_columns(self):
        d = Div(styles=Styles(display="grid", grid_template_columns="80px 1fr"))
        node = d.to_node()
        assert node.styles["grid-template-columns"] == "80px 1fr"

    def test_none_styles_skipped(self):
        d = Div(styles=Styles(color=Color(name="blue"), width=None))
        node = d.to_node()
        assert "width" not in node.styles
        assert "color" in node.styles

    def test_user_select_emits_browser_prefixes(self):
        d = Div(styles=Styles(user_select="none"))
        node = d.to_node()
        assert node.styles["user-select"] == "none"
        assert node.styles["-webkit-user-select"] == "none"
        assert node.styles["-moz-user-select"] == "none"

    def test_user_select_none_omits_all_variants(self):
        d = Div(styles=Styles(user_select=None))
        node = d.to_node()
        assert "user-select" not in node.styles
        assert "-webkit-user-select" not in node.styles
        assert "-moz-user-select" not in node.styles


class TestAttrSerialization:
    """HTML attributes → flat dict."""

    def test_id_and_class(self):
        d = Div(id_="main", class_="container")
        node = d.to_node()
        assert node.attrs["id"] == "main"
        assert node.attrs["class"] == "container"

    def test_boolean_attr_true(self):
        d = Div(args={"disabled": True})
        node = d.to_node()
        assert node.attrs["disabled"] == ""

    def test_boolean_attr_false(self):
        d = Div(args={"disabled": False})
        node = d.to_node()
        assert "disabled" not in node.attrs


class TestChildrenSerialization:
    """Child element handling."""

    def test_nested_children(self):
        tree = Div(container=[Span(key="s", container=["text"])])
        node = tree.to_node()
        assert len(node.children) == 1
        assert node.children[0].key == "s"
        assert node.children[0].tag == "span"
        assert node.children[0].text == "text"

    def test_pure_text_folded(self):
        d = Div(container=["Hello", " ", "World"])
        node = d.to_node()
        assert node.text == "Hello World"
        assert node.children == []

    def test_mixed_content_raises(self):
        d = Div(container=["text", Span()])
        with pytest.raises(ValueError, match="mixed string and element"):
            d.to_node()


class TestVoidElements:
    """Void elements never have children or text in NodeDescriptor."""

    def test_br(self):
        b = Br()
        node = b.to_node()
        assert node.tag == "br"
        assert node.children == []
        assert node.text is None

    def test_img(self):
        i = Img(args={"src": "test.png"})
        node = i.to_node()
        assert node.tag == "img"
        assert node.children == []
        assert node.text is None
