"""App entry — global theme wiring and page registration.

The look of the entire app is driven by theme.py; nothing here or in the
pages hardcodes a color, font, or radius.
"""

import reflex as rx

from . import pages  # noqa: F401  — importing registers the five routes
from .theme import GLOBAL_STYLE, STYLESHEETS

app = rx.App(
    style=GLOBAL_STYLE,
    stylesheets=STYLESHEETS,
)
