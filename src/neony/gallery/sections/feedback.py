"""Form validation and loading/empty-state feedback sections."""

from __future__ import annotations

from neony.application import icons
from neony.application.elements import (
    Alert,
    Button,
    EmptyState,
    FormField,
    Input,
    Separator,
    Skeleton,
    Spinner,
    Text,
    Textarea,
)
from neony.dom import DomEvent, Signal

from ..core import Section
from ..i18n import tr

notes = Textarea(tr.feedback.notes_placeholder, value="", rows=5, resize="vertical")
notes_value = Signal("")
notes.bind_value(notes_value)
notes_echo = Text("", role="secondary")
notes_echo.bind_text(
    notes_value,
    fmt=lambda value: tr.feedback.notes_echo_fmt.format(n=len(value)).get(),
)

email_input = Input(placeholder=tr.feedback.email_placeholder, type="email")
email_field = FormField(
    tr.feedback.email_label,
    email_input,
    help=tr.feedback.email_help,
    required=True,
)


def on_email_input(event: DomEvent) -> None:
    value = str(event.value or "")
    invalid = bool(value) and ("@" not in value or "." not in value.split("@")[-1])
    email_field.invalid = invalid
    email_field.error = tr.feedback.email_error if invalid else None


email_input.on_input(on_email_input)

undo_alert = Button(tr.feedback.alert_action, variant="ghost")


def on_undo_alert(_event: DomEvent) -> None:
    saved_alert.dismiss()


undo_alert.on_click(on_undo_alert)
saved_alert = Alert(
    tr.feedback.alert_title,
    description=tr.feedback.alert_body,
    variant="success",
    dismissible=True,
    actions=[undo_alert],
)
alert_state = Signal(False)
saved_alert.on_dismiss(lambda _alert: alert_state.set(True))
alert_status = Text("", role="secondary")
alert_status.bind_text(
    alert_state,
    fmt=lambda dismissed: tr.feedback.alert_dismissed.get() if dismissed else "",
)
restore_alert = Button(tr.feedback.alert_restore, variant="ghost")


def on_restore_alert(_event: DomEvent) -> None:
    saved_alert.dismissed = False
    alert_state.set(False)


restore_alert.on_click(on_restore_alert)

spinner = Spinner(tr.feedback.spinner_label, size="24px")
skeleton = Skeleton(variant="text", lines=3, width="72%")
empty = EmptyState(
    tr.feedback.empty_title,
    description=tr.feedback.empty_description,
    icon=icons.star,
    actions=[Button(tr.feedback.empty_action)],
)

feedback_panel = Section(
    tr.feedback.title,
    tr.feedback.blurb,
    """notes = Textarea("Notes", rows=5, resize="vertical")
notes.bind_value(notes_signal)
notes.on_input(on_preview)

email = FormField("Email", Input(type="email"),
                  help="Never shared.", required=True)
email.invalid = True
email.error = "Enter a valid email address."

alert = Alert("Saved", description="All changes synced.",
              variant="success", dismissible=True)
alert.on_dismiss(on_dismissed)
alert.dismiss()

Spinner("Loading projects", size="24px", role="accent")
Skeleton(variant="text", lines=3, width="72%")

EmptyState("No projects", description="Create one to start.",
           icon=icons.star, actions=[Button("New project")])""",
    notes,
    notes_echo,
    Separator(),
    email_field,
    Separator(),
    saved_alert,
    restore_alert,
    alert_status,
    Separator(),
    spinner,
    skeleton,
    empty,
)

PANELS = {"feedback": feedback_panel}
