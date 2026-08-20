"""NeonApplication — complete LumiView wrapper with reactive DOM.

Public API::

    from neony.application import Config, NeonApplication, WindowConfig
    from neony.application import Page, launch
    from neony.application import Theme, DARK, LIGHT, icons
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
from neony.application.icons import stub as icons
from neony.application.page import Page
from neony.application.theme import (
    CYBERANGEL_DARK,
    CYBERANGEL_LIGHT,
    DARK,
    DEEP_BLUE,
    EMBER_ZONE_DARK,
    EMBER_ZONE_LIGHT,
    LIGHT,
    NIGHTGLOW_DARK,
    NIGHTGLOW_LIGHT,
    PLANET_PLAZA_DARK,
    PLANET_PLAZA_LIGHT,
    Theme,
)
from neony.application.tray import Tray, TrayItem
from neony.application.urls import data_url, file_url

__all__ = [
    "CYBERANGEL_DARK",
    "CYBERANGEL_LIGHT",
    "DARK",
    "DEEP_BLUE",
    "EMBER_ZONE_DARK",
    "EMBER_ZONE_LIGHT",
    "LANGUAGES",
    "LIGHT",
    "NIGHTGLOW_DARK",
    "NIGHTGLOW_LIGHT",
    "PLANET_PLAZA_DARK",
    "PLANET_PLAZA_LIGHT",
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
    "icons",
    "launch",
    "register_catalog",
    "set_language",
    "tr",
    "tr_now",
]
