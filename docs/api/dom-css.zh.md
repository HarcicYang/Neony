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
前缀的变体——一个 Python 字段，覆盖所有引擎写法。

## `DomEvent`

JS 转发的事件负载:

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
`scroll_left` —— 实际滚动元素的位置，派发到最近的带 key 祖先，
高频所以渲染走延迟路径）、剪贴板数据（`clipboard_text` / `clipboard_html`）、
应用内拖拽载荷（`drag_payload`）、以及拖放文件（`drop_files`）。

## 原始元素

每个 HTML 元素都是类:`Div`， `Span`， `Body`， `H1`–`H6`，
`Input`， `Button`， `Form`， `Table` … 共享链式事件 API，
支持 `build()`(HTML 字符串)和 `to_node()`(响应式快照)。

```python
from neony.dom import Color, Div, Styles

card = Div(
    styles=Styles(padding="24px", background_color=Color(var="--color-surface")),
    container=["Hello"],
)
```

## 拖拽与重排

在 [`Reorder`](components.zh.md#reorder-组件) 组件之下，引擎委托完整的拖拽生命周期——`dragstart` / `dragenter` /
`dragover` / `dragleave` / `drop` / `dragend`——drop 载荷经
`dataTransfer` 传递。设置 `drag_payload` 让元素可拖拽，并声明引擎在
dragstart 时交给 `dataTransfer.setData` 的载荷（必须同步——Python 往返
来不及）：

```python
item = Div(key="row-1", drag_payload="row-1")  # 可拖拽 + 声明载荷
item.on_dragstart(lambda e: print("dragging", e.drag_payload))
item.on_dragend(lambda e: print("drag finished"))

drop_zone.on_drop(lambda e: reorder(e.drag_payload, e.key, e.offset_y))  # 读回载荷
```

- `drag_payload` 序列化为 `draggable="true"` + `data-neony-drag`；引擎在
  dragstart 处理器里调用 `setData("application/x-neony", payload)`，并在
  `drop` 时读回进 `DomEvent.drag_payload`。
- `dragover`/`drop` 已被引擎 `preventDefault()`，所以任意带 key 元素都是
  合法 drop 目标（且 webview 不会导航到拖入的文件）。
- 拖拽过程中引擎在插入点显示虚线落点槽（卡片纯位置位移、FLIP 动画），
  drop 时以匹配动画沉降到最终顺序。纯引擎本地实现——零 IPC、不缩放元素。
