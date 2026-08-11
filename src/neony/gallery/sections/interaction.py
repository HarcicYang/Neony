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

if TYPE_CHECKING:
    from neony.application import Page

# ── tab: events ──────────────────────────────────────────────────

# Mouse tracker: mousedown anywhere inside the zone (even on its text
# labels) bubbles to this bubble_events Div.  The DomEvent carries the
# viewport (x/y) and element-relative (offset_x/offset_y) coordinates.
tracker_text = Text("Click anywhere in this box", role="secondary")
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
mod_input = Input(placeholder="Type anywhere — the lights follow the modifiers…")
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
                Text("Tall content so the zone scrolls…", role="secondary").build(),
                Text("Keep scrolling to see live deltas.", role="secondary").build(),
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

events_panel = Section(
    "Rich Events",
    "Every delegated event carries the full payload: modifier keys "
    "(ctrl/shift/alt/meta), viewport and element-relative mouse "
    "coordinates, wheel deltas, and pointer movement — live delta and "
    "device type. Click the box, hold modifiers while typing, scroll "
    "the zone, move the pointer across the bottom box.",
    """div.on_mousedown(lambda e: f"{e.x}, {e.y} — {e.offset_x}, {e.offset_y}")
div.on_keydown(lambda e: e.ctrl_key or e.meta_key)
div.on_wheel(lambda e: f"dx: {e.delta_x}  dy: {e.delta_y}")
div.on_pointermove(lambda e: f"{e.movement_x}, {e.movement_y} — {e.pointer_type}")""",
    tracker,
    HStack(mod_input, gap="8px"),
    HStack(ctrl_chip, shift_chip, alt_chip, meta_chip, gap="16px"),
    Text(
        "Meta (Super) is often reserved by the window manager on Linux — "
        "hyprland grabs it for its own bindings, so it may never reach "
        "the page. The other three modifiers always arrive.",
        role="secondary",
        size="12px",
    ),
    wheel_zone,
    wheel_delta,
    pointer_zone,
)

# ── tab: drop ────────────────────────────────────────────────────

drop_hint = Text("Drop files anywhere in this box", role="secondary")
dragging = Signal(False)
drop_files = Signal("")
drop_hint.bind_text(dragging, fmt=lambda active: "Release to drop" if active else "Drop files anywhere in this box")
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
        drop_files.set("(no files — on WKWebView the file path is empty)")
        return
    lines = [f"{file['name']}   ({fmt_size(file['size'])}, {file['type']})" for file in event.drop_files]
    lines.append("")
    lines.extend(f"path: {file['path'] or '<unavailable>'}" for file in event.drop_files)
    drop_files.set("\n".join(lines))


drop_zone.on_dragover(on_drop_over).on_dragleave(on_drop_leave).on_drop(on_drop)

drop_panel = Section(
    "File Drop",
    "Drag files from the file manager into the dashed zone. The drop "
    "event carries each file's name, local filesystem path, size and "
    "MIME type. On WebKitGTK the webview reports empty files, so Neony "
    "takes the drop over at the native layer, hit-tests the position, "
    "and re-dispatches the drop event with the real paths; on WebView2 "
    "File.path arrives directly, on WKWebView it is empty. "
    "dragover/dragleave/drop are all delegated, and the browser's "
    "navigate-on-drop default is prevented for you.",
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
paste_input = Input(placeholder="Paste (Ctrl+V) into this field…")
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
        clip_value.set("clipboard_text: <not exposed by this backend>")
    else:
        clip_value.set(
            f"clipboard_text: {event.clipboard_text!r}"
            + (f"  html: {event.clipboard_html!r}" if event.clipboard_html else "")
        )
    clip_log_line("paste event — clipboard carried into Python")


async def on_paste_input(event: DomEvent) -> None:
    if event.value:
        clip_value.set(f"input value: {event.value!r}")


async def on_copy(event: DomEvent) -> None:
    clip_log_line("copy event (user pressed Ctrl+C)")


async def on_cut(event: DomEvent) -> None:
    clip_log_line("cut event (user pressed Ctrl+X)")


paste_input.on_paste(on_paste)
paste_input.on_input(on_paste_input)
paste_input.on_copy(on_copy)
paste_input.on_cut(on_cut)

copy_btn = Button("Copy sample text")
read_btn = Button("Read clipboard", variant="ghost")


async def on_copy_click(event: DomEvent) -> None:
    try:
        await app.clipboard_write("Neony wrote this from Python!")
    except Exception as exc:
        clip_value.set(f"write failed: {exc}")
        clip_log_line(f"clipboard_write() failed: {exc}")
        return
    clip_value.set('wrote "Neony wrote this from Python!"')


async def on_read_click(event: DomEvent) -> None:
    try:
        text = await app.clipboard_read()
    except Exception as exc:  # permission denied / no gesture
        clip_value.set(f"read failed: {exc}")
        clip_log_line(f"clipboard_read() failed: {exc}")
        return
    clip_value.set(f"read: {text!r}")


copy_btn.on_click(on_copy_click)
read_btn.on_click(on_read_click)

clipboard_panel = Section(
    "Clipboard",
    "Clipboard events carry data into Python: paste delivers "
    "clipboard_text / clipboard_html, copy / cut fire as notifications. "
    "The write/read API lives in the backend (no user gesture needed to "
    "write); read still needs the window focused.",
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
b_chip, b_dot = StatusChip("Ctrl+B — bold")
g_chip, g_dot = StatusChip("Ctrl+G — glow")
d_chip, d_dot = StatusChip("Ctrl+D — dark")
k_chip, k_dot = StatusChip("Ctrl+K (Meta+K on macOS) — theme")


async def shortcut_handler(dot: Div, message: str) -> None:
    set_dot(dot, True)
    shortcut_message.set(message)
    await app.render()
    await asyncio.sleep(0.4)
    set_dot(dot, False)


shortcuts_panel = Section(
    "Shortcuts",
    "Page-level keybindings that fire anywhere in the window — even "
    "while an input has focus, and on any tab. Register a single "
    "combo or a per-platform dict (Ctrl+Meta on macOS vs Ctrl on "
    "Linux/Windows). Modifiers must match exactly; the key matches "
    "case-insensitively. Try them from here or any other tab:",
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
chosen = {"value": ""}


def choose(value: str):
    def handler(_dialog: Dialog) -> None:
        chosen["value"] = value

    return handler


dialog = Dialog(
    title="Confirm",
    content=VStack(Text("Try the scrim, Escape, click-away, or the buttons below.")),
    width="380px",
    actions=[
        DialogAction("Confirm", variant="danger", on_click=choose("Confirm")),
        DialogAction("Cancel", variant="ghost", on_click=choose("Cancel")),
        DialogAction("Close", on_click=choose("Close")),
    ],
)
dialog_state = Signal("closed")
dialog_status = Text("", role="secondary")
dialog_status.bind_text(dialog_state)
dialog_open_btn = Button("Open dialog")


async def on_dialog_open(_event: DomEvent) -> None:
    dialog.open = True


dialog_open_btn.on_click(on_dialog_open)


def on_dialog_opened(_dialog: Dialog) -> None:
    chosen["value"] = ""
    dialog_state.set("open — waiting for a choice")


def on_dialog_closed(_dialog: Dialog) -> None:
    if chosen["value"]:
        dialog_state.set(f"closed — chose {chosen['value']!r}")
    else:
        dialog_state.set("closed — dismissed (scrim / Escape / click-away)")


dialog.on_open(on_dialog_opened)
dialog.on_close(on_dialog_closed)

# Tooltip: anchor-relative bubble, placement offsets, hover delay.
tip_top = Tooltip("Tooltip on top", anchor=Button("Hover (top)"), placement="top", delay=1)
tip_bottom = Tooltip("Tooltip below", anchor=Button("Hover (bottom)"), placement="bottom", delay=1)

# Dropdown: themed popup under a trigger (Select's pattern).
theme_choice = Signal("")
theme_dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light"), ("deep-blue", "Deep Blue")], width="160px")
theme_dd.bind_value(theme_choice)
dd_echo = Text("", role="secondary")
dd_echo.bind_text(theme_choice, fmt=lambda value: f"Dropdown: {value}")

# Menu: fixed at the cursor — right-click the button.  Also mounted at
# the page root so no ancestor transform can hijack `position: fixed`.
ctx_menu = Menu(("rename", "Rename"), ("duplicate", "Duplicate"), ("delete", "Delete"))
menu_echo = Text("", role="secondary")
menu_value = Signal("")
menu_echo.bind_text(menu_value, fmt=lambda value: f"Menu: {value}")
menu_btn = Button("Right-click me", variant="ghost")


async def on_menu_contextmenu(event: DomEvent) -> None:
    ctx_menu.open_at(event.x or 0, event.y or 0)


async def on_menu_change(event: DomEvent) -> None:
    menu_value.set(f"{event.value}")


menu_btn.on_contextmenu(on_menu_contextmenu)
ctx_menu.on_change(on_menu_change)

# ── PromptDialog: a single-field text prompt ──────────────────────────

prompt = PromptDialog(
    "What's your name?",
    title="Identify",
    placeholder="Ada Lovelace…",
    value="Ada",
)
prompt_state = Signal("closed")
prompt_status = Text("", role="secondary")
prompt_status.bind_text(prompt_state)
prompt_open_btn = Button("Ask a name")


async def on_prompt_open(_event: DomEvent) -> None:
    prompt.open = True


prompt_open_btn.on_click(on_prompt_open)
prompt.on_open(lambda _dialog: prompt_state.set("open"))
prompt.on_close(lambda _dialog: prompt_state.set("closed"))


def on_prompt_submit(value: str) -> None:
    prompt_state.set(f"submitted: {value!r}")


prompt.on_submit(on_prompt_submit)

overlays_panel = Section(
    "Overlays",
    "Four positioned layers — all CSS-anchored, zero measurement. "
    "Dialog dims the whole page with a themed scrim and centers a "
    "panel with configurable action buttons (scrim / Escape / "
    "click-away close); Tooltip wraps its anchor with placement "
    "offsets and a hover delay; Dropdown reuses the popup pattern "
    "(outsideclick close, full keyboard nav); Menu is fixed at the "
    "cursor via open_at() — right-click the button.",
    """dialog = Dialog(
    title="Confirm", content=Text("..."), width="380px",
    actions=[DialogAction("Confirm", on_click=fn), DialogAction("Cancel", variant="ghost")],  # click → close
)
dialog.open = True                        # or read the property
dialog.on_close(lambda d: print("closed"))
# action callbacks get the dialog: record which button was picked so
# on_close can tell a choice apart from a scrim / Escape dismiss.

ask = PromptDialog("Your name?", value="Ada", placeholder="Type…")
ask.open = True                           # show it
ask.on_submit(lambda v: print(f"got {v}"))  # confirm / Enter

tip = Tooltip("hint", anchor=Button("Hover"), placement="top", delay=0.4)

dd = Dropdown("Theme", items=[("dark", "Dark"), ("light", "Light")])
dd.on_change(lambda e: print(e.value))    # selected value

menu = Menu(("rename", "Rename"), ("delete", "Delete"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # cursor position
menu.on_change(lambda e: print(e.value))""",
    HStack(Text("Dialog", weight="600"), Spacer(), dialog_open_btn, gap="8px"),
    dialog_status,
    Separator(),
    HStack(Text("PromptDialog", weight="600"), Spacer(), prompt_open_btn, gap="8px"),
    prompt_status,
    Separator(),
    HStack(tip_top, tip_bottom, gap="12px"),
    Separator(),
    HStack(Text("Dropdown", weight="600"), Spacer(), theme_dd, gap="8px"),
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
    page.on_shortcut("Ctrl+B", lambda: shortcut_handler(b_dot, "Ctrl+B — bold"))
    page.on_shortcut("Ctrl+G", lambda: shortcut_handler(g_dot, "Ctrl+G — glow"))
    page.on_shortcut("Ctrl+D", lambda: shortcut_handler(d_dot, "Ctrl+D — dark"))
    page.on_shortcut(
        {"darwin": "Meta+K", "default": "Ctrl+K"},
        lambda: shortcut_handler(k_dot, "Ctrl+K / Meta+K — theme"),
    )


def _wire_overlays(page: Page) -> None:
    # Dialog / Menu / Prompt mount at the page root — a transform or
    # backdrop-filter ancestor would hijack `position: fixed` in WebKit.
    page.add(dialog, ctx_menu, prompt)


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire_modifier_keys, _wire_shortcuts, _wire_overlays]
