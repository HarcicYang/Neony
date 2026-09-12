"""Global floating-layer management contracts."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from neony.application.elements import Dialog, Dropdown, Menu, Toast, VStack
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


def test_dialog_escape_closes_nested_popup_before_the_modal() -> None:
    dropdown = Dropdown(items=["one", "two"])
    dialog = Dialog(content=VStack(dropdown), open=True)
    dropdown._open_popup()

    event = DomEvent(key=dialog._root.key, type="keydown", value="Escape")
    asyncio.run(dialog._root._handlers["keydown"][0](event))

    assert not dropdown._open
    assert dialog.open

    asyncio.run(dialog._root._handlers["keydown"][0](event))

    assert not dialog.open


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


def test_dialog_popup_menu_and_toast_share_one_logical_stack() -> None:
    dialog = Dialog(content=Div())
    toast = Toast()
    menu = Menu("action")
    scope = Div(container=[dialog._root, toast._root, menu._root])
    dropdown = Dropdown(items=["one", "two"])
    dialog._panel.container.append(dropdown._wrapper)
    dialog.open = True
    dropdown._open_popup()
    menu.open_at(10, 10, owner=dialog)
    manager = layer_manager(dialog._root)
    manager.open(toast._root, kind=Layer.TOAST, group="toast")

    top = manager.topmost()
    assert scope.container
    assert top is not None
    assert top.kind == Layer.TOAST
    assert manager.handle_escape(dialog._root) is False
    assert manager.handle_escape() is True
    assert manager.handle_escape(dialog._root) is True
    assert not menu._open
    assert manager.handle_escape(dialog._root) is True
    assert not dropdown._open
    assert manager.handle_escape(dialog._root) is True
    assert not dialog.open


def test_escape_closes_only_the_topmost_layer_in_scope() -> None:
    scope = Div()
    modal = Div()
    popup = Div()
    scope.container.extend([modal, popup])
    closed: list[str] = []
    manager = layer_manager(modal)
    manager.open(modal, kind=Layer.MODAL, group="modal", on_close=lambda: closed.append("modal"))
    manager.open(
        popup,
        kind=Layer.POPOVER,
        group="popup",
        owner=modal,
        on_close=lambda: closed.append("popup"),
    )

    assert manager.handle_escape(modal) is True
    assert closed == ["popup"]
    assert manager.handle_escape(modal) is True
    assert closed == ["popup", "modal"]
    assert manager.handle_escape(modal) is False


def test_escape_does_not_close_an_unrelated_layer() -> None:
    scope = Div()
    first = Div()
    second = Div()
    scope.container.extend([first, second])
    closed: list[str] = []
    manager = layer_manager(first)
    manager.open(first, kind=Layer.MODAL, group="modal", on_close=lambda: closed.append("first"))
    manager.open(second, kind=Layer.TOAST, group="toast", on_close=lambda: closed.append("second"))

    assert manager.handle_escape(first) is False
    assert closed == []


def test_focus_is_captured_and_restored_around_layer_lifetime() -> None:
    scope = Div()
    panel = Div()
    scope.container.append(panel)
    scripts: list[str] = []

    async def eval_js(script: str) -> None:
        scripts.append(script)

    scope._eval_js_request = eval_js

    async def exercise() -> None:
        handle = layer_manager(scope).open(panel, kind=Layer.POPOVER, group="popup")
        await asyncio.sleep(0)
        handle.close()
        await asyncio.sleep(0)

    asyncio.run(exercise())

    assert len(scripts) == 2
    assert "__neonyLayerFocus" in scripts[0]
    assert panel.key in scripts[0]
    assert "__neonyLayerFocus" in scripts[1]
    assert "target.focus" in scripts[1]


def test_exclusive_replacement_does_not_restore_the_previous_trigger() -> None:
    scope = Div()
    first = Div()
    second = Div()
    scope.container.extend([first, second])
    scripts: list[str] = []

    async def eval_js(script: str) -> None:
        scripts.append(script)

    scope._eval_js_request = eval_js

    async def exercise() -> None:
        manager = layer_manager(scope)
        manager.open(first, kind=Layer.POPOVER, group="popup", exclusive=True)
        await asyncio.sleep(0)
        manager.open(second, kind=Layer.POPOVER, group="popup", exclusive=True)
        await asyncio.sleep(0)

    asyncio.run(exercise())

    assert len(scripts) == 2
    assert all("target.focus" not in script for script in scripts)


def test_owner_cascade_restores_only_the_parent_focus() -> None:
    scope = Div()
    modal = Div()
    popup = Div()
    scope.container.extend([modal, popup])
    scripts: list[str] = []

    async def eval_js(script: str) -> None:
        scripts.append(script)

    scope._eval_js_request = eval_js

    async def exercise() -> None:
        manager = layer_manager(scope)
        parent = manager.open(modal, kind=Layer.MODAL, group="modal")
        await asyncio.sleep(0)
        manager.open(popup, kind=Layer.POPOVER, group="popup", owner=modal)
        await asyncio.sleep(0)
        parent.close()
        await asyncio.sleep(0)

    asyncio.run(exercise())

    assert len(scripts) == 3
    assert scripts[0] != scripts[1]
    assert "target.focus" in scripts[2]


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
