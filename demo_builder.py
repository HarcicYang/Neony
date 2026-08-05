#!/usr/bin/env python3
from lumiview import App, Window

from neony.dom import Body, Color, Div, Html, Styles

app = App(name="HelloLumiView")


async def main():
    title = "Hello LumiView!"
    await Window.create(
        title=title,
        html=Html(
            container=[
                Body(
                    container=[
                        Div(
                            container=["Hello!"],
                            styles=Styles(
                                color=Color(name="white"),
                                background_color=Color(name="black"),
                                width="100px",
                                height="100px",
                                display="flex",
                                justify_content="center",
                                align_items="center",
                                border_radius="50px",
                            ),
                        )
                    ],
                    styles=Styles(display="flex", justify_content="center", align_items="center"),
                )
            ]
        ).build(),
        width=900,
        height=640,
        devtools=True,
    )
    print(f"Page title: {title}")


app.run(main)
