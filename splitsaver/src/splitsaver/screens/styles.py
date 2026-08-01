"""
Shared layout constants used across screens, so spacing stays consistent
instead of every file picking its own magic numbers.

Usage:
    from splitsaver.screens.styles import SPACE_SM, SPACE_MD, margin_bottom

    toga.Label("Hi", style=Pack(margin=margin_bottom(SPACE_MD)))
"""

# Spacing scale (points). Pick from these rather than inventing new numbers.
SPACE_XS = 4    # tight gaps: label directly above its input, digits next to a unit
SPACE_SM = 8    # gaps between adjacent inline controls (input -> button, field -> label)
SPACE_MD = 12   # standard gap between stacked sections (title -> list, list -> form)
SPACE_LG = 20   # separation between clearly distinct groups on a crowded screen

# Outer margin applied to every screen's root box
SCREEN_PADDING = 12

# Font sizes
FONT_SIZE_TITLE = 18
FONT_SIZE_SUBTITLE = 13
FONT_SIZE_BODY = 14


def margin_bottom(size):
    """Margin shorthand: space below an element only."""
    return (0, 0, size, 0)


def margin_top(size):
    """Margin shorthand: space above an element only."""
    return (size, 0, 0, 0)


def margin_right(size):
    """Margin shorthand: space to the right of an element only (e.g. before the next item in a row)."""
    return (0, size, 0, 0)


def margin_left(size):
    """Margin shorthand: space to the left of an element only (e.g. indenting a sub-item)."""
    return (0, 0, 0, size)