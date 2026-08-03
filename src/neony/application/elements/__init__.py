"""Neony component library — ready-made UI building blocks.

All components share the fluent API (``.on_click(fn)`` chaining),
own their state, and are theme-aware via CSS custom properties.
"""

from neony.application.elements.base import Component
from neony.application.elements.button import Button
from neony.application.elements.checkbox import Checkbox
from neony.application.elements.heading import Heading
from neony.application.elements.input import Input
from neony.application.elements.layout import Flex, GlassPanel, HStack, Separator, Spacer, VStack
from neony.application.elements.tabs import Tabs
from neony.application.elements.text import Text

__all__ = [
    "Button",
    "Checkbox",
    "Component",
    "Flex",
    "GlassPanel",
    "HStack",
    "Heading",
    "Input",
    "Separator",
    "Spacer",
    "Tabs",
    "Text",
    "VStack",
]
