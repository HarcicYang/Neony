"""Framework i18n tests — the typed ``tr`` refs, reactive language
switching, and translated framework defaults.

The i18n state is module-global, so the autouse fixture registers the
test catalog pair and restores the language after every test.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from neony.application import (
    Catalog,
    Common,
    Config,
    Language,
    NeonApplication,
    TrRef,
    WindowConfig,
    get_language,
    register_catalog,
    set_language,
    tr,
    tr_now,
)
from neony.application.elements import Button, MessageBubble, PromptDialog, Text
from neony.dom import DOMElement, effect

_FILES_CFG = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)


class Files(BaseModel):
    """Nested sub-model — plain BaseModel, NOT a Catalog subclass."""

    model_config = _FILES_CFG
    count: TrRef[dict[str, int]] = TrRef("{n} files")


class AppCatalog(Catalog):
    save: TrRef[None] = TrRef("Save")
    files: Files = Files()


@pytest.fixture(autouse=True)
def _i18n_catalogs():
    register_catalog(Language.EN, AppCatalog())
    register_catalog(
        Language.ZH,
        AppCatalog(
            save="保存",
            files=Files(count="{n} 个文件"),
            common=Common(copy_text="复制", delete="删除", ok="确定", cancel="取消", close="关闭"),
        ),
    )
    set_language(Language.EN)
    yield
    set_language(Language.EN)


def _el_text(el: DOMElement | str) -> str:
    """First non-empty string in an element's container subtree."""
    if isinstance(el, str):
        return el
    for child in el.container:
        if isinstance(child, str):
            return child
        if isinstance(child, DOMElement):
            found = _el_text(child)
            if found:
                return found
    return ""


class TestLanguageEnum:
    def test_members_and_values(self):
        assert Language.EN.value == "en"
        assert Language.ZH.value == "zh"
        assert tuple(Language) == (
            Language.EN,
            Language.ZH,
            Language.JA,
            Language.FR,
            Language.DE,
            Language.ES,
            Language.PT,
            Language.RU,
        )

    def test_invalid_language_raises(self):
        with pytest.raises(ValueError):
            set_language("xx")

    def test_get_language(self):
        assert get_language() == Language.EN
        set_language(Language.ZH)
        assert get_language() == Language.ZH
        set_language(Language.EN)


class TestCatalogModel:
    def test_english_defaults(self):
        assert AppCatalog().save.get() == "Save"
        assert AppCatalog().common.copy_text.get() == "Copy"
        assert AppCatalog().common.delete.get() == "Delete"

    def test_frozen(self):
        with pytest.raises(ValueError):
            setattr(AppCatalog(), "save", "nope")  # noqa: B010

    def test_extra_forbidden(self):
        with pytest.raises(ValueError):
            AppCatalog(typo="x")  # type: ignore[call-arg]

    def test_per_language_override(self):
        # A standalone instance stores the override on the leaf ref directly.
        zh = AppCatalog(save="保存")
        assert zh.save._default == "保存"
        assert zh.save._override is True
        # Unset keys fall back to the English class default.
        assert zh.common.copy_text._default == "Copy"

    def test_registered_zh_resolves_via_tr(self):
        # The ZH catalog registered by the fixture resolves through ``tr``
        # after a language switch.
        set_language(Language.ZH)
        try:
            assert tr.common.copy_text.get() == "复制"
        finally:
            set_language(Language.EN)

    def test_field_type_is_trref(self):
        """Catalog fields are typed TrRefs — completion + typo-checking source."""
        assert isinstance(AppCatalog().save, TrRef)
        assert isinstance(AppCatalog().common.copy_text, TrRef)

    def test_trref_schema_rejects_wrong_type(self):
        with pytest.raises(ValidationError):
            AppCatalog(save=123)  # type: ignore[arg-type]

    def test_instance_path_isolation(self):
        """Each catalog instance owns its leaf refs (no shared-default leak)."""
        a = AppCatalog()
        b = AppCatalog()
        assert a.save is not b.save
        assert a.common is not b.common


class TestTrRef:
    def test_flat_and_nested_resolve(self):
        assert tr.common.copy_text.get() == "Copy"
        # AppCatalog keys are reachable through the test catalog's own ``tr``:
        app = AppCatalog()
        assert app.save.get() == "Save"
        assert app.files.count.get() == "{n} files"

    def test_interpolation(self):
        assert AppCatalog().files.count.format(n=5).get() == "5 files"

    def test_format_preserves_path(self):
        ref = AppCatalog().files.count.format(n=3)
        assert ref._path == ("files", "count")
        assert ref.get() == "3 files"

    def test_tr_now_immediate(self):
        assert tr_now(tr.common.copy_text) == "Copy"

    def test_tr_now_does_not_subscribe(self):
        runs: list[str] = []

        def sync() -> None:
            runs.append(tr_now(tr.common.copy_text))

        eff = effect(sync)
        assert runs == ["Copy"]
        set_language(Language.ZH)
        # tr_now reads are untracked — the effect must not re-run.
        assert runs == ["Copy"]
        eff.dispose()


class TestReactiveSwitch:
    def test_text_updates_live(self):
        t = Text(tr.common.copy_text)
        root = t.build()
        assert root.to_node().text == "Copy"
        set_language(Language.ZH)
        assert root.to_node().text == "复制"
        set_language(Language.EN)
        assert root.to_node().text == "Copy"

    def test_button_label_updates_live(self):
        b = Button(tr.common.copy_text)
        root = b.build()
        assert root.to_node().children[0].text == "Copy"
        set_language(Language.ZH)
        assert root.to_node().children[0].text == "复制"
        set_language(Language.EN)
        assert root.to_node().children[0].text == "Copy"

    def test_unregistered_language_falls_back_to_english(self):
        t = Text(tr.common.copy_text)
        root = t.build()
        set_language(Language.JA)  # valid, but no catalog registered
        assert root.to_node().text == "Copy"
        set_language(Language.EN)


class TestFrameworkDefaults:
    def test_message_bubble_default_menu_translates(self):
        set_language(Language.ZH)
        bubble = MessageBubble("hi")
        menu = bubble._menu
        assert menu is not None
        assert [_el_text(row[1]) for row in menu._rows] == ["复制", "删除"]
        set_language(Language.EN)

    def test_message_bubble_empty_menu_still_disables(self):
        bubble = MessageBubble("hi", menu_items=[])
        assert bubble._menu is None

    def test_prompt_dialog_default_labels_translate(self):
        set_language(Language.ZH)
        pd = PromptDialog("name?")
        bar = pd._panel.container[2]
        assert isinstance(bar, DOMElement)
        assert [_el_text(child) for child in bar.container] == ["取消", "确定"]
        set_language(Language.EN)

    def test_prompt_dialog_explicit_labels_win(self):
        pd = PromptDialog("name?", confirm_label="Go", cancel_label="Back")
        bar = pd._panel.container[2]
        assert isinstance(bar, DOMElement)
        assert [_el_text(child) for child in bar.container] == ["Back", "Go"]


class TestAppApi:
    def test_app_set_language_and_property(self):
        app = NeonApplication(Config(window=WindowConfig(title="t")))
        assert app.language == Language.EN
        app.set_language(Language.ZH)
        assert app.language == Language.ZH
        app.set_language(Language.EN)
        assert app.language == Language.EN
