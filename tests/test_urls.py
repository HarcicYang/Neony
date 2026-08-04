"""Local resource URL helpers — ``file_url`` / ``data_url``."""

from pathlib import Path

import pytest

from neony.application import data_url, file_url


class TestFileURL:
    def test_posix_path(self):
        assert file_url("/home/user/img.png") == "file:///home/user/img.png"

    def test_path_with_spaces_is_encoded(self):
        url = file_url("/home/user/my file.png")
        assert url.startswith("file:///home/user/my%20file.png")

    def test_non_ascii_is_encoded(self):
        url = file_url("/tmp/图像.png")
        assert url.startswith("file:///tmp/")
        assert "%" in url  # percent-encoded

    def test_relative_path_resolves_absolute(self):
        url = file_url("img.png")
        assert url.startswith("file:///")

    def test_accepts_path_object(self, tmp_path: Path):
        assert file_url(tmp_path / "a.png") == (tmp_path / "a.png").resolve().as_uri()


class TestDataURL:
    def test_svg_mime_guessed_from_extension(self, tmp_path: Path):
        svg = tmp_path / "icon.svg"
        svg.write_text("<svg/>")

        url = data_url(svg)

        assert url.startswith("data:image/svg+xml;base64,")
        assert url.endswith("PHN2Zy8+")  # base64("<svg/>")

    def test_unknown_extension_falls_back(self, tmp_path: Path):
        blob = tmp_path / "file.qwzx"
        blob.write_bytes(b"\x00\x01")

        assert data_url(blob).startswith("data:application/octet-stream;base64,")

    def test_mime_type_override(self, tmp_path: Path):
        png = tmp_path / "icon.bin"
        png.write_bytes(b"x")

        assert data_url(png, "image/png").startswith("data:image/png;base64,")

    def test_accepts_str_path(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_text("hi")

        assert data_url(str(f)) == "data:text/plain;base64,aGk="

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            data_url(tmp_path / "nope.png")
