# 为 Neony 贡献

> [Contributing (English)](CONTRIBUTING.md)

感谢你考虑为 Neony 做贡献。这是一个 alpha 项目——反馈、bug 报告与
Pull Request 都非常欢迎。本文档说明项目约定与贡献方式。

---

## 项目约定

以下是基本规则。违反这些约定的贡献可能会被退回修改。

### 1. 纯 Python API

用户永远不需要接触 HTML、JavaScript 或 CSS 字符串。布局、样式、事件、
窗口控制全部以 Python 对象暴露。不要在公开 API 中暴露原始的 JS/HTML
机制;内部实现(如 `data-window-action` 属性、JS 引擎)保持内部。

### 2. 状态在组件内部管理

组件拥有自己的状态。编程式修改更新 DOM 但不触发回调;用户事件携带
`source == "user"`。遵循现有 `Component` 模式:封装 `DOMElement` 树
(组合而非继承)、在 `__init__` 中构建为 `self._root`、用 `_bind()` 绑定
事件、在 `_on_event()` 中同步状态。

### 3. 主题通过令牌引用

组件通过 `Color(var="--color-*")` 引用主题颜色，切换主题才能零 DOM diff
全量重绘。切勿硬编码应跟随主题的颜色。

### 4. 双语文档

文档按语言拆分——英语为主，中文独立成文件:

- `readme.md`(EN)/ `readme.zh.md`(中文)
- `docs/api.en.md` / `docs/api.zh.md`
- `CONTRIBUTING.md` / `CONTRIBUTING.zh.md`

新功能必须同步更新两种语言版本。

### 5. 示例位于仓库根目录

可运行示例是根目录的 `test_*.py` 文件(如 `test_gallery.py`)。
新组件应附带示例，并把示例加入 `.zed/tasks.json`。

---

## 开发环境

项目使用 [uv](https://docs.astral.sh/uv/) 管理环境与命令。

```bash
uv sync --group dev     # 安装依赖(含开发工具)
```

### 系统依赖

Linux 上需要 WebKitGTK 技术栈:

```bash
sudo apt-get install libwebkit2gtk-4.1-dev libgtk-3-dev libxdo-dev
```

---

## 运行项目

```bash
uv run test_gallery.py              # 组件画廊示例
uv run test_custom_window.py        # 无边框窗口示例
uv run test_multi_window.py         # 多窗口示例
uv run pytest -q                    # 测试套件
uv run ruff check .                 # 代码检查
uv run ruff format .                # 格式化
uv run pyrefly check                # 类型检查
```

---

## 提交前

1. **运行全部检查** — `ruff check`、`ruff format --check`、
   `pyrefly check` 与 `pytest` 必须全部通过。CI 运行同样的命令。
2. **补充测试** — bug 修复需要回归测试;新组件需要覆盖构建/状态/
   事件(参见 `tests/test_components.py` 中的模式)。
3. **更新文档** — 行为有可见变化时更新 README(两种语言);API 变化
   更新 `docs/api.en.md` / `docs/api.zh.md`。
4. **更新 CHANGELOG** — 在 `CHANGELOG.md` 的未发布章节添加条目。

## Pull Request 流程

1. Fork 仓库并创建分支(`fix/...`、`feat/...`)。
2. 按上述要求完成改动、测试与文档。
3. 向 `master` 发起 PR，说明改动内容与原因，并注明你在哪些平台上
   验证过(例如"已在 Linux/hyprland 测试")。
4. 合并前 CI 必须通过。

## 贡献范围

**欢迎:** bug 修复、遵循现有模式的新组件、文档改进、测试覆盖、
体验打磨。

**先讨论(开 issue):** 大规模 API 变更、架构变更(桥接、diff 引擎、
主题)、许可证变更、新增运行时依赖。

**平台说明:** 项目目前在 Linux 上开发与验证。Windows/macOS 支持尚未
测试——欢迎平台相关的修复，但请明确说明你的验证范围。

---

## 许可证

提交贡献即表示你同意你的工作在项目的 [LGPL-3.0-or-later](LICENSE)
许可下发布。
