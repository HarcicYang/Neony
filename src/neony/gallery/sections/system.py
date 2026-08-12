"""System & Advanced sections — Animations, Reactive, Sidebar, Tabs, Window.

Exports ``PAGE_HOOKS`` for the page-level focus/blur lifecycle hooks that
drive the Window tab status line.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

from neony.application.elements import (
    Button,
    Checkbox,
    Component,
    GlassPanel,
    Heading,
    HStack,
    Icon,
    Input,
    Pane,
    Separator,
    Sidebar,
    Spacer,
    Tabs,
    Text,
    VStack,
)
from neony.application.theme import stub
from neony.dom import (
    Animation,
    Color,
    Computed,
    Div,
    DomEvent,
    KeyFrame,
    Props,
    Signal,
    Styles,
    batch,
    effect,
    untrack,
)

from ..core import Mono, Section, app, heat
from ..i18n import tr, tr_now

if TYPE_CHECKING:
    from neony.application import Page

# ── tab: animations ──────────────────────────────────────────────

# Typed @keyframes — chainable builder; register_keyframe injects the
# CSS into <style id="neony-keyframes"> in every window (later-wins on
# name collision).
spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)")).set("100%", Props(transform="rotate(360deg)"))
app.register_keyframe(spin)

fade_slide = (
    KeyFrame("fade-slide")
    .set("0%", Props(opacity=0, transform="translateY(8px)"))
    .set("100%", Props(opacity=1, transform="translateY(0)"))
)
app.register_keyframe(fade_slide)

# Spinner: a border ring spun by the keyframe above.  The Animation
# model references the KeyFrame by name — the browser resolves the
# @keyframes block automatically.
spinner = Div(
    styles=Styles(
        width="36px",
        height="36px",
        border="3px solid var(--color-border)",
        border_top="3px solid var(--color-accent)",
        border_radius="50%",
        animation=Animation(name="spin", duration="1s", timing="linear", iteration_count="infinite"),
    )
)
spin_state = Text("", size="12px", role="secondary")
paused = Signal(False)
spin_state.bind_text(
    paused,
    fmt=lambda is_paused: tr.system.paused.get() if is_paused else tr.system.running.get(),
)


async def on_spin_toggle(_event: DomEvent) -> None:
    anim = spinner.styles.animation
    is_paused = paused()
    if isinstance(anim, Animation):
        spinner.styles.animation = anim.model_copy(update={"play_state": "running" if is_paused else "paused"})
    paused.set(not is_paused)


spin_toggle = Button(tr.system.pause, variant="ghost")
spin_toggle.on_click(on_spin_toggle)

# A card that plays its enter animation once, on mount.
enter_card = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="16px",
        background_color=stub.surface,
        animation=Animation(name="fade-slide", duration="0.4s", timing="ease-out"),
    ),
    container=[Text(tr.system.fades_slides).build()],
)

animations_panel = Section(
    tr.system.animations_title,
    tr.system.animations_blurb,
    """spin = KeyFrame("spin").set("0%", Props(transform="rotate(0deg)"))
                     .set("100%", Props(transform="rotate(360deg)"))
app.register_keyframe(spin)
icon.styles.animation = Animation(name="spin", duration="1s",
                                  timing="linear",
                                  iteration_count="infinite")
icon.styles.animation = anim.model_copy(update={"play_state": "paused"})  # pause/resume

fade = KeyFrame("fade-slide").set("0%", Props(opacity=0, transform="translateY(8px)"))
card.styles.animation = Animation(name="fade-slide", duration="0.5s")""",
    HStack(spinner, spin_state, spin_toggle, gap="12px", align="center"),
    enter_card,
)

# ── tab: reactive ────────────────────────────────────────────────

count = Signal(0)
count_value = Text("0", size="40px", weight="bold")
count_value.bind_text(count)


class HeatBar(Component):
    """Demo-local signal-driven heat bar."""

    def __init__(self, value: Signal, *, height: str = "14px") -> None:
        super().__init__()
        self._root = Div(
            styles=Styles(
                height=height,
                border_radius="7px",
                background_color=stub.border,
                transition="all 0.15s ease",
            )
        )
        self._root.bind_style(value, "width", fmt=lambda number: f"{max(0, min(100, number))}%")
        self._root.bind_style(value, "background_color", fmt=self._color)

    @staticmethod
    def _color(number: int | float) -> Color:
        number = max(0, min(100, number))
        return Color(rgb=(int(40 + 2.1 * number), int(190 - 1.3 * number), 120))


heat_bar = HeatBar(heat)
heat_label = Text("", role="secondary")
heat_label.bind_text(heat, fmt=lambda n: tr.system.heat_fmt.format(n=n).get())

plus_btn = Button("+")
minus_btn = Button("-", variant="ghost")
plus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n + 10))))
minus_btn.on_click(lambda _e: heat.update(lambda n: max(0, min(100, n - 10))))

# Computed: two signals, one derived value, one bound label.
first_name = Signal("")
last_name = Signal("")
first_input = Input(placeholder=tr.system.first_name).bind_value(first_name)
last_input = Input(placeholder=tr.system.last_name).bind_value(last_name)
full_name = Computed(lambda: f"{first_name().strip()} {last_name().strip()}".strip())
full_echo = Text("", role="secondary")
full_echo.bind_text(
    full_name,
    fmt=lambda v: tr.system.computed_full_fmt.format(v=v).get() if v else tr.system.type_both.get(),
)


async def on_first(event: DomEvent) -> None:
    first_name.set(event.value)


async def on_last(event: DomEvent) -> None:
    last_name.set(event.value)


first_input.on_input(on_first)
last_input.on_input(on_last)

# Effect: re-runs on dependency change, cleans up via dispose().
level = Signal(50)
level_log = Signal(tr_now(tr.system.effect_fired_fmt).format(n=level()))
level_text = Mono()
level_text.bind_text(level_log)
effect_slot = {"eff": None}
running = Signal(True)
effect_state = Text("", role="secondary", size="12px")
effect_state.bind_text(
    running,
    fmt=lambda active: tr.system.effect_running.get() if active else tr.system.effect_disposed.get(),
)


def level_sync() -> None:
    level_log.set(tr_now(tr.system.effect_fired_fmt).format(n=level()))


effect_slot["eff"] = effect(level_sync)
# Label follows both the running state and the active language: the
# displayed action is "Dispose effect" while running, "Restart effect"
# after disposal.  A Computed reading ``running()`` and the tr refs
# subscribes to both — no imperative ``.label =`` overwrite (that would
# freeze the span and break the language binding).
effect_btn = Button(
    Computed(lambda: tr.system.dispose_effect.get() if running() else tr.system.restart_effect.get()),
    variant="ghost",
)


async def on_effect_toggle(_event: DomEvent) -> None:
    if running():
        current = effect_slot["eff"]
        if current is not None:
            current.dispose()
        effect_slot["eff"] = None
        running.set(False)
    else:
        effect_slot["eff"] = effect(level_sync)
        running.set(True)


effect_btn.on_click(on_effect_toggle)

level_up = Button(tr.system.level_plus)
level_down = Button(tr.system.level_minus, variant="ghost")
level_up.on_click(lambda _e: level.update(lambda n: max(0, min(100, n + 5))))
level_down.on_click(lambda _e: level.update(lambda n: max(0, min(100, n - 5))))

# bind_visible: a checkbox drives an element's display.
secret = Signal(True)
secret_block = Div(
    styles=Styles(
        border="1px solid var(--color-border)",
        border_radius="8px",
        padding="12px 16px",
        background_color=stub.surface,
    ),
    container=[Text(tr.system.secret_desc).build()],
)
secret_block.bind_visible(secret)
secret_check = Checkbox(tr.system.visible, checked=True).bind_value(secret)

# batch(): two signals changed together flush ONE effect run.
batch_a = Signal(0)
batch_b = Signal(0)
batch_runs = Signal(0)
batch_count = Mono()
batch_count.bind_text(
    batch_runs,
    fmt=lambda runs: tr.system.effect_runs_fmt.format(runs=runs, a=batch_a(), b=batch_b()).get(),
)


def batch_sync() -> None:
    batch_a()
    batch_b()
    batch_runs.update(lambda runs: runs + 1)


batch_effect = effect(batch_sync)
batch_single_btn = Button(tr.system.a_plus_1, variant="ghost")
batch_both_btn = Button(tr.system.batch_both, variant="ghost")


async def on_batch_single(_event: DomEvent) -> None:
    batch_a.update(lambda n: n + 1)


async def on_batch_both(_event: DomEvent) -> None:
    with batch():
        batch_a.update(lambda n: n + 1)
        batch_b.update(lambda n: n + 1)


batch_single_btn.on_click(on_batch_single)
batch_both_btn.on_click(on_batch_both)

# untrack(): reading a signal inside an effect without subscribing.
untrack_tracked = Signal(0)
untrack_ignored = Signal(0)
untrack_runs = Signal(0)
untrack_count = Mono()
untrack_count.bind_text(
    Computed(
        lambda: tr.system.untrack_runs_fmt.format(
            runs=untrack_runs(),
            tracked=untrack_tracked(),
            ignored=tr.system.untrack_ignored.format(n=untrack_ignored()).get(),
        ).get()
    )
)


def untrack_sync() -> None:
    untrack_tracked()
    untrack_runs.update(lambda runs: runs + 1)
    untrack(untrack_ignored.get)


untrack_effect = effect(untrack_sync)
untrack_track_btn = Button(tr.system.tracked_plus, variant="ghost")
untrack_ignore_btn = Button(tr.system.ignored_plus, variant="ghost")
untrack_track_btn.on_click(lambda _e: untrack_tracked.update(lambda n: n + 1))
untrack_ignore_btn.on_click(lambda _e: untrack_ignored.update(lambda n: n + 1))

# bind_attr: a signal drives an HTML attribute (the button's disabled).
busy = Signal(False)
busy_btn = Button(tr.system.save)
busy_btn.bind_attr(busy, "disabled")
busy_state = Text(tr.system.busy_state, role="secondary")
busy_state.bind_text(
    busy,
    fmt=lambda b: tr.system.busy_fmt.format(b=b, flag=" " if b else " not ").get(),
)
busy_toggle = Button(tr.system.toggle_busy, variant="ghost")
busy_toggle.on_click(lambda _e: busy.update(lambda b: not b))

# Computed chain: two derived values, one bound label.
price = Signal(10.0)
qty = Signal(2)
rate = Signal(0.9)
subtotal = Computed(lambda: price() * qty())
total = Computed(lambda: subtotal() * rate())
price_up = Button(tr.system.price_plus, variant="ghost")
price_down = Button(tr.system.price_minus, variant="ghost")
qty_up = Button(tr.system.qty_plus, variant="ghost")
qty_down = Button(tr.system.qty_minus, variant="ghost")
rate_up = Button(tr.system.rate_plus, variant="ghost")
rate_down = Button(tr.system.rate_minus, variant="ghost")
price_up.on_click(lambda _e: price.update(lambda v: v + 1))
price_down.on_click(lambda _e: price.update(lambda v: max(0.0, v - 1)))
qty_up.on_click(lambda _e: qty.update(lambda v: v + 1))
qty_down.on_click(lambda _e: qty.update(lambda v: max(1, v - 1)))
rate_up.on_click(lambda _e: rate.update(lambda v: min(1.0, v + 0.1)))
rate_down.on_click(lambda _e: rate.update(lambda v: max(0.1, v - 0.1)))
total_text = Text("", size="16px", weight="600")
total_text.bind_text(
    total,
    fmt=lambda v: tr.system.total_fmt.format(v=v, s=subtotal(), r=rate()).get(),
)

# bind_value: signal ↔ component value, both ways.
name_signal = Signal("")
bind_input = Input(placeholder=tr.system.bind_placeholder)
bind_input.bind_value(name_signal)
bind_echo_one = Text("", role="secondary")
bind_echo_two = Text("", role="secondary")
bind_echo_one.bind_text(name_signal, fmt=lambda v: tr.system.echo_fmt.format(n=1, v=v).get())
bind_echo_two.bind_text(name_signal, fmt=lambda v: tr.system.echo_fmt.format(n=2, v=v).get())
bind_set_btn = Button(tr.system.set_signal, variant="ghost")
bind_set_btn.on_click(lambda _e: name_signal.set(tr_now(tr.system.written_signal)))

reactive_panel = Section(
    tr.system.reactive_title,
    tr.system.reactive_blurb,
    """count = Signal(0)
label.bind_text(count)

heat = Signal(30)
bar.bind_style(heat, "width", fmt=lambda n: f"{n}%")
bar.bind_style(heat, "background_color", fmt=colorize)

full = Computed(lambda: f"{first()} {last()}")
echo.bind_text(full)

box.bind_visible(flag)
eff = effect(sync)   # re-runs on dependency change
eff.dispose()        # stops it

with batch():        # several writes → ONE effect run
    a.set(1); b.set(2)
untrack(ignored.get) # read without subscribing

btn.bind_attr(busy, "disabled")            # signal → attribute
total = Computed(lambda: subtotal() * rate())  # chains compose

inp.bind_value(name) # two-way: signal ↔ component value""",
    HStack(Text(tr.system.heat_bar, weight="600"), Spacer(), minus_btn, plus_btn, gap="8px"),
    heat_bar,
    heat_label,
    Separator(),
    HStack(first_input, last_input, gap="8px"),
    full_echo,
    Separator(),
    HStack(Text(tr.system.effect, weight="600"), Spacer(), level_down, level_up, effect_btn, gap="8px"),
    level_text,
    effect_state,
    Separator(),
    secret_check,
    secret_block,
    Separator(),
    HStack(Text(tr.system.batch, weight="600"), Spacer(), batch_single_btn, batch_both_btn, gap="8px"),
    batch_count,
    Separator(),
    HStack(Text(tr.system.untrack, weight="600"), Spacer(), untrack_track_btn, untrack_ignore_btn, gap="8px"),
    untrack_count,
    Separator(),
    HStack(Text(tr.system.bind_attr, weight="600"), Spacer(), busy_toggle, gap="8px"),
    HStack(busy_btn, busy_state, gap="12px", align="center"),
    Separator(),
    HStack(
        Text(tr.system.computed_chain, weight="600"),
        Spacer(),
        price_down,
        price_up,
        qty_down,
        qty_up,
        rate_down,
        rate_up,
        gap="8px",
    ),
    total_text,
    Separator(),
    bind_input,
    bind_echo_one,
    bind_echo_two,
    HStack(Spacer(), bind_set_btn, gap="8px"),
)

# ── tab: sidebar ─────────────────────────────────────────────────

home_pane = GlassPanel(
    Heading(tr.system.home, level=3),
    Text(tr.system.home_content, role="secondary"),
    gap="12px",
    padding="16px",
    radius="12px",
    grow=True,
)
settings_pane = GlassPanel(
    Heading(tr.system.settings, level=3),
    Text(tr.system.settings_content, role="secondary"),
    gap="12px",
    padding="16px",
    radius="12px",
    grow=True,
)
profile_pane = GlassPanel(
    Heading(tr.system.profile, level=3),
    Text(tr.system.profile_content, role="secondary"),
    gap="12px",
    padding="16px",
    radius="12px",
    grow=True,
)

active_pane = Signal("home")
sidebar = Sidebar(
    Pane(tr.system.home, key="home", icon=Icon.glyph("🏠"), panel=home_pane),
    Pane(tr.system.settings, key="settings", icon=Icon.glyph("⚙️"), panel=settings_pane),
    Pane(tr.system.profile, key="profile", icon=Icon.glyph("👤"), panel=profile_pane),
    radius="12px",
)
sidebar.bind_selected(active_pane)
sidebar_state = Text("", role="secondary", size="12px")
sidebar_state.bind_text(active_pane, fmt=lambda key: tr.system.active_fmt.format(key=key).get())

sidebar_panel = Section(
    tr.system.sidebar_title,
    tr.system.sidebar_blurb,
    """active = Signal("home")
sidebar = Sidebar(
    Pane("Home", key="home", icon=Icon.glyph("🏠"), panel=home_panel),
    Pane("Settings", key="settings", icon=Icon.glyph("⚙️"), panel=settings_panel),
)
sidebar.bind_selected(active)
state.bind_text(active, fmt=lambda key: f"active: {key}")""",
    sidebar,
    sidebar_state,
)

# ── tab: tabs ───────────────────────────────────────────────────

# Tabs owns its content panes (the _PanelHost keeps pane DOM mounted
# across switches, so input values and scroll offsets survive).  Panes
# are plain VStacks — the host already supplies the panel chrome
# (padding/surface), so wrapping in a GlassPanel would double-pad.
pane_a = VStack(
    Heading(tr.system.pane_a, level=4),
    Text(tr.system.first_pane, role="secondary"),
    gap="12px",
)
pane_b = VStack(
    Heading(tr.system.pane_b, level=4),
    Text(tr.system.second_pane, role="secondary"),
    gap="12px",
)
pane_c = VStack(Heading(tr.system.pane_c, level=4), Text(tr.system.third_pane, role="secondary"), gap="12px")

active_tab = Signal("a")
tabs = Tabs((tr.system.pane_a, pane_a, "a"), (tr.system.pane_b, pane_b, "b"), (tr.system.pane_c, pane_c, "c"))
tabs.bind_selected(active_tab)
tab_state = Text("", role="secondary", size="12px")
tab_state.bind_text(active_tab, fmt=lambda key: tr.system.tab_selected_fmt.format(key=key).get())

# Too many tabs scroll sideways instead of wrapping into extra rows;
# the edge-fade mask (on by default) hints at off-screen tabs.
scroll_tabs = Tabs(
    *[
        (
            tr.system.section_fmt.format(c=chr(65 + i)),
            VStack(Text(tr.system.panel_fmt.format(c=chr(65 + i)), role="secondary"), gap="12px"),
            chr(65 + i),  # explicit key — a reactive title can't derive one
        )
        for i in range(10)
    ]
)

tabs_panel = Section(
    tr.system.tabs_title,
    tr.system.tabs_blurb,
    """active = Signal("a")
tabs = Tabs(("A", pane_a, "a"), ("B", pane_b, "b"), ("C", pane_c, "c"))
tabs.bind_selected(active)
state.bind_text(active, fmt=lambda key: f"selected: {key}")

# overflow scrolls sideways — no wrapping
scroll = Tabs(*[(f"Section {c}", pane) for c in "ABCDEFGHIJ"])""",
    tabs,
    tab_state,
    Separator(),
    scroll_tabs,
)

# ── tab: window ──────────────────────────────────────────────────

# Wayland forbids client-side window positioning (tao's
# set_outer_position is a no-op there), so the position buttons also
# resize — the size change proves set_bounds is working either way.
_ON_WAYLAND = "WAYLAND_DISPLAY" in os.environ and sys.platform.startswith("linux")

win_state = Signal(tr_now(tr.system.window_state))
win_status = Text("", role="secondary")
win_status.bind_text(win_state)
win_note = Text(
    Computed(
        lambda: tr.system.hide_note.get() + (tr.system.wayland_note.get() if _ON_WAYLAND else tr.system.pos_note.get())
    ),
    role="secondary",
    size="12px",
)

hide_btn = Button(tr.system.hide, variant="ghost")
show_btn = Button(tr.system.show, variant="ghost")
focus_btn = Button(tr.system.focus, variant="ghost")
pos1_btn = Button(tr.system.compact_pos)
pos2_btn = Button(tr.system.default_pos, variant="ghost")


async def on_hide(event: DomEvent) -> None:
    await app.hide()
    win_state.set(tr_now(tr.system.window_hidden))
    await asyncio.sleep(2)
    await app.show()
    win_state.set(tr_now(tr.system.window_shown_restore))


async def on_show(event: DomEvent) -> None:
    await app.show()
    win_state.set(tr_now(tr.system.window_shown))


async def on_focus_click(event: DomEvent) -> None:
    await app.focus()
    win_state.set(tr_now(tr.system.window_focused))


async def on_pos1(event: DomEvent) -> None:
    await app.set_bounds(100, 100, 440, 560)
    win_state.set(tr_now(tr.system.set_bounds_fmt).format(x=100, y=100, w=440, h=560))


async def on_pos2(event: DomEvent) -> None:
    await app.set_bounds(0, 0, 560, 720)
    win_state.set(tr_now(tr.system.set_bounds_fmt).format(x=0, y=0, w=560, h=720))


hide_btn.on_click(on_hide)
show_btn.on_click(on_show)
focus_btn.on_click(on_focus_click)
pos1_btn.on_click(on_pos1)
pos2_btn.on_click(on_pos2)

window_panel = Section(
    tr.system.window_title,
    tr.system.window_blurb,
    """await app.show() / app.hide() / app.focus()
await app.set_bounds(x, y, w, h)   # outer position + inner size
page.on_focus(lambda: print("focused"))
page.on_blur(lambda: print("blurred"))""",
    win_status,
    HStack(hide_btn, show_btn, focus_btn, gap="8px"),
    HStack(pos1_btn, pos2_btn, gap="8px"),
    win_note,
)

# ── tab: dialogs ─────────────────────────────────────────────────

# File dialogs are the platform's own — zenity on Linux, osascript on
# macOS, PowerShell on Windows, tkinter fallback — shown as a child
# process so the app's event loop keeps running.  Each call suspends
# until the user picks or cancels.
dialog_open_btn = Button(tr.system.dialog_open, variant="ghost")
dialog_many_btn = Button(tr.system.dialog_open_many, variant="ghost")
dialog_save_btn = Button(tr.system.dialog_save, variant="ghost")
dialog_folder_btn = Button(tr.system.dialog_folder, variant="ghost")
dialog_state = Signal(tr_now(tr.system.dialog_idle))
dialog_echo = Text("", role="secondary")
dialog_echo.bind_text(dialog_state)


async def on_dialog_open(_event: DomEvent) -> None:
    path = await app.open_file(title=tr_now(tr.system.dialog_open_title), filetypes=[("All files", "*.*")])
    dialog_state.set(
        tr_now(tr.system.dialog_picked_fmt).format(path=path) if path else tr_now(tr.system.dialog_cancelled)
    )


async def on_dialog_many(_event: DomEvent) -> None:
    paths = await app.open_files(title=tr_now(tr.system.dialog_open_title))
    dialog_state.set(
        tr_now(tr.system.dialog_many_fmt).format(n=len(paths), names=", ".join(paths))
        if paths
        else tr_now(tr.system.dialog_cancelled)
    )


async def on_dialog_save(_event: DomEvent) -> None:
    path = await app.save_file(
        title=tr_now(tr.system.dialog_save_title), default_name="untitled.txt", filetypes=[("Text", "*.txt")]
    )
    dialog_state.set(
        tr_now(tr.system.dialog_saved_fmt).format(path=path) if path else tr_now(tr.system.dialog_cancelled)
    )


async def on_dialog_folder(_event: DomEvent) -> None:
    path = await app.select_folder(title=tr_now(tr.system.dialog_open_title))
    dialog_state.set(
        tr_now(tr.system.dialog_folder_fmt).format(path=path) if path else tr_now(tr.system.dialog_cancelled)
    )


dialog_open_btn.on_click(on_dialog_open)
dialog_many_btn.on_click(on_dialog_many)
dialog_save_btn.on_click(on_dialog_save)
dialog_folder_btn.on_click(on_dialog_folder)

dialogs_panel = Section(
    tr.system.dialogs_title,
    tr.system.dialogs_blurb,
    """path = await app.open_file(title="Open",
        filetypes=[("PNG images", "*.png")])   # None on cancel
paths = await app.open_files(...)              # [] on cancel
await app.save_file(default_name="out.txt")    # str | None
await app.select_folder()                      # str | None
# The platform's own dialog — zenity / osascript / PowerShell.""",
    HStack(dialog_open_btn, dialog_many_btn, dialog_save_btn, dialog_folder_btn, gap="8px"),
    dialog_echo,
)

PANELS = {
    "animations": animations_panel,
    "reactive": reactive_panel,
    "sidebar": sidebar_panel,
    "tabs": tabs_panel,
    "window": window_panel,
    "dialogs": dialogs_panel,
}

# ── page wiring ──────────────────────────────────────────────────


def _wire_lifecycle(page: Page) -> None:
    # Page-level lifecycle hooks drive the Window tab status line.
    page.on_focus(on_page_focus).on_blur(on_page_blur)


async def on_page_focus() -> None:
    win_state.set(tr_now(tr.system.window_focused))


async def on_page_blur() -> None:
    win_state.set(tr_now(tr.system.window_lost_focus))


PAGE_HOOKS: list[Callable[[Page], None]] = [_wire_lifecycle]
