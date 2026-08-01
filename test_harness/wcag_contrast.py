"""
Standalone WCAG 2.1 Contrast Ratio Calculator

This module provides a self-contained implementation of the WCAG 2.1 contrast
ratio calculation, independent of any Sphinx or Doxtr extension code.

WCAG 2.1 Contrast Ratio Formula (per https://www.w3.org/TR/WCAG21/#contrast-minimum):

    Contrast Ratio = (L1 + 0.05) / (L2 + 0.05)

    Where:
        L1 = relative luminance of the lighter color
        L2 = relative luminance of the darker color

    Relative Luminance (per https://www.w3.org/TR/WCAG21/#dfn-relative-luminance):

        For each sRGB color channel (R, G, B) normalized to 0-1:

            if channel <= 0.03928:
                linear = channel / 12.92
            else:
                linear = ((channel + 0.055) / 1.055) ** 2.4

        L = 0.2126 * R_linear + 0.7152 * G_linear + 0.0722 * B_linear

WCAG Thresholds:
    - Level AA (normal text):  4.5:1
    - Level AA (large text):   3:1
    - Level AAA (normal text): 7:1
    - Level AAA (large text):  4.5:1

    "Large text" is defined as 18pt (24px) regular or 14pt (18.66px) bold.

Usage:
    >>> from wcag_contrast import wcag_contrast_ratio, wcag_passes
    >>> wcag_contrast_ratio('#000000', '#FFFFFF')
    21.0
    >>> wcag_passes('#000000', '#FFFFFF', 'AA', 'normal')
    True
"""


# ---------------------------------------------------------------------------
# Color Parsing
# ---------------------------------------------------------------------------

def parse_hex_color(hex_color: str) -> tuple[int, int, int] | None:
    """Parse a hex color string to (R, G, B) integers (0-255).

    Supports:
        - 3-digit: '#RGB'  -> '#RRGGBB'
        - 4-digit: '#RGBA' -> '#RRGGBB' (alpha discarded)
        - 6-digit: '#RRGGBB'
        - 8-digit: '#RRGGBBAA' (alpha discarded)

    Args:
        hex_color: A hex color string with or without leading '#'.

    Returns:
        A (R, G, B) tuple with values in [0, 255], or None on failure.
    """
    if not hex_color:
        return None

    clean = hex_color.lstrip('#')

    # Expand short forms
    if len(clean) == 3:
        clean = ''.join(c * 2 for c in clean)
    elif len(clean) == 4:
        # 4-digit: discard alpha (the 4th digit)
        clean = ''.join(c * 2 for c in clean[:3])
    elif len(clean) == 8:
        # 8-digit: discard alpha (last 2 digits)
        clean = clean[:6]

    # Validate
    if len(clean) != 6 or not all(c in '0123456789ABCDEFabcdef' for c in clean):
        return None

    r = int(clean[0:2], 16)
    g = int(clean[2:4], 16)
    b = int(clean[4:6], 16)

    return (r, g, b)


# ---------------------------------------------------------------------------
# Relative Luminance
# ---------------------------------------------------------------------------

def _linearize(channel: int) -> float:
    """Convert a single sRGB channel (0-255) to its linear (gamma-corrected) value.

    Per WCAG 2.1:

        sRGB = channel / 255
        if sRGB <= 0.03928:
            linear = sRGB / 12.92
        else:
            linear = ((sRGB + 0.055) / 1.055) ** 2.4
    """
    srgb = channel / 255.0
    if srgb <= 0.03928:
        return srgb / 12.92
    return ((srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float | None:
    """Calculate the relative luminance of a hex color per WCAG 2.1.

    L = 0.2126 * R_linear + 0.7152 * G_linear + 0.0722 * B_linear

    Args:
        hex_color: A hex color string (with or without '#').

    Returns:
        The relative luminance value (0.0 = black, 1.0 = white), or None
        if the input is invalid.
    """
    rgb = parse_hex_color(hex_color)
    if rgb is None:
        return None

    r_lin = _linearize(rgb[0])
    g_lin = _linearize(rgb[1])
    b_lin = _linearize(rgb[2])

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


# ---------------------------------------------------------------------------
# Contrast Ratio
# ---------------------------------------------------------------------------

def wcag_contrast_ratio(color1: str, color2: str) -> float | None:
    """Calculate the WCAG 2.1 contrast ratio between two colors.

    Formula: (L1 + 0.05) / (L2 + 0.05)
    where L1 >= L2 (lighter / darker).

    The ratio ranges from 1.0 (identical colors) to 21.0 (black vs. white).

    Args:
        color1: First hex color (with or without '#').
        color2: Second hex color (with or without '#').

    Returns:
        The contrast ratio as a float, or None if either color is invalid.

    Examples:
        >>> wcag_contrast_ratio('#000000', '#FFFFFF')
        21.0
        >>> wcag_contrast_ratio('#FFFFFF', '#000000')
        21.0
        >>> wcag_contrast_ratio('#FFFFFF', '#FFFFFF')
        1.0
        >>> wcag_contrast_ratio('#767676', '#FFFFFF')
        4.479...
    """
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)

    if l1 is None or l2 is None:
        return None

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Pass / Fail Checks
# ---------------------------------------------------------------------------

# WCAG thresholds
WCAG_AA_NORMAL = 4.5   # Normal text (under 18pt regular / 14pt bold)
WCAG_AA_LARGE  = 3.0   # Large text (18pt+ regular / 14pt+ bold)
WCAG_AAA_NORMAL = 7.0  # Normal text, AAA level
WCAG_AAA_LARGE  = 4.5  # Large text, AAA level


def get_highest_contrast_color(
    foreground_color: str,
    background_color: str,
    target: str = 'foreground',
    adjust_percent: float = 0.0,
) -> str | None:
    """Auto-calculates a WCAG 4.5:1 contrast-safe color.

    Given two colors, this function determines which one should be adjusted
    to meet WCAG AA accessibility standards (minimum 4.5:1 contrast ratio).
    It iteratively lightens or darkens the target color until the threshold
    is met, falling back to pure black or white if necessary.

    Args:
        foreground_color: The foreground (text/icon) hex color.
        background_color: The background hex color.
        target: Which color to adjust. 'foreground' or 'background'.
        adjust_percent: Optional post-adjustment percentage.

    Returns:
        A hex color string (with '#') that meets the 4.5:1 WCAG AA threshold,
        or the original ``target_color`` if the threshold is already met.
        Returns ``None`` if either input is empty or invalid.
    """
    if not foreground_color or not background_color:
        return None

    if target == 'foreground':
        target_color = foreground_color
        fixed_color = background_color
    else:
        target_color = background_color
        fixed_color = foreground_color

    lum_fixed = relative_luminance(fixed_color)
    lum_target = relative_luminance(target_color)
    candidate = target_color

    if (max(lum_fixed, lum_target) - min(lum_fixed, lum_target)) > 0 and (
        (max(lum_fixed, lum_target) + 0.05) / (min(lum_fixed, lum_target) + 0.05)
    ) < 4.5:
        direction = -1 if lum_fixed > 0.17912 else 1
        for i in range(1, 101):
            test_color = _adjust_brightness(target_color, i * direction)
            lum_test = relative_luminance(test_color)
            if (max(lum_fixed, lum_test) + 0.05) / (min(lum_fixed, lum_test) + 0.05) >= 4.5:
                candidate = test_color
                break
        else:
            clean = target_color.lstrip('#')
            base = "#000000" if direction == -1 else "#FFFFFF"
            if len(clean) == 8:
                candidate = base + clean[6:8]
            elif len(clean) == 4:
                candidate = base + (clean[3] * 2)
            else:
                candidate = base

    if adjust_percent != 0.0:
        return _adjust_brightness(candidate, adjust_percent)
    return candidate


def wcag_passes(
    color1: str,
    color2: str,
    level: str = 'AA',
    text_size: str = 'normal',
) -> bool:
    """Check if two colors pass a WCAG contrast requirement.

    Args:
        color1: First hex color.
        color2: Second hex color.
        level: WCAG level — 'AA' or 'AAA'.
        text_size: Text size category — 'normal' or 'large'.

    Returns:
        True if the contrast ratio meets or exceeds the threshold.

    Examples:
        >>> wcag_passes('#000000', '#FFFFFF', 'AA', 'normal')
        True
        >>> wcag_passes('#767676', '#FFFFFF', 'AA', 'normal')
        False
        >>> wcag_passes('#767676', '#FFFFFF', 'AA', 'large')
        True
    """
    ratio = wcag_contrast_ratio(color1, color2)
    if ratio is None:
        return False

    if level == 'AA':
        threshold = WCAG_AA_LARGE if text_size == 'large' else WCAG_AA_NORMAL
    elif level == 'AAA':
        threshold = WCAG_AAA_LARGE if text_size == 'large' else WCAG_AAA_NORMAL
    else:
        raise ValueError(f"Unknown WCAG level: {level!r}. Use 'AA' or 'AAA'.")

    return ratio >= threshold


# ---------------------------------------------------------------------------
# Human-Readable Output
# ---------------------------------------------------------------------------

def wcag_label(ratio: float) -> str:
    """Return a human-readable WCAG accessibility label for a contrast ratio.

    Args:
        ratio: The contrast ratio value.

    Returns:
        A string describing which WCAG levels the ratio passes.
    """
    parts = []
    if ratio >= WCAG_AAA_NORMAL:
        parts.append('AAA (normal)')
    if ratio >= WCAG_AAA_LARGE:
        parts.append('AAA (large)')
    if ratio >= WCAG_AA_NORMAL:
        parts.append('AA (normal)')
    if ratio >= WCAG_AA_LARGE:
        parts.append('AA (large)')
    if not parts:
        return 'FAIL (below AA large-text threshold)'
    return 'PASS: ' + ', '.join(parts)


def wcag_report(color1: str, color2: str) -> str:
    """Generate a full WCAG contrast report string for two colors.

    Args:
        color1: First hex color.
        color2: Second hex color.

    Returns:
        A formatted report string showing luminance values, ratio, and pass/fail.
    """
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    ratio = wcag_contrast_ratio(color1, color2)

    lines = [
        f"WCAG 2.1 Contrast Report",
        f"{'=' * 40}",
        f"  Color 1: {color1}  (L = {l1:.4f})",
        f"  Color 2: {color2}  (L = {l2:.4f})",
        f"  Contrast Ratio: {ratio:.4f}:1",
        f"  {wcag_label(ratio)}",
    ]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Semantic Color Resolution (for the dd: syntax)
# ---------------------------------------------------------------------------

# The Doxtr core semantic palette (mirrors DOXTR_SEMANTIC_PALETTE)
SEMANTIC_PALETTE = {
    'primary':   '#2E3959',   # Navy
    'secondary': '#A64985',   # Magenta
    'info':      '#9BE2F2',   # Teal
    'success':   '#66D98E',   # Green
    'warning':   '#EA9B62',   # Coral
    'danger':    '#F2545B',   # Red
    'page':      '#FFFFFF',   # Page background
}

# Admonition types that can be used as shorthand
_ADMONITION_SHORTHANDS = frozenset([
    'note', 'warning', 'danger', 'error', 'hint', 'tip',
    'important', 'attention', 'seealso',
])

# Minimal core config for resolving dd: expressions (just the colors we need)
_CORE_ADMONITIONS = {
    'note': {
        'title_background_color': 'dd:info',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'warning': {
        'title_background_color': 'dd:warning',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'danger': {
        'title_background_color': 'dd:danger',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'error': {
        'title_background_color': 'dd:danger',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'hint': {
        'title_background_color': 'dd:success',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'tip': {
        'title_background_color': 'dd:success',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'important': {
        'title_background_color': 'dd:secondary',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'attention': {
        'title_background_color': 'dd:warning',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
    'seealso': {
        'title_background_color': 'dd:primary',
        'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
    },
}


def _adjust_brightness(hex_color: str, percentage: float) -> str:
    """Adjust the brightness of a hex color by a percentage.

    Positive percentage lightens, negative darkens.

    Args:
        hex_color: Hex color string (with or without '#').
        percentage: Percentage to adjust (-100 to +100).

    Returns:
        Adjusted hex color string with '#'.
    """
    clean = hex_color.lstrip('#')
    has_alpha = False
    alpha = ''

    if len(clean) == 8:
        has_alpha = True
        alpha = clean[6:8]
        clean = clean[:6]
    elif len(clean) == 4:
        clean = ''.join(c * 2 for c in clean[:3])

    r = int(clean[0:2], 16)
    g = int(clean[2:4], 16)
    b = int(clean[4:6], 16)

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
        return f'#{r:02X}{g:02X}{b:02X}{alpha}'
    return f'#{r:02X}{g:02X}{b:02X}'


def _resolve_color_expression(expr: str, palette: dict = None, _resolve_context: str = None) -> str | None:
    """Resolve a single dd: color expression to a static hex color.

    Supports:
        - Static hex: '#FF0000'
        - Palette key: 'dd:primary'
        - Page background: 'dd:page'
        - Admonition shorthand: 'dd:hint' (resolves to success = '#66D98E')
        - Admonition key: 'dd:hint:title_background_color'
        - Operations: ':lighten:N', ':darken:N', ':contrast:fg:primary'
          ':contrast:bg:primary'

    Args:
        expr: The color expression (with or without 'dd:' prefix).
        palette: Optional custom palette dict. Defaults to SEMANTIC_PALETTE.
        _resolve_context: The current admonition type context for 'dd:this:' resolution.

    Returns:
        A static hex color string with '#', or None on failure.
    """
    if palette is None:
        palette = SEMANTIC_PALETTE

    def _apply_op(color: str, op: str, op_arg: str | None) -> str | None:
        """Apply a color operation."""
        if op == 'lighten':
            try:
                return _adjust_brightness(color, float(op_arg))
            except (ValueError, TypeError):
                return None
        elif op == 'darken':
            try:
                return _adjust_brightness(color, -float(op_arg))
            except (ValueError, TypeError):
                return None
        elif op == 'contrast':
            # op_arg is like 'fg:primary' or 'bg:primary'
            if op_arg is None:
                return None
            if ':' not in op_arg:
                return None
            target, pk = op_arg.split(':', 1)
            if target == 'fg':
                desired_fg = palette.get(pk, color) if pk else color
                desired_bg = color
            elif target == 'bg':
                desired_bg = palette.get(pk, color) if pk else color
                desired_fg = color
            else:
                return None
            result = get_highest_contrast_color(desired_fg, desired_bg,
                                                 target='foreground'
                                                 if target == 'fg'
                                                 else 'background')
            return result
        return None

    # No dd: prefix — pass through as-is
    if not expr.startswith('dd:'):
        return expr

    inner = expr[3:]  # Remove 'dd:'

    # Check for inline hex: dd:#FFCC0025:lighten:80
    if inner.startswith('#'):
        hex_part = ''
        rest = ''
        i = 1
        while i <= len(inner):
            if i > 8:
                break
            if i < len(inner) and inner[i] not in '0123456789ABCDEFabcdef':
                break
            i += 1
        hex_part = inner[1:i]
        rest = inner[i:]

        if hex_part and len(hex_part) in (3, 4, 6, 8):
            base = f'#{hex_part}'
            if rest.startswith(':'):
                op_parts = rest[1:].split(':', 1)
                op = op_parts[0]
                op_arg = op_parts[1] if len(op_parts) > 1 else None
                return _apply_op(base, op, op_arg)
            return base

    # Standalone 'page'
    if inner == 'page':
        return palette.get('page', '#FFFFFF')

    # Check if it's a palette key (no colon)
    if ':' not in inner:
        return palette.get(inner, None)

    # Check for admonition shorthand (e.g., 'hint:title_background_color')
    first_part = inner.split(':')[0]
    if first_part in _ADMONITION_SHORTHANDS:
        # Look up in core admonitions
        adm = _CORE_ADMONITIONS.get(first_part, {})
        keys = inner.split(':')[1:]
        val = adm.get(keys[0]) if keys else None

        if val is None:
            return None

        # If the value is itself a dd: expression, resolve it
        if val.startswith('dd:'):
            val = _resolve_color_expression(val, palette)

        # Apply operation if present
        if len(keys) > 1:
            op_str = ':'.join(keys[1:])
            op_parts = op_str.split(':', 1)
            op = op_parts[0]
            op_arg = op_parts[1] if len(op_parts) > 1 else None
            return _apply_op(val, op, op_arg)

        return val

    # Split ref and rest (first colon separates ref from the rest)
    colon_pos = inner.index(':')
    ref = inner[:colon_pos]
    rest = inner[colon_pos + 1:]

    # Palette key with operation (e.g., 'primary:lighten:80')
    if ref in palette:
        base = palette[ref]
        # rest is 'lighten:80' (colon already consumed by split)
        op_parts = rest.split(':', 1)
        op = op_parts[0]
        op_arg = op_parts[1] if len(op_parts) > 1 else None
        return _apply_op(base, op, op_arg)

    # 'this:' — resolve from current admonition context
    if ref == 'this':
        key = rest.split(':')[0]
        # If we have a context, look it up in that specific admonition
        if _resolve_context and _resolve_context in _CORE_ADMONITIONS:
            adm_cfg = _CORE_ADMONITIONS[_resolve_context]
            if key in adm_cfg:
                val = adm_cfg[key]
                if val.startswith('dd:'):
                    val = _resolve_color_expression(val, palette, _resolve_context=_resolve_context)
                # Check for operation
                op_parts = rest.split(':')[1:]  # ['contrast', 'fg', 'primary']
                if len(op_parts) > 0:
                    op = op_parts[0]  # 'contrast'
                    op_arg = ':'.join(op_parts[1:]) if len(op_parts) > 1 else None  # 'fg:primary'
                    return _apply_op(val, op, op_arg)
                return val
        # Fallback: search all admonitions
        for adm_type, adm_cfg in _CORE_ADMONITIONS.items():
            if key in adm_cfg:
                val = adm_cfg[key]
                if val.startswith('dd:'):
                    val = _resolve_color_expression(val, palette, _resolve_context=_resolve_context)
                op_parts = rest.split(':')[1:]
                if len(op_parts) > 0:
                    op = op_parts[0]
                    op_arg = ':'.join(op_parts[1:]) if len(op_parts) > 1 else None
                    return _apply_op(val, op, op_arg)
                return val
        return None

    # 'page:' with operation
    if ref == 'page':
        op_parts = rest.split(':', 1)
        op = op_parts[0]
        op_arg = op_parts[1] if len(op_parts) > 1 else None
        return _apply_op(palette.get('page', '#FFFFFF'), op, op_arg)

    # Unknown expression
    return None


def _resolve_admonition_colors(admonition_type: str) -> tuple[str, str] | None:
    """Resolve the title_background_color and title_font_color for an admonition type.

    This uses the core config's color resolution logic to determine the
    final hex values.

    Args:
        admonition_type: The admonition type (e.g., 'hint', 'note', 'warning').

    Returns:
        A (title_background_color, title_font_color) tuple, or None on failure.
    """
    adm = _CORE_ADMONITIONS.get(admonition_type)
    if adm is None:
        return None

    bg_expr = adm.get('title_background_color')
    fg_expr = adm.get('title_font_color')

    if bg_expr is None:
        return None

    # Resolve background color
    bg_color = _resolve_color_expression(bg_expr)
    if bg_color is None:
        return None

    # Resolve foreground color (may reference the background)
    fg_color = None
    if fg_expr:
        fg_color = _resolve_color_expression(fg_expr, _resolve_context=admonition_type)

    return (bg_color, fg_color)


# ---------------------------------------------------------------------------
# Convenience: get colors for a specific element from core config
# ---------------------------------------------------------------------------

def get_admonition_colors(admonition_type: str) -> tuple[str, str] | None:
    """Get the resolved title_background_color and title_font_color for an admonition.

    Args:
        admonition_type: The admonition type (e.g., 'hint', 'note', 'warning').

    Returns:
        A (bg_color, fg_color) tuple of hex strings, or None on failure.
    """
    return _resolve_admonition_colors(admonition_type)
