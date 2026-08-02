#!/usr/bin/env python3
from lumiview import App, Window

app = App(name="HelloLumiView")


async def main():
    win = await Window.create(
        title="Hello LumiView!",
        url="https://harcic.is-a.dev",
        width=900,
        height=640,
        devtools=True,
    )
    title = await win.eval_js("document.title")
    print(f"Page title: {title}")


app.run(main)
