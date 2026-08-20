"""Gallery i18n — the catalog is well-formed and its keys resolve.

Importing the catalog module registers EN + ZH with the framework; the
framework resolver falls back to English for any unset key.  The leaf-walk
test resolves every catalog key through the ``tr`` chain, so a typo'd path
(which would crash the gallery at import time) surfaces here instead.
"""

from __future__ import annotations

import pytest

from neony.application import Language, set_language
from neony.dom import DOMElement
from neony.gallery.i18n import GalleryCatalog, tr, tr_now


def _unbind_tree(node: DOMElement) -> None:
    """Recursively release every signal binding in the subtree — a live
    ``tr`` binding on a child span (Button's label, Heading's text, ...)
    would otherwise keep a subscription on the global language signal
    that later tests override the catalogs under."""
    node.unbind()
    for child in node.container:
        if isinstance(child, DOMElement):
            _unbind_tree(child)


@pytest.fixture(autouse=True)
def _restore_language():
    set_language(Language.EN)
    yield
    set_language(Language.EN)


class TestCatalogShape:
    def test_frozen(self):
        with pytest.raises(ValueError):
            setattr(GalleryCatalog(), "shell", "x")  # noqa: B010

    def test_extra_forbid(self):
        with pytest.raises(ValueError):
            GalleryCatalog(typo="x")  # type: ignore[call-arg]

    def test_submodel_extra_forbid(self):
        from neony.gallery.i18n import Buttons

        with pytest.raises(ValueError):
            Buttons(typo="x")  # type: ignore[call-arg]


class TestEnKeysResolve:
    """One representative key per sub-model — catches structural typos."""

    @pytest.mark.parametrize(
        "ref,expected",
        [
            (tr.shell.h1, "Neony Component Gallery"),
            (tr.nav.home, "Home"),
            (tr.nav.icons, "Icons"),
            (tr.nav.datatable, "DataTable"),
            (tr.icons.title, "Built-in Icons"),
            (tr.home.heading, "Welcome"),
            (tr.buttons.primary, "Primary Action"),
            (tr.forms.wifi, "Wi-Fi"),
            (tr.layout.type_title, "Typography"),
            (tr.glass.glass_title, "Frosted Glass"),
            (tr.interaction.dialog_title, "Confirm"),
            (tr.data.list_title, "List"),
            (tr.chat.you_joined, "You joined the group"),
            (tr.system.reactive_title, "Reactive"),
        ],
    )
    def test_key(self, ref, expected):
        assert tr_now(ref) == expected


class TestZhKeysResolve:
    """ZH ships fully translated as the demo language."""

    def test_shell_and_sections(self):
        set_language(Language.ZH)
        try:
            assert tr_now(tr.shell.h1) == "Neony 组件画廊"
            assert tr_now(tr.nav.home) == "首页"
            assert tr_now(tr.buttons.primary) == "主要操作"
            assert tr_now(tr.forms.wifi) == "无线网"
            assert tr_now(tr.system.reactive_title) == "响应式"
        finally:
            set_language(Language.EN)


class TestInterpolation:
    """Named placeholders work in EN and ZH; ZH may reorder."""

    def test_clicks_fmt_en(self):
        assert tr_now(tr.buttons.clicks_fmt).format(n=5) == "5 clicks"

    def test_clicks_fmt_zh(self):
        set_language(Language.ZH)
        try:
            assert tr_now(tr.buttons.clicks_fmt).format(n=5) == "5 次点击"
        finally:
            set_language(Language.EN)

    def test_selected_count_fmt(self):
        assert tr_now(tr.forms.selected_count_fmt).format(n=2, total=3) == "2 of 3 selected"


class TestLiveSwitch:
    """Live Computed slots flip on set_language without rebuilding.

    Each test unbinds its widget at the end so the global language signal
    is not left with a gallery subscription that later tests (e.g.
    test_i18n, which overrides the registered catalogs) would trip on.
    """

    def test_heading_flips_live(self):
        from neony.application.elements import Heading

        h = Heading(tr.buttons.primary, level=3)
        root = h.build()
        try:
            assert h.text == "Primary Action"
            set_language(Language.ZH)
            assert h.text == "主要操作"
        finally:
            set_language(Language.EN)
            _unbind_tree(root)

    def test_button_flips_live(self):
        from neony.application.elements import Button

        b = Button(tr.buttons.primary)
        root = b.build()
        try:
            assert b.label == "Primary Action"
            set_language(Language.ZH)
            assert b.label == "主要操作"
        finally:
            set_language(Language.EN)
            _unbind_tree(root)

    def test_fmt_readout_flips_live(self):
        """Regression: a bind_text fmt that reads a catalog ref via ``.get()``
        subscribes to the language signal, so the readout re-resolves on
        set_language (the original ``tr_now`` form did not — bug)."""
        from neony.application.elements import Text
        from neony.dom import Signal

        heat = Signal(30)
        readout = Text("")
        readout.bind_text(heat, fmt=lambda n: tr.forms.shared_heat_fmt.format(n=n).get())
        root = readout.build()
        try:
            assert root.to_node().text == "shared heat signal (from the Reactive tab): 30%"
            set_language(Language.ZH)
            assert root.to_node().text == "共享 heat 信号（来自响应式标签页）：30%"  # noqa: RUF001
        finally:
            set_language(Language.EN)
            _unbind_tree(root)

    def test_datatable_names_flip_live(self):
        """DataTable row names are reactive tr refs — the name cell re-
        resolves on set_language (stable row identity key, localized display)."""
        from neony.application.elements import Column, DataTable

        table = DataTable(
            columns=[Column("Name", key="name")],
            rows=[{"key": "Kiana", "name": tr.data.kiana}],
            row_key=lambda r: r["key"],
        )
        root = table.build()
        try:
            body = [el for el in root.container if isinstance(el, DOMElement)][1]
            row = next(el for el in body.container if isinstance(el, DOMElement) and el.args.get("role") == "row")
            name_cell = next(el for el in row.container if isinstance(el, DOMElement))
            assert name_cell.to_node().text == "Kiana"
            set_language(Language.ZH)
            assert name_cell.to_node().text == "琪亚娜"
        finally:
            set_language(Language.EN)
            _unbind_tree(root)


class TestLeafWalk:
    """Resolve every catalog key through the tr chain — any typo'd path
    that would crash the gallery at import time surfaces here."""

    def test_every_leaf_resolves(self):
        def walk(node, path):
            model = type(node)
            for name in model.model_fields:
                sub = getattr(node, name)
                new_path = (*path, name)
                if hasattr(type(sub), "model_fields"):
                    walk(sub, new_path)
                else:
                    ref = tr
                    for part in new_path:
                        ref = getattr(ref, part)  # type: ignore[assignment]
                    tr_now(ref)  # type: ignore[arg-type]

        walk(GalleryCatalog(), ())


class TestLanguagePicker:
    def test_only_catalog_languages_are_offered(self):
        from neony.gallery.core import _GALLERY_LANGUAGES, _LANGUAGE_ITEMS

        assert _GALLERY_LANGUAGES == (Language.EN, Language.ZH)
        assert _LANGUAGE_ITEMS == [("en", "English"), ("zh", "中文")]


class TestSectionsBuild:
    """Import every gallery section and build the full page tree.

    The default suite never spawns a window, so nothing exercises the
    section modules except this — a pydantic validation error in a demo
    (wrong style token, bad child type) would otherwise only surface in
    the xvfb-gated smoke test.
    """

    def test_all_sections_import_and_page_builds(self):
        from neony.gallery.assemble import page
        from neony.gallery.sections import PANELS

        assert "reorder" in PANELS
        assert "dialogs" in PANELS
        page.build()
