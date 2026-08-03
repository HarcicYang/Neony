# Neony

A Pythonic, type-safe DOM builder and reactive UI framework for [LumiView](https://github.com/xiaosuawa/lumiview).

Build full HTML UIs without writing JavaScript — describe your DOM tree with
Pydantic models, render it to a desktop webview, and update it reactively with
automatic diff/patch.

## Quick Start

```python
from lumiview import App, Window, Bridge
from neony.dom import Body, Div, Styles, Color
from neony.dom.bridge import Neony

app = App(name="HelloNeony")
neony = Neony()


async def main():
    win = await Window.create(
        bridge=Bridge(includes=[neony]),
        title="Hello Neony!",
        width=900,
        height=640,
        devtools=True,
    )

    tree = Body(container=[Div(container=["Hello, World!"], key="greeting", styles=Styles(color=Color(name="white")))])

    await neony.render(tree)

    @neony.on("click", key="greeting")
    async def on_click(key, type, value):
        print(f"Clicked {key}!")


app.run(main)
```

## Features

- **Type-safe HTML tree builder** — every HTML tag is a Pydantic model
- **CSS-in-Python** — typed style properties with Literal constraints
- **Reactive diff/patch** — send minimal DOM updates, not full pages
- **Bidirectional events** — DOM events forwarded to Python, patches pushed to JS
- **Zero JS required** — the JavaScript engine is injected automatically

## License

GPL-3.0-or-later
