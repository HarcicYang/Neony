# Neony

基于 [LumiView](https://lumiview.dev) 的响应式桌面 UI 框架。

[![License: LGPL-3.0](https://img.shields.io/badge/license-LGPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)

> [English README](readme.md) · [API Reference (EN)](docs/api.en.md) · [API 参考 (中文)](docs/api.zh.md) · [贡献指南](CONTRIBUTING.zh.md)

---

## 概览

> **状态:alpha** — API 仍在演进中。欢迎反馈与贡献。

Neony 在原生窗口中渲染响应式 DOM。你完全用 Python 对象——组件、布局、样式——
拼装界面，Neony 自动对浏览器 DOM 做增量更新。不需要写 HTML、JavaScript
或 CSS 字符串。

它基于 [LumiView](https://lumiview.dev)，与 [Tauri](https://tauri.app)
使用相同的 Rust `tao`/`wry` WebView 技术栈。

- **纯 Python API** — 组件、布局、事件，全程不接触 Web 技术
- **与 Tauri 同源** — Rust `tao`/`wry` WebView(经 LumiView)
- **三套主题预设** — dark / light / deep-blue，基于 CSS 自定义属性
- **(可选)毛玻璃** — 半透明表面 + 背景模糊
- **自定义窗口装饰** — 无边框、透明窗口、自定义标题栏
- **(仅支持平台)原生窗口效果** — blur / acrylic / mica 材质

---

## 安装

```bash
pip install neony
```

需要 Python 3.11+，以及对应平台的 WebView 运行时(Linux 为 WebKitGTK，
Windows 为 WebView2，macOS 为 WKWebView)。不支持 X11 — 见
[路线图](#路线图)。

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

| 组件                      | 说明                                                          |
| ------------------------- | ------------------------------------------------------------- |
| `Button`                  | 主题按钮 — primary / ghost / danger 变体，悬停与按压反馈       |
| `Checkbox`                | 自定义复选框，含标签与 change 事件                             |
| `Input`                   | 单行输入框 — text / password / email / number…                |
| `Heading`                 | 主题标题(h1–h6)，自动字号                                      |
| `Text`                    | 内联文本，支持语义角色(primary / secondary / danger / success) |
| `Tabs`                    | 选项卡栏 + 面板，同时只显示一个                                |
| `Flex`                    | 通用弹性容器，完全控制                                         |
| `VStack` / `HStack`       | 纵向 / 横向弹性堆叠                                           |
| `Spacer`                  | 弹性空白，吸收剩余空间                                         |
| `Separator`               | 细水平分隔线                                                  |
| `GlassPanel`              | 毛玻璃容器，可选背景图                                         |
| `TitleBar`                | 无边框窗口的自定义标题栏 — 拖动、最小化 / 最大化 / 关闭       |
| `Sidebar` / `SidebarItem` | 垂直导航栏，与 TitleBar 同款玻璃风格                           |

所有组件共享链式 API，用法见 [API 参考](docs/api.zh.md)。

---

## 窗口特性

- **无边框自定义标题栏** — 设置 `decorations=False`，添加 `TitleBar`，
  拖动 / 最小化 / 最大化 / 关闭全部自动生效。见 [API 参考](docs/api.zh.md)
  与 [`test_custom_window.py`](test_custom_window.py) 示例。
- **透明窗口与原生效果** — `transparent=True` 配合 `apply_blur()`、
  `apply_acrylic()`、`apply_mica()`。见
  [`test_transparent_panel.py`](test_transparent_panel.py)。
- **编程式窗口控制** — `set_title()`、`set_size()`、`minimize()`、
  `toggle_maximize()`、`close()` … 均位于 `NeonApplication`，
  多窗口时接受 `window_index=0` 参数。
- **多窗口** — `run(*pages)` 每个页面一个窗口，共享同一事件循环与
  `app.state`。`launch([...])` 也接受列表。
  见 [`test_multi_window.py`](test_multi_window.py)。

---

## 主题

三套内置预设 — `DARK`(默认)、`LIGHT`、`DEEP_BLUE` — 以 CSS 自定义属性
暴露在 `:root`，切换主题零 DOM diff 全量重绘。切换与自定义主题见
[API 参考](docs/api.zh.md)。

---

## 示例

在仓库根目录运行:

| 文件                        | 演示内容                               |
| --------------------------- | -------------------------------------- |
| `test_gallery.py`           | 带文档与代码示例的组件画廊，玻璃标题栏  |
| `test_custom_window.py`     | 无边框窗口:TitleBar + Sidebar 一体装饰 |
| `test_transparent_panel.py` | 带原生模糊的透明悬浮面板               |
| `test_multi_window.py`      | 共享同一 app 状态的双窗口              |
| `test_reactive.py`          | 最简 `launch()` 应用                   |
| `test_builder.py`           | 不含应用层的原始 DOM 构建              |

```bash
uv run test_gallery.py
```

---

## 路线图

计划中的工作，大致按优先级排列。

### 性能优化

- [ ] **输入节流** — 合并高频 `on_input` 渲染
- [ ] **悬停降噪** — `mouseover`/`mouseout` 不应触发全树渲染
- [ ] **脏子树 diff** — 只重新 diff 状态变化的组件
- [ ] **样式直通补丁** — 纯样式变化绕过全树 diff
- [ ] **快照复用** — 未变化的子树跳过 `to_node()`

### 组件

- [ ] **表单控件** — Radio、Switch、Select/ComboBox、Slider、Progress
- [ ] **浮层** — Dialog/Modal、Tooltip、Dropdown、Menu
- [ ] **数据视图** — DataTable、List、Tree
- [ ] **内容** — Card、Avatar、Badge、Image

### 动画

- [ ] **`Styles` 支持 CSS `transition`**
- [ ] **内置动画容器**
- [ ] **状态切换过渡**

### 平台验证

- [ ] **Windows(WebView2)**
- [ ] **macOS(WKWebView)**
- [X] **Linux 桌面**
- [ ] **HiDPI / 混合 DPI 缩放**
-  x  ~~X11~~ — **不计划支持**

---

## 开发

本项目使用 [uv](https://docs.astral.sh/uv/) 作为环境管理与运行器。

```bash
uv sync --group dev   # 安装依赖(含开发工具)

uv run test_gallery.py            # 运行示例
uv run pytest -q                  # 运行测试
uv run ruff check .               # 代码检查
uv run ruff format --check .      # 格式检查
uv run pyrefly check              # 类型检查
```

---

## 许可证

[LGPL-3.0-or-later](LICENSE) © HarcicYang
