"""Utility functions for the doxtr-pdf-theme-core extension.

This module provides core utilities used throughout the extension:

- **Boolean parsing**: `to_bool()` for coercing config values to booleans
- **Color math**: CMYK conversion, contrast calculation, brightness adjustment
- **Filename sanitization**: `get_safe_filename()` for LaTeX-safe names
- **Dictionary merge**: `deep_update()` for the three-tier config cascade
- **Page color adaptation**: luminance-proportional remapping (adapt_color_to_page)

Color functions use CMYK for LaTeX compatibility and support hex colors
with 3, 4, 6, or 8 digit formats (including alpha channel).
"""
import colorsys
import re
from typing import Optional, Union
from sphinx.util import logging

logger = logging.getLogger(__name__)

# --- BOOLEAN PARSING ---
# Frozenset of strings that are considered falsy when coercing to bool.
_FALSY_STRINGS = frozenset({'false', '0', 'none', 'no', ''})

# Relative luminance of perceptual middle gray (approx. #767676 under sRGB gamma).
# Used as a heuristic in get_highest_contrast_color: if the fixed color's luminance
# is above this threshold the background is considered "light" and we darken the
# target to achieve contrast; below it we lighten.
# Derived from the WCAG relative-luminance formula applied to a 50%-linear-range
# sRGB gray value.
_MIDDLE_GRAY_LUMINANCE = 0.17912

# Precompiled regex: strips non-alpha characters for LaTeX-safe names.
# Shared between __init__.py and ast_processors/containers.py.
_RE_SAFE_NAME = re.compile(r'[^a-zA-Z]')

# --- EXTENSIBLE COLOR OPERATION REGISTRY ---
# Theme authors may register custom operations for dd: color expressions.
# Each key is an operation name (string), value is a callable(hex_color, arg) -> hex_color.
_custom_color_operations: dict = {}

# Built-in operation names that cannot be overridden by custom registrations.
_BUILTIN_COLOR_OPERATIONS = frozenset({'lighten', 'darken', 'contrast'})


def register_color_operation(name: str, fn) -> None:
    """Register a custom color operation for dd: expressions.

    The registered function is called when a dd: expression uses the given
    operation name. This allows child themes to extend the color expression
    system with custom operations.

    Args:
        name: The operation name (used in dd: expressions, e.g. 'saturate'
              would be invoked as 'dd:primary:saturate:50').
        fn: A callable with signature fn(hex_color: str, arg: str) -> str.
            Receives the current color (6-digit hex with #) and the operation
            argument (string, may be empty). Must return a 6-digit hex color
            string (with #).

    Raises:
        ValueError: If name conflicts with a built-in operation.
        TypeError: If fn is not callable.

    Example::

        from doxtr_pdf_theme_core.utils import register_color_operation

        def saturate(hex_color, amount):
            # Custom saturation logic
            return adjusted_hex

        register_color_operation('saturate', saturate)

        # Now usable in conf.py:
        # doxtr_headings = {'chapter': {'color': 'dd:primary:saturate:50'}}
    """
    if not isinstance(name, str) or not name:
        raise ValueError(
            f"register_color_operation: name must be a non-empty string, got {name!r}."
        )
    if name in _BUILTIN_COLOR_OPERATIONS:
        raise ValueError(
            f"register_color_operation: '{name}' conflicts with a built-in operation. "
            f"Built-in operations: {sorted(_BUILTIN_COLOR_OPERATIONS)}"
        )
    if not callable(fn):
        raise TypeError(
            f"register_color_operation: fn must be callable, got {type(fn).__name__}."
        )
    if name in _custom_color_operations:
        logger.warning(
            f"[Doxtr Core] Color operation '{name}' is already registered. "
            f"Overwriting with new implementation."
        )
    _custom_color_operations[name] = fn


def to_bool(value: Union[bool, int, str, None], default: bool = True) -> bool:
    """Coerce a config value to bool.

    Handles: actual booleans, integers, and string representations.
    The strings 'false', '0', 'none', 'no', and '' are all considered False;
    everything else is considered True.

    This function centralizes the boolean parsing pattern that was previously
    duplicated throughout the codebase as:
        str(val).lower() not in ['false', '0', 'none', 'no']

    Args:
        value: The value to coerce. None returns default.
        default: Returned when value is None.

    Returns:
        The boolean interpretation of the value.

    Examples:
        >>> to_bool(True)
        True
        >>> to_bool('false')
        False
        >>> to_bool(None, default=False)
        False
        >>> to_bool('yes')
        True
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    return str(value).lower() not in _FALSY_STRINGS


def get_safe_filename(name: str) -> str:
    """Creates a filesystem-safe string from a project name."""
    safe = re.sub(r'[^A-Za-z0-9\s]+', '', name).strip().replace(' ', '_')
    return safe.lower() or "document"

def adjust_hex_brightness(hex_color: str, percentage: float) -> Optional[str]:
    """Adjusts the brightness of a hex color.

    Args:
        hex_color: A hex color string (e.g. '#FF0000'). Supports 3, 4, 6, or 8 digit formats.
        percentage: Positive values lighten, negative values darken.

    Returns:
        The adjusted hex color string, or None if hex_color is empty/falsy.
    """
    if not hex_color:
        return None
        
    hex_color = hex_color.lstrip('#')
    has_alpha = False
    alpha_str = ""
    
    # 3-digit (#RGB) and 4-digit (#RGBA): expand each nibble to two chars.
    # 4-digit expands to 8 chars (RRGGBBAA); the alpha-stripping block below handles it.
    if len(hex_color) in (3, 4):
        hex_color = ''.join([c*2 for c in hex_color])

    if len(hex_color) == 8:
        has_alpha = True
        alpha_str = hex_color[6:8]
        hex_color = hex_color[:6]
        
    if len(hex_color) != 6:
        logger.warning(f"[Doxtr Core] Invalid hex color '#{hex_color}'. Cannot adjust brightness.")
        return f"#{hex_color}{alpha_str}"

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    factor = percentage / 100.0

    if factor > 0:
        r = r + (255 - r) * factor
        g = g + (255 - g) * factor
        b = b + (255 - b) * factor
    elif factor < 0:
        r = r * (1 + factor)
        g = g * (1 + factor)
        b = b * (1 + factor)

    r = max(0, min(255, int(round(r))))
    g = max(0, min(255, int(round(g))))
    b = max(0, min(255, int(round(b))))

    if has_alpha:
        return f"#{r:02X}{g:02X}{b:02X}{alpha_str}"
    return f"#{r:02X}{g:02X}{b:02X}"

def _hex_to_rgb(hex_color: str):
    clean = hex_color.lstrip('#')
    if len(clean) == 8:
        clean = clean[:6]
    elif len(clean) == 4:
        clean = ''.join([c*2 for c in clean[:3]])
    elif len(clean) == 3:
        clean = ''.join([c*2 for c in clean])
    if len(clean) != 6:
        return 0, 0, 0
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def hex_to_rgb_floats(hex_color: str) -> tuple:
    """Convert a hex color to (r, g, b) floats in [0,1] for LaTeX {rgb} format.

    Delegates to _hex_to_rgb for normalization and validation. Returns (0,0,0)
    for invalid or empty inputs rather than raising. Supports 3, 4, 6, and
    8-digit hex formats (alpha channel is stripped).

    Args:
        hex_color: A hex color string with or without leading '#'.

    Returns:
        A tuple of three floats in [0.0, 1.0].
    """
    if not hex_color or not isinstance(hex_color, str):
        return (0.0, 0.0, 0.0)
    r, g, b = _hex_to_rgb(hex_color)
    return (r / 255.0, g / 255.0, b / 255.0)

def _get_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    srgb = [x / 255.0 for x in (r, g, b)]
    linear = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in srgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

def _get_contrast_ratio(lum1: float, lum2: float) -> float:
    l1 = max(lum1, lum2)
    l2 = min(lum1, lum2)
    return (l1 + 0.05) / (l2 + 0.05)

def get_highest_contrast_color(
    foreground_color: str,
    background_color: str,
    target: str = 'foreground',
    adjust_percent: float = 0.0,
    wcag_level: float = 4.5,
    color_debug: bool = False,
) -> str:
    """Auto-calculates a WCAG contrast-safe color.

    Given two colors, this function determines which one should be adjusted
    to meet the specified WCAG accessibility contrast threshold.
    It iteratively lightens or darkens the target color until the threshold
    is met, falling back to pure black or white if necessary.

    Args:
        foreground_color: The foreground (text/icon) hex color (with or without
            leading '#'). Supports 3, 4, 6, or 8 digit formats.
        background_color: The background hex color (with or without leading '#').
            Supports 3, 4, 6, or 8 digit formats.
        target: Which color to adjust. Use ``'foreground'`` to modify the
            foreground color, or ``'background'`` to modify the background
            color. Defaults to ``'foreground'``.
        adjust_percent: Optional post-adjustment percentage applied after
            contrast is resolved. Positive values lighten, negative values
            darken. Defaults to ``0.0`` (no additional adjustment).
        wcag_level: The minimum contrast ratio threshold. Use ``4.5`` for
            WCAG AA (normal text), ``7`` for WCAG AAA (enhanced contrast).
            Defaults to ``4.5`` (AA).
        color_debug: If ``True``, logs the input and output colors for every
            contrast calculation. Useful for theme authors to verify which
            colors were auto-corrected. Defaults to ``False``.

    Returns:
        A hex color string (with '#') that meets the specified WCAG threshold,
        or the original ``target_color`` if the threshold is already met.
        Returns ``None`` if either input is empty or invalid.

    Examples:
        >>> # Auto-fix foreground to contrast against background (AA)
        >>> # White on light-teal: algorithm darkens until 4.5:1 is met (~grey)
        >>> get_highest_contrast_color('#FFFFFF', '#9BE2F2')
        '#5C5C5C'

        >>> # Auto-fix background to contrast against a fixed foreground (AAA)
        >>> # Navy on light-teal is already 7.89:1 >= 7.0, so no change needed
        >>> get_highest_contrast_color('#2E3959', '#9BE2F2', target='background', wcag_level=7)
        '#9BE2F2'

        >>> # Fix contrast, then lighten the result by 80%
        >>> # Resolved foreground is #5C5C5C; lightened 80% -> light grey
        >>> get_highest_contrast_color('#FFFFFF', '#9BE2F2', adjust_percent=80)
        '#DEDEDE'
    """
    if not foreground_color or not background_color:
        return None
        
    if target == 'foreground':
        target_color = foreground_color
        fixed_color = background_color
    else:
        target_color = background_color
        fixed_color = foreground_color
        
    lum_fixed = _get_luminance(fixed_color)
    lum_target = _get_luminance(target_color)
    candidate = target_color
    
    if _get_contrast_ratio(lum_fixed, lum_target) < wcag_level:
        direction = -1 if lum_fixed > _MIDDLE_GRAY_LUMINANCE else 1
        for i in range(1, 101):
            test_color = adjust_hex_brightness(target_color, i * direction)
            if _get_contrast_ratio(lum_fixed, _get_luminance(test_color)) >= wcag_level:
                candidate = test_color
                break
        else:
            clean = target_color.lstrip('#')
            base = "#000000" if direction == -1 else "#FFFFFF"
            if len(clean) == 8:
                candidate = base + clean[6:8]
            elif len(clean) == 4:
                candidate = base + (clean[3]*2)
            else:
                candidate = base
        
        # Debug logging
        if color_debug:
            actual_ratio = _get_contrast_ratio(lum_fixed, lum_target)
            logger.warning(
                f"[Doxtr WCAG] Contrast {actual_ratio:.2f}:1 < {wcag_level}:1 threshold. "
                f"Adjusted '{target}' from '{target_color}' to '{candidate}'. "
                f"(Fixed: '{fixed_color}' at {_get_luminance(fixed_color):.4f})"
            )
    elif color_debug:
        logger.info(
            f"[Doxtr WCAG] Contrast {_get_contrast_ratio(lum_fixed, lum_target):.2f}:1 >= {wcag_level}:1 threshold. "
            f"No adjustment needed for '{target}' ('{target_color}')."
        )
    
    if adjust_percent != 0.0:
        return adjust_hex_brightness(candidate, adjust_percent)
    return candidate

def hex_to_cmyk_string(hex_color: str) -> Optional[str]:
    """Convert a hex color to a CMYK string for LaTeX.

    Supports 3-digit (#F00), 4-digit (#F00A, alpha stripped), 6-digit (#FF0000),
    and 8-digit (#FF000080, alpha stripped) hex formats.

    Args:
        hex_color: A hex color string with or without leading '#'.

    Returns:
        A CMYK string like '0.000, 1.000, 1.000, 0.000', or None if input is empty.
    """
    if not hex_color:
        return None
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 8:
        hex_color = hex_color[:6]
    elif len(hex_color) == 4:
        # 4-digit hex: 3 color digits + 1 alpha digit — expand color, strip alpha
        hex_color = ''.join([c*2 for c in hex_color[:3]])
    elif len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6:
        logger.warning(f"[Doxtr Core] Invalid hex color '#{hex_color}'. Falling back to black.")
        return "0, 0, 0, 1"

    try:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
    except ValueError:
        logger.warning(f"[Doxtr Core] Invalid hex characters in '#{hex_color}'. Falling back to black.")
        return "0, 0, 0, 1"

    k = 1.0 - max(r, g, b)
    if k == 1.0:
        return "0, 0, 0, 1"
    
    c = (1.0 - r - k) / (1.0 - k)
    m = (1.0 - g - k) / (1.0 - k)
    y = (1.0 - b - k) / (1.0 - k)

    return f"{c:.3f}, {m:.3f}, {y:.3f}, {k:.3f}"

def deep_update(d: dict, u: dict) -> dict:
    """Recursively merge *u* into *d*, mutating *d* **in-place**.

    Warning:
        This function **mutates** the first argument ``d`` in-place. Additionally,
        nested dict values from ``u`` are **not copied** — if ``u`` contains a dict
        at a key that is absent from ``d`` (or where ``d[k]`` is not a dict), that
        dict object is assigned directly into ``d`` by reference. A subsequent
        ``deep_update`` call on the returned ``d`` can therefore mutate ``u``'s
        nested sub-dicts. Pass ``copy.deepcopy(u)`` as the second argument when
        ``u`` must remain unmodified.

    Args:
        d: The base dictionary (mutated in-place).
        u: The dictionary whose values are merged into *d*.

    Returns:
        The same *d* object (mutated), for convenience in chaining.
    """
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d

# Public alias for internal hex to RGB converter
hex_to_rgb = _hex_to_rgb


def hex_dark_invert(hex_color: str) -> Optional[str]:
    """Convert a hex colour using soft partial inversion with hue correction.

    Applies CSS ``filter: invert(0.86) hue-rotate(180deg)`` mathematically.
    Produces a soft dark palette: white (#FFFFFF) → near-black (#242424),
    black (#000000) → off-white (#DBDBDB). Neutral greys stay grey; hues are
    corrected by the 180° rotation so colours shift to their complement.

    Alpha channels (8-digit hex) are preserved unchanged.

    Args:
        hex_color: A hex colour string. Supports 3, 4, 6, or 8 digit formats.

    Returns:
        The transformed hex string, or None if input is empty/invalid.
    """
    if not hex_color:
        return None

    clean = hex_color.lstrip('#')
    alpha = ''
    if len(clean) in (3, 4):
        clean = ''.join([c * 2 for c in clean])
    if len(clean) == 8:
        alpha = clean[6:8]
        clean = clean[:6]
    if len(clean) != 6:
        logger.warning(
            f"[Doxtr Core] hex_dark_invert: invalid hex '{hex_color}'. "
            f"Returning original."
        )
        return hex_color

    try:
        r = int(clean[0:2], 16)
        g = int(clean[2:4], 16)
        b = int(clean[4:6], 16)
    except ValueError:
        logger.warning(
            f"[Doxtr Core] hex_dark_invert: invalid hex '{hex_color}'. "
            f"Returning original."
        )
        return hex_color

    # Step 1: invert(0.86)  →  c' = 219.3 − 0.72 × c
    ri = 219.3 - 0.72 * r
    gi = 219.3 - 0.72 * g
    bi = 219.3 - 0.72 * b

    # Step 2: hue-rotate(180°) — W3C CSS matrix, cos(180°)=−1, sin(180°)≈0
    def _clamp(x):
        return max(0, min(255, round(x)))

    r_out = _clamp(-0.574 * ri + 1.430 * gi + 0.144 * bi)
    g_out = _clamp( 0.426 * ri + 0.430 * gi + 0.144 * bi)
    b_out = _clamp( 0.426 * ri + 1.430 * gi - 0.856 * bi)

    result = f'#{r_out:02X}{g_out:02X}{b_out:02X}'
    return result + alpha if alpha else result


# --- PAGE COLOR ADAPTATION ---
# Luminance-proportional remapping that shifts all theme colors to maintain
# their intended relationships when the page background differs from the
# theme's designed-for background.


def _get_luminance_from_floats(r: float, g: float, b: float) -> float:
    """Compute sRGB relative luminance from float RGB values in [0, 1].

    Same formula as _get_luminance but accepts pre-normalised float inputs
    rather than parsing a hex string. Used by _shift_to_target_luminance for
    performance during binary search (avoids repeated hex parsing).

    Args:
        r: Red channel in [0.0, 1.0].
        g: Green channel in [0.0, 1.0].
        b: Blue channel in [0.0, 1.0].

    Returns:
        Relative luminance Y in [0.0, 1.0].
    """
    linear = [
        x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
        for x in (r, g, b)
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _extract_alpha(hex_color: str) -> str:
    """Extract the alpha suffix from an 8-digit hex color.

    Returns the 2-character alpha suffix (e.g. '80') for 8-digit hex, or
    an empty string for 6-digit hex and shorter formats.

    Args:
        hex_color: A hex colour string with or without leading '#'.

    Returns:
        Two-character alpha string or empty string.
    """
    clean = hex_color.lstrip('#')
    if len(clean) == 4:
        # 4-digit RGBA shorthand → expand to 8 digits, return last 2
        return clean[3] * 2
    if len(clean) == 8:
        return clean[6:8]
    return ''


def _compute_adaptation_compression(designed_lum: float, actual_lum: float) -> tuple:
    """Compute directional compression factors for page adaptation.

    Returns (compress_dark, compress_light) — separate factors for colors
    below and above the designed page luminance. Compression is directional
    because the available luminance range differs above vs. below the page.

    Compression is capped at 1.0 — colors are never expanded beyond their
    original distance. This avoids distortion when the new page has MORE
    range in a given direction than the designed page.

    Args:
        designed_lum: Luminance of the page the theme was designed against.
        actual_lum: Luminance of the target page background.

    Returns:
        Tuple of (compress_dark, compress_light) floats in [0.0, 1.0].
    """
    # Available range below designed page (for dark colors)
    orig_dark_range = designed_lum  # distance from 0 to page
    # Available range above designed page (for light colors)
    orig_light_range = 1.0 - designed_lum  # distance from page to 1

    # Available range in each direction for new page
    new_dark_range = actual_lum
    new_light_range = 1.0 - actual_lum

    # Compression = new_range / orig_range (clamped to [0, 1])
    compress_dark = min(1.0, new_dark_range / orig_dark_range) if orig_dark_range > 0.001 else 1.0
    compress_light = min(1.0, new_light_range / orig_light_range) if orig_light_range > 0.001 else 1.0

    return compress_dark, compress_light


def _shift_to_target_luminance(hex_color: str, target_lum: float) -> str:
    """Shift a color's lightness to achieve target sRGB luminance.

    Uses binary search in HLS L-channel to find the L value that produces
    the target sRGB luminance while preserving the original hue and saturation.

    sRGB luminance is monotonically increasing with HLS L for any fixed (H, S),
    guaranteeing binary search convergence regardless of hue.

    Note: Python's colorsys uses HLS ordering (hue, lightness, saturation),
    not HSL. The function signature is rgb_to_hls() → (h, l, s).

    Args:
        hex_color: The color to shift (6 or 8 digit hex with #).
        target_lum: The target sRGB relative luminance in [0.0, 1.0].

    Returns:
        Shifted hex color string preserving alpha if present.
    """
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

    # Binary search for the L value that gives target luminance
    lo, hi = 0.0, 1.0
    for _ in range(20):  # 20 iterations → precision < 0.001%
        mid = (lo + hi) / 2
        r_t, g_t, b_t = colorsys.hls_to_rgb(h, mid, s)
        lum_t = _get_luminance_from_floats(r_t, g_t, b_t)
        if lum_t < target_lum:
            lo = mid
        else:
            hi = mid

    final_l = (lo + hi) / 2
    r_f, g_f, b_f = colorsys.hls_to_rgb(h, final_l, s)
    r_out = max(0, min(255, round(r_f * 255)))
    g_out = max(0, min(255, round(g_f * 255)))
    b_out = max(0, min(255, round(b_f * 255)))

    # Preserve alpha if present
    alpha = _extract_alpha(hex_color)
    result = f'#{r_out:02X}{g_out:02X}{b_out:02X}'
    return result + alpha if alpha else result


def adapt_color_to_page(
    hex_color: str,
    designed_page: str,
    actual_page: str,
    compress_dark: float,
    compress_light: float,
) -> str:
    """Adapt a single color from designed_page context to actual_page context.

    Preserves hue and HSL saturation. Adjusts lightness via binary search in
    the HLS L-channel to achieve the target sRGB luminance. This is the
    public API for child themes that want to call adaptation on custom data.

    Args:
        hex_color: The color to adapt (6 or 8 digit hex with #).
        designed_page: The page the color was designed against.
        actual_page: The target page background.
        compress_dark: Compression factor for colors darker than page.
        compress_light: Compression factor for colors lighter than page.

    Returns:
        Adapted hex color string.
    """
    if not hex_color or not isinstance(hex_color, str) or not hex_color.startswith('#'):
        return hex_color

    # Guard designed_page and actual_page (public API safety for child themes)
    if not designed_page or not isinstance(designed_page, str) or not designed_page.startswith('#'):
        return hex_color
    if not actual_page or not isinstance(actual_page, str) or not actual_page.startswith('#'):
        return hex_color

    try:
        # Get luminances
        lum_color = _get_luminance(hex_color)
        lum_designed = _get_luminance(designed_page)
        lum_actual = _get_luminance(actual_page)

        # Fast path: color IS the designed page → return actual page
        if abs(lum_color - lum_designed) < 0.001:
            # Preserve alpha from original color if present
            alpha = _extract_alpha(hex_color)
            return actual_page + alpha if alpha else actual_page

        # Compute signed distance from designed page
        distance = lum_color - lum_designed

        # Apply directional compression
        if distance < 0:
            # Color is darker than page
            adapted_distance = distance * compress_dark
        else:
            # Color is lighter than page
            adapted_distance = distance * compress_light

        # Target luminance
        target_lum = lum_actual + adapted_distance
        target_lum = max(0.0, min(1.0, target_lum))

        # Shift the color's lightness to reach target_lum
        return _shift_to_target_luminance(hex_color, target_lum)
    except (ValueError, TypeError):
        return hex_color


def _adapt_colors_in_dict(d: dict, designed_page: str, actual_page: str,
                          compress_dark: float, compress_light: float) -> dict:
    """Recursively adapt all hex color values in a config dict.

    Processes ALL string values starting with '#' (excluding '##' escape).
    Skips dd: expressions (they don't start with '#' — resolved later against
    the adapted palette). Skips non-string values and non-dict containers.

    This mirrors the pattern used by _dark_invert_colors_in_dict: both walk
    the same dict structure applying a color transform to every '#'-prefixed
    string. No key-name filtering is applied — all '#'-prefixed strings in
    the config schema are color values (verified against core_config.py).

    Args:
        d: Configuration dictionary to process.
        designed_page: The page background the colors were designed against.
        actual_page: The target page background.
        compress_dark: Compression factor for colors darker than page.
        compress_light: Compression factor for colors lighter than page.

    Returns:
        New dict with adapted color values.
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _adapt_colors_in_dict(v, designed_page, actual_page,
                                             compress_dark, compress_light)
        elif isinstance(v, str) and v.startswith('#') and not v.startswith('##'):
            result[k] = adapt_color_to_page(v, designed_page, actual_page,
                                           compress_dark, compress_light)
        else:
            result[k] = v
    return result


# --- SEMANTIC COLOR RESOLUTION ---

_ADMONITION_SHORTHANDS = frozenset([
    # Admonition types that can be used as shorthand references (dd:note:key).
    # EXCLUDES 'warning' and 'danger' because they collide with semantic palette keys.
    # For those, use explicit path: dd:admonitions.warning:key or dd:admonitions.danger:key
    'note', 'error', 'caution', 'hint', 'tip',
    'important', 'attention', 'seealso', 'admonition',
])


def _normalize_hex_with_alpha(hex_color: str) -> str:
    """Normalize a hex color: 3-digit -> 6-digit, 4-digit -> 8-digit, 6/8-digit unchanged."""
    clean = hex_color.lstrip('#')
    if len(clean) == 3:
        clean = ''.join([c * 2 for c in clean])
    elif len(clean) == 4:
        clean = ''.join([c * 2 for c in clean])
    return f'#{clean}'


def _split_hex_opacity(color_str: str) -> tuple:
    """Split a hex color string into its base color and opacity.

    Extracts the alpha channel from 8-digit (#RRGGBBAA) and 4-digit (#RGBA)
    hex colors, returning the base color and a normalized opacity string.

    This centralizes the opacity-extraction pattern previously duplicated
    throughout config_inited() for draft watermarks and part backgrounds.

    Args:
        color_str: A hex color string. Supports 3, 4, 6, or 8 digit formats
            with or without a leading '#'. None or empty strings are returned
            unchanged with opacity '1.0'.

    Returns:
        A tuple (base_color, opacity) where:
        - base_color: The color string without the alpha channel.
          For 8-digit input: '#RRGGBB'. For 4-digit input: '#RGB'.
          For 3/6-digit input: the original string. For invalid input:
          the original string, unchanged.
        - opacity: A string representation of the alpha value normalized
          to [0.0, 1.0], e.g. '0.27', '1.0'. Always '1.0' for non-alpha
          inputs.

    Examples:
        >>> _split_hex_opacity('#00000044')
        ('#000000', '0.27')
        >>> _split_hex_opacity('#FF0000')
        ('#FF0000', '1.0')
        >>> _split_hex_opacity('#FFF')
        ('#FFF', '1.0')
        >>> _split_hex_opacity(None)
        (None, '1.0')
        >>> _split_hex_opacity('')
        ('', '1.0')
    """
    if not color_str:
        return (color_str, "1.0")
    clean_hex = color_str.lstrip('#')
    if len(clean_hex) == 8:
        try:
            opacity = str(round(int(clean_hex[6:8], 16) / 255.0, 2))
        except ValueError:
            return (color_str, "1.0")
        return (f"#{clean_hex[:6]}", opacity)
    elif len(clean_hex) == 4:
        try:
            opacity = str(round(int(clean_hex[3] * 2, 16) / 255.0, 2))
        except ValueError:
            return (color_str, "1.0")
        return (f"#{clean_hex[:3]}", opacity)
    # 3-digit and 6-digit have no alpha channel
    return (color_str, "1.0")


def resolve_color(
    value: str,
    palette: dict,
    page_bg: str,
    current_section: str,
    current_dict: dict,
    theme_defaults: dict,
    core_config: dict,
    user_config: dict,
    resolve_stack: list = None,
    root_config: dict = None,
    wcag_level: float = 4.5,
    wcag_color_debug: bool = False,
) -> str:
    """Resolve a color expression to a static hex value.

    Handles:
    - Static hex pass-through: '#FF0000', '#FFF', '#FF000080'
    - Palette lookup: 'dd:primary'
    - Page background: 'dd:page'
    - Inline hex: 'dd:#FFCC0025:lighten:80'
    - Current config: 'dd:this:key'
    - Theme config: 'dd:theme:key'
    - Core config: 'dd:core:key'
    - User config: 'dd:user:key'
    - Admonition shorthand: 'dd:note:key' -> admonitions['note']['key']
    - Explicit path: 'dd:admonitions.note:key'
    - Operations: lighten, darken, contrast:fg, contrast:bg
    - Per-call WCAG level override: contrast:fg:primary:aaa (or any numeric ratio)
    - Circular dependency detection via resolve_stack

    Args:
        value: The color expression to resolve.
        palette: The semantic palette dictionary.
        page_bg: The global page background color.
        current_section: The name of the current config section (e.g., 'admonitions').
        current_dict: The current merged config dictionary.
        theme_defaults: The theme-level defaults dictionary.
        core_config: The core config manifest dictionary.
        user_config: The user-level config dictionary.
        resolve_stack: List of (section, key) tuples for circular dependency detection.
        wcag_level: The global minimum WCAG contrast ratio threshold (default 4.5 = AA).
            Theme authors can override per-call via the contrast operation's 4th argument.
        wcag_color_debug: If True, logs input/output colors for every WCAG contrast
            calculation. Useful for theme authors verifying corrections.

    Returns:
        A static hex color string (with '#') or '#ff0000' on error.
    """
    if resolve_stack is None:
        resolve_stack = []

    def _error(msg: str) -> str:
        logger.warning(f'[Doxtr Core] {msg}')
        return '#ff0000'

    def _resolve_palette_key(key: str) -> str:
        """Resolve a palette key, returning the color or error."""
        if key in palette:
            return palette[key]
        return _error(f"Semantic palette key '{key}' not found. Using error color #ff0000.")

    def _resolve_path(path: str, scope: str = None) -> str:
        """Resolve an explicit path like 'admonitions.note' with optional scope."""
        parts = path.split('.')
        base_key = parts[0]
        keys = parts[1:]

        # Determine which config to start from
        if scope == 'theme':
            if current_section not in theme_defaults:
                return _error(f"Cross-layer dependency: '{path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Core configs must not depend on theme configs.")
            cfg = theme_defaults.get(current_section, {})
        elif scope == 'core':
            if current_section not in core_config:
                return _error(f"Cross-layer dependency: '{path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Core configs must not depend on theme configs.")
            cfg = core_config.get(current_section, {})
        elif scope == 'user':
            if current_section in ('core', 'theme'):
                return _error(f"Cross-layer dependency: '{path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Theme configs must not depend on user configs.")
            cfg = user_config.get(current_section, {})
        else:
            cfg = current_dict

        # Navigate the path
        for part in keys:
            if isinstance(cfg, dict) and part in cfg:
                cfg = cfg[part]
            else:
                full_path = '.'.join([base_key] + keys)
                return _error(f"Key '{part}' not found in '{full_path}'. Use 'dd:core:<key>' for core config or 'dd:this:<key>' for current config.")

        return cfg

    def _apply_operation(color: str, op: str, op_arg: str = None) -> str:
        """Apply a color operation (lighten, darken, contrast).

        Contrast operation format:
          contrast:fg:<palette_key>[:<wcag_level>]
          contrast:bg:<palette_key>[:<wcag_level>]

        The optional 4th argument overrides the global WCAG level for this call only.
        Accepts a numeric ratio (e.g., ``7``) or a sentinel (``aaa`` → 7, ``aa`` → 4.5).
        Example: ``dd:primary:contrast:fg:primary:aaa``
        """
        if op == 'lighten':
            try:
                pct = float(op_arg)
                return adjust_hex_brightness(color, pct)
            except (ValueError, TypeError):
                return _error(f"Invalid lighten argument '{op_arg}'. Expected a number.")
        elif op == 'darken':
            try:
                pct = float(op_arg)
                return adjust_hex_brightness(color, -pct)
            except (ValueError, TypeError):
                return _error(f"Invalid darken argument '{op_arg}'. Expected a number.")
        elif op == 'contrast':
            if op_arg is None:
                return _error(f"'contrast' operation requires a palette key suffix (e.g., 'contrast:fg:primary').")
            # Parse 'fg:<palette_key>[:<wcag_override>]' or 'bg:<palette_key>[:<wcag_override>]' or just '<target>'
            contrast_parts = op_arg.split(':')
            contrast_target = contrast_parts[0]
            contrast_palette_key = contrast_parts[1] if len(contrast_parts) > 1 else None
            wcag_override = contrast_parts[2] if len(contrast_parts) > 2 else None

            # Resolve per-call WCAG level override
            effective_wcag = wcag_level
            if wcag_override:
                wcag_override_lower = wcag_override.lower()
                if wcag_override_lower == 'aaa':
                    effective_wcag = 7.0
                elif wcag_override_lower == 'aa':
                    effective_wcag = 4.5
                else:
                    try:
                        effective_wcag = float(wcag_override)
                    except (ValueError, TypeError):
                        return _error(f"Invalid WCAG override '{wcag_override}'. Use 'aa', 'aaa', or a numeric ratio.")

            if contrast_target == 'fg':
                # Adjust foreground to contrast against background
                desired_fg = _resolve_palette_key(contrast_palette_key) if contrast_palette_key else color
                desired_bg = color
            elif contrast_target == 'bg':
                # Adjust background to contrast against foreground
                desired_bg = _resolve_palette_key(contrast_palette_key) if contrast_palette_key else color
                desired_fg = color
            else:
                return _error(f"Unknown contrast target '{contrast_target}'. Use 'fg' or 'bg'.")

            # Extract alpha for reapplication
            alpha = ''
            clean_color = color.lstrip('#')
            if len(clean_color) == 8:
                alpha = clean_color[6:8]

            result = get_highest_contrast_color(
                desired_fg, desired_bg,
                target='foreground' if contrast_target == 'fg' else 'background',
                wcag_level=effective_wcag,
                color_debug=wcag_color_debug,
            )
            if result is None:
                return _error(f"Contrast calculation failed for '{value}'.")

            # Reapply alpha if present
            if alpha:
                return f"{result[:7]}{alpha}"
            return result
        elif op in _custom_color_operations:
            try:
                return _custom_color_operations[op](color, op_arg or '')
            except Exception as e:
                return _error(f"Custom operation '{op}' failed: {e}")
        else:
            return _error(f"Unknown operation '{op}'. Use 'lighten:<n>', 'darken:<n>', or 'contrast:<target>:<key>[:<wcag_override>]'.")

    # --- Resolution ---

    # 1. Static hex pass-through
    clean = value.lstrip('#')
    if len(clean) in (3, 4, 6, 8) and all(c in '0123456789ABCDEFabcdef' for c in clean):
        return _normalize_hex_with_alpha(value)

    # 2. Require 'dd:' prefix for dynamic expressions
    if not value.startswith('dd:'):
        return _error(f"Invalid color value '{value}'. Use a hex color or a 'dd:' expression.")

    expr = value[3:]  # Remove 'dd:' prefix

    # 3. Check for inline hex: dd:#FFCC0025:lighten:80
    if expr.startswith('#'):
        hex_part = ''
        remaining = ''
        i = 1  # Start after the #
        while i <= len(expr):
            if i > 8:
                break
            if i < len(expr) and expr[i] not in '0123456789ABCDEFabcdef':
                break
            i += 1
        hex_part = expr[1:i]
        remaining = expr[i:]

        if hex_part and (len(hex_part) in (3, 4, 6, 8)):
            base_color = f'#{hex_part}'
            if remaining.startswith(':'):
                op_parts = remaining[1:].split(':')
                op = op_parts[0] if len(op_parts) > 0 else ''
                op_arg = op_parts[1] if len(op_parts) > 1 else None
                return _apply_operation(base_color, op, op_arg)
            return _normalize_hex_with_alpha(base_color)

    # 4. Check for 'page' ref (standalone or with operation)
    if expr == 'page':
        return page_bg

    # 5. Check for palette key (standalone or with operation)
    if ':' not in expr:
        if expr in palette:
            return palette[expr]
        return _error(f"Semantic palette key '{expr}' not found. Using error color #ff0000.")

    # 6. Check if first part is 'page' with operation
    first_colon = expr.index(':')
    first_part = expr[:first_colon]
    rest_expr = expr[first_colon + 1:]

    if first_part == 'page':
        if rest_expr:
            op_parts = rest_expr.split(':', 1)
            op = op_parts[0]
            op_arg = op_parts[1] if len(op_parts) > 1 else None
            return _apply_operation(page_bg, op, op_arg)
        return page_bg

    # 7. Check for admonition shorthand collision (BEFORE palette check)
    if first_part in _ADMONITION_SHORTHANDS:
        if rest_expr:
            # Warn only on genuine ambiguity: key is in both palette AND _ADMONITION_SHORTHANDS.
            # Normal shorthand use (e.g. dd:note:title_background_color) is not ambiguous — log at debug only.
            # Split rest to get key and operation (also used in warning message below)
            key_parts = rest_expr.split(':', 1)
            key = key_parts[0]
            op_str = key_parts[1] if len(key_parts) > 1 else None

            if first_part in palette:
                logger.warning(
                    f"[Doxtr Core] '{first_part}' is both a palette key and an admonition type. "
                    f"Resolving as admonition shorthand. "
                    f"To reference admonitions explicitly, use 'dd:admonitions.{first_part}:{key}'. "
                    f"To use the palette color instead, write 'dd:{first_part}' (no key suffix)."
                )
            else:
                logger.debug(
                    f"[Doxtr Core] Resolving '{first_part}' as admonition shorthand "
                    f"(dd:{first_part}:{rest_expr})."
                )

            # Look up in root config's admonitions[ref]
            adm_root = root_config or current_dict
            adm_cfg = adm_root.get('admonitions', {})
            if first_part not in adm_cfg:
                return _error(f"Admonition type '{first_part}' not found. Use 'dd:admonitions.{first_part}' for explicit path.")
            val = adm_cfg[first_part].get(key) if isinstance(adm_cfg[first_part], dict) else None

            if val is None:
                return _error(f"Key '{key}' not found in 'admonitions[{first_part}]'. Use 'dd:admonitions.{first_part}[key]' for explicit path.")

            if isinstance(val, str) and val.startswith('dd:'):
                stack_key = (current_section, f"admonitions.{first_part}.{key}")
                if stack_key in resolve_stack:
                    return _error(f"Circular dependency detected: '{value}' in '{current_section}.admonitions.{first_part}.{key}'. Color resolution aborted.")
                resolve_stack.append(stack_key)
                try:
                    resolved = resolve_color(val, palette, page_bg, current_section, current_dict, theme_defaults, core_config, user_config, resolve_stack, root_config)
                finally:
                    resolve_stack.pop()
                val = resolved

            # Apply operation if present
            if op_str:
                op_parts = op_str.split(':', 1)
                op = op_parts[0]
                op_arg = op_parts[1] if len(op_parts) > 1 else None
                val = _apply_operation(val, op, op_arg)

            return val
        else:
            # Standalone: treat as palette key
            return palette.get(first_part, _error(f"Semantic palette key '{first_part}' not found. Using error color #ff0000."))

    # 8. Check if first part is a palette key with operation
    if first_part in palette:
        base_color = palette[first_part]
        if rest_expr:
            op_parts = rest_expr.split(':', 1)
            op = op_parts[0]
            op_arg = op_parts[1] if len(op_parts) > 1 else None
            return _apply_operation(base_color, op, op_arg)
        return base_color

    # 9. Split ref and rest
    ref, rest = expr.split(':', 1)

    # 10. Check for explicit path (contains '.')
    if '.' in ref:
        path_parts = ref.split('.')
        keys = path_parts[1:]
        # Determine scope from [scope] suffix
        scope = None
        if keys and keys[-1].startswith('[') and keys[-1].endswith(']'):
            scope = keys[-1][1:-1]
            keys = keys[:-1]
        full_path = '.'.join(path_parts)

        if scope == 'theme':
            if current_section not in theme_defaults:
                return _error(f"Cross-layer dependency: '{full_path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Core configs must not depend on theme configs.")
            cfg = theme_defaults.get(current_section, {})
        elif scope == 'core':
            if current_section not in core_config:
                return _error(f"Cross-layer dependency: '{full_path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Core configs must not depend on theme configs.")
            cfg = core_config.get(current_section, {})
        elif scope == 'user':
            if current_section in ('core', 'theme'):
                return _error(f"Cross-layer dependency: '{full_path}' in '{current_section}.{keys[-1] if keys else ''}' references a layer above the current one. Theme configs must not depend on user configs.")
            cfg = user_config.get(current_section, {})
        else:
            cfg = current_dict

        for key in keys:
            if isinstance(cfg, dict) and key in cfg:
                cfg = cfg[key]
            else:
                return _error(f"Key '{key}' not found in '{full_path}'. Use 'dd:core:<key>' for core config or 'dd:this:<key>' for current config.")
        return cfg

    # 11. Scope resolution — common pattern for this/theme/core/user
    def _resolve_scope(cfg, scope_ref, rest_str, value_str):
        """Look up key in cfg, resolve dd: values, apply operations."""
        # Split rest by ':' — first part is key, rest is operation
        parts = rest_str.split(':', 1)
        key = parts[0]
        op_str = parts[1] if len(parts) > 1 else None

        if key not in cfg:
            return _error(f"Key '{key}' not found in '{scope_ref}'. Use 'dd:core:<key>' for core config or 'dd:this:<key>' for current config.")

        val = cfg[key]

        # Recursively resolve dd: values
        if isinstance(val, str) and val.startswith('dd:'):
            stack_key = (current_section, key)
            if stack_key in resolve_stack:
                return _error(f"Circular dependency detected: '{value_str}' in '{current_section}.{key}'. Color resolution aborted.")
            resolve_stack.append(stack_key)
            try:
                resolved = resolve_color(val, palette, page_bg, current_section, current_dict, theme_defaults, core_config, user_config, resolve_stack)
            finally:
                resolve_stack.pop()
            val = resolved

        # Apply operation if present
        if op_str:
            op_parts = op_str.split(':', 1)
            op = op_parts[0]
            op_arg = op_parts[1] if len(op_parts) > 1 else None
            val = _apply_operation(val, op, op_arg)

        return val

    if ref == 'this':
        return _resolve_scope(current_dict, current_section, rest, value)

    elif ref == 'theme':
        if current_section not in theme_defaults:
            return _error(f"Cross-layer dependency: 'theme' in '{current_section}.{rest}' references a layer above the current one. Core configs must not depend on theme configs.")
        return _resolve_scope(theme_defaults.get(current_section, {}), f"theme.{current_section}", rest, value)

    elif ref == 'core':
        if current_section not in core_config:
            return _error(f"Cross-layer dependency: 'core' in '{current_section}.{rest}' references a layer above the current one. Core configs must not depend on theme configs.")
        return _resolve_scope(core_config.get(current_section, {}), f"core.{current_section}", rest, value)

    elif ref == 'user':
        if current_section in ('core', 'theme'):
            return _error(f"Cross-layer dependency: 'user' in '{current_section}.{rest}' references a layer above the current one. Theme configs must not depend on user configs.")
        return _resolve_scope(user_config.get(current_section, {}), f"user.{current_section}", rest, value)

    # 12. Unknown reference — error
    return _error(f"Invalid color expression '{value}'. Use 'dd:<ref>[:<operation>[:<arg>]]' format. Example: dd:primary, dd:info:lighten:80, dd:page:contrast:fg:primary")


def resolve_all_colors(
    config_dict: dict,
    palette: dict,
    page_bg: str,
    section_name: str,
    theme_defaults: dict,
    core_config: dict,
    user_config: dict,
    resolve_stack: list = None,
    root_config: dict = None,
    wcag_level: float = 4.5,
    wcag_color_debug: bool = False,
) -> None:
    """Recursively resolve all 'dd:' color expressions in a config dict.

    Walks through config_dict, resolves every string value starting with 'dd:',
    and replaces it with the static hex result.

    Args:
        config_dict: The config dictionary to process.
        palette: The semantic palette dictionary.
        page_bg: The global page background color.
        section_name: The name of the current config section.
        theme_defaults: The theme-level defaults dictionary.
        core_config: The core config manifest dictionary.
        user_config: The user-level config dictionary.
        resolve_stack: List of (section, key) tuples for circular dependency detection.
        root_config: The top-level config dict for sibling section lookups.
        wcag_level: The global minimum WCAG contrast ratio threshold (default 4.5 = AA).
        wcag_color_debug: If True, logs input/output colors for every WCAG contrast
            calculation. Useful for theme authors verifying corrections.
    """
    if resolve_stack is None:
        resolve_stack = []
    if root_config is None:
        root_config = config_dict

    items = list(config_dict.items())
    for key, value in items:
        if isinstance(value, str) and value.startswith('dd:'):
            stack_key = (section_name, key)
            if stack_key in resolve_stack:
                logger.warning(f"[Doxtr Core] Circular dependency detected: '{value}' in '{section_name}.{key}'. Color resolution aborted.")
                config_dict[key] = '#ff0000'
                continue

            resolve_stack.append(stack_key)
            try:
                resolved = resolve_color(
                    value, palette, page_bg, section_name, config_dict,
                    theme_defaults, core_config, user_config, resolve_stack, root_config,
                    wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
                )
            finally:
                resolve_stack.pop()

            if resolved is not None:
                config_dict[key] = resolved
        elif isinstance(value, dict):
            resolve_all_colors(
                value, palette, page_bg, f"{section_name}.{key}",
                theme_defaults, core_config, user_config, resolve_stack, root_config,
                wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
            )