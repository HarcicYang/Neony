# 安装与平台

> [English version](installation-platforms.en.md) · [入门教程](../getting-started.zh.md) · [文档首页](../README.zh.md)

Neony 会把 Python 构建的 DOM 树渲染到原生 WebView 中。安装 Python 包只是
必要条件之一；WebView 和部分可选桌面集成由操作系统提供。

## Python 环境

从包索引安装应用依赖：

```bash
python -m pip install neony
```

在本仓库中开发：

```bash
uv sync --group dev
```

仓库推荐使用 `uv run`，例如：

```bash
uv run gallery
uv run python scripts/check_all.py
```

`package.json` 只用于 JavaScript runtime 测试。干净 checkout 不会包含被 Git
跟踪的 `node_modules/`；如果目录不存在，`scripts/check_all.py` 会自动执行
`npm ci`。

## Linux

项目主要在 Linux Wayland 上开发和验证。Debian/Ubuntu CI 使用以下开发包：

```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

已安装的应用还需要对应的 WebKitGTK runtime；只有开发头文件并不足够。不同
发行版的包名可能不同，请安装与 WebKitGTK 4.1 开发包匹配的运行时包。

系统托盘还需要：

```text
libayatana-appindicator
```

如果它不存在，普通窗口应用仍可运行；应用层会记录日志并跳过托盘创建。

### Wayland、X11 与 CI

Wayland 是当前 Linux 的主要验证目标。Linux blur 会在支持的 compositor 上
使用 background-effect 协议；窗口定位也会受到 Wayland 规则限制。

X11 目前不是完整支持目标。CI 使用 `xvfb-run` 做无头启动 smoke 测试，这只能
证明 demo 能进入事件循环，不能证明所有 X11 桌面行为或最终绘制效果。

## Windows

Windows 使用系统 WebView2 runtime。运行应用前请安装或启用 WebView2。Acrylic、
Mica 等原生窗口材质取决于平台和窗口配置。

项目的 Nuitka workflow 支持 Windows 打包，但正式发布前仍应在目标 Windows
版本上单独验证所需功能。

## macOS

macOS 使用系统提供的 WKWebView。文件对话框使用 `osascript`，透明窗口可以请求
原生 blur。WKWebView 不会在 web drop 事件中提供完整的文件系统元数据；依赖文件
路径的应用应使用 Neony native drop channel，并在目标系统上测试。

仓库的 Linux CI 没有完整覆盖 macOS runtime 和 HiDPI/mixed-DPI 行为，这些属于
需要单独验证的平台工作。

## 原生文件对话框

公开的异步方法是：

```python
path = await app.open_file()
paths = await app.open_files()
destination = await app.save_file(default_name="output.txt")
folder = await app.select_folder()
```

worker 会按平台选择实现：

```text
Linux   → 优先 zenity，否则 tkinter
macOS   → osascript
Windows → PowerShell
其他    → tkinter fallback
```

调用在 executor 线程中运行，对话框打开时 asyncio 事件循环仍可处理其他任务。
单选取消返回 `None`，多选取消返回 `[]`。文件过滤器使用 `(label, pattern)`
列表，例如：

```python
filetypes = [("PNG images", "*.png"), ("All files", "*.*")]
```

平台命令或 fallback 无法启动时，公开 API 会把常见失败/取消结果归一为同样的空
返回形状。正式发布到某个平台前，应在该平台实测 picker 行为。

## 常见问题

| 现象 | 首要检查 |
| --- | --- |
| Linux WebView 无法启动 | 确认 WebKitGTK runtime 和 GTK 库已安装，查看进程 stderr。 |
| 没有托盘图标 | 安装 `libayatana-appindicator`；托盘是可选功能，创建失败会被跳过。 |
| 文件选择器没有出现 | 检查 `zenity`/`osascript`/PowerShell 或 tkinter，以及显示会话环境。 |
| CI 中 demo 立即退出 | 使用 `xvfb-run`；静态检查不要直接打开真实桌面窗口，应使用 `tests/smoke_demos.py`。 |
| 透明窗口没有 blur | 检查 compositor/平台支持；blur 失败不会让窗口崩溃，窗口仍可使用。 |

想先运行一个应用，请回到[入门教程](../getting-started.zh.md)。需要精确配置
字段时，请查阅 [API 参考](../api.zh.md)。
