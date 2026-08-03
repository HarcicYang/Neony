"""Test typed HTML attribute fields on concrete element classes."""

from neony.dom import (
    Anchor,
    Audio,
    Button,
    Canvas,
    Details,
    Form,
    IFrame,
    Img,
    Input,
    Label,
    Link,
    Meta,
    Option,
    Script,
    Select,
    Source,
    Style,
    Textarea,
    Video,
)


class TestInput:
    def test_placeholder(self):
        node = Input(type="text", placeholder="Search…").to_node()
        assert node.attrs["placeholder"] == "Search…"
        assert node.attrs["type"] == "text"

    def test_build_renders_placeholder(self):
        html = Input(placeholder="Search…").build()
        assert 'placeholder="Search…"' in html

    def test_checked_true_renders_bare(self):
        html = Input(type="checkbox", checked=True).build()
        assert " checked" in html

    def test_checked_false_omitted(self):
        html = Input(type="checkbox", checked=False).build()
        assert " checked" not in html
        node = Input(type="checkbox", checked=False).to_node()
        assert "checked" not in node.attrs

    def test_numeric_attrs(self):
        node = Input(maxlength=20, min=0, max=100).to_node()
        assert node.attrs["maxlength"] == "20"
        assert node.attrs["min"] == "0"
        assert node.attrs["max"] == "100"

    def test_none_omitted(self):
        node = Input(type="text").to_node()
        assert "placeholder" not in node.attrs


class TestLabel:
    def test_for_alias(self):
        node = Label(for_="email").to_node()
        assert node.attrs["for"] == "email"

    def test_for_in_build(self):
        html = Label(for_="email").build()
        assert 'for="email"' in html


class TestAnchor:
    def test_href_target(self):
        node = Anchor(href="/about", target="_blank").to_node()
        assert node.attrs["href"] == "/about"
        assert node.attrs["target"] == "_blank"


class TestImg:
    def test_src_alt(self):
        node = Img(src="logo.png", alt="Logo", width=64, height=64).to_node()
        assert node.attrs["src"] == "logo.png"
        assert node.attrs["alt"] == "Logo"
        assert node.attrs["width"] == "64"


class TestTextarea:
    def test_placeholder_rows(self):
        node = Textarea(placeholder="Write…", rows=4, cols=40).to_node()
        assert node.attrs["placeholder"] == "Write…"
        assert node.attrs["rows"] == "4"
        assert node.attrs["cols"] == "40"


class TestButton:
    def test_type_disabled(self):
        node = Button(type="submit", disabled=True).to_node()
        assert node.attrs["type"] == "submit"
        assert node.attrs["disabled"] == ""

    def test_type_validation(self):
        node = Button(type="reset").to_node()
        assert node.attrs["type"] == "reset"


class TestSelectOption:
    def test_select_multiple(self):
        node = Select(name="tags", multiple=True, size=4).to_node()
        assert node.attrs["name"] == "tags"
        assert node.attrs["multiple"] == ""
        assert node.attrs["size"] == "4"

    def test_option_selected(self):
        node = Option(value="x", selected=True).to_node()
        assert node.attrs["value"] == "x"
        assert node.attrs["selected"] == ""


class TestForm:
    def test_action_method(self):
        node = Form(action="/submit", method="post").to_node()
        assert node.attrs["action"] == "/submit"
        assert node.attrs["method"] == "post"


class TestHeadElements:
    def test_meta_charset(self):
        node = Meta(charset="utf-8").to_node()
        assert node.attrs["charset"] == "utf-8"

    def test_meta_http_equiv_alias(self):
        node = Meta(http_equiv="refresh", content="30").to_node()
        assert node.attrs["http-equiv"] == "refresh"

    def test_link_rel_href(self):
        node = Link(rel="stylesheet", href="style.css").to_node()
        assert node.attrs["rel"] == "stylesheet"
        assert node.attrs["href"] == "style.css"

    def test_script_defer(self):
        node = Script(src="app.js", defer=True, async_=True).to_node()
        assert node.attrs["src"] == "app.js"
        assert node.attrs["defer"] == ""
        assert node.attrs["async"] == ""


class TestMedia:
    def test_video_controls(self):
        node = Video(src="movie.mp4", controls=True, loop=True).to_node()
        assert node.attrs["src"] == "movie.mp4"
        assert node.attrs["controls"] == ""
        assert node.attrs["loop"] == ""

    def test_audio_muted(self):
        node = Audio(src="sound.mp3", muted=True).to_node()
        assert node.attrs["muted"] == ""

    def test_source_srcset(self):
        node = Source(src="img.webp", srcset="img2x.webp 2x", type="image/webp").to_node()
        assert node.attrs["srcset"] == "img2x.webp 2x"
        assert node.attrs["type"] == "image/webp"


class TestMisc:
    def test_iframe_allowfullscreen(self):
        node = IFrame(src="https://example.com", allowfullscreen=True).to_node()
        assert node.attrs["src"] == "https://example.com"
        assert node.attrs["allowfullscreen"] == ""

    def test_canvas_dimensions(self):
        node = Canvas(width=300, height=150).to_node()
        assert node.attrs["width"] == "300"
        assert node.attrs["height"] == "150"

    def test_details_open(self):
        node = Details(open=True).to_node()
        assert node.attrs["open"] == ""

    def test_style_media(self):
        node = Style(media="print").to_node()
        assert node.attrs["media"] == "print"


class TestPrecedence:
    """args can still override a typed field (rendered later)."""

    def test_args_override_field(self):
        node = Input(type="text", args={"type": "password"}).to_node()
        assert node.attrs["type"] == "password"

    def test_build_args_override_field(self):
        html = Input(type="text", args={"type": "password"}).build()
        # first occurrence wins in HTML — the typed field comes first
        assert html.index('type="text"') < html.index('type="password"')
