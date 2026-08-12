# Neony API 参考

> [English Reference](api.en.md)

---

## 核心

### `NeonApplication`

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

所有窗口共享同一个 `state` 对象，是 [`SharedSignal`](#sharedsignal)
之外跨窗口数据的命令式方案。

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

**`WebViewConfig.default_context_menus`** — 默认关闭：应用自绘菜单
（`Menu` 组件、`contextmenu` 事件），webview 的原生右键菜单会盖住
它们。需要平台默认菜单时设为 `True`。

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

### `Tray` & `TrayItem` — 系统托盘（原生菜单）

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

---

## 国际化（i18n）

响应式、框架级 i18n。当前语言是一个 `Signal`；每个 `tr` 引用都是
`Computed[str]`，因此绑定文本在 `set_language()` 时实时更新，不丢失
widget 状态。

**目录是类型化模型，不是 dict。** `Catalog` 是 frozen pydantic 模型——
每个字段是一个翻译 key，带英文默认值；每种语言一个实例。子类化以添加
应用 key（扁平 `str` 字段或嵌套子模型分组）；pydantic 类默认值天然提供
逐 key 英文回退。

```python
from neony.application import Catalog, Common, Language, register_catalog, set_language, tr, tr_now


class FilesCatalog(Catalog):
    count: str = "{n} files"


class AppCatalog(Catalog):
    save: str = "Save"  # → tr.save
    files: FilesCatalog = FilesCatalog()  # → tr.files.count


register_catalog(Language.EN, AppCatalog())
register_catalog(
    Language.ZH,
    AppCatalog(
        save="保存",
        files=FilesCatalog(count="{n} 个文件"),
        common=Common(copy_text="复制", delete="删除", ok="确定", cancel="取消", close="关闭"),
    ),
)

tr.common.copy_text  # Computed[str] → "Copy"（切换语言时实时更新）
tr.files.count.format(n=5)  # 插值 → "5 files"
tr_now(tr.common.copy_text)  # 即时读、不订阅（展示时解析）
set_language(Language.ZH)  # 所有 tr.* 绑定重新解析
app.set_language(Language.ZH) / app.language  # app 级便捷方法
```

- **`Language`** —— 内置语言的 `StrEnum`（`EN/ZH/JA/FR/DE/ES/PT/RU`）；
  `set_language` 对未知语言抛 `ValueError`。合法但未注册目录的语言回落到英文。
- **`Catalog` / `Common`** —— frozen pydantic 模型（`extra="forbid"` 抓
  key 拼写错误）。`Common` 承载框架自带文案（`copy_text`、`delete`、
  `ok`、`cancel`、`close`）。
- **`tr`** —— 链式代理。`tr.<key>` 与 `tr.<group>.<key>` 各返回一个
  响应式 `Computed[str]`；传给任何接受响应式文本的组件（`Text`、
  `Button`——共享的 `_mount_text` helper 让任意组件都能接入）。
  `tr.<key>.get()` 读当前值。
- **`tr_now(tr.xx.xxx)`** —— 不订阅地读当前值；用于组件默认文案与
  菜单的展示时解析。在 effect 内安全（不漏建依赖）。
- **保留 key 名** —— 与 `Computed` 方法重名（`get`、`format`）或以 `_`
  开头的 key 无法经 `tr` 链引用。
- 框架默认文案（MessageBubble 内置右键菜单、`PromptDialog` 的
  确定/取消）经目录解析。

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
tabs = Tabs(("一", panel_one), ("二", panel_two))  # 或 tabs.add("一", panel_one)
tabs.selected_panel = panel_two  # 编程切换(组件或元素)
tabs.selected_title  # 当前激活标签的标题
tabs.selected_key = "二"  # 以标题作为 key 编程选择
tabs.bind_selected(active)  # Signal[str] ↔ 当前标签
tabs.on_change(lambda e: print(e.value))  # value = 标签标题
```

**参数:** `Tabs(*panes, glass, edge_fade=True)` — `*panes` 为 `(标题, 面板)` 对，等价于链式 `add()`。
`edge_fade` 切换标签条上的滚动指示器（浮动拇指 + 动态边缘渐变）——设 `False` 关闭。

`selected_panel` 按身份绑定可见面板（组件或其已构建的根元素，绝不重复构建）；`selected_title` 按标题字符串选择，未知标题抛 `ValueError`。`active`（下标）与 `active_key` 为已弃用别名 —— `active_key` 现在返回标签标题（此前返回不透明的元素 id）。

### `Accordion` & `Collapsible`

```python
accordion = (
    Accordion(multiple=True)
    .section("输入与表单", inputs_panel, checks_panel)
    .section("布局", layout_panel, expanded=True)
)
accordion.on_change(lambda e: print(e.value))  # value = 被切换分组的 key
accordion.expanded_keys = ["输入与表单"]  # 编程展开 —— 不触发回调
accordion.expanded_keys  # list[str]，当前展开的分组
```

`Collapsible` 是一个带标题、可在隐藏/可见之间切换的内容面板；`Accordion` 把若干折叠项堆叠在同一个滚动流里。`multiple=True`（默认）允许同时展开多个分组；`multiple=False` 为互斥模式——展开一个会收起其余的。切换仅改 `display`——展开时重放内置的 `neony-rise-in` 入场动画，因此不涉及 JS 层。

`Collapsible(title, *content, expanded=False, key=None)` 构造单个折叠项（也可作为位置参数直接传给 `Accordion`）；`key` 默认取标题的小写形式，用于 `change` 事件载荷。`.section(title, *content, ...)` 是流畅写法，一步构建并挂载一个 `Collapsible`。

用 `on_change` 监听（`event.value` 为刚被用户切换的分组 key），用 `expanded_keys` 读取完整的展开集合。`Accordion` **不**实现 `selected_key` / `bind_selected`——其选择是多值的，不适用单值选择协议。

### `Pane` & `SidebarGroup`

见下方 `Sidebar` 一节 —— `Pane` 是 Sidebar 拥有的可选项，`SidebarGroup` 是分组的标题小节。

### `Radio` & `RadioGroup`

```python
group = RadioGroup(Radio("披萨"), Radio("塔可"))
group.value  # 选中的值（默认小写 label）
group.on_change(lambda e: print(e.value))  # value = 选中的值字符串
group.value = "tacos"  # 编程设置 — 不触发回调
```

同一时刻只有一个选项被选中；组会给选项分配共享 `name`，屏幕阅读器
将其视为一个控件。单独使用的 `Radio` 是普通开关，`on_change` 携带
布尔值。

### `Switch`

```python
sw = Switch("Wi-Fi")
sw.bind_value(flag)  # 双向绑定 checked
sw.checked = True  # 编程设置 — 不触发回调
sw.on_change(lambda e: print(e.value))  # value = 是否开启
```

开关只需要同步状态时使用 `bind_value`；如果变更还要执行异步操作、
条件分支或更新多个状态，保留命名的事件处理器：

```python
async def on_wifi_change(event: DomEvent) -> None:
    await persist_setting(bool(event.value))
    status.set("已保存")


sw.on_change(on_wifi_change)
```

原生 checkbox 样式化为轨道 + 滑块（38×22px，`glass=True` 磨砂轨道）。

### `Select`

```python
sel = Select("尺寸", options=[("s", "小"), ("m", "中")], placeholder="请选择…")
sel.value  # 选中的选项值（"m"）
sel.on_change(lambda e: print(e.value))  # value = 选中的选项值
```

选项为 `str`（值即标签）或 `(value, label)` 元组。弹出列表由组件自绘
——主题化玻璃面板——因为 WebKitGTK 的原生弹出层忽略 option 的
`background-color`。键盘：Enter/Space 打开，方向键高亮，Enter 选中，
Escape/Tab 关闭；点击外部经引擎的 `outsideclick` 事件关闭。

### `ComboBox`

```python
box = ComboBox("标签", options=["work", "personal"], placeholder="输入或选择…")
tag = Signal("")
box.bind_value(tag)  # 输入与建议选择都会写回 tag
```

简单回显使用绑定即可；校验、持久化或其他异步操作则使用事件回调
（也可以与绑定同时使用）：

```python
async def on_tag_change(event: DomEvent) -> None:
    await save_tag(event.value)
    audit_log.append(event.value)


box.on_change(on_tag_change)  # event.value 是提交后的文本
```

可编辑文本框 + 主题化建议面板（原生 `<datalist>` 弹出层无法主题化）。
聚焦即弹出全部选项（单击即可见）；建议按输入前缀实时过滤；方向键
高亮、**Tab 或 Enter 自动补全**高亮建议、**PageUp/PageDown 一键选中
首/尾建议**、Escape / 点击外部关闭。值语义与 `Input` 一致：
`on_input` 只记录状态，`on_change` 在选中建议或失焦时触发。

### `Slider`

```python
sl = Slider("音量", min=0, max=100, step=5, value=40)
sl = Slider("音量", min=0, max=100, step="any")  # 无级
sl.value  # 40.0 — 已限制在 [min, max]
sl.on_input(lambda e: print(e.value))  # float，拖动中持续触发
sl.on_change(lambda e: print(e.value))  # float，松开时触发
```

轨道、accent 填充和滑块由组件自绘（顶层的原生 range 输入不可见，
负责拖动与键盘）。拖动时填充实时跟随滑块，程序化设置时 0.2s 平滑
过渡。`step="any"` 可达任意浮点值。PageUp/PageDown 按页步进（10×
step，无级时为范围 10%）——组件纠正了原生 range 反向的页方向
（WebKit 规范怪癖）。

### `Progress`

```python
bar = Progress("下载中…", value=35, max=100)
bar.value = 50  # 限制在 [0, max]；填充 0.3s 平滑过渡
Progress("扫描中…", indeterminate=True)  # 滑动扫掠动画
```

圆角轨道 + accent 填充，值变化时宽度过渡
（`indeterminate=True` 播放内置 `neony-indeterminate` 扫掠动画）。
条上携带 ARIA `role="progressbar"` + `aria-valuenow/min/max`。

### `Dialog`

```python
dlg = Dialog(
    title="确认",
    content=Text("..."),
    width="380px",
    actions=[
        DialogAction("确认", on_click=confirm_handler),  # 执行后关闭
        DialogAction("取消", variant="ghost"),
        DialogAction("关闭", close_on_click=False),  # 执行后保持打开
    ],
)
dlg.open = True  # 或读取该属性
dlg.on_close(lambda d: print("closed"))  # 回调接收对话框自身
```

固定全屏 scrim 层（`--color-bg-overlay`，跟随主题）+ 居中面板。
关闭途径：scrim 点击、Escape（焦点在对话框内时）、点击外部
（`outsideclick`）。`closable=False` 仅禁用 scrim。`actions` 渲染为
底部一排主题按钮 —— `DialogAction` 接受标签（位置参数）、
`variant`（`primary`/`ghost`/`danger`）、`on_click` 回调（收对话框
自身，同步或异步）与 `close_on_click`（默认 True）。注意：任何
`backdrop-filter` / `transform` 祖先会成为 `position: fixed` 的
containing block —— Dialog 应挂页面根或非过滤容器。

### `PromptDialog`

```python
ask = PromptDialog(
    "你的名字是？",  # 输入框上方的提示
    title="识别",
    value="Ada",  # 预填；也可通过 ask.value 重置
    placeholder="输入…",
)
ask.open = True  # 或读取该属性
ask.on_submit(lambda v: print(f"got {v}"))  # 确认 / 回车，携带输入值
ask.on_close(lambda d: print("closed"))  # 继承自 Dialog
```

专门用于单行文本输入的 `Dialog`：主题化 scrim + 居中面板，内含一条
消息、一个 `Input` 输入框与确认 / 取消按钮行。确认（主按钮，或输入框
聚焦时按 `Enter`）触发 `on_submit` 并携带输入框当前值，然后关闭；
取消（ghost 按钮、`Escape`、scrim 点击或点击外部）只关闭、不触发。
`value` 是输入框文字 —— 打开前设置可预填，提交后读取。`prompt`、
`confirm_label`、`cancel_label`、`placeholder` 均可配置。与 `Dialog`
相同的 `position: fixed` 注意点 —— 挂页面根。

### `Tooltip`

```python
tip = Tooltip("提示", anchor=Button("悬停"), placement="top", delay=0.4)
```

包装 anchor（组件在构造时 build；字符串包进 Span），悬停 `delay`
秒后显示气泡，按 `placement`（`top` / `bottom` / `left` / `right`）
锚定 —— 纯 CSS 偏移，零测量。wrapper 会冒泡 anchor 的悬停事件；
点击 anchor（聚焦）立即显示气泡，失焦隐藏。

### `Dropdown`

```python
dd = Dropdown("主题", items=[("dark", "深色"), ("light", "浅色")])
choice = Signal("")
dd.bind_value(choice)  # 双向绑定：选择结果写入 choice
dd.value  # 选中的值
```

如果选择还要触发异步加载或多个相关状态更新，使用命名的
`on_change` 处理器：

```python
async def on_theme_change(event: DomEvent) -> None:
    await reload_theme(event.value)
    status.set(f"已加载：{event.value}")


dd.on_change(on_theme_change)
```

trigger + 主题化玻璃弹出面板（原生 button 行，与 `Select` 同模式）。
完整键盘导航（Enter/Space 打开、方向键两端钳制、PageUp/PageDown
首尾、Enter 选中、Escape/Tab 与点击外部关闭）。`items` 可设置。

### `Menu`

```python
menu = Menu(("rename", "重命名"), ("delete", "删除"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # 光标位置
menu.on_change(lambda e: print(e.value))
```

`open_at(x, y)` 定位的 fixed 弹出面板 —— 通常用 `contextmenu` 事件的
视口坐标，无需测量。键盘导航与 `Dropdown` 相同；选中、Escape 或
点击外部关闭。面板**向上弹出**——底边锚在光标上方 8px——并通过
`calc()` 的 max-width/height 钳制在视口内，靠近屏幕边缘也不会溢出。

### `Toast`

```python
toast = Toast(placement="top-right", duration=3.0, top_offset="40px")
page.add(toast)  # 挂载一次到页根
toast.show("File saved", type="success")  # success / info / error
toast.show("Update available", type="info", duration=5.0)
toast.show("New message", on_click=open_it)  # 点击卡片（✕ 不触发）
toast.placement = "bottom-left"  # 运行时移动堆叠方位
toast.clear()  # 全部移除
```

宿主组件，把瞬时通知堆叠在六个屏幕方位之一（`top-left` /
`top-center` / `top-right` / `bottom-left` / `bottom-center` /
`bottom-right`）。`show(text, type=...)` 推入一张卡片 ——
`success` / `info` / `error` 决定左侧类型圆点颜色；`duration` 按次
覆盖宿主默认值，`0` 表示一直停留（点 ✕ 关闭）。`on_click`（同步或
异步）在点击卡片时触发——✕ 永不触发它——可点击的卡片会显示指针
光标。`max_toasts` 超限时驱逐最旧卡片。`top_offset` 让 top 组从窗口
顶部往下偏移——留出 `TitleBar` 的高度；bottom 组始终贴窗边。每张
卡片的**入场动画与方位方向绑定**（top 组从上方落下、bottom 组从
下方升起、角位对角滑入），出场反向重放同一 keyframe 滑向该方位
角/边。宿主是 `position: fixed` 全视口层，z-index 1100、
`pointer-events: none`（点击穿透到页面）——挂载在页根，避开
`backdrop-filter` / `transform` 祖先。

---

### `Image`

```python
from neony.application.urls import file_url, data_url

img = Image(file_url("cover.png"), width=120, height=120, fit="cover", radius="12px")
img.src = data_url("other.svg")  # 任意 URL 字符串
```

包裹单个 `<img>` 的主题化框架。`src` 是**已拼好的 URL**——本地文件传
`file_url(path)`，嵌入字节传 `data_url(path)`，或任意 `https://` URL；
组件自身不做任何路径转换（这个边界交给调用方）。圆角、overflow-hidden
的框架包裹图片，让 `object-fit` 能裁切到圆角，字节到达前显示占位色。
`width`/`height` 接受 `str`（`"40%"`）或 `int`（→ `"40px"`）。`fit` 即
`object-fit`（`cover`/`contain`/`fill`/`none`/`scale-down`）；传
`radius="50%"` 得到圆形。`src` 与 `alt` 构造后可改。

### `Avatar`

```python
av = Avatar("https://…/me.png", name="Ada Lovelace", size="56px")
letter = Avatar(name="Ada", size="40px")  # → 强调色圆盘上的 "A"
unknown = Avatar()  # → "?" 占位
inbox = Avatar(src, name="收件箱", badge=Badge(3, position="top-right"))
```

用户头像——图片、字母或占位。有 `src` 显示图片（`object-fit: cover`
裁切）；只有 `name` 时回退到首字符（大写）显示在强调色圆盘上；都没有
则显示 `?` 占位。`shape` 为 `circle`（默认）或 `square`；`radius` 覆写
形状的圆角。`alt` 覆写图片 alt 文字（否则用 `name`）。可选的 `badge`
（一个角标 `Badge`）叠加其上——Avatar 会把自己包进 relative inline-flex
容器，让角标能锚到某个角。`src`、`name`、`size` 构造后可改。

### `Badge`

```python
Badge("New", variant="accent")  # 内联标签
Badge(150)  # → "99+"（默认 max=99）
Badge(0)  # 隐藏（display:none）；Badge(0, show_zero=True) 显示
Badge(dot=True)  # 状态点，无文字
Badge(3, position="top-right")  # 角标计数——需要 position:relative 的父容器
```

小型状态标签或角标计数——一个类两种形态。`position="inline"`（默认）是
随文档流的标签，按 `variant` 染色（默认 `neutral`，可选 `accent`、
`danger`、`success`）。其他 `position`（`top-right`、`top-left`、
`bottom-right`、`bottom-left`）把标签绝对定位成角标——**组件假定父容器是
`position: relative`**（带 `badge=` 的 `Avatar`，或一个 wrapper `Div`）；
`overlap=True` 把它推得更远（`-12px`）以覆盖父元素边缘。整数内容有两点
便利：超过 `max`（默认 99）的计数折叠成 `"99+"`；零计数默认隐藏，除非
`show_zero=True`（节点保留，便于切回显）。`dot=True` 去掉文字，只留状态
点。`content`、`variant`、`dot` 构造后可改。

### `Card`

```python
card = Card(
    Text("正文里放任意子元素。"),
    title="我的卡片",
    subtitle="可选副标题",
    actions=[Button("编辑")],
    footer=[Button("取消"), Button("确定")],
    glass=True,
    role="accent",
)
card.title = "已重命名"
```

带标题的内容卡片。`*body` 是卡片正文（组件、DOM 元素或字符串）。
`title` / `subtitle` 自动生成 header（一个 `Heading` + 可选的次要 `Text`）；
自定义的 `header=` 会完全替换标题行（且优先级高于 `title`/`subtitle`/
`actions`）。`actions` 是 header 行右侧右对齐的按钮；`footer` 是按钮列表
（右对齐、分隔线之上）或任意内容节点。`glass=True` 把实色表面换成按
`role` 着色的毛玻璃面板（默认 `neutral`，可选 `accent`、`danger`、
`success`——辉光跟随主题）。`clickable=True` 让整张卡片可点击
（`cursor: pointer` + `on_click`）。`title` 与 `subtitle` 构造后可改。
Card 保留自己紧凑的样式常量（不包裹 `GlassPanel`），默认就很轻。

### `MessageBubble`

```python
other = MessageBubble(
    "Hey! Have you seen the new gallery?",
    avatar=Avatar(name="Ada"),
    name="Ada",
    actions=[("reply", "Reply"), Icon.glyph("😊")],
)
me = MessageBubble("Hi!", from_me=True)
other.on_change(lambda e: print(e.value))  # 右键菜单选择
other.on_action(lambda v: print(v))  # 快捷操作点击
```

单条聊天消息，QQ/Telegram 风格。`from_me` 切换行对齐（自己 → 右侧，
他人 → 左侧）与气泡填充色（自己 → accent 白字，他人 → 抬升面）；
朝向头像一侧的圆角做方角处理。`avatar` 是可选的 `Avatar`，放在消息
自身一侧（构造时 build 一次）；`name` 是气泡上方的可选发送者名。
`actions` 在气泡下方渲染 hover 时出现的快捷按钮——`(value, label)`
或 `str` 变成文本按钮，`Icon` 变成图标按钮；点击触发
`on_action(value)`。快捷操作行**绝对定位**在气泡正下方，出现时覆盖
下一条消息，不会撑高组件体积。`menu_items` 配置内置右键 `Menu`（默认
复制/删除；`[]` 关闭菜单但 `on_contextmenu` 仍触发），选择通过
`on_change` 派发（携带 value）。注意：菜单是气泡内的 `position:
fixed` 元素；聊天容器请避开 `backdrop-filter` / `transform` 祖先。

### `NoticeBubble`

```python
NoticeBubble("You joined the group")
```

居中的系统消息——在 flex 列消息列表里 `align-self: center` 居中，
半透明底的淡色药丸。`text` 是消息文本，或传 `content` 放自定义元素；
`text` 构造后可改。

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
  `grow=True` 撑满父区域;`radius` 覆盖默认 12px 圆角;`width` / `height`
  把面板固定为确定尺寸（配合默认非 `grow` 模式）。

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

`icon` 为 `Icon` 对象——`Icon.image(url_or_path)` 在标题左侧绘制一个小图标（固定尺寸方形，绝不拉伸）——无边框模式下
`WindowConfig.icon` 的对应物，因为无边框窗口没有 OS 装饰来承载它。

标题栏即拖拽区域(双击最大化);控制按钮带内部 `data-window-action`
属性,经 WindowControls 桥接自动路由 — 用户无需感知的实现细节。

### `Sidebar` & `SidebarItem`

垂直导航，与 `TitleBar` 同款玻璃。Sidebar 可以拥有内容面板——传入 `Pane` 子项时，点击条目（或按快捷键）在内部切换可见面板。

```python
sidebar = Sidebar(
    Pane("首页", panel=home_panel, icon=Icon.glyph("🏠"), section="常用", shortcut="Ctrl+1"),
    Pane("设置", panel=settings_panel, icon=Icon.glyph("⚙️"), section="常用"),
    Pane("统计", panel=stats_panel, icon=Icon.glyph("📊"), section="数据", shortcut="Ctrl+3"),
)
sidebar.on_change(lambda e: print(e.value))  # value = 面板 key
sidebar.selected_key = "settings"  # 编程切换,不触发回调
sidebar.selected  # 当前选中的 Pane（或 SidebarItem）对象
for combo, fn in sidebar.shortcuts():
    page.on_shortcut(combo, fn)  # 接线面板的快捷键
```

裸 rail 模式——只有 `SidebarItem` 子项，内容切换仍由用户负责：

```python
sidebar = Sidebar(
    SidebarItem("首页", icon=Icon.glyph("🏠")),
    SidebarItem("设置", icon=Icon.glyph("⚙️")),
    active_key="home",  # 已弃用 → selected_key
)
```

**参数:** `Sidebar(*children, width, glass, corner_radius, edge_fade=True)`，
`SidebarItem(label, key, icon, active)` — `*children` 为
`SidebarItem` / `SidebarGroup` / `Pane` / `(label, panel)` 元组。
`edge_fade` 切换轨道上的滚动指示器——设 `False` 关闭。玻璃侧边栏仍显示拇指，但跳过边缘渐变（WebKitGTK 中 mask-image 与背景模糊冲突）。

`Pane.key` 默认为随机 id——标签永不冲突，即使重复或非 ASCII；想要可读标识符时显式传 `key`。`shortcut` 与 `Page.on_shortcut` 同格式；快捷键切换如同点击一样触发 `change`。`selected_key` 对未知 key 抛 `ValueError`；设为 `None` 清空选择。点击条目任意位置（包括图标与文字）都生效——条目级事件会从其子元素冒泡上来。

### `Pane`

一个可选的 `Sidebar` 条目及其内容面板。

```python
pane = Pane("首页", panel=home_panel, icon=Icon.glyph("🏠"), section="常用", shortcut="Ctrl+1")
```

**参数:** `Pane(label, panel, key, icon, section, shortcut)` —
`label` 为条目文字（第一个位置参数）；`panel` 为激活时显示的组件（或元素），注册时构建一次（一个面板组件不能挂到两个 sidebar）；`key` 默认为随机 id；`section` 把连续同节的 pane 归入一个小号大写侧边栏标签下；`shortcut` 为窗口级组合键（`"Ctrl+1"` 或平台 dict 如 `{"darwin": "Meta+2", "default": "Ctrl+2"}`）。

### `SidebarGroup`

`Sidebar` 的分组小节——条目上方的小号大写标签。

```python
sidebar.add(SidebarGroup("菜单", SidebarItem("打开"), SidebarItem("保存")))
```

`SidebarGroup.add` 可链式调用，且组挂到 sidebar 之后仍可用（新增条目自动接线）。组纯属视觉：选择、`items` 与 `change` 都按 DOM 顺序作用于扁平的条目列表。连续共享同一 `section` 的 pane 渲染为一个组；同名 section 稍后重现则另起一组。

### `Tree` & `TreeNode`

可折叠导航树（左侧轨道）拥有内容宿主（右侧）。任意深度：分支节点（带 `children`）只展开/收起；叶子节点（带 `panel`）选中后在宿主显示其内容。树是单选——`selected_key` / `bind_selected` 与 `Sidebar` 行为一致。

```python
tree = Tree(
    TreeNode("首页", key="home", icon=Icon.glyph("🏠")).panel(home_panel),
    TreeNode("表单", expanded=True).children(
        TreeNode("输入", key="inputs", shortcut="Ctrl+1").panel(inputs_panel),
        TreeNode("勾选", key="checks").panel(checks_panel),
    ),
    active_key="home",  # 或 tree.selected_key = "home"
)
tree.on_change(lambda e: print(e.value))  # value = 叶子 key
for combo, fn in tree.shortcuts():
    page.on_shortcut(combo, fn)  # 叶子快捷键，同 Sidebar
```

**参数:** `Tree(*nodes, width, expanded_branches, active_key, edge_fade=True)` — `width` 为轨道宽度（宿主自适应其余空间）；`expanded_branches=True` 让顶层分支默认展开。`edge_fade` 切换轨道上的滚动指示器——设 `False` 关闭。行样式复用 `Accordion` 表头——圆角、透明、无外围包裹；轨道高度受舞台约束，内部滚动而非撑破页面。

`TreeNode(label, key, icon, panel, expanded, children, shortcut)` — 节点不能同时带 `panel` 与 `children`（否则抛错）。流畅建造器：`.panel(panel)` 挂叶子内容、`.children(*nodes)` 挂分支子节点、`.key_(key)` 设 key——全部可链式。

`key` 默认为随机 id；`selected_key` 对未知 key 抛 `ValueError`。分支带 `aria-expanded`、叶子带 `aria-selected`；行支持键盘导航（方向键移动焦点环，Enter / 空格激活，← / → 收起 / 展开分支）。

### `List` & `ListItem`

可滚动单选数据列表（listbox 模型）。同时只有一个条目被选中；`selected_key` / `bind_selected` / `on_change` 与 `Sidebar` 行为一致。

```python
fruits = List(
    "Apple",
    "Banana",
    ListItem("Cherry", key="cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.on_change(lambda e: print(e.value))  # value = 选中 key
fruits.selected_key = "cherry"  # 编程式写入，不触发回调
fruits.children("Durian", "Elderberry")  # 链式追加
fruits.bind_selected(signal)  # 双向响应式选中
```

**参数:** `List(*items, active_key=None, edge_fade=True)` — `items` 为字符串或 `ListItem(label, key=None, icon=None)`。字符串条目的 key 即其标签；标签冲突时须显式传 `key`（重复 key 抛错）。行是 `role="option"`，容器 `role="listbox"`；键盘：↑/↓ 移动选中（端点钳制，每次移动触发 `change`）、Home/End 跳到首尾、Enter/空格选中、点击选中。方向键导航时出现强调色焦点环，点击后清除。`edge_fade` 切换滚动指示器。

挂载契约：须挂在**确定高度**的 flex 父级（如 `VStack(..., grow=1)` 或 `GlassPanel(grow=True)`）；列表内部滚动行，而不是撑破页面。

### `DataTable` & `Column`

表格数据视图——列配置 + 行 dict 列表，带固定表头、点击排序与行选中（默认单选，构造时可选多选）。

```python
people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", align="right", format=lambda v: f"{v}%"),
    ],
    rows=[
        {"name": "Ada", "age": 38, "score": 92},
        {"name": "Bob", "age": 24, "score": 77},
    ],
    row_key=lambda r: r["name"],  # 默认：行索引
    active_key="Ada",
)
people.on_change(lambda e: print(e.value))  # 选中行 key
people.sort_by = ("age", "desc")  # 表头点击同样排序
people.bind_selected(signal)  # 双向响应式选中
```

列与行也可链式追加：`DataTable().column("Name").row({"name": "Ada"})`。

**参数:** `DataTable(columns=None, rows=None, *, row_key=None, selection="single", active_key=None, selected_keys=None, edge_fade=True)`。

`Column(title, key=None, width=None, sortable=False, align=None, format=None, sort_key=None)` — `key` 默认为小写标题；`width` 为 CSS 网格轨道（`"1fr"` / `"80px"`）；`align` 为 `left|center|right`；`format` 把单元格值映射为文本；`sort_key` 从行中提取自定义排序值。

`row_key` 派生每行的身份（默认行索引）且必须唯一。`sortable=True` 的表头点击排序（asc → desc，换列从 asc 开始）；排序数字感知（或用 `sort_key`），保留选中，可通过 `sort_by` 观察。表头在滚动容器内 `position: sticky`，横向滚动时表头与行保持对齐。

**选中。** `selection="single"`（默认）暴露 `selected_key`（编程式写入不触发回调）；`selection="multi"` 暴露 `selected_keys`（接受 `set`/`frozenset`/`list`/`None`），点击切换成员——`change` 携带被切换的 key，全量状态读 `selected_keys`。`bind_selected` 仅单选用（否则抛错）；错配模式的属性抛 `NotImplementedError`。

键盘：单选模式下方向键移动选中（触发 `change`）；多选模式下方向键移动焦点环、空格切换。Home/End 跳首尾；Enter/空格选中或切换。

挂载契约：须挂在**确定高度**的 flex 父级；表格内部双轴滚动。`edge_fade` 切换滚动指示器。

### `Icon`

`TitleBar`、`Sidebar`/`Pane`/`SidebarItem`、`Tabs` 与 `TreeNode` 共用的统一图标——图片或字形，二选一显式声明：

```python
Icon.image("https://example.com/logo.svg")  # 固定尺寸方形（TitleBar 同款）
Icon.image("assets/logo.png")
Icon.glyph("🏠")  # emoji / Nerd Font 字符
```

**参数:** `Icon(src, kind)` — 经 `Icon.image(url_or_path)` 或 `Icon.glyph(text)` 构造；`render(size)` 生成元素（图片形式以 `background-image: url(...)` 绘制固定尺寸方形，contain/居中/不重复，绝不拉伸）。

---

## 主题

三套内置预设 — `DARK`， `LIGHT`， `DEEP_BLUE` — 以 CSS 自定义属性暴露。每个预设都是
**不可变**的 `Theme` 实例；构造任意 `Theme` 即按其 `mode` 自动注册。

```python
app.theme  # 当前激活的预设（默认 DARK）
Theme.get("light")  # 按 mode 名单次查询已注册预设
app.theme.next()  # 切换顺序里紧接当前预设的下一个
Theme.modes()  # 已注册 mode 名，按预设构造顺序排列
Theme.mode_label("dark")  # "Light mode" — 下一个 mode 的标签
await app.set_theme(LIGHT)  # 切换当前预设并重新注入变量
```

`Theme.set_mode` / `Theme.toggle` 已移除 —— 切换改为经 `App.set_theme` 换引用，而非就地改实例。

令牌族: `--color-bg`， `--color-surface`，
`--color-text-primary` / `--color-text-secondary`， `--color-accent`，
`--color-on-accent` / `--color-on-danger`（饱和 accent / danger 填充上的文字色），
`--color-danger`， `--color-success`， `--color-border`， `--color-shadow`，
`--color-*-glass*`(磨砂变体)。

组件通过 `Color(var="--color-*")` 引用令牌，切换主题零 DOM diff 重绘。

自定义主题:

```python
from neony.application import Theme
my_theme = Theme(mode="sepia", bg="#1a1a2e", accent="#4a90d9", on_accent="#ffffff", ...)
# 构造即自动注册；需提供全部令牌 —— Theme 无默认值。
await app.set_theme(my_theme)
Theme.get("sepia") is my_theme  # True
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

### 应用内拖拽与重排

#### `Reorder` 组件

重排集合的现成方式是 `Reorder` 面板——一个由可拖拽卡片组成的 flex
容器，重排逻辑内聚在组件内部：

```python
from neony.application.elements import Reorder, ReorderItem

board = Reorder(
    ReorderItem("First", key="a"),
    ReorderItem("Second", key="b"),
    "Third",  # 纯字符串也会变成卡片（key = 标签）
    direction="row",  # "row" 或 "column"
    wrap=True,  # row + wrap = 网格（横纵都行）
    size="76px",  # 沿主轴方向的卡片尺寸
    max_width="336px",  # 可选——固定每行 4 张卡片以强制换行
)
board.on_drop(lambda e: e.value)  # 拖拽后的有序 key
board.order  # 当前按渲染顺序的 key
```

- 卡片预置为可拖拽（载荷提前声明——dragstart 里 Python 往返来不及），
  `drop` 由组件自身重排；diff 引擎自动发出 `ReorderPatch`。
- **纵横双向都支持**：引擎自动检测容器的 `flex-direction`，按光标所在
  半区判定插入侧——`row` 用 `offset_x`（前半插其前、后半插其后）、
  `column` 用 `offset_y`。`row` + wrap 会形成网格，卡片既能横向拖（行内）
  也能纵向拖（跨行）。网格在面板宽度处换行——用 `max_width` 固定宽度即可
  强制换行。
- **卡片不限于文本**：`add()` / 构造器接受任意内容——纯文本或响应式字符串、
  整个 `Component`（挂载在卡片内部），或裸 `DOMElement`。**裸内容不需要
  包装也不需要显式 key**：纯字符串用标签当 key、带 key 的 DOM 元素保留
  自己的 key，其余一切（一摞 `Card` 等）自动获得 `reorder-card-N` key。
- **按卡片内容泛型化**——`Reorder[T]` 与 `ReorderItem[T]` 以卡片内容为类型
  参数，因此任意组件（或任何内容类型）可以直接站在原本 `ReorderItem` 的
  位置上，`items` 产出 `ReorderItem[T]`：

  ```python
  from neony.application.elements import Card, Text

  board: Reorder[Card] = Reorder(Card(title="One"), Card(title="Two"))
  cards = board.items  # list[ReorderItem[Card]]——content 类型为 Card
  ```
- **面板之间可以交换卡片**：把卡片拖到另一个 `Reorder` 的卡片上，落点槽
  会移动到那个面板，drop 会把卡片移过去（从源面板的 `order` 移除并插入
  目标面板）。允许交换的面板之间，卡片 key 必须全局唯一。
- `on_drop` 触发时 `event.value` = 接收 drop 的面板重排后的卡片 key 列表。

#### 底层原语

组件之下，引擎委托完整的拖拽生命周期——`dragstart` / `dragenter` /
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

五个方法在 `Component` 上同样可用(前四个代理到组件的根元素)。绑定
写入会把元素标记为 dirty 并为其窗口调度一次渲染 — 因此无论 Signal
在哪里被修改(事件处理、定时器、其他窗口)，都无需显式调用 `render()`
就能上屏。

### `Component.bind_value` — 值双向绑定

`bind_value(signal)` 把 Signal 绑定到组件的**值**上，双向同步。它适合
直接的状态同步；如果流程需要事件上下文、条件分支、异步副作用或
批量更新，不要用它替代事件处理器：

```python
name = Signal("")
inp = Input()
inp.bind_value(name)  # 输入 → name.set()；name.set() → 输入框

vol = Signal(40)
slider.bind_value(vol)  # 拖动回写(float)
bar = Progress()
bar.bind_value(vol)  # 只写跟随

flag = Signal(False)
cb = Checkbox("x")
cb.bind_value(flag)  # 绑定的是 checked 而非 value
```

- Signal 写入立即更新组件值并随变化继续更新；用户改值回写 Signal
- `Computed` 只读绑定(不回写)
- 用户通道是组件的 `_value_event`(`input`：Input/ComboBox/Slider，
  `change`：Select/Checkbox)；Progress 无用户通道，只写
- `unbind_value()` / `unbind()` 释放绑定；程序化写值不触发回调，
  循环天然闭合(用户 → Signal → 写回相同值不再分发)

复杂流程可以在绑定之外保留命名事件处理器：

```python
flag = Signal(False)
switch = Switch("同步")
switch.bind_value(flag)  # 简单状态同步


async def on_sync_change(event: DomEvent) -> None:
    await sync_remote(bool(event.value))
    status.set("已同步")


switch.on_change(on_sync_change)
```

### 脏子树追踪

每次变更都会把元素标记为 dirty 并向上传播到根。渲染时只重新序列化
dirty 元素；未变化的子树复用缓存快照(diff 引擎视其为相同，因此零补丁)。
这是自动的 — `container.append()` 和属性赋值都会参与。
