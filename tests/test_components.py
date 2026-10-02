"""Behavior contracts for the component library.

Keep this suite focused on state transitions, event semantics, selection,
keyboard interaction, and regressions. Static DOM/style snapshots belong in
component-level contract tests only when they protect a browser-facing protocol.
"""

from typing import Any

import pytest

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
    SidebarItem,
    Slider,
    Switch,
    Tabs,
    Text,
    Toast,
    Tooltip,
    Tree,
    TreeNode,
)
from neony.application.layers import Layer
from neony.dom import Animation, Div, DOMElement, DomEvent, NodeDescriptor


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
        node = inp._input.to_node()
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

    def test_drop_on_itself_is_noop(self):
        import asyncio

        board = Reorder("a", "b", "c")
        board.build()
        cards = {card.key: card for card in board._cards}
        asyncio.run(cards["b"]._handlers["drop"][0](DomEvent(key="b", type="drop", drag_payload="b", offset_x=0)))
        assert board.order == ["a", "b", "c"]

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

    def test_programmatic_value_set_fires_nothing(self):
        group = RadioGroup(Radio("A", value="a"), Radio("B", value="b"))
        fired: list = []
        group.on_change(lambda e: fired.append(e.value))
        group.value = "b"
        assert fired == []
        assert group.items[0].checked is False
        assert group.items[1].checked is True


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
        assert [getattr(row.container[0], "container", None) for row in cb._rows] == [["work"]]

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

    def test_opening_sibling_dropdown_closes_previous_and_raises_active_layer(self):
        from neony.dom import Div

        first = Dropdown(items=["a"])
        second = Dropdown("second", items=["b"])
        Div(container=[first._root, second._root])

        self._click_trigger(first)
        assert first._open
        assert first._wrapper.styles.z_index == Layer.POPOVER
        assert first._wrapper.args["data-neony-layer"] == "popover"

        self._click_trigger(second)
        assert not first._open
        assert first._wrapper.styles.z_index is None
        assert second._open
        assert second._wrapper.styles.z_index == Layer.POPOVER

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

    def test_outsideclick_closes(self):
        import asyncio

        dd = Dropdown(items=["a"])
        self._click_trigger(dd)
        asyncio.run(dd._wrapper._handlers["outsideclick"][0](DomEvent(key=dd._wrapper.key, type="outsideclick")))
        assert dd._open is False


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
        assert picker._popup.styles.z_index is None
        assert picker._popup.styles.overflow == "visible"
        assert len(picker._branches) == 1
        picker._open_popup()
        assert picker._click_away.styles.display == "block"

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
        assert second._wrapper.styles.z_index == Layer.POPOVER

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

    def test_selected_title_unknown_raises(self):
        tabs = Tabs(("One", Text("p1")))
        with pytest.raises(ValueError):
            tabs.selected_title = "Nope"

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


class TestSidebarSelection:
    """Object-level selection + key selection on Sidebar."""

    def test_selected_object_binding(self):
        p2 = Pane("Settings", panel=Text("s"), key="settings")
        sidebar = Sidebar(Pane("Home", panel=Text("h")), p2)
        sidebar.selected = p2
        assert sidebar.selected_key == "settings"

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


class TestTreeSelection:
    """Single-select leaf semantics mirroring Sidebar."""

    def test_active_key_at_construction(self):
        tree = Tree(TreeNode("Home", key="home").panel(Text("h")), active_key="home")
        assert tree.selected_key == "home"

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


class TestListSelection:
    """Single-select list semantics mirroring Sidebar / Tree."""

    def test_active_key_at_construction(self):
        lst = List("a", "b", active_key="b")
        assert lst.selected_key == "b"
        node = lst.build().to_node()
        rows = [c for c in node.children if c.attrs.get("role") == "option"]
        assert [r.attrs.get("aria-selected") for r in rows] == ["false", "true"]

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


class TestDataTableSort:
    """Header sorting — numeric-aware, sort_key override, glyph state."""

    def test_numeric_sort(self):
        dt = DataTable(columns=[Column("Age", sortable=True)], rows=[{"age": 30}, {"age": 9}, {"age": 100}])
        dt.sort_by = ("age", "asc")
        assert [r["age"] for r in dt._display] == [9, 30, 100]
        dt.sort_by = ("age", "desc")
        assert [r["age"] for r in dt._display] == [100, 30, 9]

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


class TestDataTableVirtualization:
    """Large tables mount a bounded row window without changing the model."""

    def test_auto_materializes_bounded_window(self):
        rows = [{"name": f"row-{i}", "value": i} for i in range(1000)]
        table = DataTable(
            columns=[Column("Name"), Column("Value")],
            rows=rows,
            row_key=lambda row: row["name"],
        )

        assert table.virtualize == "auto"
        assert table._virtualized is True
        assert len(table.rows) == 1000
        assert len(table._row_by_key) <= 26
        assert len(table._body.container) == len(table._row_by_key) + 2
        hidden = len(table._row_keys) - table._virtual_end
        assert table._bottom_spacer.styles.height == f"{hidden * table._row_height:g}px"

    def test_small_table_keeps_full_dom(self):
        rows = [{"name": f"row-{i}"} for i in range(200)]
        table = DataTable(columns=[Column("Name")], rows=rows)

        assert table._virtualized is False
        assert len(table._row_by_key) == 200
        assert len(table._body.container) == 200

    def test_scroll_replaces_window(self):
        rows = [{"name": f"row-{i}"} for i in range(1000)]
        table = DataTable(columns=[Column("Name")], rows=rows, row_key=lambda row: row["name"])
        first_rows = set(table._row_by_key)

        target = 500
        table._handle_scroll(
            DomEvent(
                key=table._root.key,
                type="scroll",
                scroll_top=target * table._row_height,
                client_height=500,
            )
        )

        assert table._virtual_start == target - table._overscan
        assert "row-500" in table._row_by_key
        assert not first_rows.intersection(table._row_by_key)

    def test_offscreen_selection_and_sort_survive(self):
        rows = [{"name": f"row-{i}", "value": i} for i in range(1000)]
        table = DataTable(
            columns=[Column("Name"), Column("Value", sortable=True)],
            rows=rows,
            row_key=lambda row: row["name"],
        )

        table.selected_key = "row-900"
        table.sort_by = ("value", "desc")

        assert table.selected_key == "row-900"
        assert "row-900" not in table._row_by_key
        table._ensure_materialized("row-900")
        assert "row-900" in table._row_by_key
        assert table._row_by_key["row-900"].args["aria-selected"] == "true"

    def test_keyboard_end_materializes_target(self):
        import asyncio

        rows = [{"name": f"row-{i}"} for i in range(1000)]
        table = DataTable(
            columns=[Column("Name")],
            rows=rows,
            row_key=lambda row: row["name"],
        )
        event = DomEvent(key="row:row-0", type="keydown", value="End")

        asyncio.run(table._make_keydown_handler("row-0")(event))

        assert table.selected_key == "row-999"
        assert "row-999" in table._row_by_key
        assert table._focus_key == "row-999"

    def test_reactive_cells_dispose_effects_when_scrolled_out(self):
        from neony.dom import Signal

        signals = [Signal(f"row-{i}") for i in range(250)]
        rows = [{"name": signal, "key": f"row-{i}"} for i, signal in enumerate(signals)]
        table = DataTable(
            columns=[Column("Name")],
            rows=rows,
            row_key=lambda row: row["key"],
        )
        assert signals[0]._subs

        table._handle_scroll(
            DomEvent(
                key=table._root.key,
                type="scroll",
                scroll_top=210 * table._row_height,
                client_height=500,
            )
        )

        assert signals[0]._subs == set()
        assert signals[210]._subs

    def test_invalid_configuration_raises(self):
        bad_virtualize: Any = "sometimes"
        with pytest.raises(ValueError):
            DataTable(virtualize=bad_virtualize)
        with pytest.raises(ValueError):
            DataTable(row_height=0)
        with pytest.raises(ValueError):
            DataTable(overscan=-1)


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


class TestToastState:
    """Auto-dismiss, eviction, clear."""

    def test_auto_dismiss_removes_after_duration(self):
        import asyncio

        toast = Toast(placement="top-right")

        async def run() -> None:
            toast.show("x", duration=0.02)
            assert len(toast._cards) == 1
            await asyncio.sleep(0.4)  # duration + exit animation
            assert len(toast._cards) == 0

        asyncio.run(run())

    def test_max_toasts_evicts_oldest(self):
        import asyncio

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

        toast = Toast(placement="top-right")
        toast.show("x")
        record = toast._cards[0]
        close = record.close

        async def run() -> None:
            await close._handlers["click"][0](DomEvent(key=close.key, type="click"))
            assert len(toast._cards) == 0

        asyncio.run(run())

    def test_card_click_fires_on_click(self):
        import asyncio

        toast = Toast()
        fired: list[str] = []
        toast.show("x", on_click=lambda: fired.append("clicked"))
        card = toast._cards[0].el
        asyncio.run(card._handlers["click"][0](DomEvent(key=card.key, type="click")))
        assert fired == ["clicked"]

    def test_close_never_fires_card_click(self):
        import asyncio

        toast = Toast()
        fired: list[str] = []
        toast.show("x", on_click=lambda: fired.append("clicked"))
        record = toast._cards[0]
        asyncio.run(record.close._handlers["click"][0](DomEvent(key=record.close.key, type="click")))
        assert fired == []

    def test_async_on_click_is_awaited(self):
        import asyncio

        toast = Toast()
        fired: list[str] = []

        async def cb() -> None:
            await asyncio.sleep(0)
            fired.append("ok")

        toast.show("x", on_click=cb)
        card = toast._cards[0].el
        asyncio.run(card._handlers["click"][0](DomEvent(key=card.key, type="click")))
        assert fired == ["ok"]


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
