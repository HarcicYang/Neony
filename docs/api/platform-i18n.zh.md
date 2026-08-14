# 平台与国际化

> [English version](platform-i18n.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

国际化、主题，以及平台原生能力——窗口控制、原生文件对话框与系统托盘。
拥有这些能力的应用对象是 [`NeonApplication`](core.zh.md#neonapplication)。

## 国际化（i18n）

响应式、框架级 i18n。当前语言是一个 `Signal`；每个 `tr` 引用都是
`Computed[str]`，因此绑定文本在 `set_language()` 时实时更新，不丢失
widget 状态。

**目录是类型化模型，不是 dict。** `Catalog` 是 frozen pydantic 模型——
每个字段是一个翻译 key，带英文默认值；每种语言一个实例。子类化以添加
应用 key（扁平 `str` 字段或嵌套子模型分组）；pydantic 类默认值天然提供
逐 key 英文回退。

```python
from neony.application import Catalog, Common, Language, register_catalog, set_language, tr, tr_now


class FilesCatalog(Catalog):
    count: str = "{n} files"


class AppCatalog(Catalog):
    save: str = "Save"  # → tr.save
    files: FilesCatalog = FilesCatalog()  # → tr.files.count


register_catalog(Language.EN, AppCatalog())
register_catalog(
    Language.ZH,
    AppCatalog(
        save="保存",
        files=FilesCatalog(count="{n} 个文件"),
        common=Common(copy_text="复制", delete="删除", ok="确定", cancel="取消", close="关闭"),
    ),
)

tr.common.copy_text  # Computed[str] → "Copy"（切换语言时实时更新）
tr.files.count.format(n=5)  # 插值 → "5 files"
tr_now(tr.common.copy_text)  # 即时读、不订阅（展示时解析）
set_language(Language.ZH)  # 所有 tr.* 绑定重新解析
app.set_language(Language.ZH) / app.language  # app 级便捷方法
```

- **`Language`** —— 内置语言的 `StrEnum`（`EN/ZH/JA/FR/DE/ES/PT/RU`）；
  `set_language` 对未知语言抛 `ValueError`。合法但未注册目录的语言回落到英文。
- **`Catalog` / `Common`** —— frozen pydantic 模型（`extra="forbid"` 抓
  key 拼写错误）。`Common` 承载框架自带文案（`copy_text`、`delete`、
  `ok`、`cancel`、`close`）。
- **`tr`** —— 链式代理。`tr.<key>` 与 `tr.<group>.<key>` 各返回一个
  响应式 `Computed[str]`；传给任何接受响应式文本的组件（`Text`、
  `Button`——共享的 `_mount_text` helper 让任意组件都能接入）。
  `tr.<key>.get()` 读当前值。
- **`tr_now(tr.xx.xxx)`** —— 不订阅地读当前值；用于组件默认文案与
  菜单的展示时解析。在 effect 内安全（不漏建依赖）。
- **保留 key 名** —— 与 `Computed` 方法重名（`get`、`format`）或以 `_`
  开头的 key 无法经 `tr` 链引用。
- 框架默认文案（MessageBubble 内置右键菜单、`PromptDialog` 的
  确定/取消）经目录解析。

## 主题

三套内置预设 — `DARK`， `LIGHT`， `DEEP_BLUE` — 以 CSS 自定义属性暴露。每个预设都是
**不可变**的 `Theme` 实例；构造任意 `Theme` 即按其 `mode` 自动注册。

```python
app.theme  # 当前激活的预设（默认 DARK）
Theme.get("light")  # 按 mode 名单次查询已注册预设
app.theme.next()  # 切换顺序里紧接当前预设的下一个
Theme.modes()  # 已注册 mode 名，按预设构造顺序排列
Theme.mode_label("dark")  # "Light mode" — 下一个 mode 的标签
await app.set_theme(LIGHT)  # 切换当前预设并重新注入变量
```

`Theme.set_mode` / `Theme.toggle` 已移除 —— 切换改为经
`NeonApplication.set_theme` 换引用，而非就地改实例。

令牌族: `--color-bg`， `--color-surface`，
`--color-text-primary` / `--color-text-secondary`， `--color-accent`，
`--color-on-accent` / `--color-on-danger`（饱和 accent / danger 填充上的文字色），
`--color-danger`， `--color-success`， `--color-border`， `--color-shadow`，
`--color-*-glass*`(磨砂变体)。

组件通过 `Color(var="--color-*")` 引用令牌。切换主题只替换 `:root`
变量块，不走 DOM diff；浏览器按新的 `var(--color-*)` 重上色。

自定义主题:

```python
from neony.application import Theme

my_theme = Theme(mode="sepia", bg="#1a1a2e", accent="#4a90d9", on_accent="#ffffff", ...)
# 构造即自动注册；需提供全部令牌 —— Theme 无默认值。
await app.set_theme(my_theme)
Theme.get("sepia") is my_theme  # True
```

## 平台原生能力

### 窗口控制

[`NeonApplication`](core.zh.md#neonapplication) 上的所有异步方法：
`set_title`、`set_size`、`minimize`、`toggle_maximize`、`is_maximized`、
`set_fullscreen`、`start_dragging`、`close`、`set_icon`，以及原生
blur/acrylic/mica 效果（`apply_blur`、`apply_acrylic`、`apply_mica`、
`clear_effect`）。`transparent=True` 会自动套上平台材质（Linux 在合成器
支持时走 Wayland blur，Windows 为 Acrylic，macOS 为 Blur）。`apply_*`
是手动覆盖，且受平台限制：`apply_blur` 仅 macOS/Windows；acrylic / mica
仅 Windows 11。每个窗口控制方法都接受可选的 `window_index`（默认 0），用于多窗口应用。

### 原生文件对话框

公开的 async 方法为 `open_file`、`open_files`、`save_file` 与
`select_folder`（签名见 [`NeonApplication`](core.zh.md#neonapplication)）。worker 按平台选择实现：

```text
Linux   → 优先 zenity，否则 tkinter
macOS   → osascript
Windows → PowerShell
其他    → tkinter fallback
```

调用在 executor 线程中运行，对话框打开时 asyncio 事件循环仍可处理其他任务。
单选取消返回 `None`，多选取消返回 `[]`。文件过滤器使用 `(label, pattern)`
列表，例如 `[("PNG images", "*.png"), ("All files", "*.*")]`。平台命令或
fallback 无法启动时，公开 API 会把常见失败/取消结果归一为同样的空返回形状
——绝不抛异常。正式发布到某个平台前，应在该平台实测 picker 行为。

运行时依赖与排查表见
[安装与平台指南](../guides/installation-platforms.zh.md)。

### 系统托盘

原生托盘在 `run()` 之前经 `app.tray = Tray(...)` 配置。完整 API 见核心
章节的 `Tray` & `TrayItem`（[核心章节](core.zh.md)）。平台注意：Linux
需要 `libayatana-appindicator`，tooltip 不支持、菜单创建后不可替换。
