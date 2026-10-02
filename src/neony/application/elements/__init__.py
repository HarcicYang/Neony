"""Neony component library — ready-made UI building blocks.

All components share the fluent API (``.on_click(fn)`` chaining),
own their state, and are theme-aware via CSS custom properties.
"""

from neony.application.elements._choices import ChoiceItem, MenuSeparator
from neony.application.elements.accordion import Accordion, Collapsible
from neony.application.elements.alert import Alert
from neony.application.elements.avatar import Avatar
from neony.application.elements.badge import Badge
from neony.application.elements.base import Component
from neony.application.elements.breadcrumb import Breadcrumb
from neony.application.elements.button import Button
from neony.application.elements.card import Card
from neony.application.elements.cascading_dropdown import CascadingDropdown
from neony.application.elements.chat import MessageBubble, NoticeBubble
from neony.application.elements.checkbox import Checkbox
from neony.application.elements.combobox import ComboBox
from neony.application.elements.command_palette import Command, CommandPalette
from neony.application.elements.datatable import Column, DataTable
from neony.application.elements.dialog import Dialog, DialogAction
from neony.application.elements.drawer import Drawer
from neony.application.elements.dropdown import Dropdown
from neony.application.elements.feedback import EmptyState, Skeleton, Spinner
from neony.application.elements.form_field import FormField
from neony.application.elements.grid_view import GridView
from neony.application.elements.heading import Heading
from neony.application.elements.icon import Icon
from neony.application.elements.image import Image
from neony.application.elements.input import Input
from neony.application.elements.layout import Flex, GlassPanel, HStack, Separator, Spacer, VStack
from neony.application.elements.list import List, ListItem
from neony.application.elements.markdown import Markdown
from neony.application.elements.media import Audio, Video
from neony.application.elements.menu import Menu, MenuBranch
from neony.application.elements.pagination import Pagination
from neony.application.elements.popover import Popover
from neony.application.elements.progress import Progress
from neony.application.elements.prompt_dialog import PromptDialog
from neony.application.elements.radio import Radio, RadioGroup
from neony.application.elements.reorder import Reorder, ReorderContent, ReorderItem
from neony.application.elements.rich_text import ImageSegment, RichText, TextSegment
from neony.application.elements.scroll import ScrollArea, StickToBottom
from neony.application.elements.segmented_control import SegmentedControl
from neony.application.elements.select import Select
from neony.application.elements.sidebar import Pane, Sidebar, SidebarGroup, SidebarItem
from neony.application.elements.slider import Slider
from neony.application.elements.stepper import Step, Stepper
from neony.application.elements.switch import Switch
from neony.application.elements.tabs import Tabs
from neony.application.elements.text import Text
from neony.application.elements.textarea import Textarea
from neony.application.elements.titlebar import TitleBar
from neony.application.elements.toast import Toast
from neony.application.elements.tooltip import Tooltip
from neony.application.elements.treeview import Tree, TreeNode

__all__ = [
    "Accordion",
    "Alert",
    "Audio",
    "Avatar",
    "Badge",
    "Breadcrumb",
    "Button",
    "Card",
    "CascadingDropdown",
    "Checkbox",
    "ChoiceItem",
    "Collapsible",
    "Column",
    "ComboBox",
    "Command",
    "CommandPalette",
    "Component",
    "DataTable",
    "Dialog",
    "DialogAction",
    "Drawer",
    "Dropdown",
    "EmptyState",
    "Flex",
    "FormField",
    "GlassPanel",
    "GridView",
    "HStack",
    "Heading",
    "Icon",
    "Image",
    "ImageSegment",
    "Input",
    "List",
    "ListItem",
    "Markdown",
    "Menu",
    "MenuBranch",
    "MenuSeparator",
    "MessageBubble",
    "NoticeBubble",
    "Pagination",
    "Pane",
    "Popover",
    "Progress",
    "PromptDialog",
    "Radio",
    "RadioGroup",
    "Reorder",
    "ReorderContent",
    "ReorderItem",
    "RichText",
    "ScrollArea",
    "SegmentedControl",
    "Select",
    "Separator",
    "Sidebar",
    "SidebarGroup",
    "SidebarItem",
    "Skeleton",
    "Slider",
    "Spacer",
    "Spinner",
    "Step",
    "Stepper",
    "StickToBottom",
    "Switch",
    "Tabs",
    "Text",
    "TextSegment",
    "Textarea",
    "TitleBar",
    "Toast",
    "Tooltip",
    "Tree",
    "TreeNode",
    "VStack",
    "Video",
]
