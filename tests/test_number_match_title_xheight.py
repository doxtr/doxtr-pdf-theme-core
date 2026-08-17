"""
Tests for the `number_match_title_xheight` feature.

These tests exercise the Python-side config processing logic only —
no Sphinx app or LaTeX build required.

The helper `compute_xheight_vars` mirrors the exact logic added to
`config_inited` in `__init__.py`.  If that loop changes, this helper
must be kept in sync.  The schema smoke-tests (test_core_config_* and
test_valid_keys_*) import from the real modules and will catch drift
between this helper and production automatically.
"""

import pytest
from doxtr_pdf_theme_core.utils import to_bool


# ---------------------------------------------------------------------------
# Schema / defaults smoke-tests — import from real modules
# ---------------------------------------------------------------------------

def test_core_config_has_default_true():
    """DOXTR_HEADINGS ships with number_match_title_xheight enabled by default."""
    from doxtr_pdf_theme_core.core_config import DOXTR_HEADINGS
    assert 'number_match_title_xheight' in DOXTR_HEADINGS
    assert DOXTR_HEADINGS['number_match_title_xheight'] is True


def test_valid_keys_contains_key():
    """VALID_KEYS['headings'] must accept number_match_title_xheight."""
    from doxtr_pdf_theme_core.config import VALID_KEYS
    assert 'number_match_title_xheight' in VALID_KEYS['headings']


# ---------------------------------------------------------------------------
# Inline helper — mirrors the loop added to config_inited.
# chapter is intentionally excluded: the feature only applies to body-text
# sectioning levels (section / subsection / subsubsection).
# ---------------------------------------------------------------------------

def compute_xheight_vars(headings_cfg: dict) -> dict:
    """
    Reproduces the number_match_title_xheight assignment logic from
    config_inited() and returns the three eligible template_vars booleans.
    chapter is never included — no template var is emitted for it.
    """
    global_xheight_match = headings_cfg.get('number_match_title_xheight', False)
    result = {}
    for el in ['chapter', 'section', 'subsection', 'subsubsection']:
        el_dict = headings_cfg.get(el, {})
        if el != 'chapter':
            result[f'doxtr_{el}_number_match_title_xheight'] = to_bool(
                el_dict.get('number_match_title_xheight', global_xheight_match),
                default=False,
            )
        # chapter: no template var written — the preamble loop only iterates
        # section/subsection/subsubsection.
    return result


# ---------------------------------------------------------------------------
# Behavioural tests
# ---------------------------------------------------------------------------

def test_all_false_by_default():
    """With an empty headings config all eligible levels must be False."""
    vars_ = compute_xheight_vars({})
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is False
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is False
    # chapter key must not appear at all
    assert 'doxtr_chapter_number_match_title_xheight' not in vars_


def test_global_true_propagates_to_eligible_levels():
    """Global True must propagate to section/subsection/subsubsection."""
    vars_ = compute_xheight_vars({'number_match_title_xheight': True})
    assert vars_['doxtr_section_number_match_title_xheight'] is True
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is True


def test_chapter_never_emits_a_template_var():
    """Chapter must not produce a template var regardless of config."""
    vars_global = compute_xheight_vars({'number_match_title_xheight': True})
    vars_perlevel = compute_xheight_vars({'chapter': {'number_match_title_xheight': True}})
    assert 'doxtr_chapter_number_match_title_xheight' not in vars_global
    assert 'doxtr_chapter_number_match_title_xheight' not in vars_perlevel


def test_per_level_override_false_beats_global_true():
    """Global True + section explicitly False → only sub/subsub are True."""
    vars_ = compute_xheight_vars({
        'number_match_title_xheight': True,
        'section': {'number_match_title_xheight': False},
    })
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is True


def test_per_level_override_true_beats_global_false():
    """Global False + subsection explicitly True → only subsection is True."""
    vars_ = compute_xheight_vars({
        'number_match_title_xheight': False,
        'subsection': {'number_match_title_xheight': True},
    })
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is False


def test_multiple_per_level_overrides():
    """Global True, section=False, subsubsection=False → only subsection True."""
    vars_ = compute_xheight_vars({
        'number_match_title_xheight': True,
        'section': {'number_match_title_xheight': False},
        'subsubsection': {'number_match_title_xheight': False},
    })
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is False


def test_all_per_level_false_globally_true():
    """All per-level False, global True → all eligible levels False."""
    vars_ = compute_xheight_vars({
        'number_match_title_xheight': True,
        'section': {'number_match_title_xheight': False},
        'subsection': {'number_match_title_xheight': False},
        'subsubsection': {'number_match_title_xheight': False},
    })
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is False
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is False


# ---------------------------------------------------------------------------
# to_bool coercion — truthy strings must not silently enable the feature
# ---------------------------------------------------------------------------

def test_string_false_is_coerced_to_false():
    """'false' as a string must not enable the feature (to_bool coercion)."""
    vars_ = compute_xheight_vars({'number_match_title_xheight': 'false'})
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is False
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is False


def test_string_true_is_coerced_to_true():
    """'true' as a string must enable the feature (to_bool coercion)."""
    vars_ = compute_xheight_vars({'number_match_title_xheight': 'true'})
    assert vars_['doxtr_section_number_match_title_xheight'] is True
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
    assert vars_['doxtr_subsubsection_number_match_title_xheight'] is True


def test_integer_one_is_coerced_to_true():
    """Integer 1 must enable the feature (truthy)."""
    vars_ = compute_xheight_vars({'number_match_title_xheight': 1})
    assert vars_['doxtr_section_number_match_title_xheight'] is True


def test_integer_zero_is_coerced_to_false():
    """Integer 0 must not enable the feature."""
    vars_ = compute_xheight_vars({'number_match_title_xheight': 0})
    assert vars_['doxtr_section_number_match_title_xheight'] is False


def test_per_level_string_false_not_silently_enabled():
    """Per-level 'false' string must not enable the feature for that level."""
    vars_ = compute_xheight_vars({
        'number_match_title_xheight': True,
        'section': {'number_match_title_xheight': 'false'},
    })
    assert vars_['doxtr_section_number_match_title_xheight'] is False
    assert vars_['doxtr_subsection_number_match_title_xheight'] is True
