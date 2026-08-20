"""Built-in semantic icon namespace and font resource tests."""

import asyncio

from neony.application import Config, NeonApplication, icons
from neony.application._helpers import _Entry
from neony.application.elements import Button, Icon
from neony.application.icon_font import css
from neony.dom import Div, Span
from neony.dom.bridge import Neony


def test_public_namespace_exposes_stub_icons():
    assert isinstance(icons.home, Icon)
    assert icons.home.kind == "font"
    assert icons.home.src == "home"


def test_font_icon_has_stable_square_and_font_settings():
    span = icons.settings.render("14px")
    assert span.container == ["settings"]
    assert span.styles.width == "14px"
    assert span.styles.height == "14px"
    assert span.styles.font_family == "Neony Material Symbols Rounded"
    assert span.styles.font_variation_settings == "'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24"


def test_button_uses_icon_value_and_centers_content():
    button = Button("Save", icon=icons.check)
    node = button.build()
    assert button.icon is icons.check
    assert node.styles.display == "flex"
    assert node.styles.align_items == "center"
    assert node.styles.justify_content == "center"
    assert node.styles.gap == "8px"
    icon_span = node.container[0]
    assert isinstance(icon_span, Span)
    assert icon_span.styles.font_family == "Neony Material Symbols Rounded"


def test_font_css_is_bundled_and_cached():
    first = css()
    assert first is css()
    assert "@font-face" in first
    assert "Neony Material Symbols Rounded" in first
    assert "data:font/woff2;base64," in first


class _FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    async def eval_js(self, script: str) -> None:
        self.scripts.append(script)


def test_application_injects_the_icon_font_once_per_window():
    app = NeonApplication(Config())
    entry = _Entry(Neony(name="neony"), Div())
    window = _FakeWindow()
    entry.window = window  # type: ignore[assignment]

    asyncio.run(app._inject_icon_font(entry))

    assert len(window.scripts) == 1
    assert "neony-icon-font" in window.scripts[0]
    assert "data:font/woff2;base64," in window.scripts[0]
