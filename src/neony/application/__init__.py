"""NeonApplication — complete LumiView wrapper with reactive DOM.

Public API::

    from neony.application import Config, NeonApplication, WindowConfig
    from neony.application import Page, launch
    from neony.application import Theme, DARK, LIGHT
    from neony.application.elements import Button, Checkbox, Input, Tabs, ...
"""

from neony.application.app import NeonApplication, launch
from neony.application.config import Config, WebViewConfig, WindowConfig
from neony.application.i18n import (
    LANGUAGES,
    Catalog,
    Common,
    Language,
    TrRef,
    get_language,
    register_catalog,
    set_language,
    tr,
    tr_now,
)
from neony.application.page import Page
from neony.application.theme import (
    AURORA_GLASS_DARK,
    AURORA_GLASS_LIGHT,
    DARK,
    DEEP_BLUE,
    LIGHT,
    NEON_MICA_DARK,
    NEON_MICA_LIGHT,
    QUIET_GRAPHITE_DARK,
    QUIET_GRAPHITE_LIGHT,
    TERMINAL_EMBER_DARK,
    TERMINAL_EMBER_LIGHT,
    Theme,
)
from neony.application.tray import Tray, TrayItem
from neony.application.urls import data_url, file_url

__all__ = [
    "AURORA_GLASS_DARK",
    "AURORA_GLASS_LIGHT",
    "DARK",
    "DEEP_BLUE",
    "LANGUAGES",
    "LIGHT",
    "NEON_MICA_DARK",
    "NEON_MICA_LIGHT",
    "QUIET_GRAPHITE_DARK",
    "QUIET_GRAPHITE_LIGHT",
    "TERMINAL_EMBER_DARK",
    "TERMINAL_EMBER_LIGHT",
    "Catalog",
    "Common",
    "Config",
    "Language",
    "NeonApplication",
    "Page",
    "Theme",
    "TrRef",
    "Tray",
    "TrayItem",
    "WebViewConfig",
    "WindowConfig",
    "data_url",
    "file_url",
    "get_language",
    "launch",
    "register_catalog",
    "set_language",
    "tr",
    "tr_now",
]
