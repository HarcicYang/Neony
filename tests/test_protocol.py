"""Test PatchMessage JSON round-trip and discriminated union validation."""

import pytest
from pydantic import ValidationError

from neony.dom import NodeDescriptor
from neony.dom.bridge import (
    CreatePatch,
    MovePatch,
    PatchMessage,
    RemovePatch,
    ReorderPatch,
    ReplacePatch,
    SetTextPatch,
    UpdateAttrsPatch,
    UpdateStylesPatch,
)


def _nd(key, tag="div"):
    return NodeDescriptor(key=key, tag=tag)


class TestPatchMessageRoundTrip:
    """Each patch type survives model_dump_json → model_validate_json."""

    def test_create_patch(self):
        msg = PatchMessage(rev=1, ops=[CreatePatch(key="a", node=_nd("a", "div"), parent=None, index=0)])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert parsed.rev == 1
        assert len(parsed.ops) == 1
        op = parsed.ops[0]
        assert isinstance(op, CreatePatch)
        assert op.key == "a"

    def test_remove_patch(self):
        msg = PatchMessage(rev=2, ops=[RemovePatch(key="x")])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert isinstance(parsed.ops[0], RemovePatch)
        assert parsed.ops[0].key == "x"

    def test_replace_patch(self):
        msg = PatchMessage(rev=3, ops=[ReplacePatch(key="r", node=_nd("r", "span"))])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert isinstance(parsed.ops[0], ReplacePatch)
        assert parsed.ops[0].node.tag == "span"

    def test_reorder_patch(self):
        msg = PatchMessage(rev=4, ops=[ReorderPatch(parent="p", ordered_keys=["b", "a"])])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert isinstance(parsed.ops[0], ReorderPatch)
        assert parsed.ops[0].ordered_keys == ["b", "a"]

    def test_move_patch(self):
        msg = PatchMessage(rev=5, ops=[MovePatch(key="m", to_parent="new_parent", to_index=2)])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert isinstance(parsed.ops[0], MovePatch)
        assert parsed.ops[0].to_parent == "new_parent"

    def test_update_attrs_patch(self):
        msg = PatchMessage(
            rev=6,
            ops=[UpdateAttrsPatch(key="a", set={"class": "active"}, remove=["disabled"])],
        )
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        op = parsed.ops[0]
        assert isinstance(op, UpdateAttrsPatch)
        assert op.set == {"class": "active"}
        assert op.remove == ["disabled"]

    def test_update_styles_patch(self):
        msg = PatchMessage(
            rev=7,
            ops=[UpdateStylesPatch(key="s", set={"color": "red"}, remove=["font-size"])],
        )
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        op = parsed.ops[0]
        assert isinstance(op, UpdateStylesPatch)
        assert op.set == {"color": "red"}

    def test_set_text_patch(self):
        msg = PatchMessage(rev=8, ops=[SetTextPatch(key="t", text="hello world")])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        op = parsed.ops[0]
        assert isinstance(op, SetTextPatch)
        assert op.text == "hello world"

    def test_multiple_ops(self):
        msg = PatchMessage(
            rev=9,
            ops=[
                RemovePatch(key="old"),
                CreatePatch(key="new", node=_nd("new"), parent="root", index=0),
            ],
        )
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert len(parsed.ops) == 2
        assert isinstance(parsed.ops[0], RemovePatch)
        assert isinstance(parsed.ops[1], CreatePatch)


class TestDiscriminatedUnion:
    """The op field correctly discriminates the union type."""

    def test_invalid_op_rejected(self):
        with pytest.raises(ValidationError):
            PatchMessage.model_validate({"rev": 1, "ops": [{"op": "bogus", "key": "x"}]})

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            PatchMessage.model_validate({"rev": 1, "ops": [{"op": "create", "key": "x"}]})  # missing 'node'

    def test_empty_ops_ok(self):
        msg = PatchMessage(rev=1, ops=[])
        raw = msg.model_dump_json()
        parsed = PatchMessage.model_validate_json(raw)
        assert parsed.ops == []
