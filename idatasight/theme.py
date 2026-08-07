"""Modernist theme — the single source of truth for iDataSight's look.

Every color, font, spacing step, radius, and shadow used anywhere in the app
is defined here. To retheme the whole application, edit this file and nothing
else. Tokens mirror the ``:root`` block of the Modernist design system in the
iDataSight wireframes.
"""


class Color:
    """Color tokens."""

    bg = "#f3f2f2"
    surface = "#eae9e9"
    rail_bg = "#f6f5f2"
    text = "#201e1d"
    accent = "#ec3013"
    accent_2 = "#e15b47"
    divider = "rgba(32, 30, 29, 0.40)"

    # Derived inks (the wireframe's color-mix() values, precomputed).
    text_muted = "rgba(32, 30, 29, 0.55)"
    text_soft = "rgba(32, 30, 29, 0.70)"
    text_faint = "rgba(32, 30, 29, 0.50)"

    # Tonal ramps — one shared lightness scale across roles.
    neutral_100 = "#f8f4f4"
    neutral_200 = "#eae7e7"
    neutral_300 = "#d7d3d3"
    neutral_400 = "#bab6b6"
    neutral_500 = "#9b9797"
    neutral_600 = "#7d7979"
    neutral_700 = "#605d5d"
    neutral_800 = "#444141"
    neutral_900 = "#2d2b2b"

    accent_100 = "#fff2ef"
    accent_200 = "#ffe0d9"
    accent_300 = "#ffc4b8"
    accent_400 = "#ff9783"
    accent_500 = "#ff563c"
    accent_600 = "#dd2b0f"
    accent_700 = "#ae1800"
    accent_800 = "#7c1405"
    accent_900 = "#4d170e"

    accent_2_100 = "#fff2ef"
    accent_2_200 = "#ffe0da"
    accent_2_300 = "#ffc4b9"
    accent_2_400 = "#ff9784"
    accent_2_500 = "#ef6853"
    accent_2_600 = "#c94b39"
    accent_2_700 = "#9e3526"
    accent_2_800 = "#71261b"
    accent_2_900 = "#471d16"

    # Highlight fill for flagged table rows (2c/1f trap rows).
    flag_bg = "#fdeae6"


class Font:
    """Typography tokens."""

    heading = "'Archivo', system-ui, sans-serif"
    body = "'Archivo', system-ui, sans-serif"
    mono = "ui-monospace, Menlo, monospace"
    heading_weight = "800"

    stylesheet = (
        "https://fonts.googleapis.com/css2"
        "?family=Archivo:wght@400;600;700;800&display=swap"
    )


class Space:
    """Spacing scale."""

    s1 = "4px"
    s2 = "8px"
    s3 = "12px"
    s4 = "16px"
    s6 = "24px"
    s8 = "32px"


class Radius:
    """Corner radii — Modernist is square."""

    sm = "0px"
    md = "0px"
    lg = "0px"


class Shadow:
    """Elevation — soft ink-tinted shadows on a light ground."""

    sm = "0 1px 2px rgba(45, 43, 43, 0.14)"
    md = "0 3px 10px rgba(45, 43, 43, 0.16)"
    lg = "0 12px 32px rgba(45, 43, 43, 0.22)"


class Border:
    """Structural strokes — the Modernist hard edge."""

    hairline = f"1px solid {Color.divider}"
    frame = f"1.5px solid {Color.text}"
    heavy = f"2px solid {Color.text}"
    accent = f"2px solid {Color.accent}"
    dashed = "1.5px dashed #b5b3ab"
    rule = f"2px solid {Color.divider}"


# Global styles handed to rx.App — body ground, selection, focus ring.
GLOBAL_STYLE = {
    "font_family": Font.body,
    "font_size": "15px",
    "line_height": "1.55",
    "background": Color.bg,
    "color": Color.text,
    "::selection": {"background": "rgba(236, 48, 19, 0.30)"},
    "*:focus-visible": {
        "outline": f"2px solid {Color.accent}",
        "outline_offset": "2px",
    },
}

STYLESHEETS = [Font.stylesheet]
