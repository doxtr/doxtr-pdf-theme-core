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


# --- Runner ---

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
