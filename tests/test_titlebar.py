"""TitleBar component — window chrome for frameless windows."""

from neony.application.elements import Icon, TitleBar
from neony.dom import DOMElement


def _walk(element: DOMElement) -> list[DOMElement]:
    """All elements in the tree, depth-first."""
    out: list[DOMElement] = [element]
    for child in element.container:
        if isinstance(child, DOMElement):
            out.extend(_walk(child))
    return out


class TestTitleBarIcon:
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
