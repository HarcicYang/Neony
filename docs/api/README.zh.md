# Neony API 参考

> [English version](README.en.md) · [文档首页](../README.zh.md)

参考文档已拆分为成对章节。每个章节覆盖一个领域，提供短签名、参数、
返回值、边界说明与简短示例；长篇解释放在专题指南中。API 符号、导入
路径、命令与示例文件名在两种语言中均保持英文，便于直接复制代码。

## 章节

- [核心](core.zh.md) — `NeonApplication`、`launch`、`Config` /
  `WindowConfig` / `WebViewConfig`、`Page`、生命周期、多窗口、导航策略、
  `Tray`。
- [组件](components.zh.md) — 表单控件、文本与标签页、浮层与反馈、
  内容组件，以及 `Reorder` 拖拽重排组件。
- [布局与窗口装饰](layout-chrome.zh.md) — `VStack` / `HStack` / `Flex` /
  `Separator` / `GlassPanel`、`TitleBar`、`Sidebar` / `Pane` /
  `SidebarGroup`、`Tree`、`List`、`DataTable`、`Icon`。
- [DOM 与 CSS](dom-css.zh.md) — `Color`、`Styles`、`DomEvent`、原始 HTML
  元素与底层拖拽原语。
- [响应式](reactive.zh.md) — `Signal`、`Computed`、`effect` / `Effect`、
  `untrack`、`SharedSignal`、声明式绑定、`bind_value`、脏子树追踪。
- [平台与国际化](platform-i18n.zh.md) — 国际化、主题，以及平台原生能力
  （窗口控制、原生文件对话框、系统托盘）。

## 稳定性

Neony 处于 pre-beta。部分名称仍保留已弃用别名（如 `active_key` →
`selected_key`）；各章节会在文中标注。逐版本变更见项目
[CHANGELOG](../../CHANGELOG.md)。

尚未拆出的精确签名，旧的合并入口暂时保留在 [`api.zh.md`](../api.zh.md)，
作为稳定链接目标，供读者与外部链接过渡使用。
