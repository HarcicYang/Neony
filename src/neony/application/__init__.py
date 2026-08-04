"""NeonApplication — complete LumiView wrapper with reactive DOM.

Public API::

    from neony.application import Config, NeonApplication, WindowConfig
    from neony.application import Page, launch
    from neony.application import Theme, DARK, LIGHT
    from neony.application.elements import Button, Checkbox, Input, Tabs, ...
"""

from neony.application.app import NeonApplication, launch
from neony.application.config import Config, WebViewConfig, WindowConfig
from neony.application.page import Page
from neony.application.theme import DARK, DEEP_BLUE, LIGHT, Theme
from neony.application.urls import data_url, file_url

__all__ = [
    "DARK",
    "DEEP_BLUE",
    "LIGHT",
    "Config",
    "NeonApplication",
    "Page",
    "Theme",
    "WebViewConfig",
    "WindowConfig",
    "data_url",
    "file_url",
    "launch",
]
