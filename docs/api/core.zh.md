# 核心 API

> [English version](core.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

应用对象、入口函数与窗口生命周期。从 `neony.application` 导入。

## `NeonApplication`

应用对象 — 持有窗口、桥接、主题与共享状态。用 `Config` 构造，
组装 `Page`，然后 `run()`。

```python
from neony.application import Config, NeonApplication, Page, Theme, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="Demo", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.count = 0  # 共享可变状态
app.theme = Theme.get("light")  # run() 前选定初始预设


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

所有窗口共享同一个 `state` 对象，是
[`SharedSignal`](reactive.zh.md#sharedsignal) 之外跨窗口数据的命令式方案。

**属性:** `config`， `state`， `theme`， `ready_handler`， `close_handler`

**窗口方法**(全部异步):
`set_title(title)`， `set_size(w, h)`， `minimize()`， `toggle_maximize()`，
`is_maximized()`， `set_fullscreen(f)`， `start_dragging()`， `close()`，
`apply_blur(color?)`， `apply_acrylic(color?)`， `apply_mica()`，
`clear_effect(effect)`， `eval_js(script)`， `set_icon(icon)`

**应用方法:** `exit(code=0)` — 优雅退出整个应用(同步)。`close_to_tray=True`
时关窗只会隐藏应用，`exit()` 才是真正的退出途径——例如托盘菜单的
"退出"项。

**主题与渲染:**
`set_theme(theme)`， `sync_theme()`， `set_background(url)`， `render()`

**文件对话框**（均为 async — 系统原生）：
`open_file(...) -> str | None`，`open_files(...) -> list[str]`，
`save_file(...) -> str | None`，`select_folder(...) -> str | None`。
取消时返回 `None`（多选返回 `[]`）；对话框无法显示同样返回 `None`
— 绝不抛异常。

```python
path = await app.open_file(
    title="打开图片", default_dir="~/Pictures", filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
)
if path is None:
    return  # 取消
paths = await app.open_files(...)  # 取消返回 []
dest = await app.save_file(default_name="out.txt")  # str | None
folder = await app.select_folder()  # str | None
```

对话框就是平台自己的 — Linux 用 zenity（大多数桌面发行版自带）、
macOS 用 `osascript`、Windows 用 PowerShell，另有 tkinter 回退 —
以子进程方式弹出，对话框开启期间应用事件循环照常运转。Neony
不绘制任何东西：外观、导航与过滤完全由操作系统提供。
`filetypes` 映射到原生过滤器界面（`[("PNG images", "*.png"),
("All files", "*.*")]`）；`default_dir` / `default_name` 预选起始
位置。无 WebView、无进程内 tkinter 窗口、无内置对话框组件。

## `launch()`

一行式入口 — 从关键字参数构建 `Config`。

```python
from neony.application import Page, launch

launch(page, title="Demo", width=480, height=360, devtools=True)
```

接受全部 `WindowConfig` / `WebViewConfig` 字段，
以及 `mount_selector`、`auto_render` 和 `state`(自定义状态对象 ——
见 [`NeonApplication`](#neonapplication))。

## `Config`， `WindowConfig`， `WebViewConfig`

Pydantic 配置模型。`WindowConfig` 负责几何与外观
(`title`， `width`， `height`， `decorations`， `transparent`，
`always_on_top`， `resizable`， `icon` …)。`WebViewConfig` 负责运行时
(`devtools`， `incognito`， `user_agent`， `javascript` …)。

**`WindowConfig.icon`** — 文件路径(PNG、ICO …)或原始 RGBA 数据
`(bytes, width, height)`，显示在*带系统装饰*窗口的 OS 窗口栏中。
无边框窗口没有 OS 装饰——内联图标见 [`TitleBar`](layout-chrome.zh.md#titlebar) 的 `icon`
参数，运行时更换见 [`NeonApplication.set_icon()`](#neonapplication)。

**`WebViewConfig.default_context_menus`** — 默认关闭：应用自绘菜单
（`Menu` 组件、`contextmenu` 事件），webview 的原生右键菜单会盖住
它们。需要平台默认菜单时设为 `True`。

## `Page`

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

## 生命周期

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
[`TitleBar.override_close`](layout-chrome.zh.md#titlebar)。

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

## 多窗口

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

## 导航策略

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

## `Tray` & `TrayItem` — 系统托盘（原生菜单）

托盘图标 + 原生右键菜单，基于 lumiview .dev4（muda 菜单 + TrayIcon）。
`run()` 前赋值 `app.tray`，应用启动后图标自动创建。

```python
from neony.application import Tray, TrayItem

app.tray = Tray(
    icon="tray.png",  # 文件路径或原始 RGBA(bytes, width, height)
    tooltip="我的应用",
    items=[
        TrayItem("显示窗口", id="show", on_activate=show_handler),
        TrayItem.separator(),
        TrayItem("退出", id="quit", accelerator="CmdOrCtrl+Q", on_activate=quit_handler),
    ],
    menu_on_left_click=False,  # 把左键留给 on_left_click
    on_left_click=toggle_handler,  # 同步或异步
    close_to_tray=True,  # 关窗隐藏应用而非退出
)
```

- `TrayItem` — `text`，可选 `id`（激活回调携带）、`accelerator`（muda
  语法；Windows 可能无法从键盘触发）、`on_activate`（同步或异步，在
  asyncio 循环执行）、`checked=True` 渲染勾选项；
  `TrayItem.separator()` 为分隔线。
- `close_to_tray=True` — 拦截所有窗口的关闭请求并隐藏整个应用
  （从菜单 / 托盘点击恢复；macOS 上 Dock 点击经 `ReopenEvent`）。
  `Page.on_close` 处理器仍会执行。
- `on_left_click` — `menu_on_left_click=False` 时左键松开触发
  （典型用途：切换窗口）。
- 平台注意：**Linux 需要 libayatana-appindicator**；tooltip 不支持、
  菜单创建后不可替换。参见 [`demo_tray.py`](../../demo_tray.py)。
