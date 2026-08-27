"""Test the component library: build, state, events, theming."""

import pytest
from pydantic import ValidationError

from neony.application import DARK, LIGHT, Page, Theme
from neony.application.elements import (
    Accordion,
    Avatar,
    Badge,
    Button,
    Card,
    CascadingDropdown,
    Checkbox,
    Collapsible,
    Column,
    ComboBox,
    DataTable,
    Dialog,
    Dropdown,
    Icon,
    Image,
    Input,
    List,
    ListItem,
    Menu,
    MenuBranch,
    MessageBubble,
    NoticeBubble,
    Pane,
    Progress,
    PromptDialog,
    Radio,
    RadioGroup,
    Reorder,
    ReorderItem,
    Select,
    Sidebar,
    SidebarGroup,
    SidebarItem,
    Slider,
    Switch,
    Tabs,
    Text,
    Toast,
    Tooltip,
    Tree,
    TreeNode,
    VStack,
)
from neony.dom import Animation, BoxShadow, Color, Div, DOMElement, DomEvent, NodeDescriptor, Shadow


def _find_by_key(node: NodeDescriptor, key: str) -> NodeDescriptor | None:
    if node.key == key:
        return node
    for child in node.children:
        found = _find_by_key(child, key)
        if found:
            return found
    return None


def _walk(node: NodeDescriptor):
    yield node
    for child in node.children:
        yield from _walk(child)


def _contains_text(node: NodeDescriptor, text: str) -> bool:
    """True when any node in the subtree carries ``text`` as its text content."""
    return any(n.text == text for n in _walk(node))


def _subtree_text(node: NodeDescriptor) -> str:
    """The first non-empty text in the subtree — buttons now render their
    label in a child span, so ``node.text`` on the button is empty."""
    for n in _walk(node):
        if n.text:
            return n.text
    return ""


def _el_text(el: DOMElement | str) -> str:
    """The first non-empty string in a DOMElement subtree (mirrors
    ``_subtree_text`` for live elements, e.g. a component's private root)."""
    if isinstance(el, str):
        return el
    for child in el.container:
        if isinstance(child, str):
            return child
        if isinstance(child, DOMElement):
            found = _el_text(child)
            if found:
                return found
    return ""


def _find_button(node: NodeDescriptor, label: str) -> NodeDescriptor | None:
    """Find a <button> leaf whose text matches ``label``."""
    for n in _walk(node):
        if n.tag == "button" and _contains_text(n, label):
            return n
    return None


def _prompt_action_bar(pd: PromptDialog) -> DOMElement:
    """The confirm/cancel button row of a PromptDialog (panel child 2)."""
    bar = pd._panel.container[2]
    assert isinstance(bar, DOMElement)
    return bar


def _prompt_button(pd: PromptDialog, index: int) -> DOMElement:
    """A PromptDialog action button by index (0 = cancel, 1 = confirm)."""
    btn = _prompt_action_bar(pd).container[index]
    assert isinstance(btn, DOMElement)
    return btn


class TestComponentBuild:
    """Components build into valid DOMElement trees."""

    def test_button_build(self):
        btn = Button("Save")
        node = btn.build().to_node()
        assert node.tag == "button"
        assert _subtree_text(node) == "Save"
        assert node.styles["background-color"] == "var(--color-accent)"

    def test_button_ghost_variant(self):
        btn = Button("Cancel", variant="ghost")
        node = btn.build().to_node()
        assert node.styles["background-color"] == "var(--color-surface)"

    def test_button_primary_text_color(self):
        # Primary sits on a saturated accent fill — text must contrast, not
        # reuse the body text colour (which is dark in light mode).
        node = Button("Save").build().to_node()
        assert node.styles["color"] == "var(--color-on-accent)"

    def test_button_danger_text_color(self):
        node = Button("Delete", variant="danger").build().to_node()
        assert node.styles["color"] == "var(--color-on-danger)"

    def test_button_ghost_text_color(self):
        # Ghost sits on the surface, so it keeps the body text colour.
        node = Button("Cancel", variant="ghost").build().to_node()
        assert node.styles["color"] == "var(--color-text-primary)"

    def test_icon_only_button_has_no_empty_flex_item(self):
        btn = Button("", icon=Icon.glyph("+"))
        node = btn.build().to_node()

        assert len(node.children) == 1
        assert node.styles["justify-content"] == "center"

    def test_button_icon_supports_event_bubbling(self):
        btn = Button("Save", icon=Icon.glyph("+"))

        assert btn._icon_span is not None
        assert btn._btn.bubble_events is True
        assert btn._icon_span.bubble_events is True
        assert btn._btn.args["data-neony-event-scope"] == ""

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
        assert len(node.children) == 2  # bar + panel host
        assert len(node.children[1].children) == 2  # two slots

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
        """The visible panel's slot carries the built-in rise-in animation."""
        tabs = Tabs()
        tabs.add("One", Text("p1"))
        tabs.add("Two", Text("p2"))
        node = tabs.build().to_node()
        active_slot, inactive_slot = node.children[1].children[0], node.children[1].children[1]
        assert active_slot.styles["display"] == "flex"
        assert active_slot.styles["animation"] == "neony-rise-in 0.25s ease-out"
        assert inactive_slot.styles["display"] == "none"
        assert "animation" not in inactive_slot.styles

    def test_tabs_glass_panel_animates(self):
        tabs = Tabs(glass=True)
        tabs.add("One", Text("p1"))
        node = tabs.build().to_node()
        slot = node.children[1].children[0]
        assert slot.styles["animation"] == "neony-rise-in 0.25s ease-out"
        # Glass tint lives on the panel element inside the slot.
        panel = slot.children[0]
        assert panel.styles["backdrop-filter"] == "blur(16px)"

    def test_tabs_tab_button_transitions(self):
        tabs = Tabs()
        tabs.add("One", Text("p1"))
        node = tabs.build().to_node()
        tab = node.children[0].children[0]
        assert tab.styles["transition"] == "all var(--motion-fast) var(--motion-ease-standard)"

    def test_sidebar_item_transitions(self):
        """Active-state style swaps interpolate instead of snapping."""
        item = SidebarItem("Home")
        node = item.build().to_node()
        assert node.styles["transition"] == "all var(--motion-fast) var(--motion-ease-standard)"


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
        assert _subtree_text(btn.build().to_node()) == "B"


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


class TestReorder:
    """The drag-reorder board component: build, order state, drop events."""

    def test_build_row_wrap(self):
        board = Reorder(
            ReorderItem("A", key="a"),
            ReorderItem("B", key="b"),
            ReorderItem("C", key="c"),
            direction="row",
            wrap=True,
            size="76px",
        )
        node = board.build().to_node()
        assert node.styles["flex-direction"] == "row"
        assert node.styles["flex-wrap"] == "wrap"
        assert len(node.children) == 3
        for card in node.children:
            # each card is pre-marked draggable with its declared payload
            assert card.attrs.get("draggable") == "true"
            assert "data-neony-drag" in card.attrs
            assert card.attrs["data-neony-drag"] == card.key
        assert _contains_text(node.children[0], "A")

    def test_build_column_nowrap(self):
        board = Reorder("a", "b", direction="column", wrap=False)
        node = board.build().to_node()
        assert node.styles["flex-direction"] == "column"
        assert node.styles["flex-wrap"] == "nowrap"

    def test_order_and_items_properties(self):
        board = Reorder("a", ReorderItem("B", key="b"), "c")
        assert board.order == ["a", "b", "c"]
        assert [i.content for i in board.items] == ["a", "B", "c"]

    def test_string_label_becomes_key(self):
        board = Reorder("hello")
        assert board.order == ["hello"]

    def test_bare_component_gets_auto_key(self):
        from neony.dom import Signal

        board = Reorder(Signal("x"), Text("hi"))
        assert len(board.order) == 2
        assert board.order[0].startswith("reorder-card-")
        assert board.order[1].startswith("reorder-card-")
        assert board.order[0] != board.order[1]

    def test_duplicate_key_rejected(self):
        with pytest.raises(ValueError):
            Reorder(ReorderItem("A", key="a"), ReorderItem("B", key="a"))

    def test_drop_reorders_row_and_fires(self):
        import asyncio

        board = Reorder(
            ReorderItem("A", key="a"),
            ReorderItem("B", key="b"),
            ReorderItem("C", key="c"),
            direction="row",
            size="76px",
        )
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((list(event.value), event.source))

        board.on_drop(handler)
        board.build()
        cards = {card.key: card for card in board._cards}
        # drop B after C: offset_x = full width → second half
        asyncio.run(cards["c"]._handlers["drop"][0](DomEvent(key="c", type="drop", drag_payload="b", offset_x=76)))
        assert board.order == ["a", "c", "b"]
        assert fired == [(["a", "c", "b"], "user")]

    def test_drop_before_uses_first_half(self):
        import asyncio

        board = Reorder(
            ReorderItem("A", key="a"),
            ReorderItem("B", key="b"),
            ReorderItem("C", key="c"),
            direction="row",
            size="76px",
        )
        board.build()
        cards = {card.key: card for card in board._cards}
        # drop C before B: offset_x = 0 → first half
        asyncio.run(cards["b"]._handlers["drop"][0](DomEvent(key="b", type="drop", drag_payload="c", offset_x=0)))
        assert board.order == ["a", "c", "b"]

    def test_drop_on_itself_is_noop(self):
        import asyncio

        board = Reorder("a", "b", "c")
        board.build()
        cards = {card.key: card for card in board._cards}
        asyncio.run(cards["b"]._handlers["drop"][0](DomEvent(key="b", type="drop", drag_payload="b", offset_x=0)))
        assert board.order == ["a", "b", "c"]

    # ---- flexible content ----

    def test_accepts_any_component_as_card(self):
        inner = Text("Hello")
        board: Reorder = Reorder(ReorderItem(inner, key="x"), ReorderItem("plain"))
        node = board.build().to_node()
        assert _contains_text(node.children[0], "Hello")
        assert node.children[0].attrs["data-neony-drag"] == "x"

    def test_bare_components_enter_without_wrapper(self):
        """Bare components go straight into the board — no ReorderItem
        wrapper; auto keys are generated for them."""
        board: Reorder[Text] = Reorder(Text("Hi"), Text("Yo"))
        items = board.items
        assert isinstance(items[0].content, Text)
        assert isinstance(items[1].content, Text)
        assert items[0].content._text == "Hi"
        assert board.order[0].startswith("reorder-card-")
        assert board.order[1].startswith("reorder-card-")
        assert board.order[0] != board.order[1]

    def test_bare_components_render_as_cards(self):
        """Bare components render: the auto-keyed card is draggable and
        carries the component's content."""
        from neony.application.elements import Card

        board = Reorder(Card("Alpha", title="A"), Card("Beta", title="B"))
        node = board.build().to_node()
        assert len(node.children) == 2
        for card in node.children:
            assert card.attrs["draggable"] == "true"
            assert card.attrs["data-neony-drag"].startswith("reorder-card-")
        assert _contains_text(node.children[0], "Alpha")

    def test_keyed_dom_element_keeps_its_key(self):
        from neony.dom import Div

        el = Div(key="custom")
        board = Reorder(ReorderItem(el))
        assert board.order == ["custom"]
        board2 = Reorder(ReorderItem(el, key="el-key"))  # explicit key wins
        assert board2.order == ["el-key"]

    def test_max_width_constrains_the_board(self):
        board = Reorder("a", "b", max_width="340px")
        node = board.build().to_node()
        assert node.styles["max-width"] == "340px"

    def test_root_gets_a_key(self):
        board = Reorder("a")
        assert board.build().key.startswith("reorder-")

    # ---- cross-board moves ----

    def test_cross_board_drop_moves_the_card(self):
        import asyncio

        board_a = Reorder(ReorderItem("A1", key="a1"), ReorderItem("A2", key="a2"))
        board_b = Reorder(ReorderItem("B1", key="b1"))
        board_a.build()
        board_b.build()
        # drop A2 before B1 on board B (offset_x = 0 → left half)
        asyncio.run(
            board_b._cards[0]._handlers["drop"][0](DomEvent(key="b1", type="drop", drag_payload="a2", offset_x=0))
        )
        assert board_a.order == ["a1"]
        assert board_b.order == ["a2", "b1"]
        assert Reorder._board_by_key["a2"] is board_b

    def test_cross_board_drop_unknown_key_is_noop(self):
        import asyncio

        board = Reorder("a")
        board.build()
        asyncio.run(
            board._cards[0]._handlers["drop"][0](DomEvent(key="a", type="drop", drag_payload="ghost", offset_x=0))
        )
        assert board.order == ["a"]

    def test_cross_board_moves_reuse_dom_content(self):
        import asyncio

        el = Text("shared")
        board_a = Reorder(ReorderItem(el, key="s"))
        board_b = Reorder("b")
        board_a.build()
        board_b.build()
        moved_el = board_a._cards[0].container[0]  # the built root element
        asyncio.run(
            board_b._cards[0]._handlers["drop"][0](DomEvent(key="b", type="drop", drag_payload="s", offset_x=0))
        )
        # the SAME element object moves over (components mount once)
        assert board_b._cards[0].container[0] is moved_el
        assert board_a.order == []
        assert board_b.order == ["s", "b"]


class TestButtonFeedback:
    """Hover / press state drives style changes."""

    def test_hover_adds_glow(self):
        import asyncio

        btn = Button("x")
        assert btn._btn.styles.box_shadow is None
        handler = btn._btn._handlers["mouseover"][0]
        asyncio.run(handler(DomEvent(key=btn._btn.key, type="mouseover")))
        assert str(btn._btn.styles.box_shadow) == ("0 4px 16px var(--color-shadow), 0 0 20px var(--color-accent-glass)")

    def test_danger_hover_glow_uses_danger_color(self):
        import asyncio

        btn = Button("x", variant="danger")
        handler = btn._btn._handlers["mouseover"][0]
        asyncio.run(handler(DomEvent(key=btn._btn.key, type="mouseover")))
        assert "var(--color-danger-glass)" in str(btn._btn.styles.box_shadow or "")

    def test_focus_adds_ring_blur_removes(self):
        import asyncio

        btn = Button("x")
        h_in = btn._btn._handlers["focus"][0]
        h_out = btn._btn._handlers["blur"][0]
        asyncio.run(h_in(DomEvent(key=btn._btn.key, type="focus")))
        assert str(btn._btn.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
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
        assert str(inp._input.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
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
        assert str(cb._input.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(cb._input._handlers["blur"][0](DomEvent(key=cb._input.key, type="blur")))
        assert cb._input.styles.box_shadow is None

    def test_checkbox_focus_ring_survives_check_toggle(self):
        import asyncio

        from neony.application.elements import Checkbox

        cb = Checkbox("x")
        asyncio.run(cb._input._handlers["focus"][0](DomEvent(key=cb._input.key, type="focus")))
        asyncio.run(cb._input._handlers["change"][0](DomEvent(key=cb._input.key, type="change", value=True)))
        assert str(cb._input.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
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


class TestGlassPanelBackground:
    """GlassPanel with a background image must let it show through."""

    def test_background_panel_uses_light_glass_face(self):
        """Regression: the glass face over a background image drops from
        the dense 0.85 panel fill to the 0.60 surface fill — 0.85 plus
        the 0.7 overlay underneath left only ~4% of the image visible."""
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", background="https://example.com/bg.jpg")
        node = panel.build().to_node()
        # root [backdrop, glass]; the glass face is the last child
        glass = node.children[-1]
        assert glass.styles["background-color"] == "var(--color-surface-glass-bg)"

    def test_background_panel_overlay_layer(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", background="https://example.com/bg.jpg")
        node = panel.build().to_node()
        backdrop = node.children[0]
        overlay = "linear-gradient(var(--color-bg-overlay), var(--color-bg-overlay))"
        assert overlay in backdrop.styles["background-image"]

    def test_plain_panel_keeps_dense_face(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content")
        node = panel.build().to_node()
        assert node.styles["background-color"] == "var(--color-surface-panel-glass-bg)"

    def test_grow_panel_wraps_in_styleless_sizing_wrapper(self):
        """grow=True must bound the panel to the parent: a transparent
        styleless wrapper carries flex-grow + min-height:0 and the glass
        face inside fills it — so scroll children (a Tree rail) shrink
        and scroll instead of growing the page."""
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", grow=True)
        node = panel.build().to_node()
        # Root = the sizing wrapper: no paint, flex-grow, min-height:0.
        assert node.styles.get("background-color") is None
        assert node.styles.get("box-shadow") is None
        assert node.styles["flex-grow"] == "1"
        assert node.styles["min-height"] == "0"
        # The glass face (only child) fills the wrapper, also shrinkable.
        face = node.children[0]
        assert face.styles["background-color"] == "var(--color-surface-panel-glass-bg)"
        assert face.styles["flex-grow"] == "1"
        assert face.styles["min-height"] == "0"
        # Content is inside the face.
        assert face.text == "content"

    def test_fixed_size_panel_applies_width_height(self):
        """width/height give a non-grow panel a definite size — the glass
        face gets them directly, so it covers its content."""
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", width="360px", height="252px")
        node = panel.build().to_node()
        assert node.styles["width"] == "360px"
        assert node.styles["height"] == "252px"
        assert node.styles["background-color"] == "var(--color-surface-panel-glass-bg)"

    def test_grow_background_panel_keeps_overlay_inside_wrapper(self):
        from neony.application.elements import GlassPanel

        panel = GlassPanel("content", background="https://example.com/bg.jpg", grow=True)
        node = panel.build().to_node()
        assert node.styles.get("background-color") is None  # styleless wrapper
        face_outer = node.children[0]
        assert face_outer.styles["flex-grow"] == "1"
        assert face_outer.styles["min-height"] == "0"
        backdrop = face_outer.children[0]
        overlay = "linear-gradient(var(--color-bg-overlay), var(--color-bg-overlay))"
        assert overlay in backdrop.styles["background-image"]
        glass = face_outer.children[1]
        # Dense face (0.85) — the grow wrapper keeps the panel's own
        # fill; the 0.60 surface-face swap is only for non-grow panels.
        assert glass.styles["background-color"] == "var(--color-surface-panel-glass-bg)"


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
        assert inner.styles["min-height"] == "0"  # VStack shrink contract
        assert inner.styles["max-width"] == "600px"
        assert inner.styles["margin"] == "0 auto"
        assert len(inner.children) == 1

    def test_theme_to_css(self):
        css = DARK.to_css()
        assert "--color-bg" in css
        assert "--color-surface" in css
        assert ":root" in css

    def test_theme_modes_cycle_order(self):
        modes = Theme.modes()
        assert modes
        assert len(modes) == len(set(modes))
        for current, following in zip(modes, (*modes[1:], modes[0]), strict=True):
            assert Theme.get(current).next() is Theme.get(following)

    def test_theme_modes_not_serialized(self):
        # modes() is a classmethod (not a model field) and must never leak
        # into the CSS block; neither must the registry.
        assert "--color-modes" not in DARK.to_css()
        assert "--color-registry" not in DARK.to_css()

    def test_theme_mode_label(self):
        modes = Theme.modes()
        for current, following in zip(modes, (*modes[1:], modes[0]), strict=True):
            expected = f"{following.replace('-', ' ').title()} mode"
            assert Theme.mode_label(current) == expected
        with pytest.raises(ValueError):
            Theme.mode_label("nonexistent")

    def test_theme_registry_lookup(self):
        for mode in Theme.modes():
            assert Theme.get(mode).mode == mode
        with pytest.raises(KeyError):
            Theme.get("nonexistent")

    def test_theme_on_tokens_radiate(self):
        presets = tuple(Theme.get(mode) for mode in Theme.modes())
        for preset in presets:
            assert "--color-on-danger: #ffffff" in preset.to_css()
            assert "--color-accent:" in preset.to_css()

    def test_theme_families_have_light_and_dark_pairs(self):
        families: dict[str, set[str]] = {}
        for mode in Theme.modes():
            family, variant = mode.rsplit("-", 1)
            assert variant in {"dark", "light"}
            families.setdefault(family, set()).add(variant)
        assert families
        assert all(variants == {"dark", "light"} for variants in families.values())

    def test_theme_immutable(self):
        with pytest.raises(ValidationError):
            DARK.bg = Color(hex="#000000")  # type: ignore[misc]

    def test_theme_requires_all_tokens(self):
        # No defaults: a mode-only construction must be rejected.
        with pytest.raises(ValidationError):
            Theme(mode="x")  # type: ignore[missing-argument]

    def test_theme_stub_tokens_resolve(self):
        """The stub instance exposes typed Color tokens, not strings."""
        from neony.application.theme import stub

        assert isinstance(stub.text_primary, Color)
        assert stub.text_primary.var == "--color-text-primary"
        assert stub.accent_glass.var == "--color-accent-glass"
        assert stub.shadow.var == "--color-shadow"
        # Serialises through the same contract as any Color.
        assert str(stub.text_primary) == "var(--color-text-primary)"

    def test_theme_stub_covers_every_token(self):
        """Every Theme semantic field (minus mode) has a matching token stub.

        ``Theme.shadow`` is a BoxShadow value while ``stub.shadow`` is the
        ``--color-shadow`` Color token reference — a deliberate cross-type pair.
        """
        from neony.application.theme import stub

        stub_attrs = {name for name in stub.__annotations__ if isinstance(getattr(stub, name, None), Color)}
        semantic_fields = {name for name in Theme.model_fields if name != "mode"}
        assert stub_attrs == semantic_fields

    def test_theme_custom_preset_registers(self):
        first_mode = Theme.modes()[0]
        sepia = Theme(
            mode="sepia",
            bg=Color(hex="#1a1a2e"),
            surface=Color(hex="#252540"),
            surface_raised=Color(hex="#2e2e4a"),
            text_primary=Color(hex="#ffffff"),
            text_secondary=Color(hex="#8080a0"),
            accent=Color(hex="#4a90d9"),
            accent_dim=Color(hex="#3a7bc8"),
            danger=Color(hex="#ff6b6b"),
            success=Color(hex="#4ecdc4"),
            border=Color(rgba=(255, 255, 255, 0.06)),
            shadow=BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=Color(rgba=(0, 0, 0, 0.12)))]),
            on_accent=Color(hex="#ffffff"),
            on_danger=Color(hex="#ffffff"),
            bg_overlay=Color(rgba=(26, 26, 46, 0.7)),
            surface_glass=Color(rgba=(54, 54, 92, 0.92)),
            surface_raised_glass=Color(rgba=(64, 64, 104, 0.92)),
            border_glass=Color(rgba=(255, 255, 255, 0.08)),
            accent_glass=Color(rgba=(74, 144, 217, 0.25)),
            danger_glass=Color(rgba=(255, 107, 107, 0.25)),
            success_glass=Color(rgba=(78, 205, 196, 0.25)),
            surface_glass_bg=Color(rgba=(34, 34, 74, 0.60)),
            surface_panel_glass_bg=Color(rgba=(34, 34, 74, 0.85)),
            accent_glass_bg=Color(rgba=(74, 144, 217, 0.60)),
            danger_glass_bg=Color(rgba=(255, 107, 107, 0.60)),
        )
        try:
            assert Theme.get("sepia") is sepia
            assert "sepia" in Theme.modes()
            # Custom preset appends last; next() cycles back to the first mode.
            assert sepia.next() is Theme.get(first_mode)
        finally:
            Theme._registry.pop("sepia", None)


class TestScrollbarTheming:
    # Scrollbars are hidden entirely — WebKitGTK's native hover grows the
    # thumb unsuppressably, so nothing is drawn rather than styled.
    def test_webkit_scrollbar_is_hidden(self):
        css = DARK.to_css()
        assert "::-webkit-scrollbar{width:0;height:0;display:none}" in css

    def test_firefox_scrollbar_is_hidden(self):
        css = DARK.to_css()
        assert "scrollbar-width:none" in css

    def test_scrollbar_rules_survive_theme_switch(self):
        css = LIGHT.to_css()
        assert "::-webkit-scrollbar" in css
        assert "scrollbar-width:none" in css

    def test_thumb_class_rule_present(self):
        # The custom scroll-indicator thumb (JS-built overlay) is themed
        # via a CSS variable so it follows light/dark mode.
        css = DARK.to_css()
        assert ".neony-scroll-thumb{background-color:var(--color-text-secondary);border-radius:999px;}" in css


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
        assert str(radio._input.styles.box_shadow) == "inset 0 0 0 4px var(--color-accent)"
        assert str(radio._input.styles.border) == "1px solid var(--color-accent)"

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
        assert str(shadow) == "0 0 0 3px var(--color-accent-glass), inset 0 0 0 4px var(--color-accent)"
        asyncio.run(radio._input._handlers["blur"][0](DomEvent(key=radio._input.key, type="blur")))
        assert str(radio._input.styles.box_shadow) == "inset 0 0 0 4px var(--color-accent)"


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
        """The group-level change fires once with the selected value and
        carries ``source == "user"`` — the group binds each radio via
        ``_bind`` so the base dispatcher tags user-driven events."""
        group = RadioGroup(Radio("A", value="a"), Radio("B", value="b"))
        fired: list = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        group.on_change(handler)
        self._user_change(group.items[1])
        assert fired == [("b", "user")]

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
        assert str(sw._input.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
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
        assert [_subtree_text(row) for row in popup.children] == ["Red", "Green"]

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
        assert _subtree_text(placeholder) == "Choose…"
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

    def test_label_span_click_selects(self):
        # The label rides a child span — a real click on the text arrives
        # with the span's key, not the row's (see TestDropdownEvents).
        import asyncio

        sel = Select(options=["a", "b"])
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        sel.on_change(handler)
        row = sel._rows[1][1]
        span = row.container[0]
        assert isinstance(span, DOMElement)
        asyncio.run(row._handlers["click"][0](DomEvent(key=span.key, type="click")))
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
        assert str(sel._trigger.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
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
        assert popup.styles["animation"] == "neony-drop-in 0.2s ease-out"


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
        assert popup.styles["animation"] == "neony-drop-in 0.2s ease-out"


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
        # thumb centre rides the inset track: 8px + 30% of the remaining span
        assert thumb.styles["left"] == "calc(8px + (100% - 16px) * 0.300000)"
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
        assert str(sl._thumb.styles.box_shadow) == "0 0 0 3px var(--color-accent-glass)"
        asyncio.run(sl._input._handlers["blur"][0](DomEvent(key=sl._input.key, type="blur")))
        assert str(sl._thumb.styles.box_shadow) == "0 2px 6px var(--color-shadow)"

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

    def test_label_is_first_positional(self):
        """Regression: label is the first positional arg (like every
        other labeled control); value/max are keyword-only."""
        bar = Progress("Loading", value=35)
        node = bar.build().to_node()
        assert node.children[0].text == "Loading"
        assert node.children[0].tag == "span"  # the label span, before the track

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


class TestObjectFitStyle:
    """The Styles.object_fit field serializes to object-fit (kebab-case)."""

    def test_object_fit_serializes(self):
        from neony.dom import Div, Img, Styles

        styles = Styles(object_fit="cover")
        assert styles.object_fit == "cover"
        # end-to-end: the camel/snake field name becomes kebab-case CSS,
        # carried through on both a generic div and an <img>.
        assert "object-fit: cover" in Div(styles=styles).build()
        assert "object-fit: cover" in Img(src="x", styles=styles).build()


class TestPointerEventsStyle:
    """The Styles.pointer_events field serializes to pointer-events."""

    def test_pointer_events_serializes(self):
        from neony.dom import Div, Styles

        assert Styles(pointer_events="none").pointer_events == "none"
        assert "pointer-events: none" in Div(styles=Styles(pointer_events="none")).build()
        # the field is nullable — unset means no pointer-events rule.
        assert "pointer-events" not in Div(styles=Styles(pointer_events=None)).build()


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

    # ---- bind_value channel coverage (Switch/Dropdown/ComboBox) ----

    def test_switch_binds_checked(self):
        import asyncio

        from neony.dom import Signal

        sw = Switch("x")
        flag = Signal(False)
        sw.bind_value(flag)
        flag.set(True)
        assert sw.checked is True
        asyncio.run(sw._input._handlers["change"][0](DomEvent(key=sw._input.key, type="change", value=False)))
        assert flag() is False

    def test_dropdown_writes_value_on_change(self):
        import asyncio

        from neony.dom import Signal

        dd = Dropdown(items=["a", "b"])
        choice = Signal("")
        dd.bind_value(choice)
        row = dd._rows[1][1]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert choice() == "b"
        choice.set("a")
        assert dd.value == "a"

    def test_combobox_pick_writes_signal(self):
        import asyncio

        from neony.dom import Signal

        cb = ComboBox(options=["work"])
        text = Signal("")
        cb.bind_value(text)
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="work")))
        # A pick dispatches `change` — the second bound channel writes back.
        row = cb._rows[0]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert text() == "work"

    def test_combobox_blur_change_writes_signal(self):
        import asyncio

        from neony.dom import Signal

        cb = ComboBox(options=["work"])
        text = Signal("")
        cb.bind_value(text)
        # Real sequence: keystrokes (input) then blur-commit (change).
        asyncio.run(cb._input._handlers["input"][0](DomEvent(key=cb._input.key, type="input", value="work")))
        asyncio.run(cb._input._handlers["change"][0](DomEvent(key=cb._input.key, type="change", value="work")))
        assert text() == "work"


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
            # Two-phase close: the panel reverses its entrance keyframe
            # while the scrim fades out, then animationend/fallback hides
            # the root with display:none.
            assert dlg._root.styles.display == "flex"
            assert dlg._scrim.styles.opacity == 0.0
            assert "data-neony-outside" not in dlg._root.args
            closing = dlg._panel.styles.animation
            assert isinstance(closing, Animation)
            assert closing.name == "fade-slide"
            assert closing.direction == "reverse"
            assert closing.fill_mode == "forwards"
            assert dlg._panel.styles.width == "480px"  # closing keeps the open geometry
            await asyncio.sleep(0.35)
            assert dlg._root.styles.display == "none"
            # The forward entrance animation is restored for next open.
            restored = dlg._panel.styles.animation
            assert isinstance(restored, Animation)
            assert restored.direction == "normal"

        asyncio.run(run())

    def test_animationend_finishes_close_immediately(self):
        import asyncio

        dlg = Dialog(open=True)
        dlg.open = False
        asyncio.run(
            dlg._panel._handlers["animationend"][0](
                DomEvent(key=dlg._panel.key, type="animationend", animation_name="fade-slide")
            )
        )
        assert dlg._root.styles.display == "none"
        assert dlg._close_task is None

    def test_reopen_cancels_pending_close(self):
        import asyncio

        async def run() -> None:
            dlg = Dialog(open=True)
            dlg.open = False
            assert dlg._close_task is not None
            dlg.open = True
            assert dlg._close_task is None
            await asyncio.sleep(0.35)
            assert dlg.open
            assert dlg._root.styles.display == "flex"

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
        assert [_subtree_text(b) for b in bar.children] == ["确认", "取消"]


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


class TestPromptDialogBuild:
    """PromptDialog builds a Dialog with an input field and action row."""

    def test_prompt_dialog_build(self):
        pd = PromptDialog("What's your name?", value="Ada", title="Identify")
        node = pd.build().to_node()
        assert node.tag == "div"  # the fixed overlay root
        assert pd.prompt == "What's your name?"
        assert pd.value == "Ada"
        # Panel children: header + content (with field) + action bar.
        assert len(pd._panel.container) == 3
        assert pd._panel.styles.overflow == "visible"

    def test_value_setter_writes_field(self):
        pd = PromptDialog("Name?")
        pd.value = "Grace"
        assert pd._field.value == "Grace"

    def test_action_buttons_present(self):
        pd = PromptDialog("Name?", confirm_label="Yes", cancel_label="No")
        pd.build()
        action_bar = _prompt_action_bar(pd)
        assert len(action_bar.container) == 2
        # Buttons render their label text inside the bar.
        assert "Yes" in action_bar.build()
        assert "No" in action_bar.build()


class TestPromptDialogEvents:
    """Confirm fires on_submit with the value; cancel doesn't."""

    def test_confirm_button_submits(self):
        import asyncio

        pd = PromptDialog("Name?", value="Ada")
        pd.build()
        submitted: list[str] = []
        pd.on_submit(lambda v: submitted.append(v))
        # Confirm is the last (primary) button in the action bar.
        confirm_btn = _prompt_button(pd, 1)
        asyncio.run(confirm_btn._handlers["click"][0](DomEvent(key=confirm_btn.key, type="click")))
        assert submitted == ["Ada"]
        assert pd.open is False

    def test_cancel_does_not_submit(self):
        import asyncio

        pd = PromptDialog("Name?", value="X")
        pd.build()
        submitted: list[str] = []
        pd.on_submit(lambda v: submitted.append(v))
        cancel_btn = _prompt_button(pd, 0)
        asyncio.run(cancel_btn._handlers["click"][0](DomEvent(key=cancel_btn.key, type="click")))
        assert submitted == []
        assert pd.open is False

    def test_enter_submits(self):
        import asyncio

        pd = PromptDialog("Name?", value="Bob")
        pd.build()
        submitted: list[str] = []
        pd.on_submit(lambda v: submitted.append(v))
        field = pd._field._input
        asyncio.run(field._handlers["keydown"][0](DomEvent(key=field.key, type="keydown", value="Enter")))
        assert submitted == ["Bob"]

    def test_submit_uses_live_value(self):
        import asyncio

        pd = PromptDialog("Name?", value="Ada")
        pd.build()
        submitted: list[str] = []
        pd.on_submit(lambda v: submitted.append(v))
        # User types (input event mirrors into the field), then confirms.
        field = pd._field._input
        asyncio.run(field._handlers["input"][0](DomEvent(key=field.key, type="input", value="Grace")))
        confirm_btn = _prompt_button(pd, 1)
        asyncio.run(confirm_btn._handlers["click"][0](DomEvent(key=confirm_btn.key, type="click")))
        assert submitted == ["Grace"]

    def test_open_close_pseudo_events_inherited(self):
        import asyncio

        pd = PromptDialog("Name?")
        fired: list[bool] = []
        pd.on_open(lambda d: fired.append(d.open))
        pd.on_close(lambda d: fired.append(d.open))

        async def run() -> None:
            pd.open = True
            pd.open = False

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
        assert _subtree_text(bubble) == "hint"

    def test_placement_offsets(self):
        top = Tooltip("x", anchor=Button("a"), placement="top")
        assert top._bubble.styles.bottom == "calc(100% + 8px)"
        assert str(top._bubble.styles.transform) == "translateX(-50%)"
        right = Tooltip("x", anchor=Button("a"), placement="right")
        assert right._bubble.styles.left == "calc(100% + 8px)"
        assert str(right._bubble.styles.transform) == "translateY(-50%)"

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
        assert popup.styles["z-index"] == "1100"
        assert [_subtree_text(row) for row in popup.children] == ["Small", "Medium"]
        assert [row.attrs["role"] for row in popup.children] == ["option", "option"]

    def test_items_setter_rebuilds(self):
        dd = Dropdown(items=["a"])
        dd.items = ["x", "y"]
        assert [_el_text(row) for _value, row in dd._rows] == ["x", "y"]

    def test_value_shows_label_on_trigger(self):
        dd = Dropdown("Pick", items=[("s", "Small")])
        dd.value = "s"
        assert str(dd._label_span.container[0]) == "Small"


class TestDropdownEvents:
    def _click_trigger(self, dd):
        import asyncio

        asyncio.run(dd._trigger._handlers["mousedown"][0](DomEvent(key=dd._trigger.key, type="mousedown")))

    def test_trigger_toggles_popup_and_marker(self):
        dd = Dropdown(items=["a"])
        self._click_trigger(dd)
        assert dd._open is True
        assert dd._popup.styles.display == "flex"
        assert dd._click_away.styles.display == "block"
        assert dd._wrapper.args.get("data-neony-outside") == "true"
        self._click_trigger(dd)
        assert not dd._open
        assert dd._click_away.styles.display == "none"

    def test_click_away_closes_and_can_reopen(self):
        import asyncio

        dd = Dropdown(items=["a"])
        self._click_trigger(dd)
        asyncio.run(dd._click_away._handlers["mousedown"][0](DomEvent(key=dd._click_away.key, type="mousedown")))
        assert not dd._open
        self._click_trigger(dd)
        assert dd._open

    def test_opening_sibling_dropdown_closes_previous_and_raises_active_layer(self):
        from neony.dom import Div

        first = Dropdown(items=["a"])
        second = Dropdown("second", items=["b"])
        Div(container=[first._root, second._root])

        self._click_trigger(first)
        assert first._open
        assert first._wrapper.styles.z_index == 1200

        self._click_trigger(second)
        assert not first._open
        assert first._wrapper.styles.z_index is None
        assert second._open
        assert second._wrapper.styles.z_index == 1200

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

    def test_label_span_click_selects(self):
        # Regression: the label rides a child span, so a real click on the
        # text arrives with the SPAN's key — the row handler must rewrite it
        # to the row's own key before the row lookup (drop-in from the JS
        # closest() bubbling, not the direct row-key path above).
        import asyncio

        dd = Dropdown(items=[("a", "A"), ("b", "B")])
        fired: list[tuple] = []

        async def handler(event: DomEvent):
            fired.append((event.value, event.source))

        dd.on_change(handler)
        row = dd._rows[1][1]
        span = row.container[0]
        assert isinstance(span, DOMElement)
        asyncio.run(row._handlers["click"][0](DomEvent(key=span.key, type="click")))
        assert dd.value == "b"
        assert fired == [("b", "user")]
        assert dd._open is False

    def test_label_span_hover_highlights(self):
        import asyncio

        dd = Dropdown(items=[("a", "A"), ("b", "B")])
        row = dd._rows[1][1]
        span = row.container[0]
        assert isinstance(span, DOMElement)
        asyncio.run(row._handlers["mouseover"][0](DomEvent(key=span.key, type="mouseover")))
        assert 1 in dd._hovered
        asyncio.run(row._handlers["mouseout"][0](DomEvent(key=span.key, type="mouseout")))
        assert 1 not in dd._hovered

    def test_chevron_rotates_without_replacing_glyph(self):
        dd = Dropdown(items=["a"])

        glyph = dd._chevron.container[0]
        assert isinstance(glyph, DOMElement)
        assert glyph.container == ["expand_more"]
        dd._open_popup()
        assert isinstance(glyph, DOMElement)
        assert glyph.container == ["expand_more"]
        assert dd._chevron.styles.transform == "rotate(180deg)"
        dd._close()
        assert dd._chevron.styles.transform is None

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
        assert [_subtree_text(row) for row in node.children] == ["Action A", "Action B"]
        assert node.children[0].attrs["role"] == "menuitem"

    def test_branch_builds_nested_menu(self):
        menu = Menu(MenuBranch("Themes", [("dark", "Dark"), ("light", "Light")]))
        node = menu.build().to_node()
        assert len(menu._branches) == 1
        branch = next(iter(menu._branches.values()))
        assert branch._parent is menu
        assert branch._root.styles.position == "absolute"
        assert branch._root.styles.z_index == 700
        assert branch._root.styles.overflow == "visible"
        assert node.children[0].attrs["data-neony-cascade-row"] == "true"
        assert node.children[0].children[0].attrs["role"] == "menuitem"
        chevron = menu._branch_chevrons[next(iter(menu._branches))]
        glyph = chevron.container[0]
        assert isinstance(glyph, DOMElement)
        assert glyph.container == ["chevron_right"]
        assert chevron.styles.transform is None


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

    def test_label_span_click_selects(self):
        # The label rides a child span — a real click on the text arrives
        # with the span's key, not the row's (see TestDropdownEvents).
        import asyncio

        menu = Menu(("a", "A"), ("b", "B"))
        menu.open_at(0, 0)
        fired: list = []
        menu.on_change(lambda e: fired.append(e.value))
        row = menu._rows[1][1]
        span = row.container[0]
        assert isinstance(span, DOMElement)
        asyncio.run(row._handlers["click"][0](DomEvent(key=span.key, type="click")))
        assert fired == ["b"]
        assert menu._open is False

    def test_hover_applies_and_clears_row_style(self):
        import asyncio

        menu = Menu("a", "b")
        row = menu._rows[1][1]
        asyncio.run(row._handlers["mouseover"][0](DomEvent(key=row.key, type="mouseover")))
        assert str(row.styles.background_color) == "var(--color-surface-glass-bg)"
        asyncio.run(row._handlers["mouseout"][0](DomEvent(key=row.key, type="mouseout")))
        assert str(row.styles.background_color) == "transparent"

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

    def test_sibling_branches_are_mutually_exclusive(self):
        import asyncio

        menu = Menu(
            MenuBranch("Themes", [("dark", "Dark")]),
            MenuBranch("Languages", [("en", "English")]),
        )
        menu.open_at(0, 0)
        first_key = menu._rows[0][1].key
        second_key = menu._rows[1][1].key
        asyncio.run(menu._rows[0][1]._handlers["mouseover"][0](DomEvent(key=first_key, type="mouseover")))
        first = menu._branches[first_key]
        asyncio.run(menu._rows[1][1]._handlers["mouseover"][0](DomEvent(key=second_key, type="mouseover")))
        second = menu._branches[second_key]
        assert first._open is False
        assert second._open is True
        assert menu._branch_chevrons[first_key].styles.transform is None
        assert menu._branch_chevrons[second_key].styles.transform == "rotate(90deg)"

    def test_branch_hover_opens_and_leaf_click_closes_tree(self):
        import asyncio

        menu = Menu(MenuBranch("Themes", [("dark", "Dark"), ("light", "Light")]))
        menu.open_at(0, 0)
        branch_key = menu._rows[0][1].key
        asyncio.run(menu._rows[0][1]._handlers["mouseover"][0](DomEvent(key=branch_key, type="mouseover")))
        branch = menu._branches[branch_key]
        assert branch._open is True
        fired: list[str] = []
        menu.on_change(lambda event: fired.append(event.value))
        leaf = branch._rows[1][1]
        asyncio.run(leaf._handlers["click"][0](DomEvent(key=leaf.key, type="click")))
        assert fired == ["light"]
        assert menu._open is False
        assert branch._open is False

    def test_outsideclick_closes(self):
        import asyncio

        menu = Menu("a")
        menu.open_at(0, 0)
        asyncio.run(menu._root._handlers["outsideclick"][0](DomEvent(key=menu._root.key, type="outsideclick")))
        assert menu._open is False

    def test_opening_second_top_level_menu_closes_first(self):
        first = Menu("first")
        second = Menu("second")
        Div(container=[first._root, second._root])
        first.open_at(10, 10)
        second.open_at(20, 20)

        assert not first._open
        assert first._root.styles.display == "none"
        assert "data-neony-overlay-open" not in first._root.args
        assert second._open
        assert second._root.args["data-neony-overlay-group"] == "context-menu"

    def test_opening_second_menu_closes_first_menu_tree(self):
        first = Menu(MenuBranch("Branch", ["leaf"]))
        branch = next(iter(first._branches.values()))
        second = Menu("second")
        Div(container=[first._root, second._root])
        first.open_at(10, 10)
        branch._open_submenu()
        second.open_at(20, 20)

        assert not first._open
        assert not branch._open
        assert second._open


class TestCascadingDropdown:
    def test_builds_fixed_trigger_and_nested_popup(self):
        picker = CascadingDropdown(
            "Theme",
            items=[MenuBranch("Graphite", [("dark", "Dark"), ("light", "Light")])],
        )
        node = picker.build().to_node()
        assert node.children[1].attrs["role"] == "combobox"
        assert node.children[1].attrs["aria-haspopup"] == "menu"
        assert picker._popup.styles.position == "absolute"
        assert picker._popup.styles.z_index == 1100
        assert picker._popup.styles.overflow == "visible"
        assert len(picker._branches) == 1
        picker._open_popup()
        assert picker._click_away.styles.display == "block"
        from neony.dom import Animation

        animation = picker._popup.styles.animation
        assert isinstance(animation, Animation)
        assert animation.name == "neony-drop-in"
        assert animation.duration == "var(--motion-normal)"
        glyph = picker._chevron.container[0]
        assert isinstance(glyph, DOMElement)
        assert glyph.container == ["expand_more"]
        assert picker._chevron.styles.transform == "rotate(180deg)"

    def test_cascading_dropdown_outsideclick_closes_all_branches(self):
        import asyncio

        picker = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["dark"])])
        picker._open_popup()
        key = next(iter(picker._branches))
        picker._open_branch(key)
        assert picker._wrapper.args["data-neony-outside"] == "true"
        asyncio.run(
            picker._wrapper._handlers["outsideclick"][0](DomEvent(key=picker._wrapper.key, type="outsideclick"))
        )
        assert not picker._open
        assert picker._branches[key].styles.display == "none"
        assert picker._click_away.styles.display == "none"

    def test_cascading_dropdown_click_away_closes_and_can_reopen(self):
        import asyncio

        picker = CascadingDropdown("Theme", items=[MenuBranch("Palette", ["dark"])])
        picker._open_popup()
        asyncio.run(picker._wrapper._handlers["mousedown"][0](DomEvent(key=picker._click_away.key, type="mousedown")))
        assert not picker._open
        picker._open_popup()
        assert picker._open

    def test_cascading_dropdown_does_not_join_context_menu_group(self):
        picker = CascadingDropdown("Theme", items=["dark"])
        picker._open_popup()
        context_menu = Menu("copy")
        context_menu.open_at(10, 10)

        assert picker._open
        assert picker._popup.styles.position == "absolute"
        assert context_menu._open

    def test_opening_sibling_cascading_dropdown_closes_previous(self):
        from neony.dom import Div

        first = CascadingDropdown("first", items=["dark"])
        second = CascadingDropdown("second", items=["light"])
        Div(container=[first._root, second._root])

        first._open_popup()
        assert first._open

        second._open_popup()
        assert not first._open
        assert first._wrapper.styles.z_index is None
        assert second._open
        assert second._wrapper.styles.z_index == 1200

    def test_sibling_branches_are_mutually_exclusive(self):
        picker = CascadingDropdown(
            "Theme",
            items=[
                MenuBranch("Graphite", [("graphite-dark", "Dark")]),
                MenuBranch("Aurora", [("aurora-dark", "Dark")]),
            ],
        )
        first_key, second_key = list(picker._branches)
        picker._open_branch(first_key)
        first = picker._branches[first_key]
        picker._open_branch(second_key)
        second = picker._branches[second_key]
        assert first.styles.display == "none"
        assert second.styles.display == "flex"

    def test_leaf_selection_updates_value_and_dispatches(self):
        import asyncio

        picker = CascadingDropdown(
            "Theme",
            items=[MenuBranch("Graphite", [("dark", "Dark"), ("light", "Light")])],
        )
        picked: list[str] = []
        picker.on_change(lambda event: picked.append(event.value))
        leaf = picker._rows[1][1]
        asyncio.run(leaf._handlers["click"][0](DomEvent(key=leaf.key, type="click")))
        assert picker.value == "light"
        assert picked == ["light"]


class TestImageBuild:
    """Image wraps an <img> in a rounded, overflow-hidden frame."""

    def test_image_build(self):
        img = Image("http://x/y.png", alt="cat")
        node = img.build().to_node()
        assert node.tag == "div"  # the frame
        assert len(node.children) == 1
        inner = node.children[0]
        assert inner.tag == "img"
        assert inner.attrs["src"] == "http://x/y.png"
        assert inner.attrs["alt"] == "cat"
        assert inner.attrs["loading"] == "lazy"
        assert inner.styles["object-fit"] == "cover"
        assert inner.styles["width"] == "100%"
        assert inner.styles["height"] == "100%"

    def test_frame_crops_and_tints(self):
        img = Image("x")
        node = img.build().to_node()
        assert node.styles["overflow"] == "hidden"
        assert node.styles["border-radius"] == "8px"
        # Default placeholder tint is the raised-surface token.
        assert node.styles["background-color"] == "var(--color-surface-raised)"

    def test_fit_serializes(self):
        node = Image("x", fit="contain").build().to_node()
        assert node.children[0].styles["object-fit"] == "contain"

    def test_int_width_to_px(self):
        node = Image("x", width=120, height=80).build().to_node()
        assert node.styles["width"] == "120px"
        assert node.styles["height"] == "80px"

    def test_str_width_passes_through(self):
        node = Image("x", width="40%", height="auto").build().to_node()
        assert node.styles["width"] == "40%"
        assert node.styles["height"] == "auto"

    def test_radius_round(self):
        node = Image("x", radius="50%").build().to_node()
        assert node.styles["border-radius"] == "50%"

    def test_loading_attribute(self):
        node = Image("x", loading="eager").build().to_node()
        assert node.children[0].attrs["loading"] == "eager"

    def test_placeholder_hex_and_token(self):
        # Component.build() returns the DOMElement; DOMElement.build()
        # renders the HTML string.
        assert "background-color: #333333" in Image("x", placeholder="#333333").build().build()
        assert "background-color: transparent" in Image("x", placeholder="transparent").build().build()


class TestImageState:
    def test_src_setter_writes_dom(self):
        img = Image("a")
        img.src = "b"
        assert img.src == "b"
        assert img._img.src == "b"

    def test_alt_setter_writes_dom(self):
        img = Image("a")
        img.alt = "new alt"
        assert img.alt == "new alt"
        assert img._img.alt == "new alt"


class TestBadgeBuild:
    """Badge — inline pill or corner count."""

    def test_inline_neutral_default(self):
        b = Badge("New").build().to_node()
        assert b.tag == "span"
        assert b.text == "New"
        assert b.styles["display"] == "inline-flex"
        assert b.styles["background-color"] == "var(--color-surface-raised)"
        assert b.styles["color"] == "var(--color-text-secondary)"
        assert "position" not in b.styles or b.styles.get("position") is None

    def test_variant_colors(self):
        assert Badge("x", variant="accent").build().to_node().styles["background-color"] == "var(--color-accent)"
        assert Badge("x", variant="danger").build().to_node().styles["background-color"] == "var(--color-danger)"
        assert Badge("x", variant="success").build().to_node().styles["background-color"] == "var(--color-success)"
        # accent/danger/success use white text
        assert Badge("x", variant="accent").build().to_node().styles["color"] == "white"

    def test_dot_renders_no_text(self):
        b = Badge(dot=True).build().to_node()
        assert b.text is None  # empty container
        assert b.styles["display"] == "inline-block"
        assert b.styles["width"] == "8px"
        assert b.styles["height"] == "8px"
        # Dot coloured by variant (default neutral → raised token).
        assert b.styles["background-color"] == "var(--color-surface-raised)"

    def test_corner_position_is_absolute(self):
        b = Badge(3, position="top-right").build().to_node()
        assert b.styles["position"] == "absolute"
        assert b.styles["top"] == "-6px"
        assert b.styles["right"] == "-6px"
        assert b.styles["z-index"] == "10"
        assert b.styles["box-shadow"] == "0 0 0 2px var(--color-bg)"

    def test_corner_overlap_pushes_further(self):
        b = Badge(3, position="top-right", overlap=True).build().to_node()
        assert b.styles["top"] == "-12px"
        assert b.styles["right"] == "-12px"

    def test_max_overflow_format(self):
        assert Badge(150, max=99).build().to_node().text == "99+"
        assert Badge(5, max=99).build().to_node().text == "5"

    def test_zero_hidden_by_default(self):
        assert Badge(0).build().to_node().styles["display"] == "none"
        assert Badge(0, show_zero=True).build().to_node().styles["display"] == "inline-flex"

    def test_string_content_not_clamped(self):
        assert Badge("999").build().to_node().text == "999"


class TestBadgeState:
    def test_content_setter_updates_text_and_visibility(self):
        b = Badge(5)
        b.content = 0
        assert b.build().to_node().styles["display"] == "none"
        # build() can only run once — a fresh instance checks the clamp.
        b2 = Badge(5)
        b2.content = 200
        assert b2.build().to_node().text == "99+"

    def test_variant_setter_swaps_color(self):
        b = Badge("x")
        b.variant = "danger"
        assert b.build().to_node().styles["background-color"] == "var(--color-danger)"

    def test_dot_setter_switches_shape(self):
        b = Badge("x")
        b.dot = True
        node = b.build().to_node()
        assert node.text is None
        assert node.styles["display"] == "inline-block"


class TestAvatarBuild:
    """Avatar — image, initial, or placeholder in a clipped disc."""

    def test_image_avatar_renders_img(self):
        a = Avatar("u.png", name="alice").build().to_node()
        assert a.tag == "div"
        assert len(a.children) == 1
        img = a.children[0]
        assert img.tag == "img"
        assert img.attrs["src"] == "u.png"
        assert img.attrs["alt"] == "alice"  # name used as alt
        assert img.styles["object-fit"] == "cover"

    def test_letter_avatar_initial(self):
        a = Avatar(name="alice bob").build().to_node()
        span = a.children[0]
        assert span.tag == "span"
        assert span.text == "A"
        assert span.styles["color"] == "white"

    def test_unknown_name_falls_back(self):
        assert Avatar().build().to_node().children[0].text == "?"
        assert Avatar(name="   ").build().to_node().children[0].text == "?"

    def test_circle_default_radius(self):
        assert Avatar("u").build().to_node().styles["border-radius"] == "50%"

    def test_square_shape(self):
        assert Avatar("u", shape="square").build().to_node().styles["border-radius"] == "8px"

    def test_custom_radius_overrides(self):
        assert Avatar("u", radius="4px").build().to_node().styles["border-radius"] == "4px"

    def test_size_sets_both_dims(self):
        n = Avatar("u", size="64px").build().to_node()
        assert n.styles["width"] == "64px"
        assert n.styles["height"] == "64px"

    def test_flex_shrink_zero(self):
        # Prevents the avatar being squeezed in an HStack.
        assert Avatar("u").build().to_node().styles["flex-shrink"] == "0"

    def test_no_border(self):
        assert "border" not in Avatar("u", border=False).build().to_node().styles

    def test_alt_overrides_name(self):
        assert Avatar("u", name="alice", alt="photo").build().to_node().children[0].attrs["alt"] == "photo"

    def test_badge_overlay_wraps_relative(self):
        av = Avatar("u", badge=Badge(3, position="top-right"))
        n = av.build().to_node()
        assert n.styles["position"] == "relative"
        assert len(n.children) == 2  # inner disc + badge


class TestAvatarState:
    def test_src_setter_switches_letter_to_image(self):
        # build() runs once; the setter mutates the already-built inner disc.
        av = Avatar(name="A")
        av.build()
        assert av._inner.container[0].build().startswith("<span")  # type: ignore[union-attr]
        av.src = "u.png"
        assert av._inner.container[0].build().startswith("<img")  # type: ignore[union-attr]

    def test_name_setter_updates_initial(self):
        av = Avatar(name="A")
        av.build()
        av.name = "Bob"
        assert av._inner.container[0].to_node().text == "B"  # type: ignore[union-attr]

    def test_size_setter_writes_styles(self):
        av = Avatar("u")
        av.build()
        av.size = "80px"
        styles = av._inner.styles
        assert styles.width == "80px"
        assert styles.height == "80px"


class TestCardBuild:
    """Card — titled content panel, optional glass / actions / footer."""

    def test_card_body_only(self):
        c = Card(Text("hi")).build().to_node()
        assert c.tag == "div"
        assert c.styles["background-color"] == "var(--color-surface)"
        assert c.styles["border"] == "1px solid var(--color-border)"
        assert len(c.children) == 1  # body only

    def test_card_title_creates_header(self):
        c = Card(Text("x"), title="T").build().to_node()
        assert len(c.children) == 2  # header + body
        # The header is a VStack; find the Heading text inside it.
        assert _contains_text(c.children[0], "T")

    def test_card_subtitle(self):
        c = Card(Text("x"), title="T", subtitle="S").build().to_node()
        assert _contains_text(c.children[0], "S")

    def test_card_actions_right_align(self):
        c = Card(Text("x"), title="T", actions=[Button("Edit")]).build().to_node()
        header = c.children[0]
        # Header is an HStack; the last leaf should be the button.
        assert _find_button(header, "Edit") is not None

    def test_card_footer_separator_plus_buttons(self):
        c = Card(Text("x"), footer=[Button("OK")]).build().to_node()
        assert len(c.children) == 3  # body + separator + footer
        assert c.children[1].tag == "div"  # separator renders as a div
        assert _find_button(c.children[2], "OK") is not None

    def test_card_glass_swaps_style(self):
        c = Card(Text("x"), glass=True).build().to_node()
        assert c.styles["background-color"] == "var(--color-surface-panel-glass-bg)"
        assert "blur" in c.styles["backdrop-filter"]

    def test_card_role_glow(self):
        c = Card(Text("x"), glass=True, role="accent").build().to_node()
        assert "var(--color-accent-glass)" in c.styles["box-shadow"]

    def test_card_custom_header_overrides_title(self):
        c = Card(Text("x"), title="ignored", header=Text("custom")).build().to_node()
        header = c.children[0]
        assert header.tag == "span" and header.text == "custom"
        assert not _contains_text(header, "ignored")

    def test_card_clickable_adds_cursor(self):
        c = Card(Text("x"), clickable=True).build().to_node()
        assert c.styles["cursor"] == "pointer"

    def test_card_width(self):
        assert Card(Text("x"), width="320px").build().to_node().styles["width"] == "320px"


class TestCardState:
    def test_title_setter_updates_heading(self):
        card = Card(Text("x"), title="A")
        card.build()
        assert card._title_heading is not None
        card.title = "B"
        assert card._title_heading.text == "B"

    def test_subtitle_setter(self):
        card = Card(Text("x"), title="A", subtitle="old")
        card.build()
        assert card._subtitle_text is not None
        card.subtitle = "new"
        assert card._subtitle_text.text == "new"


class TestCardEvents:
    """Card declares click in _bound_events — on_click must not double-wire."""

    def test_clickable_fires_click(self):
        import asyncio

        card = Card(Text("x"), clickable=True)
        fired: list = []
        card.on_click(lambda e: fired.append(1))
        asyncio.run(card._root._handlers["click"][0](DomEvent(key=card._root.key, type="click")))
        assert fired == [1]

    def test_on_click_does_not_double_wire(self):
        # Regression: _bound_events={"click"} stops on() lazily wiring a
        # second handler alongside the one _bind already attached.
        card = Card(Text("x"), clickable=True)
        card.on_click(lambda e: None)
        assert len(card._root._handlers.get("click", [])) == 1

    def test_non_clickable_has_no_click_handler(self):
        card = Card(Text("x"))
        card.on_click(lambda e: None)
        # click is in _bound_events, so on() won't wire it; and the card
        # wasn't clickable, so _bind never attached one either.
        assert "click" not in card._root._handlers


class TestTabsSelection:
    """Unified selection API on Tabs: constructor children, object-level
    selected_panel, title-key selection, and the active_key fix."""

    def test_constructor_children_pairs(self):
        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        node = tabs.build().to_node()
        assert len(node.children) == 2  # bar + panel host
        assert len(node.children[1].children) == 2  # one slot per panel

    def test_constructor_children_equal_chain(self):
        chained = Tabs()
        chained.add("One", Text("p1"))
        chained.add("Two", Text("p2"))
        direct = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        assert direct._titles == chained._titles

    def test_selected_panel_object_binding(self):
        p1, p2 = Text("p1"), Text("p2")
        tabs = Tabs(("One", p1), ("Two", p2))
        # Binding the raw DOMElement (build() once already mounted it).
        tabs.selected_panel = p2._root
        node = tabs.build().to_node()
        host = node.children[1]
        assert host.children[1].styles["display"] == "flex"
        assert host.children[0].styles["display"] == "none"

    def test_selected_panel_component_binding(self):
        p1, p2 = Text("p1"), Text("p2")
        tabs = Tabs(("One", p1), ("Two", p2))
        # Binding the Component: resolved via identity against registered
        # panels — never a second build().
        tabs.selected_panel = p2
        assert tabs.selected_title == "Two"

    def test_selected_panel_unknown_raises(self):
        tabs = Tabs(("One", Text("p1")))
        with pytest.raises(ValueError):
            tabs.selected_panel = Text("stranger")
        with pytest.raises(ValueError):
            tabs.selected_panel = Div()

    def test_selected_title_returns_title(self):
        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        assert tabs.selected_title == "One"
        tabs.selected_title = "Two"
        assert tabs.selected_title == "Two"

    def test_selected_title_unknown_raises(self):
        tabs = Tabs(("One", Text("p1")))
        with pytest.raises(ValueError):
            tabs.selected_title = "Nope"

    def test_active_alias_and_active_key_returns_title(self):
        """Regression: active_key returned an opaque DOM uuid before;
        it now returns the tab title."""
        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        assert tabs.active == 0
        assert tabs.active_key == "One"
        tabs.active = 1
        assert tabs.active_key == "Two"

    def test_tab_click_dispatches_change_with_title(self):
        import asyncio

        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        fired: list = []
        tabs.on_change(lambda e: fired.append((e.value, e.source)))
        tab = tabs._tab_elems[1]
        asyncio.run(tab._handlers["click"][0](DomEvent(key=tab.key, type="click")))
        assert fired == [("Two", "user")]

    def test_programmatic_select_no_callback(self):

        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        fired: list = []
        tabs.on_change(lambda e: fired.append(1))
        tabs.selected_title = "Two"
        assert fired == []


class TestTabsSelectedKey:
    """Tabs.selected_key (title-as-key) powers bind_selected on Tabs."""

    def test_selected_key_aliases_selected_title(self):
        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        assert tabs.selected_key == "One"
        tabs.selected_key = "Two"
        assert tabs.selected_title == "Two"
        with pytest.raises(ValueError):
            tabs.selected_key = "Nope"
        with pytest.raises(ValueError):
            tabs.selected_key = None  # a tab is always selected

    def test_tabs_bind_selected_two_way(self):
        import asyncio

        from neony.dom import Signal

        tabs = Tabs(("One", Text("p1")), ("Two", Text("p2")))
        active = Signal("One")
        tabs.bind_selected(active)
        active.set("Two")
        assert tabs.selected_title == "Two"
        # User tab click writes the signal back.
        tab = tabs._tab_elems[0]
        asyncio.run(tab._handlers["click"][0](DomEvent(key=tab.key, type="click")))
        assert active() == "One"
        assert tabs.selected_key == "One"


class TestSidebarPaneBuild:
    """Sidebar structural modes: bare rail vs rail + pane host."""

    def test_bare_rail_structure(self):
        sidebar = Sidebar(SidebarItem("Home"))
        node = sidebar.build().to_node()
        # wrapper[row] -> rail only; no pane host.
        assert len(node.children) == 1
        rail = node.children[0]
        assert rail.styles["width"] == "200px"
        assert rail.styles["background-color"] == "var(--color-surface-glass-bg)"

    def test_gallery_bare_rail_config(self):
        """The gallery's bare-rail Sidebar config must keep working unchanged."""
        sidebar = Sidebar(
            SidebarItem("Home", icon=Icon.glyph("🏠")),
            SidebarItem("Settings", icon=Icon.glyph("⚙️")),
            SidebarItem("Profile", icon=Icon.glyph("👤")),
            active_key="home",
            corner_radius="0px",
        )
        node = sidebar.build().to_node()
        rail = node.children[0]
        assert rail.styles["width"] == "200px"
        assert rail.styles["border-top-right-radius"] == "0px"
        assert sidebar.active_key == "home"
        assert sidebar.selected_key == "home"

    def test_pane_sidebar_structure(self):
        sidebar = Sidebar(Pane("Home", panel=Text("home")))
        node = sidebar.build().to_node()
        # wrapper[row] -> rail + host; host holds one slot.
        assert len(node.children) == 2
        host = node.children[1]
        assert len(host.children) == 1
        assert node.styles["flex-grow"] == "1"

    def test_slot_visibility_and_animation(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h")),
            Pane("Settings", panel=Text("s")),
        )
        node = sidebar.build().to_node()
        host = node.children[1]
        active_slot, inactive_slot = host.children[0], host.children[1]
        assert active_slot.styles["display"] == "flex"
        assert active_slot.styles["animation"] == "neony-rise-in 0.25s ease-out"
        assert inactive_slot.styles["display"] == "none"
        assert "animation" not in inactive_slot.styles

    def test_active_slot_stretches_to_host_height(self):
        """Regression: the visible slot must flex-grow so panes that
        stretch themselves (GlassPanel grow=True) resolve against a
        definite parent height.  Without it the panel stops at its
        content height and the host's background shows below."""
        sidebar = Sidebar(Pane("Home", panel=Text("h")))
        node = sidebar.build().to_node()
        host = node.children[1]
        active_slot = host.children[0]
        assert active_slot.styles["flex-grow"] == "1"
        assert active_slot.styles["min-height"] == "0"
        # ... but it must never shrink: a pane taller than the host must
        # push the host's overflow:auto into scrolling, not be compressed
        # into the host height.  flex-shrink would squash the pane's rows
        # together and they would overlap visually.
        assert active_slot.styles["flex-shrink"] == "0"

    def test_pane_switching_toggles_slots(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h")),
            Pane("Settings", panel=Text("s")),
        )
        sidebar.selected_key = sidebar.panes[1].key
        node = sidebar.build().to_node()
        host = node.children[1]
        assert host.children[0].styles["display"] == "none"
        assert host.children[1].styles["display"] == "flex"

    def test_constructor_tuple_panes(self):
        sidebar = Sidebar(("Home", Text("h")))
        node = sidebar.build().to_node()
        assert len(node.children) == 2  # rail + host

    def test_constructor_pane_models(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h"), icon=Icon.glyph("🏠")))
        node = sidebar.build().to_node()
        assert len(node.children[0].children) == 1  # one rail item

    def test_mixed_bare_items_and_panes(self):
        sidebar = Sidebar(
            SidebarItem("About", key="about"),
            Pane("Home", panel=Text("h")),
        )
        node = sidebar.build().to_node()
        rail = node.children[0]
        # bare item first (flat), then pane entry — rail order preserved.
        assert len(rail.children) == 2
        assert len(node.children) == 2  # rail + host

    def test_default_random_key(self):
        """Pane keys default to random ids — labels never collide, even
        when duplicated or non-ASCII."""
        sidebar = Sidebar(Pane("首页", panel=Text("a")), Pane("首页", panel=Text("b")))
        keys = [p.key for p in sidebar.panes]
        assert len(keys) == 2
        assert keys[0] != keys[1]
        # random uuid hex, not derived from the label
        assert keys[0] != "首页".lower()

    def test_explicit_duplicate_key_raises(self):
        with pytest.raises(ValueError):
            Sidebar(Pane("Home", panel=Text("a"), key="x"), Pane("Other", panel=Text("b"), key="x"))

    def test_build_once_second_raises(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h")))
        sidebar.build()
        with pytest.raises(RuntimeError):
            sidebar.build()


class TestSidebarGroup:
    """SidebarGroup: titled sections; post-attach adds stay wired."""

    def test_group_structure(self):
        sidebar = Sidebar(SidebarGroup("General", SidebarItem("Home"), SidebarItem("Settings")))
        node = sidebar.build().to_node()
        rail = node.children[0]
        group = rail.children[0]
        assert len(group.children) == 3  # label + 2 items

    def test_group_label_uppercase_spacing(self):
        group = SidebarGroup("General", SidebarItem("Home"))
        node = group.build().to_node()
        label = node.children[0]
        assert label.styles["text-transform"] == "uppercase"
        assert label.styles["letter-spacing"] == "0.08em"
        assert label.styles["color"] == "var(--color-text-secondary)"

    def test_group_item_click_dispatches_change(self):
        import asyncio

        sidebar = Sidebar(SidebarGroup("General", SidebarItem("Home", key="home")))
        fired: list = []
        sidebar.on_change(lambda e: fired.append((e.value, e.source)))
        item = sidebar._items[0]
        for handler in list(item._root._handlers["click"]):
            asyncio.run(handler(DomEvent(key=item._root.key, type="click")))
        assert fired == [("home", "user")]

    def test_post_attach_group_add_wired(self):
        """Regression: an item added to a group AFTER the group is
        attached to a sidebar is still wired (no double build)."""
        import asyncio

        group = SidebarGroup("General", SidebarItem("Home", key="home"))
        sidebar = Sidebar(group)
        group.add(SidebarItem("Settings", key="settings"))
        assert [i.key for i in sidebar.items] == ["home", "settings"]
        item = sidebar._items[1]
        fired: list = []
        sidebar.on_change(lambda e: fired.append(e.value))
        for handler in list(item._root._handlers["click"]):
            asyncio.run(handler(DomEvent(key=item._root.key, type="click")))
        assert fired == ["settings"]

    def test_post_attach_add_first_becomes_selected(self):
        group = SidebarGroup("General")
        sidebar = Sidebar(group)
        group.add(SidebarItem("Home", key="home"))
        assert sidebar.selected_key == "home"
        assert sidebar._items[0].active is True

    def test_sidebar_add_group_never_rebuilds(self):
        """Items are built once by the group; the sidebar wires the
        built roots — a second build would raise."""
        group = SidebarGroup("General", SidebarItem("Home", key="home"))
        sidebar = Sidebar(group)
        assert [i.key for i in sidebar.items] == ["home"]


class TestSidebarSelection:
    """Object-level selection + key selection on Sidebar."""

    def test_selected_object_binding(self):
        p2 = Pane("Settings", panel=Text("s"), key="settings")
        sidebar = Sidebar(Pane("Home", panel=Text("h")), p2)
        sidebar.selected = p2
        assert sidebar.selected_key == "settings"

    def test_selected_returns_entry_object(self):
        p1 = Pane("Home", panel=Text("h"), key="home")
        sidebar = Sidebar(p1)
        assert sidebar.selected is p1

    def test_selected_unknown_object_raises(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h")))
        with pytest.raises(ValueError):
            sidebar.selected = Pane("Stranger", panel=Text("s"))

    def test_selected_key_readwrite(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), key="home"),
            Pane("Settings", panel=Text("s"), key="settings"),
        )
        sidebar.selected_key = "settings"
        assert sidebar.selected_key == "settings"
        # None needs a fallback_panel — without one it raises.
        with pytest.raises(ValueError):
            sidebar.selected_key = None

    def test_selected_key_none_with_fallback(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), key="home"),
            fallback_panel=Text("nothing selected"),
        )
        sidebar.selected_key = None
        assert sidebar.selected_key is None

    def test_selected_key_unknown_raises(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h")))
        with pytest.raises(ValueError):
            sidebar.selected_key = "nope"

    def test_active_key_alias(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), key="home"),
            active_key="home",
        )
        assert sidebar.active_key == "home"
        # Deprecated alias follows the same None rule.
        with pytest.raises(ValueError):
            sidebar.active_key = None

    def test_first_pane_auto_selected(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        assert sidebar.selected_key == "home"
        node = sidebar.build().to_node()
        assert node.children[1].children[0].styles["display"] == "flex"

    def test_programmatic_select_no_callback(self):

        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        fired: list = []
        sidebar.on_change(lambda e: fired.append(1))
        sidebar.selected_key = "home"
        assert fired == []

    def test_section_auto_grouping(self):
        sidebar = Sidebar(
            Pane("A", panel=Text("a"), section="General"),
            Pane("B", panel=Text("b"), section="General"),
        )
        node = sidebar.build().to_node()
        rail = node.children[0]
        assert len(rail.children) == 1  # one group
        group = rail.children[0]
        assert len(group.children) == 3  # label + 2 items

    def test_section_nonconsecutive_splits(self):
        sidebar = Sidebar(
            Pane("A", panel=Text("a"), section="X"),
            Pane("B", panel=Text("b"), section="Y"),
            Pane("C", panel=Text("c"), section="X"),
        )
        node = sidebar.build().to_node()
        rail = node.children[0]
        assert len(rail.children) == 3  # group X, group Y, group X (split)

    def test_section_none_lands_bare(self):
        sidebar = Sidebar(
            Pane("A", panel=Text("a"), section="X"),
            Pane("B", panel=Text("b")),
        )
        node = sidebar.build().to_node()
        rail = node.children[0]
        assert len(rail.children) == 2  # group X + bare item


class TestSidebarPaneEvents:
    """Change dispatch and live (post-build) registration."""

    def test_item_click_dispatches_change_with_key(self):
        import asyncio

        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), key="home"),
            Pane("Settings", panel=Text("s"), key="settings"),
        )
        fired: list = []
        sidebar.on_change(lambda e: fired.append((e.value, e.source)))
        item = sidebar._items[1]
        for handler in list(item._root._handlers["click"]):
            asyncio.run(handler(DomEvent(key=item._root.key, type="click")))
        assert fired == [("settings", "user")]
        node = sidebar.build().to_node()
        assert node.children[1].children[1].styles["display"] == "flex"

    def test_post_build_add_pane(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.build()
        sidebar.add_pane("Settings", Text("s"), key="settings")
        assert sidebar.selected_key == "home"
        assert "settings" in [p.key for p in sidebar.panes]
        sidebar.selected_key = "settings"
        # Post-build adds land in a live slot; selecting shows it.
        node = sidebar._root.to_node()
        host = node.children[1]
        assert host.children[0].styles["display"] == "none"
        assert host.children[1].styles["display"] == "flex"

    def test_post_build_add_bare_item(self):
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.build()
        sidebar.add(SidebarItem("About", key="about"))
        assert "about" in [i.key for i in sidebar.items]


class TestSidebarShortcuts:
    """Per-pane shortcuts: collected pairs, synthesized user events."""

    def test_shortcuts_returns_pairs(self):
        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), shortcut="Ctrl+1"),
            Pane("Settings", panel=Text("s"), shortcut={"darwin": "Meta+2", "default": "Ctrl+2"}),
        )
        pairs = sidebar.shortcuts()
        assert len(pairs) == 2
        assert pairs[0][0] == "Ctrl+1"
        assert pairs[1][0] == {"darwin": "Meta+2", "default": "Ctrl+2"}

    def test_auto_shortcut_by_default(self):
        # The first pane gets an auto Ctrl+1 unless it declares a manual
        # shortcut (which wins).
        sidebar = Sidebar(Pane("Home", panel=Text("h")))
        assert [combo for combo, _ in sidebar.shortcuts()] == ["Ctrl+1"]

    def test_auto_shortcuts_1_to_9_then_0(self):
        sidebar = Sidebar(*[Pane(f"P{i}", panel=Text("x"), key=f"p{i}") for i in range(1, 11)])
        combos = [combo for combo, _ in sidebar.shortcuts()]
        assert combos == [f"Ctrl+{i % 10}" for i in range(1, 11)]  # Ctrl+1..9, then Ctrl+0

    def test_shortcut_handler_selects_and_dispatches(self):
        import asyncio

        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home", shortcut="Ctrl+1"))
        fired: list = []
        sidebar.on_change(lambda e: fired.append((e.value, e.source)))
        asyncio.run(sidebar.shortcuts()[0][1]())
        assert sidebar.selected_key == "home"
        assert fired == [("home", "user")]

    def test_invalid_shortcut_combo_raises(self):
        with pytest.raises(ValueError):
            Sidebar(Pane("Home", panel=Text("h"), shortcut="X"))


class TestBindSelected:
    """bind_selected: two-way Signal binding on selection components."""

    def test_signal_writes_selection(self):
        from neony.dom import Signal

        sel = Signal("home")
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.bind_selected(sel)
        sel.set("home")
        assert sidebar.selected_key == "home"

    def test_user_selection_writes_signal(self):
        import asyncio

        from neony.dom import Signal

        sel = Signal("home")
        sidebar = Sidebar(
            Pane("Home", panel=Text("h"), key="home"),
            Pane("Settings", panel=Text("s"), key="settings"),
        )
        sidebar.bind_selected(sel)
        item = sidebar._items[1]
        for handler in list(item._root._handlers["click"]):
            asyncio.run(handler(DomEvent(key=item._root.key, type="click")))
        assert sel() == "settings"

    def test_computed_read_only(self):
        from neony.dom import Computed, Signal

        base = Signal("home")
        computed = Computed(lambda: base())
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.bind_selected(computed)
        # Computed has no .set — the writer path never attaches.
        assert sidebar._selected_writer is None

    def test_unbind_removes_writer(self):
        from neony.dom import Signal

        sel = Signal("home")
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.bind_selected(sel)
        sidebar.unbind_selected()
        assert sidebar._selected_effect is None
        assert sidebar._selected_writer is None
        # writer removed from change callbacks
        assert "change" not in sidebar._callbacks or all(
            fn is not sidebar._selected_writer for fn in sidebar._callbacks.get("change", [])
        )

    def test_unbind_clears_both_bindings(self):
        from neony.dom import Signal

        sel = Signal("home")
        sidebar = Sidebar(Pane("Home", panel=Text("h"), key="home"))
        sidebar.bind_selected(sel)
        sidebar.unbind()
        assert sidebar._selected_effect is None


class TestRadioGroupSelection:
    def test_selected_key_alias(self):
        group = RadioGroup(Radio("One", value="1"), Radio("Two", value="2"))
        assert group.selected_key == "1"
        group.selected_key = "2"
        assert group.value == "2"
        assert group.selected_key == "2"


class TestSidebarStylesSerialization:
    def test_text_transform_and_letter_spacing_serialize(self):
        from neony.dom import Styles

        node = Div(styles=Styles(text_transform="uppercase", letter_spacing="0.08em")).to_node()
        assert node.styles["text-transform"] == "uppercase"
        assert node.styles["letter-spacing"] == "0.08em"


class TestCollapsibleBuild:
    """Collapsible structure: header row, content panel, key model."""

    def test_default_key_is_lowercased_title(self):
        c = Collapsible("Inputs", Text("a"))
        assert c.key == "inputs"

    def test_explicit_key(self):
        c = Collapsible("Inputs", Text("a"), key="in")
        assert c.key == "in"

    def test_structure_header_and_content(self):
        c = Collapsible("Inputs", Text("a"), Text("b"))
        node = c.build().to_node()
        assert len(node.children) == 2  # header + content
        header, content = node.children
        assert header.attrs["role"] == "button"
        assert header.attrs["tabindex"] == "0"
        # content holds the two built children
        assert len(content.children) == 2

    def test_content_components_built_once(self):
        t = Text("only")
        Collapsible("X", t).build()
        with pytest.raises(RuntimeError):
            t.build()

    def test_collapsed_content_hidden_expanded_visible(self):
        closed = Collapsible("A", Text("a")).build().to_node()
        assert closed.children[1].styles["display"] == "none"
        opened = Collapsible("B", Text("b"), expanded=True).build().to_node()
        assert opened.children[1].styles["display"] == "flex"
        assert opened.children[1].styles["animation"] == "neony-drop-in 0.25s ease-out"

    def test_chevron_rotates_when_open(self):
        closed = Collapsible("A", Text("a")).build().to_node()
        opened = Collapsible("B", Text("b"), expanded=True).build().to_node()
        # header -> [title, chevron-wrap]; chevron is the wrap's only child.
        closed_chev = closed.children[0].children[1].children[0]
        opened_chev = opened.children[0].children[1].children[0]
        assert "transform" not in closed_chev.styles
        assert opened_chev.styles["transform"] == "rotate(90deg)"


class TestCollapsibleExpanded:
    """Expanded state: programmatic vs user-driven, the no-callback rule."""

    def test_programmatic_set_no_callback(self):
        c = Collapsible("A", Text("a"))
        fired: list = []
        c.on_change(lambda e: fired.append(1))
        c.expanded = True
        c.toggle()
        assert fired == []
        assert c.expanded is False  # True then toggle -> False

    def test_click_toggles_and_dispatches_change(self):
        import asyncio

        c = Collapsible("Solo", Text("x"))
        fired: list = []
        c.on_change(lambda e: fired.append((e.value, e.source)))
        asyncio.run(c._header._handlers["click"][0](DomEvent(key=c._header.key, type="click")))
        assert fired == [("solo", "user")]
        assert c.expanded is True

    def test_click_flips_aria_expanded(self):
        import asyncio

        c = Collapsible("A", Text("a"))
        asyncio.run(c._header._handlers["click"][0](DomEvent(key=c._header.key, type="click")))
        node = c.build().to_node()
        assert node.children[0].attrs["aria-expanded"] == "true"


class TestCollapsibleKeyboard:
    """Keyboard activation via Enter / Space on a role=button header."""

    def test_enter_activates(self):
        import asyncio

        c = Collapsible("Kb", Text("k"))
        fired: list = []
        c.on_change(lambda e: fired.append(e.value))
        asyncio.run(c._header._handlers["keydown"][0](DomEvent(key=c._header.key, type="keydown", value="Enter")))
        assert c.expanded is True
        assert fired == ["kb"]

    def test_space_activates(self):
        import asyncio

        c = Collapsible("Kb", Text("k"))
        asyncio.run(c._header._handlers["keydown"][0](DomEvent(key=c._header.key, type="keydown", value=" ")))
        assert c.expanded is True

    def test_arrow_does_not_activate(self):
        import asyncio

        c = Collapsible("Kb", Text("k"))
        fired: list = []
        c.on_change(lambda e: fired.append(e.value))
        asyncio.run(c._header._handlers["keydown"][0](DomEvent(key=c._header.key, type="keydown", value="ArrowDown")))
        assert c.expanded is False
        assert fired == []


class TestAccordionBuild:
    """Accordion stacking: items, fluent section(), multiple default."""

    def test_items_stacked_in_root(self):
        acc = Accordion(Collapsible("A", Text("a")), Collapsible("B", Text("b")))
        node = acc.build().to_node()
        assert len(node.children) == 2

    def test_section_fluent_returns_self_and_equivalent(self):
        fluent = Accordion(multiple=True).section("A", Text("a")).section("B", Text("b"))
        direct = Accordion(Collapsible("A", Text("a")), Collapsible("B", Text("b")))
        assert [i.key for i in fluent.items] == [i.key for i in direct.items]

    def test_multiple_defaults_true(self):
        assert Accordion().multiple is True

    def test_section_passes_expanded_and_key(self):
        acc = Accordion().section("Open", Text("x"), expanded=True, key="o")
        item = acc.items[0]
        assert item.key == "o"
        assert item.expanded is True

    def test_double_adopt_raises(self):
        c = Collapsible("A", Text("a"))
        Accordion(c)
        with pytest.raises(ValueError):
            Accordion(c)

    def test_build_once_second_raises(self):
        acc = Accordion(Collapsible("A", Text("a")))
        acc.build()
        with pytest.raises(RuntimeError):
            acc.build()


class TestAccordionExpandedKeys:
    """expanded_keys read/programmatic write, and single-open behaviour."""

    def test_expanded_keys_in_order(self):
        acc = Accordion(
            Collapsible("A", Text("a"), expanded=True),
            Collapsible("B", Text("b")),
            Collapsible("C", Text("c"), expanded=True),
        )
        assert acc.expanded_keys == ["a", "c"]

    def test_set_expanded_keys_programmatic_no_callback(self):
        acc = Accordion(Collapsible("A", Text("a")), Collapsible("B", Text("b")))
        fired: list = []
        acc.on_change(lambda e: fired.append(e.value))
        acc.expanded_keys = ["b"]
        assert acc.expanded_keys == ["b"]
        assert fired == []

    def test_set_expanded_keys_unknown_ignored(self):
        acc = Accordion(Collapsible("A", Text("a")))
        acc.expanded_keys = ["nope"]
        assert acc.expanded_keys == []

    def test_single_open_construction_collapses_later_sibling(self):
        a = Collapsible("A", Text("a"), expanded=True)
        b = Collapsible("B", Text("b"), expanded=True)
        acc = Accordion(a, b, multiple=False)
        # Only the first declared-expanded survives; later sibling collapses.
        assert acc.expanded_keys == ["a"]
        assert b.expanded is False

    def test_single_open_mutual_exclusion_on_click(self):
        import asyncio

        a = Collapsible("A", Text("a"), expanded=True)
        b = Collapsible("B", Text("b"))
        acc = Accordion(a, b, multiple=False)
        asyncio.run(b._header._handlers["click"][0](DomEvent(key=b._header.key, type="click")))
        assert a.expanded is False
        assert b.expanded is True
        assert acc.expanded_keys == ["b"]


class TestAccordionChange:
    """Container-level change + the deliberate absence of bind_selected."""

    def test_change_carries_child_key_and_user_source(self):
        import asyncio

        acc = Accordion(multiple=True).section("Inputs", Text("i")).section("Layout", Text("l"))
        fired: list = []
        acc.on_change(lambda e: fired.append((e.value, e.source)))
        first = acc.items[0]
        asyncio.run(first._header._handlers["click"][0](DomEvent(key=first._header.key, type="click")))
        assert fired == [("inputs", "user")]
        assert acc.expanded_keys == ["inputs"]

    def test_selected_key_not_supported(self):
        # Accordion is multi-open by design; the single-value selection
        # protocol does not fit — accessing it must raise (base behaviour).
        acc = Accordion(Collapsible("A", Text("a")))
        with pytest.raises(NotImplementedError):
            _ = acc.selected_key


class TestAccordionStylesSerialization:
    """Styles on the new component serialize through the node bridge."""

    def test_reset_styles_replaces_root(self):
        from neony.dom import Styles

        acc = Accordion(Collapsible("A", Text("a")))
        acc.reset_styles(Styles(display="flex", gap="20px"))
        node = acc.build().to_node()
        assert node.styles["display"] == "flex"
        assert node.styles["gap"] == "20px"

    def test_header_theme_tokens_not_hardcoded(self):
        node = Collapsible("A", Text("a"), expanded=True).build().to_node()
        header = node.children[0]
        # colours flow from CSS custom properties, not literal hex.
        assert header.styles["color"] == "var(--color-text-primary)"
        assert header.styles["background-color"] == "var(--color-surface)"


class TestIcon:
    """The unified Icon type: image vs glyph rendering."""

    def test_image_renders_fixed_square(self):
        from neony.application.elements import Icon

        span = Icon.image("https://example.com/logo.svg").render("18px")
        assert span.styles.background_image == "url(https://example.com/logo.svg)"
        assert span.styles.width == "18px"
        assert span.styles.height == "18px"
        assert span.styles.background_repeat == "no-repeat"
        assert span.container == []  # image icon: no text content

    def test_glyph_renders_text(self):
        from neony.application.elements import Icon

        span = Icon.glyph("🏠").render("16px")
        assert span.container == ["🏠"]
        assert span.styles.font_size == "16px"
        assert span.styles.background_image is None
        assert span.styles.width == "16px"
        assert span.styles.height == "16px"

    def test_repr_distinguishes_kinds(self):
        from neony.application.elements import Icon

        assert repr(Icon.image("x.png")).startswith("Icon.image(")
        assert repr(Icon.glyph("x")).startswith("Icon.glyph(")


class TestTreeNodeModel:
    """TreeNode: builder form, branch/leaf exclusivity, keys."""

    def test_fluent_panel_and_children(self):
        node = TreeNode("Home", key="home").panel(Text("h"))
        assert node.is_leaf
        assert not node.is_branch
        branch = TreeNode("Forms").children(
            TreeNode("Inputs", key="inputs").panel(Text("i")),
            TreeNode("Checks", key="checks").panel(Text("c")),
        )
        assert branch.is_branch
        assert not branch.is_leaf
        assert len(branch._children) == 2

    def test_panel_and_children_mutually_exclusive(self):
        with pytest.raises(ValueError):
            TreeNode("X", panel=Text("p"), children=[TreeNode("Y").panel(Text("q"))])
        node = TreeNode("X").children(TreeNode("Y").panel(Text("q")))
        with pytest.raises(ValueError):
            node.panel(Text("p"))
        leaf = TreeNode("X").panel(Text("p"))
        with pytest.raises(ValueError):
            leaf.children(TreeNode("Y").panel(Text("q")))

    def test_key_defaults_to_random_id(self):
        a, b = TreeNode("A"), TreeNode("B")
        assert a.resolved_key != b.resolved_key
        assert a.resolved_key == a.resolved_key  # stable after resolution

    def test_explicit_key(self):
        assert TreeNode("A", key="a").resolved_key == "a"

    def test_key_builder(self):
        assert TreeNode("A").key_("a").resolved_key == "a"


class TestTreeBuild:
    """Tree structure: rail + host, leaves into slots, branch wrappers."""

    def test_rail_and_host_present(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        node = tree.build().to_node()
        assert len(node.children) == 2  # rail + host
        rail, host = node.children
        assert rail.styles["width"] == "220px"
        assert host.styles["display"] == "flex"

    def test_host_slots_equal_leaf_count(self):
        tree = Tree(
            TreeNode("Home", key="home").panel(Text("h")),
            TreeNode("Forms", key="forms").children(
                TreeNode("Inputs", key="inputs").panel(Text("i")),
                TreeNode("Checks", key="checks").panel(Text("c")),
            ),
        )
        node = tree.build().to_node()
        host = node.children[1]
        assert len(host.children) == 3  # one slot per leaf, branches take none

    def test_branches_expanded_by_default_at_top_level(self):
        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        forms = next(n for n in tree.items if n.resolved_key == "forms")
        assert forms.expanded is True

    def test_branches_hidden_when_expanded_branches_false(self):
        tree = Tree(
            TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))),
            expanded_branches=False,
        )
        forms = next(n for n in tree.items if n.resolved_key == "forms")
        assert forms.expanded is False

    def test_explicit_expanded_wins(self):
        tree = Tree(
            TreeNode("A", key="a", expanded=False).children(TreeNode("X", key="x").panel(Text("x"))),
            TreeNode("B", key="b", expanded=True).children(TreeNode("Y", key="y").panel(Text("y"))),
        )
        assert [n.resolved_key for n in tree.items if n.is_branch and n.expanded] == ["b"]

    def test_arbitrary_depth(self):
        tree = Tree(
            TreeNode("L1", key="l1").children(
                TreeNode("L2", key="l2").children(TreeNode("L3", key="l3").panel(Text("deep")))
            )
        )
        node = tree.build().to_node()
        # No wrapper elements: rows and children columns sit directly in
        # the rail.  root -> [rail, host]; rail -> [L1 row, L1 col];
        # col -> [L2 row, L2 col]; col -> [L3 row].
        rail = node.children[0]
        l2_col = rail.children[1]
        l3_col = l2_col.children[1]
        l3_row = l3_col.children[0]
        assert l3_row.attrs["role"] == "treeitem"
        assert len(tree._nodes) == 3

    def test_rows_are_rail_children_not_wrapped(self):
        # Accordion-style rows: each node's row is a direct child of the
        # rail (or of a children column) — no rectangular wrapper around
        # a branch's row + children column.
        tree = Tree(
            TreeNode("Home", key="home").panel(Text("h")),
            TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))),
        )
        node = tree.build().to_node()
        rail = node.children[0]
        home_row, forms_row = rail.children[0], rail.children[1]
        assert home_row.attrs["role"] == "treeitem"
        assert forms_row.attrs["role"] == "treeitem"
        # The children column is the third child (after the branch row).
        assert len(rail.children) == 3

    def test_leaf_without_panel_raises(self):
        # Fail fast at registration: a leaf must carry a panel.
        with pytest.raises(ValueError):
            Tree(TreeNode("Home", key="home"))

    def test_children_fluent(self):
        tree = Tree().children(
            TreeNode("A", key="a").panel(Text("a")),
            TreeNode("B", key="b").panel(Text("b")),
        )
        assert len(tree.items) == 2


class TestTreeSelection:
    """Single-select leaf semantics mirroring Sidebar."""

    def test_active_key_at_construction(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")), active_key="home")
        assert tree.selected_key == "home"

    def test_unknown_active_key_raises(self):
        with pytest.raises(ValueError):
            Tree(TreeNode("Home", key="home").panel(Text("h")), active_key="nope")

    def test_click_leaf_selects_and_switches_host(self):
        import asyncio

        tree = Tree(
            TreeNode("Home", key="home").panel(Text("h")),
            TreeNode("Inputs", key="inputs").panel(Text("i")),
        )
        row = tree._row_by_key["inputs"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert tree.selected_key == "inputs"
        node = tree.build().to_node()
        host = node.children[1]
        assert host.children[1].styles["display"] == "flex"
        assert host.children[0].styles["display"] == "none"

    def test_click_branch_does_not_select(self):
        import asyncio

        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        row = tree._row_by_key["forms"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert tree.selected_key is None

    def test_programmatic_select_no_callback(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        fired: list = []
        tree.on_change(lambda e: fired.append(e.value))
        tree.selected_key = "home"
        assert fired == []

    def test_unknown_selected_key_raises(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        with pytest.raises(ValueError):
            tree.selected_key = "nope"

    def test_change_carries_leaf_key_user_source(self):
        import asyncio

        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        fired: list = []
        tree.on_change(lambda e: fired.append((e.value, e.source)))
        row = tree._row_by_key["home"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert fired == [("home", "user")]

    def test_bind_selected_two_way(self):
        import asyncio

        from neony.dom import Signal

        tree = Tree(
            TreeNode("Home", key="home").panel(Text("h")),
            TreeNode("Inputs", key="inputs").panel(Text("i")),
        )
        sig = Signal("home")
        tree.bind_selected(sig)
        sig.set("inputs")
        assert tree.selected_key == "inputs"
        row = tree._row_by_key["home"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert sig() == "home"

    def test_active_key_alias(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        tree.active_key = "home"
        assert tree.selected_key == "home"
        assert tree.active_key == "home"


class TestTreeExpandCollapse:
    """Branch toggling: display switch on the children column."""

    def test_toggle_flips_column_and_aria(self):
        import asyncio

        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        row = tree._row_by_key["forms"]
        col = tree._children_cols["forms"]
        assert col.styles.display == "flex"
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert col.styles.display == "none"
        assert row.args["aria-expanded"] == "false"
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert col.styles.display == "flex"
        assert row.args["aria-expanded"] == "true"

    def test_collapse_keeps_subtree_state(self):
        import asyncio

        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        # Select the leaf, then collapse the branch, then re-expand.
        x = tree._row_by_key["x"]
        asyncio.run(x._handlers["click"][0](DomEvent(key=x.key, type="click")))
        forms = tree._row_by_key["forms"]
        asyncio.run(forms._handlers["click"][0](DomEvent(key=forms.key, type="click")))
        asyncio.run(forms._handlers["click"][0](DomEvent(key=forms.key, type="click")))
        assert tree.selected_key == "x"  # selection survives the round trip


class TestTreeKeyboard:
    """Keyboard navigation: arrows, activation, focus ring."""

    def test_enter_activates_leaf(self):
        import asyncio

        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        row = tree._row_by_key["home"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="Enter")))
        assert tree.selected_key == "home"

    def test_space_activates_branch(self):
        import asyncio

        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        row = tree._row_by_key["forms"]
        col = tree._children_cols["forms"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value=" ")))
        assert col.styles.display == "none"  # collapsed

    def test_arrow_down_moves_focus_ring(self):
        import asyncio

        tree = Tree(
            TreeNode("A", key="a").panel(Text("a")),
            TreeNode("B", key="b").panel(Text("b")),
        )
        a = tree._row_by_key["a"]
        b = tree._row_by_key["b"]
        asyncio.run(a._handlers["keydown"][0](DomEvent(key=a.key, type="keydown", value="ArrowDown")))
        assert b.styles.box_shadow is not None
        assert a.styles.box_shadow is None

    def test_arrow_right_expands_collapsed_branch(self):
        import asyncio

        tree = Tree(
            TreeNode("Forms", key="forms", expanded=False).children(TreeNode("X", key="x").panel(Text("x"))),
            expanded_branches=False,
        )
        row = tree._row_by_key["forms"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowRight")))
        col = tree._children_cols["forms"]
        assert col.styles.display == "flex"

    def test_arrow_left_collapses_expanded_branch(self):
        import asyncio

        tree = Tree(TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))))
        row = tree._row_by_key["forms"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowLeft")))
        col = tree._children_cols["forms"]
        assert col.styles.display == "none"

    def test_rows_carry_aria_roles(self):
        tree = Tree(
            TreeNode("Home", key="home").panel(Text("h")),
            TreeNode("Forms", key="forms").children(TreeNode("X", key="x").panel(Text("x"))),
        )
        tree.build().to_node()
        leaf = tree._row_by_key["home"]
        branch = tree._row_by_key["forms"]
        assert leaf.args["role"] == "treeitem"
        assert leaf.args["tabindex"] == "0"
        assert branch.args["role"] == "treeitem"
        assert branch.args["aria-expanded"] == "true"


class TestTreeShortcuts:
    """Leaf shortcuts collected via Tree.shortcuts()."""

    def test_shortcuts_collected(self):
        tree = Tree(
            TreeNode("Home", key="home", shortcut="Ctrl+1").panel(Text("h")),
            TreeNode("Other", key="other").panel(Text("o")),
        )
        combos = [combo for combo, _ in tree.shortcuts()]
        assert combos == ["Ctrl+1"]

    def test_invalid_shortcut_raises_at_registration(self):
        with pytest.raises(ValueError):
            Tree(TreeNode("Home", key="home", shortcut="Nope+Nope+Nope").panel(Text("h")))


class TestTreeStylesSerialization:
    """Theme tokens flow through the new component."""

    def test_reset_styles_replaces_root(self):
        from neony.dom import Styles

        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        tree.reset_styles(Styles(display="flex", gap="20px"))
        node = tree.build().to_node()
        assert node.styles["display"] == "flex"
        assert node.styles["gap"] == "20px"

    def test_theme_tokens_not_hardcoded(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")))
        node = tree.build().to_node()
        rail = node.children[0]
        # The rail is chrome-free (transparent) — no hardcoded colors.
        assert rail.styles.get("background-color") is None
        # The Home leaf row (direct rail child, accordion-style): rounded,
        # transparent, 16px left padding so icons don't hug the edge.
        row_node = rail.children[0]
        assert row_node.styles["background-color"] == "transparent"
        assert row_node.styles["border-radius"] == "8px"
        assert row_node.styles["padding-left"] == "calc(16px + 0 * 16px)"


class TestScrollIndicator:
    """edge_fade now drives the JS scroll indicator (data-neony-scroll is
    auto-derived from overflow at serialization; the static Python mask
    is gone — the JS engine owns the dynamic edge fade)."""

    def test_tabs_bar_scroll_indicator_on_by_default(self):
        tabs = Tabs(("A", Text("p1")))
        assert tabs._bar.scroll_indicator is True

    def test_tabs_edge_fade_false_turns_off_indicator(self):
        tabs = Tabs(("A", Text("p1")), edge_fade=False)
        assert tabs._bar.scroll_indicator is False

    def test_sidebar_rail_scroll_indicator_off_when_edge_fade_false(self):
        sb = Sidebar(SidebarItem("x"), edge_fade=False)
        assert sb._rail.scroll_indicator is False

    def test_tree_rail_scroll_indicator_off_when_edge_fade_false(self):
        tree = Tree(TreeNode("a", key="a").panel(Text("h")), edge_fade=False)
        assert tree._rail.scroll_indicator is False

    def test_serialization_derives_marker_on_tabs_bar(self):
        tabs = Tabs(("A", Text("p1")))
        node = tabs.build().to_node()
        bar = node.children[0]
        # Compact strip: explicit "x-silent" (thumb hidden until hover)
        # overrides the auto-derived horizontal marker.
        assert bar.attrs["data-neony-scroll"] == "x-silent"

    def test_serialization_omits_marker_when_disabled(self):
        tabs = Tabs(("A", Text("p1")), edge_fade=False)
        node = tabs.build().to_node()
        bar = node.children[0]
        assert "data-neony-scroll" not in bar.attrs

    def test_sidebar_serialization_derives_vertical_marker(self):
        sb = Sidebar(SidebarItem("x"))
        node = sb.build().to_node()
        rail = node.children[0]
        assert rail.attrs["data-neony-scroll"] == "y"

    def test_static_masks_removed_from_styles_constants(self):
        from neony.application.elements.sidebar import _SOLID
        from neony.application.elements.treeview import _RAIL

        # JS owns the fade now — no static mask baked into Python styles.
        assert _SOLID.mask_image is None
        assert _RAIL.mask_image is None
        assert Tabs(("A", Text("p1")))._bar.styles.mask_image is None
        assert Sidebar(SidebarItem("x"))._rail.styles.mask_image is None
        assert Tree(TreeNode("a", key="a").panel(Text("h")))._rail.styles.mask_image is None


class TestListBuild:
    """List construction renders option rows with listbox semantics."""

    def test_renders_label_rows(self):
        lst = List("Alice", "Bob", ListItem("Carol", key="carol"))
        node = lst.build().to_node()
        assert node.attrs["role"] == "listbox"
        rows = [c for c in node.children if c.attrs.get("role") == "option"]
        assert [r.text for r in rows] == ["Alice", "Bob", "Carol"]
        assert [r.attrs.get("aria-selected") for r in rows] == ["false", "false", "false"]
        assert all(r.attrs.get("tabindex") == "0" for r in rows)

    def test_default_key_is_label(self):
        lst = List("Alice", "Bob")
        assert lst.items[0].key == "Alice"
        assert lst.items[1].key == "Bob"

    def test_icon_renders(self):
        lst = List(ListItem("X", icon=Icon.glyph("⭐")))
        node = lst.build().to_node()
        row = node.children[0]
        assert _contains_text(row, "X")
        assert _contains_text(row, "⭐")

    def test_duplicate_key_raises(self):
        with pytest.raises(ValueError):
            List("a", ListItem("b", key="a"))

    def test_add_and_children_chainable(self):
        lst = List("a")
        lst.add("b").children("c", "d")
        assert [item.label for item in lst.items] == ["a", "b", "c", "d"]

    def test_scroll_indicator_default(self):
        lst = List("a")
        node = lst.build().to_node()
        assert node.attrs["data-neony-scroll"] == "y"

    def test_edge_fade_false_turns_off_indicator(self):
        lst = List("a", edge_fade=False)
        node = lst.build().to_node()
        assert "data-neony-scroll" not in node.attrs


class TestListSelection:
    """Single-select list semantics mirroring Sidebar / Tree."""

    def test_active_key_at_construction(self):
        lst = List("a", "b", active_key="b")
        assert lst.selected_key == "b"
        node = lst.build().to_node()
        rows = [c for c in node.children if c.attrs.get("role") == "option"]
        assert [r.attrs.get("aria-selected") for r in rows] == ["false", "true"]

    def test_unknown_active_key_raises(self):
        with pytest.raises(ValueError):
            List("a", active_key="nope")

    def test_click_selects_and_dispatches(self):
        import asyncio

        lst = List("a", "b")
        fired: list = []
        lst.on_change(lambda e: fired.append((e.value, e.source)))
        row = lst._row_by_key["b"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert lst.selected_key == "b"
        assert fired == [("b", "user")]

    def test_programmatic_select_no_callback(self):
        lst = List("a", "b")
        fired: list = []
        lst.on_change(lambda e: fired.append(e.value))
        lst.selected_key = "b"
        assert fired == []

    def test_unknown_selected_key_raises(self):
        lst = List("a")
        with pytest.raises(ValueError):
            lst.selected_key = "nope"

    def test_select_none_clears(self):
        lst = List("a", "b", active_key="a")
        lst.selected_key = None
        assert lst.selected_key is None

    def test_enter_selects(self):
        import asyncio

        lst = List("a", "b")
        fired: list = []
        lst.on_change(lambda e: fired.append(e.value))
        row = lst._row_by_key["a"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="Enter")))
        assert lst.selected_key == "a"
        assert fired == ["a"]

    def test_arrow_down_moves_selection(self):
        import asyncio

        lst = List("a", "b", "c", active_key="a")
        fired: list = []
        lst.on_change(lambda e: fired.append(e.value))
        row = lst._row_by_key["a"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowDown")))
        assert lst.selected_key == "b"
        assert fired == ["b"]
        # the focused row now carries the ring
        assert lst._row_by_key["b"].styles.box_shadow is not None
        assert lst._row_by_key["a"].styles.box_shadow is None

    def test_arrow_clamps_at_end_no_dispatch(self):
        import asyncio

        lst = List("a", "b", "c", active_key="c")
        fired: list = []
        lst.on_change(lambda e: fired.append(e.value))
        row = lst._row_by_key["c"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowDown")))
        assert lst.selected_key == "c"
        assert fired == []

    def test_home_end_jump(self):
        import asyncio

        lst = List("a", "b", "c", active_key="b")
        row = lst._row_by_key["b"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="Home")))
        assert lst.selected_key == "a"
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="End")))
        assert lst.selected_key == "c"

    def test_click_clears_focus_ring(self):
        import asyncio

        lst = List("a", "b", "c", active_key="a")
        row_a = lst._row_by_key["a"]
        asyncio.run(row_a._handlers["keydown"][0](DomEvent(key=row_a.key, type="keydown", value="ArrowDown")))
        assert lst._row_by_key["b"].styles.box_shadow is not None
        row_b = lst._row_by_key["b"]
        asyncio.run(row_b._handlers["click"][0](DomEvent(key=row_b.key, type="click")))
        assert lst._row_by_key["b"].styles.box_shadow is None

    def test_bind_selected_two_way(self):
        import asyncio

        from neony.dom import Signal

        lst = List("a", "b")
        sig = Signal("a")
        lst.bind_selected(sig)
        sig.set("b")
        assert lst.selected_key == "b"
        row = lst._row_by_key["a"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert sig() == "a"

    def test_active_key_alias(self):
        lst = List("a", "b")
        lst.active_key = "b"
        assert lst.selected_key == "b"
        assert lst.active_key == "b"


class TestDataTableBuild:
    """Column config + data rows render a sticky-header grid table."""

    def test_renders_header_and_rows(self):
        dt = DataTable(
            columns=[Column("Name"), Column("Age", align="right", width="80px")],
            rows=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 24}],
        )
        node = dt.build().to_node()
        header, body = node.children[0], node.children[1]
        assert len(header.children) == 2
        assert _contains_text(header, "Name")
        assert _contains_text(header, "Age")
        # sticky header
        assert header.styles["position"] == "sticky"
        assert header.styles["top"] == "0"
        assert header.styles["grid-template-columns"] == "1fr 80px"
        # rows + cells
        rows = body.children
        assert len(rows) == 2
        assert [r.attrs["role"] for r in rows] == ["row", "row"]
        assert [[c.text for c in r.children] for r in rows] == [["Alice", "30"], ["Bob", "24"]]
        assert all(c.attrs["role"] == "cell" for c in rows[0].children)
        assert rows[0].styles["grid-template-columns"] == "1fr 80px"

    def test_missing_cell_is_empty(self):
        dt = DataTable(columns=[Column("Name"), Column("Age")], rows=[{"name": "x"}])
        node = dt.build().to_node()
        row = node.children[1].children[0]
        assert [c.text for c in row.children] == ["x", ""]

    def test_format_callback(self):
        dt = DataTable(columns=[Column("Age", format=lambda v: f"{v}岁")], rows=[{"age": 30}])
        node = dt.build().to_node()
        assert node.children[1].children[0].children[0].text == "30岁"

    def test_align_applies_text_align(self):
        dt = DataTable(columns=[Column("Age", align="right")], rows=[{"age": 1}])
        node = dt.build().to_node()
        assert node.children[1].children[0].children[0].styles["text-align"] == "right"

    def test_default_row_key_is_index(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}, {"name": "b"}])
        assert dt._row_keys == ["0", "1"]

    def test_custom_row_key(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], row_key=lambda r: r["name"])
        assert dt._row_keys == ["a"]

    def test_duplicate_row_key_raises(self):
        with pytest.raises(ValueError):
            DataTable(
                columns=[Column("Name")],
                rows=[{"name": "a"}, {"name": "a"}],
                row_key=lambda r: r["name"],
            )

    def test_duplicate_column_key_raises(self):
        with pytest.raises(ValueError):
            DataTable().column("Name").column(Column("name"))

    def test_chainable_column_row(self):
        dt = DataTable().column("Name").column("Age").row({"name": "x", "age": 1})
        assert [col.title for col in dt.columns] == ["Name", "Age"]
        assert dt.rows == [{"name": "x", "age": 1}]
        assert dt._row_keys == ["0"]

    def test_rows_setter_rebuilds(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], row_key=lambda r: r["name"])
        dt.rows = [{"name": "b"}, {"name": "c"}]
        assert [row["name"] for row in dt.rows] == ["b", "c"]
        assert dt._row_keys == ["b", "c"]


class TestDataTableSort:
    """Header sorting — numeric-aware, sort_key override, glyph state."""

    def test_numeric_sort(self):
        dt = DataTable(columns=[Column("Age", sortable=True)], rows=[{"age": 30}, {"age": 9}, {"age": 100}])
        dt.sort_by = ("age", "asc")
        assert [r["age"] for r in dt._display] == [9, 30, 100]
        dt.sort_by = ("age", "desc")
        assert [r["age"] for r in dt._display] == [100, 30, 9]

    def test_str_sort(self):
        dt = DataTable(columns=[Column("Name", sortable=True)], rows=[{"name": "b"}, {"name": "A"}, {"name": "a"}])
        dt.sort_by = ("name", "asc")
        assert [r["name"] for r in dt._display] == ["A", "a", "b"]

    def test_sort_key_override(self):
        dt = DataTable(
            columns=[Column("Name", sortable=True, sort_key=lambda r: r["name"].lower())],
            rows=[{"name": "B"}, {"name": "a"}],
        )
        dt.sort_by = ("name", "asc")
        assert [r["name"] for r in dt._display] == ["a", "B"]

    def test_header_click_toggles(self):
        import asyncio

        dt = DataTable(columns=[Column("Name", sortable=True)], rows=[{"name": "b"}, {"name": "a"}])
        cell = dt._header_cells["name"]
        asyncio.run(cell._handlers["click"][0](DomEvent(key=cell.key, type="click")))
        assert dt.sort_by == ("name", "asc")
        assert [r["name"] for r in dt._display] == ["a", "b"]
        asyncio.run(cell._handlers["click"][0](DomEvent(key=cell.key, type="click")))
        assert dt.sort_by == ("name", "desc")
        assert [r["name"] for r in dt._display] == ["b", "a"]

    def test_sort_preserves_selection(self):
        dt = DataTable(
            columns=[Column("Name", sortable=True)],
            rows=[{"name": "b"}, {"name": "a"}],
            row_key=lambda r: r["name"],
            active_key="b",
        )
        dt.sort_by = ("name", "asc")
        assert dt.selected_key == "b"

    def test_sort_by_invalid_raises(self):
        dt = DataTable(columns=[Column("Name", sortable=True)], rows=[{"name": "a"}])
        with pytest.raises(ValueError):
            dt.sort_by = ("age", "asc")
        with pytest.raises(ValueError):
            dt.sort_by = ("name", "up")

    def test_rows_setter_keeps_sort(self):
        dt = DataTable(columns=[Column("Age", sortable=True)], rows=[{"age": 2}, {"age": 1}])
        dt.sort_by = ("age", "asc")
        dt.rows = [{"age": 5}, {"age": 3}]
        assert [r["age"] for r in dt._display] == [3, 5]

    def test_glyph_marks_active_sort(self):
        dt = DataTable(columns=[Column("Name", sortable=True)], rows=[{"name": "a"}])
        glyph = dt._glyphs["name"]
        icon = glyph.container[0]
        assert isinstance(icon, DOMElement)
        assert icon.container == ["unfold_more"]
        dt.sort_by = ("name", "desc")
        icon = glyph.container[0]
        assert isinstance(icon, DOMElement)
        assert icon.container == ["arrow_downward"]


class TestDataTableSelection:
    """Row selection — single (selected_key) and multi (selected_keys)."""

    def test_single_click_selects(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
        )
        fired: list = []
        dt.on_change(lambda e: fired.append((e.value, e.source)))
        row = dt._row_by_key["b"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert dt.selected_key == "b"
        assert fired == [("b", "user")]
        rows = dt._root.to_node().children[1].children
        assert [r.attrs.get("aria-selected") for r in rows] == ["false", "true"]

    def test_programmatic_no_callback(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], row_key=lambda r: r["name"])
        fired: list = []
        dt.on_change(lambda e: fired.append(e.value))
        dt.selected_key = "a"
        assert fired == []

    def test_unknown_selected_key_raises(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}])
        with pytest.raises(ValueError):
            dt.selected_key = "nope"

    def test_selected_key_none_clears(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], row_key=lambda r: r["name"])
        dt.selected_key = "a"
        dt.selected_key = None
        assert dt.selected_key is None

    def test_multi_toggle(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            selection="multi",
        )
        dt.selected_keys = {"a"}
        row = dt._row_by_key["a"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert dt.selected_keys == frozenset()
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert dt.selected_keys == frozenset({"a"})

    def test_multi_change_carries_toggled_key(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            selection="multi",
        )
        dt.selected_keys = {"a"}
        fired: list = []
        dt.on_change(lambda e: fired.append(e.value))
        row = dt._row_by_key["b"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert fired == ["b"]
        assert dt.selected_keys == frozenset({"a", "b"})

    def test_multi_selected_keys_setter_replaces(self):
        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}, {"name": "c"}],
            row_key=lambda r: r["name"],
            selection="multi",
        )
        dt.selected_keys = {"a", "b"}
        dt.selected_keys = ["c"]
        assert dt.selected_keys == frozenset({"c"})
        dt.selected_keys = None
        assert dt.selected_keys == frozenset()

    def test_multi_unknown_key_raises(self):
        dt = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], selection="multi")
        with pytest.raises(ValueError):
            dt.selected_keys = {"nope"}

    def test_wrong_mode_property_raises(self):
        single = DataTable(columns=[Column("Name")], rows=[{"name": "a"}])
        with pytest.raises(NotImplementedError):
            _ = single.selected_keys
        multi = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], selection="multi")
        with pytest.raises(NotImplementedError):
            _ = multi.selected_key

    def test_bind_selected_multi_raises(self):
        from neony.dom import Signal

        multi = DataTable(columns=[Column("Name")], rows=[{"name": "a"}], selection="multi")
        with pytest.raises(ValueError):
            multi.bind_selected(Signal("a"))

    def test_bind_selected_two_way(self):
        import asyncio

        from neony.dom import Signal

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
        )
        sig = Signal("a")
        dt.bind_selected(sig)
        sig.set("b")
        assert dt.selected_key == "b"
        row = dt._row_by_key["a"]
        asyncio.run(row._handlers["click"][0](DomEvent(key=row.key, type="click")))
        assert sig() == "a"

    def test_rows_replacement_prunes_selection(self):
        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            active_key="a",
        )
        dt.rows = [{"name": "c"}]
        assert dt.selected_key is None


class TestDataTableKeyboard:
    """Keyboard nav — single selects, multi moves a focus ring."""

    def test_arrow_down_single_moves_selection(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            active_key="a",
        )
        fired: list = []
        dt.on_change(lambda e: fired.append(e.value))
        row = dt._row_by_key["a"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowDown")))
        assert dt.selected_key == "b"
        assert fired == ["b"]

    def test_arrow_clamps_at_end(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            active_key="b",
        )
        fired: list = []
        dt.on_change(lambda e: fired.append(e.value))
        row = dt._row_by_key["b"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowDown")))
        assert dt.selected_key == "b"
        assert fired == []

    def test_arrow_down_multi_moves_focus_only(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            selection="multi",
        )
        row = dt._row_by_key["a"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value="ArrowDown")))
        assert dt.selected_keys == frozenset()
        assert dt._focus_key == "b"

    def test_space_toggles_multi(self):
        import asyncio

        dt = DataTable(
            columns=[Column("Name")],
            rows=[{"name": "a"}, {"name": "b"}],
            row_key=lambda r: r["name"],
            selection="multi",
        )
        fired: list = []
        dt.on_change(lambda e: fired.append(e.value))
        row = dt._row_by_key["a"]
        asyncio.run(row._handlers["keydown"][0](DomEvent(key=row.key, type="keydown", value=" ")))
        assert dt.selected_keys == frozenset({"a"})
        assert fired == ["a"]


class TestProgrammaticMirrorToSignal:
    """Programmatic value/selected_key/checked writes mirror into the
    bound signal — the setter is the sync point, users never write
    ``signal.set`` themselves."""

    def test_list_selected_key_mirrors(self):
        from neony.dom import Signal

        lst = List("a", "b")
        sig = Signal("a")
        lst.bind_selected(sig)
        lst.selected_key = "b"
        assert sig() == "b"

    def test_datatable_selected_key_mirrors(self):
        from neony.dom import Signal

        dt = DataTable(columns=[Column("N")], rows=[{"n": "a"}, {"n": "b"}], row_key=lambda r: r["n"])
        sig = Signal("a")
        dt.bind_selected(sig)
        dt.selected_key = "b"
        assert sig() == "b"

    def test_combobox_value_mirrors(self):
        from neony.dom import Signal

        cb = ComboBox("Tag", options=["work"])
        sig = Signal("")
        cb.bind_value(sig)
        cb.value = "work"
        assert sig() == "work"

    def test_input_value_mirrors(self):
        from neony.dom import Signal

        inp = Input()
        sig = Signal("")
        inp.bind_value(sig)
        inp.value = "hi"
        assert sig() == "hi"

    def test_checkbox_checked_mirrors(self):
        from neony.dom import Signal

        cb = Checkbox("x")
        sig = Signal(False)
        cb.bind_value(sig)
        cb.checked = True
        assert sig() is True

    def test_mirror_is_loop_safe(self):
        """signal → component effect must not ping-pong with the mirror."""
        from neony.dom import Signal

        lst = List("a", "b")
        sig = Signal("a")
        lst.bind_selected(sig)
        lst.selected_key = "b"  # mirror: sig → b
        sig.set("a")  # drives the component back
        assert lst.selected_key == "a"
        assert sig() == "a"

    def test_mirror_fires_no_user_callback(self):
        from neony.dom import Signal

        lst = List("a", "b")
        sig = Signal("a")
        lst.bind_selected(sig)
        fired: list = []
        lst.on_change(lambda e: fired.append(e.value))
        lst.selected_key = "b"
        assert fired == []
        assert sig() == "b"

    def test_unbind_stops_mirror(self):
        from neony.dom import Signal

        lst = List("a", "b")
        sig = Signal("a")
        lst.bind_selected(sig)
        lst.unbind_selected()
        lst.selected_key = "b"
        assert sig() == "a"  # no longer mirrored


class TestListVirtualization:
    def test_large_list_materializes_bounded_window(self):
        items = [f"item-{i}" for i in range(1000)]
        listing = List(*items)

        assert listing._virtualized is True
        assert len(listing.items) == 1000
        assert len(listing._row_by_key) <= 26
        assert len(listing._root.container) == len(listing._row_by_key) + 2
        hidden = len(listing.items) - listing._virtual_end
        assert listing._bottom_spacer.styles.height == f"{hidden * listing._VIRTUAL_ROW_HEIGHT}px"

    def test_small_list_keeps_full_dom(self):
        listing = List(*(f"item-{i}" for i in range(200)))

        assert listing._virtualized is False
        assert len(listing._row_by_key) == 200
        assert len(listing._root.container) == 200

    def test_scroll_replaces_window_and_preserves_full_model(self):
        listing = List(*(f"item-{i}" for i in range(1000)))
        first_rows = set(listing._row_by_key)

        target = 500
        scroll_top = target * listing._VIRTUAL_ROW_HEIGHT
        listing._handle_scroll(DomEvent(key=listing._root.key, type="scroll", scroll_top=scroll_top, client_height=500))

        assert listing._virtual_start == target - listing._VIRTUAL_OVERSCAN
        assert "item-500" in listing._row_by_key
        assert not first_rows.intersection(listing._row_by_key)
        assert [item.key for item in listing.items[:2]] == ["item-0", "item-1"]

    def test_offscreen_programmatic_selection_keeps_public_semantics(self):
        listing = List(*(f"item-{i}" for i in range(1000)))

        listing.selected_key = "item-900"

        assert listing.selected_key == "item-900"
        assert "item-900" not in listing._row_by_key

    def test_keyboard_end_materializes_target(self):
        import asyncio

        listing = List(*(f"item-{i}" for i in range(1000)))
        event = DomEvent(key="row:item-0", type="keydown", value="End")

        asyncio.run(listing._make_keydown_handler("item-0")(event))

        assert listing.selected_key == "item-999"
        assert "item-999" in listing._row_by_key
        assert listing._focus_key == "item-999"

    def test_reactive_rows_dispose_effects_when_scrolled_out(self):
        from neony.dom import Signal

        signals = [Signal(f"item-{i}") for i in range(250)]
        listing = List(*(ListItem(signal, key=f"item-{i}") for i, signal in enumerate(signals)))
        assert signals[0]._subs

        scroll_top = 210 * listing._VIRTUAL_ROW_HEIGHT
        listing._handle_scroll(DomEvent(key=listing._root.key, type="scroll", scroll_top=scroll_top, client_height=500))

        assert signals[0]._subs == set()
        assert signals[210]._subs


class TestDataTableParentChain:
    """Rebuilt rows must keep _parent links so dirty changes propagate."""

    def test_body_parent_is_root(self):
        dt = DataTable(columns=[Column("N")], rows=[{"n": "a"}], row_key=lambda r: r["n"])
        assert dt._body._parent is dt._root

    def test_rows_parent_is_body(self):
        dt = DataTable(columns=[Column("N")], rows=[{"n": "a"}, {"n": "b"}], row_key=lambda r: r["n"])
        assert dt._row_by_key["a"]._parent is dt._body

    def test_column_rebuild_keeps_parent(self):
        dt = DataTable().column("Name").row({"name": "x"})
        assert dt._body._parent is dt._root
        assert dt._row_by_key["0"]._parent is dt._body


class TestToastBuild:
    """Toast host layer + card construction."""

    def test_root_is_pass_through_layer(self):
        toast = Toast()
        assert toast._root.styles.position == "fixed"
        assert toast._root.styles.pointer_events == "none"
        assert toast._root.styles.z_index == 1200
        assert toast._root.styles.display == "flex"
        assert toast._root.styles.flex_direction == "column"

    def test_placement_alignment(self):
        from neony.application.elements import Toast

        top_right = Toast(placement="top-right")
        assert top_right._root.styles.align_items == "flex-end"
        assert top_right._root.styles.justify_content == "flex-start"
        bottom_center = Toast(placement="bottom-center")
        assert bottom_center._root.styles.align_items == "center"
        assert bottom_center._root.styles.justify_content == "flex-end"

    def test_placement_setter_relocates(self):
        from neony.application.elements import Toast

        toast = Toast(placement="top-right")
        toast.placement = "bottom-left"
        assert toast.placement == "bottom-left"
        assert toast._prepend is False
        assert toast._suffix == "bl"
        assert toast._root.styles.align_items == "flex-start"
        assert toast._root.styles.justify_content == "flex-end"
        toast.show("x")
        anim = toast._cards[0].el.styles.animation
        assert isinstance(anim, Animation)
        assert anim.name == "neony-toast-in-bl"

    def test_top_offset_clears_chrome(self):
        """Top placements start below top_offset (e.g. a TitleBar); bottom
        placements still hug the window edge."""
        from neony.application.elements import Toast

        top = Toast(placement="top-right", top_offset="40px")
        assert top._root.styles.top == "40px"
        # relocating keeps the offset
        top.placement = "top-left"
        assert top._root.styles.top == "40px"
        bottom = Toast(placement="bottom-left", top_offset="40px")
        assert bottom._root.styles.top == "0"

    def test_show_creates_card(self):
        from neony.application.theme import stub

        toast = Toast()
        toast.show("Saved", type="success")
        assert len(toast._cards) == 1
        card = toast._cards[0].el
        assert card.styles.pointer_events == "auto"
        assert card.args.get("role") == "status"
        # a coloured accent dot, the message, and a ✕ button.
        dot = card.container[0]
        assert isinstance(dot, DOMElement)
        assert dot.styles.background_color == stub.success
        assert "Saved" in card.build()

    def test_type_colors(self):
        from neony.application.elements import Toast
        from neony.application.theme import stub

        def dot(toast: Toast) -> DOMElement:
            el = toast._cards[0].el.container[0]
            assert isinstance(el, DOMElement)
            return el

        info = Toast()
        info.show("i", type="info")
        assert dot(info).styles.background_color == stub.accent
        error = Toast()
        error.show("e", type="error")
        assert dot(error).styles.background_color == stub.danger

    def test_top_prepends_bottom_appends(self):
        from neony.application.elements import Toast

        def label(record) -> str:
            span = record.el.container[1]
            assert isinstance(span, DOMElement)
            return str(span.container[0])

        top = Toast(placement="top-right")
        top.show("A")
        top.show("B")
        assert label(top._cards[0]) == "B"  # newest on top
        assert label(top._cards[1]) == "A"

        bottom = Toast(placement="bottom-right")
        bottom.show("A")
        bottom.show("B")
        assert label(bottom._cards[0]) == "A"  # newest hugs the edge
        assert label(bottom._cards[1]) == "B"

    def test_enter_keyframe_matches_placement(self):
        from neony.application.elements import Toast

        def enter_name(toast: Toast) -> str:
            anim = toast._cards[0].el.styles.animation
            assert isinstance(anim, Animation)
            return anim.name

        top_right = Toast(placement="top-right")
        top_right.show("x")
        assert enter_name(top_right) == "neony-toast-in-tr"

        bottom_center = Toast(placement="bottom-center")
        bottom_center.show("x")
        assert enter_name(bottom_center) == "neony-toast-in-bc"


class TestToastState:
    """Auto-dismiss, eviction, clear."""

    def test_auto_dismiss_removes_after_duration(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="top-right")

        async def run() -> None:
            toast.show("x", duration=0.02)
            assert len(toast._cards) == 1
            await asyncio.sleep(0.4)  # duration + exit animation
            assert len(toast._cards) == 0

        asyncio.run(run())

    def test_zero_duration_sticks(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="top-right")
        toast.show("x", duration=0)

        async def run() -> None:
            await asyncio.sleep(0.1)
            assert len(toast._cards) == 1

        asyncio.run(run())

    def test_max_toasts_evicts_oldest(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="top-right", max_toasts=2)

        async def run() -> None:
            toast.show("A")
            toast.show("B")
            toast.show("C")
            await asyncio.sleep(0.4)  # let the eviction exit play out
            # A was furthest from the top edge — evicted.
            labels = []
            for c in toast._cards:
                span = c.el.container[1]
                assert isinstance(span, DOMElement)
                labels.append(str(span.container[0]))
            assert sorted(labels) == ["B", "C"]

        asyncio.run(run())

    def test_clear_removes_all(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="top-right")

        async def run() -> None:
            toast.show("a", duration=10)
            toast.show("b", duration=10)
            assert len(toast._cards) == 2
            toast.clear()
            assert len(toast._cards) == 0
            assert len(toast._root.container) == 0

        asyncio.run(run())


class TestToastEvents:
    """✕ button dismisses a single card."""

    def test_close_button_dismisses(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="top-right")
        toast.show("x")
        record = toast._cards[0]
        close = record.close

        async def run() -> None:
            await close._handlers["click"][0](DomEvent(key=close.key, type="click"))
            assert len(toast._cards) == 0

        asyncio.run(run())

    def test_exit_reverses_enter_keyframe(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast(placement="bottom-left")
        toast.show("x")
        record = toast._cards[0]

        async def run() -> None:
            task = asyncio.create_task(record.close._handlers["click"][0](DomEvent(key=record.close.key, type="click")))
            await asyncio.sleep(0)
            exit_anim = record.el.styles.animation
            assert isinstance(exit_anim, Animation)
            assert exit_anim.name == "neony-toast-in-bl"
            assert exit_anim.direction == "reverse"
            assert exit_anim.fill_mode == "forwards"
            await task

        asyncio.run(run())

    def test_card_click_fires_on_click(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast()
        fired: list[str] = []
        toast.show("x", on_click=lambda: fired.append("clicked"))
        card = toast._cards[0].el
        asyncio.run(card._handlers["click"][0](DomEvent(key=card.key, type="click")))
        assert fired == ["clicked"]

    def test_inner_label_click_bubbles_to_card(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast()
        fired: list[str] = []
        toast.show("hello", on_click=lambda: fired.append("clicked"))
        label = toast._cards[0].el.container[1]
        assert isinstance(label, DOMElement)
        # clicking the label routes through the card's bubbled handler
        card_handler = toast._cards[0].el._handlers["click"][0]
        asyncio.run(card_handler(DomEvent(key=label.key, type="click")))
        assert fired == ["clicked"]

    def test_close_never_fires_card_click(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast()
        fired: list[str] = []
        toast.show("x", on_click=lambda: fired.append("clicked"))
        record = toast._cards[0]
        asyncio.run(record.close._handlers["click"][0](DomEvent(key=record.close.key, type="click")))
        assert fired == []

    def test_async_on_click_is_awaited(self):
        import asyncio

        from neony.application.elements import Toast

        toast = Toast()
        fired: list[str] = []

        async def cb() -> None:
            await asyncio.sleep(0)
            fired.append("ok")

        toast.show("x", on_click=cb)
        card = toast._cards[0].el
        asyncio.run(card._handlers["click"][0](DomEvent(key=card.key, type="click")))
        assert fired == ["ok"]

    def test_clickable_card_shows_pointer_cursor(self):
        from neony.application.elements import Toast

        clickable = Toast()
        clickable.show("x", on_click=lambda: None)
        assert clickable._cards[0].el.styles.cursor == "pointer"

        plain = Toast()
        plain.show("x")
        assert plain._cards[0].el.styles.cursor is None


class TestToastParentChain:
    """Cards must keep _parent links so dirty changes propagate."""

    def test_card_parent_is_root(self):
        from neony.application.elements import Toast

        toast = Toast()
        toast.show("x")
        assert toast._cards[0].el._parent is toast._root


class TestMessageBubbleBuild:
    """MessageBubble layout, styling, optional pieces."""

    def test_renders_text(self):
        b = MessageBubble("hello")
        assert _contains_text(b.build().to_node(), "hello")

    def test_from_me_style(self):
        from neony.application.theme import stub

        me = MessageBubble("hi", from_me=True)
        assert me._root.styles.justify_content == "flex-end"
        assert me._col.styles.align_items == "flex-end"
        assert me._bubble.styles.background_color == stub.accent
        assert me._bubble.styles.color == Color(name="white")
        assert me._bubble.styles.border_radius == "16px 16px 4px 16px"

    def test_from_other_style(self):
        from neony.application.theme import stub

        other = MessageBubble("hi")
        assert other._root.styles.justify_content == "flex-start"
        assert other._col.styles.align_items == "flex-start"
        assert other._bubble.styles.background_color == stub.surface_raised
        assert other._bubble.styles.color == stub.text_primary
        assert other._bubble.styles.border_radius == "16px 16px 16px 4px"

    def test_avatar_side(self):
        av = Avatar(name="A")
        other = MessageBubble("hi", avatar=av)
        assert other._root.container[0] is other._avatar_el  # avatar leads
        assert other._root.container[1] is other._col

        me = MessageBubble("hi", from_me=True, avatar=Avatar(name="A"))
        assert me._root.container[0] is me._col  # avatar trails
        assert me._root.container[1] is me._avatar_el

    def test_no_avatar_single_column(self):
        b = MessageBubble("hi")
        assert b._avatar_el is None
        assert b._root.container[0] is b._col

    def test_name_label_optional(self):
        b = MessageBubble("hi", name="Ada")
        assert b._name_span.styles.display != "none"
        assert b._name_span.container[0] == "Ada"

        anonymous = MessageBubble("hi")
        assert anonymous._name_span.styles.display == "none"

    def test_actions_hidden_by_default(self):
        b = MessageBubble("hi", actions=[("reply", "Reply")])
        assert b._actions.styles.display == "none"
        assert len(b._actions.container) == 1

    def test_actions_are_out_of_flow(self):
        """Quick actions must not change the bubble's footprint when they
        appear — they anchor absolutely to the column below the bubble."""
        b = MessageBubble("hi", actions=[("reply", "Reply")])
        assert b._col.styles.position == "relative"
        assert b._actions.styles.position == "absolute"
        assert b._actions.styles.top == "calc(100% + 2px)"
        # right-aligned (from_me) anchors to the right edge; others to left
        me = MessageBubble("hi", from_me=True, actions=[("a", "A")])
        assert me._actions.styles.right == "0"
        assert me._actions.styles.left is None
        other = MessageBubble("hi", actions=[("a", "A")])
        assert other._actions.styles.left == "0"
        assert other._actions.styles.right is None

    def test_icon_action_value_is_glyph(self):
        b = MessageBubble("hi", actions=[Icon.glyph("😊")])
        btn = b._actions.container[0]
        assert isinstance(btn, DOMElement)
        assert b._action_by_key[btn.key] == "😊"

    def test_content_and_set_content_public_access(self):
        old_content = Div(key="old", container=["old"])
        bubble = MessageBubble(content=old_content)
        assert bubble.content is old_content

        new_content = Div(key="new", container=["new"])
        bubble.set_content(new_content)
        assert bubble.content is new_content
        assert new_content._parent is bubble._bubble
        assert old_content._parent is None

    def test_action_public_layout_api(self):
        bubble = MessageBubble(
            "hi",
            from_me=True,
            white_space="pre-wrap",
            actions_placement="beside",
            action_size="28px",
            actions=[Icon.glyph("😊")],
        )
        button = bubble.action_elements()[0]
        assert bubble._actions.styles.top == "50%"
        assert bubble._actions.styles.right == "calc(100% + 6px)"
        assert bubble._actions.styles.transform == "translateY(-50%)"
        assert bubble._bubble.styles.white_space == "pre-wrap"
        assert button.styles.width == "28px"
        assert button.styles.height == "28px"
        assert button.styles.padding == "0"
        assert bubble.action_values() == ("😊",)
        icon = button.container[0]
        assert isinstance(icon, DOMElement)
        assert icon.styles.pointer_events == "none"

    def test_name_badge_survives_name_updates(self):
        badge = Badge("OP", variant="accent")
        bubble = MessageBubble("hi", name="Ada", name_badge=badge)
        badge_el = bubble._name_span.container[1]
        assert isinstance(bubble._name_span.container[0], DOMElement)
        assert bubble._name_span.container[0].container == ["Ada"]
        assert bubble._name_span.container == [bubble._name_span.container[0], badge_el]
        assert bubble._name_span.styles.gap == "4px"

        bubble.name = "Grace"
        assert bubble._name_span.container == [bubble._name_span.container[0], badge_el]
        assert bubble._name_span.container[0].container == ["Grace"]

    def test_name_badge_has_element_only_reactive_children(self):
        bubble = MessageBubble("hi", name="Ada", name_badge=Badge("OP"))
        node = bubble.build().to_node()
        name_node = next(item for item in _walk(node) if item.key == bubble._name_span.key)
        assert all(isinstance(child, str) is False for child in name_node.children)

    def test_actions_visibility_and_overlay_slot(self):
        bubble = MessageBubble("hi", actions=[("reply", "Reply")])
        overlay = Div(key="overlay")
        bubble.overlay_slot.container.append(overlay)

        assert not bubble.actions_visible
        bubble.show_actions()
        assert bubble.actions_visible
        bubble.hide_actions()
        assert not bubble.actions_visible
        assert overlay._parent is bubble.overlay_slot


class TestMessageBubbleEvents:
    """Context menu, hover reveal, action clicks."""

    def test_contextmenu_opens_menu_at_cursor(self):
        import asyncio

        b = MessageBubble("hi")
        asyncio.run(b._root._handlers["contextmenu"][0](DomEvent(key=b._root.key, type="contextmenu", x=100, y=50)))
        assert b._menu is not None
        assert b._menu._open is True
        assert b._menu._root.styles.left == "100px"

    def test_menu_selection_forwards_change(self):
        import asyncio

        b = MessageBubble("hi")
        assert b._menu is not None
        fired: list[str] = []
        b.on_change(lambda e: fired.append(e.value))
        copy_row = b._menu._rows[0][1]  # ("copy", button)

        async def run() -> None:
            await copy_row._handlers["click"][0](DomEvent(key=copy_row.key, type="click"))
            assert not b._menu._open  # selection closes the menu
            assert fired == ["copy"]

        asyncio.run(run())

    def test_hover_shows_and_hides_actions_after_grace_delay(self):
        import asyncio

        b = MessageBubble("hi", actions=[("reply", "Reply")])

        async def run() -> None:
            # real enter (related key outside) reveals the actions
            await b._root._handlers["mouseover"][0](DomEvent(key=b._root.key, type="mouseover", related_key=None))
            assert b._actions.styles.display == "flex"
            # moving onto the actions row is an inner hop — stays visible
            await b._root._handlers["mouseover"][0](
                DomEvent(key=b._actions.key, type="mouseover", related_key=b._actions.key)
            )
            assert b._actions.styles.display == "flex"
            # A real leave preserves the row briefly so the pointer can cross
            # the absolute-positioning gap before it reaches a button.
            await b._root._handlers["mouseout"][0](DomEvent(key=b._root.key, type="mouseout", related_key=None))
            assert b._actions.styles.display == "flex"
            await asyncio.sleep(0.2)
            assert b._actions.styles.display == "none"

        asyncio.run(run())

    def test_reentering_actions_during_grace_delay_cancels_hide(self):
        import asyncio

        b = MessageBubble("hi", actions=[("reply", "Reply")])

        async def run() -> None:
            await b._root._handlers["mouseover"][0](DomEvent(key=b._root.key, type="mouseover"))
            await b._root._handlers["mouseout"][0](DomEvent(key=b._root.key, type="mouseout"))
            await asyncio.sleep(0.05)
            await b._root._handlers["mouseover"][0](DomEvent(key=b._actions.key, type="mouseover"))
            await asyncio.sleep(0.2)

        asyncio.run(run())
        assert b._actions.styles.display == "flex"

    def test_hover_actions_are_exclusive_across_bubbles(self):
        import asyncio

        first = MessageBubble("first", actions=[("reply", "Reply")])
        second = MessageBubble("second", actions=[("reply", "Reply")])
        Div(container=[first._root, second._root])

        async def run() -> None:
            await first._root._handlers["mouseover"][0](DomEvent(key=first._root.key, type="mouseover"))
            await second._root._handlers["mouseover"][0](DomEvent(key=second._root.key, type="mouseover"))
            # A delayed leave from the first bubble cannot clear the newer owner.
            await first._root._handlers["mouseout"][0](DomEvent(key=first._root.key, type="mouseout"))

        asyncio.run(run())
        assert first._actions.styles.display == "none"
        assert second._actions.styles.display == "flex"

    def test_action_click_dispatches(self):
        import asyncio

        b = MessageBubble("hi", actions=[("reply", "Reply")])
        fired: list[str] = []
        b.on_action(lambda v: fired.append(v))
        btn = b._actions.container[0]
        assert isinstance(btn, DOMElement)

        async def run() -> None:
            await btn._handlers["click"][0](DomEvent(key=btn.key, type="click"))
            assert fired == ["reply"]

        asyncio.run(run())

    def test_menu_disabled_still_fires_contextmenu(self):
        import asyncio

        b = MessageBubble("hi", menu_items=[])
        assert b._menu is None
        fired: list[float] = []
        b.on_contextmenu(lambda e: fired.append(e.x))
        asyncio.run(b._root._handlers["contextmenu"][0](DomEvent(key=b._root.key, type="contextmenu", x=5, y=6)))
        assert fired == [5.0]

    def test_bubble_does_not_double_wire_click(self):
        """on_click must not wire the root a second time (declared bound)."""
        b = MessageBubble("hi", actions=[("a", "A")])
        btn = b._actions.container[0]
        assert isinstance(btn, DOMElement)
        b.on_click(lambda _e: None)
        # the action button keeps exactly its own dispatcher
        assert len(btn._handlers.get("click", [])) == 1


class TestMessageBubbleParentChain:
    """Row children keep _parent links so dirty changes propagate."""

    def test_action_parent_is_actions_row(self):
        b = MessageBubble("hi", actions=[("reply", "Reply")])
        btn = b._actions.container[0]
        assert isinstance(btn, DOMElement)
        assert btn._parent is b._actions

    def test_col_children_parent(self):
        b = MessageBubble("hi", name="Ada")
        assert b._bubble._parent is b._col
        assert b._actions._parent is b._col
        assert b._col._parent is b._root

    def test_menu_root_mounted_in_row(self):
        b = MessageBubble("hi")
        assert b._menu is not None
        assert b._menu._root._parent is b._root


class TestNoticeBubbleBuild:
    """NoticeBubble — the centered system message."""

    def test_centered_and_text(self):
        n = NoticeBubble("You joined the group")
        assert n._root.styles.align_self == "center"
        assert n._root.styles.display == "inline-flex"
        assert n._root.container[0] == "You joined the group"

    def test_text_setter(self):
        n = NoticeBubble("old")
        n.text = "new"
        assert n._root.container[0] == "new"

    def test_content_passthrough(self):
        n = NoticeBubble(content=Div(key="custom", container=["x"]))
        el = n._root.container[0]
        assert isinstance(el, DOMElement)
        assert el.key == "custom"
