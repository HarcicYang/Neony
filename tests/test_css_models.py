"""Unit tests for the typed CSS value models and length helpers."""

from __future__ import annotations

from neony.dom import BoxShadow, Color, Shadow, Styles, calc, pct, px


class TestLengthHelpers:
    def test_px_numbers(self) -> None:
        assert px(200) == "200px"
        assert px(0) == "0"  # zero stays bare
        assert px(8.5) == "8.5px"

    def test_px_strings_pass_through(self) -> None:
        assert px("200px") == "200px"
        assert px("50%") == "50%"
        assert px("10px 14px") == "10px 14px"
        assert px("auto") == "auto"
        assert px("calc(100% - 8px)") == "calc(100% - 8px)"

    def test_pct(self) -> None:
        assert pct(50) == "50%"
        assert pct(50.5) == "50.5%"
        assert pct("42.00%") == "42.00%"

    def test_calc(self) -> None:
        assert calc("100% - 8px") == "calc(100% - 8px)"
        assert calc("16px + 2 * 24px") == "calc(16px + 2 * 24px)"


class TestFlexFields:
    def test_flex_grow_accepts_numbers(self) -> None:
        # Bare numbers store as-is; the render loop str()s them.
        assert Styles(flex_grow=2).model_dump()["flex_grow"] == 2
        assert Styles(flex_grow="1").model_dump()["flex_grow"] == "1"
        assert Styles(flex_shrink=0).model_dump()["flex_shrink"] == 0


class TestShadow:
    def test_zero_stays_bare(self) -> None:
        s = Shadow(x=0, y=8, blur=32, color=Color(rgba=(0, 0, 0, 0.25)))
        assert s.model_dump() == "0 8px 32px rgba(0, 0, 0, 0.25)"

    def test_inset(self) -> None:
        s = Shadow(inset=True, blur=0, spread="4px", color=Color(var="--color-accent"))
        assert s.model_dump() == "inset 0 0 0 4px var(--color-accent)"

    def test_str_repr_delegate_to_serializer(self) -> None:
        s = Shadow(x=0, y=2, blur=6, color=Color(var="--color-shadow"))
        assert str(s) == s.model_dump()
        assert repr(s) == s.model_dump()


class TestBoxShadow:
    def test_layers_comma_joined(self) -> None:
        b = BoxShadow(
            layers=[
                Shadow(x=0, y=4, blur=16, color=Color(var="--color-shadow")),
                Shadow(x=0, y=0, blur=20, color=Color(var="--color-accent-glass")),
            ]
        )
        assert b.model_dump() == "0 4px 16px var(--color-shadow), 0 0 20px var(--color-accent-glass)"

    def test_str_delegates(self) -> None:
        b = BoxShadow(layers=[Shadow(x=0, y=8, blur=32, color=Color(var="--color-shadow"))])
        assert str(b) == "0 8px 32px var(--color-shadow)"
