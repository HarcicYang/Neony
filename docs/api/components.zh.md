# 组件

> [English version](components.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

所有组件继承 `Component` — 链式 `on_*` 方法、状态属性、源感知事件。

从 `neony.application.elements` 导入。

## 表单控件

### `Button`

```python
Button("Primary")  # 强调背景
Button("Ghost", variant="ghost")  # 描边表面
Button("Delete", variant="danger")  # 危险色
Button("Glass", glass=True)  # 磨砂变体
Button("Ok", disabled=True)  # 置灰
button.on_click(handler)  # 点击事件
```

### `Checkbox`

```python
cb = Checkbox("Pizza")
cb.checked = True  # 编程设置 — 不触发回调
cb.on_change(lambda e: print(e.value))  # value = 是否勾选
```

### `Input`

```python
inp = Input(placeholder="你的名字…", type="text")  # text | password | email | number …
inp.on_input(lambda e: print(e.value))  # 实时值
```

### `Radio` & `RadioGroup`

```python
group = RadioGroup(Radio("披萨"), Radio("塔可"))
group.value  # 选中的值（默认小写 label）
group.on_change(lambda e: print(e.value))  # value = 选中的值字符串
group.value = "tacos"  # 编程设置 — 不触发回调
```

同一时刻只有一个选项被选中；组会给选项分配共享 `name`，屏幕阅读器
将其视为一个控件。单独使用的 `Radio` 是普通开关，`on_change` 携带
布尔值。

### `Switch`

```python
sw = Switch("Wi-Fi")
sw.bind_value(flag)  # 双向绑定 checked
sw.checked = True  # 编程设置 — 不触发回调
sw.on_change(lambda e: print(e.value))  # value = 是否开启
```

开关只需要同步状态时使用 `bind_value`；如果变更还要执行异步操作、
条件分支或更新多个状态，保留命名的事件处理器：

```python
async def on_wifi_change(event: DomEvent) -> None:
    await persist_setting(bool(event.value))
    status.set("已保存")


sw.on_change(on_wifi_change)
```

原生 checkbox 样式化为轨道 + 滑块（38×22px，`glass=True` 磨砂轨道）。

### `Select`

```python
sel = Select("尺寸", options=[("s", "小"), ("m", "中")], placeholder="请选择…")
sel.value  # 选中的选项值（"m"）
sel.on_change(lambda e: print(e.value))  # value = 选中的选项值
```

选项为 `str`（值即标签）或 `(value, label)` 元组。弹出列表由组件自绘
——主题化玻璃面板——因为 WebKitGTK 的原生弹出层忽略 option 的
`background-color`。键盘：Enter/Space 打开，方向键高亮，Enter 选中，
Escape/Tab 关闭；点击外部经引擎的 `outsideclick` 事件关闭。

### `ComboBox`

```python
box = ComboBox("标签", options=["work", "personal"], placeholder="输入或选择…")
tag = Signal("")
box.bind_value(tag)  # 输入与建议选择都会写回 tag
```

简单回显使用绑定即可；校验、持久化或其他异步操作则使用事件回调
（也可以与绑定同时使用）：

```python
async def on_tag_change(event: DomEvent) -> None:
    await save_tag(event.value)
    audit_log.append(event.value)


box.on_change(on_tag_change)  # event.value 是提交后的文本
```

可编辑文本框 + 主题化建议面板（原生 `<datalist>` 弹出层无法主题化）。

聚焦即弹出全部选项（单击即可见）；建议按输入前缀实时过滤；方向键
高亮、**Tab 或 Enter 自动补全**高亮建议、**PageUp/PageDown 一键选中
首/尾建议**、Escape / 点击外部关闭。值语义与 `Input` 一致：
`on_input` 只记录状态，`on_change` 在选中建议或失焦时触发。

### `Slider`

```python
sl = Slider("音量", min=0, max=100, step=5, value=40)
sl = Slider("音量", min=0, max=100, step="any")  # 无级
sl.value  # 40.0 — 已限制在 [min, max]
sl.on_input(lambda e: print(e.value))  # float，拖动中持续触发
sl.on_change(lambda e: print(e.value))  # float，松开时触发
```

轨道、accent 填充和滑块由组件自绘（顶层的原生 range 输入不可见，
负责拖动与键盘）。拖动时填充实时跟随滑块，程序化设置时 0.2s 平滑
过渡。`step="any"` 可达任意浮点值。PageUp/PageDown 按页步进（10×
step，无级时为范围 10%）——组件纠正了原生 range 反向的页方向
（WebKit 规范怪癖）。

### `Progress`

```python
bar = Progress("下载中…", value=35, max=100)
bar.value = 50  # 限制在 [0, max]；填充 0.3s 平滑过渡
Progress("扫描中…", indeterminate=True)  # 滑动扫掠动画
```

圆角轨道 + accent 填充，值变化时宽度过渡
（`indeterminate=True` 播放内置 `neony-indeterminate` 扫掠动画）。

条上携带 ARIA `role="progressbar"` + `aria-valuenow/min/max`。

## 文本与标签页

### `Heading` & `Text`

```python
Heading("标题", level=1)  # h1–h6
Text("正文")  # 主文字
Text("次要", role="secondary")  # 次要文字
Text("错误", role="danger")  # 危险文字
Text("成功", role="success")  # 成功文字
```

### `Tabs`

```python
tabs = Tabs(("一", panel_one), ("二", panel_two))  # 或 tabs.add("一", panel_one)
tabs.selected_panel = panel_two  # 编程切换(组件或元素)
tabs.selected_title  # 当前激活标签的标题
tabs.selected_key = "二"  # 以标题作为 key 编程选择
tabs.bind_selected(active)  # Signal[str] ↔ 当前标签
tabs.on_change(lambda e: print(e.value))  # value = 标签标题
```

**参数:** `Tabs(*panes, glass, edge_fade=True)` — `*panes` 为 `(标题, 面板)` 对，等价于链式 `add()`。

`edge_fade` 切换标签条上的滚动指示器（浮动滑块 + 动态边缘渐变）——设 `False` 关闭。

`selected_panel` 按身份绑定可见面板（组件或其已构建的根元素，绝不重复构建）；`selected_title` 按标题字符串选择，未知标题抛 `ValueError`。`active`（下标）与 `active_key` 为已弃用别名 —— `active_key` 现在返回标签标题（此前返回不透明的元素 id）。

### `Accordion` & `Collapsible`

```python
accordion = (
    Accordion(multiple=True)
    .section("输入与表单", inputs_panel, checks_panel)
    .section("布局", layout_panel, expanded=True)
)
accordion.on_change(lambda e: print(e.value))  # value = 被切换分组的 key
accordion.expanded_keys = ["输入与表单"]  # 编程展开 —— 不触发回调
accordion.expanded_keys  # list[str]，当前展开的分组
```

`Collapsible` 是一个带标题、可在隐藏/可见之间切换的内容面板；`Accordion` 把若干折叠项堆叠在同一个滚动流里。`multiple=True`（默认）允许同时展开多个分组；`multiple=False` 为互斥模式——展开一个会收起其余的。切换仅改 `display`——展开时重放内置的 `neony-rise-in` 入场动画，因此不涉及 JS 层。

`Collapsible(title, *content, expanded=False, key=None)` 构造单个折叠项（也可作为位置参数直接传给 `Accordion`）；`key` 默认取标题的小写形式，用于 `change` 事件载荷。`.section(title, *content, ...)` 是流畅写法，一步构建并挂载一个 `Collapsible`。

用 `on_change` 监听（`event.value` 为刚被用户切换的分组 key），用 `expanded_keys` 读取完整的展开集合。`Accordion` **不**实现 `selected_key` / `bind_selected`——其选择是多值的，不适用单值选择协议。

## 浮层与反馈

### `Dialog`

```python
dlg = Dialog(
    title="确认",
    content=Text("..."),
    width="380px",
    actions=[
        DialogAction("确认", on_click=confirm_handler),  # 执行后关闭
        DialogAction("取消", variant="ghost"),
        DialogAction("关闭", close_on_click=False),  # 执行后保持打开
    ],
)
dlg.open = True  # 或读取该属性
dlg.on_close(lambda d: print("closed"))  # 回调接收对话框自身
```

固定全屏 scrim 层（`--color-bg-overlay`，跟随主题）+ 居中面板。

关闭途径：scrim 点击、Escape（焦点在对话框内时）、点击外部
（`outsideclick`）。`closable=False` 仅禁用 scrim。`actions` 渲染为
底部一排主题按钮 —— `DialogAction` 接受标签（位置参数）、
`variant`（`primary`/`ghost`/`danger`）、`on_click` 回调（收对话框
自身，同步或异步）与 `close_on_click`（默认 True）。注意：任何
`backdrop-filter` / `transform` 祖先会成为 `position: fixed` 的
containing block —— Dialog 应挂页面根或非过滤容器。

### `PromptDialog`

```python
ask = PromptDialog(
    "你的名字是？",  # 输入框上方的提示
    title="识别",
    value="Ada",  # 预填；也可通过 ask.value 重置
    placeholder="输入…",
)
ask.open = True  # 或读取该属性
ask.on_submit(lambda v: print(f"got {v}"))  # 确认 / 回车，携带输入值
ask.on_close(lambda d: print("closed"))  # 继承自 Dialog
```

专门用于单行文本输入的 `Dialog`：主题化 scrim + 居中面板，内含一条
消息、一个 `Input` 输入框与确认 / 取消按钮行。确认（主按钮，或输入框
聚焦时按 `Enter`）触发 `on_submit` 并携带输入框当前值，然后关闭；
取消（ghost 按钮、`Escape`、scrim 点击或点击外部）只关闭、不触发。

`value` 是输入框文字 —— 打开前设置可预填，提交后读取。`prompt`、
`confirm_label`、`cancel_label`、`placeholder` 均可配置。与 `Dialog`
相同的 `position: fixed` 注意点 —— 挂页面根。

### `Tooltip`

```python
tip = Tooltip("提示", anchor=Button("悬停"), placement="top", delay=0.4)
```

包装 anchor（组件在构造时 build；字符串包进 Span），悬停 `delay`
秒后显示气泡，按 `placement`（`top` / `bottom` / `left` / `right`）
锚定 —— 纯 CSS 偏移，零测量。wrapper 会冒泡 anchor 的悬停事件；
点击 anchor（聚焦）立即显示气泡，失焦隐藏。

### `Dropdown`

```python
dd = Dropdown("主题", items=[("dark", "深色"), ("light", "浅色")])
choice = Signal("")
dd.bind_value(choice)  # 双向绑定：选择结果写入 choice
dd.value  # 选中的值
```

如果选择还要触发异步加载或多个相关状态更新，使用命名的
`on_change` 处理器：

```python
async def on_theme_change(event: DomEvent) -> None:
    await reload_theme(event.value)
    status.set(f"已加载：{event.value}")


dd.on_change(on_theme_change)
```

trigger + 主题化玻璃弹出面板（原生 button 行，与 `Select` 同模式）。

完整键盘导航（Enter/Space 打开、方向键两端钳制、PageUp/PageDown
首尾、Enter 选中、Escape/Tab 与点击外部关闭）。`items` 可设置。

### `Menu`

```python
menu = Menu(("rename", "重命名"), ("delete", "删除"))
btn.on_contextmenu(lambda e: menu.open_at(e.x, e.y))  # 光标位置
menu.on_change(lambda e: print(e.value))
```

`open_at(x, y)` 定位的 fixed 弹出面板 —— 通常用 `contextmenu` 事件的
视口坐标，无需测量。键盘导航与 `Dropdown` 相同；选中、Escape 或
点击外部关闭。面板**向上弹出**——底边锚在光标上方 8px——并通过
`calc()` 的 max-width/height 钳制在视口内，靠近屏幕边缘也不会溢出。

### `Toast`

```python
toast = Toast(placement="top-right", duration=3.0, top_offset="40px")
page.add(toast)  # 挂载一次到页根
toast.show("File saved", type="success")  # success / info / error
toast.show("Update available", type="info", duration=5.0)
toast.show("New message", on_click=open_it)  # 点击卡片（✕ 不触发）
toast.placement = "bottom-left"  # 运行时移动堆叠方位
toast.clear()  # 全部移除
```

宿主组件，把瞬时通知堆叠在六个屏幕方位之一（`top-left` /
`top-center` / `top-right` / `bottom-left` / `bottom-center` /
`bottom-right`）。`show(text, type=...)` 推入一张卡片 ——
`success` / `info` / `error` 决定左侧类型圆点颜色；`duration` 按次
覆盖宿主默认值，`0` 表示一直停留（点 ✕ 关闭）。`on_click`（同步或
异步）在点击卡片时触发——✕ 永不触发它——可点击的卡片会显示指针
光标。`max_toasts` 超限时驱逐最旧卡片。`top_offset` 让 top 组从窗口
顶部往下偏移——留出 `TitleBar` 的高度；bottom 组始终贴窗边。每张
卡片的**入场动画与方位方向绑定**（top 组从上方落下、bottom 组从
下方升起、角位对角滑入），出场反向重放同一 keyframe 滑向该方位
角/边。宿主是 `position: fixed` 全视口层，z-index 1100、
`pointer-events: none`（点击穿透到页面）——挂载在页根，避开
`backdrop-filter` / `transform` 祖先。

## 内容

### `Image`

```python
from neony.application.urls import file_url, data_url

img = Image(file_url("cover.png"), width=120, height=120, fit="cover", radius="12px")
img.src = data_url("other.svg")  # 任意 URL 字符串
```

包裹单个 `<img>` 的主题化框架。`src` 是**已拼好的 URL**——本地文件传
`file_url(path)`，经内置 `neony://local` 协议流式加载传 `local_url(path)`
（`file://` 被拦截时可用），嵌入字节传 `data_url(path)`，或任意 `https://` URL；
组件自身不做任何路径转换（这个边界交给调用方）。圆角、overflow-hidden
的框架包裹图片，让 `object-fit` 能裁切到圆角，字节到达前显示占位色。

`width`/`height` 接受 `str`（`"40%"`）或 `int`（→ `"40px"`）。`fit` 即
`object-fit`（`cover`/`contain`/`fill`/`none`/`scale-down`）；传
`radius="50%"` 得到圆形。`src` 与 `alt` 构造后可改。

### `Avatar`

```python
av = Avatar("https://…/me.png", name="Ada Lovelace", size="56px")
letter = Avatar(name="Ada", size="40px")  # → 强调色圆盘上的 "A"
unknown = Avatar()  # → "?" 占位
inbox = Avatar(src, name="收件箱", badge=Badge(3, position="top-right"))
```

用户头像——图片、字母或占位。有 `src` 显示图片（`object-fit: cover`
裁切）；只有 `name` 时回退到首字符（大写）显示在强调色圆盘上；都没有
则显示 `?` 占位。`shape` 为 `circle`（默认）或 `square`；`radius` 覆写
形状的圆角。`alt` 覆写图片 alt 文字（否则用 `name`）。可选的 `badge`
（一个角标 `Badge`）叠加其上——Avatar 会把自己包进 relative inline-flex
容器，让角标能锚到某个角。`src`、`name`、`size` 构造后可改。

### `Badge`

```python
Badge("New", variant="accent")  # 内联标签
Badge(150)  # → "99+"（默认 max=99）
Badge(0)  # 隐藏（display:none）；Badge(0, show_zero=True) 显示
Badge(dot=True)  # 状态点，无文字
Badge(3, position="top-right")  # 角标计数——需要 position:relative 的父容器
```

小型状态标签或角标计数——一个类两种形态。`position="inline"`（默认）是
随文档流的标签，按 `variant` 染色（默认 `neutral`，可选 `accent`、
`danger`、`success`）。其他 `position`（`top-right`、`top-left`、
`bottom-right`、`bottom-left`）把标签绝对定位成角标——**组件假定父容器是
`position: relative`**（带 `badge=` 的 `Avatar`，或一个 wrapper `Div`）；
`overlap=True` 把它推得更远（`-12px`）以覆盖父元素边缘。整数内容有两点
便利：超过 `max`（默认 99）的计数折叠成 `"99+"`；零计数默认隐藏，除非
`show_zero=True`（节点保留，便于切回显）。`dot=True` 去掉文字，只留状态
点。`content`、`variant`、`dot` 构造后可改。

### `Card`

```python
card = Card(
    Text("正文里放任意子元素。"),
    title="我的卡片",
    subtitle="可选副标题",
    actions=[Button("编辑")],
    footer=[Button("取消"), Button("确定")],
    glass=True,
    role="accent",
)
card.title = "已重命名"
```

带标题的内容卡片。`*body` 是卡片正文（组件、DOM 元素或字符串）。

`title` / `subtitle` 自动生成 header（一个 `Heading` + 可选的次要 `Text`）；
自定义的 `header=` 会完全替换标题行（且优先级高于 `title`/`subtitle`/
`actions`）。`actions` 是 header 行右侧右对齐的按钮；`footer` 是按钮列表
（右对齐、分隔线之上）或任意内容节点。`glass=True` 把实色表面换成按
`role` 着色的毛玻璃面板（默认 `neutral`，可选 `accent`、`danger`、
`success`——辉光跟随主题）。`clickable=True` 让整张卡片可点击
（`cursor: pointer` + `on_click`）。`title` 与 `subtitle` 构造后可改。

Card 保留自己紧凑的样式常量（不包裹 `GlassPanel`），默认就很轻。

### `MessageBubble`

```python
other = MessageBubble(
    "Hey! Have you seen the new gallery?",
    avatar=Avatar(name="Ada"),
    name="Ada",
    actions=[("reply", "Reply"), Icon.glyph("😊")],
)
me = MessageBubble("Hi!", from_me=True)
other.on_change(lambda e: print(e.value))  # 右键菜单选择
other.on_action(lambda v: print(v))  # 快捷操作点击
```

单条聊天消息，QQ/Telegram 风格。`from_me` 切换行对齐（自己 → 右侧，
他人 → 左侧）与气泡填充色（自己 → accent 白字，他人 → 抬升面）；
朝向头像一侧的圆角做方角处理。`avatar` 是可选的 `Avatar`，放在消息
自身一侧（构造时 build 一次）；`name` 是气泡上方的可选发送者名。

`actions` 在气泡下方渲染 hover 时出现的快捷按钮——`(value, label)`
或 `str` 变成文本按钮，`Icon` 变成图标按钮；点击触发
`on_action(value)`。快捷操作行**绝对定位**在气泡正下方，出现时覆盖
下一条消息，不会撑高组件体积；同一窗口内只有当前悬停消息会显示快捷
操作行。`menu_items` 配置内置右键 `Menu`（默认复制/删除；`[]` 关闭菜单
但 `on_contextmenu` 仍触发），选择通过 `on_change` 派发（携带 value）；
同一窗口内打开该光标菜单会关闭此前打开的光标菜单。注意：菜单是气泡内
的 `position: fixed` 元素；聊天容器请避开 `backdrop-filter` /
`transform` 祖先。

### `NoticeBubble`

```python
NoticeBubble("You joined the group")
```

居中的系统消息——在 flex 列消息列表里 `align-self: center` 居中，
半透明底的淡色药丸。`text` 是消息文本，或传 `content` 放自定义元素；
`text` 构造后可改。

## 富文本与滚动

### `RichText`

```python
from neony.application.elements import ImageSegment, RichText, TextSegment

editor = RichText(segments=["你好", ImageSegment(src="x.png"), "世界"])
editor.insert_image("y.png", at_caret=True)  # 插入到光标处
editor.on_change(lambda e: print(e.value))  # 有序分段
editor.on_submit(lambda e: send())  # Enter（IME 安全）
segments = editor.content()  # [TextSegment, ImageSegment, ...]
```

行内 `contenteditable` 编辑器。文字与图片分段共存于实时 DOM；Python
diff 冻结这个受管子树的差异更新，因此输入、输入法组合与光标都能在
Neony 渲染中保持稳定。扁平位置按一个文字字符记 1、一张行内图片记 1。

- `content() -> list[TextSegment | ImageSegment]` — 有序内容。
- `set_content(segments)` — 编程式替换。
- `insert_text(text, *, at_caret=True)` / `insert_image(src, *, at_caret=True, alt="", width=None, height=None)`。图片默认显示为 `40×40px`；自定义尺寸的显示上限为 `320×240px`，宽度同时不超过编辑器容器。
- `caret_position()` / `selection_range()` / `set_caret(position)` / `focus()`。
- 粘贴图片时，RichText 会读取系统剪贴板中的图片字节，并替换浏览器自动插入的 `blob:` 图片；无需额外配置即可保留图片数据并应用图片尺寸限制。
- 事件：`on_change`（`event.value` 为分段列表）、`on_submit`
  （Enter；默认换行被拦截）、`on_input`、`on_click`、
  `on_paste_files`（原始合成粘贴事件）、`on_paste_image`
  （`event.value` 为临时文件路径列表）。

### `ScrollArea`

```python
area = ScrollArea(message_list)
await area.scroll_to_bottom()
await area.scroll_to_top()
await area.scroll_to(120, behavior="smooth")
```

可滚动的垂直区域。所有 DOM 滚动都通过内部 `window.neony` 命令完成——
用户代码无需编写 JavaScript。挂载契约：必须挂在确定高度的 flex 父级
（组件使用 `flex_grow + flex_basis:0 + min_height:0`）。

### `StickToBottom`

```python
stick = StickToBottom(message_list)
await stick.scroll_to_bottom(force=True)
```

聊天流滚动容器。用户接近底部时自动贴底；向上滚动暂停贴底，回到接近
底部时恢复。该行为由内部 JS 引擎负责（`data-neony-autostick`）；
`scroll_to_bottom(force=True)` 忽略当前贴底状态强制滚到底部。
挂载契约与 `ScrollArea` 相同。


## 拖拽与重排

### `Reorder` 组件

重排集合的现成方式是 `Reorder` 面板——一个由可拖拽卡片组成的 flex
容器，重排逻辑内聚在组件内部：

```python
from neony.application.elements import Reorder, ReorderItem

board = Reorder(
    ReorderItem("First", key="a"),
    ReorderItem("Second", key="b"),
    "Third",  # 纯字符串也会变成卡片（key = 标签）
    direction="row",  # "row" 或 "column"
    wrap=True,  # row + wrap = 网格（横纵都行）
    size="76px",  # 沿主轴方向的卡片尺寸
    max_width="336px",  # 可选——固定每行 4 张卡片以强制换行
)
board.on_drop(lambda e: e.value)  # 拖拽后的有序 key
board.order  # 当前按渲染顺序的 key
```

- 卡片预置为可拖拽（载荷提前声明——dragstart 里 Python 往返来不及），
  `drop` 由组件自身重排；diff 引擎自动发出 `ReorderPatch`。
- **纵横双向都支持**：引擎自动检测容器的 `flex-direction`，按光标所在
  半区判定插入侧——`row` 用 `offset_x`（前半插其前、后半插其后）、
  `column` 用 `offset_y`。`row` + wrap 会形成网格，卡片既能横向拖（行内）
  也能纵向拖（跨行）。网格在面板宽度处换行——用 `max_width` 固定宽度即可
  强制换行。
- **卡片不限于文本**：`add()` / 构造器接受任意内容——纯文本或响应式字符串、
  整个 `Component`（挂载在卡片内部），或裸 `DOMElement`。**裸内容不需要
  包装也不需要显式 key**：纯字符串用标签当 key、带 key 的 DOM 元素保留
  自己的 key，其余一切（一摞 `Card` 等）自动获得 `reorder-card-N` key。
- **按卡片内容泛型化**——`Reorder[T]` 与 `ReorderItem[T]` 以卡片内容为类型
  参数，因此任意组件（或任何内容类型）可以直接站在原本 `ReorderItem` 的
  位置上，`items` 产出 `ReorderItem[T]`：

  ```python
  from neony.application.elements import Card, Text

  board: Reorder[Card] = Reorder(Card(title="One"), Card(title="Two"))
  cards = board.items  # list[ReorderItem[Card]]——content 类型为 Card
  ```
- **面板之间可以交换卡片**：把卡片拖到另一个 `Reorder` 的卡片上，落点槽
  会移动到那个面板，drop 会把卡片移过去（从源面板的 `order` 移除并插入
  目标面板）。允许交换的面板之间，卡片 key 必须全局唯一。
- `on_drop` 触发时 `event.value` = 接收 drop 的面板重排后的卡片 key 列表。

底层拖拽原语（`drag_payload`、`dataTransfer`）见
[DOM 与 CSS → 拖拽与重排](dom-css.zh.md#拖拽与重排)。
