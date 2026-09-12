"""FormField — label, help text and validation state around any control."""

from __future__ import annotations

from neony.application.theme import Theme, stub
from neony.dom import Div, DOMElement, Label, Span, Styles, Transition

from .base import Component, ReactiveText, _mount_text

_ROOT = Styles(display="flex", flex_direction="column", gap="6px", width="100%")
_LABEL = Styles(
    display="flex",
    align_items="center",
    gap="4px",
    font_size="13px",
    font_weight="600",
    color=stub.text_secondary,
)
_REQUIRED = Styles(color=stub.danger, display="none")
_SLOT = Styles(
    display="flex",
    flex_direction="column",
    border_radius="9px",
    transition=Transition(property="box-shadow", duration="0.15s", timing="ease"),
)
_MESSAGE = Styles(font_size="12px", color=stub.text_secondary, line_height="1.4")
_ERROR = _MESSAGE.model_copy(update={"color": stub.danger, "display": "none"})


class FormField(Component):
    """A labelled form row with optional help and inline error text.

    The label is connected through ``aria-labelledby``; help and error
    text are connected through ``aria-describedby``.  ``invalid=True``
    draws a danger focus halo around the control and exposes
    ``aria-invalid="true"``.
    """

    def __init__(
        self,
        label: ReactiveText,
        control: Component | DOMElement,
        *,
        help: ReactiveText | None = None,
        required: bool = False,
        invalid: bool = False,
        error: ReactiveText | None = None,
    ) -> None:
        super().__init__()
        self._label: ReactiveText = label
        self._help: ReactiveText | None = help
        self._error: ReactiveText | None = error
        self._required = required
        self._invalid = invalid

        if isinstance(control, Component):
            self._track_component(control)
            self._control = control.build()
        else:
            self._control = control
        self._control_root = self._control
        if self._control_root.id_ is None:
            self._control_root.id_ = self._control_root.key

        self._label_el = Label(styles=_LABEL)
        self._label_el.id_ = self._label_el.key
        self._label_span = Span(container=[])
        self._required_span = Span(container=["*"], styles=_REQUIRED)
        _mount_text(self._label_span, label)
        self._label_el.container = [self._label_span, self._required_span]

        self._help_span = Span(container=[], styles=_MESSAGE)
        self._help_span.id_ = self._help_span.key
        self._error_span = Span(container=[], styles=_ERROR)
        self._error_span.id_ = self._error_span.key
        self._render_message(self._help_span, self._help)
        self._render_message(self._error_span, self._error)

        self._slot = Div(styles=_SLOT, container=[self._control_root])
        self._root = Div(
            styles=_ROOT,
            container=[self._label_el, self._slot, self._help_span, self._error_span],
        )
        self._apply_state()

    @property
    def label(self) -> str:
        if isinstance(self._label, str):
            return self._label
        return self._label()

    @label.setter
    def label(self, value: str) -> None:
        self._label = value
        self._label_span._unbind_text()
        self._label_span.container = [value]

    @property
    def control(self) -> DOMElement:
        """The mounted control root (read-only)."""
        return self._control_root

    @property
    def help(self) -> str | None:
        return self._resolve_message(self._help)

    @help.setter
    def help(self, value: ReactiveText | None) -> None:
        self._help = value
        self._render_message(self._help_span, value)
        self._apply_state()

    @property
    def error(self) -> str | None:
        return self._resolve_message(self._error)

    @error.setter
    def error(self, value: ReactiveText | None) -> None:
        self._error = value
        self._render_message(self._error_span, value)
        self._apply_state()

    @property
    def required(self) -> bool:
        return self._required

    @required.setter
    def required(self, value: bool) -> None:
        self._required = value
        self._apply_state()

    @property
    def invalid(self) -> bool:
        return self._invalid

    @invalid.setter
    def invalid(self, value: bool) -> None:
        self._invalid = value
        self._apply_state()

    @staticmethod
    def _resolve_message(value: ReactiveText | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return value()

    @staticmethod
    def _render_message(span: Span, value: ReactiveText | None) -> None:
        span._unbind_text()
        if value is None:
            span.container = []
        else:
            _mount_text(span, value)

    def _apply_state(self) -> None:
        self._required_span.styles = _REQUIRED.model_copy(update={"display": "inline" if self._required else "none"})
        has_error = self._resolve_message(self._error) is not None
        self._error_span.styles = _ERROR.model_copy(update={"display": "block" if has_error else "none"})

        args = dict(self._control_root.args)
        args["aria-labelledby"] = self._label_el.key
        if self._required:
            args["aria-required"] = "true"
        else:
            args.pop("aria-required", None)
        described_by = [
            span.key for span, value in ((self._help_span, self._help), (self._error_span, self._error)) if value
        ]
        if described_by:
            args["aria-describedby"] = " ".join(described_by)
        else:
            args.pop("aria-describedby", None)
        if self._invalid:
            args["aria-invalid"] = "true"
        else:
            args.pop("aria-invalid", None)
        self._control_root.args = args

        self._slot.styles = _SLOT.model_copy(
            update={"box_shadow": Theme.focus_glow("danger") if self._invalid else None}
        )
