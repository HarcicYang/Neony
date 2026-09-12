"""P1 feedback and form components: build, state, events and accessibility."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from neony.application import icons
from neony.application.elements import (
    Alert,
    Button,
    EmptyState,
    FormField,
    Input,
    Skeleton,
    Spinner,
    Textarea,
)
from neony.dom import DOMElement, DomEvent, NodeDescriptor, Signal


def _walk(node: NodeDescriptor):
    yield node
    for child in node.children:
        yield from _walk(child)


def _contains_text(node: NodeDescriptor, text: str) -> bool:
    return any(candidate.text == text for candidate in _walk(node))


class TestTextarea:
    def test_build_and_initial_value(self):
        field = Textarea("Notes", value="draft", rows=6, resize="vertical")
        node = field.build().to_node()

        assert node.tag == "textarea"
        assert node.attrs["placeholder"] == "Notes"
        assert node.attrs["rows"] == "6"
        assert node.styles["resize"] == "vertical"
        assert node.text == "draft"

    def test_user_input_updates_state_and_source(self):
        field = Textarea()
        fired: list[tuple[str, str]] = []
        field.on_input(lambda event: fired.append((event.value, event.source)))

        asyncio.run(
            field._textarea._handlers["input"][0](DomEvent(key=field._textarea.key, type="input", value="hello"))
        )

        assert field.value == "hello"
        assert fired == [("hello", "user")]

    def test_programmatic_write_does_not_fire_input(self):
        field = Textarea()
        fired: list[str] = []
        field.on_input(lambda event: fired.append(event.value))

        field.value = "programmatic"

        assert fired == []

    def test_bind_value_two_way(self):
        field = Textarea()
        signal = Signal("")
        field.bind_value(signal)

        signal.set("from signal")
        assert field.value == "from signal"

        asyncio.run(
            field._textarea._handlers["input"][0](DomEvent(key=field._textarea.key, type="input", value="from user"))
        )
        assert signal() == "from user"

        field.unbind_value()
        field.value = "after unbind"
        assert signal() == "from user"

    def test_invalid_configuration_raises(self):
        with pytest.raises(ValueError):
            Textarea(rows=0)
        with pytest.raises(ValueError):
            Textarea(maxlength=-1)


class TestFormField:
    def test_builds_label_help_and_relationship(self):
        field = FormField(
            "Email",
            Input(type="email"),
            help="Never shared.",
            required=True,
        )
        node = field.build().to_node()
        control = node.children[1].children[0]

        assert _contains_text(node, "Email")
        assert _contains_text(node, "Never shared.")
        assert control.attrs["aria-labelledby"]
        assert control.attrs["aria-describedby"]
        assert control.attrs["aria-required"] == "true"
        assert control.attrs["type"] == "email"

    def test_invalid_and_error_are_exposed(self):
        field = FormField("Email", Input(), invalid=True, error="Invalid email")
        node = field.build().to_node()
        control = node.children[1].children[0]

        assert _contains_text(node, "Invalid email")
        assert control.attrs["aria-invalid"] == "true"
        assert node.children[1].styles["box-shadow"]

        field.invalid = False
        node = field._root.to_node()
        control = node.children[1].children[0]
        assert "aria-invalid" not in control.attrs
        assert "box-shadow" not in node.children[1].styles

    def test_required_star_can_toggle(self):
        field = FormField("Name", Input())
        assert field._required_span.styles.display == "none"

        field.required = True

        assert field._required_span.styles.display == "inline"
        assert field.control.args["aria-required"] == "true"

    def test_component_control_is_mounted_once(self):
        control = Input()
        field = FormField("Name", control)

        assert field.build().to_node()
        with pytest.raises(RuntimeError):
            control.build()


class TestAlert:
    def test_build_variant_and_actions(self):
        alert = Alert(
            "Saved",
            description="All changes synced.",
            variant="success",
            dismissible=True,
            actions=[Button("Undo")],
        )
        node = alert.build().to_node()

        assert node.attrs["role"] == "alert"
        assert node.styles["border-left"] == "3px solid var(--color-success)"
        assert _contains_text(node, "Saved")
        assert _contains_text(node, "All changes synced.")
        assert _contains_text(node, "Undo")
        assert any(child.tag == "button" for child in _walk(node))

    def test_dismiss_is_a_lifecycle_pseudo_event(self):
        alert = Alert("Saved", dismissible=True)
        dismissed: list[Alert] = []
        alert.on_dismiss(dismissed.append)

        alert.dismiss()
        alert.dismiss()

        assert alert.dismissed is True
        assert alert._root.styles.display == "none"
        assert dismissed == [alert]

    def test_close_button_dismisses(self):
        alert = Alert("Saved", dismissible=True)
        fired: list[Alert] = []
        alert.on_dismiss(fired.append)
        button = alert._close_button
        assert button is not None
        icon = button.container[0]
        assert isinstance(icon, DOMElement)

        # The click target is the icon span; it bubbles to the button.
        asyncio.run(button._handlers["click"][0](DomEvent(key=icon.key, type="click")))

        assert alert.dismissed is True
        assert fired == [alert]

    def test_title_description_and_variant_update(self):
        alert = Alert("Old", description="Old body")

        alert.title = "New"
        alert.description = "New body"
        alert.variant = "danger"

        node = alert._root.to_node()
        assert _contains_text(node, "New")
        assert _contains_text(node, "New body")
        assert node.styles["border-left"] == "3px solid var(--color-danger)"

    def test_unknown_variant_raises(self):
        bad_variant: Any = "warning"
        with pytest.raises(ValueError):
            Alert("x", variant=bad_variant)


class TestSpinner:
    def test_build_and_animation(self):
        spinner = Spinner("Loading projects", size="24px", role="success")
        node = spinner.build().to_node()

        assert node.attrs["role"] == "status"
        assert _contains_text(node, "Loading projects")
        assert node.children[0].styles["width"] == "24px"
        assert node.children[0].styles["border-top"] == "2px solid var(--color-success)"
        assert node.children[0].styles["animation"] == "neony-spin 0.8s linear infinite"

    def test_label_size_and_role_update(self):
        spinner = Spinner("")

        spinner.label = "Saving"
        spinner.size = "32px"
        spinner.role = "danger"

        node = spinner._root.to_node()
        assert _contains_text(node, "Saving")
        assert node.children[0].styles["width"] == "32px"
        assert node.children[0].styles["border-top"] == "2px solid var(--color-danger)"

        spinner.label = ""
        assert len(spinner._root.container) == 1

    def test_unknown_role_raises(self):
        bad_role: Any = "warning"
        with pytest.raises(ValueError):
            Spinner(role=bad_role)


class TestSkeleton:
    def test_text_lines_and_animation(self):
        skeleton = Skeleton(variant="text", lines=3, width="70%")
        node = skeleton.build().to_node()

        assert len(node.children) == 3
        assert all(child.styles["width"] == "70%" for child in node.children)
        assert all("animation" in child.styles for child in node.children)

        skeleton.animation = False
        assert all("animation" not in child.styles for child in skeleton._root.to_node().children)

    def test_circle_and_rect_dimensions(self):
        circle = Skeleton(variant="circle").build().to_node().children[0]
        rect = Skeleton(variant="rect").build().to_node().children[0]

        assert circle.styles["width"] == "40px"
        assert circle.styles["height"] == "40px"
        assert circle.styles["border-radius"] == "50%"
        assert rect.styles["height"] == "80px"

    def test_lines_must_be_positive(self):
        with pytest.raises(ValueError):
            Skeleton(lines=0)


class TestEmptyState:
    def test_build_icon_description_and_actions(self):
        empty = EmptyState(
            "No projects",
            description="Create one to start.",
            icon=icons.star,
            actions=[Button("New project")],
        )
        node = empty.build().to_node()

        assert node.attrs["role"] == "status"
        assert _contains_text(node, "No projects")
        assert _contains_text(node, "Create one to start.")
        assert _contains_text(node, "New project")
        assert any(candidate.tag == "span" for candidate in _walk(node))

    def test_description_updates(self):
        empty = EmptyState("No projects", actions=[Button("New project")])
        assert len(empty._root.container) == 2

        empty.description = "Try another filter."

        assert len(empty._root.container) == 3
        assert _contains_text(empty._root.to_node(), "Try another filter.")
        assert _contains_text(empty._root.to_node(), "New project")

    def test_icon_updates(self):
        empty = EmptyState("Empty")
        empty.icon = icons.star
        assert len(empty._root.container) == 2

        empty.icon = None
        assert len(empty._root.container) == 1
