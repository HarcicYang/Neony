from neony.application.motion import DEFAULT, Motion, popup_animation, stub, submenu_animation, transition


def test_default_motion_registers_and_emits_css_tokens():
    assert Motion.get("default") is DEFAULT
    css = DEFAULT.to_css()
    assert "--motion-fast: 0.12s" in css
    assert "--motion-normal: 0.18s" in css


def test_stub_uses_css_variables():
    assert stub.fast == "var(--motion-fast)"
    assert stub.ease_enter == "var(--motion-ease-enter)"


def test_default_css_contains_all_motion_variables():
    css = DEFAULT.to_css()
    for name in ("fast", "normal", "slow", "ease-standard", "ease-enter", "ease-exit"):
        assert f"--motion-{name}:" in css


def test_factories_use_stub_tokens():
    assert transition("transform").duration == stub.normal
    assert popup_animation().duration == stub.normal
    assert popup_animation().name == "neony-drop-in"
    assert submenu_animation().timing == stub.ease_enter
