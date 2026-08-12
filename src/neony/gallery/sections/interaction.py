"""Interaction sections — Events, File Drop, Clipboard, Shortcuts, Overlays.

Exports ``PAGE_HOOKS`` for the page-level wiring these sections own:
window-level modifier-key handlers, in-app shortcuts, and the overlays
(Dialog / Menu / Prompt) mounted at the page root.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from neony.application.elements import (
    Button,
    Dialog,
    DialogAction,
    Dropdown,
    HStack,
    Input,
    Menu,
    PromptDialog,
    Separator,
    Spacer,
    Text,
    Tooltip,
    VStack,
)
from neony.application.theme import stub
from neony.dom import Div, DomEvent, Signal, Styles

from ..core import Mono, Section, StatusChip, app, set_dot
from ..i18n import tr, tr_now

if TYPE_CHECKING:
    from neony.application import Page

# ── tab: events ──────────────────────────────────────────────────

# Mouse tracker: mousedown anywhere inside the zone (even on its text
# labels) bubbles to this bubble_events Div.  The DomEvent carries the
# viewport (x/y) and element-relative (offset_x/offset_y) coordinates.
tracker_text = Text(tr.interaction.click_anywhere, role="secondary")
click_info = Signal("—")
click_pos = Mono()
click_pos.bind_text(click_info)

tracker = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        min_height="90px",
        display="flex",
        flex_direction="column",
        gap="8px",
        justify_content="center",
    ),
    container=[tracker_text.build(), click_pos],
)
tracker.bubble_events = True


async def on_tracker_down(event: DomEvent) -> None:
    click_info.set(f"down at ({event.x:.0f}, {event.y:.0f})  offset ({event.offset_x:.0f}, {event.offset_y:.0f})")


tracker.on_mousedown(on_tracker_down)

# Modifier keys: window-level handlers (registered on the Page below)
# — the lights follow Ctrl / Shift / Alt / Meta wherever keys land,
# no input focus required.
mod_input = Input(placeholder=tr.interaction.mod_placeholder)
ctrl_chip, ctrl_dot = StatusChip("Ctrl")
shift_chip, shift_dot = StatusChip("Shift")
alt_chip, alt_dot = StatusChip("Alt")
meta_chip, meta_dot = StatusChip("Meta")


async def on_mod_key(event: DomEvent) -> None:
    # Both keydown and keyup carry the pressed set at that moment, so
    # re-syncing the lights from the event is enough — no state to keep.
    set_dot(ctrl_dot, event.ctrl_key)
    set_dot(shift_dot, event.shift_key)
    set_dot(alt_dot, event.alt_key)
    set_dot(meta_dot, event.meta_key)


# Wheel deltas: scroll inside the zone; the handler reads delta_x/delta_y.
# WebKitGTK delivers one event per notch in PIXEL mode (delta_mode=0)
# with a constant fractional delta (±94.5 per notch, verified on 2.52);
# trackpads give continuous fractional deltas in the same mode. Line
# mode (delta_mode=1, x16) occurs on other backends. The readout
# converts to pixels via the mode factor and keeps a running total.
# The readout sits BELOW the scrollable zone so it stays visible while
# the content scrolls away.
wheel_total = Signal(0.0)
wheel_readout = Signal("dx: —   dy: —   total: 0px")
wheel_delta = Mono()
wheel_delta.bind_text(wheel_readout)
wheel_zone = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        height="120px",
        overflow="auto",
    ),
    container=[
        Div(
            styles=Styles(height="300px", padding_top="4px"),
            container=[
                Text(tr.interaction.wheel_tall, role="secondary").build(),
                Text(tr.interaction.wheel_keep, role="secondary").build(),
            ],
        )
    ],
)
wheel_zone.bubble_events = True


async def on_wheel(event: DomEvent) -> None:
    # delta_mode: 0 = pixels, 1 = lines (x16), 2 = pages (x256).
    factor = 16 ** (event.delta_mode or 0)
    px = (event.delta_y or 0) * factor
    wheel_total.update(lambda total: total + px)
    wheel_readout.set(
        f"dy: {event.delta_y:+.0f} (mode {event.delta_mode})   dx: {event.delta_x:+.0f}   total: {wheel_total():+.0f}px"
    )


wheel_zone.on_wheel(on_wheel)

# Pointer move: live tracking.  movement_x/y are the delta since the
# last pointermove — no manual position bookkeeping needed — and
# pointer_type tells mouse / pen / touch apart.  Pointermove rides the
# deferred render path, so the readout coalesces to one render per
# frame instead of one per event.
pointer_info = Signal("—")
pointer_readout = Mono()
pointer_readout.bind_text(pointer_info)
pointer_zone = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        min_height="90px",
        display="flex",
        flex_direction="column",
        gap="8px",
        justify_content="center",
    ),
    container=[pointer_readout],
)
pointer_zone.bubble_events = True


async def on_pointer_move(event: DomEvent) -> None:
    pointer_info.set(
        f"({event.x:.0f}, {event.y:.0f})   "
        f"movement ({event.movement_x:+.0f}, {event.movement_y:+.0f})   "
        f"{event.pointer_type or '?'}"
    )


pointer_zone.on_pointermove(on_pointer_move)

# Scroll position: a scrollable box reports its scrollTop/scrollLeft live.
# Scroll is high-frequency, so it rides the deferred render path — the
# readout coalesces to one render per frame.
scroll_info = Signal("top: 0px   left: 0px")
scroll_readout = Mono()
scroll_readout.bind_text(scroll_info)
scroll_zone = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        height="120px",
        overflow="auto",
    ),
    container=[
        Div(
            styles=Styles(height="300px", padding_top="4px"),
            container=[
                Text(tr.interaction.scroll_tall, role="secondary").build(),
                Text(tr.interaction.scroll_keep, role="secondary").build(),
            ],
        )
    ],
)
scroll_zone.bubble_events = True


async def on_scroll(event: DomEvent) -> None:
    scroll_info.set(f"top: {event.scroll_top}px   left: {event.scroll_left}px")


scroll_zone.on_scroll(on_scroll)

events_panel = Section(
    tr.interaction.events_title,
    tr.interaction.events_blurb,
    """div.on_mousedown(lambda e: f"{e.x}, {e.y} — {e.offset_x}, {e.offset_y}")
div.on_keydown(lambda e: e.ctrl_key or e.meta_key)
div.on_wheel(lambda e: f"dx: {e.delta_x}  dy: {e.delta_y}")
div.on_pointermove(lambda e: f"{e.movement_x}, {e.movement_y} — {e.pointer_type}")
div.on_scroll(lambda e: f"top: {e.scroll_top}  left: {e.scroll_left}")""",
    tracker,
    HStack(mod_input, gap="8px"),
    HStack(ctrl_chip, shift_chip, alt_chip, meta_chip, gap="16px"),
    Text(tr.interaction.meta_reserved, role="secondary", size="12px"),
    wheel_zone,
    wheel_delta,
    pointer_zone,
    scroll_zone,
    scroll_readout,
)

# ── tab: drop ────────────────────────────────────────────────────

drop_hint = Text(tr.interaction.drop_hint, role="secondary")
dragging = Signal(False)
drop_files = Signal("")
drop_hint.bind_text(
    dragging,
    fmt=lambda active: tr.interaction.drop_release.get() if active else tr.interaction.drop_hint.get(),
)
drop_list = Mono(size="12px")
drop_list.bind_text(drop_files)

drop_zone = Div(
    styles=Styles(
        border="2px dashed var(--color-border)",
        border_radius="8px",
        padding="20px",
        min_height="140px",
        display="flex",
        flex_direction="column",
        gap="8px",
        justify_content="center",
        align_items="center",
        transition="all 0.15s ease",
    ),
    container=[drop_hint.build(), drop_list],
)
drop_zone.bubble_events = True
drop_zone.bind_style(
    dragging,
    "border",
    fmt=lambda active: "2px dashed var(--color-accent)" if active else "2px dashed var(--color-border)",
)
drop_zone.bind_style(
    dragging,
    "background_color",
    fmt=lambda active: stub.surface if active else None,
)


def fmt_size(size: int) -> str:
    """Human-readable byte count."""
    if size >= 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


async def on_drop_over(_event: DomEvent) -> None:
    dragging.set(True)


async def on_drop_leave(_event: DomEvent) -> None:
    dragging.set(False)


async def on_drop(event: DomEvent) -> None:
    dragging.set(False)
    if not event.drop_files:
        drop_files.set(tr_now(tr.interaction.no_files))
        return
    lines = [f"{file['name']}   ({fmt_size(file['size'])}, {file['type']})" for file in event.drop_files]
    lines.append("")
    lines.extend(f"path: {file['path'] or tr_now(tr.interaction.path_unavailable)}" for file in event.drop_files)
    drop_files.set("\n".join(lines))


drop_zone.on_dragover(on_drop_over).on_dragleave(on_drop_leave).on_drop(on_drop)

drop_panel = Section(
    tr.interaction.drop_title,
    tr.interaction.drop_blurb,
    """zone = Div(styles=Styles(border="2px dashed var(--color-border)"))
zone.on_dragover(lambda e: highlight(zone))
zone.on_dragleave(lambda e: unhighlight(zone))
zone.on_drop(lambda e: [print(f["name"], f["path"]) for f in e.drop_files])""",
    drop_zone,
)

# ── tab: clipboard ───────────────────────────────────────────────

clip_log = Text("", role="secondary")
clip_history = Signal("")
clip_log.bind_text(clip_history)
paste_input = Input(placeholder=tr.interaction.paste_placeholder)
clip_value = Signal("")
clip_line = Mono(size="12px")
clip_line.bind_text(clip_value)
clip_entries: list[str] = []


def clip_log_line(line: str) -> None:
    """Keep the last 4 log lines in Signal state."""
    clip_entries.append(line)
    clip_history.set("\n".join(clip_entries[-4:]))


async def on_paste(event: DomEvent) -> None:
    # clipboard_text may be None on some backends — the input's own
    # value (updated by the input event right after) is the fallback.
    if event.clipboard_text is None:
        clip_value.set(tr_now(tr.interaction.clip_not_exposed))
    else:
        text = tr_now(tr.interaction.clip_text_fmt).format(value=event.clipboard_text)
        if event.clipboard_html:
            text += tr_now(tr.interaction.clip_text_html_fmt).format(html=event.clipboard_html)
        clip_value.set(text)
    clip_log_line(tr_now(tr.interaction.clip_paste_event))


async def on_paste_input(event: DomEvent) -> None:
    if event.value:
        clip_value.set(tr_now(tr.interaction.clip_input_fmt).format(value=event.value))


async def on_copy(event: DomEvent) -> None:
    clip_log_line(tr_now(tr.interaction.clip_copy_event))


async def on_cut(event: DomEvent) -> None:
    clip_log_line(tr_now(tr.interaction.clip_cut_event))


paste_input.on_paste(on_paste)
paste_input.on_input(on_paste_input)
paste_input.on_copy(on_copy)
paste_input.on_cut(on_cut)

copy_btn = Button(tr.interaction.copy_sample)
read_btn = Button(tr.interaction.read_clipboard, variant="ghost")


async def on_copy_click(event: DomEvent) -> None:
    try:
        await app.clipboard_write(tr_now(tr.interaction.wrote_sample))
    except Exception as exc:
        clip_value.set(tr_now(tr.interaction.write_failed_fmt).format(exc=exc))
        clip_log_line(tr_now(tr.interaction.write_failed_log_fmt).format(exc=exc))
        return
    clip_value.set(tr_now(tr.interaction.wrote_fmt).format(text=tr_now(tr.interaction.wrote_sample)))


async def on_read_click(event: DomEvent) -> None:
    try:
        text = await app.clipboard_read()
    except Exception as exc:  # permission denied / no gesture
        clip_value.set(tr_now(tr.interaction.read_failed_fmt).format(exc=exc))
        clip_log_line(tr_now(tr.interaction.read_failed_log_fmt).format(exc=exc))
        return
    clip_value.set(tr_now(tr.interaction.read_fmt).format(text=text))


copy_btn.on_click(on_copy_click)
read_btn.on_click(on_read_click)

clipboard_panel = Section(
    tr.interaction.clipboard_title,
    tr.interaction.clipboard_blurb,
    """inp.on_paste(lambda e: print(e.clipboard_text, e.clipboard_html))
inp.on_copy(lambda e: print("copy"))
inp.on_cut(lambda e: print("cut"))
await app.clipboard_write("hello")
text = await app.clipboard_read()""",
    paste_input,
    clip_line,
    HStack(copy_btn, read_btn, gap="8px"),
    clip_log,
)

# ── tab: shortcuts ───────────────────────────────────────────────

shortcut_message = Signal("")
shortcut_log = Text("", role="secondary")
shortcut_log.bind_text(shortcut_message)
b_chip, b_dot = StatusChip(tr.interaction.ctrl_b)
g_chip, g_dot = StatusChip(tr.interaction.ctrl_g)
d_chip, d_dot = StatusChip(tr.interaction.ctrl_d)
k_chip, k_dot = StatusChip(tr.interaction.ctrl_k)


async def shortcut_handler(dot: Div, message: str) -> None:
    set_dot(dot, True)
    shortcut_message.set(message)
    await app.render()
    await asyncio.sleep(0.4)
    set_dot(dot, False)


shortcuts_panel = Section(
    tr.interaction.shortcuts_title,
    tr.interaction.shortcuts_blurb,
    """page.on_shortcut("Ctrl+B", bold)
page.on_shortcut({"darwin": "Meta+K", "default": "Ctrl+K"}, theme)
# handlers receive no arguments; sync or async""",
    shortcut_log,
    HStack(b_chip, g_chip, d_chip, k_chip, gap="16px"),
)

# ── tab: overlays ────────────────────────────────────────────────

# Dialog: a fixed full-page scrim + centered panel.  Mounted at the
# PAGE ROOT — a transform / backdrop-filter ancestor (like an animated
# panel's rise-in animation) would hijack `position: fixed` in WebKit.
# Closes via scrim / Escape / click-away; the action buttons run their
# callbacks and close by default.
# Action callbacks receive the dialog itself; each records the pick so
# the close callback can tell a button choice apart from a dismiss.
# The recorded values are stable internal sentinels (not the translated
# labels) so the comparison holds across languages.
chosen = {"value": ""}


def choose(value: str):
    def handler(_dialog: Dialog) -> None:
        chosen["value"] = value

    return handler


dialog = Dialog(
    title=tr.interaction.dialog_title,
    content=VStack(Text(tr.interaction.dialog_body)),
    width="380px",
    actions=[
        DialogAction(tr.interaction.dialog_confirm, variant="danger", on_click=choose("confirm")),
        DialogAction(tr.interaction.dialog_cancel, variant="ghost", on_click=choose("cancel")),
        DialogAction(tr.interaction.dialog_close, on_click=choose("close")),
    ],
)
dialog_state = Signal("closed")
dialog_status = Text("", role="secondary")
dialog_status.bind_text(dialog_state)
dialog_open_btn = Button(tr.interaction.dialog_open_btn)


async def on_dialog_open(_event: DomEvent) -> None:
    dialog.open = True


dialog_open_btn.on_click(on_dialog_open)


def on_dialog_opened(_dialog: Dialog) -> None:
    chosen["value"] = ""
    dialog_state.set(tr_now(tr.interaction.dialog_open_state))


def on_dialog_closed(_dialog: Dialog) -> None:
    if chosen["value"]:
        dialog_state.set(tr_now(tr.interaction.dialog_chose_fmt).format(value=chosen["value"]))
    else:
        dialog_state.set(tr_now(tr.interaction.dialog_dismiss))


dialog.on_open(on_dialog_opened)
dialog.on_close(on_dialog_closed)

# Tooltip: anchor-relative bubble, placement offsets, hover delay.
tip_top = Tooltip(tr.interaction.tooltip_top, anchor=Button(tr.interaction.hover_top), placement="top", delay=1)
tip_bottom = Tooltip(
    tr.interaction.tooltip_bottom, anchor=Button(tr.interaction.hover_bottom), placement="bottom", delay=1
)

# Dropdown: themed popup under a trigger (Select's pattern).
theme_choice = Signal("")
theme_dd = Dropdown(
    tr.interaction.theme_label,
    items=[("dark", tr.interaction.dark), ("light", tr.interaction.light), ("deep-blue", tr.interaction.deep_blue)],
    width="160px",
)
theme_dd.bind_value(theme_choice)
dd_echo = Text("", role="secondary")
dd_echo.bind_text(theme_choice, fmt=lambda value: tr.interaction.dropdown_fmt.format(value=value).get())

# Menu: fixed at the cursor — right-click the button.  Also mounted at
# the page root so no ancestor transform can hijack `position: fixed`.
ctx_menu = Menu(
    ("rename", tr.interaction.rename),
    ("duplicate", tr.interaction.duplicate),
    ("delete", tr.interaction.delete),
)
menu_echo = Text("", role="secondary")
menu_value = Signal("")
menu_echo.bind_text(menu_value, fmt=lambda value: tr.interaction.menu_fmt.format(value=value).get())
menu_btn = Button(tr.interaction.right_click, variant="ghost")


async def on_menu_contextmenu(event: DomEvent) -> None:
    ctx_menu.open_at(event.x or 0, event.y or 0)


async def on_menu_change(event: DomEvent) -> None:
    menu_value.set(f"{event.value}")


menu_btn.on_contextmenu(on_menu_contextmenu)
ctx_menu.on_change(on_menu_change)

# ── PromptDialog: a single-field text prompt ──────────────────────────

prompt = PromptDialog(
    tr.interaction.prompt_question,
    title=tr.interaction.identify,
    placeholder=tr.interaction.name_placeholder,
    value="Hiro",
)
prompt_state = Signal("closed")
prompt_status = Text("", role="secondary")
prompt_status.bind_text(prompt_state)
prompt_open_btn = Button(tr.interaction.prompt_open_btn)


async def on_prompt_open(_event: DomEvent) -> None:
    prompt.open = True


prompt_open_btn.on_click(on_prompt_open)
prompt.on_open(lambda _dialog: prompt_state.set(tr_now(tr.interaction.prompt_open_state)))
prompt.on_close(lambda _dialog: prompt_state.set(tr_now(tr.interaction.prompt_closed_state)))


def on_prompt_submit(value: str) -> None:
    prompt_state.set(tr_now(tr.interaction.prompt_submitted_fmt).format(value=value))


prompt.on_submit(on_prompt_submit)

overlays_panel = Section(
    tr.interaction.overlays_title,
    tr.interaction.overlays_blurb,
    """dialog = Dialog(
    title="Confirm", content=Text("..."), width="380px",
    actions=[DialogAction("Confirm", on_click=fn), DialogAction("Cancel", variant="ghost")],  # click → close
)
dialog.open = True                        # or read the property
dialog.on_close(lambda d: print("closed"))
# action callbacks get the dialog: record which button was picked so
# on_close can tell a choice apart from a scrim / Escape dismiss.

ask = PromptDialog("Your name?", value="Hiro", placeholder="Type…")
ask.open = True                           # show it
ask.on_submit(lambda v: print(f"got {v}"))  # confirm / Enter

tip = Tooltip("hint", anchor=Button("Hover"), placement="top", delay=0.4)

dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light")])
dd.on_change(lambda e: print(e.value))    # selected value

menu = Menu(("rename", "Rename"), ("delete", "Delete"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # cursor position
menu.on_change(lambda e: print(e.value))""",
    HStack(Text(tr.interaction.dialog_label, weight="600"), Spacer(), dialog_open_btn, gap="8px"),
    dialog_status,
    Separator(),
    HStack(Text(tr.interaction.prompt_label, weight="600"), Spacer(), prompt_open_btn, gap="8px"),
    prompt_status,
    Separator(),
    HStack(tip_top, tip_bottom, gap="12px"),
    Separator(),
    HStack(Text(tr.interaction.dropdown_label, weight="600"), Spacer(), theme_dd, gap="8px"),
    dd_echo,
    Separator(),
    menu_btn,
    menu_echo,
)

PANELS = {
    "events": events_panel,
    "drop": drop_panel,
    "clipboard": clipboard_panel,
    "shortcuts": shortcuts_panel,
    "overlays": overlays_panel,
}

# ── page wiring ──────────────────────────────────────────────────


def _wire_modifier_keys(page: Page) -> None:
    # Window-level key events drive the Events tab's modifier lights —
    # they respond wherever keys land, even while an input has focus.
    page.on_keydown(on_mod_key).on_keyup(on_mod_key)


def _wire_shortcuts(page: Page) -> None:
    # In-app shortcuts fire even while an input has focus, on any tab.
    # The handler lights its dot, then dims it again after a beat.
    page.on_shortcut("Ctrl+B", lambda: shortcut_handler(b_dot, tr_now(tr.interaction.ctrl_b)))
    page.on_shortcut("Ctrl+G", lambda: shortcut_handler(g_dot, tr_now(tr.interaction.ctrl_g)))
    page.on_shortcut("Ctrl+D", lambda: shortcut_handler(d_dot, tr_now(tr.interaction.ctrl_d)))
    page.on_shortcut(
        {"darwin": "Meta+K", "default": "Ctrl+K"},
        lambda: shortcut_handler(k_dot, tr_now(tr.interaction.ctrl_k)),
    )


def _wire_overlays(page: Page) -> None:
    # Dialog / Menu / Prompt mount at the page root — a transform or
    # backdrop-filter ancestor would hijack `position: fixed` in WebKit.
    page.add(dialog, ctx_menu, prompt)


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire_modifier_keys, _wire_shortcuts, _wire_overlays]
