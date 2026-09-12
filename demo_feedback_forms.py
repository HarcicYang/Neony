#!/usr/bin/env python3
"""P1 feedback and form components in one runnable window."""

from neony.application import Page, icons, launch
from neony.application.elements import (
    Alert,
    Button,
    EmptyState,
    FormField,
    Heading,
    HStack,
    Input,
    Separator,
    Skeleton,
    Spinner,
    Text,
    Textarea,
)
from neony.dom import DomEvent, Signal

notes = Textarea("Notes", rows=5)
notes_value = Signal("")
notes.bind_value(notes_value)
notes_status = Text("", role="secondary")
notes_status.bind_text(notes_value, fmt=lambda value: f"{len(value)} characters")

email_input = Input(placeholder="name@example.com", type="email")
email = FormField("Email", email_input, help="Used only for notifications.", required=True)


def validate_email(event: DomEvent) -> None:
    value = str(event.value or "")
    invalid = bool(value) and ("@" not in value or "." not in value.split("@")[-1])
    email.invalid = invalid
    email.error = "Enter a valid email address." if invalid else None


email_input.on_input(validate_email)

undo = Button("Undo", variant="ghost")


def undo_save(_event: DomEvent) -> None:
    saved.dismiss()


undo.on_click(undo_save)
saved = Alert(
    "Changes saved",
    description="Your preferences are up to date.",
    variant="success",
    dismissible=True,
    actions=[undo],
)
status = Text("", role="secondary")
status_value = Signal("")
status.bind_text(status_value)


def on_dismiss(_alert: Alert) -> None:
    status_value.set("Alert dismissed.")


saved.on_dismiss(on_dismiss)


def restore_alert(_event: DomEvent) -> None:
    saved.dismissed = False
    status_value.set("")


restore = Button("Restore alert", variant="ghost").on_click(restore_alert)

page = Page(gap="16px", padding="24px", max_width="680px").add(
    Heading("Feedback & forms", level=1),
    Text("Multiline input, validation, alerts, loading and empty states.", role="secondary"),
    Separator(),
    notes,
    notes_status,
    email,
    saved,
    HStack(restore, status, gap="10px", align="center"),
    Separator(),
    HStack(Spinner("Loading projects", size="24px"), Skeleton(lines=2, width="180px"), gap="24px", align="center"),
    EmptyState(
        "No projects yet",
        description="Create one to start.",
        icon=icons.star,
        actions=[Button("New project")],
    ),
)


def main() -> None:
    launch(page, title="Neony - Feedback & Forms", width=720, height=760, devtools=True)


if __name__ == "__main__":
    main()
