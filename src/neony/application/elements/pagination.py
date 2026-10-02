"""Pagination — bounded page navigation with ellipsis compression."""

from __future__ import annotations

from neony.application.theme import stub
from neony.dom import Button as _ButtonElem
from neony.dom import Color, Div, DomEvent, Span, Styles

from .base import Component
from .icon import Icon

_ROOT = Styles(display="flex", align_items="center", gap="4px", flex_wrap="wrap")
_PAGE = Styles(
    display="inline-flex",
    align_items="center",
    justify_content="center",
    min_width="32px",
    height="32px",
    padding="0 7px",
    border="none",
    border_radius="7px",
    background_color=Color(name="transparent"),
    color=stub.text_primary,
    font_size="13px",
    cursor="pointer",
)
_ACTIVE = _PAGE.model_copy(update={"background_color": stub.accent, "color": stub.on_accent})
_DISABLED = _PAGE.model_copy(update={"color": stub.text_secondary, "cursor": "default", "opacity": 0.45})
_ELLIPSIS = _PAGE.model_copy(update={"cursor": "default", "color": stub.text_secondary})


class Pagination(Component):
    """A page selector with previous/next controls and ellipses."""

    _bound_events: frozenset[str] = frozenset({"change", "click", "keydown"})
    _value_event: str | None = "change"

    def __init__(
        self,
        value: int = 1,
        page_count: int = 1,
        *,
        siblings: int = 1,
        boundary: int = 1,
        disabled: bool = False,
    ) -> None:
        if page_count < 1:
            raise ValueError("Pagination: page_count must be >= 1")
        if siblings < 0 or boundary < 0:
            raise ValueError("Pagination: siblings and boundary must be non-negative")
        super().__init__()
        self._page_count = page_count
        self._siblings = siblings
        self._boundary = boundary
        self._disabled = disabled
        self._value = max(1, min(page_count, int(value)))
        self._root = Div(styles=_ROOT, args={"role": "navigation", "aria-label": "Pagination"}, container=[])
        self._root.bubble_events = True
        self._bind(self._root, "keydown")
        self._render()

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, value: int) -> None:
        self._value = max(1, min(self._page_count, int(value)))
        self._render()
        self._mirror_value(self._value)

    @property
    def page_count(self) -> int:
        return self._page_count

    @page_count.setter
    def page_count(self, value: int) -> None:
        if value < 1:
            raise ValueError("Pagination: page_count must be >= 1")
        self._page_count = value
        self._value = min(self._value, value)
        self._render()

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        self._render()

    def _pages(self) -> list[int | None]:
        pages = {1, self._page_count, self._value}
        for delta in range(1, self._siblings + 1):
            pages.add(self._value - delta)
            pages.add(self._value + delta)
        for delta in range(self._boundary):
            pages.add(1 + delta)
            pages.add(self._page_count - delta)
        ordered = sorted(page for page in pages if 1 <= page <= self._page_count)
        output: list[int | None] = []
        previous = 0
        for page in ordered:
            if previous and page - previous > 1:
                output.append(None)
            output.append(page)
            previous = page
        return output

    def _button(
        self,
        content: str | list,
        *,
        page: int | None,
        active: bool = False,
        disabled: bool = False,
        label: str | None = None,
    ) -> _ButtonElem:
        styles = _DISABLED if disabled else (_ACTIVE if active else _PAGE)
        args = {"aria-current": "page"} if active else {}
        if label:
            args["aria-label"] = label
        button = _ButtonElem(type="button", container=content, styles=styles, disabled=disabled, args=args)
        button.bubble_events = True
        if page is not None and not disabled:
            button.on("click", self._make_page_handler(page))
        return button

    def _render(self) -> None:
        self._root.container = []
        prev_disabled = self._disabled or self._value <= 1
        next_disabled = self._disabled or self._value >= self._page_count
        self._root.container.append(
            self._button(
                [Icon._font("chevron_left").render("16px")],
                page=self._value - 1 if self._value > 1 else None,
                disabled=prev_disabled,
                label="Previous page",
            )
        )
        for page in self._pages():
            if page is None:
                self._root.container.append(Span(container=["..."], styles=_ELLIPSIS))
            else:
                self._root.container.append(
                    self._button(
                        [str(page)],
                        page=page,
                        active=page == self._value,
                        disabled=self._disabled,
                        label=f"Page {page}",
                    )
                )
        self._root.container.append(
            self._button(
                [Icon._font("chevron_right").render("16px")],
                page=self._value + 1 if self._value < self._page_count else None,
                disabled=next_disabled,
                label="Next page",
            )
        )

    def _make_page_handler(self, page: int):
        async def handler(event: DomEvent) -> None:
            event.source = "user"
            self.value = page
            event.value = page
            await self._dispatch("change", event)

        return handler

    async def _on_event(self, event_type: str, event: DomEvent) -> None:
        if event_type == "keydown":
            key = event.value
            if key == "ArrowLeft":
                changed = self._select_relative(-1, event)
            elif key == "ArrowRight":
                changed = self._select_relative(1, event)
            elif key == "Home":
                self.value = 1
                event.value = 1
                changed = True
            elif key == "End":
                self.value = self._page_count
                event.value = self._page_count
                changed = True
            else:
                changed = False
            if changed:
                await self._dispatch("change", event)
                event.value = key
        await self._dispatch(event_type, event)

    def _select_relative(self, delta: int, event: DomEvent) -> bool:
        target = max(1, min(self._page_count, self._value + delta))
        if target != self._value:
            self.value = target
            event.value = target
            return True
        return False
