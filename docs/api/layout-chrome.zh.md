# 布局与窗口装饰

> [English version](layout-chrome.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

弹性容器、毛玻璃面板，以及导航 / 装饰组件——`TitleBar`、`Sidebar`、
`Tree`、`List`、`DataTable`。布局原语和装饰组件都从
`neony.application.elements` 导入。

## 弹性容器

```python
VStack(a, b, gap="12px", align="stretch")  # 纵向
HStack(a, Spacer(), b, gap="8px")  # 横向,Spacer 推挤
Flex(*items, direction="row", wrap="wrap", gap="8px")  # 完全控制
Separator()  # 分隔线（默认 type="horizontal"，也可 "vertical"）
GlassPanel(Heading("磨砂"), background=url, grow=True)  # 磨砂舞台
```

- `VStack` / `HStack` / `Flex` 接受 `grow` 撑满剩余空间。
- `GlassPanel`: 半透明表面 + 背景模糊;`background=url` 在面板内绘制图片;
  `grow=True` 撑满父区域;`radius` 覆盖默认 12px 圆角;`width` / `height`
  把面板固定为确定尺寸（配合默认非 `grow` 模式）。

## 网格容器

```python
from neony.dom import Columns  # CSS 值类型在 neony.dom 里

GridView(cards, columns=Columns.responsive(120))  # 随窗口重排的卡片墙
GridView(cards, columns=Columns.fixed(3), gap="12px")
GridView(cards, uniform=False)  # 卡片保持自身高度
```

- `columns` 决定列布局：`Columns.fixed(n)` 均分 `n` 列；
  `Columns.responsive(min_width)` 按容器宽度自动排列（加 `fit=True`
  让内容较少的行拉伸铺满）；`Columns(tracks=...)` 显式指定列宽。
  完整 `Columns` 用法见 [DOM 与 CSS](dom-css.zh.md)。
- `uniform=True`（默认）让同行内所有卡片等高于最高的那块——图片网格
  整齐划一；`uniform=False` 保持各自内容高度，顶部对齐。
- 长标签在卡片内自动换行而不会撑破布局，窗口缩放时行列自动重排，
  无需额外样式。

## `TitleBar`

无边框窗口的自定义标题栏。需 `WindowConfig(decorations=False)`。

```python
titlebar = TitleBar("My App")  # 零配置,拖动/最小化/最大化/关闭
titlebar.on_close(lambda e: print("bye"))  # 附加回调
titlebar.override_close(confirm_close)  # 完全接管关闭
titlebar.leading_slot.container.append(custom_element)
```

**参数：** `title`、`icon`、`show_minimize`、`show_maximize`、
`icon_size`、`icon_styles`、`leading`、`trailing`、`show_minimize`、
`show_maximize`、`show_close`、`height`

`icon` 为 `Icon` 对象——`Icon.image(url_or_path)` 在标题左侧绘制一个小图标（固定尺寸方形，绝不拉伸）——无边框模式下
`WindowConfig.icon` 的对应物，因为无边框窗口没有 OS 装饰来承载它。

标题栏即拖拽区域（双击最大化）；控制按钮自动接线到窗口。
`leading_slot` / `trailing_slot` 是只读插槽：前者包含图标、前置内容与
标题，后者包含后置内容和窗口控制按钮。

## `Sidebar` & `SidebarItem`

垂直导航，与 `TitleBar` 同款玻璃。Sidebar 可以拥有内容面板——传入 `Pane` 子项时，点击条目（或按快捷键）切换可见面板。

```python
sidebar = Sidebar(
    Pane("首页", panel=home_panel, icon=Icon.glyph("🏠"), section="常用", shortcut="Ctrl+1"),
    Pane("设置", panel=settings_panel, icon=Icon.glyph("⚙️"), section="常用"),
    Pane("统计", panel=stats_panel, icon=Icon.glyph("📊"), section="数据", shortcut="Ctrl+3"),
)
sidebar.on_change(lambda e: print(e.value))  # value = 面板 key
sidebar.selected_key = "settings"  # 编程切换,不触发回调
sidebar.selected  # 当前选中的 Pane（或 SidebarItem）对象
for combo, fn in sidebar.shortcuts():
    page.on_shortcut(combo, fn)  # 接线面板的快捷键
```

裸 rail 模式——只有 `SidebarItem` 子项，内容切换仍由用户负责：

```python
sidebar = Sidebar(
    SidebarItem("首页", icon=Icon.glyph("🏠")),
    SidebarItem("设置", icon=Icon.glyph("⚙️")),
    active_key="home",  # 已弃用 → selected_key
)
```

**参数:** `Sidebar(*children, width, glass, corner_radius, edge_fade=True)`，
`SidebarItem(label, key, icon, active)` — `*children` 为
`SidebarItem` / `SidebarGroup` / `Pane` / `(label, panel)` 元组。

`edge_fade` 切换轨道上的滚动指示器——设 `False` 关闭。玻璃侧边栏仍显示滑块，但跳过边缘渐变（WebKitGTK 中 mask-image 与背景模糊冲突）。

`Pane.key` 默认为随机 id——标签永不冲突，即使重复或非 ASCII；想要可读标识符时显式传 `key`。`shortcut` 与 `Page.on_shortcut` 同格式；快捷键切换如同点击一样触发 `change`。`selected_key` 对未知 key 抛 `ValueError`；设为 `None` 清空选择。点击条目任意位置（包括图标与文字）都生效——条目级事件会从其子元素冒泡上来。

### `Pane`

一个可选的 `Sidebar` 条目及其内容面板。

```python
pane = Pane("首页", panel=home_panel, icon=Icon.glyph("🏠"), section="常用", shortcut="Ctrl+1")
```

**参数:** `Pane(label, panel, key, icon, section, shortcut)` —
`label` 为条目文字（第一个位置参数）；`panel` 为激活时显示的组件（或元素），注册时构建一次（一个面板组件不能挂到两个 sidebar）；`key` 默认为随机 id；`section` 把连续同节的 pane 归入一个小号大写侧边栏标签下；`shortcut` 为窗口级组合键（`"Ctrl+1"` 或平台 dict 如 `{"darwin": "Meta+2", "default": "Ctrl+2"}`）。

### `SidebarGroup`

`Sidebar` 的分组小节——条目上方的小号大写标签。

```python
sidebar.add(SidebarGroup("菜单", SidebarItem("打开"), SidebarItem("保存")))
```

`SidebarGroup.add` 可链式调用，且组挂到 sidebar 之后仍可用（新增条目自动接线）。组纯属视觉：选择、`items` 与 `change` 都按 DOM 顺序作用于扁平的条目列表。连续共享同一 `section` 的 pane 渲染为一个组；同名 section 稍后重现则另起一组。

## `Tree` & `TreeNode`

可折叠导航树（左侧轨道）拥有内容宿主（右侧）。任意深度：分支节点（带 `children`）只展开/收起；叶子节点（带 `panel`）选中后在宿主显示其内容。树是单选——`selected_key` / `bind_selected` 与 `Sidebar` 行为一致。

```python
tree = Tree(
    TreeNode("首页", key="home", icon=Icon.glyph("🏠")).panel(home_panel),
    TreeNode("表单", expanded=True).children(
        TreeNode("输入", key="inputs", shortcut="Ctrl+1").panel(inputs_panel),
        TreeNode("勾选", key="checks").panel(checks_panel),
    ),
    active_key="home",  # 或 tree.selected_key = "home"
)
tree.on_change(lambda e: print(e.value))  # value = 叶子 key
for combo, fn in tree.shortcuts():
    page.on_shortcut(combo, fn)  # 叶子快捷键，同 Sidebar
```

**参数:** `Tree(*nodes, width, expanded_branches, active_key, edge_fade=True)` — `width` 为轨道宽度（宿主自适应其余空间）；`expanded_branches=True` 让顶层分支默认展开。`edge_fade` 切换轨道上的滚动指示器——设 `False` 关闭。行样式复用 `Accordion` 表头——圆角、透明、无外围包裹；轨道高度受舞台约束，在舞台内滚动而非撑破页面。

`TreeNode(label, key, icon, panel, expanded, children, shortcut)` — 节点不能同时带 `panel` 与 `children`（否则抛错）。流畅建造器：`.panel(panel)` 挂叶子内容、`.children(*nodes)` 挂分支子节点、`.key_(key)` 设 key——全部可链式。

`key` 默认为随机 id；`selected_key` 对未知 key 抛 `ValueError`。分支带 `aria-expanded`、叶子带 `aria-selected`；行支持键盘导航（方向键移动焦点环，Enter / 空格激活，← / → 收起 / 展开分支）。

## `List` & `ListItem`

可滚动单选数据列表（listbox 模型）。同时只有一个条目被选中；`selected_key` / `bind_selected` / `on_change` 与 `Sidebar` 行为一致。

```python
fruits = List(
    "Apple",
    "Banana",
    ListItem("Cherry", key="cherry", icon=Icon.glyph("🍒")),
    active_key="Apple",
)
fruits.on_change(lambda e: print(e.value))  # value = 选中 key
fruits.selected_key = "cherry"  # 编程式写入，不触发回调
fruits.children("Durian", "Elderberry")  # 链式追加
fruits.bind_selected(signal)  # 双向响应式选中
```

**参数:** `List(*items, active_key=None, edge_fade=True)` — `items` 为字符串或 `ListItem(label, key=None, icon=None)`。字符串条目的 key 即其标签；标签冲突时须显式传 `key`（重复 key 抛错）。行是 `role="option"`，容器 `role="listbox"`；键盘：↑/↓ 移动选中（端点钳制，每次移动触发 `change`）、Home/End 跳到首尾、Enter/空格选中、点击选中。方向键导航时出现强调色焦点环，点击后清除。`edge_fade` 切换滚动指示器。

须挂在**确定高度**的 flex 父级（如 `VStack(..., grow=1)` 或 `GlassPanel(grow=True)`）；列表在父级内滚动行，而不是撑破页面。

## `DataTable` & `Column`

表格数据视图——列配置 + 行 dict 列表，带固定表头、点击排序与行选中（默认单选，构造时可选多选）。

```python
people = DataTable(
    columns=[
        Column("Name", key="name", sortable=True, width="2fr"),
        Column("Age", key="age", sortable=True, align="right", width="80px"),
        Column("Score", key="score", align="right", format=lambda v: f"{v}%"),
    ],
    rows=[
        {"name": "Ada", "age": 38, "score": 92},
        {"name": "Bob", "age": 24, "score": 77},
    ],
    row_key=lambda r: r["name"],  # 默认：行索引
    active_key="Ada",
)
people.on_change(lambda e: print(e.value))  # 选中行 key
people.sort_by = ("age", "desc")  # 表头点击同样排序
people.bind_selected(signal)  # 双向响应式选中
```

列与行也可链式追加：`DataTable().column("Name").row({"name": "Ada"})`。

**参数:** `DataTable(columns=None, rows=None, *, row_key=None, selection="single", active_key=None, selected_keys=None, edge_fade=True)`。

`Column(title, key=None, width=None, sortable=False, align=None, format=None, sort_key=None)` — `key` 默认为小写标题；`width` 为 CSS 网格轨道（`"1fr"` / `"80px"`）；`align` 为 `left|center|right`；`format` 把单元格值映射为文本；`sort_key` 从行中提取自定义排序值。

`row_key` 派生每行的身份（默认行索引）且必须唯一。`sortable=True` 的表头点击排序（asc → desc，换列从 asc 开始）；排序数字感知（或用 `sort_key`），保留选中，可通过 `sort_by` 观察。表头在滚动容器内 `position: sticky`，横向滚动时表头与行保持对齐。

**选中。** `selection="single"`（默认）暴露 `selected_key`（编程式写入不触发回调）；`selection="multi"` 暴露 `selected_keys`（接受 `set`/`frozenset`/`list`/`None`），点击切换成员——`change` 携带被切换的 key，全量状态读 `selected_keys`。`bind_selected` 仅单选用（否则抛错）；错配模式的属性抛 `NotImplementedError`。

键盘：单选模式下方向键移动选中（触发 `change`）；多选模式下方向键移动焦点环、空格切换。Home/End 跳首尾；Enter/空格选中或切换。

须挂在**确定高度**的 flex 父级；表格在父级内双轴滚动。`edge_fade` 切换滚动指示器。

## `Icon`

内置 UI 图标经 `icons` 命名空间暴露；图标目录实现类保持私有，不属于公开 API：

```python
from neony.application import icons
from neony.application.elements import Button

Button("保存", icon=icons.check)
SidebarItem("首页", icon=icons.home)
```

内置目录只使用一套随包分发的 Material Symbols Rounded 字体。图标继承组件的 `color` 主题令牌，采用固定方形几何，并统一 weight/fill/grade/optical-size 设置。

`Icon.image(url_or_path)` 用于 Logo 与原生图片资源，`Icon.glyph(text)` 用于明确的自定义文本或 emoji 内容。两者都会返回 `Icon`，可传给各组件的 `icon` 参数，包括 `Button.icon: Icon | None`。
