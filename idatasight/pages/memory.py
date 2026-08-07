"""Page 5 · Memory — two histories, kept apart (wireframe 2e)."""

import reflex as rx

from ..components.shell import shell
from ..components.ui import btn, card, chip, note
from ..models import Analyst, TimelineEvent
from ..state import AppState
from ..theme import Border, Color, Space


def analyst_chip(a: Analyst) -> rx.Component:
    label = rx.cond(
        a.belief_label != "",
        a.name + " — " + a.belief_label,
        a.name + " ▾",
    )
    return rx.el.span(
        rx.cond(a.selected, chip(label, "solid"), chip(label, "outline")),
        cursor="pointer",
        on_click=AppState.select_analyst(a.name),
    )


def timeline_event(e: TimelineEvent) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            position="absolute",
            left="-21px",
            top="4px",
            width="9px",
            height="9px",
            background=rx.cond(e.kind == "belief", Color.accent, "#ffffff"),
            border=rx.cond(
                e.kind == "belief",
                f"2px solid {Color.accent}",
                f"2px solid {Color.text}",
            ),
        ),
        rx.el.div(
            rx.el.span(
                e.title,
                font_weight=rx.cond(e.kind == "belief", "700", "500"),
                font_size="13.5px",
            ),
            rx.cond(
                e.when != "",
                note(rx.el.span(" ", e.when), display="inline", margin_left="6px"),
                rx.fragment(),
            ),
        ),
        rx.cond(
            e.detail != "",
            rx.el.div(e.detail, font_size="12.5px", margin_top="2px"),
            rx.fragment(),
        ),
        rx.cond(
            e.note != "",
            note(e.note, margin_top="2px"),
            rx.fragment(),
        ),
        position="relative",
        margin_bottom=Space.s4,
    )


@rx.page(route="/memory", title="iDataSight · Memory", on_load=AppState.load_memory)
def memory_page() -> rx.Component:
    return shell(
        rx.el.div(
            rx.el.span(
                AppState.belief_name, font_weight="700", font_size="16px"
            ),
            rx.foreach(AppState.analysts, analyst_chip),
            rx.el.span(flex="1"),
            btn(AppState.version_label, variant="ghost"),
            display="flex",
            align_items="center",
            gap=Space.s3,
            margin_bottom=Space.s3,
        ),
        rx.el.div(
            rx.el.span(
                rx.el.span("● ", color=Color.accent),
                "belief change — meaning moved",
            ),
            rx.el.span("○ data update — verdicts moved"),
            display="flex",
            gap=Space.s4,
            font_size="12px",
            color=Color.neutral_600,
            margin_bottom=Space.s3,
        ),
        rx.el.div(
            rx.foreach(AppState.timeline, timeline_event),
            border_left=Border.heavy,
            margin_left="6px",
            padding_left="22px",
        ),
        rx.cond(
            AppState.compare_note != "",
            card(
                AppState.compare_note,
                dashed=True,
                font_size="12.5px",
                margin_top=Space.s2,
            ),
            rx.fragment(),
        ),
        active="Memory",
    )
