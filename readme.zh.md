# Neony

基于 [LumiView](https://github.com/xiaosuawa/lumiview) 的响应式桌面 UI 框架。

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)
[![Status: pre-beta](https://img.shields.io/badge/status-pre--beta-yellow.svg)](#)

> 📖 **文档（最新发布）：** [简体中文](https://harcic.me/neony/zh) · [English](https://harcic.me/neony)
>
> 托管文档指向 **最新tag**。需要 **最新 commit** 的文档（仓库内
> `docs/`），见 [`docs/`](../../tree/HEAD/docs/) —
> [`docs/README.zh.md`](../../blob/HEAD/docs/README.zh.md)、
> [`入门教程`](../../blob/HEAD/docs/getting-started.zh.md)、
> [`api/ 章节`](../../tree/HEAD/docs/api)。

> [English README](readme.md) · [贡献指南](CONTRIBUTING.zh.md)

---

## 概览

> **状态: pre-beta** — API 仍在演进中。欢迎反馈与贡献。

Neony 在原生窗口中渲染响应式 DOM。你完全用 Python 对象——组件、布局、样式——拼装界面，Neony 自动对浏览器 DOM 做增量更新。应用代码不必写
HTML 或 JavaScript。

它基于 [LumiView](https://lumiview.dev)，与 [Tauri](https://tauri.app)
使用相同的 Rust `tao`/`wry` WebView 技术栈。

- **纯 Python API** — 组件、布局、事件；应用代码不必写 HTML 或 JavaScript
- **细粒度响应式** — `Signal` / `Computed` / `Effect` 原语 + 声明式绑定
- **与 Tauri 同源** — Rust `tao`/`wry` WebView (经 LumiView)
- **八套主题预设** — Nightglow / Planet Plaza / Ember Zone / Cyberangel 四个视觉族，每族 light / dark 成对
- **(可选)毛玻璃** — 半透明表面 + 背景模糊
- **语义色光晕** — 焦点环与悬停辉光跟随元素语义颜色
- **滚动指示器** — 原生滚动条被隐藏；滚动表面获得随主题的浮动滑块（静止时淡显、滚动/悬停时增强、可拖拽、点击轨道翻页），以及只在内容真正溢出的方向显示的动态边缘渐变
- **自定义窗口装饰** — 无边框、透明窗口、自定义标题栏
- **(仅支持平台)原生窗口效果** — blur / acrylic / mica 材质

---

## 安装

```bash
pip install neony
```

需要 Python 3.11+，以及对应平台的 WebView 运行时（Linux 为 WebKitGTK、Windows 为 WebView2、macOS 为 WKWebView）。Linux 目前主要在
Wayland 上开发和验证；X11 还不是完整支持目标。系统依赖与故障排查见
[安装与平台指南](docs/guides/installation-platforms.zh.md)。系统托盘在 Linux 需要 `libayatana-appindicator`。

---

## 快速开始

```python
from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack
from neony.dom import Signal

clicks = Signal(0)
counter = Button("Click me")
counter.bind_text(clicks, fmt=lambda count: f"Clicked {count} times!" if count else "Click me")
counter.on_click(lambda _event: clicks.update(lambda count: count + 1))

page = Page(gap="16px").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("用纯 Python 构建桌面 UI。", role="secondary"),
        counter,
        gap="12px",
    )
)

launch(page, title="My App", width=480, height=360, devtools=True)
```

---

## 组件

从 `neony.application.elements` 导入。

| 组件                        | 说明                                                                                                                      |
|-----------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `Button`                    | 主题按钮 — primary / ghost / danger 变体，悬停与按压反馈                                                                  |
| `Checkbox`                  | 自定义复选框，含标签与 change 事件                                                                                        |
| `Radio` / `RadioGroup`      | 互斥单选组，组 change 携带选中值                                                                                          |
| `Switch`                    | 轨道 + 滑块开关，基于原生 checkbox                                                                                        |
| `Select`                    | 主题下拉框 — `str` 或 `(value, label)` 选项                                                                               |
| `ComboBox`                  | 可编辑文本 + 主题化建议面板                                                                                               |
| `Slider`                    | 动画填充滑块 — 有级或无级（`step="any"`）                                                                                 |
| `Progress`                  | 动画填充进度条 — 确定值或滑动 `indeterminate`                                                                             |
| `Dialog`                    | 固定 scrim + 居中玻璃面板 — scrim / Escape / ✕ / 点击外部关闭                                                            |
| `PromptDialog`              | 基于 `Dialog` 的单行文本提示 — 确认 / 取消，Enter / Escape                                                                |
| `Tooltip`                   | 包裹 anchor 的悬停气泡，placement 偏移 + 悬停延迟                                                                         |
| `Dropdown`                  | trigger 下的主题化弹出面板 — 完整键盘导航 + 点击外部关闭                                                                  |
| `Menu` / `MenuBranch`       | 光标定位的固定弹出菜单（`open_at(x, y)` 来自 contextmenu），支持级联分支                                                  |
| `CascadingDropdown`         | 多级触发式下拉 — 嵌套分支在父项旁展开                                                                                     |
| `Toast`                     | 屏幕边缘的瞬时通知 — 6 方位、success/info/error、与方位绑定的方向性动画                                                   |
| `Input`                     | 单行输入框 — text / password / email / number…                                                                            |
| `Heading`                   | 主题标题(h1–h6)，自动字号                                                                                                 |
| `Text`                      | 内联文本，支持语义角色(primary / secondary / danger / success)                                                            |
| `Tabs`                      | 选项卡栏 + 面板，同时只显示一个 — 构造器子项、`selected_panel` / `selected_title` / `selected_key`                        |
| `Accordion` / `Collapsible` | 单列滚动流中的可展开分组 — 流畅 `.section()`、默认可多组同时展开（`multiple=False` 为互斥）、`expanded_keys`、`on_change` |
| `Tree` / `TreeNode`         | 可折叠导航树 + 内容宿主 — 任意深度、流畅建造器写法、点叶子在右侧显示其面板                                                |
| `List` / `ListItem`         | 可滚动单选数据列表 — listbox 模型、方向键移动选中、`selected_key` / `bind_selected`                                       |
| `DataTable` / `Column`      | 列配置 + 数据行 — 固定表头、点击排序、单选 / 多选行                                                                       |
| `Reorder` / `ReorderItem`   | 拖拽重排面板 — 任意组件/DOM 元素都可作为卡片；`direction` + `wrap` 可作网格纵横双向重排，多个面板可交换卡片               |
| `ReorderContent`            | 可重排容器内容 — 不带面板边框/背景的拖拽重排                                                                              |
| `Icon`                      | 统一图标 — `Icon.image(url_or_path)` 固定方形图片或 `Icon.glyph(text)` 字形，TitleBar / Sidebar / Tabs / Tree 共用        |
| `Flex`                      | 通用弹性容器，完全控制                                                                                                    |
| `VStack` / `HStack`         | 纵向 / 横向弹性堆叠                                                                                                       |
| `Spacer`                    | 弹性空白，吸收剩余空间                                                                                                    |
| `Separator`                 | 细分隔线 — 水平（默认）或垂直                                                                                             |
| `GlassPanel`                | 毛玻璃容器，可选背景图                                                                                                    |
| `TitleBar`                  | 无边框窗口的自定义标题栏 — 拖动、最小化 / 最大化 / 关闭                                                                   |
| `Sidebar` / `SidebarItem`   | 拥有内容面板的垂直导航 — `Pane`、`SidebarGroup` 分组小节、每面板快捷键；与 TitleBar 同款玻璃风格                          |
| `Pane`                      | 可选的 Sidebar 条目 + 内容面板 — `key`、`icon`、`section`、`shortcut`                                                     |
| `SidebarGroup`              | Sidebar 的分组小节 — 条目上方的小号大写标签                                                                               |
| `Image`                     | 主题化图片，圆角 overflow-hidden 框架（`src` 为任意 URL）                                                                 |
| `Video` / `Audio`           | 全托管主题化媒体播放器 — 自绘传输条，`neony://` 本地源，HEVC 转码回退                                                     |
| `Avatar`                    | 用户头像 — 图片 / 字母占位 / 空占位，可选角标 `badge`                                                                     |
| `Badge`                     | 状态标签或角标计数 — 多变体、状态点、`99+` 截断、0 自动隐藏                                                               |
| `Card`                      | 带标题的内容卡片 — 操作区、页脚、可选毛玻璃 `glass` 表面                                                                  |
| `MessageBubble`             | 聊天消息 — from_me 对齐/配色、可选头像 + 昵称、内置右键菜单、hover 快捷操作                                               |
| `NoticeBubble`              | 聊天居中的系统提示药丸                                                                                                    |
| `RichText`                  | 行内 contenteditable 编辑器 — 文字 + 图片、光标/选区 API、光标处插入、`content()` 分段、IME 安全、粘贴图片文件            |
| `ScrollArea`                | 可滚动垂直区域，带 `scroll_to_bottom()` / `scroll_to_top()` / `scroll_to()`                                               |
| `StickToBottom`             | 聊天流滚动容器 — 接近底部自动贴底；上滚暂停，回到底部附近恢复                                                             |

所有组件共享链式 API，用法见 [API 索引](docs/api/README.zh.md)。

---

## 窗口特性

- **无边框自定义标题栏** — 设置 `decorations=False`，添加 `TitleBar`，拖动 / 最小化 / 最大化 / 关闭全部自动生效。见
  [`docs/api/layout-chrome.zh.md`](docs/api/layout-chrome.zh.md) 与
  [`demo_custom_window.py`](demo_custom_window.py) 示例。
- **透明窗口与原生效果** — `transparent=True` 会自动套上平台材质（Linux 在合成器支持时走 Wayland blur，Windows 为
  Acrylic，macOS 为 Blur）。`apply_blur()`、`apply_acrylic()`、`apply_mica()` 是手动覆盖，且受平台限制（`apply_blur` 仅
  macOS/Windows；acrylic / mica 仅 Windows 11）。见 [`demo_transparent_panel.py`](demo_transparent_panel.py)。
- **编程式窗口控制** — `set_title()`、`set_size()`、`minimize()`、
  `toggle_maximize()`、`close()` … 均位于 `NeonApplication`，多窗口时接受 `window_index=0` 参数。
- **剪贴板** — `app.clipboard_write(text)` / `app.clipboard_read()`。
- **本地资源 URL** — `file_url()` / `data_url()`，处理 Windows 路径、空格与非 ASCII 文件名。
- **自定义协议** — 通过 `neony://<key>/…` URL 向页面提供内容：用
  `@protocol("key")` 声明处理器（普通函数或方法均可），再传给
  `launch(page, protocols=[...])`。内置 `local_files` 处理器经
  `neony://local/…` 提供本地文件（支持 Range），解决 WebView 拦截
  `file://` 子资源的问题；`local_url(path)` /
  `protocol_url(key, value)` 负责构建 URL。受管 `Video` / `Audio`
  组件会自动水合 `neony://` 源——媒体管线读不了自定义 scheme，运行时 fetch 字节后换成 Blob URL——本地媒体播放与拖动进度开箱即用。
  原始 `<audio>` / `<video>` DOM 元素不再水合。参见 [`demo_protocols.py`](demo_protocols.py)。
- **国际化** — 类型化目录 + `tr` / `set_language()`；绑定文案在切换语言时即时更新。
- **多窗口** — `run(*pages)` 每个页面一个窗口，共享同一事件循环与
  `app.state`。`launch([...])` 也接受列表。见 [`demo_multi_window.py`](demo_multi_window.py)。
- **系统托盘** — `app.tray = Tray(icon, tooltip, items=[...])` 添加托盘图标与原生右键菜单；`close_to_tray=True`
  关窗时隐藏应用而非退出。Linux 需要 `libayatana-appindicator`。见
  [`demo_tray.py`](demo_tray.py)。
- **原生文件对话框** — `app.open_file()`、`app.open_files()`、
  `app.save_file()`、`app.select_folder()` 调用平台自己的选择器 — Linux 为 zenity、macOS 为 `osascript`、Windows 为
  PowerShell，另有 tkinter 回退（取消返回 `None`，多选取消返回 `[]`）。

---

## 主题

四个视觉族共八套内置预设 — Nightglow、Planet Plaza、Ember Zone、Cyberangel，每族 light / dark 成对 — 以 CSS 自定义属性暴露在
`:root`；历史名称 `DARK`（默认）、`LIGHT`、`DEEP_BLUE` 仍作为别名保留。切换主题只替换这块变量，浏览器按新的
`var(--color-*)` 重上色。滚动条与交互光晕（焦点环、悬停辉光）引用同一套 token，因此也随主题
自动切换。切换与自定义主题见 [API 参考](docs/api/platform-i18n.zh.md)。运动令牌采用同样机制：`Motion.DEFAULT` 注入
`--motion-*` 变量，`transition()` / `popup_animation()` / `submenu_animation()` 覆盖常见交互。

---

## 示例

在仓库根目录运行:

| 文件                             | 演示内容                                   |
|----------------------------------|--------------------------------------------|
| `demo_hello.py`                  | 最小示例                                   |
| `gallery` 包（`uv run gallery`） | 带文档与代码示例的组件画廊，玻璃标题栏     |
| `demo_custom_window.py`          | 无边框窗口：TitleBar + Sidebar 一体装饰    |
| `demo_transparent_panel.py`      | 带原生模糊的透明悬浮面板                   |
| `demo_multi_window.py`           | 共享同一 app 状态的双窗口                  |
| `demo_reactive.py`               | Signal API：声明式绑定替代手动刷新         |
| `demo_accordion.py`              | Accordion：单列滚动流中的可展开分组        |
| `demo_tree.py`                   | Tree：可折叠导航树 + 内容宿主              |
| `demo_tray.py`                   | 系统托盘：原生菜单 + 关闭到托盘模式        |
| `demo_builder.py`                | 居中 `Page`，组件与原始样式 `Div` 混用     |
| `demo_media.py`                  | 受管 `Video` / `Audio` 播放器与媒体事件    |
| `demo_protocols.py`              | `neony://` 自定义协议：本地媒体 + 动态响应 |

```bash
uv run gallery
```

---

## 路线图

计划中的工作已移入 [ROADMAP.md](ROADMAP.md) — 性能、事件、生命周期、组件、动画、平台集成与验证。

---

## 从源码运行示例

仓库根目录的示例需要先按[贡献指南](CONTRIBUTING.zh.md)配置开发环境，
再运行：

```bash
uv run gallery
```

开发、测试与文档规范见贡献指南。

---

## 许可证

[Apache-2.0](LICENSE) © HarcicYang
