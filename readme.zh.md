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
- **主题化滚动条** — 滚动条跟随活跃主题(WebKit + Firefox)
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

| 组件                      | 说明                                                           |
| ------------------------- | -------------------------------------------------------------- |
| `Button`                  | 主题按钮 — primary / ghost / danger 变体，悬停与按压反馈       |
| `Checkbox`                | 自定义复选框，含标签与 change 事件                             |
| `Input`                   | 单行输入框 — text / password / email / number…                 |
| `Heading`                 | 主题标题(h1–h6)，自动字号                                      |
| `Text`                    | 内联文本，支持语义角色(primary / secondary / danger / success) |
| `Tabs`                    | 选项卡栏 + 面板，同时只显示一个                                |
| `Flex`                    | 通用弹性容器，完全控制                                         |
| `VStack` / `HStack`       | 纵向 / 横向弹性堆叠                                            |
| `Spacer`                  | 弹性空白，吸收剩余空间                                         |
| `Separator`               | 细水平分隔线                                                   |
| `GlassPanel`              | 毛玻璃容器，可选背景图                                         |
| `TitleBar`                | 无边框窗口的自定义标题栏 — 拖动、最小化 / 最大化 / 关闭        |
| `Sidebar` / `SidebarItem` | 垂直导航栏，与 TitleBar 同款玻璃风格                           |

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
| `demo_gallery.py`               | 带文档与代码示例的组件画廊，玻璃标题栏 |
| `demo_custom_window.py`         | 无边框窗口:TitleBar + Sidebar 一体装饰 |
| `demo_transparent_panel.py`     | 带原生模糊的透明悬浮面板               |
| `demo_multi_window.py`          | 共享同一 app 状态的双窗口              |
| `demo_reactive.py`              | Signal API:声明式绑定替代手动刷新      |
| `demo_builder.py`               | 不含应用层的原始 DOM 构建              |

```bash
uv run demo_gallery.py
```

---

## 路线图

计划中的工作，大致按优先级排列。

### 性能优化

- [x] **悬停降噪** — `mouseover`/`mouseout`/`focus`/`blur` 延迟渲染(一帧合并)
- [~] **输入节流** — 合并渲染管线已就位；`on_input` 仍逐键渲染，接入延迟路径仅需一行
- [x] **脏子树 diff** — 只有变化的元素重新序列化，变更会向上标记祖先
- [x] **快照复用** — 未变化的子树复用缓存快照，跳过 `to_node()`
- [x] **样式直通补丁** — 纯样式变化绕过全树 diff

### 响应式

- [x] **Signal 原语** — `Signal` / `Computed` / `Effect`，自动依赖追踪 + `batch()` 合并
- [x] **声明式绑定** — 元素与组件上的 `bind_text()` / `bind_style()` / `bind_attr()` / `bind_visible()`
- [x] **跨窗口响应式** — 共享 Signal 写入自动更新所有绑定的窗口
- [x] **JS 单元测试** — vitest + jsdom 覆盖浏览器运行时(事件委托、补丁引擎)

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

- [x] **Windows(WebView2)**
- [ ] **macOS(WKWebView)**
- [x] **Linux 桌面(Wayland)**
- [ ] **HiDPI / 混合 DPI 缩放**

> 注：
> 对于 Linux 兼容性，我们的测试工作将不会覆盖 x11，请自行测试
> 对于 macOS 兼容性，我们没有条件进行实际测试，请自行测试

---

## 开发

本项目使用 [uv](https://docs.astral.sh/uv/) 作为环境管理与运行器。

```bash
uv sync --group dev   # 安装依赖(含开发工具)
npm ci                # 安装 JS 开发依赖(vitest、jsdom)

uv run demo_gallery.py            # 运行示例
uv run pytest -q                  # 运行 Python 测试
uv run ruff check .               # 代码检查
uv run ruff format --check .      # 格式检查
uv run pyrefly check              # 类型检查
npm test                          # 运行 JS 测试(vitest)
```

---

## 许可证

[LGPL-3.0-or-later](LICENSE) © HarcicYang
