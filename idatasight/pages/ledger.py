"""Page 4 · Ledger — the one-chart page (wireframe 2d)."""

import reflex as rx

from ..components.shell import rail, shell
from ..components.ui import kicker, note, tile
from ..state import AppState
from ..theme import Border, Color, Font, Space


def cost_chart() -> rx.Component:
    return rx.el.div(
        rx.recharts.line_chart(
            rx.recharts.line(
                data_key="without memory",
                stroke=Color.neutral_500,
                stroke_width=2,
                stroke_dasharray="5 3",
                type_="linear",
                dot=False,
                is_animation_active=False,
            ),
            rx.recharts.line(
                data_key="with memory",
                stroke=Color.accent,
                stroke_width=2.5,
                type_="linear",
                dot=False,
                is_animation_active=False,
            ),
            rx.recharts.x_axis(
                data_key="episode",
                tick_line=False,
                stroke=Color.text,
                custom_attrs={"fontSize": "11px", "fontFamily": Font.body},
            ),
            rx.recharts.y_axis(
                tick_line=False,
                stroke=Color.text,
                custom_attrs={"fontSize": "11px", "fontFamily": Font.body},
            ),
            rx.recharts.legend(icon_type="plainline"),
            rx.recharts.graphing_tooltip(),
            data=AppState.ledger_points,
            width="100%",
            height=260,
            margin={"top": 16, "right": 24, "left": 0, "bottom": 4},
        ),
        border=Border.frame,
        background="#ffffff",
        padding=f"{Space.s3} {Space.s3} {Space.s1}",
    )


@rx.page(route="/ledger", title="iDataSight · Ledger", on_load=AppState.load_ledger)
def ledger_page() -> rx.Component:
    return shell(
        kicker("Cost per correct answer, by episode"),
        cost_chart(),
        rx.el.div(
            rx.foreach(AppState.ledger_tiles, tile),
            display="flex",
            gap=Space.s2,
            margin_top=Space.s3,
        ),
        note(
            "every run appended a row — this chart is a live query, not a slide",
            margin_top=Space.s3,
        ),
        active="Ledger",
        rail_component=rail("Ledger", items=AppState.ledger_rows),
    )
