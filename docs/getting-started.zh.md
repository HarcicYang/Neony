# 入门教程

> [English version](getting-started.en.md) · [文档首页](README.zh.md)

本教程会带你从一个空的 Python 文件开始，构建一个小型响应式桌面窗口。

示例使用的公开导入路径和模式与 [`demo_hello.py`](../demo_hello.py) 一致。

## 1. 安装前置

Neony 需要 Python 3.11 或更高版本，以及对应平台的原生 WebView 运行时。

普通应用可以安装发布包：

```bash
python -m pip install neony
```

如果你是在本仓库中开发，则安装开发环境：

```bash
uv sync --group dev
```

平台相关依赖见[安装与平台指南](guides/installation-platforms.zh.md)。

## 2. 创建第一个窗口

创建 `hello.py`，写入：

```python
from neony.application import Page, launch
from neony.application.elements import Button, Heading, Text, VStack
from neony.dom import Signal

clicks = Signal(0)
counter = Button("Click me")

counter.bind_text(
    clicks,
    fmt=lambda count: f"Clicked {count} times!" if count else "Click me",
)
counter.on_click(lambda _event: clicks.update(lambda count: count + 1))

page = Page(gap="16px").add(
    VStack(
        Heading("Hello, Neony", level=1),
        Text("Build desktop UI in pure Python.", role="secondary"),
        counter,
        gap="12px",
    )
)

launch(page, title="My App", width=480, height=360)
```

在文件所在目录运行：

```bash
python hello.py
```

仓库中的同等示例是 [`demo_hello.py`](../demo_hello.py)。需要对照经过测试
的仓库示例时，优先阅读该文件。

## 3. 理解界面树

`Page` 是顶层容器，`.add()` 支持链式调用，可以接收组件或原始 DOM 元素。

`VStack` 和 `HStack` 是常用的 flex 容器；需要完整 flex 参数时可以使用
`Flex`。

常用布局参数包括：

- `gap`：子项之间的间距；
- `padding`：容器内部留白；
- `max_width`：限制内容宽度并保持居中；
- `fill=True`：让 chrome 或布局占满窗口高度；
- flex 组件的 `grow`：吸收剩余空间。

[`demo_builder.py`](../demo_builder.py) 展示了居中页面、原始样式 `Div` 和
框架组件的组合方式。

## 4. 处理用户事件

`on_click()` 回调会收到 `DomEvent`。简单计数器只需更新 Signal；如果需要
读取事件字段、执行多个步骤、I/O 或错误处理，可以使用具名的同步/异步函数：

```python
async def save(event) -> None:
    print(event.type, event.value)


button.on_click(save)
```

程序化状态修改会更新界面，但不会伪造用户事件。真正的 DOM 用户交互进入
组件回调时，事件的 `source` 为 `"user"`。完整事件 API 可查当前
[API 参考](api.zh.md)；事件专题指南将在后续补齐。

## 5. 添加响应式展示

Signal 可以直接调用读取，通过 `.set()` 或 `.update()` 写入：

```python
name = Signal("")
label = Text("")
label.bind_text(name, fmt=lambda value: f"Hello, {value}!" if value else "")
```

其他常用绑定：

```python
element.bind_style(signal, "width", fmt=lambda value: f"{value}%")
element.bind_attr(signal, "aria-label")
element.bind_visible(signal)
```

使用 `Computed` 表示派生值，使用 `effect()` 处理副作用；需要事件上下文或
多步骤行为时，仍然使用普通 `on_*` 回调。完整示例
[`demo_reactive.py`](../demo_reactive.py) 同时展示 Signal、Computed、Effect、
`bind_value`、`bind_style` 和 `bind_visible`。

## 6. 设置样式

组件使用类型化 `Styles` 和语义主题 token，常见场景不需要手写原始 CSS：

```python
from neony.application.theme import stub
from neony.dom import Div, Styles

surface = Div(
    styles=Styles(
        padding="16px",
        border_radius="8px",
        background_color=stub.surface,
        color=stub.text_primary,
    )
)
```

内置主题是 `DARK`、`LIGHT` 和 `DEEP_BLUE`。需要自定义 token、transition
或 keyframe 时，再阅读主题与 CSS 专题指南。

## 7. 下一步阅读

- 需要安装帮助：阅读[安装与平台指南](guides/installation-platforms.zh.md)。
- 需要状态同步：后续阅读 `guides/reactive.zh.md`，先运行
  [`demo_reactive.py`](../demo_reactive.py)。
- 需要无边框窗口：查 API 中的 `Page`、`WindowConfig`、`TitleBar`，再运行
  [`demo_custom_window.py`](../demo_custom_window.py)。
- 需要多窗口：运行 [`demo_multi_window.py`](../demo_multi_window.py)。
- 需要组件画廊：运行：

  ```bash
  uv run gallery
  ```

精确签名请查 [API 参考](api.zh.md)；修改仓库前请阅读
[贡献指南](../CONTRIBUTING.zh.md)。
