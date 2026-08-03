"""Test unique key generation and rendering."""

import pytest

from neony.dom import Div


class TestKeyGeneration:
    """Key auto-generation and manual override."""

    def test_auto_generated_key(self):
        """Every DOMElement gets a key automatically."""
        d = Div()
        assert d.key
        assert isinstance(d.key, str)
        assert len(d.key) == 32  # uuid4 hex

    def test_keys_are_unique(self):
        """Two instances get different keys."""
        d1 = Div()
        d2 = Div()
        assert d1.key != d2.key

    def test_manual_key_override(self):
        """User-specified key is preserved."""
        d = Div(key="sidebar")
        assert d.key == "sidebar"

    def test_manual_key_not_overwritten(self):
        """Key factory does not overwrite a provided key."""
        d = Div(key="explicit")
        assert d.key == "explicit"


class TestKeyInBuild:
    """The key appears as data-neony-key in HTML output."""

    def test_build_includes_data_key(self):
        d = Div(key="mydiv")
        html = d.build()
        assert 'data-neony-key="mydiv"' in html

    def test_build_auto_key_present(self):
        d = Div()
        html = d.build()
        assert 'data-neony-key="' in html
        # Extract the key from the attribute
        assert d.key in html


class TestDuplicateKeyDetection:
    """to_node() rejects duplicate keys."""

    def test_duplicate_keys_raises(self):
        from neony.dom import Div

        tree = Div(
            container=[
                Div(key="dup"),
                Div(key="dup"),
            ]
        )
        with pytest.raises(ValueError, match="Duplicate key"):
            tree.to_node()

    def test_unique_keys_ok(self):
        from neony.dom import Div

        tree = Div(
            container=[
                Div(key="a"),
                Div(key="b"),
            ]
        )
        node = tree.to_node()
        assert len(node.children) == 2
