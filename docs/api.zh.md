# Neony API 参考

> [English Reference](api.en.md)

---

## 核心

### `NeonApplication`

应用对象 — 持有窗口、桥接、主题与共享状态。用 `Config` 构造,
组装 `Page`,然后 `run()`。

```python
from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # 共享可变状态
app.theme.set_mode("light")  # 切换主题


def main() -> None:
    app.run(page)
```

**属性:** `config`, `state`, `theme`, `ready_handler`

**窗口方法**(全部异步):
`set_title(title)`, `set_size(w, h)`, `minimize()`, `toggle_maximize()`,
`is_maximized()`, `set_fullscreen(f)`, `start_dragging()`, `close()`,
`apply_blur(color?)`, `apply_acrylic(color?)`, `apply_mica()`,
`clear_effect(effect)`, `eval_js(script)`

**主题与渲染:**
`sync_theme()`, `set_background(url)`, `render()`

### `launch()`

一行式入口 — 从关键字参数构建 `Config`。

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

接受全部 `WindowConfig` / `WebViewConfig` 字段,
以及 `mount_selector` 和 `auto_render`。

### `Config`, `WindowConfig`, `WebViewConfig`

Pydantic 配置模型。`WindowConfig` 负责几何与外观
(`title`, `width`, `height`, `decorations`, `transparent`,
`always_on_top`, `resizable` …)。`WebViewConfig` 负责运行时
(`devtools`, `incognito`, `user_agent`, `javascript` …)。

### `Page`

顶层弹性列容器。两层结构:全屏背景层 + 限宽居中的内容列。

```python
Page(gap="16px", padding="24px", max_width="720px")
Page(fill=True, radius="12px")  # 装饰性布局
```

**参数:** `direction`, `gap`, `padding`, `align`, `justify`,
`width`, `max_width`, `glass`, `fill`, `radius`

`fill=True` 撑满窗口高度。`radius` 圆角窗口边框(用于透明无边框窗口)。

**方法:** `add(child)`(链式), `build()` → DOMElement

### 多窗口

`run()` 接受多个页面,每个页面打开一个窗口。所有窗口共享同一事件循环
与 `app.state` 命名空间;事件处理器只重渲染事件来源窗口。

```python
app = NeonApplication(Config(...))
app.run(page_one, page_two)


async def on_ready() -> None:
    await app.set_title("Counter", window_index=0)
    await app.set_title("Display", window_index=1)


app.ready_handler = on_ready
```

每个窗口控制方法都接受 `window_index`(默认 0)。
`launch([page_one, page_two], ...)` 也接受列表。

---

## 组件

所有组件继承 `Component` — 链式 `on_*` 方法、状态属性、源感知事件。
从 `neony.application.elements` 导入。

### `Button`

```python
Button("Primary")  # 强调背景
Button("Ghost", variant="ghost")  # 描边表面
Button("Delete", variant="danger")  # 危险色
Button("Glass", glass=True)  # 磨砂变体
Button("Ok", disabled=True)  # 置灰
button.on_click(handler)  # 点击事件
```

### `Checkbox`

```python
cb = Checkbox("Pizza")
cb.checked = True  # 编程设置 — 不触发回调
cb.on_change(lambda e: print(e.value))  # value = 是否勾选
```

### `Input`

```python
inp = Input(placeholder="你的名字…", type="text")  # text | password | email | number …
inp.on_input(lambda e: print(e.value))  # 实时值
```

### `Heading` & `Text`

```python
Heading("标题", level=1)  # h1–h6
Text("正文")  # 主文字
Text("次要", role="secondary")  # 次要文字
Text("错误", role="danger")  # 危险文字
Text("成功", role="success")  # 成功文字
```

### `Tabs`

```python
tabs = Tabs(glass=True)
tabs.add("一", panel_one)
tabs.add("二", panel_two)
tabs.active = 1  # 编程切换
tabs.active_key  # 当前面板 key
```

---

## 布局

```python
VStack(a, b, gap="12px", align="stretch")  # 纵向
HStack(a, Spacer(), b, gap="8px")  # 横向,Spacer 推挤
Flex(*items, direction="row", wrap="wrap", gap="8px")  # 完全控制
Separator()  # 分隔线
GlassPanel(Heading("磨砂"), background=url, grow=True)  # 磨砂舞台
```

- `VStack` / `HStack` / `Flex` 接受 `grow` 撑满剩余空间。
- `GlassPanel`: 半透明表面 + 背景模糊;`background=url` 在面板内绘制图片;
  `grow=True` 撑满父区域;`radius` 覆盖默认 12px 圆角。

---

## 窗口装饰

### `TitleBar`

无边框窗口的自定义标题栏。需 `WindowConfig(decorations=False)`。

```python
titlebar = TitleBar("My App")  # 零配置,拖动/最小化/最大化/关闭
titlebar.on_close(lambda e: print("bye"))  # 附加回调
titlebar.override_close(confirm_close)  # 完全接管关闭
```

**参数:** `title`, `show_minimize`, `show_maximize`, `show_close`, `height`

标题栏即拖拽区域(双击最大化);控制按钮通过 WindowControls 桥接自动路由。

### `Sidebar` & `SidebarItem`

垂直导航,与 `TitleBar` 同款玻璃。

```python
sidebar = Sidebar(
    SidebarItem("首页", icon="🏠"),
    SidebarItem("设置", icon="⚙️"),
    active_key="home",
)
sidebar.on_change(lambda e: switch(e.value))  # value = item key
sidebar.active_key = "settings"  # 编程切换,不触发回调
```

**参数:** `Sidebar(width, glass, corner_radius)`,
`SidebarItem(label, key, icon, active)`

---

## 主题

三套预设 — `DARK`, `LIGHT`, `DEEP_BLUE` — 以 CSS 自定义属性暴露。

```python
app.theme.set_mode("dark")  # dark | light | deep-blue
app.theme.toggle()  # 循环切换
await app.sync_theme()  # 重新注入变量
```

令牌族: `--color-bg`, `--color-surface`,
`--color-text-primary` / `--color-text-secondary`, `--color-accent`,
`--color-danger`, `--color-success`, `--color-border`,
`--color-*-glass*`(磨砂变体)。

组件通过 `Color(var="--color-*")` 引用令牌,切换主题零 DOM diff 重绘。

自定义主题:

```python
from neony.application import Theme
my_theme = Theme(mode="dark", bg="#0a0a0f", accent="#7c4dff", ...)
app.theme = my_theme
await app.sync_theme()
```

---

## DOM 原语

从 `neony.dom` 导入。

### `Color`

```python
Color(name="white")
Color(hex="#ff6b6b")
Color(rgb=(255, 107, 107))
Color(rgba=(255, 107, 107, 0.5))
Color(var="--color-accent")  # 主题令牌
```

### `Styles`

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
)
```

### `DomEvent`

JS 转发的事件负载:

```python
async def handler(event: DomEvent) -> None:
    event.key  # 元素标识
    event.type  # "click" | "input" | ...
    event.value  # 元素相关值
    event.source  # "user" | "program"
```

### 原始元素

每个 HTML 元素都是类:`Div`, `Span`, `Body`, `H1`–`H6`,
`Input`, `Button`, `Form`, `Table` … 共享链式事件 API,
支持 `build()`(HTML 字符串)和 `to_node()`(响应式快照)。

```python
from neony.dom import Color, Div, Styles

card = Div(
    styles=Styles(padding="24px", background_color=Color(var="--color-surface")),
    container=["Hello"],
)
```
