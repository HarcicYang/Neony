# Neony Reference / Neony 参考文档

Component and API reference. English is the primary language; Chinese
follows each section.
组件与 API 参考。英语为主,中文紧随其后。

---

## 1. Core / 核心

### `NeonApplication`

The application object — owns the window, the bridge, the theme, and
shared state. Construct with a `Config`, build a `Page`, then `run()`.
应用对象 — 持有窗口、桥接、主题与共享状态。用 `Config` 构造,组装 `Page`,然后 `run()`。

```python
from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # shared state / 共享状态
app.theme.set_mode("light")  # switch theme / 切换主题


def main() -> None:
    app.run(page)
```

**Attributes / 属性:** `config`, `state`, `theme`, `ready_handler`

**Window methods / 窗口方法** (all async / 全部为异步):
`set_title()`, `set_size()`, `minimize()`, `toggle_maximize()`,
`is_maximized()`, `set_fullscreen()`, `start_dragging()`, `close()`,
`apply_blur()`, `apply_acrylic()`, `apply_mica()`, `clear_effect()`,
`eval_js()`

**Theme / rendering / 主题与渲染:** `sync_theme()`, `set_background(url)`,
`render()`

### `launch()`

One-liner entry point — build a `Config` from keyword arguments.
一行式入口 — 从关键字参数构建 `Config`。

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

Accepts all `WindowConfig` / `WebViewConfig` fields plus
`mount_selector` and `auto_render`.
接受全部 `WindowConfig` / `WebViewConfig` 字段,以及 `mount_selector` 和 `auto_render`。

### `Config`, `WindowConfig`, `WebViewConfig`

Pydantic config models. `WindowConfig` covers geometry and appearance
(`title`, `width`, `height`, `decorations`, `transparent`,
`always_on_top`, `resizable`, …). `WebViewConfig` covers the runtime
(`devtools`, `incognito`, `user_agent`, `javascript`, …).
Pydantic 配置模型。`WindowConfig` 负责几何与外观(`title`、`width`、`height`、
`decorations`、`transparent`、`always_on_top`、`resizable` …)。
`WebViewConfig` 负责运行时(`devtools`、`incognito`、`user_agent`、`javascript` …)。

### `Page`

Top-level container. Two layers: a full-viewport backdrop and a
width-constrained, centered content column.
顶层容器。两层结构:全屏背景层 + 限宽居中的内容列。

```python
Page(gap="16px", padding="24px", max_width="720px")
Page(fill=True, radius="12px")  # chrome layouts / 装饰性布局
```

**Options / 参数:** `direction`, `gap`, `padding`, `align`, `justify`,
`width`, `max_width`, `glass`, `fill`, `radius`
(`fill` stretches to the window; `radius` rounds the window frame /
`fill` 撑满窗口,`radius` 圆角窗口边框)

---

## 2. Components / 组件

All components inherit `Component` — fluent `on_*` chaining, state
properties, source-aware events (programmatic changes never fire
callbacks).
所有组件继承 `Component` — 链式 `on_*` 方法、状态属性、源感知事件
(编程式修改不触发回调)。

### `Button`

```python
Button("Primary")  # accent bg / 强调背景
Button("Ghost", variant="ghost")  # bordered surface / 描边表面
Button("Delete", variant="danger")  # danger color / 危险色
Button("Glass", glass=True)  # frosted variant / 磨砂变体
Button("Ok", disabled=True)  # dimmed / 置灰
button.on_click(handler)  # click event / 点击事件
```

### `Checkbox`

```python
cb = Checkbox("Pizza")
cb.checked = True  # programmatic — no callback / 编程设置 — 不触发回调
cb.on_change(lambda e: print(e.value))  # value = checked bool
```

### `Input`

```python
inp = Input(placeholder="Your name…", type="text")  # text | password | email | number …
inp.on_input(lambda e: print(e.value))  # live value / 实时值
```

### `Heading` & `Text`

```python
Heading("Title", level=1)  # h1–h6 / 1–6 级
Text("Body copy")  # primary / 主文字
Text("Muted", role="secondary")  # muted / 次要
Text("Error", role="danger")  # danger / 危险
Text("OK", role="success")  # success / 成功
```

### `Tabs`

```python
tabs = Tabs(glass=True)
tabs.add("One", panel_one)
tabs.add("Two", panel_two)
tabs.active = 1  # programmatic switch / 编程切换
tabs.active_key  # key of the active panel / 当前面板 key
```

---

## 3. Layout / 布局

```python
VStack(child_a, child_b, gap="12px", align="stretch")  # column / 纵向
HStack(a, Spacer(), b, gap="8px")  # row, spacer pushes / 横向,Spacer 推挤
Flex(*items, direction="row", wrap="wrap", gap="8px")  # full control / 完全控制
Separator()  # divider / 分隔线
GlassPanel(Heading("Frosted"), background=url, grow=True)  # frosted stage / 磨砂舞台
```

- `VStack` / `HStack` / `Flex` accept `grow: int` to fill remaining space
  in a parent column/row. 接受 `grow: int` 撑满父容器剩余空间。
- `GlassPanel` — translucent surface with backdrop blur; `background=url`
  paints an image inside the panel; `grow=True` fills the parent region;
  `radius` overrides the default 12px corner radius.
  半透明表面 + 背景模糊;`background=url` 在面板内绘制图片;`grow=True`
  撑满父区域;`radius` 覆盖默认 12px 圆角。

---

## 4. Chrome / 窗口装饰

### `TitleBar`

Custom window chrome for frameless windows. Requires
`WindowConfig(decorations=False)` — the WindowControls bridge scope is
loaded automatically.
无边框窗口的自定义标题栏。需要 `WindowConfig(decorations=False)` —
WindowControls 桥接作用域会自动加载。

```python
titlebar = TitleBar("My App")  # zero config: drag + min/max/close work
titlebar.on_close(lambda e: log("bye"))  # extra callback / 附加回调
titlebar.override_close(confirm_close)  # take over the action / 完全接管
```

**Options / 参数:** `title`, `show_minimize`, `show_maximize`,
`show_close`, `height`

The bar is a drag region (double-click maximizes); control buttons carry
internal `data-window-action` attributes routed through the bridge — an
implementation detail users never see.
标题栏即拖拽区域(双击最大化);控制按钮带内部 `data-window-action`
属性,经桥接路由——用户无需感知的实现细节。

### `Sidebar` & `SidebarItem`

Vertical navigation, glass-matched to `TitleBar`.
垂直导航,与 `TitleBar` 同款玻璃。

```python
sidebar = Sidebar(
    SidebarItem("Home", icon="🏠"),
    SidebarItem("Settings", icon="⚙️"),
    active_key="home",
)
sidebar.on_change(lambda e: switch(e.value))  # value = item key
sidebar.active_key = "settings"  # programmatic, no callback
```

**Options / 参数:** `Sidebar(width, glass, corner_radius)`,
`SidebarItem(label, key, icon, active)`

---

## 5. Theming / 主题

Three presets exposed as CSS custom properties on `:root`.
三套预设,以 CSS 自定义属性暴露在 `:root`。

```python
app.theme.set_mode("dark")  # dark | light | deep-blue
app.theme.toggle()  # cycle / 循环切换
await app.sync_theme()  # re-inject variables / 重新注入变量
```

Token families / 令牌族:`--color-bg`, `--color-surface`,
`--color-text-primary/secondary`, `--color-accent`, `--color-danger`,
`--color-success`, `--color-border`, `--color-shadow`,
`--color-*-glass*`(frosted variants / 磨砂变体)。

Components reference tokens via `Color(var="--color-*")`, so a theme
switch redraws everything with zero DOM diff.
组件通过 `Color(var="--color-*")` 引用令牌,切换主题零 DOM diff 全量重绘。

Custom themes / 自定义主题:

```python
from neony.application import Theme
my_theme = Theme(mode="dark", bg="#0a0a0f", accent="#7c4dff", ...)
app.theme = my_theme
await app.sync_theme()
```

---

## 6. DOM Primitives / DOM 原语

Import from `neony.dom` / 从 `neony.dom` 导入。

### `Color`

```python
Color(name="white")  # CSS keyword / 关键字
Color(hex="#ff6b6b")  # #RRGGBB
Color(rgb=(255, 107, 107))
Color(rgba=(255, 107, 107, 0.5))
Color(var="--color-accent")  # theme token / 主题令牌
```

### `Styles`

Typed CSS properties model — colors, dimensions, flexbox, spacing,
typography, borders (incl. per-corner radii), backdrop-filter, and more.
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

Event payload forwarded from JavaScript:
JS 转发的事件负载:

```python
async def handler(event: DomEvent) -> None:
    event.key  # element identity / 元素标识
    event.type  # "click" | "input" | ...
    event.value  # element-specific / 元素相关值
    event.source  # "user" | "program"
```

### Raw elements / 原始元素

Every HTML element is a class: `Div`, `Span`, `Body`, `H1`–`H6`,
`Input`, `Button`, `Form`, `Table`, … They share the fluent event API
and support `build()` (HTML string) and `to_node()` (reactive snapshot).
每个 HTML 元素都是类:`Div`、`Span`、`Body`、`H1`–`H6`、`Input`、
`Button`、`Form`、`Table` … 共享链式事件 API,支持 `build()`(HTML 字符串)
和 `to_node()`(响应式快照)。

```python
from neony.dom import Color, Div, Styles

card = Div(
    styles=Styles(padding="24px", background_color=Color(var="--color-surface")),
    container=["Hello"],
)
```
