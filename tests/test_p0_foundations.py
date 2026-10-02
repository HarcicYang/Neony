"""P0 shared contracts: rich choices, focus scope metadata, validation."""

import asyncio
from typing import Any, cast

import pytest

from neony.application.elements import (
    ChoiceItem,
    ComboBox,
    Dialog,
    Dropdown,
    FormField,
    Icon,
    Input,
    Menu,
    MenuSeparator,
    Select,
    Text,
)
from neony.application.layers import Layer, layer_manager
from neony.dom import Div, DOMElement, DomEvent


class TestChoiceItem:
    def test_defaults_and_legacy_forms_share_one_model(self):
        item = ChoiceItem("save")
        assert item.value == "save"
        assert item.label == "save"
        assert item.checked is None

        menu = Menu("copy", ("delete", "Delete"), ChoiceItem("pin", "Pin", checked=True))
        assert [row[0] for row in menu._rows] == ["copy", "delete", "pin"]
        pin = menu._choice_by_index[2]
        assert isinstance(pin, ChoiceItem)
        assert pin.checked is True

    def test_rich_menu_rows_render_metadata_and_separator(self):
        menu = Menu(
            ChoiceItem("copy", "Copy", icon=Icon.glyph("C"), shortcut="Ctrl+C", checked=True),
            MenuSeparator(),
            ChoiceItem("delete", "Delete", danger=True, disabled=True),
        )

        copy_row = menu._rows[0][1]
        assert len(copy_row.container) == 4  # check, icon, label, shortcut
        check = copy_row.container[0]
        shortcut = copy_row.container[3]
        assert isinstance(check, DOMElement)
        assert check.key != cast(Any, copy_row.container[1]).key
        assert isinstance(shortcut, DOMElement)
        assert shortcut.container == ["Ctrl+C"]
        assert menu._rows[1][1].args["role"] == "separator"
        assert cast(Any, menu._rows[2][1]).disabled is True
        assert menu._selectable == [0]

    def test_disabled_choice_is_not_keyboard_selected_or_clicked(self):
        fired: list[str] = []
        menu = Menu(
            ChoiceItem("disabled", "Disabled", disabled=True),
            ChoiceItem("enabled", "Enabled"),
        )
        menu.on_change(lambda event: fired.append(event.value))

        menu._move_active(1)
        assert menu._active_index == 1

        disabled_row = menu._rows[0][1]
        asyncio.run(menu._on_event("click", DomEvent(key=disabled_row.key, type="click")))
        assert fired == []

        asyncio.run(menu._select_active(DomEvent(key="", type="keydown", value="Enter")))
        assert fired == ["enabled"]

    def test_dropdown_select_and_combobox_accept_choice_items(self):
        choice = ChoiceItem("m", "Medium")
        dropdown = Dropdown("Size", items=[ChoiceItem("s", "Small", disabled=True), choice])
        dropdown.value = "m"
        assert dropdown.value == "m"
        labels = [cast(Any, row).container[0].container for row in dropdown._popup.container]
        assert ["Small"] in labels

        select = Select("Size", options=[ChoiceItem("s", "Small", disabled=True), choice])
        select._open_popup()
        select._move_active(1)
        asyncio.run(select._select_active(DomEvent(key="", type="keydown", value="Enter")))
        assert select.value == "m"

        combo = ComboBox(options=[ChoiceItem("m", "Medium")], value="m")
        assert combo.value == "m"
        assert combo._input.value == "Medium"


class TestFocusContract:
    def test_trap_scope_exposes_initial_focus_and_cleans_up(self):
        scope = Div(key="focus-scope")
        target = Div(key="focus-target")
        manager = layer_manager(scope)
        handle = manager.open(
            scope,
            kind=Layer.MODAL,
            group="modal",
            focus_scope="trap",
            initial_focus=target,
        )

        assert handle.focus_scope == "trap"
        assert handle.initial_focus_key == "focus-target"
        assert scope.args["data-neony-focus-scope"] == "trap"
        assert scope.args["data-neony-initial-focus"] == "focus-target"

        manager.close(handle)
        assert "data-neony-focus-scope" not in scope.args
        assert "data-neony-initial-focus" not in scope.args

    def test_invalid_focus_scope_is_rejected(self):
        scope = Div(key="bad-scope")
        with pytest.raises(ValueError):
            layer_manager(scope).open(scope, kind=Layer.MODAL, group="modal", focus_scope="wrong")  # type: ignore[arg-type]

    def test_trap_scope_schedules_initial_focus_script(self):
        scope = Div()
        panel = Div()
        scope.container.append(panel)
        scripts: list[str] = []

        async def eval_js(script: str) -> None:
            scripts.append(script)

        scope._eval_js_request = eval_js

        async def exercise() -> None:
            layer_manager(scope).open(
                panel,
                kind=Layer.MODAL,
                group="modal",
                focus_scope="trap",
                initial_focus=panel,
            )
            await asyncio.sleep(0)

        asyncio.run(exercise())
        assert "__neonyFocusInitial" in scripts[-1]
        assert panel.key in scripts[-1]

    def test_dialog_uses_modal_focus_contract(self):
        dialog = Dialog(content=Text("Body"), initial_focus=Text("Focus me"))
        assert dialog._root.args["role"] == "dialog"
        assert dialog._root.args["aria-modal"] == "true"
        assert dialog._root.args["aria-labelledby"]
        assert dialog.initial_focus is not None


class TestFormFieldValidation:
    def test_required_validation_updates_error_and_aria(self):
        field = FormField("Email", Input())
        assert field.validate() is True

        field.required = True
        assert field.validate() is False
        assert field.error == "Required"
        assert field.invalid is True
        assert field.control.args["aria-invalid"] == "true"

    def test_validator_receives_control_value_and_can_pass_or_fail(self):
        control = Input(value="ada@example.com")
        field = FormField(
            "Email",
            control,
            validator=lambda value: None if "@" in value else "Invalid email",
        )
        assert field.validate() is True

        control.value = "invalid"
        assert field.validate() is False
        assert field.error == "Invalid email"
        assert field.invalid is True

    def test_explicit_value_supports_plain_dom_controls(self):
        field = FormField("Code", Div(), validator=lambda value: "Bad" if value != "ok" else None)
        assert field.validate("no") is False
        assert field.validate("ok") is True
        assert field.error is None
        assert field.invalid is False
