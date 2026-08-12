"""Gallery translation catalog — one sub-model per section, plus shell/nav.

Each field is a :class:`~neony.application.TrRef`; ``tr.nav.home`` returns
one that re-resolves on language change.  ZH ships fully translated as the
demo language; any other registered language falls back to English per the
framework resolver.

Reserved key names: a field named ``get`` / ``format`` or with a leading
``_`` is shadowed by the ``Computed`` API and unreachable through ``tr``.
All interpolated templates use named placeholders (``{value}``, ``{n}``)
so a translator may reorder them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from neony.application import Catalog, Language, register_catalog
from neony.application.i18n import Common, TrRef, tr_now

__all__ = ["GalleryCatalog", "Language", "register_catalog", "tr", "tr_now"]

_CFG = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)


class Shell(BaseModel):
    model_config = _CFG
    window_title: TrRef[None] = TrRef("Neony — Component Gallery")
    titlebar: TrRef[None] = TrRef("Neony — Component Gallery")
    h1: TrRef[None] = TrRef("Neony Component Gallery")
    tagline: TrRef[None] = TrRef("Every component, one page — with docs and code samples")
    light_mode: TrRef[None] = TrRef("Light mode")
    dark_mode: TrRef[None] = TrRef("Dark mode")
    deep_blue_mode: TrRef[None] = TrRef("Deep Blue mode")
    language: TrRef[None] = TrRef("Language")


class Nav(BaseModel):
    model_config = _CFG
    home: TrRef[None] = TrRef("Home")
    buttons: TrRef[None] = TrRef("Buttons")
    inputs_forms: TrRef[None] = TrRef("Inputs & Forms")
    inputs: TrRef[None] = TrRef("Inputs")
    checks: TrRef[None] = TrRef("Checks")
    forms: TrRef[None] = TrRef("Forms")
    layout_type: TrRef[None] = TrRef("Layout & Type")
    layout: TrRef[None] = TrRef("Layout")
    type: TrRef[None] = TrRef("Type")
    glass_content: TrRef[None] = TrRef("Glass & Content")
    glass: TrRef[None] = TrRef("Glass")
    content: TrRef[None] = TrRef("Content")
    icon: TrRef[None] = TrRef("Icon")
    interaction: TrRef[None] = TrRef("Interaction & Events")
    events: TrRef[None] = TrRef("Events")
    drop: TrRef[None] = TrRef("Drop")
    clipboard: TrRef[None] = TrRef("Clipboard")
    shortcuts: TrRef[None] = TrRef("Shortcuts")
    overlays: TrRef[None] = TrRef("Overlays")
    data_views: TrRef[None] = TrRef("Data views")
    list: TrRef[None] = TrRef("List")
    datatable: TrRef[None] = TrRef("DataTable")
    notify_chat: TrRef[None] = TrRef("Notifications & Chat")
    notifications: TrRef[None] = TrRef("Notifications")
    chat: TrRef[None] = TrRef("Chat")
    system: TrRef[None] = TrRef("System & Advanced")
    animations: TrRef[None] = TrRef("Animations")
    reactive: TrRef[None] = TrRef("Reactive")
    sidebar: TrRef[None] = TrRef("Sidebar")
    tabs: TrRef[None] = TrRef("Tabs")
    window: TrRef[None] = TrRef("Window")


class Home(BaseModel):
    model_config = _CFG
    heading: TrRef[None] = TrRef("Welcome")
    body: TrRef[None] = TrRef(
        "This gallery is organized as a tree: pick a category on the "
        "left, expand it, and select a component to see its docs and "
        "live demos here. Every section pairs a demo with the Python "
        "snippet that produced it, so the gallery doubles as a reference."
    )


class Buttons(BaseModel):
    model_config = _CFG
    section_title: TrRef[None] = TrRef("Buttons")
    section_blurb: TrRef[None] = TrRef(
        "Three variants (primary, ghost, danger) with hover / press feedback "
        "and colour-matched glows — hover lifts with a halo in the variant's "
        "own colour, focus draws a tinted ring. reset_styles() replaces the "
        "base look while keeping the feedback. The counter holds its state "
        "in a Signal — the click only bumps it, bind_text redraws the label."
    )
    primary: TrRef[None] = TrRef("Primary Action")
    ghost: TrRef[None] = TrRef("Ghost Button")
    danger: TrRef[None] = TrRef("Delete")
    disabled: TrRef[None] = TrRef("Disabled")
    custom: TrRef[None] = TrRef("Custom")
    click_me: TrRef[None] = TrRef("Click me")
    clicks_fmt: TrRef[dict[str, object]] = TrRef("{n} clicks")


class Forms(BaseModel):
    model_config = _CFG
    inputs_title: TrRef[None] = TrRef("Inputs")
    inputs_blurb: TrRef[None] = TrRef(
        "Text, password and email fields. Each input binds its value to a "
        "Signal and each echo binds declaratively to that Signal with a "
        "formatting function."
    )
    name_placeholder: TrRef[None] = TrRef("Your name…")
    password_placeholder: TrRef[None] = TrRef("Password")
    email_placeholder: TrRef[None] = TrRef("Email")
    hello_fmt: TrRef[dict[str, object]] = TrRef("Hello, {value}!")
    length_fmt: TrRef[dict[str, object]] = TrRef("Length: {value}")
    email_fmt: TrRef[dict[str, object]] = TrRef("Email: {value}")
    checks_title: TrRef[None] = TrRef("Checkboxes")
    checks_blurb: TrRef[None] = TrRef(
        "Custom-styled toggles with a change event. Signals are the single "
        "source of truth: each food checkbox is bound two-way via bind_value, "
        '"Select all" is a Computed bound read-only, and the status line is '
        "a bound text — nothing refreshes by hand."
    )
    select_all: TrRef[None] = TrRef("Select all")
    pizza: TrRef[None] = TrRef("Pizza")
    tacos: TrRef[None] = TrRef("Tacos")
    ramen: TrRef[None] = TrRef("Ramen")
    selected_count_fmt: TrRef[dict[str, object]] = TrRef("{n} of {total} selected")
    forms_title: TrRef[None] = TrRef("Forms")
    forms_blurb: TrRef[None] = TrRef(
        "Radio groups, switches, dropdowns, combo boxes, sliders and "
        "progress bars. State is owned by the component: programmatic "
        "writes never fire callbacks, user-driven events carry "
        'source == "user". Sliders draw their own fill track; step="any" '
        "makes one stepless. The volume slider, its readout and a progress "
        "bar all share one Signal via bind_value — drag and watch the "
        "others follow. The heat readout at the bottom follows the Reactive "
        "tab's shared signal."
    )
    picked_fmt: TrRef[dict[str, object]] = TrRef("Picked: {value}")
    wifi: TrRef[None] = TrRef("Wi-Fi")
    on: TrRef[None] = TrRef("On")
    off: TrRef[None] = TrRef("Off")
    size: TrRef[None] = TrRef("Size")
    small: TrRef[None] = TrRef("Small")
    medium: TrRef[None] = TrRef("Medium")
    large: TrRef[None] = TrRef("Large")
    pick_size_placeholder: TrRef[None] = TrRef("Pick a size…")
    selected_fmt: TrRef[dict[str, object]] = TrRef("Selected: {value}")
    tag: TrRef[None] = TrRef("Tag")
    tag_placeholder: TrRef[None] = TrRef("Type or pick…")
    tag_fmt: TrRef[dict[str, object]] = TrRef("Tag: {value}")
    volume_stepped: TrRef[None] = TrRef("Volume (stepped)")
    volume_continuous: TrRef[None] = TrRef("Volume (continuous)")
    progress_follows: TrRef[None] = TrRef("The progress bar follows the same signal")
    downloading: TrRef[None] = TrRef("Downloading…")
    scanning: TrRef[None] = TrRef("Scanning…")
    advance: TrRef[None] = TrRef("+15%")
    shared_heat_fmt: TrRef[dict[str, object]] = TrRef("shared heat signal (from the Reactive tab): {n}%")


class Layout(BaseModel):
    model_config = _CFG
    layout_title: TrRef[None] = TrRef("Layout")
    layout_blurb: TrRef[None] = TrRef(
        "HStack rows with Spacer pushing content; Flex gives full control, "
        "including wrapping. VStack stacks vertically, Separator divides, "
        "GlassPanel frosts."
    )
    title: TrRef[None] = TrRef("Title")
    edit: TrRef[None] = TrRef("Edit")
    item_fmt: TrRef[dict[str, object]] = TrRef("Item {i}")
    frosted: TrRef[None] = TrRef("Frosted")
    type_title: TrRef[None] = TrRef("Typography")
    type_blurb: TrRef[None] = TrRef(
        "Six heading levels plus semantic text roles that follow the theme. "
        "user_select controls text selection: the first row below cannot be "
        "highlighted, the second can."
    )
    locked_copy: TrRef[None] = TrRef("Locked copy — user_select='none' blocks selection.")
    heading_n: TrRef[None] = TrRef("Heading {n}")
    primary_text: TrRef[None] = TrRef("Primary text — the default body copy.")
    secondary_text: TrRef[None] = TrRef("Secondary text — muted, less important.")
    danger_text: TrRef[None] = TrRef("Danger text — errors and destructive emphasis.")
    success_text: TrRef[None] = TrRef("Success text — confirmations.")
    selectable_copy: TrRef[None] = TrRef("Selectable copy — the normal default.")


class Glass(BaseModel):
    model_config = _CFG
    glass_title: TrRef[None] = TrRef("Frosted Glass")
    glass_blurb: TrRef[None] = TrRef(
        "GlassPanel blurs the background image; components with glass=True "
        "keep their theme colours while gaining the frosted surface. A "
        "semantic role tints the panel's border AND its outer glow; "
        "per-corner radii join chrome at any angle."
    )
    input_placeholder: TrRef[None] = TrRef("Glass input…")
    typed_fmt: TrRef[dict[str, object]] = TrRef("Typed: {value}")
    frosted_stage: TrRef[None] = TrRef("Frosted Stage")
    stage_desc: TrRef[None] = TrRef("Components inside keep their theme colours while gaining the frosted look.")
    primary: TrRef[None] = TrRef("Primary")
    ghost: TrRef[None] = TrRef("Ghost")
    danger: TrRef[None] = TrRef("Danger")
    glass_checkbox: TrRef[None] = TrRef("Glass checkbox")
    success_glow: TrRef[None] = TrRef("Success — role glows follow the theme")
    danger_emphasis: TrRef[None] = TrRef("Danger — destructive emphasis")
    corners_desc: TrRef[None] = TrRef("Per-corner radii — 24px / 4px / 24px / 4px")
    icon_title: TrRef[None] = TrRef("Window Icon")
    icon_blurb: TrRef[None] = TrRef(
        "Frameless windows show the icon inline in the TitleBar; decorated "
        "windows hand it to the OS window chrome via WindowConfig.icon — "
        "both take the same URL or file path. file_url() / data_url() turn "
        "local files into URL strings for icons, backgrounds and images."
    )
    icon_live: TrRef[None] = TrRef("Live: the favicon in the titlebar above uses TitleBar(icon=...).")
    icon_decorated: TrRef[None] = TrRef(
        "For decorated windows the taskbar / titlebar icon comes from "
        "WindowConfig.icon; TitleBar(icon=...) only affects frameless chrome."
    )
    content_title: TrRef[None] = TrRef("Content")
    content_blurb: TrRef[None] = TrRef(
        "Display components — Image, Avatar, Badge, and Card. Pure presentation; "
        "they reuse the theme tokens so they redraw on theme switch."
    )
    image_heading: TrRef[None] = TrRef("Image")
    avatar_heading: TrRef[None] = TrRef("Avatar")
    badge_heading: TrRef[None] = TrRef("Badge")
    card_heading: TrRef[None] = TrRef("Card")
    image_alt: TrRef[None] = TrRef("Neony icon")
    image_alt_round: TrRef[None] = TrRef("round")
    av_name: TrRef[None] = TrRef("Neony")
    av_ada: TrRef[None] = TrRef("Elysia")
    av_inbox: TrRef[None] = TrRef("Inbox")
    badge_new: TrRef[None] = TrRef("New")
    badge_verified: TrRef[None] = TrRef("verified")
    badge_plain: TrRef[None] = TrRef("plain")
    inline_pills: TrRef[None] = TrRef("Inline pills:")
    counts_desc: TrRef[None] = TrRef("Counts (150 → 99+, 0 hidden unless show_zero):")
    card_body: TrRef[None] = TrRef("The body holds any children — text, components, or raw nodes.")
    plain_card_title: TrRef[None] = TrRef("Plain card")
    plain_card_subtitle: TrRef[None] = TrRef("A solid surface with a soft shadow")
    edit: TrRef[None] = TrRef("Edit")
    card_clicked: TrRef[None] = TrRef("Card clicked.")
    glass_card_body: TrRef[None] = TrRef("Frosted glass tinted by role — the accent glow follows the theme.")
    glass_card_title: TrRef[None] = TrRef("Glass card")
    glass_card_subtitle: TrRef[None] = TrRef("role='accent'")


class Interaction(BaseModel):
    model_config = _CFG
    events_title: TrRef[None] = TrRef("Rich Events")
    events_blurb: TrRef[None] = TrRef(
        "Every delegated event carries the full payload: modifier keys "
        "(ctrl/shift/alt/meta), viewport and element-relative mouse "
        "coordinates, wheel deltas, and pointer movement — live delta and "
        "device type. Click the box, hold modifiers while typing, scroll "
        "the zone, move the pointer across the bottom box."
    )
    click_anywhere: TrRef[None] = TrRef("Click anywhere in this box")
    mod_placeholder: TrRef[None] = TrRef("Type anywhere — the lights follow the modifiers…")
    meta_reserved: TrRef[None] = TrRef(
        "Meta (Super) is often reserved by the window manager on Linux — "
        "hyprland grabs it for its own bindings, so it may never reach "
        "the page. The other three modifiers always arrive."
    )
    wheel_tall: TrRef[None] = TrRef("Tall content so the zone scrolls…")
    wheel_keep: TrRef[None] = TrRef("Keep scrolling to see live deltas.")
    drop_title: TrRef[None] = TrRef("File Drop")
    drop_blurb: TrRef[None] = TrRef(
        "Drag files from the file manager into the dashed zone. The drop "
        "event carries each file's name, local filesystem path, size and "
        "MIME type. On WebKitGTK the webview reports empty files, so Neony "
        "takes the drop over at the native layer, hit-tests the position, "
        "and re-dispatches the drop event with the real paths; on WebView2 "
        "File.path arrives directly, on WKWebView it is empty. "
        "dragover/dragleave/drop are all delegated, and the browser's "
        "navigate-on-drop default is prevented for you."
    )
    drop_hint: TrRef[None] = TrRef("Drop files anywhere in this box")
    drop_release: TrRef[None] = TrRef("Release to drop")
    no_files: TrRef[None] = TrRef("(no files — on WKWebView the file path is empty)")
    path_unavailable: TrRef[None] = TrRef("<unavailable>")
    clipboard_title: TrRef[None] = TrRef("Clipboard")
    clipboard_blurb: TrRef[None] = TrRef(
        "Clipboard events carry data into Python: paste delivers "
        "clipboard_text / clipboard_html, copy / cut fire as notifications. "
        "The write/read API lives in the backend (no user gesture needed to "
        "write); read still needs the window focused."
    )
    paste_placeholder: TrRef[None] = TrRef("Paste (Ctrl+V) into this field…")
    clip_not_exposed: TrRef[None] = TrRef("clipboard_text: <not exposed by this backend>")
    clip_text_fmt: TrRef[dict[str, object]] = TrRef("clipboard_text: {value!r}")
    clip_text_html_fmt: TrRef[dict[str, object]] = TrRef("  html: {html!r}")
    clip_paste_event: TrRef[None] = TrRef("paste event — clipboard carried into Python")
    clip_copy_event: TrRef[None] = TrRef("copy event (user pressed Ctrl+C)")
    clip_cut_event: TrRef[None] = TrRef("cut event (user pressed Ctrl+X)")
    clip_input_fmt: TrRef[dict[str, object]] = TrRef("input value: {value!r}")
    copy_sample: TrRef[None] = TrRef("Copy sample text")
    read_clipboard: TrRef[None] = TrRef("Read clipboard")
    wrote_sample: TrRef[None] = TrRef("Neony wrote this from Python!")
    write_failed_fmt: TrRef[dict[str, object]] = TrRef("write failed: {exc}")
    write_failed_log_fmt: TrRef[dict[str, object]] = TrRef("clipboard_write() failed: {exc}")
    wrote_fmt: TrRef[dict[str, object]] = TrRef("wrote {text!r}")
    read_failed_fmt: TrRef[dict[str, object]] = TrRef("read failed: {exc}")
    read_failed_log_fmt: TrRef[dict[str, object]] = TrRef("clipboard_read() failed: {exc}")
    read_fmt: TrRef[dict[str, object]] = TrRef("read: {text!r}")
    shortcuts_title: TrRef[None] = TrRef("Shortcuts")
    shortcuts_blurb: TrRef[None] = TrRef(
        "Page-level keybindings that fire anywhere in the window — even "
        "while an input has focus, and on any tab. Register a single "
        "combo or a per-platform dict (Ctrl+Meta on macOS vs Ctrl on "
        "Linux/Windows). Modifiers must match exactly; the key matches "
        "case-insensitively. Try them from here or any other tab:"
    )
    ctrl_b: TrRef[None] = TrRef("Ctrl+B — bold")
    ctrl_g: TrRef[None] = TrRef("Ctrl+G — glow")
    ctrl_d: TrRef[None] = TrRef("Ctrl+D — dark")
    ctrl_k: TrRef[None] = TrRef("Ctrl+K (Meta+K on macOS) — theme")
    overlays_title: TrRef[None] = TrRef("Overlays")
    overlays_blurb: TrRef[None] = TrRef(
        "Four positioned layers — all CSS-anchored, zero measurement. "
        "Dialog dims the whole page with a themed scrim and centers a "
        "panel with configurable action buttons (scrim / Escape / "
        "click-away close); Tooltip wraps its anchor with placement "
        "offsets and a hover delay; Dropdown reuses the popup pattern "
        "(outsideclick close, full keyboard nav); Menu is fixed at the "
        "cursor via open_at() — right-click the button."
    )
    dialog_title: TrRef[None] = TrRef("Confirm")
    dialog_label: TrRef[None] = TrRef("Dialog")
    prompt_label: TrRef[None] = TrRef("PromptDialog")
    dropdown_label: TrRef[None] = TrRef("Dropdown")
    dialog_body: TrRef[None] = TrRef("Try the scrim, Escape, click-away, or the buttons below.")
    dialog_confirm: TrRef[None] = TrRef("Confirm")
    dialog_cancel: TrRef[None] = TrRef("Cancel")
    dialog_close: TrRef[None] = TrRef("Close")
    dialog_open_btn: TrRef[None] = TrRef("Open dialog")
    dialog_open_state: TrRef[None] = TrRef("open — waiting for a choice")
    dialog_chose_fmt: TrRef[dict[str, object]] = TrRef("closed — chose {value!r}")
    dialog_dismiss: TrRef[None] = TrRef("closed — dismissed (scrim / Escape / click-away)")
    tooltip_top: TrRef[None] = TrRef("Tooltip on top")
    hover_top: TrRef[None] = TrRef("Hover (top)")
    tooltip_bottom: TrRef[None] = TrRef("Tooltip below")
    hover_bottom: TrRef[None] = TrRef("Hover (bottom)")
    theme_label: TrRef[None] = TrRef("Theme")
    dark: TrRef[None] = TrRef("Dark")
    light: TrRef[None] = TrRef("Light")
    deep_blue: TrRef[None] = TrRef("Deep Blue")
    dropdown_fmt: TrRef[dict[str, object]] = TrRef("Dropdown: {value}")
    rename: TrRef[None] = TrRef("Rename")
    duplicate: TrRef[None] = TrRef("Duplicate")
    delete: TrRef[None] = TrRef("Delete")
    menu_fmt: TrRef[dict[str, object]] = TrRef("Menu: {value}")
    right_click: TrRef[None] = TrRef("Right-click me")
    prompt_question: TrRef[None] = TrRef("What's your name?")
    identify: TrRef[None] = TrRef("Identify")
    name_placeholder: TrRef[None] = TrRef("Hiro…")
    prompt_open_btn: TrRef[None] = TrRef("Ask a name")
    prompt_open_state: TrRef[None] = TrRef("open")
    prompt_closed_state: TrRef[None] = TrRef("closed")
    prompt_submitted_fmt: TrRef[dict[str, object]] = TrRef("submitted: {value!r}")


class Data(BaseModel):
    model_config = _CFG
    list_title: TrRef[None] = TrRef("List")
    list_blurb: TrRef[None] = TrRef(
        "A scrollable, single-select data list — the listbox model. Arrow "
        "keys move the selection directly (each move fires change), Home/End "
        "jump to the ends, Enter/Space select, and a click selects. The "
        "selection is two-way reactive via bind_selected — user clicks write "
        "the signal, and programmatic selected_key writes mirror into it."
    )
    apple: TrRef[None] = TrRef("Apple")
    banana: TrRef[None] = TrRef("Banana")
    cherry: TrRef[None] = TrRef("Cherry")
    durian: TrRef[None] = TrRef("Durian")
    elderberry: TrRef[None] = TrRef("Elderberry")
    select_durian: TrRef[None] = TrRef("Select 'Durian'")
    selected_fmt: TrRef[dict[str, object]] = TrRef("selected: {key}")
    table_title: TrRef[None] = TrRef("DataTable")
    table_blurb: TrRef[None] = TrRef(
        "Column config + data rows with a sticky header, click-to-sort "
        "columns, and row selection. Columns lay out with CSS grid "
        "(width tracks like '2fr' / '80px'), the header sticks while the "
        "body scrolls, and sorting is numeric-aware (or via a per-column "
        "sort_key). Selection is single by default or multi at construction."
    )
    name: TrRef[None] = TrRef("Name")
    role: TrRef[None] = TrRef("Role")
    age: TrRef[None] = TrRef("Age")
    score: TrRef[None] = TrRef("Score")
    kiana: TrRef[None] = TrRef("Kiana")
    mei: TrRef[None] = TrRef("Mei")
    bronya: TrRef[None] = TrRef("Bronya")
    elysia: TrRef[None] = TrRef("Elysia")
    eden: TrRef[None] = TrRef("Eden")
    sort_by_age: TrRef[None] = TrRef("Sort by age ↓")
    kiana_role: TrRef[None] = TrRef("Herrscher of Flamescion")
    mei_role: TrRef[None] = TrRef("Herrscher of Thunder")
    bronya_role: TrRef[None] = TrRef("Herrscher of Reason")
    elysia_role: TrRef[None] = TrRef("Miss Pink Elf♪")
    eden_role: TrRef[None] = TrRef("Golden Diva")
    service: TrRef[None] = TrRef("Service")
    status: TrRef[None] = TrRef("Status")
    ok: TrRef[None] = TrRef("ok")
    degraded: TrRef[None] = TrRef("degraded")
    selected_none: TrRef[None] = TrRef("none")


class Chat(BaseModel):
    model_config = _CFG
    notifications_title: TrRef[None] = TrRef("Notifications")
    notifications_blurb: TrRef[None] = TrRef(
        "Transient in-app notifications stacked at a screen edge. The host "
        "sits at the page root as a full-viewport layer (z-index 1100, "
        "pointer-events none); cards enter and leave with an animation "
        "tied to their placement — top ones drop in, bottom ones rise up, "
        "corners slide diagonally — and auto-dismiss after `duration`. "
        "A card is clickable when `on_click` is passed (the ✕ never fires it)."
    )
    placement: TrRef[None] = TrRef("Placement")
    toast_saved: TrRef[None] = TrRef("File saved successfully")
    toast_clicked: TrRef[None] = TrRef("toast clicked")
    toast_success: TrRef[None] = TrRef("Success")
    toast_info: TrRef[None] = TrRef("Info")
    toast_error: TrRef[None] = TrRef("Error")
    toast_update: TrRef[None] = TrRef("Update available")
    toast_connection: TrRef[None] = TrRef("Connection lost — retrying…")
    toast_clear: TrRef[None] = TrRef("Clear")
    chat_title: TrRef[None] = TrRef("Chat")
    chat_blurb: TrRef[None] = TrRef(
        "QQ/Telegram-style message bubbles and the centered system notice. "
        "`from_me` flips alignment (right, accent fill) vs. others (left, "
        "raised surface); an optional avatar sits on the message's side. "
        "Right-click a bubble for its built-in menu, hover it for quick "
        "actions."
    )
    other_msg: TrRef[None] = TrRef("Hey! Have you seen the new gallery?")
    me_msg: TrRef[None] = TrRef("Just shipped it — three new components.")
    # ``copy`` is a reserved pydantic v1 name (shadows BaseModel.copy) —
    # the key is ``copy_text`` but the resolved label stays "Copy".
    copy_text: TrRef[None] = TrRef("Copy")
    you_joined: TrRef[None] = TrRef("You joined the group")
    menu_fmt: TrRef[dict[str, object]] = TrRef("menu: {value}")
    action_fmt: TrRef[dict[str, object]] = TrRef("action: {value}")
    right_click_hint: TrRef[None] = TrRef("Right-click a bubble for its menu; hover for quick actions.")


class System(BaseModel):
    model_config = _CFG
    animations_title: TrRef[None] = TrRef("Animations")
    animations_blurb: TrRef[None] = TrRef(
        "Typed @keyframes: build a KeyFrame with the chainable .set() "
        "builder, register it once, and reference it from any element's "
        "Animation model — multi-stop, named, and injected into a global "
        "<style> like the theme. The spinner loops forever; the card plays "
        "a one-shot fade-slide on mount. Pause/resume toggles play-state."
    )
    paused: TrRef[None] = TrRef("paused")
    running: TrRef[None] = TrRef("running")
    pause: TrRef[None] = TrRef("Pause")
    fades_slides: TrRef[None] = TrRef("Fades + slides in on mount")
    reactive_title: TrRef[None] = TrRef("Reactive")
    heat_bar: TrRef[None] = TrRef("Heat bar")
    effect: TrRef[None] = TrRef("Effect")
    batch: TrRef[None] = TrRef("batch()")
    untrack: TrRef[None] = TrRef("untrack()")
    bind_attr: TrRef[None] = TrRef("bind_attr")
    computed_chain: TrRef[None] = TrRef("Computed chain")
    reactive_blurb: TrRef[None] = TrRef(
        "Signal, Computed and Effect with declarative bindings — no manual "
        "refresh calls. bind_text / bind_style / bind_visible / bind_attr "
        "/ bind_value follow their signal; batch() coalesces writes into "
        "one flush, untrack() reads without subscribing, computed chains "
        "compose. The heat bar is shared across tabs — bump it here, watch "
        "the Forms tab."
    )
    heat_fmt: TrRef[dict[str, object]] = TrRef("heat: {n}%")
    first_name: TrRef[None] = TrRef("First name")
    last_name: TrRef[None] = TrRef("Last name")
    computed_full_fmt: TrRef[dict[str, object]] = TrRef("Computed full name: {v}")
    type_both: TrRef[None] = TrRef("Type both names…")
    effect_fired_fmt: TrRef[dict[str, object]] = TrRef("Effect fired — level = {n}")
    effect_running: TrRef[None] = TrRef("effect: running")
    effect_disposed: TrRef[None] = TrRef("effect: disposed — level changes no longer sync")
    dispose_effect: TrRef[None] = TrRef("Dispose effect")
    restart_effect: TrRef[None] = TrRef("Restart effect")
    level_plus: TrRef[None] = TrRef("Level +5")
    level_minus: TrRef[None] = TrRef("Level -5")
    secret_desc: TrRef[None] = TrRef("This box's display is bound to a Signal.")
    visible: TrRef[None] = TrRef("Visible")
    effect_runs_fmt: TrRef[dict[str, object]] = TrRef("effect runs: {runs}  (a={a}, b={b})")
    a_plus_1: TrRef[None] = TrRef("a + 1")
    batch_both: TrRef[None] = TrRef("a + 1, b + 1 inside batch()")
    tracked_plus: TrRef[None] = TrRef("tracked + 1")
    ignored_plus: TrRef[None] = TrRef("ignored + 1 (untracked — no re-run)")
    untrack_runs_fmt: TrRef[dict[str, object]] = TrRef(
        "effect runs: {runs}  (tracked={tracked}, {ignored} read via untrack — no subscription)"
    )
    untrack_ignored: TrRef[None] = TrRef("ignored={n}")
    busy_state: TrRef[None] = TrRef("busy: false — the disabled attribute follows the signal")
    busy_fmt: TrRef[dict[str, object]] = TrRef("busy: {b} — disabled={flag}set on the button")
    toggle_busy: TrRef[None] = TrRef("Toggle busy")
    price_plus: TrRef[None] = TrRef("price +1")
    price_minus: TrRef[None] = TrRef("price -1")
    qty_plus: TrRef[None] = TrRef("qty +1")
    qty_minus: TrRef[None] = TrRef("qty -1")
    rate_plus: TrRef[None] = TrRef("rate +0.1")
    rate_minus: TrRef[None] = TrRef("rate -0.1")
    total_fmt: TrRef[dict[str, object]] = TrRef("total: ¥{v:.2f}   (subtotal ¥{s:.2f} x rate {r:.1f})")
    bind_placeholder: TrRef[None] = TrRef("Type — the signal follows every keystroke…")
    echo_fmt: TrRef[dict[str, object]] = TrRef("echo {n}: {v}")
    set_signal: TrRef[None] = TrRef("Set signal → component")
    written_signal: TrRef[None] = TrRef("written from the signal side")
    sidebar_title: TrRef[None] = TrRef("Sidebar")
    save: TrRef[None] = TrRef("Save")
    sidebar_blurb: TrRef[None] = TrRef(
        "A Sidebar can own its content panes. Pane keys are explicit, "
        "selected state binds to a Signal, and clicking an item switches "
        "the mounted pane without a hand-written mapping or switch function."
    )
    home: TrRef[None] = TrRef("Home")
    settings: TrRef[None] = TrRef("Settings")
    profile: TrRef[None] = TrRef("Profile")
    home_content: TrRef[None] = TrRef("Home content — the Sidebar owns this pane.")
    settings_content: TrRef[None] = TrRef("Settings content — select another entry to switch panes.")
    profile_content: TrRef[None] = TrRef("Profile content — pane state remains mounted while hidden.")
    active_fmt: TrRef[dict[str, object]] = TrRef("active: {key}")
    tabs_title: TrRef[None] = TrRef("Tabs")
    tabs_blurb: TrRef[None] = TrRef(
        "Tabs own their content panes — pane state survives switches because "
        "the DOM stays mounted. Selection binds to a Signal (like Sidebar). "
        "When tabs overflow the bar they scroll horizontally with an edge-fade "
        "hint rather than wrapping; arrow keys rotate, Enter/Space activates."
    )
    pane_a: TrRef[None] = TrRef("Pane A")
    pane_b: TrRef[None] = TrRef("Pane B")
    pane_c: TrRef[None] = TrRef("Pane C")
    first_pane: TrRef[None] = TrRef("First pane — Tabs owns its panels.")
    second_pane: TrRef[None] = TrRef("Second pane — state stays mounted while hidden.")
    third_pane: TrRef[None] = TrRef("Third pane.")
    section_fmt: TrRef[dict[str, object]] = TrRef("Section {c}")
    panel_fmt: TrRef[dict[str, object]] = TrRef("Panel {c} content.")
    tab_selected_fmt: TrRef[dict[str, object]] = TrRef("selected: {key}")
    window_title: TrRef[None] = TrRef("Window State")
    window_blurb: TrRef[None] = TrRef(
        "show / hide / focus move the window on screen; set_bounds positions "
        "it via tao (outer position) and resizes it. The status line also "
        "tracks the page's on_focus / on_blur lifecycle hooks (not emitted "
        "on every stack — Wayland/GTK focus events are backend-dependent)."
    )
    window_state: TrRef[None] = TrRef("Window state")
    hide_note: TrRef[None] = TrRef(
        "Hide auto-restores after 2s (the Show button lives inside the window, so a permanent hide would trap you). "
    )
    wayland_note: TrRef[None] = TrRef(
        "On Wayland window position is a no-op (the protocol forbids "
        "client-side positioning). Resize is a request: tiling WMs ignore "
        "it while the window is tiled — float the window (e.g. Win+F) "
        "for set_bounds/set_size to apply."
    )
    pos_note: TrRef[None] = TrRef("Position is in logical pixels from the top-left of the screen.")
    hide: TrRef[None] = TrRef("Hide")
    show: TrRef[None] = TrRef("Show")
    focus: TrRef[None] = TrRef("Focus")
    compact_pos: TrRef[None] = TrRef("Compact @ (100, 100)")
    default_pos: TrRef[None] = TrRef("Default @ (0, 0)")
    window_hidden: TrRef[None] = TrRef("Window hidden — auto-restoring in 2s…")
    window_shown_restore: TrRef[None] = TrRef("Window shown again (auto-restore)")
    window_shown: TrRef[None] = TrRef("Window shown")
    window_focused: TrRef[None] = TrRef("Window focused")
    set_bounds_fmt: TrRef[dict[str, object]] = TrRef("set_bounds({x}, {y}, {w}, {h}) applied")
    window_lost_focus: TrRef[None] = TrRef("Window lost focus (or hidden)")


class GalleryCatalog(Catalog):
    shell: Shell = Shell()
    nav: Nav = Nav()
    home: Home = Home()
    buttons: Buttons = Buttons()
    forms: Forms = Forms()
    layout: Layout = Layout()
    glass: Glass = Glass()
    interaction: Interaction = Interaction()
    data: Data = Data()
    chat: Chat = Chat()
    system: System = System()


#: Gallery-wide typed ``tr`` — ``tr.nav.home`` returns a reactive ``TrRef``.
tr: GalleryCatalog = GalleryCatalog()

register_catalog(Language.EN, GalleryCatalog())
register_catalog(
    Language.ZH,
    GalleryCatalog(
        common=Common(
            copy_text="复制",
            delete="删除",
            ok="确定",
            cancel="取消",
            close="关闭",
        ),
        shell=Shell(
            window_title="Neony — 组件画廊",
            titlebar="Neony — 组件画廊",
            h1="Neony 组件画廊",
            tagline="每个组件，同一页面——附带文档与代码示例",
            light_mode="浅色模式",
            dark_mode="深色模式",
            deep_blue_mode="深蓝模式",
            language="语言",
        ),
        nav=Nav(
            home="首页",
            buttons="按钮",
            inputs_forms="输入与表单",
            inputs="输入框",
            checks="复选框",
            forms="表单",
            layout_type="布局与排版",
            layout="布局",
            type="排版",
            glass_content="玻璃与内容",
            glass="玻璃",
            content="内容",
            icon="窗口图标",
            interaction="交互与事件",
            events="事件",
            drop="文件拖放",
            clipboard="剪贴板",
            shortcuts="快捷键",
            overlays="Overlays",
            data_views="数据视图",
            list="列表",
            datatable="数据表",
            notify_chat="通知与聊天",
            notifications="通知",
            chat="聊天",
            system="系统与高级",
            animations="动画",
            reactive="响应式",
            sidebar="侧边栏",
            tabs="标签页",
            window="窗口",
        ),
        home=Home(
            heading="欢迎",
            body=(
                "本画廊以树形结构组织：从左侧选择一个分类，展开它，再点选一个组件，"
                "即可在此查看它的文档和实时演示。每个小节都把一个演示与生成它的 Python "
                "代码片段配对，因此这个画廊本身就是一份参考手册。"
            ),
        ),
        buttons=Buttons(
            section_title="按钮",
            section_blurb=(
                "三种变体（primary、ghost、danger）带悬停/按下反馈和颜色匹配的辉光——"
                "悬停时以变体自身的颜色抬升出光晕，聚焦时绘制一圈着色光环。reset_styles() "
                "在保留反馈的前提下替换基础外观。计数器把状态保存在 Signal 里——点击只递增它，"
                "bind_text 负责重绘标签。"
            ),
            primary="主要操作",
            ghost="幽灵按钮",
            danger="删除",
            disabled="已禁用",
            custom="自定义",
            click_me="点我",
            clicks_fmt="{n} 次点击",
        ),
        forms=Forms(
            inputs_title="输入框",
            inputs_blurb=(
                "文本、密码和邮箱字段。每个输入框把值绑定到 Signal，每个回显用格式化函数声明式地绑定到同一个 Signal。"
            ),
            name_placeholder="你的名字…",
            password_placeholder="密码",
            email_placeholder="邮箱",
            hello_fmt="你好，{value}！",
            length_fmt="长度：{value}",
            email_fmt="邮箱：{value}",
            checks_title="复选框",
            checks_blurb=(
                "带 change 事件的自定义开关。Signal 是唯一数据源：每个食物复选框通过 "
                "bind_value 双向绑定，「全选」是一个只读绑定的 Computed，状态行是绑定的文本——"
                "无需手动刷新。"
            ),
            select_all="全选",
            pizza="披萨",
            tacos="塔可",
            ramen="拉面",
            selected_count_fmt="已选 {n} / {total} 项",
            forms_title="表单",
            forms_blurb=(
                "单选组、开关、下拉框、组合框、滑块和进度条。状态由组件持有：程序化写入绝不"
                '触发回调，用户事件携带 source == "user"。滑块自己绘制填充轨道；step="any" '
                "让一个滑块无级连续。音量滑块、它的读数和一个进度条通过 bind_value 共享同一个 "
                "Signal——拖动一下就能看到它们一起变化。底部的 heat 读数跟随响应式标签页的共享信号。"
            ),
            picked_fmt="已选：{value}",
            wifi="无线网",
            on="开",
            off="关",
            size="尺寸",
            small="小",
            medium="中",
            large="大",
            pick_size_placeholder="挑选一个尺寸…",
            selected_fmt="已选：{value}",
            tag="标签",
            tag_placeholder="输入或选择…",
            tag_fmt="标签：{value}",
            volume_stepped="音量（步进）",
            volume_continuous="音量（连续）",
            progress_follows="进度条跟随同一个信号",
            downloading="下载中…",
            scanning="扫描中…",
            advance="+15%",
            shared_heat_fmt="共享 heat 信号（来自响应式标签页）：{n}%",
        ),
        layout=Layout(
            layout_title="布局",
            layout_blurb=(
                "HStack 行布局用 Spacer 把内容推向右；Flex 提供完全控制，包括换行。VStack "
                "垂直堆叠，Separator 分隔，GlassPanel 做毛玻璃。"
            ),
            title="标题",
            edit="编辑",
            item_fmt="条目 {i}",
            frosted="毛玻璃",
            type_title="排版",
            type_blurb=(
                "六个标题级别加上跟随主题的语义文本角色。user_select 控制文本是否可选中："
                "下面第一行不可高亮，第二行可以。"
            ),
            locked_copy="锁定文本——user_select='none' 阻止选中。",
            heading_n="标题 {n}",
            primary_text="主文本——默认正文。",
            secondary_text="次要文本——弱化、较不重要。",
            danger_text="危险文本——错误与破坏性强调。",
            success_text="成功文本——确认信息。",
            selectable_copy="可选中文本——普通默认。",
        ),
        glass=Glass(
            glass_title="毛玻璃",
            glass_blurb=(
                "GlassPanel 模糊背景图片；glass=True 的组件保留主题色并获得磨砂表面。"
                "语义角色同时给面板的边框和外部光晕着色；每角半径可让面板在任何角度"
                "贴合窗口镶边。"
            ),
            input_placeholder="玻璃输入框…",
            typed_fmt="已输入：{value}",
            frosted_stage="Frosted Stage",
            stage_desc="Components inside keep their theme colours while gaining the frosted look.",
            primary="主要",
            ghost="幽灵",
            danger="危险",
            glass_checkbox="玻璃复选框",
            success_glow="成功——角色光晕跟随主题",
            danger_emphasis="危险——破坏性强调",
            corners_desc="每角半径——24px / 4px / 24px / 4px",
            icon_title="窗口图标",
            icon_blurb=(
                "无边框窗口把图标内联画在 TitleBar 里；带边框窗口通过 WindowConfig.icon "
                "把它交给操作系统窗口镶边——两者接受相同的 URL 或文件路径。file_url() / "
                "data_url() 把本地文件转成图标、背景和图片用的 URL 字符串。"
            ),
            icon_live="实时：上方标题栏的 favicon 用了 TitleBar(icon=...)。",
            icon_decorated=(
                "对带边框窗口，任务栏/标题栏图标来自 WindowConfig.icon；TitleBar(icon=...) 只影响无边框镶边。"
            ),
            content_title="内容",
            content_blurb=(
                "展示型组件——Image、Avatar、Badge 和 Card。纯表现层；它们复用主题令牌，因此切换主题时自动重绘。"
            ),
            image_heading="图片",
            avatar_heading="头像",
            badge_heading="徽标",
            card_heading="卡片",
            image_alt="Neony 图标",
            image_alt_round="圆形",
            av_name="Neony",
            av_ada="爱莉希雅",
            av_inbox="收件箱",
            badge_new="新增",
            badge_verified="已认证",
            badge_plain="普通",
            inline_pills="内联标签：",
            counts_desc="计数（150 → 99+，0 默认隐藏除非 show_zero）：",
            card_body="正文可以容纳任意子元素——文本、组件或裸节点。",
            plain_card_title="朴素卡片",
            plain_card_subtitle="带柔和阴影的实色表面",
            edit="编辑",
            card_clicked="卡片已点击。",
            glass_card_body="由角色着色的磨砂玻璃——强调光晕跟随主题。",
            glass_card_title="玻璃卡片",
            glass_card_subtitle="role='accent'",
        ),
        interaction=Interaction(
            events_title="Rich Events",
            events_blurb=(
                "每个委托事件都携带完整载荷：修饰键（ctrl/shift/alt/meta）、视口和元素相对"
                "鼠标坐标、滚轮增量、指针移动——实时增量和设备类型。点击方框、输入时按住"
                "修饰键、滚动区域、把指针移过底部方框。"
            ),
            click_anywhere="点击此框内任意位置",
            mod_placeholder="在任意处输入——灯光跟随修饰键…",
            meta_reserved=(
                "在 Linux 上，Meta（Super）常被窗口管理器占用——hyprland 会抓走它用于自己的"
                "绑定，所以它可能永远到不了页面。另外三个修饰键总是到达。"
            ),
            wheel_tall="高内容让区域可以滚动…",
            wheel_keep="继续滚动查看实时增量。",
            drop_title="文件拖放",
            drop_blurb=(
                "从文件管理器把文件拖进虚线区域。drop 事件携带每个文件的名称、本地路径、"
                "大小和 MIME 类型。在 WebKitGTK 上 webview 报告空文件，所以 Neony 在原生层"
                "接管拖放、命中测试位置、并用真实路径重新派发 drop 事件；在 WebView2 上 "
                "File.path 直接到达，在 WKWebView 上为空。dragover/dragleave/drop 全部委托，"
                "并且浏览器拖放即导航的默认行为已为你阻止。"
            ),
            drop_hint="把文件拖到此框内任意位置",
            drop_release="松开以释放",
            no_files="（无文件——在 WKWebView 上文件路径为空）",
            path_unavailable="<不可用>",
            clipboard_title="剪贴板",
            clipboard_blurb=(
                "剪贴板事件把数据带进 Python：粘贴传递 clipboard_text / clipboard_html，"
                "复制/剪切作为通知触发。写入/读取 API 位于后端（写入无需用户手势）；"
                "读取仍需要窗口获得焦点。"
            ),
            paste_placeholder="粘贴（Ctrl+V）到此字段…",
            clip_not_exposed="clipboard_text：<此后端未暴露>",
            clip_text_fmt="clipboard_text：{value!r}",
            clip_text_html_fmt="  html：{html!r}",
            clip_paste_event="paste 事件——剪贴板已带入 Python",
            clip_copy_event="copy 事件（用户按了 Ctrl+C）",
            clip_cut_event="cut 事件（用户按了 Ctrl+X）",
            clip_input_fmt="输入值：{value!r}",
            copy_sample="复制示例文本",
            read_clipboard="读取剪贴板",
            wrote_sample="Neony 从 Python 写入了这条！",
            write_failed_fmt="写入失败：{exc}",
            write_failed_log_fmt="clipboard_write() 失败：{exc}",
            wrote_fmt="已写入 {text!r}",
            read_failed_fmt="读取失败：{exc}",
            read_failed_log_fmt="clipboard_read() 失败：{exc}",
            read_fmt="读取：{text!r}",
            shortcuts_title="快捷键",
            shortcuts_blurb=(
                "在窗口任意位置都能触发的页面级按键绑定——即使输入框获得焦点、在任何标签页"
                "都行。注册单个组合键或按平台的字典（macOS 用 Ctrl+Meta，Linux/Windows 用 "
                "Ctrl）。修饰键必须精确匹配；按键名大小写不敏感。从这里或任何其他标签页试试："
            ),
            ctrl_b="Ctrl+B — 加粗",
            ctrl_g="Ctrl+G — 光晕",
            ctrl_d="Ctrl+D — 深色",
            ctrl_k="Ctrl+K（macOS 上为 Meta+K）— 主题",
            overlays_title="Overlays",
            overlays_blurb=(
                "四层定位——全部 CSS 锚定，零测量。Dialog 用主题遮罩压暗整个页面并居中一块"
                "带可配置操作按钮的面板（遮罩 / Escape / 点击外部关闭）；Tooltip 包裹锚点并"
                "带位置偏移和悬停延迟；Dropdown 复用弹出模式（点击外部关闭、完整键盘导航）；"
                "Menu 通过 open_at() 固定在光标处——右键点击按钮。"
            ),
            dialog_title="确认",
            dialog_label="对话框",
            prompt_label="输入对话框",
            dropdown_label="下拉框",
            dialog_body="试试遮罩、Escape、点击外部，或下面的按钮。",
            dialog_confirm="确认",
            dialog_cancel="取消",
            dialog_close="关闭",
            dialog_open_btn="打开对话框",
            dialog_open_state="已打开——等待选择",
            dialog_chose_fmt="已关闭——选择了 {value!r}",
            dialog_dismiss="已关闭——已消除（遮罩 / Escape / 点击外部）",
            tooltip_top="顶部提示",
            hover_top="悬停（顶部）",
            tooltip_bottom="底部提示",
            hover_bottom="悬停（底部）",
            theme_label="主题",
            dark="深色",
            light="浅色",
            deep_blue="深蓝",
            dropdown_fmt="下拉框：{value}",
            rename="重命名",
            duplicate="复制",
            delete="删除",
            menu_fmt="菜单：{value}",
            right_click="右键点击我",
            prompt_question="你叫什么名字？",
            identify="识别",
            name_placeholder="希罗…",
            prompt_open_btn="询问名字",
            prompt_open_state="已打开",
            prompt_closed_state="已关闭",
            prompt_submitted_fmt="已提交：{value!r}",
        ),
        data=Data(
            list_title="列表",
            list_blurb=(
                "可滚动、单选的数据列表——listbox 模型。方向键直接移动选择（每次移动触发 "
                "change），Home/End 跳到两端，Enter/空格选择，点击也选择。选择通过 bind_selected "
                "双向响应——用户点击写入信号，程序化 selected_key 写入会镜像进它。"
            ),
            apple="苹果",
            banana="香蕉",
            cherry="樱桃",
            durian="榴莲",
            elderberry="接骨木果",
            select_durian="选择「榴莲」",
            selected_fmt="已选：{key}",
            table_title="数据表",
            table_blurb=(
                "列配置 + 数据行，带吸顶表头、点击排序的列和行选择。列用 CSS grid 布局"
                "（像 '2fr' / '80px' 这样的宽度轨道），表头吸顶而表体滚动，排序对数字感知"
                "（或通过每列的 sort_key）。选择默认单选，构造时可选多选。"
            ),
            name="姓名",
            role="角色",
            age="年龄",
            score="分数",
            kiana="琪亚娜",
            mei="芽衣",
            bronya="布洛妮娅",
            elysia="爱莉希雅",
            eden="伊甸",
            sort_by_age="按年龄排序 ↓",
            kiana_role="薪炎之律者",
            mei_role="雷之律者",
            bronya_role="理之律者",
            elysia_role="粉色妖精小姐♪",
            eden_role="黄金·璀耀之歌",
            service="服务",
            status="状态",
            ok="正常",
            degraded="降级",
            selected_none="无",
        ),
        chat=Chat(
            notifications_title="通知",
            notifications_blurb=(
                "堆叠在屏幕边缘的瞬时应用内通知。宿主位于页面根部，是一个全视口图层"
                "（z-index 1100，pointer-events none）；卡片进入和离开时按各自位置播放动画——"
                "顶部下落、底部上升、角落对角滑动——并在 `duration` 后自动消失。传入 `on_click` "
                "时卡片可点击（✕ 永不触发它）。"
            ),
            placement="位置",
            toast_saved="文件保存成功",
            toast_clicked="toast 已点击",
            toast_success="成功",
            toast_info="信息",
            toast_error="错误",
            toast_update="有可用更新",
            toast_connection="连接已断开——正在重试…",
            toast_clear="清空",
            chat_title="聊天",
            chat_blurb=(
                "QQ/Telegram 风格的消息气泡和居中的系统提示。`from_me` 翻转对齐（右侧、强调色"
                "填充）与其他人（左侧、凸起表面）；消息侧可放可选头像。右键气泡打开内置菜单，"
                "悬停它可看到快捷操作。"
            ),
            other_msg="嘿！你看到新的画廊了吗？",
            me_msg="刚上线——三个新组件。",
            copy_text="复制",
            you_joined="你加入了群聊",
            menu_fmt="菜单：{value}",
            action_fmt="操作：{value}",
            right_click_hint="右键气泡打开菜单；悬停查看快捷操作。",
        ),
        system=System(
            animations_title="动画",
            animations_blurb=(
                "类型化 @keyframes：用链式 .set() 构建 KeyFrame，注册一次，即可从任意元素的 "
                "Animation 模型引用——多关键帧、命名，并像主题一样注入到全局 <style>。旋转器"
                "无限循环；卡片在挂载时播放一次 fade-slide。暂停/恢复切换播放状态。"
            ),
            paused="已暂停",
            running="运行中",
            pause="暂停",
            fades_slides="挂载时淡入并滑入",
            reactive_title="响应式",
            heat_bar="热度条",
            effect="Effect",
            batch="batch()",
            untrack="untrack()",
            bind_attr="bind_attr",
            computed_chain="Computed 链",
            reactive_blurb=(
                "Signal、Computed 和 Effect 配声明式绑定——无需手动刷新调用。bind_text / "
                "bind_style / bind_visible / bind_attr / bind_value 跟随各自的信号；batch() "
                "把多次写入合并成一次刷新，untrack() 不订阅地读取，computed 链可以组合。"
                "heat 条在标签页间共享——在这里调整它，看表单页。"
            ),
            heat_fmt="heat：{n}%",
            first_name="名",
            last_name="姓",
            computed_full_fmt="Computed 全名：{v}",
            type_both="输入两个名字…",
            effect_fired_fmt="Effect 已触发——level = {n}",
            effect_running="effect：运行中",
            effect_disposed="effect：已释放——level 变化不再同步",
            dispose_effect="释放 effect",
            restart_effect="重启 effect",
            level_plus="等级 +5",
            level_minus="等级 -5",
            secret_desc="这个盒子的显示绑定到一个 Signal。",
            visible="可见",
            effect_runs_fmt="effect 运行：{runs}  （a={a}, b={b}）",
            a_plus_1="a + 1",
            batch_both="在 batch() 内 a + 1, b + 1",
            tracked_plus="tracked + 1",
            ignored_plus="ignored + 1（untracked——不再重跑）",
            untrack_runs_fmt="effect 运行：{runs}  （tracked={tracked}，{ignored} 经 untrack 读取——无订阅）",
            untrack_ignored="ignored={n}",
            busy_state="busy：false——disabled 属性跟随信号",
            busy_fmt="busy：{b}——disabled={flag}在按钮上设置",
            toggle_busy="切换 busy",
            price_plus="price +1",
            price_minus="price -1",
            qty_plus="qty +1",
            qty_minus="qty -1",
            rate_plus="rate +0.1",
            rate_minus="rate -0.1",
            total_fmt="总计：¥{v:.2f}   （小计 ¥{s:.2f} × 汇率 {r:.1f}）",
            bind_placeholder="输入——信号跟随每一次击键…",
            echo_fmt="回显 {n}：{v}",
            set_signal="设置信号 → 组件",
            written_signal="从信号侧写入",
            sidebar_title="侧边栏",
            save="保存",
            sidebar_blurb=(
                "Sidebar 可以拥有自己的内容面板。Pane 的 key 是显式的，选中状态绑定到 Signal，"
                "点击条目即可切换已挂载的面板，无需手写映射或 switch 函数。"
            ),
            home="首页",
            settings="设置",
            profile="个人资料",
            home_content="首页内容——Sidebar 拥有这个面板。",
            settings_content="设置内容——选择另一条目来切换面板。",
            profile_content="个人资料内容——面板在隐藏时保持挂载状态。",
            active_fmt="当前：{key}",
            tabs_title="标签页",
            tabs_blurb=(
                "Tabs 拥有自己的内容面板——因为 DOM 保持挂载，面板状态在切换时存活。选择"
                "绑定到 Signal（和 Sidebar 一样）。当标签溢出栏位时横向滚动并带边缘淡出提示，"
                "而不是换行；方向键轮转，Enter/空格激活。"
            ),
            pane_a="面板 A",
            pane_b="面板 B",
            pane_c="面板 C",
            first_pane="第一个面板——Tabs 拥有自己的面板。",
            second_pane="第二个面板——隐藏时状态保持挂载。",
            third_pane="第三个面板。",
            section_fmt="分区 {c}",
            panel_fmt="面板 {c} 内容。",
            tab_selected_fmt="已选：{key}",
            window_title="窗口状态",
            window_blurb=(
                "show / hide / focus 在屏幕上移动窗口；set_bounds 通过 tao（外部位置）定位并"
                "调整大小。状态行还跟踪页面的 on_focus / on_blur 生命周期钩子（并非每个栈都会"
                "发出——Wayland/GTK 的焦点事件取决于后端）。"
            ),
            window_state="窗口状态",
            hide_note=("隐藏后 2 秒会自动恢复（「显示」按钮就在窗口内部，若永久隐藏会把自己困住）。"),
            wayland_note=(
                "在 Wayland 上，窗口定位是空操作（协议禁止客户端定位）。调整大小只是一次请求："
                "窗口处于平铺状态时平铺式 WM 会忽略它——先将窗口设为浮动（如 Win+F），"
                "set_bounds/set_size 才会生效。"
            ),
            pos_note="位置以屏幕左上角为原点，单位为逻辑像素。",
            hide="隐藏",
            show="显示",
            focus="聚焦",
            compact_pos="紧凑 @ (100, 100)",
            default_pos="默认 @ (0, 0)",
            window_hidden="窗口已隐藏——2 秒后自动恢复…",
            window_shown_restore="窗口再次显示（自动恢复）",
            window_shown="窗口已显示",
            window_focused="窗口已聚焦",
            set_bounds_fmt="已应用 set_bounds({x}, {y}, {w}, {h})",
            window_lost_focus="窗口失去焦点（或已隐藏）",
        ),
    ),
)
