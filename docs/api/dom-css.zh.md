# DOM 与 CSS

> [English version](dom-css.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

组件之下的类型化 DOM 层——原始 HTML 元素、`Styles`、`Color`、
`DomEvent` 负载，以及底层拖拽原语。从 `neony.dom` 导入。

## `Color`

```python
Color(name="white")
Color(hex="#ff6b6b")
Color(rgb=(255, 107, 107))
Color(rgba=(255, 107, 107, 0.5))
Color(var="--color-accent")  # 主题令牌
```

## `Styles`

类型化 CSS 属性模型 — 颜色、尺寸、弹性布局、间距、排版、边框(含单角圆角)、
backdrop-filter 等。

```python
Styles(
    display="flex",
    flex_direction="column",
    gap="12px",
    padding="24px",
    background_color=Color(var="--color-surface-glass-bg"),
    backdrop_filter="blur(16px)",
    border_radius="12px",
    border_top_right_radius="12px",
    user_select="none",  # 自动输出 user-select + -webkit/-moz 前缀
)
```

需要浏览器前缀的属性（`backdrop-filter`、`user-select`）会自动输出带
前缀的变体——一个 Python 字段，覆盖全部写法。

## `DomEvent`

交付给事件处理器的事件负载:

```python
async def handler(event: DomEvent) -> None:
    event.key  # 元素标识
    event.type  # "click" | "input" | "scroll" | ...
    event.value  # 元素相关值
    event.source  # "user" | "program"
```

携带这些字段的事件会带上相应富字段:修饰键（`ctrl_key` / `shift_key` /
`alt_key` / `meta_key`）、鼠标坐标（`x` / `y` / `offset_x` / `offset_y`）、
指针增量（`movement_x` / `movement_y` / `pointer_type`）、滚轮增量
（`delta_x` / `delta_y` / `delta_mode`）、滚动位置（`scroll_top` /
`scroll_left` —— 实际滚动元素的位置，派发到最近的带 key 祖先）、剪贴板数据
（`clipboard_text` / `clipboard_html`）、
应用内拖拽载荷（`drag_payload`）、以及拖放文件（`drop_files`）。

## 原始元素

每个 HTML 元素都是类：`Div`、`Span`、`Body`、`H1`–`H6`、
`Input`、`Button`、`Form`、`Table` … 共享链式事件 API，
支持 `build()`（HTML 字符串）和 `to_node()`（可挂载节点）。

```python
from neony.dom import Color, Div, Styles

card = Div(
    styles=Styles(padding="24px", background_color=Color(var="--color-surface")),
    container=["Hello"],
)
```

## 拖拽与重排

低层拖拽 API 可用于任意元素。设置 `drag_payload` 让元素可拖拽，并为其
声明稳定的载荷；drop 时载荷通过 `DomEvent.drag_payload` 交回，位置由
`event.x` / `event.y` / `offset_x` / `offset_y` 给出：

```python
item = Div(key="row-1", drag_payload="row-1")  # 可拖拽 + 声明载荷
item.on_dragstart(lambda e: print("dragging", e.drag_payload))
item.on_dragend(lambda e: print("drag finished"))

drop_zone.on_drop(lambda e: reorder(e.drag_payload, e.key, e.offset_y))  # 读回载荷
```

- 元素与组件均可监听 `dragstart` / `dragenter` / `dragover` /
  `dragleave` / `drop` / `dragend`。
- `dragover` / `drop` 已被处理，任意带 key 元素都是合法 drop 目标，
  拖入文件也不会让 webview 导航离开。
- 应用内拖拽过程中，插入点显示虚线落点槽；drop 时卡片动画重排到最终顺序。
