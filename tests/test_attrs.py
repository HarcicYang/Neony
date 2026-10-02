"""Test typed HTML attribute fields on concrete element classes."""

from neony.dom import (
    Button,
    Div,
    Input,
    Styles,
)


class TestInput:
    def test_checked_false_omitted(self):
        html = Input(type="checkbox", checked=False).build()
        assert " checked" not in html
        node = Input(type="checkbox", checked=False).to_node()
        assert "checked" not in node.attrs

    def test_none_omitted(self):
        node = Input(type="text").to_node()
        assert "placeholder" not in node.attrs


class TestButton:
    def test_type_validation(self):
        node = Button(type="reset").to_node()
        assert node.attrs["type"] == "reset"


class TestPrecedence:
    """args can still override a typed field (rendered later)."""

    def test_args_override_field(self):
        node = Input(type="text", args={"type": "password"}).to_node()
        assert node.attrs["type"] == "password"


class TestScrollIndicatorDerivation:
    """``data-neony-scroll`` is auto-derived from overflow when
    ``scroll_indicator`` is on (default) and not explicitly set."""

    def test_vertical_overflow_derives_y(self):
        node = Div(styles=Styles(overflow_y="auto")).to_node()
        assert node.attrs.get("data-neony-scroll") == "y"

    def test_horizontal_overflow_derives_x(self):
        node = Div(styles=Styles(overflow_x="auto")).to_node()
        assert node.attrs.get("data-neony-scroll") == "x"

    def test_both_axes_derives_true(self):
        node = Div(styles=Styles(overflow="auto")).to_node()
        assert node.attrs.get("data-neony-scroll") == "true"

    def test_non_scrollable_derives_nothing(self):
        node = Div(styles=Styles(overflow_y="hidden")).to_node()
        assert "data-neony-scroll" not in node.attrs

    def test_scroll_indicator_false_suppresses(self):
        node = Div(styles=Styles(overflow_y="auto"), scroll_indicator=False).to_node()
        assert "data-neony-scroll" not in node.attrs

    def test_explicit_marker_respected(self):
        # An explicit args value wins over derivation.
        node = Div(styles=Styles(overflow_y="auto"), args={"data-neony-scroll": "off"}).to_node()
        assert node.attrs.get("data-neony-scroll") == "off"


class TestDragPayload:
    """``drag_payload`` makes an element draggable and serializes the
    payload the JS engine hands to ``dataTransfer.setData``."""

    def test_payload_serializes_draggable_and_marker(self):
        node = Div(key="item", drag_payload="row-1").to_node()
        # draggable is an *enumerated* attribute — the literal "true"
        # (a bare/empty value resolves to "auto" and stays un-draggable).
        assert node.attrs["draggable"] == "true"
        assert node.attrs["data-neony-drag"] == "row-1"

    def test_clear_payload_removes_marker(self):
        el = Div(drag_payload="row-1")
        assert el.drag_payload == "row-1"
        el.drag_payload = None
        node = el.to_node()
        assert "draggable" not in node.attrs
        assert "data-neony-drag" not in node.attrs
