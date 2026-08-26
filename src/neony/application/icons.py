"""Built-in semantic icon namespace.

Use the public :data:`stub`; the catalog implementation deliberately
remains private.  Every built-in icon is rendered by Neony's self-hosted
Material Symbols Rounded font, so it is offline and visually consistent on
all supported platforms.
"""

from __future__ import annotations

from typing import ClassVar

from neony.application.elements.icon import Icon


def _font_icon(name: str) -> Icon:
    """Build one private, themed font-icon descriptor.

    Material Symbols uses standard OpenType ligatures: the semantic name is
    the text payload and the bundled font resolves it to the matching glyph.
    """
    return Icon._font(name)


class _IconsStub:
    """Typed public namespace for Neony's built-in icons.

    This is intentionally a stub, like :mod:`neony.application.theme`'s
    ``stub``: it exposes immutable, prebuilt descriptors and not a mutable
    catalog class.  User code imports :data:`stub` (or the application-level
    ``icons`` alias) only.
    """

    # Navigation / application
    home: ClassVar[Icon] = _font_icon("home")
    settings: ClassVar[Icon] = _font_icon("settings")
    person: ClassVar[Icon] = _font_icon("person")
    search: ClassVar[Icon] = _font_icon("search")
    menu: ClassVar[Icon] = _font_icon("menu")
    close: ClassVar[Icon] = _font_icon("close")

    # Actions / editing
    add: ClassVar[Icon] = _font_icon("add")
    check: ClassVar[Icon] = _font_icon("check")
    edit: ClassVar[Icon] = _font_icon("edit")
    delete: ClassVar[Icon] = _font_icon("delete")
    content_copy: ClassVar[Icon] = _font_icon("content_copy")
    refresh: ClassVar[Icon] = _font_icon("refresh")
    star: ClassVar[Icon] = _font_icon("star")
    save: ClassVar[Icon] = _font_icon("save")
    undo: ClassVar[Icon] = _font_icon("undo")
    redo: ClassVar[Icon] = _font_icon("redo")
    share: ClassVar[Icon] = _font_icon("share")
    launch: ClassVar[Icon] = _font_icon("launch")
    open_in_new: ClassVar[Icon] = _font_icon("open_in_new")
    download: ClassVar[Icon] = _font_icon("download")
    upload: ClassVar[Icon] = _font_icon("upload")
    send: ClassVar[Icon] = _font_icon("send")
    done: ClassVar[Icon] = _font_icon("done")
    done_all: ClassVar[Icon] = _font_icon("done_all")
    done_outline: ClassVar[Icon] = _font_icon("done_outline")
    download_done: ClassVar[Icon] = _font_icon("download_done")

    # Direction / disclosure
    chevron_left: ClassVar[Icon] = _font_icon("chevron_left")
    chevron_right: ClassVar[Icon] = _font_icon("chevron_right")
    expand_more: ClassVar[Icon] = _font_icon("expand_more")
    expand_less: ClassVar[Icon] = _font_icon("expand_less")
    arrow_upward: ClassVar[Icon] = _font_icon("arrow_upward")
    arrow_downward: ClassVar[Icon] = _font_icon("arrow_downward")
    unfold_more: ClassVar[Icon] = _font_icon("unfold_more")
    unfold_less: ClassVar[Icon] = _font_icon("unfold_less")
    arrow_back: ClassVar[Icon] = _font_icon("arrow_back")
    arrow_forward: ClassVar[Icon] = _font_icon("arrow_forward")
    arrow_back_ios: ClassVar[Icon] = _font_icon("arrow_back_ios")
    arrow_forward_ios: ClassVar[Icon] = _font_icon("arrow_forward_ios")
    north_east: ClassVar[Icon] = _font_icon("north_east")
    south_east: ClassVar[Icon] = _font_icon("south_east")
    south_west: ClassVar[Icon] = _font_icon("south_west")
    north_west: ClassVar[Icon] = _font_icon("north_west")
    call_made: ClassVar[Icon] = _font_icon("call_made")
    call_received: ClassVar[Icon] = _font_icon("call_received")
    keyboard_arrow_up: ClassVar[Icon] = _font_icon("keyboard_arrow_up")
    keyboard_arrow_down: ClassVar[Icon] = _font_icon("keyboard_arrow_down")
    keyboard_arrow_left: ClassVar[Icon] = _font_icon("keyboard_arrow_left")
    keyboard_arrow_right: ClassVar[Icon] = _font_icon("keyboard_arrow_right")
    keyboard_double_arrow_up: ClassVar[Icon] = _font_icon("keyboard_double_arrow_up")
    keyboard_double_arrow_down: ClassVar[Icon] = _font_icon("keyboard_double_arrow_down")
    keyboard_double_arrow_left: ClassVar[Icon] = _font_icon("keyboard_double_arrow_left")
    keyboard_double_arrow_right: ClassVar[Icon] = _font_icon("keyboard_double_arrow_right")

    # Status / content
    info: ClassVar[Icon] = _font_icon("info")
    warning: ClassVar[Icon] = _font_icon("warning")
    error: ClassVar[Icon] = _font_icon("error")
    favorite: ClassVar[Icon] = _font_icon("favorite")
    chat: ClassVar[Icon] = _font_icon("chat")
    block: ClassVar[Icon] = _font_icon("block")
    cancel: ClassVar[Icon] = _font_icon("cancel")
    hourglass: ClassVar[Icon] = _font_icon("hourglass")
    restart_alt: ClassVar[Icon] = _font_icon("restart_alt")
    autorenew: ClassVar[Icon] = _font_icon("autorenew")
    cached: ClassVar[Icon] = _font_icon("cached")
    loop: ClassVar[Icon] = _font_icon("loop")
    repeat: ClassVar[Icon] = _font_icon("repeat")
    verified: ClassVar[Icon] = _font_icon("verified")
    help: ClassVar[Icon] = _font_icon("help")
    help_outline: ClassVar[Icon] = _font_icon("help_outline")
    question_mark: ClassVar[Icon] = _font_icon("question_mark")
    tips_and_updates: ClassVar[Icon] = _font_icon("tips_and_updates")
    celebration: ClassVar[Icon] = _font_icon("celebration")
    rocket: ClassVar[Icon] = _font_icon("rocket")
    offline_pin: ClassVar[Icon] = _font_icon("offline_pin")
    checklist: ClassVar[Icon] = _font_icon("checklist")
    check_circle: ClassVar[Icon] = _font_icon("check_circle")
    add_circle: ClassVar[Icon] = _font_icon("add_circle")
    remove_circle: ClassVar[Icon] = _font_icon("remove_circle")
    warning_amber: ClassVar[Icon] = _font_icon("warning_amber")

    # Media / playback
    play_arrow: ClassVar[Icon] = _font_icon("play_arrow")
    pause: ClassVar[Icon] = _font_icon("pause")
    volume_up: ClassVar[Icon] = _font_icon("volume_up")
    volume_off: ClassVar[Icon] = _font_icon("volume_off")
    volume_mute: ClassVar[Icon] = _font_icon("volume_mute")

    # Selection / forms
    check_box: ClassVar[Icon] = _font_icon("check_box")
    indeterminate_check_box: ClassVar[Icon] = _font_icon("indeterminate_check_box")
    toggle_on: ClassVar[Icon] = _font_icon("toggle_on")
    toggle_off: ClassVar[Icon] = _font_icon("toggle_off")
    radio_button_checked: ClassVar[Icon] = _font_icon("radio_button_checked")
    radio_button_unchecked: ClassVar[Icon] = _font_icon("radio_button_unchecked")
    square: ClassVar[Icon] = _font_icon("square")
    circle: ClassVar[Icon] = _font_icon("circle")
    crop_square: ClassVar[Icon] = _font_icon("crop_square")

    # Window / layout
    fullscreen: ClassVar[Icon] = _font_icon("fullscreen")
    close_fullscreen: ClassVar[Icon] = _font_icon("close_fullscreen")
    open_in_full: ClassVar[Icon] = _font_icon("open_in_full")
    minimize: ClassVar[Icon] = _font_icon("minimize")
    maximize: ClassVar[Icon] = _font_icon("maximize")
    drag_indicator: ClassVar[Icon] = _font_icon("drag_indicator")
    drag_handle: ClassVar[Icon] = _font_icon("drag_handle")
    reorder: ClassVar[Icon] = _font_icon("reorder")
    widgets: ClassVar[Icon] = _font_icon("widgets")

    # Views / navigation chrome
    dashboard: ClassVar[Icon] = _font_icon("dashboard")
    grid_view: ClassVar[Icon] = _font_icon("grid_view")
    list: ClassVar[Icon] = _font_icon("list")
    more_vert: ClassVar[Icon] = _font_icon("more_vert")
    more_horiz: ClassVar[Icon] = _font_icon("more_horiz")
    logout: ClassVar[Icon] = _font_icon("logout")
    login: ClassVar[Icon] = _font_icon("login")
    lock: ClassVar[Icon] = _font_icon("lock")
    lock_open: ClassVar[Icon] = _font_icon("lock_open")
    visibility: ClassVar[Icon] = _font_icon("visibility")
    visibility_off: ClassVar[Icon] = _font_icon("visibility_off")
    dark_mode: ClassVar[Icon] = _font_icon("dark_mode")
    light_mode: ClassVar[Icon] = _font_icon("light_mode")
    notifications: ClassVar[Icon] = _font_icon("notifications")
    bookmark: ClassVar[Icon] = _font_icon("bookmark")
    pin: ClassVar[Icon] = _font_icon("pin")
    label: ClassVar[Icon] = _font_icon("label")
    tag: ClassVar[Icon] = _font_icon("tag")
    filter: ClassVar[Icon] = _font_icon("filter")
    filter_list: ClassVar[Icon] = _font_icon("filter_list")
    sort: ClassVar[Icon] = _font_icon("sort")
    calendar_today: ClassVar[Icon] = _font_icon("calendar_today")
    email: ClassVar[Icon] = _font_icon("email")
    link: ClassVar[Icon] = _font_icon("link")
    image: ClassVar[Icon] = _font_icon("image")

    # Tools / analytics
    settings_suggest: ClassVar[Icon] = _font_icon("settings_suggest")
    build: ClassVar[Icon] = _font_icon("build")
    extension: ClassVar[Icon] = _font_icon("extension")
    inventory: ClassVar[Icon] = _font_icon("inventory")
    history: ClassVar[Icon] = _font_icon("history")
    restore: ClassVar[Icon] = _font_icon("restore")
    query_stats: ClassVar[Icon] = _font_icon("query_stats")
    insights: ClassVar[Icon] = _font_icon("insights")
    monitoring: ClassVar[Icon] = _font_icon("monitoring")
    bar_chart: ClassVar[Icon] = _font_icon("bar_chart")
    show_chart: ClassVar[Icon] = _font_icon("show_chart")
    pie_chart: ClassVar[Icon] = _font_icon("pie_chart")
    timeline: ClassVar[Icon] = _font_icon("timeline")
    leaderboard: ClassVar[Icon] = _font_icon("leaderboard")
    summarize: ClassVar[Icon] = _font_icon("summarize")
    fact_check: ClassVar[Icon] = _font_icon("fact_check")
    tune: ClassVar[Icon] = _font_icon("tune")

    # Security / accounts
    key: ClassVar[Icon] = _font_icon("key")
    password: ClassVar[Icon] = _font_icon("password")
    shield: ClassVar[Icon] = _font_icon("shield")
    shield_lock: ClassVar[Icon] = _font_icon("shield_lock")
    verified_user: ClassVar[Icon] = _font_icon("verified_user")
    admin_panel_settings: ClassVar[Icon] = _font_icon("admin_panel_settings")
    manage_accounts: ClassVar[Icon] = _font_icon("manage_accounts")
    account_tree: ClassVar[Icon] = _font_icon("account_tree")
    group: ClassVar[Icon] = _font_icon("group")
    person_add: ClassVar[Icon] = _font_icon("person_add")
    badge: ClassVar[Icon] = _font_icon("badge")

    # Devices / data
    devices: ClassVar[Icon] = _font_icon("devices")
    monitor: ClassVar[Icon] = _font_icon("monitor")
    laptop: ClassVar[Icon] = _font_icon("laptop")
    smart_toy: ClassVar[Icon] = _font_icon("smart_toy")
    psychology: ClassVar[Icon] = _font_icon("psychology")
    hub: ClassVar[Icon] = _font_icon("hub")
    schema: ClassVar[Icon] = _font_icon("schema")
    route: ClassVar[Icon] = _font_icon("route")
    data_object: ClassVar[Icon] = _font_icon("data_object")
    data_array: ClassVar[Icon] = _font_icon("data_array")
    functions: ClassVar[Icon] = _font_icon("functions")
    calculate: ClassVar[Icon] = _font_icon("calculate")
    science: ClassVar[Icon] = _font_icon("science")
    construction: ClassVar[Icon] = _font_icon("construction")
    terminal: ClassVar[Icon] = _font_icon("terminal")
    database: ClassVar[Icon] = _font_icon("database")
    cloud: ClassVar[Icon] = _font_icon("cloud")
    sync: ClassVar[Icon] = _font_icon("sync")
    code: ClassVar[Icon] = _font_icon("code")
    code_blocks: ClassVar[Icon] = _font_icon("code_blocks")

    # Documents / content
    folder_open: ClassVar[Icon] = _font_icon("folder_open")
    attach_file: ClassVar[Icon] = _font_icon("attach_file")
    description: ClassVar[Icon] = _font_icon("description")
    article: ClassVar[Icon] = _font_icon("article")
    note: ClassVar[Icon] = _font_icon("note")
    receipt: ClassVar[Icon] = _font_icon("receipt")

    # Payments / expression / assorted
    payments: ClassVar[Icon] = _font_icon("payments")
    credit_card: ClassVar[Icon] = _font_icon("credit_card")
    account_balance_wallet: ClassVar[Icon] = _font_icon("account_balance_wallet")
    wallet: ClassVar[Icon] = _font_icon("wallet")
    emoji_objects: ClassVar[Icon] = _font_icon("emoji_objects")
    mood: ClassVar[Icon] = _font_icon("mood")
    sentiment_satisfied: ClassVar[Icon] = _font_icon("sentiment_satisfied")
    fastfood: ClassVar[Icon] = _font_icon("fastfood")
    aspect_ratio: ClassVar[Icon] = _font_icon("aspect_ratio")


#: Public semantic icon namespace.  Do not import its private implementation.
stub = _IconsStub()

__all__ = ["stub"]
