# Neony API 参考

> [English version](README.en.md) · [文档首页](../README.zh.md)

每个章节覆盖一个领域，提供短签名、参数、返回值、边界说明与简短示例；
长篇解释放在专题指南中。API 符号、导入路径、命令与示例文件名在两种
语言中均保持英文，便于直接复制代码。

## 章节

- [核心](core.zh.md) — `NeonApplication`、`launch`、`Config` /
  `WindowConfig` / `WebViewConfig`、`Page`、生命周期、多窗口、导航策略、
  `Tray`。
- [组件](components.zh.md) — 表单控件、文本与标签页、浮层与反馈、
  内容组件、`Menu` / `MenuBranch` / `CascadingDropdown` 级联菜单，
  以及 `Reorder` 拖拽重排组件。
- [布局与窗口装饰](layout-chrome.zh.md) — `VStack` / `HStack` / `Flex` /
  `Separator` / `GlassPanel`、`TitleBar`、`Sidebar` / `Pane` /
  `SidebarGroup`、`Tree`、`List`、`DataTable`、`Icon`。
- [DOM 与 CSS](dom-css.zh.md) — `Color`、`Styles`、`DomEvent`、原始 HTML
  元素与底层拖拽原语。
- [响应式](reactive.zh.md) — `Signal`、`Computed`、`effect` / `Effect`、
  `untrack`、`SharedSignal`、声明式绑定、`bind_value`、自动渲染。
- [平台与国际化](platform-i18n.zh.md) — 国际化、主题、运动令牌，以及
  平台原生能力（窗口控制、原生文件对话框、系统托盘）。
