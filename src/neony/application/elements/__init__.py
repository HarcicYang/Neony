"""Neony component library — ready-made UI building blocks.

All components share the fluent API (``.on_click(fn)`` chaining),
own their state, and are theme-aware via CSS custom properties.
"""

from neony.application.elements.accordion import Accordion, Collapsible
from neony.application.elements.avatar import Avatar
from neony.application.elements.badge import Badge
from neony.application.elements.base import Component
from neony.application.elements.button import Button
from neony.application.elements.card import Card
from neony.application.elements.chat import MessageBubble, NoticeBubble
from neony.application.elements.checkbox import Checkbox
from neony.application.elements.combobox import ComboBox
from neony.application.elements.datatable import Column, DataTable
from neony.application.elements.dialog import Dialog, DialogAction
from neony.application.elements.dropdown import Dropdown
from neony.application.elements.heading import Heading
from neony.application.elements.icon import Icon
from neony.application.elements.image import Image
from neony.application.elements.input import Input
from neony.application.elements.layout import Flex, GlassPanel, HStack, Separator, Spacer, VStack
from neony.application.elements.list import List, ListItem
from neony.application.elements.menu import Menu
from neony.application.elements.progress import Progress
from neony.application.elements.prompt_dialog import PromptDialog
from neony.application.elements.radio import Radio, RadioGroup
from neony.application.elements.select import Select
from neony.application.elements.sidebar import Pane, Sidebar, SidebarGroup, SidebarItem
from neony.application.elements.slider import Slider
from neony.application.elements.switch import Switch
from neony.application.elements.tabs import Tabs
from neony.application.elements.text import Text
from neony.application.elements.titlebar import TitleBar
from neony.application.elements.toast import Toast
from neony.application.elements.tooltip import Tooltip
from neony.application.elements.treeview import Tree, TreeNode

__all__ = [
    "Accordion",
    "Avatar",
    "Badge",
    "Button",
    "Card",
    "Checkbox",
    "Collapsible",
    "Column",
    "ComboBox",
    "Component",
    "DataTable",
    "Dialog",
    "DialogAction",
    "Dropdown",
    "Flex",
    "GlassPanel",
    "HStack",
    "Heading",
    "Icon",
    "Image",
    "Input",
    "List",
    "ListItem",
    "Menu",
    "MessageBubble",
    "NoticeBubble",
    "Pane",
    "Progress",
    "PromptDialog",
    "Radio",
    "RadioGroup",
    "Select",
    "Separator",
    "Sidebar",
    "SidebarGroup",
    "SidebarItem",
    "Slider",
    "Spacer",
    "Switch",
    "Tabs",
    "Text",
    "TitleBar",
    "Toast",
    "Tooltip",
    "Tree",
    "TreeNode",
    "VStack",
]
