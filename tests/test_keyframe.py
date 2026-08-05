"""Tests for the typed KeyFrame / Props / Animation API."""

from neony.dom import Animation, Color, Div, KeyFrame, Props, Styles


class TestProps:
    """Props renders the animatable-subset declarations."""

    def test_empty_props_renders_empty(self):
        assert Props().to_css() == ""

    def test_single_field(self):
        assert Props(opacity=0.5).to_css() == "opacity: 0.5"

    def test_snake_case_to_kebab(self):
        css = Props(background_color=Color(name="red"), backdrop_filter="blur(4px)")
        assert css.to_css() == "background-color: red; backdrop-filter: blur(4px)"

    def test_color_flattened_by_serializer(self):
        css = Props(color=Color(hex="#ff0000")).to_css()
        assert css == "color: #ff0000"

    def test_multiple_fields_in_declaration_order(self):
        css = Props(opacity=0.5, transform="rotate(45deg)", width="100px").to_css()
        assert css == "opacity: 0.5; transform: rotate(45deg); width: 100px"


class TestKeyFrameStop:
    """One stop holds a percent and a Props."""

    def test_default_props(self):
        from neony.dom.base import KeyFrameStop

        stop = KeyFrameStop(percent="50%")
        assert stop.percent == "50%"
        assert stop.props == Props()

    def test_populated_props(self):
        from neony.dom.base import KeyFrameStop

        stop = KeyFrameStop(percent="100%", props=Props(opacity=0))
        assert stop.props.opacity == 0


class TestKeyFrame:
    """Chainable builder."""

    def test_chain_appends_in_order(self):
        spin = (
            KeyFrame("spin").set("0%", Props(transform="rotate(0deg)")).set("100%", Props(transform="rotate(360deg)"))
        )
        assert spin.name == "spin"
        assert [s.percent for s in spin.stops] == ["0%", "100%"]
        assert spin.stops[0].props.transform == "rotate(0deg)"
        assert spin.stops[1].props.transform == "rotate(360deg)"

    def test_constructed_without_stops(self):
        kf = KeyFrame("empty")
        assert kf.stops == []

    def test_to_css_format(self):
        spin = (
            KeyFrame("spin").set("0%", Props(transform="rotate(0deg)")).set("100%", Props(transform="rotate(360deg)"))
        )
        expected = "@keyframes spin {\n  0% { transform: rotate(0deg) }\n  100% { transform: rotate(360deg) }\n}"
        assert spin.to_css() == expected

    def test_later_wins_identical_name(self):
        """Re-registering the same name replaces the CSS (dict semantics)."""
        first = KeyFrame("spin").set("0%", Props(opacity=0))
        second = KeyFrame("spin").set("0%", Props(opacity=1))
        # app.register_keyframe stores by name — simulate the overwrite:
        registry: dict[str, str] = {}
        registry[first.name] = first.to_css()
        registry[second.name] = second.to_css()
        assert registry["spin"] == second.to_css()
        assert "opacity: 1" in registry["spin"]


class TestAnimation:
    """Animation serializes to the CSS shorthand, omitting defaults."""

    def test_default_shorthand(self):
        assert Animation(name="spin").model_dump() == "spin 1s ease"

    def test_custom_duration_and_count(self):
        a = Animation(name="spin", duration="2s", iteration_count="infinite")
        assert a.model_dump() == "spin 2s ease infinite"

    def test_partial_customization_omits_defaults(self):
        a = Animation(name="fade", delay="0.5s", fill_mode="forwards")
        assert a.model_dump() == "fade 1s ease 0.5s forwards"

    def test_all_custom(self):
        a = Animation(
            name="slide",
            duration="0.4s",
            timing="ease-in-out",
            delay="0.1s",
            iteration_count="3",
            direction="alternate",
            fill_mode="both",
            play_state="paused",
        )
        assert a.model_dump() == "slide 0.4s ease-in-out 0.1s 3 alternate both paused"

    def test_raw_string_escape_hatch(self):
        assert Animation(name="spin", timing="steps(4, end)").model_dump() == "spin 1s steps(4, end)"


class TestStylesIntegration:
    """Styles.animation flows through the serialization pipeline."""

    def test_animation_serialized_to_kebab(self):
        d = Div(styles=Styles(animation=Animation(name="spin", duration="2s", iteration_count="infinite")))
        node = d.to_node()
        assert node.styles["animation"] == "spin 2s ease infinite"

    def test_raw_string_animation(self):
        d = Div(styles=Styles(animation="spin 1s linear"))
        node = d.to_node()
        assert node.styles["animation"] == "spin 1s linear"

    def test_none_animation_skipped(self):
        d = Div(styles=Styles(animation=None))
        node = d.to_node()
        assert "animation" not in node.styles
