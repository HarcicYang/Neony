# Neony 文档

> [English documentation](README.en.md)

Neony 是一个处于 pre-beta 阶段的 Python 响应式桌面 UI 框架。本目录按
使用任务组织：新用户先读入门教程，常见功能查阅指南，需要精确签名时再查
API 参考。

## 从这里开始

- [入门教程](getting-started.zh.md) —— 从安装 Neony 开始，逐步构建一个小型
  响应式窗口。
- [安装与平台](guides/installation-platforms.zh.md) —— 系统依赖、平台边界、
  原生对话框和故障排查。
- [示例索引](../readme.zh.md#示例) —— 当前仓库根目录中的可运行示例。

## 指南

新用户应优先沿着入门教程阅读；指南覆盖常见应用功能。

- [安装与平台](guides/installation-platforms.zh.md)
- [贡献指南](../CONTRIBUTING.zh.md)
- [路线图](../ROADMAP.md)
- [变更记录](../CHANGELOG.md)

## API 参考

参考文档已拆分为成对章节——每个章节覆盖一个领域，提供短签名、参数、
返回值、边界说明与简短示例。

- [API 索引](api/README.zh.md) —— 完整章节列表。
- [核心](api/core.zh.md) —— 应用、入口、生命周期、托盘。
- [组件](api/components.zh.md) —— 表单控件、浮层、内容。
- [布局与窗口装饰](api/layout-chrome.zh.md) —— 弹性面板、侧边栏、树、
  列表、表格。
- [DOM 与 CSS](api/dom-css.zh.md) —— `Color`、`Styles`、`DomEvent`、拖拽。
- [响应式](api/reactive.zh.md) —— `Signal`、`Computed`、绑定。
- [平台与国际化](api/platform-i18n.zh.md) —— 主题、i18n、原生能力。

旧的合并入口 [`api.zh.md`](api.zh.md) 作为稳定链接目标保留，并重定向到
上述章节。API 符号、导入路径、命令和示例文件名在两种语言中保持原样，方便
直接复制代码。

## 语言与职责

英文和中文使用独立文件，并通过文件头互相链接。新增功能应同步更新两种
语言。教程性解释放在指南中；短签名、参数、返回值和边界行为放在 API
参考中。根目录 README 继续负责项目概览和最短入口。

返回[中文 README](../readme.zh.md)，或阅读 [English README](../readme.md)。
