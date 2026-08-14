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

项目主要在 Linux Wayland 上开发和验证。原生 WebView 绑定链接的是
**WebKitGTK 4.1** API（GTK 3、libsoup 3），因此每个发行版都需要安装能提供
`libwebkit2gtk-4.1.so.0` 的包。不同发行版的包名不同，下面给出常见发行版
的安装命令。

### 开发依赖

Debian 和 Ubuntu：

```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

Fedora：

```bash
sudo dnf install -y webkit2gtk4.1-devel gtk3-devel libxdo-devel
```

Arch Linux：

```bash
sudo pacman -S --needed webkit2gtk-4.1 gtk3 xdotool
```

openSUSE：

```bash
sudo zypper install libwebkit2gtk-4_1-0-devel gtk3-devel libxdo-devel
```

> 上面的每个 `-dev`/`-devel`/普通包都会通过依赖关系自动带入与之匹配的
> WebKitGTK 4.1 运行时、GTK 3 和 libsoup 3。

### 打包应用所需的运行时依赖

打包后的应用需要对应的 WebKitGTK **运行时**，而不是编译头文件。在目标机器上
只需安装运行时包：

```text
Debian/Ubuntu : sudo apt-get install libwebkit2gtk-4.1-0
Fedora        : sudo dnf install webkit2gtk4.1
Arch Linux    : sudo pacman -S webkit2gtk-4.1
openSUSE      : sudo zypper install libwebkit2gtk-4_1-0
```

> Arch 用户注意：上游打包流程曾记录 `webkit2gtk-6.0`，但该包提供的是 GTK 4 /
> 更新的 API，并非本框架所链接的版本。本框架面向 WebKitGTK 4.1 API，因此请
> 安装 `webkit2gtk-4.1`。

### 可选的系统托盘依赖

原生托盘集成在运行时动态加载该库，因此它是可选依赖而非硬链接：

```text
Debian/Ubuntu : libayatana-appindicator3-1  （构建时还需 libayatana-appindicator3-dev）
Fedora        : libayatana-appindicator-gtk3
Arch Linux    : libayatana-appindicator
openSUSE      : libayatana-appindicator3-1
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
