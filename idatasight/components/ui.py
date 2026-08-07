"""Modernist UI primitives — every style value comes from theme.py."""

import reflex as rx

from ..models import MemoryItem, Tile
from ..theme import Border, Color, Font, Radius, Shadow, Space


def kicker(text, red_square: bool = False, **style) -> rx.Component:
    """Small uppercase section label (the wireframe's .h)."""
    children = []
    if red_square:
        children.append(
            rx.el.span("■ ", color=Color.accent, font_size="10px")
        )
    children.append(rx.el.span(text))
    base = {
        "font_size": "11px",
        "font_weight": "700",
        "letter_spacing": "0.1em",
        "text_transform": "uppercase",
        "color": Color.neutral_600,
        "margin_bottom": Space.s2,
    }
    base |= style
    return rx.el.div(*children, **base)


def note(text, italic: bool = True, **style) -> rx.Component:
    """Muted footnote (the wireframe's .note)."""
    base = {
        "font_size": "12px",
        "color": Color.neutral_600,
        "font_style": "italic" if italic else "normal",
    }
    base |= style
    return rx.el.div(text, **base)


def btn(label: str, variant: str = "primary", **props) -> rx.Component:
    """Modernist button. Variants: primary (accent), dark, ghost."""
    base = {
        "display": "inline-flex",
        "align_items": "center",
        "gap": "6px",
        "cursor": "pointer",
        "font_family": Font.heading,
        "font_weight": "600",
        "font_size": "13px",
        "line_height": "1.2",
        "padding": "8px 16px",
        "border": "1.5px solid transparent",
        "border_radius": Radius.md,
        "white_space": "nowrap",
    }
    if variant == "primary":
        base |= {"background": Color.accent, "color": Color.bg}
        base["_hover"] = {"background": Color.accent_600}
    elif variant == "dark":
        base |= {"background": Color.text, "color": Color.bg}
        base["_hover"] = {"background": Color.neutral_800}
    else:  # ghost
        base |= {
            "background": "transparent",
            "color": Color.text,
            "border": Border.frame,
        }
        base["_hover"] = {"background": "rgba(32, 30, 29, 0.07)"}
    return rx.el.button(label, style=base, **props)


def chip(text, variant: str = "outline", **props) -> rx.Component:
    """Bordered mono chip (the wireframe's .chip)."""
    style = {
        "display": "inline-flex",
        "align_items": "center",
        "border": f"1px solid {Color.neutral_400}",
        "background": "#ffffff",
        "color": Color.text,
        "padding": "3px 9px",
        "font_size": "11.5px",
        "font_family": Font.mono,
        "border_radius": Radius.sm,
    }
    if variant == "red":
        style |= {"border_color": Color.accent, "color": Color.accent}
    elif variant == "solid":
        style |= {
            "background": Color.text,
            "border_color": Color.text,
            "color": "#ffffff",
        }
    return rx.el.span(text, style=style, **props)


def card(*children, accent: bool = False, dashed: bool = False, **style):
    """Framed card (the wireframe's .card / .dash)."""
    border = Border.frame
    background = "#ffffff"
    if accent:
        border = Border.accent
    if dashed:
        border = Border.dashed
        background = "#faf9f7"
    base = {
        "border": border,
        "background": background,
        "padding": f"{Space.s3} {Space.s4}",
        "border_radius": Radius.md,
    }
    base |= style  # explicit overrides win
    return rx.el.div(*children, **base)


def tile(t: Tile) -> rx.Component:
    """Stat tile (the wireframe's .tile). Safe inside rx.foreach."""
    return rx.el.div(
        rx.el.div(
            t.value,
            font_size="22px",
            font_weight="800",
            letter_spacing="-0.01em",
            font_family=Font.heading,
            color=rx.cond(t.accent, Color.accent, Color.text),
        ),
        rx.el.div(
            t.label,
            font_size="10.5px",
            color=Color.neutral_600,
            text_transform="uppercase",
            letter_spacing="0.05em",
            margin_top="2px",
        ),
        border=Border.frame,
        padding=f"{Space.s2} {Space.s3}",
        flex="1",
        background="#ffffff",
    )


def mem_card(item: MemoryItem) -> rx.Component:
    """Rail memory entry (the wireframe's .mem). Safe inside rx.foreach."""
    return rx.el.div(
        item.name,
        rx.el.span(
            item.note,
            display="block",
            color=Color.neutral_600,
            font_size="10.5px",
            font_family=Font.body,
            font_weight="400",
        ),
        border=rx.cond(item.highlight, Border.accent, Border.frame),
        background="#ffffff",
        padding=f"{Space.s2} {Space.s2}",
        font_size="12px",
        font_weight="600",
        line_height="1.4",
    )


def bar(width: str, red: bool = False, **style) -> rx.Component:
    """Solid token bar (the wireframe's .tokbar)."""
    return rx.el.div(
        width=width,
        height="10px",
        background=Color.accent if red else Color.text,
        display="inline-block",
        vertical_align="middle",
        **style,
    )


# --- table helpers ---------------------------------------------------------

TH_STYLE = {
    "font_size": "11px",
    "text_transform": "uppercase",
    "letter_spacing": "0.08em",
    "text_align": "left",
    "color": Color.text_muted,
    "border_bottom": Border.heavy,
    "padding": f"{Space.s2} {Space.s2}",
    "font_weight": "700",
}

TD_STYLE = {
    "border_bottom": f"1px solid {Color.neutral_300}",
    "padding": f"{Space.s2} {Space.s2}",
    "vertical_align": "top",
    "font_size": "13.5px",
}


def th(text) -> rx.Component:
    return rx.el.th(text, style=TH_STYLE)


def td(*children, mono: bool = False, **style) -> rx.Component:
    s = dict(TD_STYLE)
    if mono:
        s |= {"font_family": Font.mono, "font_size": "12.5px"}
    s |= style
    return rx.el.td(*children, style=s)


def table(*children, **style) -> rx.Component:
    return rx.el.table(
        *children,
        width="100%",
        border_collapse="collapse",
        **style,
    )
