"""Tests for the system tray API — Tray / TrayItem construction and the
mapping to lumiview's native menu items."""

from neony.application import Tray, TrayItem


class TestTrayItem:
    def test_plain_item(self):
        item = TrayItem("Show", id="show", accelerator="CmdOrCtrl+S")
        assert item.text == "Show"
        assert item.id == "show"
        assert item.accelerator == "CmdOrCtrl+S"
        assert item.checked is None
        assert item._separator is False

    def test_check_item(self):
        item = TrayItem("Mute", checked=True)
        assert item.checked is True

    def test_separator_marker(self):
        item = TrayItem.separator()
        assert item._separator is True


class TestTray:
    def test_defaults(self):
        tray = Tray(icon="tray.png")
        assert tray.tooltip is None
        assert tray.items == []
        assert tray.menu_on_left_click is True
        assert tray.close_to_tray is False

    def test_icon_forms(self):
        Tray(icon="icon.png")
        Tray(icon=(b"\x00\x00\x00\xff" * 16, 4, 4))

    def test_maps_to_lumiview_items(self):
        tray = Tray(
            icon="icon.png",
            items=[
                TrayItem("Show", id="show"),
                TrayItem.separator(),
                TrayItem("Mute", checked=True),
            ],
        )
        items = tray._to_lumiview_items()
        assert [type(i).__name__ for i in items] == ["MenuItem", "PredefinedMenuItem", "CheckMenuItem"]
        assert items[0].text == "Show"
        assert items[0].id == "show"
        assert items[2].text == "Mute"
        assert items[2].checked is True

    def test_on_activate_passthrough(self):
        calls: list = []

        def handler(_event):
            calls.append(1)

        tray = Tray(icon="icon.png", items=[TrayItem("Go", on_activate=handler)])
        item = tray._to_lumiview_items()[0]
        item._activate_callbacks[0](None)
        assert calls == [1]
