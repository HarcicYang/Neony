"""Global floating-layer management contracts."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from neony.application.elements import Dialog, Dropdown, Menu, VStack
from neony.application.layers import Layer, LocalLayer, layer_manager, layers_css
from neony.dom import Div, DomEvent


def test_layer_bands_have_stable_order() -> None:
    assert (
        Layer.BACKGROUND
        < Layer.BACKGROUND_TINT
        < Layer.TOOLTIP
        < Layer.POPOVER
        < Layer.MENU
        < Layer.MODAL
        < Layer.TOAST
        < Layer.DRAG_GHOST
    )


def test_managers_are_isolated_per_mounted_tree() -> None:
    first_scope = Div()
    second_scope = Div()
    first = Div()
    second = Div()
    first_scope.container.append(first)
    second_scope.container.append(second)

    first_handle = layer_manager(first).open(first, kind=Layer.POPOVER, group="popup")
    second_handle = layer_manager(second).open(second, kind=Layer.POPOVER, group="popup")

    assert first_handle.z_index == Layer.POPOVER
    assert second_handle.z_index == Layer.POPOVER


def test_exclusive_group_closes_previous_through_callback() -> None:
    scope = Div()
    first = Div()
    second = Div()
    scope.container.extend([first, second])
    closed: list[str] = []

    manager = layer_manager(first)
    first_handle = manager.open(
        first,
        kind=Layer.POPOVER,
        group="popup",
        exclusive=True,
        on_close=lambda: closed.append("first"),
    )
    second_handle = manager.open(
        second,
        kind=Layer.POPOVER,
        group="popup",
        exclusive=True,
    )

    assert closed == ["first"]
    assert not first_handle.active
    assert first_handle.element.styles.z_index is None
    assert second_handle.active
    assert second.styles.z_index == Layer.POPOVER


def test_same_element_reopen_brings_its_existing_handle_to_front() -> None:
    scope = Div()
    first = Div()
    second = Div()
    scope.container.extend([first, second])
    manager = layer_manager(first)

    first_handle = manager.open(first, kind=Layer.POPOVER, group="popup")
    second_handle = manager.open(second, kind=Layer.POPOVER, group="popup")
    assert second_handle.z_index > first_handle.z_index

    reopened = manager.open(first, kind=Layer.POPOVER, group="popup")
    assert reopened is first_handle
    assert reopened.z_index > second_handle.z_index


def test_modal_closes_lower_transient_layers() -> None:
    scope = Div()
    popup = Div()
    modal = Div()
    scope.container.extend([popup, modal])
    closed: list[str] = []

    manager = layer_manager(popup)
    popup_handle = manager.open(
        popup,
        kind=Layer.POPOVER,
        group="popup",
        on_close=lambda: closed.append("popup"),
    )
    manager.open(modal, kind=Layer.MODAL, group="modal")

    assert closed == ["popup"]
    assert not popup_handle.active
    assert popup.styles.z_index is None
    assert modal.styles.z_index == Layer.MODAL


def test_topmost_can_filter_by_group() -> None:
    scope = Div()
    popup = Div()
    menu = Div()
    scope.container.extend([popup, menu])
    manager = layer_manager(popup)

    popup_handle = manager.open(popup, kind=Layer.POPOVER, group="popup")
    menu_handle = manager.open(menu, kind=Layer.MENU, group="menu")

    assert manager.topmost() is menu_handle
    assert manager.topmost("popup") is popup_handle
    assert manager.topmost("missing") is None


def test_popup_inside_modal_is_topmost_despite_a_lower_z_index() -> None:
    scope = Div()
    modal = Div()
    popup = Div()
    modal.container.append(popup)
    scope.container.append(modal)
    manager = layer_manager(popup)

    modal_handle = manager.open(modal, kind=Layer.MODAL, group="modal")
    popup_handle = manager.open(popup, kind=Layer.POPOVER, group="popup")

    assert popup_handle.z_index < modal_handle.z_index
    assert popup_handle.stack_order > modal_handle.stack_order
    assert manager.topmost() is popup_handle
    assert popup.args["data-neony-layer-order"] == str(popup_handle.stack_order)
    assert popup.args["data-neony-layer-z"] == str(popup_handle.z_index)


def test_close_clears_managed_styles_and_attributes() -> None:
    scope = Div()
    panel = Div()
    scope.container.append(panel)
    handle = layer_manager(panel).open(panel, kind=Layer.POPOVER, group="popup")

    handle.close()

    assert panel.styles.z_index is None
    assert "data-neony-layer" not in panel.args
    assert "data-neony-layer-order" not in panel.args
    assert "data-neony-layer-z" not in panel.args
    assert "data-neony-layer-open" not in panel.args


def test_dialog_containing_dropdown_routes_outsideclick_to_the_dropdown() -> None:
    dropdown = Dropdown(items=["one", "two"])
    dialog = Dialog(content=VStack(dropdown), open=True)
    dropdown._open_popup()

    manager = layer_manager(dropdown._wrapper)
    top = manager.topmost()
    assert top is dropdown._layer_handle
    assert top is not None
    assert top.group == "popup"
    assert top.stack_order > int(dialog._root.args["data-neony-layer-order"])
    popup_z = dropdown._wrapper.styles.z_index
    modal_z = dialog._root.styles.z_index
    assert popup_z is not None
    assert modal_z is not None
    assert popup_z < modal_z

    asyncio.run(
        dropdown._wrapper._handlers["outsideclick"][0](DomEvent(key=dropdown._wrapper.key, type="outsideclick"))
    )
    assert not dropdown._open
    assert dialog.open


def test_owner_aware_menu_follows_modal_layer_and_closes_with_it() -> None:
    dialog = Dialog(content=Div())
    menu = Menu("action")
    Div(container=[dialog._root, menu._root])
    dialog.open = True
    menu.open_at(10, 10, owner=dialog)

    assert menu._open
    assert menu._root.styles.z_index is not None
    assert dialog._root.styles.z_index is not None
    assert menu._root.styles.z_index > dialog._root.styles.z_index

    dialog.open = False
    assert not menu._open


def test_layers_css_exposes_js_runtime_values() -> None:
    css = layers_css()

    assert f"--neony-layer-toast: {int(Layer.TOAST)}" in css
    assert f"--neony-layer-local-indicator: {int(LocalLayer.INDICATOR)}" in css
    assert f"--neony-layer-drag-ghost: {int(Layer.DRAG_GHOST)}" in css


def test_components_do_not_embed_raw_z_index_values() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "neony" / "application" / "elements"
    failures: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "z_index":
                if not isinstance(node.value, (ast.Attribute, ast.Name)):
                    failures.append(f"{path.name}:{node.lineno}")
            elif isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "z_index"
                        and not isinstance(value, (ast.Attribute, ast.Name))
                    ):
                        failures.append(f"{path.name}:{node.lineno}")

    assert failures == []
