"""Page 3 · Analysis — verdicts · traps caught · the receipt (wireframe 2c)."""

import reflex as rx

from ..components.shell import shell
from ..components.ui import bar, btn, card, chip, kicker, note, table, td, th
from ..models import Trap, Verdict
from ..state import AppState
from ..theme import Border, Color, Space


def verdict_row(v: Verdict) -> rx.Component:
    return rx.el.tr(
        td(v.country),
        td(v.primary),
        rx.cond(
            v.outside,
            td(v.verdict, font_style="italic", color=Color.neutral_600),
            td(v.verdict, font_weight="700"),
        ),
    )


def trap_card(t: Trap) -> rx.Component:
    return card(
        rx.el.div(t.entity, font_weight="700", font_size="13px"),
        rx.el.div(
            rx.el.span(t.decoy_name, font_size="12px", flex="none"),
            rx.el.div(bar(t.decoy_width), width="110px", flex="none"),
            rx.el.span(t.decoy_label, font_size="12px"),
            margin_top="6px",
            display="flex",
            align_items="center",
            gap="6px",
        ),
        rx.el.div(
            rx.el.span(t.primary_name, font_size="12px", flex="none"),
            rx.el.div(bar(t.primary_width, red=True), width="110px", flex="none"),
            rx.el.span(t.primary_label, font_size="12px"),
            margin_top="3px",
            display="flex",
            align_items="center",
            gap="6px",
        ),
        note(
            rx.el.span(
                "unguided reading: ",
                t.unguided,
                " · your belief: ",
                rx.el.span(t.believed, font_weight="700"),
            ),
            margin_top="6px",
        ),
        accent=True,
    )


@rx.page(
    route="/analysis",
    title="iDataSight · Analysis",
    on_load=AppState.load_analysis,
)
def analysis_page() -> rx.Component:
    return shell(
        rx.el.div(
            chip(AppState.belief_label, "solid"),
            note("recalled"),
            rx.el.span(flex="1"),
            btn("Run", variant="primary", on_click=AppState.run_analysis),
            display="flex",
            align_items="center",
            gap=Space.s3,
            margin_bottom=Space.s4,
        ),
        rx.el.div(
            rx.el.div(
                kicker("Verdicts — under your belief"),
                table(
                    rx.el.thead(
                        rx.el.tr(th("Country"), th("Primary"), th("Verdict"))
                    ),
                    rx.el.tbody(rx.foreach(AppState.verdicts, verdict_row)),
                ),
                flex="1.1",
                min_width="0",
            ),
            rx.el.div(
                kicker(
                    rx.el.span("Traps caught — ", AppState.trap_count),
                    red_square=True,
                ),
                rx.foreach(AppState.traps, trap_card),
                note(AppState.thesis_note, margin_top=Space.s2),
                flex="1",
                min_width="0",
            ),
            display="flex",
            gap=Space.s6,
            align_items="flex-start",
        ),
        rx.el.div(
            rx.el.span(
                rx.el.span("Receipt", font_weight="700", color=Color.text),
                " · ",
                AppState.receipt.tokens,
                " tokens · ",
                AppState.receipt.series,
                " series",
            ),
            rx.el.span(
                "ungrounded: ",
                AppState.receipt.ungrounded_tokens,
                " · ",
                AppState.receipt.ungrounded_series,
            ),
            rx.el.span(
                "logged → ledger row #",
                AppState.receipt.ledger_row,
                margin_left="auto",
            ),
            display="flex",
            gap=Space.s4,
            font_size="12px",
            color=Color.neutral_600,
            border_top=Border.heavy,
            margin_top=Space.s6,
            padding_top=Space.s2,
        ),
        active="Analysis",
    )
