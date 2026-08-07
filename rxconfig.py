import reflex as rx

config = rx.Config(
    app_name="idatasight",
    plugins=[
        rx.plugins.RadixThemesPlugin(theme=rx.theme(appearance="light")),
    ],
    disable_plugins=[rx.plugins.SitemapPlugin],
)
