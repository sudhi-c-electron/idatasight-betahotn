"""Page 2 · Beliefs — declare, then ratify each field (wireframe 2b)."""

import reflex as rx

from ..components.shell import shell
from ..components.ui import btn, card, chip, kicker, note
from ..models import GroundingField
from ..state import AppState
from ..theme import Border, Color, Font, Space

INPUT_STYLE = {
    "width": "100%",
    "border": Border.frame,
    "background": "#ffffff",
    "padding": "8px 10px",
    "font_family": Font.body,
    "font_size": "14px",
    "color": Color.text,
    "caret_color": Color.accent,
    "border_radius": "0px",
}


def field_row(f: GroundingField) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            f.key,
            width="92px",
            flex="none",
            font_size="11px",
            font_weight="700",
            letter_spacing="0.1em",
            text_transform="uppercase",
            color=Color.neutral_600,
            padding_top="2px",
        ),
        rx.el.div(
            rx.cond(
                f.editing,
                rx.el.input(
                    default_value=f.value,
                    on_blur=lambda v: AppState.set_field_value(f.key, v),
                    style=INPUT_STYLE | {"font_size": "13px"},
                ),
                rx.el.span(
                    f.value,
                    font_size="13.5px",
                    font_family=rx.cond(f.mono, Font.mono, Font.body),
                ),
            ),
            flex="1",
            min_width="0",
        ),
        rx.el.div(
            rx.cond(
                f.editing,
                chip(
                    "✓ done",
                    "solid",
                    cursor="pointer",
                    on_click=AppState.finish_edit(f.key),
                ),
                rx.fragment(
                    chip(
                        rx.cond(f.ratified, "✓ ratified", "✓"),
                        "red",
                        cursor="pointer",
                        on_click=AppState.ratify_field(f.key),
                    ),
                    chip(
                        "✎",
                        "outline",
                        cursor="pointer",
                        margin_left="4px",
                        on_click=AppState.edit_field(f.key),
                    ),
                ),
            ),
            flex="none",
            text_align="right",
        ),
        display="flex",
        gap=Space.s3,
        align_items="flex-start",
        padding=f"{Space.s2} 0",
        border_bottom=f"1px solid {Color.neutral_300}",
    )


@rx.page(
    route="/beliefs",
    title="iDataSight · Beliefs",
    on_load=AppState.load_beliefs_page,
)
def beliefs_page() -> rx.Component:
    return shell(
        kicker("Your hypothesis, in your own words"),
        rx.el.textarea(
            value=AppState.hypothesis,
            on_change=AppState.set_hypothesis,
            style=INPUT_STYLE | {"min_height": "64px", "resize": "vertical"},
        ),
        rx.el.div(
            btn(
                "Draft the grounding →",
                variant="ghost",
                on_click=AppState.draft_grounding,
            ),
            margin=f"{Space.s3} 0",
        ),
        rx.cond(
            AppState.drafted,
            card(
                kicker("Drafted from your words — a proposal, you decide"),
                rx.foreach(AppState.draft_fields, field_row),
                rx.el.div(
                    btn(
                        "Ratify & remember",
                        variant="primary",
                        on_click=AppState.ratify_belief,
                    ),
                    margin_top=Space.s3,
                ),
                border=Border.heavy,
            ),
            rx.fragment(),
        ),
        rx.cond(
            AppState.ratify_error != "",
            note(AppState.ratify_error, color=Color.accent, margin_bottom=Space.s3),
            rx.fragment(),
        ),
        rx.cond(
            AppState.ratified_version != "",
            card(
                rx.el.span(
                    "Your belief is remembered — ",
                    rx.el.span(
                        AppState.ratified_version,
                        " · ",
                        AppState.remembered_on,
                        font_weight="700",
                    ),
                    ". ",
                    font_weight="600",
                ),
                rx.el.span(
                    "Reopening it later drafts the next version; "
                    "a version is never overwritten.",
                    color=Color.neutral_700,
                ),
                dashed=True,
                font_size="12.5px",
                margin_top=Space.s3,
            ),
            rx.fragment(),
        ),
        active="Beliefs",
    )
