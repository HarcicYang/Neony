# 响应式

> [English version](reactive.en.md) · [API 索引](README.zh.md) · [文档首页](../README.zh.md)

从 `neony.dom` 导入。V-DOM diff 引擎响应整棵树的变更；这些原语响应
单个状态的变化。

## `Signal`

单一响应式值。用 `signal()` 读取(在 effect/computed 内读取会记录依赖)；
用 `set()` / `update()` 写入。

```python
from neony.dom import Signal

count = Signal(0)
count.get()  # 0
count()  # 同样 — 调用即读取
count.set(5)
count.update(lambda c: c + 1)  # 6 — 原地变更
```

写入相等的值(`==`)不触发通知。

## `Computed`

惰性求值、带缓存的派生值。只在依赖变化时重算；computed 可以依赖
其他 computed。

```python
from neony.dom import Computed, Signal

count = Signal(2)
double = Computed(lambda: count() * 2)
double()  # 4(缓存，直到 count 变化)
```

## `effect()` / `Effect`

立即执行 `fn`，之后每当它读过的 Signal 变化就重新执行。返回可释放的
`Effect`。

```python
from neony.dom import Signal, effect

name = Signal("Neony")
stop = effect(lambda: print(f"hello {name()}"))  # 立即打印
name.set("world")  # 重新执行
stop.dispose()  # 取消所有订阅
```

重跑是合并的:有事件循环时延迟到 `loop.call_soon`；用 `batch()` 做同步合并。

```python
from neony.dom import batch, Signal

count = Signal(0)
effect(lambda: print(count()))  # 打印 0
with batch():
    count.set(1)
    count.set(2)  # 只重跑一次，打印 2
```

## `untrack()`

执行函数但不记录依赖读取。

```python
from neony.dom import Signal, untrack

log = Signal(0)
effect(lambda: untrack(lambda: print(log())))  # 读取但永不订阅
```

## `SharedSignal`

用于跨窗口共享的 `Signal` — 一次写入更新所有绑定了它的窗口(每个窗口
各自调度自己的渲染)。

```python
from neony.dom import SharedSignal

count = SharedSignal(0)
label_a.bind_text(count)  # 窗口 A
label_b.bind_text(count)  # 窗口 B
count.set(1)  # 两个窗口都更新
```

## 声明式绑定

把 Signal 绑定到元素(或组件)上，DOM 自动跟随 — 不再需要手动刷新调用。

```python
from neony.dom import Signal

count = Signal(0)
label.bind_text(count, fmt=str)  # 文本内容
bar.bind_style(count, "opacity", fmt=lambda v: v / 100)  # CSS 属性
img.bind_attr(count, "src")  # HTML 属性
panel.bind_visible(count)  # 假值时 display: none
```

- `bind_text(signal, fmt=str)` — 用单个文本字符串替换元素的子节点
- `bind_style(signal, prop, fmt=None)` — `prop` 是 `Styles` 字段名
  (snake_case)；Signal 值为 `None` 时移除该属性
- `bind_attr(signal, name, fmt=str)` — 写入原始属性袋
- `bind_visible(signal)` — 假值时隐藏(`display: none`)，真值时恢复
  绑定前的 display 值
- `unbind()` — 释放元素上的所有绑定

五个方法在 `Component` 上同样可用(前四个代理到组件的根元素)。绑定
写入会把元素标记为 dirty 并为其窗口调度一次渲染 — 因此无论 Signal
在哪里被修改(事件处理、定时器、其他窗口)，都无需显式调用 `render()`
就能上屏。

## `Component.bind_value` — 值双向绑定

`bind_value(signal)` 把 Signal 绑定到组件的**值**上，双向同步。它适合
直接的状态同步；如果流程需要事件上下文、条件分支、异步副作用或
批量更新，不要用它替代事件处理器：

```python
name = Signal("")
inp = Input()
inp.bind_value(name)  # 输入 → name.set()；name.set() → 输入框

vol = Signal(40)
slider.bind_value(vol)  # 拖动回写(float)
bar = Progress()
bar.bind_value(vol)  # 只写跟随

flag = Signal(False)
cb = Checkbox("x")
cb.bind_value(flag)  # 绑定的是 checked 而非 value
```

- Signal 写入立即更新组件值并随变化继续更新；用户改值回写 Signal
- `Computed` 只读绑定(不回写)
- 用户通道是组件的 `_value_event`(`input`：Input/ComboBox/Slider，
  `change`：Select/Checkbox)；Progress 无用户通道，只写
- `unbind_value()` / `unbind()` 释放绑定；程序化写值不触发回调，
  循环天然闭合(用户 → Signal → 写回相同值不再分发)

复杂流程可以在绑定之外保留命名事件处理器：

```python
flag = Signal(False)
switch = Switch("同步")
switch.bind_value(flag)  # 简单状态同步


async def on_sync_change(event: DomEvent) -> None:
    await sync_remote(bool(event.value))
    status.set("已同步")


switch.on_change(on_sync_change)
```

## 脏子树追踪

每次变更都会把元素标记为 dirty 并向上传播到根。渲染时只重新序列化
dirty 元素；未变化的子树复用缓存快照(diff 引擎视其为相同，因此零补丁)。

这是自动的 — `container.append()` 和属性赋值都会参与。
