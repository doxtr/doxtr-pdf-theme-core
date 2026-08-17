"""Color preparation helpers for LaTeX preamble generation (RGB float output).

This module provides utilities for converting hex colors to RGB float format
suitable for LaTeX's ``{rgb}`` color model, with safe fallbacks to prevent
build failures. All colors in the document use the same RGB colorspace as
embedded raster images, preventing visible seams in PDF viewers that handle
CMYK and RGB colorspace conversions differently.

Error Handling Contract (Two-Tier System)
-----------------------------------------
This module follows a two-tier error handling pattern:

1. **Boundary functions** (user-facing, like `safe_cmyk()`):
   - Log a warning on invalid input
   - Return a safe default value
   - NEVER raise exceptions
   - NEVER return None where a string is expected downstream

2. **Internal helpers** (in utils.py, like `_hex_to_rgb`, `_get_luminance`):
   - Return None or a sentinel on invalid input
   - Do NOT log — the caller decides whether to log
   - Let the boundary function handle user feedback

The `safe_cmyk()` function is the primary boundary function for color values
that will be embedded in LaTeX. All color values destined for LaTeX output
should pass through `safe_cmyk()` to ensure valid RGB float strings.
"""
from typing import Optional, List, Tuple
from sphinx.util import logging

from .utils import hex_to_cmyk_string, hex_to_rgb_floats, get_highest_contrast_color

__all__ = [
    'safe_cmyk',
    'safe_rgb',
    'prepare_cmyk_colors',
    'CONTAINER_COLOR_KEYS',
    'TABLE_COLOR_KEYS',
    'FIGURE_COLOR_KEYS',
    'CODE_COLOR_KEYS',
    'SIDEBAR_COLOR_KEYS',
    'TOPIC_COLOR_KEYS',
    'CONTENTS_COLOR_KEYS',
]

logger = logging.getLogger(__name__)


def safe_cmyk(color_val: Optional[str], default: str = '0.000, 0.000, 0.000') -> str:
    """Convert a hex color to RGB float format for LaTeX ``\\definecolor{}{rgb}{}``.

    Despite the legacy name ``safe_cmyk``, this function now outputs RGB float
    values (r, g, b in [0.0, 1.0]) for use with LaTeX's ``{rgb}`` color model.
    This ensures all document colors share the same colorspace as embedded
    raster images, preventing visible seams in PDF viewers that handle CMYK
    and RGB colorspace conversions differently.

    This is the PRIMARY BOUNDARY FUNCTION for color values in LaTeX output.
    It implements the "never fail" contract:
    - Always returns a valid RGB float string
    - NEVER returns None
    - NEVER raises exceptions
    - Logs warnings on invalid input for debugging

    Use this function for ALL color values that will be embedded in LaTeX.
    Internal color processing functions may return None; wrap their output
    with safe_cmyk() before passing to LaTeX templates.

    Args:
        color_val: A hex color string (e.g. '#FF0000'), an existing RGB float
                   string (3 comma-separated values), or None/empty.
        default: RGB float fallback if conversion fails. Defaults to black.

    Returns:
        A valid RGB float color string suitable for LaTeX ``{rgb}`` model.
        Never None.

    Examples:
        >>> safe_cmyk('#FF0000')
        '1.000, 0.000, 0.000'
        >>> safe_cmyk(None)
        '0.000, 0.000, 0.000'
        >>> safe_cmyk('#242424')
        '0.141, 0.141, 0.141'
    """
    if not color_val:
        return default
    # If value is already a float string (contains commas), pass through.
    # Handles both 3-value (rgb) and legacy 4-value (cmyk) strings.
    if isinstance(color_val, str) and ',' in color_val:
        return color_val
    try:
        r, g, b = hex_to_rgb_floats(color_val)
        return f'{r:.3f}, {g:.3f}, {b:.3f}'
    except Exception as e:
        logger.warning(f"[Doxtr Core] Color conversion failed for '{color_val}': {e}. Using default.")
        return default


# --- Color key groups per element type ---
# Used by prepare_cmyk_colors() to batch-convert color keys to CMYK.
# Each tuple is (key_name, default_hex_value).

CONTAINER_COLOR_KEYS: List[Tuple[str, str]] = [
    ('title_color', '#000000'),
    ('title_font_color', '#FFFFFF'),
    ('title_icon_color', '#FFFFFF'),
    ('content_font_color', '#000000'),
    ('content_background_color', '#FFFFFF'),
    ('title_background_color', '#FFFFFF'),
    ('quote_font_color', '#000000'),
    ('quote_background_color', '#FFFFFF'),
    ('quote_frame_color', '#000000'),
]

TABLE_COLOR_KEYS: List[Tuple[str, str]] = [
    ('header_background_color', '#1E3A8A'),
    ('header_font_color', '#FFFFFF'),
    ('row_color_odd', '#F8FAFC'),
    ('row_color_even', '#FFFFFF'),
    ('title_background_color', '#1E3A8A'),
    ('title_font_color', '#FFFFFF'),
    ('title_background_fade_mask_color', '#FFFFFF'),
]

FIGURE_COLOR_KEYS: List[Tuple[str, str]] = [
    ('caption_background_color', '#FFFFFF'),
    ('caption_font_color', '#000000'),
]

CODE_COLOR_KEYS: List[Tuple[str, str]] = [
    ('title_background_color', '#1E3A8A'),
    ('title_font_color', '#FFFFFF'),
    ('content_background_color', '#F8FAFC'),
    ('content_font_color', '#0F172A'),
    ('border_color', '#1E3A8A'),
    ('icon_color', '#FFFFFF'),
]

SIDEBAR_COLOR_KEYS: List[Tuple[str, str]] = [
    ('title_background_color', '#184878'),
    ('title_font_color', '#FFFFFF'),
    ('title_icon_color', '#78D8F0'),
    ('content_background_color', '#F0F8FF'),
    ('content_font_color', '#1A1A2E'),
    ('border_color', '#184878'),
    ('subtitle_font_color', '#306090'),
]

TOPIC_COLOR_KEYS: List[Tuple[str, str]] = [
    ('title_background_color', '#1E3A6E'),
    ('title_font_color', '#FFFFFF'),
    ('title_icon_color', '#FFFFFF'),
    ('content_background_color', '#F0F4FA'),
    ('content_font_color', '#1A1A2E'),
    ('border_color', '#3A5A8E'),
    ('bottom_frame_color', '#1E3A6E'),
    ('cutaway_fill_color', '#FFFFFF'),
]

CONTENTS_COLOR_KEYS: List[Tuple[str, str]] = [
    ('title_background_color', '#1E3A6E'),
    ('title_font_color', '#FFFFFF'),
    ('title_icon_color', '#FFFFFF'),
    ('content_background_color', '#F0F4FA'),
    ('content_font_color', '#1A1A2E'),
    ('border_color', '#3A5A8E'),
    ('bottom_frame_color', '#1E3A6E'),
    ('cutaway_fill_color', '#FFFFFF'),
]


def prepare_cmyk_colors(conf: dict, color_key_defaults: List[Tuple[str, str]]) -> None:
    """Add `_cmyk` suffixed entries to conf for each (key, default) pair.

    This function processes a configuration dictionary and adds CMYK-converted
    versions of color values. For each key in color_key_defaults, it looks up
    the value in conf (falling back to the default), converts it to CMYK,
    and stores it with a '_cmyk' suffix.

    Args:
        conf: The config dict to update in-place.
        color_key_defaults: List of (key, default_hex) tuples.

    Example:
        >>> conf = {'title_color': '#FF0000'}
        >>> prepare_cmyk_colors(conf, [('title_color', '#000000')])
        >>> conf['title_color_cmyk']
        '0.000, 1.000, 1.000, 0.000'
    """
    for key, default in color_key_defaults:
        cmyk_key = f'{key}_cmyk'
        val = conf.get(key) or default
        conf[cmyk_key] = safe_cmyk(val)


# Historical naming: safe_cmyk() actually produces RGB floats, not CMYK.
# The name dates from when the extension used CMYK output. Adding this alias
# for clarity in new code while preserving backward compatibility.
safe_rgb = safe_cmyk
