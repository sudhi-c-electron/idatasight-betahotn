"""Shared chrome — top nav, memory rail, and the page shell.

Every page renders inside shell(): the 5-tab bar on top, content on the left,
the always-present rail on the right.
"""

import reflex as rx

from ..state import AppState
from ..theme import Border, Color, Font, Space
from .ui import mem_card, note

NAV_TABS = [
    ("Datasets", "/"),
    ("Beliefs", "/beliefs"),
    ("Analysis", "/analysis"),
    ("Ledger", "/ledger"),
    ("Memory", "/memory"),
]


def _tab(label: str, href: str, active: bool) -> rx.Component:
    return rx.link(
        label,
        href=href,
        font_size="12px",
        font_weight="700" if active else "500",
        text_transform="uppercase",
        letter_spacing="0.07em",
        text_decoration="none",
        color=Color.text if active else Color.neutral_600,
        border_bottom=(
            f"2px solid {Color.accent}" if active else "2px solid transparent"
        ),
        padding_bottom="3px",
        _hover={"color": Color.accent},
    )


def nav(active: str) -> rx.Component:
    return rx.el.header(
        rx.el.span(
            rx.el.span("i", color=Color.accent),
            "DataSight",
            font_family=Font.heading,
            font_weight=Font.heading_weight,
            font_size="19px",
            margin_right="auto",
        ),
        *[_tab(label, href, label == active) for label, href in NAV_TABS],
        rx.el.span(
            width="16px",
            height="16px",
            border=Border.frame,
            border_radius="50%",
            margin_left=Space.s4,
        ),
        display="flex",
        align_items="center",
        gap=Space.s6,
        padding=f"{Space.s3} {Space.s6}",
        border_bottom=Border.rule,
        background=Color.bg,
    )


def rail(
    title: str = "Memory",
    items=None,
    extra: rx.Component | None = None,
) -> rx.Component:
    """The right-hand rail. Defaults to the shared beliefs memory."""
    if items is None:
        items = AppState.beliefs
    children = [
        rx.el.div(
            rx.el.span("■ ", color=Color.accent, font_size="10px"),
            title,
            font_size="11px",
            font_weight="700",
            letter_spacing="0.1em",
            text_transform="uppercase",
            color=Color.neutral_600,
            margin_bottom=Space.s1,
        ),
        rx.foreach(items, mem_card),
    ]
    if extra is not None:
        children.append(extra)
    return rx.el.aside(
        *children,
        width="230px",
        flex="none",
        border_left=Border.heavy,
        padding=f"{Space.s4} {Space.s3}",
        background=Color.rail_bg,
        display="flex",
        flex_direction="column",
        gap="9px",
    )


def shell(
    *content,
    active: str,
    rail_component: rx.Component | None = None,
) -> rx.Component:
    return rx.el.div(
        nav(active),
        rx.el.div(
            rx.el.main(
                *content,
                flex="1",
                min_width="0",
                padding=f"{Space.s6} {Space.s8}",
                max_width="960px",
            ),
            rail_component if rail_component is not None else rail(),
            display="flex",
            align_items="stretch",
            flex="1",
        ),
        display="flex",
        flex_direction="column",
        min_height="100vh",
        background=Color.bg,
    )


def rail_note(text: str) -> rx.Component:
    return note(text, italic=False, font_size="10.5px")
