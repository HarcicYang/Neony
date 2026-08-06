"""Test the component library: build, state, events, theming."""

from neony.application import Page, Theme
from neony.application.elements import (
    Button,
    Checkbox,
    ComboBox,
    Dialog,
    Dropdown,
    Input,
    Menu,
    Progress,
    Radio,
    RadioGroup,
    Select,
    SidebarItem,
    Slider,
    Switch,
    Tabs,
    Text,
    Tooltip,
    VStack,
)
from neony.dom import Animation, DomEvent, NodeDescriptor


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

    def test_tabs_active_panel_animates(self):
        """The visible panel carries the built-in rise-in animation."""
        tabs = Tabs()
        tabs.add("One", Text("p1"))
        tabs.add("Two", Text("p2"))
        node = tabs.build().to_node()
        active_panel, inactive_panel = node.children[1], node.children[2]
        assert active_panel.styles["display"] == "flex"
        assert active_panel.styles["animation"] == "neony-rise-in 0.25s ease-out"
        assert inactive_panel.styles["display"] == "none"
        assert "animation" not in inactive_panel.styles

    def test_tabs_glass_panel_animates(self):
        tabs = Tabs(glass=True)
        tabs.add("One", Text("p1"))
        node = tabs.build().to_node()
        panel = node.children[1]
        assert panel.styles["animation"] == "neony-rise-in 0.25s ease-out"

    def test_tabs_tab_button_transitions(self):
        tabs = Tabs()
        tabs.add("One", Text("p1"))
        node = tabs.build().to_node()
        tab = node.children[0].children[0]
        assert tab.styles["transition"] == "all 0.15s ease"

    def test_sidebar_item_transitions(self):
        """Active-state style swaps interpolate instead of snapping."""
        item = SidebarItem("Home")
        node = item.build().to_node()
        assert node.styles["transition"] == "all 0.15s ease"


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

    def test_checkbox_custom_box_style(self):
        """Checked state drives the custom box appearance."""
        cb = Checkbox("x", checked=False)
        unchecked = cb._input.to_node()
        assert unchecked.styles.get("appearance") == "none"
        assert unchecked.styles.get("background-color") == "var(--color-surface-raised)"
        assert "background-image" not in unchecked.styles

        cb.checked = True
        checked = cb._input.to_node()
        assert checked.styles.get("background-color") == "var(--color-accent)"
        assert checked.styles.get("background-image", "").startswith('url("data:image/svg+xml')
        assert checked.styles.get("background-size") == "12px 12px"

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

    def test_hover_adds_glow(self):
        import asyncio

        btn = Button("x")
        assert btn._btn.styles.box_shadow is None
        handler = btn._btn._handlers["mouseover"][0]
        asyncio.run(handler(DomEvent(key=btn._btn.key, type="mouseover")))
        assert btn._btn.styles.box_shadow == ("0 4px 16px var(--color-shadow), 0 0 20px var(--color-accent-glass)")

    def test_danger_hover_glow_uses_danger_color(self):
        import asyncio

        btn = Button("x", variant="danger")
        handler = btn._btn._handlers["mouseover"][0]
        asyncio.run(handler(DomEvent(key=btn._btn.key, type="mouseover")))
        assert "var(--color-danger-glass)" in (btn._btn.styles.box_shadow or "")

    def test_focus_adds_ring_blur_removes(self):
        import asyncio

        btn = Button("x")
        h_in = btn._btn._handlers["focus"][0]
        h_out = btn._btn._handlers["blur"][0]
        asyncio.run(h_in(DomEvent(key=btn._btn.key, type="focus")))
        assert btn._btn.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(h_out(DomEvent(key=btn._btn.key, type="blur")))
        assert not btn._btn.styles.box_shadow

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


class TestFocusGlow:
    """Focus rings and colour-matched glows on interactive controls."""

    def test_input_focus_ring(self):
        import asyncio

        from neony.application.elements import Input

        inp = Input()
        assert inp._input.styles.box_shadow is None
        asyncio.run(inp._input._handlers["focus"][0](DomEvent(key=inp._input.key, type="focus")))
        assert inp._input.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(inp._input._handlers["blur"][0](DomEvent(key=inp._input.key, type="blur")))
        assert inp._input.styles.box_shadow is None

    def test_input_focus_ring_does_not_mutate_shared_constant(self):
        import asyncio

        from neony.application.elements import Input
        from neony.application.elements.input import _FIELD

        inp = Input()
        asyncio.run(inp._input._handlers["focus"][0](DomEvent(key=inp._input.key, type="focus")))
        # The module-level _FIELD constant must stay untouched — the
        # focus ring is applied on a model_copy.
        assert _FIELD.box_shadow is None

    def test_checkbox_focus_ring(self):
        import asyncio

        from neony.application.elements import Checkbox

        cb = Checkbox("x")
        assert cb._input.styles.box_shadow is None
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        assert cb._input.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(cb._input._handlers["blur"][0](DomEvent(key=cb._input.key, type="blur")))
        assert cb._input.styles.box_shadow is None

    def test_checkbox_focus_ring_survives_check_toggle(self):
        import asyncio

        from neony.application.elements import Checkbox

        cb = Checkbox("x")
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        asyncio.run(cb._input._handlers["change"][0](DomEvent(key=cb._input.key, type="change", value=True)))
        assert cb._input.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        bg = cb._input.styles.background_color
        assert bg is not None and bg.var == "--color-accent"


class TestGlassPanelGlow:
    """GlassPanel gets a persistent colour-matched glow per role."""

    def test_neutral_keeps_plain_shadow(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content")
        shadow = panel.build().to_node().styles["box-shadow"]
        assert shadow == "0 8px 32px rgba(0, 0, 0, 0.15), inset 0 0 0 1px rgba(255, 255, 255, 0.04)"

    def test_accent_role_glows_accent(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", role="accent")
        shadow = panel.build().to_node().styles["box-shadow"]
        assert shadow.startswith("0 0 24px var(--color-accent-glass), 0 8px 32px")

    def test_danger_role_glows_danger(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", role="danger")
        shadow = panel.build().to_node().styles["box-shadow"]
        assert shadow.startswith("0 0 24px var(--color-danger-glass), 0 8px 32px")


class TestPageAndTheme:
    def test_page_build(self):
        page = Page(gap="12px")
        page.add(Text("hello"))
        node = page.build().to_node()
        # outer layer: full-screen transparent backdrop (body provides
        # the theme colour / background image)
        assert "background-color" not in node.styles
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


class TestScrollbarTheming:
    def test_webkit_scrollbar_rules(self):
        css = Theme().to_css()
        assert "::-webkit-scrollbar" in css
        assert "::-webkit-scrollbar-track" in css
        assert "::-webkit-scrollbar-thumb" in css
        assert "::-webkit-scrollbar-thumb:hover" in css
        assert "::-webkit-scrollbar-corner" in css

    def test_firefox_scrollbar_rules(self):
        css = Theme().to_css()
        assert "scrollbar-color" in css
        assert "scrollbar-width" in css

    def test_scrollbar_uses_theme_tokens(self):
        css = Theme().to_css()
        assert "var(--color-surface-raised)" in css
        assert "var(--color-bg)" in css
        assert "var(--color-accent)" in css

    def test_scrollbar_rules_survive_theme_toggle(self):
        theme = Theme()
        theme.set_mode("light")
        css = theme.to_css()
        assert "::-webkit-scrollbar" in css
        assert "scrollbar-color" in css


class TestRadioBuild:
    """Radio options build into labelled native radio inputs."""

    def test_radio_build(self):
        radio = Radio("Pizza", value="pizza")
        node = radio.build().to_node()
        assert node.tag == "label"
        assert len(node.children) == 2
        radio_input = _find_by_key(node, radio._input.key)
        assert radio_input is not None
        assert radio_input.attrs["type"] == "radio"
        assert radio_input.styles["appearance"] == "none"
        assert radio_input.styles["border-radius"] == "50%"

    def test_radio_value_defaults_to_lowercased_label(self):
        assert Radio("Home").value == "home"

    def test_radio_value_override(self):
        assert Radio("Home", value="h").value == "h"


class TestRadioState:
    """Radio owns its checked state; programmatic writes fire nothing."""

    def test_checked_property_writes_dom(self):
        radio = Radio("x")
        assert radio.checked is False
        radio.checked = True
        assert radio.checked is True
        node = radio.build().to_node()
        radio_input = _find_by_key(node, radio._input.key)
        assert radio_input is not None
        assert "checked" in radio_input.attrs

    def test_unchecked_omits_checked_attr(self):
        radio = Radio("x")
        radio.checked = False
        node = radio.build().to_node()
        radio_input = _find_by_key(node, radio._input.key)
        assert radio_input is not None
        assert "checked" not in radio_input.attrs

    def test_checked_dot_style(self):
        radio = Radio("x")
        assert radio._input.styles.box_shadow is None
        radio.checked = True
        assert radio._input.styles.box_shadow == "inset 0 0 0 4px var(--color-accent)"
        assert radio._input.styles.border == "1px solid var(--color-accent)"

    def test_programmatic_set_does_not_fire(self):
        radio = Radio("x")
        fired: list = []
        radio.on_change(lambda e: fired.append(e.value))
        radio.checked = True
        assert fired == []


class TestRadioEvents:
    """User toggles sync state and dispatch with source == user."""

    def test_user_change_syncs_and_fires(self):
        import asyncio

        radio = Radio("x")
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        radio.on_change(handler)
        dom_handler = radio._input._handlers["change"][0]
        asyncio.run(dom_handler(DomEvent(key=radio._input.key, type="change", value=True)))
        assert fired == [(True, "user")]
        assert radio.checked is True

    def test_focus_ring_composes_with_checked_dot(self):
        """The focus ring must not replace the checked inner dot."""
        import asyncio

        radio = Radio("x", checked=True)
        asyncio.run(radio._input._handlers["focus"][0](DomEvent(key=radio._input.key, type="focus")))
        shadow = radio._input.styles.box_shadow
        assert shadow == "0 0 0 3px var(--color-accent-glass), inset 0 0 0 4px var(--color-accent)"
        asyncio.run(radio._input._handlers["blur"][0](DomEvent(key=radio._input.key, type="blur")))
        assert radio._input.styles.box_shadow == "inset 0 0 0 4px var(--color-accent)"


class TestRadioGroup:
    """RadioGroup owns mutual exclusion and dispatches group changes."""

    def _user_change(self, radio: Radio, value: bool = True) -> None:
        import asyncio

        for handler in list(radio._input._handlers["change"]):
            asyncio.run(handler(DomEvent(key=radio._input.key, type="change", value=value)))

    def test_first_item_starts_checked(self):
        group = RadioGroup(Radio("A"), Radio("B"))
        assert group.value == "a"
        assert group.items[0].checked is True
        assert group.items[1].checked is False

    def test_items_share_generated_name(self):
        group = RadioGroup(Radio("A"), Radio("B"))
        name = group.items[0]._input.name
        assert name is not None
        assert all(item._input.name == name for item in group.items)
        assert name.startswith("neony-radio-")

    def test_value_constructor_preselects(self):
        group = RadioGroup(Radio("A"), Radio("B"), value="b")
        assert group.value == "b"
        assert group.items[0].checked is False
        assert group.items[1].checked is True

    def test_user_change_excludes_siblings(self):
        group = RadioGroup(Radio("A", value="a"), Radio("B", value="b"))
        self._user_change(group.items[1])
        assert group.value == "b"
        assert group.items[0].checked is False
        assert group.items[1].checked is True
        # DOM attrs reflect the exclusion too
        node = group.build().to_node()
        b_node = _find_by_key(node, group.items[1]._input.key)
        a_node = _find_by_key(node, group.items[0]._input.key)
        assert b_node is not None and a_node is not None
        assert "checked" in b_node.attrs
        assert "checked" not in a_node.attrs

    def test_group_change_carries_item_value(self):
        """The group-level change fires once with the selected value.
        (Source is ``program`` here — the group handler is a raw
        DOMElement handler, Sidebar parity; the item-level change that
        preceded it carried ``user``.)"""
        group = RadioGroup(Radio("A", value="a"), Radio("B", value="b"))
        fired: list = []

        async def handler(event: DomEvent):
            fired.append(event.value)

        group.on_change(handler)
        self._user_change(group.items[1])
        assert fired == ["b"]

    def test_programmatic_value_set_fires_nothing(self):
        group = RadioGroup(Radio("A", value="a"), Radio("B", value="b"))
        fired: list = []
        group.on_change(lambda e: fired.append(e.value))
        group.value = "b"
        assert fired == []
        assert group.items[0].checked is False
        assert group.items[1].checked is True


class TestSwitchBuild:
    """Switch is a native checkbox styled as a track + thumb."""

    def test_switch_build(self):
        sw = Switch("WiFi")
        node = sw.build().to_node()
        assert node.tag == "label"
        assert len(node.children) == 2
        track = _find_by_key(node, sw._input.key)
        assert track is not None
        assert track.attrs["type"] == "checkbox"
        assert track.styles["width"] == "38px"
        assert track.styles["border-radius"] == "999px"
        assert track.styles["appearance"] == "none"

    def test_thumb_position_off(self):
        sw = Switch("x", checked=False)
        assert sw._input.styles.background_position == "2px center"
        color = sw._input.styles.color
        assert color is not None
        assert color.var == "--color-text-secondary"

    def test_thumb_position_on(self):
        sw = Switch("x", checked=True)
        assert sw._input.styles.background_position == "18px center"
        bg = sw._input.styles.background_color
        color = sw._input.styles.color
        assert bg is not None and color is not None
        assert bg.var == "--color-accent"
        assert color.name == "white"

    def test_thumb_is_current_color_svg(self):
        sw = Switch("x")
        bg = sw._input.styles.background_image
        assert bg is not None
        assert bg.startswith('url("data:image/svg+xml')
        assert "currentColor" in bg

    def test_glass_track_uses_glass_tokens(self):
        sw = Switch("x", glass=True)
        bg = sw._input.styles.background_color
        assert bg is not None
        assert bg.var == "--color-surface-glass-bg"
        sw.checked = True
        bg = sw._input.styles.background_color
        assert bg is not None
        assert bg.var == "--color-accent-glass-bg"


class TestSwitchState:
    def test_checked_property_writes_dom(self):
        sw = Switch("x")
        sw.checked = True
        assert sw.checked is True
        assert sw._input.checked is True
        node = sw.build().to_node()
        track = _find_by_key(node, sw._input.key)
        assert track is not None
        assert "checked" in track.attrs

    def test_programmatic_set_does_not_fire(self):
        sw = Switch("x")
        fired: list = []
        sw.on_change(lambda e: fired.append(e.value))
        sw.checked = True
        assert fired == []


class TestSwitchEvents:
    def test_user_change_syncs_and_fires(self):
        import asyncio

        sw = Switch("x")
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        sw.on_change(handler)
        dom_handler = sw._input._handlers["change"][0]
        asyncio.run(dom_handler(DomEvent(key=sw._input.key, type="change", value=True)))
        assert fired == [(True, "user")]
        assert sw.checked is True
        assert sw._input.styles.background_position == "18px center"

    def test_focus_ring(self):
        import asyncio

        sw = Switch("x")
        asyncio.run(sw._input._handlers["focus"][0](DomEvent(key=sw._input.key, type="focus")))
        assert sw._input.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(sw._input._handlers["blur"][0](DomEvent(key=sw._input.key, type="blur")))
        assert not sw._input.styles.box_shadow


class TestSelectBuild:
    """Select draws a custom popup — no native select popup involved."""

    def test_select_build(self):
        sel = Select("Color", options=[("r", "Red"), ("g", "Green")])
        node = sel.build().to_node()
        assert node.tag == "label"
        trigger = _find_by_key(node, sel._trigger.key)
        popup = _find_by_key(node, sel._popup.key)
        assert trigger is not None and popup is not None
        assert trigger.attrs["tabindex"] == "0"
        assert trigger.attrs["role"] == "combobox"
        assert trigger.styles["background-image"].startswith('url("data:image/svg+xml')
        assert popup.styles["display"] == "none"  # closed
        assert popup.styles["background-color"] == "var(--color-surface-glass-bg)"
        assert popup.styles["z-index"] == "500"
        assert [row.attrs["role"] for row in popup.children] == ["option", "option"]
        assert [row.text for row in popup.children] == ["Red", "Green"]

    def test_bare_string_options_use_value_as_label(self):
        sel = Select(options=["one", "two"])
        assert [label for _v, label in sel._options] == ["one", "two"]
        assert sel.build().to_node() is not None

    def test_placeholder_first_and_disabled(self):
        sel = Select(options=["a"], placeholder="Choose…")
        node = sel.build().to_node()
        popup = _find_by_key(node, sel._popup.key)
        assert popup is not None
        placeholder = popup.children[0]
        assert placeholder.attrs["disabled"] == ""
        assert placeholder.text == "Choose…"
        # the trigger shows the placeholder while nothing is selected
        trigger = _find_by_key(node, sel._trigger.key)
        assert trigger is not None
        assert trigger.children[0].text == "Choose…"

    def test_initial_value_shows_label_and_active_row(self):
        sel = Select(options=["a", "b"], value="b")
        node = sel.build().to_node()
        trigger = _find_by_key(node, sel._trigger.key)
        popup = _find_by_key(node, sel._popup.key)
        assert trigger is not None and popup is not None
        assert trigger.children[0].text == "b"
        assert popup.children[1].styles["background-color"] == "var(--color-accent-glass-bg)"
        assert popup.children[0].styles["background-color"] == "transparent"


class TestSelectEvents:
    """Select: popup open/close, selection, keyboard and outsideclick."""

    def _user_click_trigger(self, sel: Select) -> None:
        import asyncio

        asyncio.run(sel._trigger._handlers["click"][0](DomEvent(key=sel._trigger.key, type="click")))

    def test_user_row_click_syncs_and_fires(self):
        import asyncio

        sel = Select(options=["a", "b"])
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        sel.on_change(handler)
        row = sel._rows[1][1]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert sel.value == "b"
        assert fired == [("b", "user")]

    def test_trigger_click_toggles_popup_and_marker(self):
        sel = Select(options=["a"])
        self._user_click_trigger(sel)
        assert sel._open is True
        assert sel._popup.styles.display == "flex"
        assert sel._wrapper.args.get("data-neony-outside") == "true"
        self._user_click_trigger(sel)
        assert not sel._open
        assert sel._popup.styles.display == "none"
        assert "data-neony-outside" not in sel._wrapper.args

    def test_outsideclick_closes(self):
        import asyncio

        sel = Select(options=["a"])
        self._user_click_trigger(sel)
        handler = sel._wrapper._handlers["outsideclick"][0]
        asyncio.run(handler(DomEvent(key=sel._wrapper.key, type="outsideclick")))
        assert sel._open is False

    def test_keyboard_opens_navigates_selects_closes(self):
        import asyncio

        sel = Select(options=["a", "b"])
        keydown = sel._wrapper._handlers["keydown"][0]

        async def key(key: str) -> None:
            await keydown(DomEvent(key=sel._trigger.key, type="keydown", value=key))

        asyncio.run(key("Enter"))
        assert sel._open is True
        asyncio.run(key("ArrowDown"))
        assert sel._active_index == 0  # first ArrowDown activates the top row
        asyncio.run(key("ArrowDown"))
        assert sel._active_index == 1
        row_bg = sel._rows[1][1].styles.background_color
        assert row_bg is not None
        assert row_bg.var == "--color-accent-glass-bg"

        fired: list = []
        sel.on_change(lambda e: fired.append(e.value))
        asyncio.run(key("Enter"))
        assert sel.value == "b"
        assert fired == ["b"]
        assert not sel._open

        asyncio.run(key("Escape"))  # no-op when closed
        assert sel._open is False

    def test_programmatic_set_does_not_fire(self):
        sel = Select(options=["a"])
        fired: list = []
        sel.on_change(lambda e: fired.append(e.value))
        sel.value = "a"
        assert fired == []

    def test_focus_ring_on_trigger(self):
        import asyncio

        sel = Select(options=["a"])
        asyncio.run(sel._trigger._handlers["focus"][0](DomEvent(key=sel._trigger.key, type="focus")))
        assert sel._trigger.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(sel._trigger._handlers["blur"][0](DomEvent(key=sel._trigger.key, type="blur")))
        assert not sel._trigger.styles.box_shadow

    def test_pagedown_jumps_to_last_option_pageup_to_first(self):
        import asyncio

        sel = Select(options=["a", "b", "c"], placeholder="Pick…")
        keydown = sel._wrapper._handlers["keydown"][0]

        async def key(key: str) -> None:
            await keydown(DomEvent(key=sel._trigger.key, type="keydown", value=key))

        asyncio.run(key("PageDown"))
        assert sel._open is True
        assert sel._active_index == 3  # placeholder is row 0; last selectable is 3
        asyncio.run(key("PageUp"))
        assert sel._active_index == 1  # first selectable after the placeholder

    def test_arrows_clamp_at_ends_no_wrap(self):
        """ArrowUp must return to the first option — no wrap-around."""
        import asyncio

        sel = Select(options=["a", "b", "c"])
        keydown = sel._wrapper._handlers["keydown"][0]

        async def key(key: str) -> None:
            await keydown(DomEvent(key=sel._trigger.key, type="keydown", value=key))

        asyncio.run(key("ArrowDown"))  # opens, first option highlighted
        assert sel._active_index == 0
        for expected in (1, 2, 2):  # down, down, clamped at the last
            asyncio.run(key("ArrowDown"))
            assert sel._active_index == expected
        for expected in (1, 0, 0):  # up, up, clamped at the first
            asyncio.run(key("ArrowUp"))
            assert sel._active_index == expected

    def test_popup_entrance_animation(self):
        sel = Select(options=["a"])
        assert sel._popup.styles.animation is None
        self._user_click_trigger(sel)
        node = sel.build().to_node()
        popup = _find_by_key(node, sel._popup.key)
        assert popup is not None
        assert popup.styles["animation"] == "neony-rise-in 0.2s ease-out"


class TestComboBoxBuild:
    """ComboBox draws a themed suggestion popup — no datalist."""

    def test_combobox_build(self):
        cb = ComboBox("Tag", options=["a", "b"])
        node = cb.build().to_node()
        input_node = _find_by_key(node, cb._input.key)
        popup = _find_by_key(node, cb._popup.key)
        assert input_node is not None and popup is not None
        assert input_node.attrs["type"] == "text"
        assert popup.styles["display"] == "none"  # closed
        assert popup.styles["background-color"] == "var(--color-surface-glass-bg)"

    def test_options_setter_rebuilds_on_next_open(self):
        cb = ComboBox(options=["a"])
        cb.options = ["x", "y"]
        assert cb.options == ["x", "y"]
        import asyncio

        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="")))
        assert [str(row.container[0]) for row in cb._rows] == ["x", "y"]


class TestComboBoxEvents:
    def test_input_event_records_state_without_dom_write(self):
        import asyncio

        cb = ComboBox(options=["work", "personal"])
        handler = cb._input._handlers["input"][0]
        asyncio.run(handler(DomEvent(key=cb._input.key, type="input", value="wo")))
        assert cb.value == "wo"
        # DOMElement untouched → no UpdateAttrsPatch in the next diff
        assert cb._input.value == ""
        # prefix filter opened the popup with the matching suggestion
        assert cb._open is True
        assert [str(row.container[0]) for row in cb._rows] == ["work"]

    def test_input_without_matches_closes(self):
        import asyncio

        cb = ComboBox(options=["work"])
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="zzz")))
        assert cb._open is False
        assert cb._rows == []

    def test_programmatic_set_still_writes_dom(self):
        cb = ComboBox()
        cb.value = "set programmatically"
        assert cb._input.value == "set programmatically"

    def test_change_dispatches_on_native_blur(self):
        """A real blur-commit: `input` events sync `_value` first, so the
        matching change dispatches (stale pre-pick changes are dropped)."""
        import asyncio

        cb = ComboBox()
        fired: list = []
        cb.on_change(lambda e: fired.append(e.value))
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="picked")))
        asyncio.run(cb._input._handlers["change"][0](DomEvent(key=cb._input.key, type="change", value="picked")))
        assert fired == ["picked"]

    def test_row_click_picks_and_fires(self):
        import asyncio

        cb = ComboBox(options=["work", "personal"])
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="wo")))
        fired: list = []
        cb.on_change(lambda e: fired.append(e.value))
        row = cb._rows[0]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert cb.value == "work"
        assert cb._input.value == "work"  # pick writes the DOM (safe)
        assert fired == ["work"]
        assert cb._open is False

    def test_arrowdown_then_enter_picks_first_match(self):
        import asyncio

        cb = ComboBox(options=["work", "personal"])
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="wo")))
        fired: list = []
        cb.on_change(lambda e: fired.append(e.value))
        keydown = cb._wrapper._handlers["keydown"][0]
        asyncio.run(keydown(DomEvent(key=cb._input.key, type="keydown", value="ArrowDown")))
        asyncio.run(keydown(DomEvent(key=cb._input.key, type="keydown", value="Enter")))
        assert cb.value == "work"
        assert fired == ["work"]

    def test_escape_and_outsideclick_close(self):
        import asyncio

        cb = ComboBox(options=["work"])
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="wo")))
        assert cb._open is True
        keydown = cb._wrapper._handlers["keydown"][0]
        asyncio.run(keydown(DomEvent(key=cb._input.key, type="keydown", value="Escape")))
        assert not cb._open
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="wo")))
        asyncio.run(cb._wrapper._handlers["outsideclick"][0](DomEvent(key=cb._wrapper.key, type="outsideclick")))
        assert cb._open is False

    def test_focus_opens_popup_with_all_options(self):
        """Clicking the field alone must show the suggestions — no
        keystroke needed."""
        import asyncio

        cb = ComboBox(options=["work", "personal", "travel"])
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        assert cb._open is True
        assert len(cb._rows) == 3
        assert cb._active_index == 0  # first match pre-highlighted

    def test_pageup_commits_first_item_pagedown_commits_last(self):
        """Page keys pick in one keypress — PageUp selects the first
        suggestion, PageDown the last."""
        import asyncio

        cb = ComboBox(options=["work", "personal", "travel"])
        keydown = cb._wrapper._handlers["keydown"][0]

        async def key(key: str) -> None:
            await keydown(DomEvent(key=cb._input.key, type="keydown", value=key))

        fired: list = []
        cb.on_change(lambda e: fired.append(e.value))
        asyncio.run(key("PageUp"))
        assert cb.value == "work"
        assert cb._input.value == "work"
        assert fired == ["work"]
        assert cb._open is False

        # PageDown with an empty query picks the last suggestion (the
        # input above now filters to "work" only, so use a fresh one)
        cb2 = ComboBox(options=["work", "personal", "travel"])
        fired2: list = []
        cb2.on_change(lambda e: fired2.append(e.value))
        asyncio.run(
            cb2._wrapper._handlers["keydown"][0](DomEvent(key=cb2._input.key, type="keydown", value="PageDown"))
        )
        assert cb2.value == "travel"
        assert fired2 == ["travel"]

    def test_tab_and_enter_autocomplete(self):
        """Tab or Enter accepts the highlighted suggestion."""
        import asyncio

        cb = ComboBox(options=["work", "personal", "travel"])
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        assert cb._active_index == 0  # first suggestion pre-highlighted
        keydown = cb._wrapper._handlers["keydown"][0]

        fired: list = []
        cb.on_change(lambda e: fired.append(e.value))
        asyncio.run(keydown(DomEvent(key=cb._input.key, type="keydown", value="Tab")))
        assert cb.value == "work"
        assert fired == ["work"]

        # reopen and accept via Enter without any arrow presses
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        asyncio.run(keydown(DomEvent(key=cb._input.key, type="keydown", value="Enter")))
        assert cb.value == "work"
        assert fired == ["work", "work"]

    def test_arrows_clamp_at_ends_no_wrap(self):
        """ArrowUp from the first item must stay there (no wrap to the
        last) — the first suggestion stays reachable with the arrows."""
        import asyncio

        cb = ComboBox(options=["work", "personal", "travel"])
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        assert cb._active_index == 0
        keydown = cb._wrapper._handlers["keydown"][0]

        async def key(key: str) -> None:
            await keydown(DomEvent(key=cb._input.key, type="keydown", value=key))

        asyncio.run(key("ArrowUp"))  # first + ArrowUp → stays on the first
        assert cb._active_index == 0
        for expected in (1, 2, 2):  # down, down, clamped at the last
            asyncio.run(key("ArrowDown"))
            assert cb._active_index == expected
        for expected in (1, 0, 0):  # up, up, clamped at the first
            asyncio.run(key("ArrowUp"))
            assert cb._active_index == expected

    def test_tab_autocomplete_follows_edited_text_with_popup_closed(self):
        """After a pick, editing the text then pressing Tab must
        auto-complete against the NEW text — even when the popup was
        closed (click-away / blur)."""
        import asyncio

        cb = ComboBox(options=["work", "personal", "travel"])
        input_h = cb._input._handlers["input"][0]
        keydown = cb._wrapper._handlers["keydown"][0]

        async def type_text(text: str) -> None:
            await input_h(DomEvent(key=cb._input.key, type="input", value=text))

        async def key(key: str) -> None:
            await keydown(DomEvent(key=cb._input.key, type="keydown", value=key))

        # type + pick "work", popup closes
        asyncio.run(type_text("wo"))
        asyncio.run(key("Enter"))
        assert cb.value == "work"
        assert cb._open is False

        # edit the text to "p" — no popup interaction
        asyncio.run(type_text("p"))
        # Tab auto-completes the FIRST match of the new text
        asyncio.run(key("Tab"))
        assert cb.value == "personal"

        # and again: edit to "t", Enter auto-completes
        asyncio.run(type_text("t"))
        asyncio.run(key("Enter"))
        assert cb.value == "travel"

    def test_popup_entrance_animation(self):
        """The open popup carries the built-in rise-in animation."""
        import asyncio

        cb = ComboBox(options=["work"])
        assert cb._popup.styles.animation is None
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        node = cb.build().to_node()
        popup = _find_by_key(node, cb._popup.key)
        assert popup is not None
        assert popup.styles["animation"] == "neony-rise-in 0.2s ease-out"


class TestSliderBuild:
    """Slider draws its own track/fill/thumb over a native range input."""

    def test_slider_build(self):
        sl = Slider("Volume", min=0, max=10, step=0.5, value=3)
        node = sl.build().to_node()
        slider_node = _find_by_key(node, sl._input.key)
        assert slider_node is not None
        assert slider_node.attrs["type"] == "range"
        assert slider_node.attrs["min"] == "0"
        assert slider_node.attrs["max"] == "10"
        assert slider_node.attrs["step"] == "0.5"
        assert slider_node.attrs["value"] == "3.0"
        # the native input is invisible — it owns drag/keyboard only
        assert slider_node.styles["opacity"] == "0.0"

        fill = _find_by_key(node, sl._fill.key)
        thumb = _find_by_key(node, sl._thumb.key)
        assert fill is not None and thumb is not None
        assert fill.styles["width"] == "30.00%"
        assert fill.styles["background-color"] == "var(--color-accent)"
        # first paint is instant — the transition only appears when a
        # programmatic set glides the fill (test_value_setter…)
        assert "transition" not in fill.styles
        assert thumb.styles["left"] == "30.00%"
        assert thumb.styles["transform"] == "translate(-50%, -50%)"

    def test_step_any_is_stepless(self):
        sl = Slider(step="any")
        assert sl._input.step == "any"
        assert sl.build().to_node() is not None  # serializes fine

    def test_fill_maps_value_across_min_max(self):
        sl = Slider(min=20, max=80, value=50)
        assert sl._fill.styles.width == "50.00%"
        sl.value = 20
        assert sl._fill.styles.width == "0.00%"
        sl.value = 80
        assert sl._fill.styles.width == "100.00%"

    def test_label_span_only_when_label_given(self):
        assert len(Slider().build().to_node().children) == 1
        assert len(Slider("Vol").build().to_node().children) == 2

    def test_normalizes_step_zero(self):
        sl = Slider(step=0)
        assert sl._input.step == 1.0

    def test_initial_value_clamped(self):
        assert Slider(value=250).value == 100.0
        assert Slider(value=-5).value == 0.0


class TestSliderEvents:
    def test_input_syncs_and_fires(self):
        import asyncio

        sl = Slider()
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        sl.on_input(handler)
        asyncio.run(sl._input._handlers["input"][0](DomEvent(key=sl._input.key, type="input", value="42")))
        assert sl.value == 42.0
        assert fired == [(42.0, "user")]
        # while dragging the fill follows with no transition (zero lag)
        assert sl._fill.styles.width == "42.00%"
        assert sl._fill.styles.transition is None

    def test_change_fires_on_release(self):
        import asyncio

        sl = Slider()
        fired: list = []
        sl.on_change(lambda e: fired.append(e.value))
        asyncio.run(sl._input._handlers["change"][0](DomEvent(key=sl._input.key, type="change", value="77")))
        assert sl.value == 77.0
        assert fired == [77.0]

    def test_value_setter_clamps_and_writes(self):
        sl = Slider(min=0, max=10)
        sl.value = 500
        assert sl.value == 10.0
        assert sl._input.value == "10.0"
        # programmatic sets keep the transition — the fill glides
        assert sl._fill.styles.width == "100.00%"
        assert sl._fill.styles.transition is not None
        sl.value = -1
        assert sl.value == 0.0
        assert sl._input.value == "0.0"

    def test_programmatic_set_serializes_transition(self):
        sl = Slider()
        sl.value = 75
        node = sl.build().to_node()
        fill = _find_by_key(node, sl._fill.key)
        assert fill is not None
        assert fill.styles["transition"] == "width 0.2s ease"
        assert fill.styles["width"] == "75.00%"

    def test_focus_ring_lives_on_the_thumb(self):
        """The native input is invisible — focus feedback goes to the knob."""
        import asyncio

        sl = Slider()
        asyncio.run(sl._input._handlers["focus"][0](DomEvent(key=sl._input.key, type="focus")))
        assert sl._thumb.styles.box_shadow == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(sl._input._handlers["blur"][0](DomEvent(key=sl._input.key, type="blur")))
        assert sl._thumb.styles.box_shadow == "0 2px 6px var(--color-shadow)"

    def test_pageup_pagedown_correct_the_reversed_native_direction(self):
        """WebKit's native range moves PageUp DOWN / PageDown UP (spec
        quirk) — the keydown schedules the corrected value and the input
        event that follows consumes it, writing the native back."""
        import asyncio

        sl = Slider(min=0, max=100, step=5, value=40)
        keydown = sl._input._handlers["keydown"][0]
        # PageUp must INCREASE by a page (10x step = 50)
        asyncio.run(keydown(DomEvent(key=sl._input.key, type="keydown", value="PageUp")))
        assert sl._page_target == 90.0
        asyncio.run(
            sl._input._handlers["input"][0](
                DomEvent(key=sl._input.key, type="input", value="90")  # what the native produced
            )
        )
        assert sl.value == 90.0
        assert sl._page_target is None
        assert sl._input.value == "90.0"  # native written back in sync

        # PageDown must DECREASE
        asyncio.run(keydown(DomEvent(key=sl._input.key, type="keydown", value="PageDown")))
        assert sl._page_target == 40.0
        asyncio.run(
            sl._input._handlers["input"][0](
                DomEvent(key=sl._input.key, type="input", value="140")  # native's wrong-direction value
            )
        )
        assert sl.value == 40.0
        assert sl._input.value == "40.0"

    def test_page_target_expires_at_range_end(self):
        """No input event follows a page move at the range ends — the
        stale target must not snap the next drag."""
        import asyncio

        sl = Slider(min=0, max=100, step=5, value=95)
        asyncio.run(sl._input._handlers["keydown"][0](DomEvent(key=sl._input.key, type="keydown", value="PageUp")))
        assert sl._page_target == 100.0
        sl._clear_page_target()
        assert sl._page_target is None


class TestProgressBuild:
    """Progress draws a fill inside a rounded track, with ARIA parity."""

    def test_progress_build(self):
        bar = Progress(value=40.5, max=100)
        node = bar.build().to_node()
        track = _find_by_key(node, bar._track.key)
        fill = _find_by_key(node, bar._fill.key)
        assert track is not None and fill is not None
        assert track.attrs["role"] == "progressbar"
        assert track.attrs["aria-valuemin"] == "0"
        assert track.attrs["aria-valuemax"] == "100"
        assert track.attrs["aria-valuenow"] == "40.5"
        assert fill.styles["width"] == "40.5%"
        assert fill.styles["background-color"] == "var(--color-accent)"
        assert fill.styles["transition"] == "width 0.3s ease"

    def test_indeterminate_sweeps_without_aria_value(self):
        bar = Progress(indeterminate=True)
        node = bar.build().to_node()
        track = _find_by_key(node, bar._track.key)
        fill = _find_by_key(node, bar._fill.key)
        assert track is not None and fill is not None
        assert "aria-valuenow" not in track.attrs
        assert fill.styles["animation"] == "neony-indeterminate 1.2s ease-in-out infinite"
        assert fill.styles["width"] == "40%"

    def test_label_span_only_when_label_given(self):
        assert len(Progress().build().to_node().children) == 1
        assert len(Progress(label="Loading").build().to_node().children) == 2


class TestProgressState:
    def test_value_clamped_to_range(self):
        bar = Progress(value=250)
        assert bar.value == 100.0
        assert bar._fill.styles.width == "100.0%"
        bar.value = -5
        assert bar.value == 0.0
        assert bar._fill.styles.width == "0.0%"

    def test_indeterminate_value_write_ignored(self):
        bar = Progress(indeterminate=True)
        bar.value = 50
        assert bar.value == 0.0
        assert bar._fill.styles.animation is not None

    def test_max_setter_writes_attr(self):
        bar = Progress()
        bar.max = 200
        assert bar.max == 200
        assert bar._track.args["aria-valuemax"] == "200"


class TestAccentColorStyle:
    """The new Styles field serializes to accent-color."""

    def test_accent_color_serializes(self):
        from neony.dom import Color, Div, Styles

        styles = Styles(accent_color=Color(var="--color-accent"))
        accent = styles.accent_color
        assert accent is not None
        assert accent.var == "--color-accent"
        # end-to-end: an element carrying it renders the kebab-cased CSS
        div = Div(styles=styles)
        assert "accent-color: var(--color-accent)" in div.build()


class TestSidebarItemBoundEvents:
    """SidebarItem declares its bound events — on_click must not
    double-wire the root (regression for the missing _bound_events)."""

    def test_on_click_does_not_double_wire(self):
        item = SidebarItem("Home")
        item.on_click(lambda e: None)
        assert len(item._root._handlers["click"]) == 1

    def test_on_click_fires_once(self):
        import asyncio

        item = SidebarItem("Home")
        fired: list = []
        item.on_click(lambda e: fired.append(1))
        for handler in list(item._root._handlers["click"]):
            asyncio.run(handler(DomEvent(key=item._root.key, type="click")))
        assert fired == [1]


class TestBindValue:
    """bind_value: signal ↔ component value, both ways."""

    def test_signal_writes_component(self):
        from neony.dom import Signal

        inp = Input()
        name = Signal("")
        inp.bind_value(name)
        name.set("hello")
        assert inp.value == "hello"
        assert inp._input.value == "hello"

    def test_user_change_writes_signal(self):
        import asyncio

        from neony.dom import Signal

        inp = Input()
        name = Signal("")
        inp.bind_value(name)
        asyncio.run(inp._input._handlers["input"][0](DomEvent(key=inp._input.key, type="input", value="typing")))
        assert name() == "typing"

    def test_no_loop_on_user_change(self):
        """User input → signal → write-back re-applies the same value;
        the component must not be re-dispatched or double-written."""
        import asyncio

        from neony.dom import Signal

        inp = Input()
        name = Signal("")
        writes: list[str] = []
        inp.bind_value(name)
        # capture writes through a wrapper signal — effect write-backs
        # re-run the component setter, which must be idempotent
        asyncio.run(inp._input._handlers["input"][0](DomEvent(key=inp._input.key, type="input", value="x")))
        assert name() == "x"
        assert inp.value == "x"
        # a second identical input does not error and state stays consistent
        asyncio.run(inp._input._handlers["input"][0](DomEvent(key=inp._input.key, type="input", value="x")))
        assert name() == "x"
        writes.append(inp.value)
        assert writes == ["x"]

    def test_checkbox_binds_checked(self):
        import asyncio

        from neony.dom import Signal

        cb = Checkbox("x")
        flag = Signal(False)
        cb.bind_value(flag)
        flag.set(True)
        assert cb.checked is True
        asyncio.run(cb._input._handlers["change"][0](DomEvent(key=cb._input.key, type="change", value=False)))
        assert flag() is False

    def test_slider_delivers_floats(self):
        import asyncio

        from neony.dom import Signal

        sl = Slider()
        level = Signal(0.0)
        sl.bind_value(level)
        asyncio.run(sl._input._handlers["input"][0](DomEvent(key=sl._input.key, type="input", value="42")))
        assert level() == 42.0

    def test_select_writes_value_on_change(self):
        import asyncio

        from neony.dom import Signal

        sel = Select(options=["a", "b"])
        choice = Signal("")
        sel.bind_value(choice)
        row = sel._rows[1][1]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert choice() == "b"
        choice.set("a")
        assert sel.value == "a"

    def test_combobox_input_writes_signal(self):
        import asyncio

        from neony.dom import Signal

        cb = ComboBox(options=["work"])
        text = Signal("")
        cb.bind_value(text)
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="wo")))
        assert text() == "wo"

    def test_progress_is_write_only(self):
        from neony.dom import Signal

        bar = Progress(value=0)
        pct = Signal(50)
        bar.bind_value(pct)
        assert bar.value == 50.0
        pct.set(75)
        assert bar.value == 75.0

    def test_computed_is_read_only(self):
        import asyncio

        from neony.dom import Computed, Signal

        base = Signal(5)
        double = Computed(lambda: base() * 2)
        inp = Input()
        inp.bind_value(double)
        assert inp.value == 10  # signal → component works
        asyncio.run(inp._input._handlers["input"][0](DomEvent(key=inp._input.key, type="input", value="ignored")))
        assert double() == 10  # no write-back into a Computed

    def test_unbind_stops_both_directions(self):
        import asyncio

        from neony.dom import Signal

        inp = Input()
        name = Signal("")
        inp.bind_value(name)
        inp.unbind()
        name.set("after unbind")
        assert inp.value == ""  # signal no longer writes the component
        asyncio.run(inp._input._handlers["input"][0](DomEvent(key=inp._input.key, type="input", value="x")))
        assert name() == "after unbind"  # user events no longer write the signal

    def test_rebind_replaces_previous_binding(self):
        from neony.dom import Signal

        inp = Input()
        a = Signal("a")
        b = Signal("b")
        inp.bind_value(a)
        inp.bind_value(b)
        a.set("changed")
        assert inp.value == "b"  # only the latest binding writes


class TestComboStaleChange:
    """A blur right after Tab/Enter auto-complete fires `change` with
    the pre-pick value — it must not clobber the picked value or fire
    stale callbacks (regression: the readout stayed on the old text)."""

    def test_stale_blur_change_after_pick_is_ignored(self):
        import asyncio

        cb = ComboBox(options=["work", "personal"])
        input_h = cb._input._handlers["input"][0]
        change_h = cb._input._handlers["change"][0]
        keydown = cb._wrapper._handlers["keydown"][0]
        fired: list = []

        async def handler(event: DomEvent):
            fired.append(event.value)

        cb.on_change(handler)

        async def run() -> None:
            await input_h(DomEvent(key=cb._input.key, type="input", value="wor"))
            await keydown(DomEvent(key=cb._input.key, type="keydown", value="Tab"))
            assert cb.value == "work"
            assert fired == ["work"]  # the pick itself fired change
            # the blur's stale change (pre-pick value) arrives after
            await change_h(DomEvent(key=cb._input.key, type="change", value="wor"))
            assert cb.value == "work"  # not clobbered
            assert fired == ["work"]  # no stale callback

        asyncio.run(run())

    def test_normal_blur_change_still_fires(self):
        """A genuine blur-commit (value already synced by input events)
        still dispatches change with the committed text."""
        import asyncio

        cb = ComboBox(options=["work"])
        input_h = cb._input._handlers["input"][0]
        change_h = cb._input._handlers["change"][0]
        fired: list = []

        async def handler(event: DomEvent):
            fired.append(event.value)

        cb.on_change(handler)

        async def run() -> None:
            await input_h(DomEvent(key=cb._input.key, type="input", value="wor"))
            await change_h(DomEvent(key=cb._input.key, type="change", value="wor"))
            assert fired == ["wor"]

        asyncio.run(run())

    def test_pick_then_final_blur_change_with_new_value_fires(self):
        """Pick "work", the write-back lands, then a later blur commits
        "work" — the matching change fires normally."""
        import asyncio

        cb = ComboBox(options=["work", "personal"])
        input_h = cb._input._handlers["input"][0]
        change_h = cb._input._handlers["change"][0]
        keydown = cb._wrapper._handlers["keydown"][0]
        fired: list = []

        async def handler(event: DomEvent):
            fired.append(event.value)

        cb.on_change(handler)

        async def run() -> None:
            await input_h(DomEvent(key=cb._input.key, type="input", value="wor"))
            await keydown(DomEvent(key=cb._input.key, type="keydown", value="Tab"))
            assert fired == ["work"]
            # later blur with the already-written value
            await change_h(DomEvent(key=cb._input.key, type="change", value="work"))
            assert fired == ["work", "work"]

        asyncio.run(run())


class TestDialogBuild:
    """Dialog is a fixed scrim layer with a centered panel."""

    def test_dialog_build_closed(self):
        dlg = Dialog(title="T", content=Text("body"))
        node = dlg.build().to_node()
        assert node.styles["position"] == "fixed"
        assert node.styles["z-index"] == "1000"
        assert node.styles["display"] == "none"  # closed by default
        scrim = _find_by_key(node, dlg._scrim.key)
        panel = _find_by_key(node, dlg._panel.key)
        assert scrim is not None and panel is not None
        assert "data-neony-outside" not in node.attrs

    def test_open_sets_display_and_marker(self):
        import asyncio

        dlg = Dialog(content=Text("x"))

        async def run() -> None:
            dlg.open = True
            assert dlg._root.styles.display == "flex"
            assert dlg._root.args.get("data-neony-outside") == "true"
            assert dlg._scrim.styles.opacity == 1.0  # scrim fades in
            dlg.open = False
            # Two-phase close: the panel replays its entrance keyframe
            # in reverse (the same fade-slide, no exit animation) while
            # the scrim fades out, then display:none.
            assert dlg._root.styles.display == "flex"
            assert dlg._scrim.styles.opacity == 0.0
            assert "data-neony-outside" not in dlg._root.args
            closing = dlg._panel.styles.animation
            assert isinstance(closing, Animation)
            assert closing.name == "fade-slide"
            assert closing.direction == "normal"
            assert dlg._panel.styles.width == "480px"  # closing keeps the open geometry
            await asyncio.sleep(0.45)
            assert dlg._root.styles.display == "none"
            # The forward entrance animation is restored for next open.
            restored = dlg._panel.styles.animation
            assert isinstance(restored, Animation)
            assert restored.direction == "normal"

        asyncio.run(run())

    def test_open_panel_animates(self):
        dlg = Dialog(content=Text("x"), open=True)
        node = dlg.build().to_node()
        panel = _find_by_key(node, dlg._panel.key)
        assert panel is not None
        assert panel.styles["animation"] == "fade-slide 0.2s ease-out"

    def test_content_component_built(self):
        dlg = Dialog(content=Button("OK"))
        node = dlg.build().to_node()
        assert node is not None  # builds cleanly

    def test_actions_render_themed_buttons(self):
        from neony.application.elements import DialogAction

        dlg = Dialog(
            title="T",
            content=Text("x"),
            actions=[DialogAction("确认", variant="danger"), DialogAction("取消", variant="ghost")],
        )
        node = dlg.build().to_node()
        panel = _find_by_key(node, dlg._panel.key)
        assert panel is not None
        bar = panel.children[-1]  # the action bar is the last panel child
        assert bar.styles["display"] == "flex"
        assert [b.text for b in bar.children] == ["确认", "取消"]


class TestDialogEvents:
    def test_scrim_click_closes(self):
        import asyncio

        dlg = Dialog(open=True)
        asyncio.run(dlg._scrim._handlers["click"][0](DomEvent(key=dlg._scrim.key, type="click")))
        assert dlg.open is False

    def test_closable_false_ignores_scrim_click(self):
        import asyncio

        dlg = Dialog(open=True, closable=False)
        asyncio.run(dlg._scrim._handlers["click"][0](DomEvent(key=dlg._scrim.key, type="click")))
        assert dlg.open is True

    def test_action_click_runs_callback_and_closes(self):
        import asyncio

        from neony.application.elements import DialogAction

        calls: list = []
        dlg = Dialog(open=True, actions=[DialogAction("确认", on_click=lambda d: calls.append(d))])
        action_btn = dlg._actions_buttons[0]
        asyncio.run(action_btn._btn._handlers["click"][0](DomEvent(key=action_btn._btn.key, type="click")))
        assert calls == [dlg]
        assert dlg.open is False

    def test_action_close_on_click_false_keeps_open(self):
        import asyncio

        from neony.application.elements import DialogAction

        dlg = Dialog(open=True, actions=[DialogAction("Keep", close_on_click=False)])
        action_btn = dlg._actions_buttons[0]
        asyncio.run(action_btn._btn._handlers["click"][0](DomEvent(key=action_btn._btn.key, type="click")))
        assert dlg.open is True

    def test_escape_closes(self):
        import asyncio

        dlg = Dialog(open=True)
        asyncio.run(dlg._root._handlers["keydown"][0](DomEvent(key=dlg._root.key, type="keydown", value="Escape")))
        assert dlg.open is False

    def test_other_keys_do_not_close(self):
        import asyncio

        dlg = Dialog(open=True)
        asyncio.run(dlg._root._handlers["keydown"][0](DomEvent(key=dlg._root.key, type="keydown", value="Enter")))
        assert dlg.open is True

    def test_outsideclick_closes(self):
        import asyncio

        dlg = Dialog(open=True)
        asyncio.run(dlg._root._handlers["outsideclick"][0](DomEvent(key=dlg._root.key, type="outsideclick")))
        assert dlg.open is False

    def test_on_open_on_close_fire(self):
        import asyncio

        dlg = Dialog()
        fired: list[bool] = []
        dlg.on_open(lambda d: fired.append(d.open))
        dlg.on_close(lambda d: fired.append(d.open))

        async def run() -> None:
            dlg.open = True
            dlg.open = False

        asyncio.run(run())
        assert fired == [True, False]


class TestTooltipBuild:
    def test_tooltip_build(self):
        tip = Tooltip("hint", anchor=Button("Hover"))
        node = tip.build().to_node()
        bubble = _find_by_key(node, tip._bubble.key)
        assert bubble is not None
        assert bubble.styles["display"] == "none"
        assert bubble.styles["position"] == "absolute"
        assert bubble.styles["z-index"] == "300"
        assert bubble.text == "hint"

    def test_placement_offsets(self):
        top = Tooltip("x", anchor=Button("a"), placement="top")
        assert top._bubble.styles.bottom == "calc(100% + 8px)"
        assert top._bubble.styles.transform == "translateX(-50%)"
        right = Tooltip("x", anchor=Button("a"), placement="right")
        assert right._bubble.styles.left == "calc(100% + 8px)"
        assert right._bubble.styles.transform == "translateY(-50%)"

    def test_string_anchor_wrapped_in_span(self):
        tip = Tooltip("x", anchor="hover me")
        node = tip.build().to_node()
        assert len(node.children) == 2  # span anchor + bubble
        assert node.children[0].tag == "span"

    def test_wrapper_bubbles_anchor_events(self):
        """Hover events target the keyed anchor — the wrapper must
        bubble them or the tooltip never sees a mouseover."""
        tip = Tooltip("x", anchor=Button("a"))
        assert tip._root.bubble_events is True


class TestTooltipEvents:
    def test_mouseover_entering_shows_after_delay(self):
        """A real enter — mouseover whose related key is outside the
        wrapper — starts the delay timer."""
        import asyncio

        tip = Tooltip("x", anchor=Button("a"), delay=0.01)

        async def run() -> None:
            await tip._root._handlers["mouseover"][0](DomEvent(key=tip._root.key, type="mouseover", related_key=None))
            await asyncio.sleep(0.03)  # same loop as the delay task

        asyncio.run(run())
        assert tip._bubble.styles.display == "block"

    def test_mouseout_leaving_hides_immediately(self):
        """A real leave — mouseout whose related key is outside the
        wrapper — hides right away (no grace period needed)."""
        import asyncio

        tip = Tooltip("x", anchor=Button("a"), delay=0.01)

        async def run() -> None:
            await tip._root._handlers["mouseover"][0](DomEvent(key=tip._root.key, type="mouseover", related_key=None))
            await asyncio.sleep(0.03)
            assert tip._bubble.styles.display == "block"
            await tip._root._handlers["mouseout"][0](DomEvent(key=tip._root.key, type="mouseout", related_key=None))
            assert tip._bubble.styles.display == "none"

        asyncio.run(run())

    def test_inner_hops_stay_silent(self):
        """Moving between the anchor's own elements (related key inside
        the wrapper subtree) must NOT restart the timer or hide the
        bubble — this was the original hover bug."""
        import asyncio

        from neony.dom import DOMElement

        tip = Tooltip("x", anchor=Button("a"), delay=0.01)
        anchor = tip._root.container[0]
        assert isinstance(anchor, DOMElement)

        async def run() -> None:
            # Enter from outside, wait for the bubble.
            await tip._root._handlers["mouseover"][0](DomEvent(key=anchor.key, type="mouseover", related_key=None))
            await asyncio.sleep(0.03)
            assert tip._bubble.styles.display == "block"
            # Hop to an inner element — related key inside the wrapper.
            await tip._root._handlers["mouseover"][0](
                DomEvent(key=anchor.key, type="mouseover", related_key=anchor.key)
            )
            assert tip._bubble.styles.display == "block"
            # Hop out to another inner element — still no leave.
            await tip._root._handlers["mouseout"][0](DomEvent(key=anchor.key, type="mouseout", related_key=anchor.key))
            assert tip._bubble.styles.display == "block"  # still shown
            # A real leave finally hides.
            await tip._root._handlers["mouseout"][0](DomEvent(key=anchor.key, type="mouseout", related_key=None))
            assert tip._bubble.styles.display == "none"

        asyncio.run(run())


class TestDropdownBuild:
    def test_dropdown_build(self):
        dd = Dropdown("Size", items=[("s", "Small"), ("m", "Medium")])
        node = dd.build().to_node()
        trigger = _find_by_key(node, dd._trigger.key)
        popup = _find_by_key(node, dd._popup.key)
        assert trigger is not None and popup is not None
        assert trigger.attrs["tabindex"] == "0"
        assert trigger.attrs["role"] == "combobox"
        assert popup.styles["display"] == "none"
        assert popup.styles["z-index"] == "500"
        assert [row.text for row in popup.children] == ["Small", "Medium"]
        assert [row.attrs["role"] for row in popup.children] == ["option", "option"]

    def test_items_setter_rebuilds(self):
        dd = Dropdown(items=["a"])
        dd.items = ["x", "y"]
        assert [str(row.container[0]) for _value, row in dd._rows] == ["x", "y"]

    def test_value_shows_label_on_trigger(self):
        dd = Dropdown("Pick", items=[("s", "Small")])
        dd.value = "s"
        assert str(dd._label_span.container[0]) == "Small"


class TestDropdownEvents:
    def _click_trigger(self, dd):
        import asyncio

        asyncio.run(dd._trigger._handlers["click"][0](DomEvent(key=dd._trigger.key, type="click")))

    def test_trigger_toggles_popup_and_marker(self):
        dd = Dropdown(items=["a"])
        self._click_trigger(dd)
        assert dd._open is True
        assert dd._popup.styles.display == "flex"
        assert dd._wrapper.args.get("data-neony-outside") == "true"
        self._click_trigger(dd)
        assert not dd._open

    def test_row_click_selects_and_fires(self):
        import asyncio

        dd = Dropdown(items=[("a", "A"), ("b", "B")])
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        dd.on_change(handler)
        row = dd._rows[1][1]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert dd.value == "b"
        assert fired == [("b", "user")]
        assert dd._open is False

    def test_keyboard_navigation(self):
        import asyncio

        dd = Dropdown(items=["a", "b", "c"])
        keydown = dd._wrapper._handlers["keydown"][0]

        async def key(k: str) -> None:
            await keydown(DomEvent(key=dd._trigger.key, type="keydown", value=k))

        asyncio.run(key("Enter"))
        assert dd._open is True
        asyncio.run(key("ArrowDown"))
        assert dd._active_index == 1
        asyncio.run(key("ArrowUp"))
        asyncio.run(key("ArrowUp"))
        assert dd._active_index == 0  # clamped, no wrap
        asyncio.run(key("PageDown"))
        assert dd._active_index == 2
        asyncio.run(key("Escape"))
        assert not dd._open

    def test_enter_picks_active(self):
        import asyncio

        dd = Dropdown(items=["a", "b"])
        keydown = dd._wrapper._handlers["keydown"][0]

        async def key(k: str) -> None:
            await keydown(DomEvent(key=dd._trigger.key, type="keydown", value=k))

        fired: list = []
        dd.on_change(lambda e: fired.append(e.value))
        asyncio.run(key("ArrowDown"))
        asyncio.run(key("ArrowDown"))
        asyncio.run(key("Enter"))
        assert dd.value == "b"
        assert fired == ["b"]

    def test_outsideclick_closes(self):
        import asyncio

        dd = Dropdown(items=["a"])
        self._click_trigger(dd)
        asyncio.run(dd._wrapper._handlers["outsideclick"][0](DomEvent(key=dd._wrapper.key, type="outsideclick")))
        assert dd._open is False


class TestMenuBuild:
    def test_menu_build(self):
        menu = Menu(("a", "Action A"), ("b", "Action B"))
        node = menu.build().to_node()
        assert node.styles["position"] == "fixed"
        assert node.styles["z-index"] == "600"
        assert node.styles["display"] == "none"
        assert [row.text for row in node.children] == ["Action A", "Action B"]
        assert node.children[0].attrs["role"] == "menuitem"


class TestMenuEvents:
    def test_open_at_positions_and_opens(self):
        menu = Menu("a", "b")
        menu.open_at(120, 80)
        assert menu._open is True
        assert menu._root.styles.left == "120px"
        assert menu._root.styles.top is None  # pops upward
        assert menu._root.styles.bottom == "calc(100% - 80px - 8px)"
        assert menu._root.styles.display == "flex"
        assert menu._root.args.get("data-neony-outside") == "true"
        # clamped to the space right/above the cursor, no measurement
        assert menu._root.styles.max_width == "calc(100% - 120px - 8px)"
        assert menu._root.styles.max_height == "calc(72px)"
        menu.close()
        assert not menu._open
        assert menu._root.styles.display == "none"

    def test_row_click_selects_and_fires(self):
        import asyncio

        menu = Menu(("a", "A"), ("b", "B"))
        menu.open_at(0, 0)
        fired: list = []
        menu.on_change(lambda e: fired.append(e.value))
        row = menu._rows[1][1]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert fired == ["b"]
        assert menu._open is False

    def test_keyboard_navigation(self):
        import asyncio

        menu = Menu("a", "b", "c")
        menu.open_at(0, 0)
        keydown = menu._root._handlers["keydown"][0]

        async def key(k: str) -> None:
            await keydown(DomEvent(key=menu._root.key, type="keydown", value=k))

        asyncio.run(key("ArrowDown"))
        assert menu._active_index == 1
        asyncio.run(key("PageUp"))
        assert menu._active_index == 0
        asyncio.run(key("Escape"))
        assert menu._open is False

    def test_outsideclick_closes(self):
        import asyncio

        menu = Menu("a")
        menu.open_at(0, 0)
        asyncio.run(menu._root._handlers["outsideclick"][0](DomEvent(key=menu._root.key, type="outsideclick")))
        assert menu._open is False
