# Reactivity

> [中文版本](reactive.zh.md) · [API index](README.en.md) · [Documentation home](../README.en.md)

Import from `neony.dom`. The V-DOM diff engine reacts to whole-tree
mutations; these primitives react to individual state changes.

## `Signal`

A single reactive value. Read with `signal()` (inside an effect/computed
this records a dependency); write with `set()` / `update()`.

```python
from neony.dom import Signal

count = Signal(0)
count.get()  # 0
count()  # same — call = read
count.set(5)
count.update(lambda c: c + 1)  # 6 — mutate in place
```

Writing an equal value (`==`) notifies nothing.

## `Computed`

A lazily evaluated, cached derived value. Recomputes only when a
dependency changed; computeds may depend on other computeds.

```python
from neony.dom import Computed, Signal

count = Signal(2)
double = Computed(lambda: count() * 2)
double()  # 4 (cached until count changes)
```

## `effect()` / `Effect`

Runs `fn` immediately, then re-runs it whenever any Signal it read
changes. Returns a disposable `Effect`.

```python
from neony.dom import Signal, effect

name = Signal("Neony")
stop = effect(lambda: print(f"hello {name()}"))  # prints immediately
name.set("world")  # re-runs
stop.dispose()  # unsubscribes everything
```

Re-runs are coalesced: with a running event loop they are deferred to
`loop.call_soon`; use `batch()` to coalesce synchronously.

```python
from neony.dom import batch, Signal

count = Signal(0)
effect(lambda: print(count()))  # prints 0
with batch():
    count.set(1)
    count.set(2)  # one re-run, prints 2
```

## `untrack()`

Run a function without recording dependency reads.

```python
from neony.dom import Signal, untrack

log = Signal(0)
effect(lambda: untrack(lambda: print(log())))  # reads but never subscribes
```

## `SharedSignal`

A `Signal` meant to be shared across every window — a write updates all
windows with a binding (each window schedules its own render).

```python
from neony.dom import SharedSignal

count = SharedSignal(0)
label_a.bind_text(count)  # window A
label_b.bind_text(count)  # window B
count.set(1)  # both windows update
```

## Declarative bindings

Bind a signal to an element (or component) so the DOM follows it
automatically — no manual refresh calls.

```python
from neony.dom import Signal

count = Signal(0)
label.bind_text(count, fmt=str)  # text content
bar.bind_style(count, "opacity", fmt=lambda v: v / 100)  # CSS property
img.bind_attr(count, "src")  # HTML attribute
panel.bind_visible(count)  # display: none when falsy
```

- `bind_text(signal, fmt=str)` — replaces the element's children with a
  single text string
- `bind_style(signal, prop, fmt=None)` — `prop` is a `Styles` field name
  (snake_case); a `None` signal value removes the property
- `bind_attr(signal, name, fmt=str)` — writes into the raw attribute bag
- `bind_visible(signal)` — hides (`display: none`) when falsy, restores
  the pre-binding display value when truthy
- `unbind()` — dispose every binding on the element

All five are also available on `Component` (the first four proxy to the
component's root element). A binding write marks the element dirty and
schedules a render for its window, so a signal changed from anywhere —
an event handler, a timer, another window — reaches the screen without
an explicit `render()` call.

## `Component.bind_value` — two-way value binding

`bind_value(signal)` binds a signal to a component's *value*, both
ways. Use it for direct state synchronization; it does not replace event
handlers for workflows that need event context, branching, asynchronous
side effects, or multiple state updates:

```python
name = Signal("")
inp = Input()
inp.bind_value(name)  # typing → name.set(); name.set() → field

vol = Signal(40)
slider.bind_value(vol)  # drags write back (floats)
bar = Progress()
bar.bind_value(vol)  # write-only follower

flag = Signal(False)
cb = Checkbox("x")
cb.bind_value(flag)  # binds `checked`, not `value`
```

- signal writes update the component value immediately and on change;
  user value changes write back to the signal
- `Computed` binds read-only (no write-back)
- the user channel is the component's `_value_event` (`input` on
  Input/Slider, `change` on Select/Checkbox/Switch/Dropdown); ComboBox
  binds both `input` and `change` so typing and suggestion picks are
  covered; Progress has no user channel and binds write-only
- `unbind_value()` / `unbind()` dispose the binding; programmatic value
  writes never fire callbacks, so the loop closes (user → signal →
  write-back re-applies the same value without re-dispatching)

For complex behavior, keep a named event handler alongside the binding:

```python
flag = Signal(False)
switch = Switch("Sync")
switch.bind_value(flag)  # simple state synchronization


async def on_sync_change(event: DomEvent) -> None:
    await sync_remote(bool(event.value))
    status.set("synced")


switch.on_change(on_sync_change)
```

## Dirty-subtree tracking

Every mutation marks the element dirty and propagates up to the root.
Rendering re-serializes only dirty elements; unchanged subtrees reuse
their cached snapshots (which the diff engine sees as identical, so zero
patches are emitted). This is automatic — `container.append()` and
property assignment both participate.
