"""Test the component library: build, state, events, theming."""

from neony.application import Page, Theme
from neony.application.elements import Button, Checkbox, Input, Tabs, Text, VStack
from neony.dom import DomEvent, NodeDescriptor


def _find_by_key(node: NodeDescriptor, key: str) -> NodeDescriptor | None:
    if node.key == key:
        return node
    for child in node.children:
        found = _find_by_key(child, key)
        if found:
            return found
    return None


class TestComponentBuild:
    """Components build into valid DOMElement trees."""

    def test_button_build(self):
        btn = Button("Save")
        node = btn.build().to_node()
        assert node.tag == "button"
        assert node.text == "Save"
        assert node.styles["background-color"] == "var(--color-accent)"

    def test_button_ghost_variant(self):
        btn = Button("Cancel", variant="ghost")
        node = btn.build().to_node()
        assert node.styles["background-color"] == "var(--color-surface)"

    def test_checkbox_build(self):
        cb = Checkbox("Pizza")
        node = cb.build().to_node()
        assert node.tag == "label"
        assert len(node.children) == 2

    def test_input_build(self):
        inp = Input(placeholder="Email", type="email")
        node = inp.build().to_node()
        assert node.tag == "input"
        assert node.attrs["placeholder"] == "Email"
        assert node.attrs["type"] == "email"

    def test_text_roles(self):
        assert Text("hi", role="secondary").build().to_node().styles["color"] == "var(--color-text-secondary)"
        assert Text("hi", role="danger").build().to_node().styles["color"] == "var(--color-danger)"

    def test_vstack_build(self):
        stack = VStack(Button("A"), Button("B"), gap="8px")
        node = stack.build().to_node()
        assert node.styles["display"] == "flex"
        assert node.styles["flex-direction"] == "column"
        assert len(node.children) == 2

    def test_tabs_build(self):
        tabs = Tabs()
        tabs.add("One", Text("panel 1"))
        tabs.add("Two", Text("panel 2"))
        node = tabs.build().to_node()
        assert len(node.children) == 3  # bar + 2 panels

    def test_tabs_active_styles(self):
        tabs = Tabs()
        tabs.add("One", Text("p1"))
        tabs.add("Two", Text("p2"))
        node = tabs.build().to_node()
        # bar is children[0]; its children are the tab buttons
        bar = node.children[0]
        assert bar.children[0].styles["background-color"] == "var(--color-accent)"
        assert bar.children[1].styles["background-color"] == "var(--color-surface)"


class TestComponentState:
    """Components own their state."""

    def test_checkbox_checked_property(self):
        cb = Checkbox("x", checked=True)
        assert cb.checked is True
        cb.checked = False
        assert cb.checked is False
        # DOMElement attr updated immediately
        node = cb.build().to_node()
        checkbox = _find_by_key(node, cb._input.key)
        assert checkbox is not None
        assert "checked" not in checkbox.attrs

    def test_input_value_property(self):
        inp = Input()
        inp.value = "hello"
        assert inp.value == "hello"
        node = inp.build().to_node()
        assert node.attrs["value"] == "hello"

    def test_button_label_setter(self):
        btn = Button("A")
        btn.label = "B"
        assert btn.build().to_node().text == "B"


class TestComponentEvents:
    """Events dispatch only for user-driven changes."""

    def test_programmatic_set_does_not_fire(self):
        cb = Checkbox("x")
        fired: list[bool] = []

        async def handler(event: DomEvent):
            fired.append(event.value)

        cb.on_change(handler)
        cb.checked = True  # programmatic — must NOT fire
        assert fired == []

    def test_user_dispatch_fires(self):
        import asyncio

        cb = Checkbox("x")
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            # snapshot value+source inside the callback — the event's
            # source field is reset after dispatch completes
            fired.append((event.value, event.source))

        cb.on_change(handler)
        # simulate the DOM event arriving through the component handler
        dom_handler = cb._input._handlers["change"][0]
        asyncio.run(dom_handler(DomEvent(key=cb._input.key, type="change", value=True)))
        assert fired == [(True, "user")]
        # state synced from the event
        assert cb.checked is True

    def test_reset_styles_replaces(self):
        btn = Button("x")
        from neony.dom import Styles

        btn.reset_styles(Styles(width="100px"))
        node = btn.build().to_node()
        assert node.styles["width"] == "100px"
        assert "background-color" not in node.styles

    def test_reset_styles_chainable(self):
        btn = Button("x")
        from neony.dom import Styles

        result = btn.reset_styles(Styles(width="1px"))
        assert result is btn


class TestButtonFeedback:
    """Hover / press state drives style changes."""

    def test_hover_adds_shadow(self):
        import asyncio

        btn = Button("x")
        assert btn._btn.styles.box_shadow is None
        handler = btn._btn._handlers["mouseover"][0]
        asyncio.run(handler(DomEvent(key=btn._btn.key, type="mouseover")))
        assert btn._btn.styles.box_shadow == "0 4px 16px var(--color-shadow)"

    def test_mouseout_clears_hover(self):
        import asyncio

        btn = Button("x")
        h_in = btn._btn._handlers["mouseover"][0]
        h_out = btn._btn._handlers["mouseout"][0]
        asyncio.run(h_in(DomEvent(key=btn._btn.key, type="mouseover")))
        asyncio.run(h_out(DomEvent(key=btn._btn.key, type="mouseout")))
        assert btn._btn.styles.box_shadow is None

    def test_press_dims(self):
        import asyncio

        btn = Button("x")
        h_down = btn._btn._handlers["mousedown"][0]
        asyncio.run(h_down(DomEvent(key=btn._btn.key, type="mousedown")))
        assert btn._btn.styles.opacity == 0.8


class TestInputNoLoop:
    """User input must not write the value back to the DOM tree.

    Writing back diffs an UpdateAttrsPatch → JS setAttribute("value")
    → WebKitGTK refires `input` → infinite loop. State is recorded only.
    """

    def test_input_event_records_state_without_dom_write(self):
        import asyncio

        from neony.application.elements import Input

        inp = Input()
        handler = inp._input._handlers["input"][0]
        asyncio.run(handler(DomEvent(key=inp._input.key, type="input", value="hello")))
        # state recorded
        assert inp.value == "hello"
        # DOMElement untouched → no UpdateAttrsPatch in the next diff
        assert inp._input.value == ""

    def test_programmatic_set_still_writes_dom(self):
        from neony.application.elements import Input

        inp = Input()
        inp.value = "set programmatically"
        assert inp._input.value == "set programmatically"


class TestPageAndTheme:
    def test_page_build(self):
        page = Page(gap="12px")
        page.add(Text("hello"))
        node = page.build().to_node()
        # outer layer: full-screen background
        assert node.styles["background-color"] == "var(--color-bg)"
        assert "margin" not in node.styles
        assert "max-width" not in node.styles
        # inner layer: centered, width-constrained flex column
        inner = node.children[0]
        assert inner.styles["display"] == "flex"
        assert inner.styles["flex-direction"] == "column"
        assert inner.styles["max-width"] == "600px"
        assert inner.styles["margin"] == "0 auto"
        assert len(inner.children) == 1

    def test_theme_to_css(self):
        theme = Theme()
        css = theme.to_css()
        assert "--color-bg" in css
        assert "--color-surface" in css
        assert ":root" in css

    def test_theme_toggle(self):
        theme = Theme()
        assert theme.mode == "dark"
        theme.toggle()
        assert theme.mode == "light"
        assert theme.bg != "#1a1a2e"
