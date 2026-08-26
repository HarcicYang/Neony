# 为 Neony 贡献

> [Contributing (English)](CONTRIBUTING.md)

感谢你考虑为 Neony 做贡献。这是一个 pre-beta 项目——反馈、bug 报告与
Pull Request 都非常欢迎。本文档说明项目约定与贡献方式。

---

## 项目约定

以下是基本规则。违反这些约定的贡献可能会被退回修改。

### 1. 纯 Python API

用户永远不需要接触 HTML、JavaScript 或 CSS 字符串。布局、样式、事件、
窗口控制全部以 Python 对象暴露。不要在公开 API 中暴露原始的 JS/HTML
机制;内部实现(如 `data-window-action`、浏览器侧管道)保持内部。

### 2. 状态在组件内部管理

组件拥有自己的状态。编程式修改更新 DOM 但不触发回调;用户事件携带
`source == "user"`。遵循现有 `Component` 模式:封装 `DOMElement` 树
(组合而非继承)、在 `__init__` 中构建为 `self._root`、用 `_bind()` 绑定
事件、在 `_on_event()` 中同步状态。

例外与补充约定:

- **生命周期伪事件**是唯一例外——`open`/`close` 这类伪事件(`_dispatch_pseudo`)
  在编程式写入时**也会**触发回调,这是有意设计(见 `Dialog.open`)。
- **`_bound_events` 必须等于组件内部真正 `_dispatch` 过的事件集合**——
  声明了却从不分发,用户的 `on_*` 回调就是死回调。
- **绕开 `_bind` 的 raw handler 必须手动 `event.source = "user"`**(或改走
  `_bind` 让基类自动设)。
- **滚动/自固定组件必须挂在确定高度 flex 父级**——自固定容器用
  `flex-grow + flex-basis:0 + min-height:0`;滚动元素还要有显式高度基准
  (cross-axis 用 `height:100%`)。挂在 auto 高度父级上,滚动会失效、组件
  会把页面撑开。新组件照此实现并在 docstring 声明挂载契约。

### 3. 主题通过令牌引用

组件通过 `Color(var="--color-*")` 引用主题颜色，切换主题才只需替换
`:root` 变量、不走 DOM diff。切勿硬编码应跟随主题的颜色。

### 4. 双语文档

文档按语言拆分——英语为主，中文独立成文件:

- `readme.md`(EN)/ `readme.zh.md`(中文)
- `docs/api/*.en.md` / `docs/api/*.zh.md`
- `CONTRIBUTING.md` / `CONTRIBUTING.zh.md`

新功能必须同步更新两种语言版本。

### 5. 示例位于仓库根目录

可运行示例是根目录的 `demo_*.py` 文件(如 `demo_custom_window.py`)。
组件画廊是例外——它位于 `neony.gallery` 包中(`uv run gallery`)。
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
uv run gallery                      # 组件画廊示例
uv run demo_custom_window.py        # 无边框窗口示例
uv run demo_multi_window.py         # 多窗口示例
uv run python scripts/check_all.py  # 完整检查 — ruff / pyrefly / pytest / vitest
```

浏览器侧运行时（事件委托、点击外部关闭处理）有自己的 JS 测试套件，
位于 `tests/js/`，由 `scripts/check_all.py` 一并运行（jsdom 环境下的
vitest）。干净 checkout 不包含被 Git 跟踪的 `node_modules/`；目录不存在时，
检查脚本会自动执行 `npm ci`。新增 **Python** 组件通常不需要写 JS 测试——
只有改了 `src/neony/javascript/*` 才需要补充用例。

---

## 提交前

1. **运行全部检查** — 一条命令跑完整套件：
   `uv run python scripts/check_all.py`（ruff check + format、pyrefly、
   pytest 与 JS 的 vitest）。任何一项失败脚本都以非零退出码结束——
   这正是 CI 的 `test` job 所运行的命令，本地跑绿即 CI 跑绿。
   `--fix` 会先应用 ruff 的自动修复；`--smoke` 额外运行需要显示环境
   的冒烟测试（Linux 上需要 `xvfb-run`）。
2. **补充测试** — bug 修复需要回归测试;新组件需要覆盖构建/状态/
   事件(参见 `tests/test_components.py` 中的模式)。
3. **更新文档** — 行为有可见变化时更新 README（两种语言）；API 变化更新
   成对的 `docs/api/*.en.md` / `docs/api/*.zh.md` 章节；章节列表变化时
   同步更新 `docs/api/README.*`；新增的 demo 也要加入根 README 的 demos 表。
4. **遵循 Conventional Commits** — 提交信息加类型与可选 scope 前缀:
   `feat(scope):`、`fix(scope):`、`perf(scope):`、`refactor(scope):`、
   `docs:`、`chore:`、……。Changelog(`CHANGELOG.md`)由人工维护;
   GitHub release 描述由 GitHub 根据提交列表自动生成。

## Pull Request 流程

1. Fork 仓库并创建分支(`fix/...`、`feat/...`)。
2. 按上述要求完成改动、测试与文档。
3. 向 `master` 发起 PR，说明改动内容与原因，并注明你在哪些平台上
   验证过(例如"已在 Linux/hyprland 测试")。
4. 合并前 CI 必须通过。

## 贡献范围

**欢迎:** bug 修复、遵循现有模式的新组件、文档改进、测试覆盖、
体验打磨。

**先讨论(开 issue):** 大规模 API 变更、架构变更(窗口桥接、渲染内部机制、
主题)、许可证变更、新增运行时依赖。

**平台说明:** 路线图目前将 Windows/WebView2 和 Linux Wayland 标记为已验证目标。
macOS/WKWebView 与 HiDPI/mixed-DPI 行为仍需要单独验证。CI 会通过 Xvfb 使用
X11 做无头启动检查，但这不等同于完整的 X11 桌面支持承诺。提交平台相关修改
时，请明确写出实际验证过的环境。

---

## 许可证

提交贡献即表示你同意你的工作在项目的 [Apache-2.0](LICENSE)
许可下发布。
