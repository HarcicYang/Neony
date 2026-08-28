"""Grid container — a responsive CSS-grid layout component.

``GridView`` lays children out in the column tracks described by a typed
:class:`Columns` definition.  Each child is wrapped in a grid item that
absorbs the two classic grid sizing traps: ``min-width: 0`` releases the
automatic track minimum (otherwise one long unbreakable word pins its
track wide and the grid overflows the container), and an inherited
``word-break: break-word`` lets such words wrap inside the item.

``uniform=True`` (the default) stretches every item in a row to the
row's tallest child — the wrapper becomes a nested one-cell grid whose
item stretches both ways, so user elements fill their cell without any
style changes of their own.  ``uniform=False`` keeps items at their
natural height, top-aligned.
"""

from __future__ import annotations

from neony.dom import Columns, Div, DOMElement, Styles

from .base import Component


class GridView(Component):
    """A responsive grid container.

    - ``*children`` — grid contents (Components, DOMElements, or strings);
      each is placed in its own grid item.
    - ``columns`` — a typed :class:`Columns` track definition; ``None``
      defaults to ``Columns.responsive(120)`` (as many 120px columns as
      fit the container).
    - ``gap`` — spacing between tracks (``"12px 8px"`` sets row/column
      gaps separately).
    - ``uniform`` — stretch every item in a row to the row's tallest
      child (default, even card-like tiles); ``False`` keeps natural
      heights, top-aligned.
    - ``padding`` / ``width`` / ``grow`` — container box adjustments
      (``grow`` for mounting inside a flex parent).
    """

    def __init__(
        self,
        *children: Component | DOMElement | str,
        columns: Columns | None = None,
        gap: str = "8px",
        uniform: bool = True,
        padding: str = "0px",
        width: str | None = None,
        grow: int = 0,
    ) -> None:
        super().__init__()
        container_styles = Styles(
            display="grid",
            grid_template_columns=columns if columns is not None else Columns.responsive(120),
            gap=gap,
            padding=padding,
            width=width,
            flex_grow=grow,
        )
        if not uniform:
            # Natural heights.  The default ``stretch`` would pull each
            # wrapper up to the row height while its child stays short —
            # the exact uneven-tile look ``uniform`` exists to avoid.
            container_styles = container_styles.model_copy(update={"align_items": "start"})

        wrapped: list[DOMElement | str] = []
        for child in children:
            if isinstance(child, Component):
                self._track_component(child)
                child = child.build()
            # Every wrapper gets a fresh Styles: Styles instances carry
            # their owner element back for dirty-marking, so they can
            # never be shared between grid items.
            wrapper_styles = Styles(min_width="0", word_break="break-word")
            if uniform:
                # A nested one-cell grid: the child is its only item and
                # stretches both ways, sharing the row height.
                wrapper_styles = wrapper_styles.model_copy(update={"display": "grid"})
            wrapped.append(Div(styles=wrapper_styles, container=[child]))

        self._root = Div(styles=container_styles, container=wrapped)
