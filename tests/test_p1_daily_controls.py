"""P1 daily-control behavior: loading buttons and indeterminate checkboxes."""

import asyncio

from neony.application.elements import (
    Breadcrumb,
    Button,
    Checkbox,
    ChoiceItem,
    Icon,
    Input,
    Pagination,
    SegmentedControl,
    Step,
    Stepper,
    Text,
)
from neony.dom import Button as DomButton
from neony.dom import DOMElement, DomEvent


def test_button_loading_blocks_clicks_and_exposes_busy_state():
    fired: list[str] = []
    button = Button("Save", icon=Icon.glyph("S"), loading=True)
    button.on_click(lambda _event: fired.append("clicked"))

    assert button.loading is True
    assert button._btn.disabled is True
    assert button._btn.args["aria-busy"] == "true"
    assert button._spinner_span in button._btn.container

    asyncio.run(button._on_event("click", DomEvent(key=button._btn.key, type="click")))
    assert fired == []

    button.loading = False
    assert button._btn.disabled is False
    assert "aria-busy" not in button._btn.args
    assert button._icon_span in button._btn.container


def test_checkbox_indeterminate_uses_mixed_state_until_user_click():
    checkbox = Checkbox("Select all", indeterminate=True)

    assert checkbox.indeterminate is True
    assert checkbox._input.args["data-neony-indeterminate"] == "true"
    assert checkbox._input.args["aria-checked"] == "mixed"
    assert checkbox._input.styles.background_image is not None

    asyncio.run(checkbox._input._handlers["change"][0](DomEvent(key=checkbox._input.key, type="change", value=True)))
    assert checkbox.indeterminate is False
    assert checkbox.checked is True
    assert "data-neony-indeterminate" not in checkbox._input.args
    assert "aria-checked" not in checkbox._input.args


def test_input_adornments_clear_and_submit():
    submitted: list[tuple[str, str]] = []
    input_field = Input(
        value="hello",
        prefix=Icon.glyph("@"),
        suffix=".com",
        clearable=True,
    )
    input_field.on_submit(lambda event: submitted.append((event.value, event.source)))

    assert input_field._root.to_node().tag == "div"
    assert input_field._root.container[0] is input_field._prefix_slot
    assert input_field._root.container[-1] is input_field._suffix_slot
    assert input_field._clear_button is not None
    assert input_field._clear_button.styles.display == "inline-flex"

    asyncio.run(
        input_field._clear_button._handlers["click"][0](DomEvent(key=input_field._clear_button.key, type="click"))
    )
    assert input_field.value == ""
    assert input_field._input.value == ""
    assert input_field._clear_button.styles.display == "none"

    asyncio.run(
        input_field._input._handlers["keydown"][0](DomEvent(key=input_field._input.key, type="keydown", value="Enter"))
    )
    assert submitted == [("", "user")]

    asyncio.run(
        input_field._input._handlers["keydown"][0](
            DomEvent(key=input_field._input.key, type="keydown", value="Enter", is_composing=True)
        )
    )
    assert len(submitted) == 1


def test_password_input_reveal_toggle_preserves_value():
    input_field = Input(value="secret", type="password", reveal_password=True)
    assert input_field._reveal_button is not None
    assert input_field._input.type == "password"

    asyncio.run(
        input_field._reveal_button._handlers["click"][0](DomEvent(key=input_field._reveal_button.key, type="click"))
    )
    assert input_field._input.type == "text"
    assert input_field.value == "secret"
    assert input_field._reveal_button.args["aria-label"] == "Hide password"


def test_segmented_control_selects_and_skips_disabled_segments():
    changed: list[str] = []
    control = SegmentedControl(
        ChoiceItem("list", "List"),
        ChoiceItem("grid", "Grid"),
        ChoiceItem("board", "Board", disabled=True),
        value="list",
    )
    control.on_change(lambda event: changed.append(event.value))

    asyncio.run(control._on_keydown(DomEvent(key=control._root.key, type="keydown", value="ArrowRight")))
    assert control.value == "grid"
    assert changed == ["grid"]

    asyncio.run(control._on_keydown(DomEvent(key=control._root.key, type="keydown", value="ArrowRight")))
    assert control.value == "list"
    assert changed == ["grid", "list"]


def test_breadcrumb_marks_last_item_current_and_dispatches_ancestors():
    changed: list[str] = []
    crumbs = Breadcrumb("Workspace", ("project", "Neony"), "Settings")
    crumbs.on_change(lambda event: changed.append(event.value))

    assert crumbs._root.args["aria-label"] == "Breadcrumb"
    current = crumbs._root.container[-1]
    assert isinstance(current, DOMElement)
    assert current.args["aria-current"] == "page"

    asyncio.run(crumbs._rows[1]._handlers["click"][0](DomEvent(key=crumbs._rows[1].key, type="click")))
    assert changed == ["project"]


def test_pagination_clamps_compresses_and_dispatches_pages():
    changed: list[int] = []
    pager = Pagination(value=5, page_count=20, siblings=1, boundary=1)
    pager.on_change(lambda event: changed.append(event.value))

    rendered = pager._pages()
    assert rendered[0] == 1
    assert rendered[-1] == 20
    assert None in rendered

    next_button = next(
        row for row in pager._root.container if isinstance(row, DomButton) and row.args.get("aria-label") == "Next page"
    )
    asyncio.run(next_button._handlers["click"][0](DomEvent(key=next_button.key, type="click")))
    assert pager.value == 6
    assert changed == [6]

    pager.value = 999
    assert pager.value == 20


def test_stepper_switches_persistent_panels_and_enforces_linear_flow():
    changed: list[str] = []
    stepper = Stepper(
        Step("Account", Text("Account body"), key="account"),
        Step("Plan", Text("Plan body"), key="plan"),
        Step("Review", Text("Review body"), key="review"),
        linear=True,
    )
    stepper.on_change(lambda event: changed.append(event.value))

    assert stepper.selected_key == "account"
    assert stepper._host._active == 0

    asyncio.run(stepper._rows[2]._handlers["click"][0](DomEvent(key=stepper._rows[2].key, type="click")))
    assert stepper.selected_key == "account"
    assert changed == []

    assert stepper.next() is True
    assert stepper.selected_key == "plan"
    assert stepper._host._active == 1

    asyncio.run(stepper._rows[2]._handlers["click"][0](DomEvent(key=stepper._rows[2].key, type="click")))
    assert stepper.selected_key == "review"
    assert changed == ["review"]
