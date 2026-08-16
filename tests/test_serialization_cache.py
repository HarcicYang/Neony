"""Regression tests for serialization caches on DOM elements and Styles.

Large trees build thousands of small pydantic models; these caches keep
``to_node()`` / direct-patch serialization from re-running pydantic model
serializers for every node on every render.
"""

from neony.dom import Color, Div, Styles


class TestStylesSerializationCache:
    def test_cached_css_dict_is_reused_until_mutation(self):
        styles = Styles(color=Color(name="red"))
        first = styles._serialize_css()
        assert first == {"color": "red"}
        assert styles._serialize_css() is first

        styles.color = Color(name="blue")
        assert styles._serialize_css() == {"color": "blue"}

    def test_model_copy_does_not_carry_stale_css_cache(self):
        styles = Styles(color=Color(name="red"))
        assert styles._serialize_css() == {"color": "red"}

        copied = styles.model_copy(update={"box_shadow": "0 0 3px red"})
        assert copied._serialize_css() == {"color": "red", "box-shadow": "0 0 3px red"}

    def test_owner_mutation_invalidates_style_cache(self):
        div = Div(styles=Styles(color=Color(name="red")))
        first = div._serialize_styles()
        assert first == {"color": "red"}
        assert div._serialize_styles() is first

        div.styles.color = Color(name="blue")
        assert div._serialize_styles() == {"color": "blue"}


class TestAttrSerializationCache:
    def test_cached_attr_dict_is_reused_until_mutation(self):
        div = Div(id_="main", args={"title": "hello"})
        first = div._serialize_attrs()
        assert first == {"id": "main", "title": "hello"}
        assert div._serialize_attrs() is first

        div.id_ = "other"
        assert div._serialize_attrs() == {"id": "other", "title": "hello"}

    def test_set_attr_invalidates_cache(self):
        div = Div(args={"title": "hello"})
        assert div._serialize_attrs() == {"title": "hello"}

        div._set_attr("disabled", True)
        assert div._serialize_attrs() == {"title": "hello", "disabled": ""}

    def test_style_overflow_mutation_recomputes_scroll_marker(self):
        div = Div(styles=Styles(overflow_y="auto"))
        attrs = div._serialize_attrs()
        assert "data-neony-scroll" in attrs

        div.styles.overflow_y = None
        assert "data-neony-scroll" not in div._serialize_attrs()
        div.styles.overflow_y = "auto"
        assert "data-neony-scroll" in div._serialize_attrs()
