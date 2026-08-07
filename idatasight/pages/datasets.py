"""Page 1 · Datasets — choose the variant; refresh lives here (wireframe 2a)."""

import reflex as rx

from ..components.shell import rail, rail_note, shell
from ..components.ui import btn, card, kicker, note, table, td, th
from ..models import ColumnInfo, Dataset
from ..state import AppState
from ..theme import Border, Color, Space


def dataset_card(d: Dataset) -> rx.Component:
    return rx.el.div(
        rx.el.div(d.name, font_weight="700", font_size="14px"),
        note(d.source, margin_top="1px"),
        rx.el.div(d.summary, font_size="12px", margin_top="4px"),
        note(d.refreshed, margin_top="2px"),
        border=rx.cond(
            d.id == AppState.selected_dataset_id, Border.accent, Border.frame
        ),
        background="#ffffff",
        padding=f"{Space.s3} {Space.s4}",
        cursor="pointer",
        on_click=AppState.select_dataset(d.id),
    )


def column_row(c: ColumnInfo) -> rx.Component:
    return rx.el.tr(
        td(c.indicator, mono=True),
        td(c.unit),
        td(c.meaning),
    )


@rx.page(route="/", title="iDataSight · Datasets", on_load=AppState.load_datasets)
def datasets_page() -> rx.Component:
    return shell(
        rx.el.div(
            rx.foreach(AppState.datasets, dataset_card),
            display="grid",
            grid_template_columns="repeat(3, 1fr)",
            gap=Space.s3,
        ),
        kicker(
            "Columns — plain language, no interpretation yet",
            margin_top=Space.s6,
        ),
        table(
            rx.el.thead(
                rx.el.tr(th("Indicator"), th("Unit"), th("What it measures"))
            ),
            rx.el.tbody(rx.foreach(AppState.columns, column_row)),
            margin_bottom=Space.s4,
        ),
        rx.el.div(
            btn(
                "Analyze this →",
                variant="primary",
                on_click=rx.redirect("/analysis"),
            ),
            btn("Refresh data", variant="ghost", on_click=AppState.refresh_dataset),
            note("new rows re-run every remembered belief, automatically"),
            display="flex",
            align_items="center",
            gap=Space.s3,
        ),
        rx.cond(
            AppState.refresh_note != "",
            note(AppState.refresh_note, color=Color.accent, margin_top=Space.s2),
            rx.fragment(),
        ),
        active="Datasets",
        rail_component=rail(
            "Memory",
            extra=rail_note(
                rx.el.span(
                    AppState.selected_dataset.beliefs_attached,
                    " beliefs watch this dataset",
                )
            ),
        ),
    )
