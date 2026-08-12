# Neony

基于 [LumiView](https://github.com/xiaosuawa/lumiview) 的响应式桌面 UI 框架。

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)

> [English README](readme.md) · [API Reference (EN)](docs/api.en.md) · [API 参考 (中文)](docs/api.zh.md) · [贡献指南](CONTRIBUTING.zh.md)

---

## 概览

> **状态:alpha** — API 仍在演进中。欢迎反馈与贡献。

Neony 在原生窗口中渲染响应式 DOM。你完全用 Python 对象——组件、布局、样式——
拼装界面，Neony 自动对浏览器 DOM 做增量更新。不需要写 HTML、JavaScript。

它基于 [LumiView](https://lumiview.dev)，与 [Tauri](https://tauri.app)
使用相同的 Rust `tao`/`wry` WebView 技术栈。

- **纯 Python API** — 组件、布局、事件，全程不接触 Web 技术
- **细粒度响应式** — `Signal` / `Computed` / `Effect` 原语 + 声明式绑定
- **脏子树 diff** — 只有变化的元素重新序列化，未变子树复用缓存快照
- **样式直通补丁** — 纯样式/属性变化(hover、focus、press)直接从快照缓存打补丁，跳过序列化与 diff
- **与 Tauri 同源** — Rust `tao`/`wry` WebView(经 LumiView)
- **三套主题预设** — dark / light / deep-blue，基于 CSS 自定义属性
- **(可选)毛玻璃** — 半透明表面 + 背景模糊
- **语义色光晕** — 焦点环与悬停辉光跟随元素语义颜色
- **滚动指示器** — 原生滚动条被隐藏；滚动表面获得随主题的浮动拇指(静止时淡显、滚动/悬停时增强、可拖拽、点击轨道翻页)，以及只在内容真正溢出方向显示的动态边缘渐变
- **自定义窗口装饰** — 无边框、透明窗口、自定义标题栏
- **(仅支持平台)原生窗口效果** — blur / acrylic / mica 材质

---

## 安装

```bash
pip install neony
```

需要 Python 3.11+，以及对应平台的 WebView 运行时(Linux 为 WebKitGTK，
Windows 为 WebView2，macOS 为 WKWebView)。不支持 X11 — 见
[路线图](ROADMAP.md)。系统托盘在 Linux 需要 `libayatana-appindicator`。

---

## 快速开始

```python
from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack

counter = Button("Click me")


async def on_click(event) -> None:
    counter.label = "Clicked!"


counter.on_click(on_click)

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

| 组件                      | 说明                                                           |
| ------------------------- | -------------------------------------------------------------- |
| `Button`                  | 主题按钮 — primary / ghost / danger 变体，悬停与按压反馈       |
| `Checkbox`                | 自定义复选框，含标签与 change 事件                             |
| `Radio` / `RadioGroup`    | 互斥单选组，组 change 携带选中值                               |
| `Switch`                  | 轨道 + 滑块开关，基于原生 checkbox                             |
| `Select`                  | 主题下拉框 — `str` 或 `(value, label)` 选项                    |
| `ComboBox`                | 可编辑文本 + 主题化建议面板                                    |
| `Slider`                  | 动画填充滑块 — 有级或无级（`step="any"`）                     |
| `Progress`                | 动画填充进度条 — 确定值或滑动 `indeterminate`                  |
| `Dialog`                  | 固定 scrim + 居中玻璃面板 — scrim / Escape / ✕ / 点击外部关闭   |
| `Tooltip`                 | 包裹 anchor 的悬停气泡，placement 偏移 + 悬停延迟               |
| `Dropdown`                | trigger 下的主题化弹出面板 — 完整键盘导航 + 点击外部关闭        |
| `Menu`                    | 光标定位的固定弹出菜单（`open_at(x, y)` 来自 contextmenu）      |
| `Toast`                   | 屏幕边缘的瞬时通知 — 6 方位、success/info/error、与方位绑定的方向性动画 |
| `Input`                   | 单行输入框 — text / password / email / number…                 |
| `Heading`                 | 主题标题(h1–h6)，自动字号                                      |
| `Text`                    | 内联文本，支持语义角色(primary / secondary / danger / success) |
| `Tabs`                    | 选项卡栏 + 面板，同时只显示一个 — 构造器子项、`selected_panel` / `selected_title` / `selected_key` |
| `Accordion` / `Collapsible` | 单列滚动流中的可展开分组 — 流畅 `.section()`、多组同时展开、`expanded_keys`、`on_change` |
| `Tree` / `TreeNode`       | 可折叠导航树 + 内容宿主 — 任意深度、流畅建造器写法、点叶子在右侧显示其面板 |
| `List` / `ListItem`       | 可滚动单选数据列表 — listbox 模型、方向键移动选中、`selected_key` / `bind_selected` |
| `DataTable` / `Column`    | 列配置 + 数据行 — 固定表头、点击排序、单选 / 多选行 |
| `Reorder` / `ReorderItem` | 拖拽重排面板 — 任意组件/DOM 元素都可作为卡片；`direction` + `wrap` 可作网格纵横双向重排，多个面板可交换卡片 |
| `Icon`                    | 统一图标 — `Icon.image(url)` 固定方形图片或 `Icon.glyph(text)` 字形，TitleBar / Sidebar / Tabs / Tree 共用 |
| `Flex`                    | 通用弹性容器，完全控制                                         |
| `VStack` / `HStack`       | 纵向 / 横向弹性堆叠                                            |
| `Spacer`                  | 弹性空白，吸收剩余空间                                         |
| `Separator`               | 细水平分隔线                                                   |
| `GlassPanel`              | 毛玻璃容器，可选背景图                                         |
| `TitleBar`                | 无边框窗口的自定义标题栏 — 拖动、最小化 / 最大化 / 关闭        |
| `Sidebar` / `SidebarItem` | 拥有内容面板的垂直导航 — `Pane`、`SidebarGroup` 分组小节、每面板快捷键;与 TitleBar 同款玻璃风格 |
| `Pane`                    | 可选的 Sidebar 条目 + 内容面板 — `key`、`icon`、`section`、`shortcut` |
| `SidebarGroup`            | Sidebar 的分组小节 — 条目上方的小号大写标签                    |
| `Image`                   | 主题化图片，圆角 overflow-hidden 框架（`src` 为任意 URL）     |
| `Avatar`                  | 用户头像 — 图片 / 字母占位 / 空占位，可选角标 `badge`         |
| `Badge`                   | 状态标签或角标计数 — 多变体、状态点、`99+` 截断、0 自动隐藏    |
| `Card`                    | 带标题的内容卡片 — 操作区、页脚、可选毛玻璃 `glass` 表面       |
| `MessageBubble`           | QQ/Telegram 风格聊天消息 — from_me 对齐/配色、可选头像 + 昵称、内置右键菜单、hover 快捷操作 |
| `NoticeBubble`            | 聊天居中的系统提示药丸                                           |

所有组件共享链式 API，用法见 [API 参考](docs/api.zh.md)。

---

## 窗口特性

- **无边框自定义标题栏** — 设置 `decorations=False`，添加 `TitleBar`，
  拖动 / 最小化 / 最大化 / 关闭全部自动生效。见 [API 参考](docs/api.zh.md)
  与 [`demo_custom_window.py`](demo_custom_window.py) 示例。
- **透明窗口与原生效果** — `transparent=True` 配合 `apply_blur()`、
  `apply_acrylic()`、`apply_mica()`。见
  [`demo_transparent_panel.py`](demo_transparent_panel.py)。
- **编程式窗口控制** — `set_title()`、`set_size()`、`minimize()`、
  `toggle_maximize()`、`close()` … 均位于 `NeonApplication`，
  多窗口时接受 `window_index=0` 参数。
- **多窗口** — `run(*pages)` 每个页面一个窗口，共享同一事件循环与
  `app.state`。`launch([...])` 也接受列表。
  见 [`demo_multi_window.py`](demo_multi_window.py)。
- **系统托盘** — `app.tray = Tray(icon, tooltip, items=[...])` 添加
  托盘图标与原生右键菜单；`close_to_tray=True` 关窗时隐藏应用而非退出。
  Linux 需要 `libayatana-appindicator`。见
  [`demo_tray.py`](demo_tray.py)。
- **原生文件对话框** — `app.open_file()`、`app.open_files()`、
  `app.save_file()`、`app.select_folder()` 在一次性 tkinter 子进程中
  显示自绘的深色主题文件选择器；结果通过类型化的 `multiprocessing`
  管道返回（取消返回 `None`，多选取消返回 `[]`）。没有 stdout/JSON
  文本解析，事件循环保持响应。

---

## 主题

三套内置预设 — `DARK`(默认)、`LIGHT`、`DEEP_BLUE` — 以 CSS 自定义属性
暴露在 `:root`，切换主题零 DOM diff 全量重绘。滚动条与交互光晕(焦点环、
悬停辉光)引用同一套 `--color-*` token，因此也随主题自动切换。切换与
自定义主题见 [API 参考](docs/api.zh.md)。

---

## 示例

在仓库根目录运行:

| 文件                            | 演示内容                               |
| ------------------------------- | -------------------------------------- |
| `demo_hello.py`                 | 最小示例(与快速入门一致)               |
| `gallery` 包(`uv run gallery`) | 带文档与代码示例的组件画廊，玻璃标题栏 |
| `demo_custom_window.py`         | 无边框窗口:TitleBar + Sidebar 一体装饰 |
| `demo_transparent_panel.py`     | 带原生模糊的透明悬浮面板               |
| `demo_multi_window.py`          | 共享同一 app 状态的双窗口              |
| `demo_reactive.py`              | Signal API:声明式绑定替代手动刷新      |
| `demo_accordion.py`             | Accordion:单列滚动流中的可展开分组     |
| `demo_tree.py`                  | Tree:可折叠导航树 + 内容宿主           |
| `demo_tray.py`                  | 系统托盘:原生菜单 + 关闭到托盘模式     |
| `demo_builder.py`               | 使用 `Page` + 组件 + `launch()` 的最小应用 |

```bash
uv run gallery
```

---

## 路线图

计划中的工作已移入 [ROADMAP.md](ROADMAP.md) — 性能、事件、生命周期、
组件、动画、平台集成与验证。

---

## 开发

本项目使用 [uv](https://docs.astral.sh/uv/) 作为环境管理与运行器。

```bash
uv sync --group dev   # 安装依赖(含开发工具)

uv run gallery                       # 运行组件画廊
uv run python scripts/check_all.py   # 运行完整检查(ruff / pyrefly / pytest / vitest)
```

---

## 许可证

[Apache-2.0](LICENSE) © HarcicYang
