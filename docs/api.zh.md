# Neony API 参考

> [English Reference](api.en.md)

---

## 核心

### `NeonApplication`

应用对象 — 持有窗口、桥接、主题与共享状态。用 `Config` 构造，
组装 `Page`，然后 `run()`。

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

**类型化 state:** `state` 默认是裸 `SimpleNamespace`。通过 `state=` 参数
传入任意对象 —— `dataclass`、pydantic 模型或普通类 —— 可获得类型安全的
属性访问与 IDE 补全：

```python
from dataclasses import dataclass


@dataclass
class AppState:
    count: int = 0
    user_name: str = ""


app = NeonApplication(Config(...), state=AppState())
app.state.count += 1  # 类型为 int
app.state.user_name = "Ada"
```

所有窗口共享同一个 `state` 对象，是 [`SharedSignal`](#sharedsignal)
之外跨窗口数据的命令式方案。

**属性:** `config`， `state`， `theme`， `ready_handler`， `close_handler`

**窗口方法**(全部异步):
`set_title(title)`， `set_size(w, h)`， `minimize()`， `toggle_maximize()`，
`is_maximized()`， `set_fullscreen(f)`， `start_dragging()`， `close()`，
`apply_blur(color?)`， `apply_acrylic(color?)`， `apply_mica()`，
`clear_effect(effect)`， `eval_js(script)`， `set_icon(icon)`

**主题与渲染:**
`sync_theme()`， `set_background(url)`， `render()`

### `launch()`

一行式入口 — 从关键字参数构建 `Config`。

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

接受全部 `WindowConfig` / `WebViewConfig` 字段，
以及 `mount_selector`、`auto_render` 和 `state`(自定义状态对象 ——
见 [`NeonApplication`](#neonapplication))。

### `Config`， `WindowConfig`， `WebViewConfig`

Pydantic 配置模型。`WindowConfig` 负责几何与外观
(`title`， `width`， `height`， `decorations`， `transparent`，
`always_on_top`， `resizable`， `icon` …)。`WebViewConfig` 负责运行时
(`devtools`， `incognito`， `user_agent`， `javascript` …)。

**`WindowConfig.icon`** — 文件路径(PNG、ICO …)或原始 RGBA 数据
`(bytes, width, height)`，显示在*带系统装饰*窗口的 OS 窗口栏中。
无边框窗口没有 OS 装饰——内联图标见 [`TitleBar`](#titlebar) 的 `icon`
参数，运行时更换见 [`set_icon()`](#neonapplication)。

### `Page`

顶层弹性列容器。两层结构:全屏背景层 + 限宽居中的内容列。

```python
Page(gap="16px", padding="24px", max_width="720px")
Page(fill=True, radius="12px")  # 装饰性布局
```

**参数:** `direction`， `gap`， `padding`， `align`， `justify`，
`width`， `max_width`， `glass`， `fill`， `radius`

`fill=True` 撑满窗口高度。`radius` 圆角窗口边框(用于透明无边框窗口)。

**方法:** `add(child)`(链式)， `on_close(fn)`(链式 —— 见
[生命周期](#生命周期))， `build()` → DOMElement

### 生命周期

启动与收尾都用普通属性声明 —— 框架内部负责与原生窗口事件的接线。

```python
async def on_ready() -> None:
    print("窗口已就绪")


async def on_shutdown() -> None:
    save_state(app.state)  # 所有窗口关闭后执行


app.ready_handler = on_ready
app.close_handler = on_shutdown
```

`close_handler` 恰好执行一次:最后一个窗口关闭后、事件循环停止前 ——
异步清理的最后机会。

**按窗口关闭** — `Page.on_close(fn)`(同步或异步，链式，可注册多个)。
该页面窗口关闭时触发，在真正关闭之前执行;异常只记录日志，绝不阻止
关闭。若要"关闭前确认"对话框，请接管标题栏关闭按钮 —— 见
[`TitleBar.override_close`](#titlebar)。

```python
page = Page()
page.on_close(lambda: print("窗口关闭中"))
```

**焦点追踪** — `Page.on_focus(fn)` / `Page.on_blur(fn)`(同步或异步，
链式，可注册多个)在页面窗口获得 / 失去键盘焦点时触发——用于暂停
定时器、更新状态栏，或在多窗口应用中判断哪个窗口处于活动状态。

```python
page = Page()
page.on_focus(lambda: print("活跃"))
page.on_blur(lambda: print("非活跃"))
```

### 导航策略

页面内的链接或重定向会把 webview 导航走、离开你的 UI。Neony 为每个
窗口安装安全默认值——拦截所有导航、拒绝所有新窗口请求、取消所有
下载——没有你的允许，什么都不会逃逸。按页面覆盖即可。

**决策型策略** — 单个处理器，最后注册的胜出(决策无法合并):

```python
# 只允许你自己的站点，其余全部拦截。
page.on_navigation(lambda url: url.startswith("https://myapp.example"))

# target="_blank" 链接与 window.open():返回 "allow" 或 "deny"。
page.on_new_window(lambda url: "deny")

# 返回 True 允许、False 取消，或返回路径把下载重定向到自定义位置。
page.on_download_started(lambda url, path: "/downloads/")
```

**通知型** — 多个处理器堆叠，全部执行:

```python
# url、最终路径(取消时为 None)、成功标志。
page.on_download_completed(lambda url, path, ok: print(f"下载完成 {path}"))
```

### 多窗口

`run()` 接受多个页面，每个页面打开一个窗口。所有窗口共享同一事件循环
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

**参数:** `title`， `icon`， `show_minimize`， `show_maximize`，
`show_close`， `height`

`icon` 在标题左侧绘制一个小图标(URL 或文件路径)——无边框模式下
`WindowConfig.icon` 的对应物，因为无边框窗口没有 OS 装饰来承载它。

标题栏即拖拽区域(双击最大化);控制按钮带内部 `data-window-action`
属性,经 WindowControls 桥接自动路由 — 用户无需感知的实现细节。

### `Sidebar` & `SidebarItem`

垂直导航，与 `TitleBar` 同款玻璃。

```python
sidebar = Sidebar(
    SidebarItem("首页", icon="🏠"),
    SidebarItem("设置", icon="⚙️"),
    active_key="home",
)
sidebar.on_change(lambda e: switch(e.value))  # value = item key
sidebar.active_key = "settings"  # 编程切换,不触发回调
```

**参数:** `Sidebar(width, glass, corner_radius)`，
`SidebarItem(label, key, icon, active)`

点击条目任意位置（包括图标与文字）都生效——条目级事件会从其子元素冒泡上来。

---

## 主题

三套预设 — `DARK`， `LIGHT`， `DEEP_BLUE` — 以 CSS 自定义属性暴露。

```python
app.theme.set_mode("dark")  # dark | light | deep-blue
app.theme.toggle()  # 循环切换
await app.sync_theme()  # 重新注入变量
```

令牌族: `--color-bg`， `--color-surface`，
`--color-text-primary` / `--color-text-secondary`， `--color-accent`，
`--color-danger`， `--color-success`， `--color-border`， `--color-shadow`，
`--color-*-glass*`(磨砂变体)。

组件通过 `Color(var="--color-*")` 引用令牌，切换主题零 DOM diff 重绘。

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
    user_select="none",  # 自动输出 user-select + -webkit/-moz 前缀
)
```

需要浏览器前缀的属性（`backdrop-filter`、`user-select`）会自动输出带
前缀的变体——一个 Python 字段，覆盖所有引擎写法。

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

## 响应式

从 `neony.dom` 导入。V-DOM diff 引擎响应整棵树的变更；这些原语响应
单个状态的变化。

### `Signal`

单一响应式值。用 `signal()` 读取(在 effect/computed 内读取会记录依赖)；
用 `set()` / `update()` 写入。

```python
from neony.dom import Signal

count = Signal(0)
count.get()  # 0
count()  # 同样 — 调用即读取
count.set(5)
count.update(lambda c: c + 1)  # 6 — 原地变更
```

写入相等的值(`==`)不触发通知。

### `Computed`

惰性求值、带缓存的派生值。只在依赖变化时重算；computed 可以依赖
其他 computed。

```python
from neony.dom import Computed, Signal

count = Signal(2)
double = Computed(lambda: count() * 2)
double()  # 4(缓存，直到 count 变化)
```

### `effect()` / `Effect`

立即执行 `fn`，之后每当它读过的 Signal 变化就重新执行。返回可释放的
`Effect`。

```python
from neony.dom import Signal, effect

name = Signal("Neony")
stop = effect(lambda: print(f"hello {name()}"))  # 立即打印
name.set("world")  # 重新执行
stop.dispose()  # 取消所有订阅
```

重跑是合并的:有事件循环时延迟到 `loop.call_soon`；用 `batch()` 做同步合并。

```python
from neony.dom import batch, Signal

count = Signal(0)
effect(lambda: print(count()))  # 打印 0
with batch():
    count.set(1)
    count.set(2)  # 只重跑一次，打印 2
```

### `untrack()`

执行函数但不记录依赖读取。

```python
from neony.dom import Signal, untrack

log = Signal(0)
effect(lambda: untrack(lambda: print(log())))  # 读取但永不订阅
```

### `SharedSignal`

用于跨窗口共享的 `Signal` — 一次写入更新所有绑定了它的窗口(每个窗口
各自调度自己的渲染)。

```python
from neony.dom import SharedSignal

count = SharedSignal(0)
label_a.bind_text(count)  # 窗口 A
label_b.bind_text(count)  # 窗口 B
count.set(1)  # 两个窗口都更新
```

### 声明式绑定

把 Signal 绑定到元素(或组件)上，DOM 自动跟随 — 不再需要手动刷新调用。

```python
from neony.dom import Signal

count = Signal(0)
label.bind_text(count, fmt=str)  # 文本内容
bar.bind_style(count, "opacity", fmt=lambda v: v / 100)  # CSS 属性
img.bind_attr(count, "src")  # HTML 属性
panel.bind_visible(count)  # 假值时 display: none
```

- `bind_text(signal, fmt=str)` — 用单个文本字符串替换元素的子节点
- `bind_style(signal, prop, fmt=None)` — `prop` 是 `Styles` 字段名
  (snake_case)；Signal 值为 `None` 时移除该属性
- `bind_attr(signal, name, fmt=str)` — 写入原始属性袋
- `bind_visible(signal)` — 假值时隐藏(`display: none`)，真值时恢复
  绑定前的 display 值
- `unbind()` — 释放元素上的所有绑定

四个方法在 `Component` 上同样可用(代理到组件的根元素)。绑定写入会把
元素标记为 dirty 并为其窗口调度一次渲染 — 因此无论 Signal 在哪里被
修改(事件处理、定时器、其他窗口)，都无需显式调用 `render()` 就能上屏。

### 脏子树追踪

每次变更都会把元素标记为 dirty 并向上传播到根。渲染时只重新序列化
dirty 元素；未变化的子树复用缓存快照(diff 引擎视其为相同，因此零补丁)。
这是自动的 — `container.append()` 和属性赋值都会参与。
