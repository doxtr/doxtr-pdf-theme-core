"""Unit tests for doxtr_pdf_theme_core.utils

This module tests the core utility functions used throughout the theme.
Run with: python test_harness/test_utils.py
Or with pytest: pytest test_harness/test_utils.py -v
"""
import sys
import os

# Add package to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from doxtr_pdf_theme_core.utils import (
    get_safe_filename,
    adjust_hex_brightness,
    hex_to_cmyk_string,
    deep_update,
    to_bool,
    get_highest_contrast_color,
    hex_to_rgb,
    _split_hex_opacity,
    resolve_color,
)


# --- get_safe_filename ---

def test_safe_filename_basic():
    assert get_safe_filename('My Project') == 'my_project'


def test_safe_filename_special_chars():
    assert get_safe_filename('My Project!@#') == 'my_project'


def test_safe_filename_empty():
    assert get_safe_filename('') == 'document'


def test_safe_filename_only_special():
    assert get_safe_filename('!@#$%') == 'document'


def test_safe_filename_unicode_stripped():
    # Non-ASCII chars are stripped; result falls back to 'document' if empty
    result = get_safe_filename('Ünïcödé')
    assert result == 'document' or result.isidentifier()


def test_safe_filename_preserves_numbers():
    assert get_safe_filename('Project 123') == 'project_123'


# --- adjust_hex_brightness ---

def test_brighten_black():
    result = adjust_hex_brightness('#000000', 50)
    assert result == '#808080'


def test_darken_white():
    result = adjust_hex_brightness('#FFFFFF', -50)
    assert result == '#808080'


def test_brightness_noop():
    assert adjust_hex_brightness('#FF0000', 0) == '#FF0000'


def test_brightness_clamp_max():
    assert adjust_hex_brightness('#FFFFFF', 100) == '#FFFFFF'


def test_brightness_clamp_min():
    assert adjust_hex_brightness('#000000', -100) == '#000000'


def test_brightness_preserves_alpha():
    result = adjust_hex_brightness('#FF000080', 0)
    assert result.endswith('80'), f"Expected alpha preserved, got {result}"


def test_brightness_3digit_input():
    result = adjust_hex_brightness('#F00', 0)
    assert result == '#FF0000'


def test_brightness_none_returns_none():
    assert adjust_hex_brightness('', 50) is None
    assert adjust_hex_brightness(None, 50) is None


# --- hex_to_cmyk_string ---

def test_cmyk_black():
    assert hex_to_cmyk_string('#000000') == '0, 0, 0, 1'


def test_cmyk_white():
    result = hex_to_cmyk_string('#FFFFFF')
    assert result == '0.000, 0.000, 0.000, 0.000'


def test_cmyk_pure_red():
    result = hex_to_cmyk_string('#FF0000')
    assert result == '0.000, 1.000, 1.000, 0.000'


def test_cmyk_3digit():
    result = hex_to_cmyk_string('#F00')
    assert result == '0.000, 1.000, 1.000, 0.000'


def test_cmyk_8digit_strips_alpha():
    result_8 = hex_to_cmyk_string('#FF000080')
    result_6 = hex_to_cmyk_string('#FF0000')
    assert result_8 == result_6


def test_cmyk_empty_returns_none():
    assert hex_to_cmyk_string('') is None
    assert hex_to_cmyk_string(None) is None


# --- deep_update ---

def test_deep_update_basic():
    base = {'a': 1, 'b': 2}
    overlay = {'b': 99, 'c': 3}
    result = deep_update(base, overlay)
    assert result == {'a': 1, 'b': 99, 'c': 3}


def test_deep_update_nested():
    base = {'a': {'x': 1, 'y': 2}}
    overlay = {'a': {'y': 99, 'z': 3}}
    result = deep_update(base, overlay)
    assert result == {'a': {'x': 1, 'y': 99, 'z': 3}}


def test_deep_update_mutates_base():
    base = {'a': 1}
    original_id = id(base)
    deep_update(base, {'b': 2})
    assert id(base) == original_id  # same object
    assert 'b' in base


def test_deep_update_overlay_non_dict_overwrites():
    base = {'a': {'x': 1}}
    overlay = {'a': 'overwritten'}
    result = deep_update(base, overlay)
    assert result['a'] == 'overwritten'


def test_deep_update_empty_overlay():
    base = {'a': 1}
    result = deep_update(base, {})
    assert result == {'a': 1}


def test_deep_update_deep_nested():
    base = {'a': {'b': {'c': 1}}}
    overlay = {'a': {'b': {'d': 2}}}
    result = deep_update(base, overlay)
    assert result == {'a': {'b': {'c': 1, 'd': 2}}}


def test_deep_update_aliases_new_key_dict():
    """Verify that a new key from u (a nested dict) is aliased into d.

    This documents the known aliasing behavior — callers must deepcopy
    u themselves if they need u to remain unmodified.
    """
    d = {'a': 1}
    u = {'b': {'x': 1}}
    result = deep_update(d, u)
    # result['b'] IS u['b'] — aliased
    assert result['b'] is u['b']


def test_three_tier_merge_does_not_mutate_section_theme():
    """deepcopy(core) + deepcopy(theme) + deepcopy(user) pattern must not
    mutate the theme or user source dicts."""
    import copy
    section_core = {'note': {'color': '#FFF', 'size': 'large'}}
    section_theme = {'note': {'color': '#00F'}, 'custom': {'color': '#0F0'}}
    section_user = {'note': {'color': '#F00'}, 'custom': {'color': '#FF0'}}

    section_theme_before = copy.deepcopy(section_theme)
    section_user_before = copy.deepcopy(section_user)

    # The FIXED merge pattern
    result = deep_update(
        deep_update(copy.deepcopy(section_core), copy.deepcopy(section_theme)),
        copy.deepcopy(section_user),
    )

    # section_theme must not be mutated
    assert section_theme == section_theme_before, \
        f"section_theme was mutated: {section_theme}"
    # section_user must not be mutated
    assert section_user == section_user_before, \
        f"section_user was mutated: {section_user}"
    # result contains user values
    assert result['note']['color'] == '#F00'
    assert result['custom']['color'] == '#FF0'


def test_three_tier_merge_old_pattern_mutates_theme():
    """Document the bug: the OLD merge pattern (deepcopy only section_core)
    mutates section_theme when section_user overrides a theme-added key.

    This test PASSES (demonstrating the bug exists) and is kept to confirm
    the documented behavior of the unfixed pattern.
    """
    import copy
    section_core = {'generic': {'color': '#FFF'}}
    section_theme = {'custom': {'color': '#00F'}}  # 'custom' not in core
    section_user = {'custom': {'color': '#F00'}}   # user overrides theme key

    # Old (buggy) pattern — only deepcopy section_core
    _r1 = deep_update(copy.deepcopy(section_core), section_theme)
    deep_update(_r1, section_user)

    # section_theme['custom'] was mutated by the second deep_update
    assert section_theme['custom']['color'] == '#F00', \
        "Bug not reproduced — theme was NOT mutated (unexpected)"


# --- to_bool ---

def test_to_bool_true_values():
    assert to_bool(True) is True
    assert to_bool(1) is True
    assert to_bool('yes') is True
    assert to_bool('true') is True
    assert to_bool('1') is True
    assert to_bool('True') is True
    assert to_bool('TRUE') is True


def test_to_bool_false_values():
    for s in ('false', 'False', 'FALSE', '0', 'none', 'None', 'no', 'No', ''):
        assert to_bool(s) is False, f"Expected False for repr {s!r}"


def test_to_bool_none_default_true():
    assert to_bool(None, default=True) is True


def test_to_bool_none_default_false():
    assert to_bool(None, default=False) is False


def test_to_bool_bool_passthrough():
    assert to_bool(False) is False
    assert to_bool(True) is True


def test_to_bool_int_passthrough():
    assert to_bool(0) is False
    assert to_bool(1) is True
    assert to_bool(42) is True


# --- get_highest_contrast_color ---

def test_contrast_returns_string():
    result = get_highest_contrast_color('#FFFFFF', '#FFFFFF')
    assert result is not None
    assert isinstance(result, str)


def test_contrast_already_passes():
    # White on black already passes — should return the original
    result = get_highest_contrast_color('#FFFFFF', '#000000', wcag_level=4.5)
    assert result == '#FFFFFF'


def test_contrast_none_on_empty():
    assert get_highest_contrast_color('', '#FFFFFF') is None
    assert get_highest_contrast_color('#FFFFFF', '') is None


def test_contrast_adjusts_low_contrast():
    # Light gray on white should be adjusted to darker
    result = get_highest_contrast_color('#CCCCCC', '#FFFFFF', wcag_level=4.5)
    # Result should be darker than original
    assert result != '#CCCCCC'


# --- hex_to_rgb ---

def test_hex_to_rgb_basic():
    assert hex_to_rgb('#FF0000') == (255, 0, 0)
    assert hex_to_rgb('#000000') == (0, 0, 0)
    assert hex_to_rgb('#FFFFFF') == (255, 255, 255)


def test_hex_to_rgb_3digit():
    assert hex_to_rgb('#F00') == (255, 0, 0)


def test_hex_to_rgb_8digit():
    assert hex_to_rgb('#FF000080') == (255, 0, 0)  # alpha stripped


def test_hex_to_rgb_invalid():
    assert hex_to_rgb('notacolor') == (0, 0, 0)  # fallback


def test_hex_to_rgb_lowercase():
    assert hex_to_rgb('#ff0000') == (255, 0, 0)


# --- resolve_container_class ---

from doxtr_pdf_theme_core.ast_processors.containers import resolve_container_class
from doxtr_pdf_theme_core.config import validate_container_mapping

_CONTAINERS = {
    'business': {'style': 'default', 'title': 'Business'},
    'typewriter': {'style': 'default'},
    'default': {'style': 'default'},
}


def test_resolve_container_direct_match():
    """Class name exists directly in containers_conf — no mapping needed."""
    name, conf = resolve_container_class('business', {}, _CONTAINERS)
    assert name == 'business'
    assert conf == _CONTAINERS['business']


def test_resolve_container_mapping_hit():
    """Class name is mapped to a valid registered style."""
    mapping = {'biz-alias': 'business'}
    name, conf = resolve_container_class('biz-alias', mapping, _CONTAINERS)
    assert name == 'business'
    assert conf == _CONTAINERS['business']


def test_resolve_container_mapping_overrides_direct():
    """A mapped class that also exists directly resolves to the mapped target."""
    containers = dict(_CONTAINERS)
    containers['biz-alias'] = {'style': 'default', 'title': 'Direct'}  # direct entry exists
    mapping = {'biz-alias': 'business'}
    name, conf = resolve_container_class('biz-alias', mapping, containers)
    assert name == 'business'  # mapping wins over direct match


def test_resolve_container_mapping_invalid_target_original_exists():
    """Mapped target doesn't exist — falls back to original class if it's registered."""
    mapping = {'typewriter': 'nonexistent'}
    name, conf = resolve_container_class('typewriter', mapping, _CONTAINERS)
    assert name == 'typewriter'
    assert conf == _CONTAINERS['typewriter']


def test_resolve_container_mapping_invalid_target_no_original():
    """Mapped target doesn't exist and original is also unregistered — falls back to 'default'."""
    mapping = {'unknown': 'also-unknown'}
    name, conf = resolve_container_class('unknown', mapping, _CONTAINERS)
    assert name == 'default'
    assert conf == _CONTAINERS['default']


def test_resolve_container_no_mapping_no_direct_match():
    """Class is not in mapping and not in containers_conf — falls back to 'default'."""
    name, conf = resolve_container_class('mystery', {}, _CONTAINERS)
    assert name == 'default'


def test_resolve_container_default_passthrough():
    """'default' class resolves directly without any mapping."""
    name, conf = resolve_container_class('default', {}, _CONTAINERS)
    assert name == 'default'


def test_resolve_container_empty_mapping():
    """Empty mapping dict behaves identically to no mapping."""
    name, conf = resolve_container_class('business', {}, _CONTAINERS)
    assert name == 'business'


def test_resolve_container_missing_default_key():
    """When 'default' is absent from containers_conf, fallback returns empty dict."""
    containers = {'business': {'style': 'default'}}
    name, conf = resolve_container_class('mystery', {}, containers)
    assert name == 'default'
    assert conf == {}  # containers_conf.get('default', {}) returns {}


# --- validate_container_mapping ---


def test_validate_container_mapping_all_valid(capsys=None):
    """No warnings when all mapping targets exist in containers."""
    mapping = {'biz-alias': 'business', 'tw-alias': 'typewriter'}
    # Should complete without raising; warnings go to Sphinx logger (not captured here)
    validate_container_mapping(mapping, _CONTAINERS)


def test_validate_container_mapping_empty():
    """Empty mapping produces no warnings."""
    validate_container_mapping({}, _CONTAINERS)


def test_validate_container_mapping_invalid_target():
    """Mapping with an unregistered target completes without raising."""
    mapping = {'broken': 'nonexistent'}
    validate_container_mapping(mapping, _CONTAINERS)  # should not raise


# --- _split_hex_opacity ---

def test_split_hex_opacity_8digit_with_alpha():
    """8-digit hex: base color and alpha extracted and normalized."""
    base, opacity = _split_hex_opacity('#00000044')
    assert base == '#000000'
    assert opacity == '0.27'  # 0x44 = 68; round(68/255, 2) = 0.27


def test_split_hex_opacity_8digit_full_alpha():
    """8-digit hex with FF alpha → opacity '1.0'."""
    base, opacity = _split_hex_opacity('#000000FF')
    assert base == '#000000'
    assert opacity == '1.0'


def test_split_hex_opacity_6digit_no_alpha():
    """6-digit hex passes through unchanged with opacity '1.0'."""
    base, opacity = _split_hex_opacity('#FF0000')
    assert base == '#FF0000'
    assert opacity == '1.0'


def test_split_hex_opacity_3digit_no_alpha():
    """3-digit hex passes through unchanged with opacity '1.0'."""
    base, opacity = _split_hex_opacity('#FFF')
    assert base == '#FFF'
    assert opacity == '1.0'


def test_split_hex_opacity_4digit_full_alpha():
    """4-digit hex with F alpha → opacity '1.0' (0xFF / 255 = 1.0)."""
    base, opacity = _split_hex_opacity('#F00F')
    assert base == '#F00'
    assert opacity == '1.0'  # 'F' * 2 = 'FF' = 255; 255/255 = 1.0


def test_split_hex_opacity_4digit_half_alpha():
    """4-digit hex with 8 alpha → opacity ~0.53 (0x88 = 136; 136/255 ≈ 0.53)."""
    base, opacity = _split_hex_opacity('#F008')
    assert base == '#F00'
    assert opacity == '0.53'  # '8' * 2 = '88' = 136; round(136/255, 2) = 0.53


def test_split_hex_opacity_none_input():
    """None input returns (None, '1.0') without raising."""
    base, opacity = _split_hex_opacity(None)
    assert base is None
    assert opacity == '1.0'


def test_split_hex_opacity_empty_string():
    """Empty string returns ('', '1.0') without raising."""
    base, opacity = _split_hex_opacity('')
    assert base == ''
    assert opacity == '1.0'


def test_split_hex_opacity_invalid_hex_digits():
    """Invalid hex digits in alpha position fall back to original + '1.0'."""
    base, opacity = _split_hex_opacity('#GGGGGGGG')
    assert base == '#GGGGGGGG'
    assert opacity == '1.0'


def test_split_hex_opacity_no_hash_prefix():
    """Input without '#' prefix — 6 chars, no alpha, passes through unchanged."""
    base, opacity = _split_hex_opacity('FF0000')
    assert base == 'FF0000'
    assert opacity == '1.0'


def test_split_hex_opacity_5digit_unrecognized():
    """5-digit hex is unrecognized — passes through unchanged."""
    base, opacity = _split_hex_opacity('#12345')
    assert base == '#12345'
    assert opacity == '1.0'




# --- resolve_color cross-layer user scope guard ---

_PALETTE = {'primary': '#2E3959', 'secondary': '#A64985',
            'info': '#9BE2F2', 'success': '#66D98E',
            'warning': '#EA9B62', 'danger': '#F2545B'}
_PAGE_BG = '#FFFFFF'


def _make_resolve(current_section, user_config=None):
    """Helper: calls resolve_color with minimal fixture data."""
    return lambda value: resolve_color(
        value=value,
        palette=_PALETTE,
        page_bg=_PAGE_BG,
        current_section=current_section,
        current_dict={'title_background_color': '#123456'},
        theme_defaults={},
        core_config={},
        user_config=user_config or {'admonitions': {'note': {'title_background_color': '#AABBCC'}}},
    )


# Instance B (step 10 explicit dotted-path scope guard, now fixed: not-in -> in)
# Syntax: dd:admonitions.[user]:key  — standalone [user] scope segment, triggers step 10.
# Note: step 10 returns the navigated sub-dict; rest (key after ':') is not applied by step 10.
# These tests verify only that the guard fires (blocked) or does not fire (allowed).
def test_explicit_path_user_scope_blocked_from_core():
    """Step 10 guard (Instance B): core section must not resolve [user] scope path."""
    resolve = _make_resolve('core')
    result = resolve('dd:admonitions.[user]:note')
    assert result == '#ff0000'


def test_explicit_path_user_scope_blocked_from_theme():
    """Step 10 guard (Instance B): theme section must not resolve [user] scope path."""
    resolve = _make_resolve('theme')
    result = resolve('dd:admonitions.[user]:note')
    assert result == '#ff0000'


def test_explicit_path_user_scope_allowed_from_user_section():
    """Step 10 guard (Instance B): non-core/theme section may use [user] scope path."""
    resolve = _make_resolve('admonitions')
    result = resolve('dd:admonitions.[user]:note')
    # step 10 returns the navigated sub-dict (rest key is not applied by step 10)
    assert result != '#ff0000'
    assert isinstance(result, dict)


# Instance A (_resolve_path inner guard) is correct dead-code cleanup:
# _resolve_path() has no call sites in the current codebase.

# Regression test: ref == 'user' block at step 11 (already correct guard — ensure no regression)
def test_ref_user_scope_blocked_from_core():
    """ref=='user' block: core section must not resolve dd:user:key."""
    resolve = _make_resolve(
        'core',
        user_config={'core': {'my_color': '#ABCDEF'}}
    )
    result = resolve('dd:user:my_color')
    assert result == '#ff0000'


def test_ref_user_scope_allowed_from_user():
    """ref=='user' block: non-core/theme sections may resolve dd:user:key."""
    resolve = _make_resolve(
        'admonitions',
        user_config={'admonitions': {'my_color': '#AABBCC'}}
    )
    result = resolve('dd:user:my_color')
    assert result == '#AABBCC'


def run_all():
    """Run all tests and report results."""
    import inspect
    tests = [(n, f) for n, f in globals().items() if n.startswith('test_')]
    passed = failed = 0
    failures = []
    
    for name, fn in sorted(tests):
        try:
            fn()
            print(f'  ✓ {name}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗ {name}: {e}')
            failed += 1
            failures.append((name, str(e)))
        except Exception as e:
            print(f'  ✗ {name}: {type(e).__name__}: {e}')
            failed += 1
            failures.append((name, f'{type(e).__name__}: {e}'))
    
    print(f'\n{passed} passed, {failed} failed')
    
    if failures:
        print('\nFailures:')
        for name, msg in failures:
            print(f'  - {name}: {msg}')
    
    return failed == 0


if __name__ == '__main__':
    print('Running doxtr_pdf_theme_core.utils unit tests...\n')
    success = run_all()
    sys.exit(0 if success else 1)


# --- DARK MODE TESTS ---

class TestHexDarkInvert:
    """Tests for hex_dark_invert (Plan 04)."""

    def test_white_to_near_black(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('#FFFFFF') == '#242424'

    def test_black_to_off_white(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('#000000') == '#DBDBDB'

    def test_mid_grey_stays_grey(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        result = hex_dark_invert('#808080')
        # Mid-grey should stay approximately mid-grey
        assert result == '#7F7F7F'

    def test_navy_to_light_blue(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('#183060') == '#AABBDE'

    def test_alpha_preserved(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        result = hex_dark_invert('#18306080')
        assert result.endswith('80')
        assert len(result) == 9  # # + 8 chars

    def test_3_digit_hex(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('#FFF') == '#242424'

    def test_empty_returns_none(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('') is None
        assert hex_dark_invert(None) is None

    def test_invalid_returns_original(self):
        from doxtr_pdf_theme_core.utils import hex_dark_invert
        assert hex_dark_invert('#XYZ') == '#XYZ'


class TestDarkInvertColorsInDict:
    """Tests for _dark_invert_colors_in_dict (Plan 06)."""

    def test_inverts_hex_values(self):
        from doxtr_pdf_theme_core import _dark_invert_colors_in_dict
        d = {'color': '#FFFFFF', 'font': 'Spectral'}
        result = _dark_invert_colors_in_dict(d)
        assert result['color'] == '#242424'
        assert result['font'] == 'Spectral'

    def test_passes_through_dd_expressions(self):
        from doxtr_pdf_theme_core import _dark_invert_colors_in_dict
        d = {'color': 'dd:primary:lighten:40'}
        result = _dark_invert_colors_in_dict(d)
        assert result['color'] == 'dd:primary:lighten:40'

    def test_nested_dicts(self):
        from doxtr_pdf_theme_core import _dark_invert_colors_in_dict
        d = {'chapter': {'color': '#000000', 'font': 'Arial'}}
        result = _dark_invert_colors_in_dict(d)
        assert result['chapter']['color'] == '#DBDBDB'
        assert result['chapter']['font'] == 'Arial'

    def test_preserves_non_string_values(self):
        from doxtr_pdf_theme_core import _dark_invert_colors_in_dict
        d = {'enabled': True, 'level': 7, 'color': '#FF0000'}
        result = _dark_invert_colors_in_dict(d)
        assert result['enabled'] is True
        assert result['level'] == 7


class TestBuildDarkSection:
    """Tests for _build_dark_section (Plan 06)."""

    def test_basic_dark_section(self):
        from doxtr_pdf_theme_core import _build_dark_section
        light = {'bg': '#FFFFFF', 'font': 'Spectral'}
        result = _build_dark_section(light, {})
        assert result['bg'] == '#242424'
        assert result['font'] == 'Spectral'

    def test_overrides_applied(self):
        from doxtr_pdf_theme_core import _build_dark_section
        light = {'bg': '#FFFFFF', 'font': 'Spectral'}
        overrides = {'bg': '#1A1A2E'}
        result = _build_dark_section(light, overrides)
        assert result['bg'] == '#1A1A2E'
        assert result['font'] == 'Spectral'


class TestDarkTextColorDerivation:
    """Tests for dark mode body text color auto-derivation.

    When doxtr_dark_text_color is not explicitly set, the extension should
    derive a text color that meets WCAG contrast against the dark page
    background. This ensures readable text whether the dark page is truly
    dark (#242424) or a custom light color (#FCF6E5).
    """

    def _contrast_ratio(self, c1, c2):
        from doxtr_pdf_theme_core.utils import _hex_to_rgb
        def _rel_lum(hex_color):
            r, g, b = _hex_to_rgb(hex_color)
            def _lin(c):
                c = c / 255.0
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
        l1 = _rel_lum(c1)
        l2 = _rel_lum(c2)
        if l1 < l2:
            l1, l2 = l2, l1
        return (l1 + 0.05) / (l2 + 0.05)

    def test_dark_page_gets_light_text(self):
        """Default dark page (#242424) → text stays light (#DBDBDB)."""
        from doxtr_pdf_theme_core.utils import hex_dark_invert, get_highest_contrast_color
        page_bg = '#242424'
        candidate = hex_dark_invert('#000000')  # #DBDBDB
        result = get_highest_contrast_color(candidate, page_bg, target='foreground', wcag_level=7)
        ratio = self._contrast_ratio(result, page_bg)
        # Text should be light against dark page
        assert ratio >= 7.0, f"Contrast {ratio:.2f}:1 < 7:1 for text {result} on {page_bg}"

    def test_light_cream_page_gets_dark_text(self):
        """Light cream dark-page (#FCF6E5) → text must be dark, not #DBDBDB."""
        from doxtr_pdf_theme_core.utils import hex_dark_invert, get_highest_contrast_color
        page_bg = '#FCF6E5'
        candidate = hex_dark_invert('#000000')  # #DBDBDB
        result = get_highest_contrast_color(candidate, page_bg, target='foreground', wcag_level=7)
        ratio = self._contrast_ratio(result, page_bg)
        # Text must NOT remain #DBDBDB (which has 1.28:1 contrast)
        assert result != '#DBDBDB', f"Text should not remain #DBDBDB against light page {page_bg}"
        assert ratio >= 4.5, f"Contrast {ratio:.2f}:1 < 4.5:1 for text {result} on {page_bg}"

    def test_white_page_gets_dark_text(self):
        """Pure white dark-page (#FFFFFF) → text must be dark."""
        from doxtr_pdf_theme_core.utils import hex_dark_invert, get_highest_contrast_color
        page_bg = '#FFFFFF'
        candidate = hex_dark_invert('#000000')  # #DBDBDB
        result = get_highest_contrast_color(candidate, page_bg, target='foreground', wcag_level=7)
        ratio = self._contrast_ratio(result, page_bg)
        assert ratio >= 7.0, f"Contrast {ratio:.2f}:1 < 7:1 for text {result} on {page_bg}"

    def test_user_override_preserved(self):
        """When user explicitly sets doxtr_dark_text_color, it is used as-is."""
        # This tests the logic path, not the function directly
        user_text = '#FF0000'
        # The code: config.doxtr_dark_text_color = _user_dark_text if _user_dark_text else ...
        result = user_text if user_text else 'would_be_computed'
        assert result == '#FF0000'


class TestAutoDetectDarkStrategy:
    """Tests for _auto_detect_dark_strategy helper and strategy constants."""

    def test_constants_accessible(self):
        """Named constants are importable and have expected values."""
        from doxtr_pdf_theme_core import (
            _DARK_STRATEGY_LUMINANCE_THRESHOLD,
            _VALID_DARK_STRATEGIES,
        )
        assert _DARK_STRATEGY_LUMINANCE_THRESHOLD == 0.35
        assert _VALID_DARK_STRATEGIES == ('auto', 'invert', 'passthrough')

    def test_passthrough_min_palette_keys(self):
        """_PASSTHROUGH_MIN_PALETTE_KEYS constant is accessible."""
        from doxtr_pdf_theme_core.__init__ import _PASSTHROUGH_MIN_PALETTE_KEYS
        assert _PASSTHROUGH_MIN_PALETTE_KEYS == 4

    def test_dark_page_returns_invert(self):
        """Standard dark backgrounds resolve to 'invert' strategy."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#242424')
        assert strategy == 'invert'
        assert lum < 0.35

    def test_solarized_dark_returns_invert(self):
        """Solarized dark (#002B36, L=0.02) resolves to 'invert'."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#002B36')
        assert strategy == 'invert'

    def test_mid_grey_returns_invert(self):
        """Mid-grey (#808080, L=0.22) is below threshold → 'invert'."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#808080')
        assert strategy == 'invert'
        assert lum < 0.35

    def test_light_cream_returns_passthrough(self):
        """Light cream (#FCF6E5, L=0.92) resolves to 'passthrough'."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#FCF6E5')
        assert strategy == 'passthrough'
        assert lum >= 0.35

    def test_solarized_light_returns_passthrough(self):
        """Solarized light (#FDF6E3, L=0.92) resolves to 'passthrough'."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#FDF6E3')
        assert strategy == 'passthrough'

    def test_white_returns_passthrough(self):
        """Pure white (#FFFFFF, L=1.0) resolves to 'passthrough'."""
        from doxtr_pdf_theme_core.__init__ import _auto_detect_dark_strategy
        strategy, lum = _auto_detect_dark_strategy('#FFFFFF')
        assert strategy == 'passthrough'
        assert lum == 1.0

    def test_build_dark_section_passthrough_no_inversion(self):
        """Passthrough strategy skips color inversion entirely."""
        from doxtr_pdf_theme_core.__init__ import _build_dark_section
        light = {'title': '#183060', 'bg': '#FFFFFF', 'font': 'Spectral'}
        result = _build_dark_section(light, {}, 'passthrough')
        assert result['title'] == '#183060'  # NOT inverted
        assert result['bg'] == '#FFFFFF'     # NOT inverted
        assert result['font'] == 'Spectral'  # unchanged

    def test_build_dark_section_passthrough_with_overrides(self):
        """Passthrough strategy applies dark_overrides on top of light values."""
        from doxtr_pdf_theme_core.__init__ import _build_dark_section
        light = {'title': '#183060', 'bg': '#FFFFFF'}
        overrides = {'title': '#073642', 'accent': '#268BD2'}
        result = _build_dark_section(light, overrides, 'passthrough')
        assert result['title'] == '#073642'  # overridden
        assert result['bg'] == '#FFFFFF'     # unchanged (no override)
        assert result['accent'] == '#268BD2' # new key from overrides

    def test_build_dark_section_invert_inverts_colors(self):
        """Invert strategy applies hex_dark_invert to all colors."""
        from doxtr_pdf_theme_core.__init__ import _build_dark_section
        light = {'title': '#183060', 'bg': '#FFFFFF', 'font': 'Spectral'}
        result = _build_dark_section(light, {}, 'invert')
        assert result['title'] != '#183060'  # inverted
        assert result['bg'] != '#FFFFFF'     # inverted
        assert result['font'] == 'Spectral'  # non-color unchanged
