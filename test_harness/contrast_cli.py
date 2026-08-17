#!/usr/bin/env python3
"""
WCAG Contrast Ratio CLI Tool

Quickly evaluate the contrast ratio between two colors.

Usage:
    # Two hex colors:
    python contrast_cli.py '#000000' '#FFFFFF'

    # Two hex colors without # prefix:
    python contrast_cli.py 000000 FFFFFF

    # Semantic color syntax (resolves dd: expressions):
    python contrast_cli.py 'dd:primary' 'dd:page'
    python contrast_cli.py 'dd:success' 'dd:this:title_background_color:contrast:fg:primary'

    # Admonition shorthand:
    python contrast_cli.py 'dd:hint:title_background_color' 'dd:hint:title_font_color'

    # Short hex:
    python contrast_cli.py '#F00' '#FFF'

Exit codes:
    0  Contrast passes WCAG AA (normal text, 4.5:1)
    1  Contrast fails WCAG AA
    2  Invalid input
"""

import sys
import os

# Allow importing from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wcag_contrast import (
    wcag_contrast_ratio,
    wcag_passes,
    wcag_report,
    wcag_label,
    parse_hex_color,
    _resolve_color_expression,
    get_admonition_colors,
    relative_luminance,
)


def resolve_color_input(raw: str) -> str:
    """Resolve a color input to a static hex string.

    Tries:
        1. Static hex pass-through ('#FF0000', '#FFF', '#FF000080')
        2. Semantic dd: expression resolution ('dd:primary', 'dd:success:lighten:80')
        3. Admonition shorthand ('dd:hint:title_background_color')

    Args:
        raw: The raw color input string.

    Returns:
        A resolved hex color string (with '#').

    Raises:
        ValueError: If the input cannot be resolved.
    """
    # Strip whitespace and quotes
    raw = raw.strip().strip("'\"")

    # Try static hex first
    if raw.startswith('#'):
        rgb = parse_hex_color(raw)
        if rgb is not None:
            return raw

    # Try dd: expression resolution
    if raw.startswith('dd:'):
        resolved = _resolve_color_expression(raw)
        if resolved is not None:
            return resolved
        raise ValueError(f"Cannot resolve dd: expression: {raw!r}")

    # Try without # prefix as hex
    if len(raw) in (3, 4, 6, 8) and all(c in '0123456789ABCDEFabcdef' for c in raw):
        return f'#{raw}'

    raise ValueError(f"Cannot parse color: {raw!r}. Use hex (#RRGGBB) or dd: expression.")


def print_separator():
    print("-" * 52)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nUsage:")
        print("  python contrast_cli.py <color1> <color2> [level] [text_size]")
        print("\nArguments:")
        print("  color1       First color (hex or dd: expression)")
        print("  color2       Second color (hex or dd: expression)")
        print("  level        WCAG level: 'AA' (default) or 'AAA'")
        print("  text_size    Text size: 'normal' (default) or 'large'")
        print("\nExamples:")
        print("  python contrast_cli.py '#000000' '#FFFFFF'")
        print("  python contrast_cli.py 'dd:primary' 'dd:page'")
        print("  python contrast_cli.py 'dd:hint:title_background_color' 'dd:hint:title_font_color'")
        print("  python contrast_cli.py '#66D98E' 'auto'  # auto = auto-contrast fg for bg")
        sys.exit(0)

    raw1 = sys.argv[1]
    raw2 = sys.argv[2]
    level = sys.argv[3].upper() if len(sys.argv) > 3 else 'AA'
    text_size = sys.argv[4].lower() if len(sys.argv) > 4 else 'normal'

    if level not in ('AA', 'AAA'):
        print(f"Error: Unknown WCAG level '{level}'. Use 'AA' or 'AAA'.", file=sys.stderr)
        sys.exit(2)
    if text_size not in ('normal', 'large'):
        print(f"Error: Unknown text size '{text_size}'. Use 'normal' or 'large'.", file=sys.stderr)
        sys.exit(2)

    # Resolve colors
    try:
        color1 = resolve_color_input(raw1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        color2 = resolve_color_input(raw2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    # Calculate contrast
    ratio = wcag_contrast_ratio(color1, color2)
    if ratio is None:
        print("Error: Could not calculate contrast ratio.", file=sys.stderr)
        sys.exit(2)

    passes = wcag_passes(color1, color2, level, text_size)

    # Print report
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)

    print(f"\n  WCAG 2.1 Contrast Ratio Calculator")
    print_separator()
    print(f"  Input 1:  {raw1!r} → {color1}  (L = {l1:.4f})")
    print(f"  Input 2:  {raw2!r} → {color2}  (L = {l2:.4f})")
    print_separator()

    lighter = max(l1, l2)
    darker = min(l1, l2)
    print(f"  Lighter luminance:  {lighter:.6f}")
    print(f"  Darker luminance:   {darker:.6f}")
    print(f"  Formula:            (L1 + 0.05) / (L2 + 0.05)")
    print(f"  Result:             ({lighter:.6f} + 0.05) / ({darker:.6f} + 0.05)")
    print(f"  ──────────────────────────────────────────────────")
    print(f"  Contrast Ratio:     {ratio:.4f}:1")
    print_separator()

    # Thresholds
    if level == 'AA':
        threshold = 3.0 if text_size == 'large' else 4.5
        label = 'AA (large)' if text_size == 'large' else 'AA (normal)'
    else:
        threshold = 4.5 if text_size == 'large' else 7.0
        label = 'AAA (large)' if text_size == 'large' else 'AAA (normal)'

    status = 'PASS ✓' if passes else 'FAIL ✗'
    print(f"  WCAG {level} ({text_size}):  {status}  (threshold: ≥ {threshold}:1)")
    print_separator()

    # Additional thresholds
    if level == 'AA':
        print(f"  WCAG AA (normal):   {'PASS ✓' if wcag_passes(color1, color2, 'AA', 'normal') else 'FAIL ✗'}  (≥ 4.5:1)")
        print(f"  WCAG AA (large):    {'PASS ✓' if wcag_passes(color1, color2, 'AA', 'large') else 'FAIL ✗'}  (≥ 3.0:1)")
        print(f"  WCAG AAA (normal):  {'PASS ✓' if wcag_passes(color1, color2, 'AAA', 'normal') else 'FAIL ✗'}  (≥ 7.0:1)")
        print(f"  WCAG AAA (large):   {'PASS ✓' if wcag_passes(color1, color2, 'AAA', 'large') else 'FAIL ✗'}  (≥ 4.5:1)")
    else:
        print(f"  WCAG AA (normal):   {'PASS ✓' if wcag_passes(color1, color2, 'AA', 'normal') else 'FAIL ✗'}  (≥ 4.5:1)")
        print(f"  WCAG AA (large):    {'PASS ✓' if wcag_passes(color1, color2, 'AA', 'large') else 'FAIL ✗'}  (≥ 3.0:1)")
        print(f"  WCAG AAA (normal):  {'PASS ✓' if wcag_passes(color1, color2, 'AAA', 'normal') else 'FAIL ✗'}  (≥ 7.0:1)")
        print(f"  WCAG AAA (large):   {'PASS ✓' if wcag_passes(color1, color2, 'AAA', 'large') else 'FAIL ✗'}  (≥ 4.5:1)")

    print(f"\n{wcag_label(ratio)}")
    print()

    sys.exit(0 if passes else 1)


if __name__ == '__main__':
    main()
