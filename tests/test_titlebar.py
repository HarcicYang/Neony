"""TitleBar component — window chrome for frameless windows."""

from neony.application.elements import Icon, TitleBar
from neony.dom import Div, DOMElement, Styles


def _walk(element: DOMElement) -> list[DOMElement]:
    """All elements in the tree, depth-first."""
    out: list[DOMElement] = [element]
    for child in element.container:
        if isinstance(child, DOMElement):
            out.extend(_walk(child))
    return out


class TestTitleBarIcon:
    def test_window_control_glyphs_and_hit_targets(self):
        tb = TitleBar("My App")

        for button, ligature in (
            (tb._btn_min, "remove"),
            (tb._btn_max, "crop_square"),
            (tb._btn_close, "close"),
        ):
            assert len(button.container) == 1
            icon = button.container[0]
            assert isinstance(icon, DOMElement)
            assert icon.container == [ligature]
            assert button.args["data-neony-event-scope"] == ""
            assert button.bubble_events is True

        actions = [button.args.get("data-window-action") for button in (tb._btn_min, tb._btn_max, tb._btn_close)]
        assert actions == ["minimize", "toggleMaximize", "close"]

    def test_instances_do_not_share_control_elements(self):
        first = TitleBar("First")
        second = TitleBar("Second")

        first.build()
        second.build()

    def test_icon_element_rendered_before_title(self):
        tb = TitleBar("My App", icon=Icon.image("https://example.com/icon.svg"))
        root = tb.build()

        elements = _walk(root)
        icons = [e for e in elements if e.styles.background_image is not None]

        assert len(icons) == 1
        assert icons[0].styles.background_image == "url(https://example.com/icon.svg)"
        assert icons[0].styles.width == "18px"
        assert icons[0].styles.height == "18px"

    def test_no_icon_element_without_icon(self):
        tb = TitleBar("My App")
        root = tb.build()

        elements = _walk(root)
        assert all(e.styles.background_image is None for e in elements)

    def test_icon_size_and_style_overrides(self):
        tb = TitleBar(
            "My App",
            icon=Icon.image("https://example.com/icon.svg"),
            icon_size="22px",
            icon_styles=Styles(border_radius="8px"),
        )
        root = tb.build()
        elements = _walk(root)
        icons = [e for e in elements if e.styles.background_image is not None]
        assert len(icons) == 1
        assert icons[0].styles.width == "22px"
        assert icons[0].styles.border_radius == "8px"

    def test_leading_and_trailing_slots(self):
        lead = Div(key="lead")
        trail = Div(key="trail")
        tb = TitleBar("My App", leading=[lead], trailing=[trail])

        assert tb.leading_slot is tb._left_side
        assert tb.trailing_slot is tb._right_side
        assert lead._parent is tb.leading_slot
        assert trail._parent is tb.trailing_slot
        assert tb.trailing_slot.container[0] is trail
        assert tb.trailing_slot.container[-3:] == [tb._btn_min, tb._btn_max, tb._btn_close]
