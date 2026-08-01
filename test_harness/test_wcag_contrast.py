"""
Tests for the WCAG Contrast Ratio Calculator.

These tests are fully independent of the Doxtr Sphinx extension.
They validate the standalone WCAG 2.1 implementation in wcag_contrast.py.

Run with:
    python -m pytest test_wcag_contrast.py -v
    or
    python test_wcag_contrast.py    # runs doctests + assertions
"""

import math
import sys
import os

# Allow running tests from the test_harness directory
sys.path.insert(0, os.path.dirname(__file__))

from wcag_contrast import (
    parse_hex_color,
    _linearize,
    relative_luminance,
    wcag_contrast_ratio,
    wcag_passes,
    wcag_label,
    wcag_report,
    _adjust_brightness,
    _resolve_color_expression,
    _resolve_admonition_colors,
    get_admonition_colors,
    get_highest_contrast_color,
    SEMANTIC_PALETTE,
    WCAG_AA_NORMAL,
    WCAG_AA_LARGE,
    WCAG_AAA_NORMAL,
    WCAG_AAA_LARGE,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_close(a, b, tolerance=1e-6, label=""):
    """Assert two floats are within tolerance."""
    diff = abs(a - b)
    if diff > tolerance:
        raise AssertionError(
            f"{label}: {a} != {b} (diff={diff:.10f}, tol={tolerance})"
        )


# ---------------------------------------------------------------------------
# 1. parse_hex_color
# ---------------------------------------------------------------------------

def test_parse_hex_color_3digit():
    assert parse_hex_color('#F00') == (255, 0, 0)
    assert parse_hex_color('F00') == (255, 0, 0)
    assert parse_hex_color('#abc') == (170, 187, 204)


def test_parse_hex_color_6digit():
    assert parse_hex_color('#000000') == (0, 0, 0)
    assert parse_hex_color('#FFFFFF') == (255, 255, 255)
    assert parse_hex_color('#1E3A5F') == (30, 58, 95)


def test_parse_hex_color_8digit():
    result = parse_hex_color('#FF000080')
    assert result == (255, 0, 0), f"Expected (255, 0, 0), got {result}"


def test_parse_hex_color_invalid():
    assert parse_hex_color('') is None
    assert parse_hex_color('notacolor') is None
    assert parse_hex_color('#GGGGGG') is None
    assert parse_hex_color('#12345') is None


# ---------------------------------------------------------------------------
# 2. _linearize
# ---------------------------------------------------------------------------

def test_linearize_below_threshold():
    # 0 / 255 = 0.0 => 0.0 / 12.92 = 0.0
    assert _linearize(0) == 0.0

    # 8 / 255 ≈ 0.03137 <= 0.03928 => 0.03137 / 12.92
    val = (8 / 255.0) / 12.92
    _assert_close(_linearize(8), val)


def test_linearize_above_threshold():
    # 255 / 255 = 1.0 => ((1.0 + 0.055) / 1.055) ** 2.4 = 1.0
    _assert_close(_linearize(255), 1.0)

    # 128 / 255 ≈ 0.50196 > 0.03928
    srgb = 128 / 255.0
    expected = ((srgb + 0.055) / 1.055) ** 2.4
    _assert_close(_linearize(128), expected)


def test_linearize_boundary():
    # 10 / 255 ≈ 0.03922 — just below threshold
    val_below = (10 / 255.0) / 12.92
    _assert_close(_linearize(10), val_below)
    # 11 / 255 ≈ 0.04314 — just above threshold
    srgb = 11 / 255.0
    val_above = ((srgb + 0.055) / 1.055) ** 2.4
    _assert_close(_linearize(11), val_above)


# ---------------------------------------------------------------------------
# 3. relative_luminance
# ---------------------------------------------------------------------------

def test_luminance_black():
    _assert_close(relative_luminance('#000000'), 0.0)


def test_luminance_white():
    _assert_close(relative_luminance('#FFFFFF'), 1.0)


def test_luminance_gray():
    srgb = 128 / 255.0
    linear = ((srgb + 0.055) / 1.055) ** 2.4
    expected = 0.2126 * linear + 0.7152 * linear + 0.0722 * linear
    _assert_close(relative_luminance('#808080'), expected)


def test_luminance_invalid():
    assert relative_luminance('') is None
    assert relative_luminance('notacolor') is None


# ---------------------------------------------------------------------------
# 4. wcag_contrast_ratio
# ---------------------------------------------------------------------------

def test_contrast_black_white():
    ratio = wcag_contrast_ratio('#000000', '#FFFFFF')
    assert ratio is not None
    _assert_close(ratio, 21.0)


def test_contrast_white_black():
    ratio1 = wcag_contrast_ratio('#000000', '#FFFFFF')
    ratio2 = wcag_contrast_ratio('#FFFFFF', '#000000')
    assert ratio1 == ratio2


def test_contrast_same_color():
    _assert_close(wcag_contrast_ratio('#FFFFFF', '#FFFFFF'), 1.0)
    _assert_close(wcag_contrast_ratio('#808080', '#808080'), 1.0)


def test_contrast_known_values():
    # #767676 on #FFFFFF should be ~4.54:1 (passes AA normal text)
    ratio = wcag_contrast_ratio('#767676', '#FFFFFF')
    assert ratio is not None
    _assert_close(ratio, 4.542, tolerance=0.01)
    assert ratio >= 4.5, "#767676 on white should pass AA (4.5:1)"


def test_contrast_invalid_input():
    assert wcag_contrast_ratio('', '#FFFFFF') is None
    assert wcag_contrast_ratio('#000000', '') is None
    assert wcag_contrast_ratio('notacolor', '#FFFFFF') is None


def test_contrast_short_hex():
    # #FFF on #000 = 21:1
    ratio = wcag_contrast_ratio('#FFF', '#000')
    _assert_close(ratio, 21.0)
    # #F00 on #FFF — red on white = 3.998:1 (FAILS AA normal text)
    ratio = wcag_contrast_ratio('#F00', '#FFFFFF')
    assert ratio is not None, "Contrast ratio should not be None for short hex"
    assert ratio < 4.5, f"Red on white should fail AA: {ratio:.4f}:1"


# ---------------------------------------------------------------------------
# 5. wcag_passes
# ---------------------------------------------------------------------------

def test_passes_aa_normal():
    assert wcag_passes('#000000', '#FFFFFF', 'AA', 'normal') is True
    # #767676 on white = 4.54:1 → PASSES AA
    assert wcag_passes('#767676', '#FFFFFF', 'AA', 'normal') is True
    # #777777 on white = 4.41:1 → FAILS AA
    assert wcag_passes('#777777', '#FFFFFF', 'AA', 'normal') is False
    # #757575 on white = 4.61:1 → PASSES AA
    assert wcag_passes('#757575', '#FFFFFF', 'AA', 'normal') is True


def test_passes_aa_large():
    assert wcag_passes('#767676', '#FFFFFF', 'AA', 'large') is True  # 4.54 >= 3.0
    assert wcag_passes('#000000', '#FFFFFF', 'AA', 'large') is True


def test_passes_aaa():
    assert wcag_passes('#000000', '#FFFFFF', 'AAA', 'normal') is True
    # #888888 on white = ~3.96:1 → FAILS AAA (7:1)
    assert wcag_passes('#888888', '#FFFFFF', 'AAA', 'normal') is False
    # #AAAAAA on white = 2.32:1 → FAILS AAA (7:1)
    assert wcag_passes('#AAAAAA', '#FFFFFF', 'AAA', 'normal') is False
    # #595959 on white = 7.00:1 → PASSES AAA
    assert wcag_passes('#595959', '#FFFFFF', 'AAA', 'normal') is True


def test_passes_invalid_level():
    try:
        wcag_passes('#000000', '#FFFFFF', 'INVALID')
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_passes_invalid_colors():
    assert wcag_passes('', '#FFFFFF', 'AA', 'normal') is False
    assert wcag_passes('#000000', '', 'AA', 'normal') is False


# ---------------------------------------------------------------------------
# 6. wcag_label
# ---------------------------------------------------------------------------

def test_wcag_label():
    assert wcag_label(1.0) == 'FAIL (below AA large-text threshold)'
    # 2.5 fails all thresholds (AA large = 3:1)
    assert wcag_label(2.5) == 'FAIL (below AA large-text threshold)'
    assert wcag_label(3.0) == 'PASS: AA (large)'
    assert wcag_label(3.5) == 'PASS: AA (large)'
    # 4.5 passes AAA (large) and AA (normal) and AA (large)
    assert wcag_label(4.5) == 'PASS: AAA (large), AA (normal), AA (large)'
    assert wcag_label(5.0) == 'PASS: AAA (large), AA (normal), AA (large)'
    # 7.0 passes all levels
    assert wcag_label(7.0) == 'PASS: AAA (normal), AAA (large), AA (normal), AA (large)'
    assert wcag_label(7.5) == 'PASS: AAA (normal), AAA (large), AA (normal), AA (large)'
    assert wcag_label(21.0) == 'PASS: AAA (normal), AAA (large), AA (normal), AA (large)'


# ---------------------------------------------------------------------------
# 7. wcag_report
# ---------------------------------------------------------------------------

def test_wcag_report():
    report = wcag_report('#000000', '#FFFFFF')
    assert 'WCAG 2.1 Contrast Report' in report
    assert '#000000' in report
    assert '#FFFFFF' in report
    assert '21.0' in report
    assert 'PASS' in report


# ---------------------------------------------------------------------------
# 8. _adjust_brightness
# ---------------------------------------------------------------------------

def test_adjust_brightness_lighten():
    result = _adjust_brightness('#000000', 50)
    assert result == '#808080'


def test_adjust_brightness_darken():
    result = _adjust_brightness('#FFFFFF', -50)
    assert result == '#808080'


def test_adjust_brightness_zero():
    result = _adjust_brightness('#FF0000', 0)
    assert result == '#FF0000'


def test_adjust_brightness_clamp():
    result = _adjust_brightness('#FFFFFF', 100)
    assert result == '#FFFFFF'
    result = _adjust_brightness('#000000', -100)
    assert result == '#000000'


# ---------------------------------------------------------------------------
# 9. _resolve_color_expression
# ---------------------------------------------------------------------------

def test_resolve_static_hex():
    assert _resolve_color_expression('#FF0000') == '#FF0000'
    assert _resolve_color_expression('FF0000') == 'FF0000'


def test_resolve_palette_key():
    assert _resolve_color_expression('dd:primary') == '#2E3959'
    assert _resolve_color_expression('dd:secondary') == '#A64985'
    assert _resolve_color_expression('dd:info') == '#9BE2F2'
    assert _resolve_color_expression('dd:success') == '#66D98E'
    assert _resolve_color_expression('dd:warning') == '#EA9B62'
    assert _resolve_color_expression('dd:danger') == '#F2545B'
    assert _resolve_color_expression('dd:page') == '#FFFFFF'


def test_resolve_lighten():
    result = _resolve_color_expression('dd:success:lighten:80')
    assert result is not None, f"Expected resolved color, got {result}"
    rgb = parse_hex_color(result)
    assert rgb is not None, f"Cannot parse result: {result}"
    assert rgb[0] > 102 or rgb[1] > 217 or rgb[2] > 142, (
        f"Lightened color {result} should be lighter than #66D98E"
    )


def test_resolve_darken():
    result = _resolve_color_expression('dd:primary:darken:20')
    assert result is not None, f"Expected resolved color, got {result}"
    rgb = parse_hex_color(result)
    assert rgb is not None, f"Cannot parse result: {result}"
    assert rgb[0] < 46 or rgb[1] < 57 or rgb[2] < 89, (
        f"Darkened color {result} should be darker than #2E3959"
    )


def test_resolve_invalid_palette():
    assert _resolve_color_expression('dd:nonexistent') is None


# ---------------------------------------------------------------------------
# 10. Admonition color resolution
# ---------------------------------------------------------------------------

def test_resolve_hint_colors():
    """Resolve the hint admonition's background and foreground colors.

    The hint admonition in core_config.py is defined as:

        'hint': {
            'title_background_color': 'dd:success',
            'title_font_color': 'dd:this:title_background_color:contrast:fg:primary',
            ...
        }

    Resolution steps:
        1. title_background_color = 'dd:success' → '#66D98E' (from semantic palette)
        2. title_font_color = 'dd:this:title_background_color:contrast:fg:primary'
           → Resolve 'this:title_background_color' = '#66D98E'
           → Apply 'contrast:fg:primary': find foreground that contrasts
             against '#66D98E' with target 'primary' = '#2E3959'
    """
    result = _resolve_admonition_colors('hint')
    assert result is not None, f"Failed to resolve hint admonition colors, got {result}"

    bg_color, fg_color = result

    # Background should be the success palette color
    assert bg_color == '#66D98E', f"Expected bg='#66D98E', got '{bg_color}'"

    # Foreground should be a color that contrasts with '#66D98E'
    # against the 'primary' target '#2E3959'
    assert fg_color is not None, f"Foreground color is None"
    assert fg_color.startswith('#'), f"Foreground '{fg_color}' is not a hex color"

    # Verify the contrast ratio between bg and fg is >= 4.5:1
    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation failed"
    assert ratio >= 4.5, (
        f"Hint admonition contrast ratio {ratio:.4f}:1 is below WCAG AA "
        f"threshold (4.5:1). bg={bg_color}, fg={fg_color}"
    )

    print(f"\n  Hint admonition:")
    print(f"    title_background_color: {bg_color}")
    print(f"    title_font_color:       {fg_color}")
    print(f"    Contrast ratio:         {ratio:.4f}:1")
    print(f"    WCAG AA (normal):       {'PASS' if ratio >= 4.5 else 'FAIL'}")
    print(f"    WCAG AA (large):        {'PASS' if ratio >= 3.0 else 'FAIL'}")
    print(f"    WCAG AAA (normal):      {'PASS' if ratio >= 7.0 else 'FAIL'}")


def test_resolve_note_colors():
    """Resolve the note admonition's colors."""
    result = _resolve_admonition_colors('note')
    assert result is not None, f"Failed to resolve note colors, got {result}"

    bg_color, fg_color = result
    assert bg_color == '#9BE2F2', f"Expected bg='#9BE2F2', got '{bg_color}'"

    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation failed"
    assert ratio >= 4.5, (
        f"Note admonition contrast ratio {ratio:.4f}:1 is below WCAG AA "
        f"threshold (4.5:1). bg={bg_color}, fg={fg_color}"
    )

    print(f"\n  Note admonition:")
    print(f"    title_background_color: {bg_color}")
    print(f"    title_font_color:       {fg_color}")
    print(f"    Contrast ratio:         {ratio:.4f}:1")


def test_resolve_warning_colors():
    """Resolve the warning admonition's colors."""
    result = _resolve_admonition_colors('warning')
    assert result is not None, f"Failed to resolve warning colors, got {result}"

    bg_color, fg_color = result
    assert bg_color == '#EA9B62', f"Expected bg='#EA9B62', got '{bg_color}'"

    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation failed"
    assert ratio >= 4.5, (
        f"Warning admonition contrast ratio {ratio:.4f}:1 is below WCAG AA "
        f"threshold (4.5:1). bg={bg_color}, fg={fg_color}"
    )

    print(f"\n  Warning admonition:")
    print(f"    title_background_color: {bg_color}")
    print(f"    title_font_color:       {fg_color}")
    print(f"    Contrast ratio:         {ratio:.4f}:1")


def test_resolve_danger_colors():
    """Resolve the danger admonition's colors."""
    result = _resolve_admonition_colors('danger')
    assert result is not None, f"Failed to resolve danger colors, got {result}"

    bg_color, fg_color = result
    assert bg_color == '#F2545B', f"Expected bg='#F2545B', got '{bg_color}'"

    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation failed"
    assert ratio >= 4.5, (
        f"Danger admonition contrast ratio {ratio:.4f}:1 is below WCAG AA "
        f"threshold (4.5:1). bg={bg_color}, fg={fg_color}"
    )

    print(f"\n  Danger admonition:")
    print(f"    title_background_color: {bg_color}")
    print(f"    title_font_color:       {fg_color}")
    print(f"    Contrast ratio:         {ratio:.4f}:1")


def test_resolve_important_colors():
    """Resolve the important admonition's colors."""
    result = _resolve_admonition_colors('important')
    assert result is not None, f"Failed to resolve important colors, got {result}"

    bg_color, fg_color = result
    assert bg_color == '#A64985', f"Expected bg='#A64985', got '{bg_color}'"

    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation failed"
    assert ratio >= 4.5, (
        f"Important admonition contrast ratio {ratio:.4f}:1 is below WCAG AA "
        f"threshold (4.5:1). bg={bg_color}, fg={fg_color}"
    )

    print(f"\n  Important admonition:")
    print(f"    title_background_color: {bg_color}")
    print(f"    title_font_color:       {fg_color}")
    print(f"    Contrast ratio:         {ratio:.4f}:1")


def test_resolve_unknown_admonition():
    """Resolving a non-existent admonition type should return None."""
    result = _resolve_admonition_colors('nonexistent')
    assert result is None


# ---------------------------------------------------------------------------
# 11. get_admonition_colors (public API)
# ---------------------------------------------------------------------------

def test_get_admonition_colors_public_api():
    """Test the public get_admonition_colors() API."""
    result = get_admonition_colors('hint')
    assert result is not None, f"Failed to get hint colors via public API, got {result}"
    bg_color, fg_color = result
    assert bg_color == '#66D98E'
    assert fg_color is not None, "Foreground color should not be None"

    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None
    assert ratio >= 4.5, f"Contrast ratio {ratio:.4f}:1 below WCAG AA threshold"


# ---------------------------------------------------------------------------
# 12. Integration: Full hint admonition contrast test
# ---------------------------------------------------------------------------

def test_hint_admonition_full_contrast_analysis():
    """
    Full analysis of the hint admonition's title_background_color and
    title_font_color as defined in core_config.py.

    The hint admonition uses:
        title_background_color: 'dd:success'  → '#66D98E' (green)
        title_font_color:       'dd:this:title_background_color:contrast:fg:primary'
                                  → resolves to a color that contrasts
                                    against '#66D98E' with target 'primary'
                                    ('#2E3959')

    This test verifies:
        1. The background color resolves to '#66D98E'
        2. The foreground color is resolved correctly
        3. The contrast ratio meets WCAG AA (4.5:1) for normal text
        4. The contrast ratio meets WCAG AAA (7:1) if possible
        5. The contrast ratio meets WCAG AA (3:1) for large text
    """
    bg_color, fg_color = get_admonition_colors('hint')

    # Step 1: Verify background color
    assert bg_color == '#66D98E', (
        f"Expected background '#66D98E', got '{bg_color}'"
    )

    # Step 2: Verify foreground is a valid hex color
    assert fg_color is not None, f"Foreground color should not be None, got {fg_color}"
    assert fg_color.startswith('#'), (
        f"Foreground '{fg_color}' should start with '#'"
    )
    rgb = parse_hex_color(fg_color)
    assert rgb is not None, f"Foreground '{fg_color}' is not a valid hex color"

    # Step 3: Calculate and verify contrast ratio
    ratio = wcag_contrast_ratio(bg_color, fg_color)
    assert ratio is not None, "Contrast ratio calculation should not return None"

    # Step 4: WCAG AA normal text (4.5:1)
    assert ratio >= 4.5, (
        f"FAIL: Contrast ratio {ratio:.4f}:1 does not meet "
        f"WCAG AA normal text requirement (4.5:1)\n"
        f"  Background: {bg_color}\n"
        f"  Foreground: {fg_color}"
    )

    # Step 5: WCAG AA large text (3:1)
    assert ratio >= 3.0, (
        f"FAIL: Contrast ratio {ratio:.4f}:1 does not meet "
        f"WCAG AA large text requirement (3:1)"
    )

    # Step 6: Print full report
    l_bg = relative_luminance(bg_color)
    l_fg = relative_luminance(fg_color)
    lighter = max(l_bg, l_fg)
    darker = min(l_bg, l_fg)

    print("\n" + "=" * 50)
    print("  HINT ADMONITION — WCAG Contrast Analysis")
    print("=" * 50)
    print(f"  title_background_color:  {bg_color}")
    print(f"  title_font_color:        {fg_color}")
    print(f"  ─────────────────────────────────")
    print(f"  Luminance (bg):          {l_bg:.6f}")
    print(f"  Luminance (fg):          {l_fg:.6f}")
    print(f"  Lighter:                 {lighter:.6f}")
    print(f"  Darker:                  {darker:.6f}")
    print(f"  ─────────────────────────────────")
    print(f"  Contrast Ratio:          {ratio:.4f}:1")
    print(f"  ─────────────────────────────────")
    print(f"  WCAG AA (normal text):   {'PASS ✓' if ratio >= 4.5 else 'FAIL ✗'}  (≥ 4.5:1)")
    print(f"  WCAG AA (large text):    {'PASS ✓' if ratio >= 3.0 else 'FAIL ✗'}  (≥ 3.0:1)")
    print(f"  WCAG AAA (normal text):  {'PASS ✓' if ratio >= 7.0 else 'FAIL ✗'}  (≥ 7.0:1)")
    print(f"  WCAG AAA (large text):   {'PASS ✓' if ratio >= 4.5 else 'FAIL ✗'}  (≥ 4.5:1)")
    print("=" * 50)


# ---------------------------------------------------------------------------
# 13. Edge cases and boundary tests
# ---------------------------------------------------------------------------

def test_contrast_ratio_boundary_AA():
    """Test colors that are right at the AA boundary."""
    # #767676 on #FFFFFF should be just above 4.5:1
    ratio = wcag_contrast_ratio('#767676', '#FFFFFF')
    assert ratio is not None
    assert ratio >= 4.5, f"#767676 on white should pass AA: {ratio:.4f}:1"

    # #777777 on #FFFFFF should be just below 4.5:1
    ratio = wcag_contrast_ratio('#777777', '#FFFFFF')
    assert ratio is not None
    assert ratio < 4.5, f"#777777 on white should fail AA: {ratio:.4f}:1"


def test_contrast_ratio_boundary_AAA():
    """Test colors that are right at the AAA boundary."""
    # #595959 on #FFFFFF should be just above 7:1
    ratio = wcag_contrast_ratio('#595959', '#FFFFFF')
    assert ratio is not None
    assert ratio >= 7.0, f"#595959 on white should pass AAA: {ratio:.4f}:1"

    # #5A5A5A on #FFFFFF should be just below 7:1
    ratio = wcag_contrast_ratio('#5A5A5A', '#FFFFFF')
    assert ratio is not None
    assert ratio < 7.0, f"#5A5A5A on white should fail AAA: {ratio:.4f}:1"


def test_contrast_ratio_monochrome():
    """Colors with same luminance should have 1:1 ratio."""
    ratio = wcag_contrast_ratio('#808080', '#808080')
    _assert_close(ratio, 1.0)


def test_semantic_palette_values():
    """Verify all semantic palette colors are valid hex."""
    for name, color in SEMANTIC_PALETTE.items():
        rgb = parse_hex_color(color)
        assert rgb is not None, f"Palette '{name}' = '{color}' is not a valid hex color"


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests and print results."""
    tests = [
        ("parse_hex_color 3-digit", test_parse_hex_color_3digit),
        ("parse_hex_color 6-digit", test_parse_hex_color_6digit),
        ("parse_hex_color 8-digit", test_parse_hex_color_8digit),
        ("parse_hex_color invalid", test_parse_hex_color_invalid),
        ("linearize below threshold", test_linearize_below_threshold),
        ("linearize above threshold", test_linearize_above_threshold),
        ("linearize boundary", test_linearize_boundary),
        ("luminance black", test_luminance_black),
        ("luminance white", test_luminance_white),
        ("luminance gray", test_luminance_gray),
        ("luminance invalid", test_luminance_invalid),
        ("contrast black-white", test_contrast_black_white),
        ("contrast white-black", test_contrast_white_black),
        ("contrast same color", test_contrast_same_color),
        ("contrast known values", test_contrast_known_values),
        ("contrast invalid input", test_contrast_invalid_input),
        ("contrast short hex", test_contrast_short_hex),
        ("passes AA normal", test_passes_aa_normal),
        ("passes AA large", test_passes_aa_large),
        ("passes AAA", test_passes_aaa),
        ("passes invalid level", test_passes_invalid_level),
        ("passes invalid colors", test_passes_invalid_colors),
        ("wcag_label", test_wcag_label),
        ("wcag_report", test_wcag_report),
        ("adjust_brightness lighten", test_adjust_brightness_lighten),
        ("adjust_brightness darken", test_adjust_brightness_darken),
        ("adjust_brightness zero", test_adjust_brightness_zero),
        ("adjust_brightness clamp", test_adjust_brightness_clamp),
        ("resolve static hex", test_resolve_static_hex),
        ("resolve palette key", test_resolve_palette_key),
        ("resolve lighten", test_resolve_lighten),
        ("resolve darken", test_resolve_darken),
        ("resolve invalid palette", test_resolve_invalid_palette),
        ("resolve hint colors", test_resolve_hint_colors),
        ("resolve note colors", test_resolve_note_colors),
        ("resolve warning colors", test_resolve_warning_colors),
        ("resolve danger colors", test_resolve_danger_colors),
        ("resolve important colors", test_resolve_important_colors),
        ("resolve unknown admonition", test_resolve_unknown_admonition),
        ("get_admonition_colors public API", test_get_admonition_colors_public_api),
        ("hint full contrast analysis", test_hint_admonition_full_contrast_analysis),
        ("contrast ratio boundary AA", test_contrast_ratio_boundary_AA),
        ("contrast ratio boundary AAA", test_contrast_ratio_boundary_AAA),
        ("contrast ratio monochrome", test_contrast_ratio_monochrome),
        ("semantic palette values", test_semantic_palette_values),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, func in tests:
        try:
            func()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
            errors.append((name, e))

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed ({passed + failed} total)")
    if errors:
        print(f"\n  Failed tests:")
        for name, e in errors:
            print(f"    - {name}: {e}")
    print(f"{'=' * 50}")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
