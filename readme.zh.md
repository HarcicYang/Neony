# Neony

基于 [LumiView](https://lumiview.dev) 的响应式桌面 UI 框架。

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#)

> [English README](readme.md) · [API Reference (EN)](docs/api.en.md) · [API 参考 (中文)](docs/api.zh.md)

---

## 概览

Neony 在原生窗口中渲染响应式 DOM。你完全用 Python 对象——组件、布局、样式——
拼装界面,Neony 自动对浏览器 DOM 做增量更新。不需要写 HTML、JavaScript
或 CSS 字符串。

- **纯 Python API** — 组件、布局、事件,全程不接触 Web 技术
- **响应式引擎** — 首次渲染挂载整棵树,之后只发送最小变更补丁
- **三套主题预设** — dark / light / deep-blue,基于 CSS 自定义属性
- **毛玻璃** — 半透明表面 + 背景模糊
- **自定义窗口装饰** — 无边框、透明窗口、自定义标题栏
- **原生窗口效果** — blur / acrylic / mica 材质

---

## 安装

```bash
pip install neony
```

需要 Python 3.11+,以及对应平台的 WebView 运行时(Linux 为 WebKitGTK,
Windows 为 WebView2,macOS 为 WKWebView)。

---

## 快速开始

### 最简单的方式 — `launch()`

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

### 完整控制 — `NeonApplication`

```python
from neony.application import Config, NeonApplication, Page, WebViewConfig, WindowConfig

app = NeonApplication(
    Config(
        window=WindowConfig(title="My App", width=480, height=360),
        webview=WebViewConfig(devtools=True),
    )
)
app.state.my_value = "hello"  # 共享状态


def main() -> None:
    app.run(page)


if __name__ == "__main__":
    main()
```

---

## 组件

从 `neony.application.elements` 导入。

| 组件 | 说明 |
|---|---|
| `Button` | 主题按钮 — primary / ghost / danger 变体,悬停与按压反馈 |
| `Checkbox` | 自定义复选框,含标签与 change 事件 |
| `Input` | 单行输入框 — text / password / email / number… |
| `Heading` | 主题标题(h1–h6),自动字号 |
| `Text` | 内联文本,支持语义角色(primary / secondary / danger / success) |
| `Tabs` | 选项卡栏 + 面板,同时只显示一个 |
| `Flex` | 通用弹性容器,完全控制 |
| `VStack` / `HStack` | 纵向 / 横向弹性堆叠 |
| `Spacer` | 弹性空白,吸收剩余空间 |
| `Separator` | 细水平分隔线 |
| `GlassPanel` | 毛玻璃容器,可选背景图 |
| `TitleBar` | 无边框窗口的自定义标题栏 — 拖动、最小化 / 最大化 / 关闭 |
| `Sidebar` / `SidebarItem` | 垂直导航栏,与 TitleBar 同款玻璃风格 |

所有组件共享链式 API:

```python
button.on_click(handler)  # 绑定事件
button.label = "New"  # 修改状态(不触发回调)
button.reset_styles(Styles(...))  # 替换基础样式
```

---

## 窗口特性

### 无边框自定义标题栏

设置 `decorations=False`,由 `TitleBar` 组件全权接管:

```python
app = NeonApplication(
    Config(
        window=WindowConfig(
            title="Neony Studio",
            width=600,
            height=480,
            decorations=False,
            transparent=True,
        ),
        webview=WebViewConfig(devtools=True),
    )
)

titlebar = TitleBar("Neony Studio")  # 零配置 — 拖动 / 最小化 / 最大化 / 关闭
titlebar.on_close(lambda e: print("bye"))  # 附加回调
titlebar.override_close(confirm_close)  # 完全接管关闭动作

page = Page(gap="0px", padding="0px", max_width="100%", fill=True, radius="12px")
page.add(VStack(titlebar, content, gap="0px", grow=1))
```

- 拖动标题栏移动窗口,双击最大化。
- `override_close(fn)` 可禁用内置关闭动作,用于关闭前确认。

### 透明窗口与原生效果

```python
window = WindowConfig(transparent=True, always_on_top=True)
await app.apply_blur()  # 原生模糊
await app.apply_acrylic()  # Windows 11 acrylic
await app.apply_mica()  # Windows 11 mica
```

### 编程式窗口控制

`set_title()`, `set_size()`, `minimize()`, `toggle_maximize()`,
`set_fullscreen()`, `start_dragging()`, `close()`, `eval_js()` —
以上方法均位于 `NeonApplication`,多窗口时每个方法都接受
`window_index=0` 参数。

### 多窗口

向 `run()` 传入多个页面,每个页面打开一个窗口。所有窗口共享同一个
LumiView 事件循环与 `app.state` 命名空间;事件处理器只重渲染
事件来源窗口。

```python
app.run(page_one, page_two)


async def on_ready() -> None:
    await app.set_title("Counter", window_index=0)
    await app.set_title("Display", window_index=1)


app.ready_handler = on_ready
```

`launch()` 也接受列表:

```python
launch([page_one, page_two], title="Multi", width=360, height=240)
```

---

## 主题

三套内置预设 — `DARK`(默认)、`LIGHT`、`DEEP_BLUE` — 以 CSS 自定义属性
暴露在 `:root`,切换主题零 DOM diff 全量重绘。

```python
app.theme.set_mode("light")  # dark | light | deep-blue
app.theme.toggle()  # 循环切换
await app.sync_theme()  # 重新注入 CSS 变量
```

### 背景图与玻璃

```python
await app.set_background("https://example.com/bg.webp")
# 玻璃组件(glass=True、GlassPanel)通过半透明表面模糊背景图
```

---

## 示例

在仓库根目录运行:

| 文件 | 演示内容 |
|---|---|
| `test_gallery.py` | 带文档与代码示例的组件画廊,玻璃标题栏 |
| `test_custom_window.py` | 无边框窗口:TitleBar + Sidebar 一体装饰 |
| `test_transparent_panel.py` | 带原生模糊的透明悬浮面板 |
| `test_multi_window.py` | 共享同一 app 状态的双窗口 |
| `test_reactive.py` | 最简 `launch()` 应用 |
| `test_builder.py` | 不含应用层的原始 DOM 构建 |

```bash
python test_gallery.py
```

---

## 许可证

[GPL-3.0-or-later](LICENSE) © HarcicYang
