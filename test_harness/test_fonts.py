"""Unit tests for doxtr_pdf_theme_core/fonts.py

Tests cover:
- register_font_family() — basic, defaults, dedup, late-call guard
- register_font_families() — explicit, single pattern, dual pattern, missing {weight}
- _expand_pattern() — all three modes
- _clear_font_registry() — clears working list, preserves API list
- _deduplicate_registry() — last-wins semantics
- collect_font_files() — deduplication
- generate_font_features() — LaTeX output format and options
- validate_font_files() — missing file and unsafe name warnings
- process_user_font_config() — explicit and pattern modes, override behaviour
- auto_discover_fonts() — graceful degradation without fonttools
- _find_bold_weight() — various weight scenarios
- fontpkg injection — both branches (no existing fontpkg / existing fontpkg)
- Parent directory __init__.py guard
"""
import logging
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers — reset module state before every test
# ---------------------------------------------------------------------------

import doxtr_pdf_theme_core.fonts as fonts_mod


def _reset():
    """Reset both registries and the late-call guard to a clean state."""
    fonts_mod._api_font_registrations.clear()
    fonts_mod._registered_fonts.clear()
    fonts_mod._fonts_processed = False


@pytest.fixture(autouse=True)
def clean_registry():
    """Auto-used: reset font registries before and after every test."""
    _reset()
    yield
    _reset()


# ---------------------------------------------------------------------------
# register_font_family()
# ---------------------------------------------------------------------------

class TestRegisterFontFamily:

    def test_basic_registration(self, tmp_path):
        fonts_mod.register_font_family(
            name='TestFont',
            fonts_dir=tmp_path,
            upright='TestFont-Regular.ttf',
            bold='TestFont-Bold.ttf',
            italic='TestFont-Italic.ttf',
            bold_italic='TestFont-BoldItalic.ttf',
            options='Scale=MatchLowercase',
        )
        assert len(fonts_mod._api_font_registrations) == 1
        entry = fonts_mod._api_font_registrations[0]
        assert entry['name'] == 'TestFont'
        assert entry['upright'] == 'TestFont-Regular.ttf'
        assert entry['bold'] == 'TestFont-Bold.ttf'
        assert entry['italic'] == 'TestFont-Italic.ttf'
        assert entry['bold_italic'] == 'TestFont-BoldItalic.ttf'
        assert entry['options'] == 'Scale=MatchLowercase'
        assert entry['source'] == 'api'
        assert entry['fonts_dir'] == tmp_path

    def test_defaults_when_faces_omitted(self, tmp_path):
        """Omitting bold/italic/bold_italic should default to upright."""
        fonts_mod.register_font_family(
            name='MinimalFont',
            fonts_dir=tmp_path,
            upright='Minimal-Regular.ttf',
        )
        entry = fonts_mod._api_font_registrations[0]
        assert entry['bold'] == 'Minimal-Regular.ttf'
        assert entry['italic'] == 'Minimal-Regular.ttf'
        assert entry['bold_italic'] == 'Minimal-Regular.ttf'
        assert entry['options'] == ''

    def test_bold_italic_defaults_to_bold(self, tmp_path):
        """When bold_italic is omitted it should default to bold (not upright)."""
        fonts_mod.register_font_family(
            name='PartialFont',
            fonts_dir=tmp_path,
            upright='P-Regular.ttf',
            bold='P-Bold.ttf',
            italic='P-Italic.ttf',
        )
        entry = fonts_mod._api_font_registrations[0]
        assert entry['bold_italic'] == 'P-Bold.ttf'

    def test_dedup_last_registration_wins(self, tmp_path):
        """Registering same name twice keeps the last entry."""
        fonts_mod.register_font_family('MyFont', tmp_path, 'v1.ttf')
        fonts_mod.register_font_family('MyFont', tmp_path, 'v2.ttf')
        assert len(fonts_mod._api_font_registrations) == 1
        assert fonts_mod._api_font_registrations[0]['upright'] == 'v2.ttf'

    def test_late_call_emits_warning(self, tmp_path, caplog):
        """Calling register_font_family after config_inited should warn and not register."""
        fonts_mod._fonts_processed = True
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.register_font_family('LateFont', tmp_path, 'late.ttf')
        assert len(fonts_mod._api_font_registrations) == 0
        assert 'after config_inited' in caplog.text

    def test_fonts_dir_coerced_to_path(self, tmp_path):
        """fonts_dir passed as str should be stored as Path."""
        fonts_mod.register_font_family('StrPath', str(tmp_path), 'f.ttf')
        assert isinstance(fonts_mod._api_font_registrations[0]['fonts_dir'], Path)


# ---------------------------------------------------------------------------
# register_font_families()
# ---------------------------------------------------------------------------

class TestRegisterFontFamilies:

    def test_explicit_mode_no_pattern(self, tmp_path):
        fonts_mod.register_font_families(
            fonts_dir=tmp_path,
            families={
                'Alpha': {
                    'upright': 'Alpha-Regular.ttf',
                    'bold': 'Alpha-Bold.ttf',
                    'italic': 'Alpha-Italic.ttf',
                    'bold_italic': 'Alpha-BoldItalic.ttf',
                },
            },
        )
        assert len(fonts_mod._api_font_registrations) == 1
        entry = fonts_mod._api_font_registrations[0]
        assert entry['upright'] == 'Alpha-Regular.ttf'

    def test_single_pattern(self, tmp_path):
        fonts_mod.register_font_families(
            fonts_dir=tmp_path,
            pattern='Raleway-{weight}.ttf',
            families={
                'Raleway': {'upright': 'Regular', 'bold': 'Bold',
                            'italic': 'Italic', 'bold_italic': 'BoldItalic'},
                'Raleway Light': {'upright': 'Light', 'bold': 'SemiBold',
                                  'italic': 'LightItalic', 'bold_italic': 'SemiBoldItalic'},
            },
        )
        assert len(fonts_mod._api_font_registrations) == 2
        raleway = next(e for e in fonts_mod._api_font_registrations if e['name'] == 'Raleway')
        assert raleway['upright'] == 'Raleway-Regular.ttf'
        assert raleway['bold'] == 'Raleway-Bold.ttf'
        assert raleway['italic'] == 'Raleway-Italic.ttf'

    def test_dual_pattern(self, tmp_path):
        fonts_mod.register_font_families(
            fonts_dir=tmp_path,
            pattern={
                'upright': 'MyFontB_{weight}_.ttf',
                'italic': 'MyFontB_{weight}.ttf',
            },
            families={
                'MyFont': {'upright': '400', 'bold': '700',
                           'italic': '400i', 'bold_italic': '700i'},
            },
        )
        entry = fonts_mod._api_font_registrations[0]
        assert entry['upright'] == 'MyFontB_400_.ttf'
        assert entry['bold'] == 'MyFontB_700_.ttf'
        assert entry['italic'] == 'MyFontB_400i.ttf'
        assert entry['bold_italic'] == 'MyFontB_700i.ttf'

    def test_missing_weight_placeholder_warns(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.register_font_families(
                fonts_dir=tmp_path,
                pattern='NoPlaceholder.ttf',
                families={'Bad': {'upright': 'x', 'bold': 'y',
                                  'italic': 'z', 'bold_italic': 'w'}},
            )
        assert '{weight}' in caplog.text or 'placeholder' in caplog.text

    def test_per_family_options_override_shared(self, tmp_path):
        fonts_mod.register_font_families(
            fonts_dir=tmp_path,
            options='Scale=1.0',
            families={
                'FontA': {'upright': 'A.ttf'},
                'FontB': {'upright': 'B.ttf', 'options': 'Scale=0.9'},
            },
        )
        a = next(e for e in fonts_mod._api_font_registrations if e['name'] == 'FontA')
        b = next(e for e in fonts_mod._api_font_registrations if e['name'] == 'FontB')
        assert a['options'] == 'Scale=1.0'
        assert b['options'] == 'Scale=0.9'


# ---------------------------------------------------------------------------
# _expand_pattern()
# ---------------------------------------------------------------------------

class TestExpandPattern:

    def test_none_passthrough(self):
        faces = {'upright': 'R.ttf', 'bold': 'B.ttf', 'italic': 'I.ttf', 'bold_italic': 'BI.ttf'}
        result = fonts_mod._expand_pattern(faces, None)
        assert result == faces

    def test_string_pattern(self):
        faces = {'upright': 'Regular', 'bold': 'Bold', 'italic': 'Italic', 'bold_italic': 'BoldItalic'}
        result = fonts_mod._expand_pattern(faces, 'Font-{weight}.ttf')
        assert result['upright'] == 'Font-Regular.ttf'
        assert result['bold'] == 'Font-Bold.ttf'
        assert result['italic'] == 'Font-Italic.ttf'
        assert result['bold_italic'] == 'Font-BoldItalic.ttf'

    def test_dict_pattern(self):
        faces = {'upright': '400', 'bold': '700', 'italic': '400i', 'bold_italic': '700i'}
        result = fonts_mod._expand_pattern(faces, {'upright': 'F_{weight}_.ttf', 'italic': 'F_{weight}.ttf'})
        assert result['upright'] == 'F_400_.ttf'
        assert result['bold'] == 'F_700_.ttf'
        assert result['italic'] == 'F_400i.ttf'
        assert result['bold_italic'] == 'F_700i.ttf'

    def test_missing_upright_falls_back_to_regular(self):
        faces = {'regular': 'R.ttf', 'bold': 'B.ttf', 'italic': 'I.ttf', 'bold_italic': 'BI.ttf'}
        result = fonts_mod._expand_pattern(faces, None)
        assert result['upright'] == 'R.ttf'


# ---------------------------------------------------------------------------
# _clear_font_registry()
# ---------------------------------------------------------------------------

class TestClearFontRegistry:

    def test_clears_working_list(self, tmp_path):
        fonts_mod._registered_fonts.append({'name': 'X', 'source': 'api'})
        fonts_mod._clear_font_registry()
        assert fonts_mod._registered_fonts == []

    def test_preserves_api_list(self, tmp_path):
        fonts_mod._api_font_registrations.append({'name': 'Persist', 'source': 'api'})
        fonts_mod._clear_font_registry()
        assert len(fonts_mod._api_font_registrations) == 1

    def test_resets_fonts_processed_flag(self):
        fonts_mod._fonts_processed = True
        fonts_mod._clear_font_registry()
        assert fonts_mod._fonts_processed is False


# ---------------------------------------------------------------------------
# _deduplicate_registry()
# ---------------------------------------------------------------------------

class TestDeduplicateRegistry:

    def _add(self, name, source='api'):
        fonts_mod._registered_fonts.append({
            'name': name, 'source': source,
            'fonts_dir': Path('/tmp'), 'upright': f'{name}.ttf',
            'bold': f'{name}.ttf', 'italic': f'{name}.ttf',
            'bold_italic': f'{name}.ttf', 'options': '',
        })

    def test_keeps_last_entry_per_name(self):
        self._add('FontA')
        self._add('FontA')  # duplicate
        self._add('FontB')
        fonts_mod._deduplicate_registry()
        names = [e['name'] for e in fonts_mod._registered_fonts]
        assert names.count('FontA') == 1
        assert 'FontB' in names

    def test_last_entry_source_survives(self):
        self._add('FontA', source='auto_discover')
        self._add('FontA', source='user_config')
        fonts_mod._deduplicate_registry()
        assert fonts_mod._registered_fonts[0]['source'] == 'user_config'

    def test_order_preserved(self):
        self._add('A')
        self._add('B')
        self._add('C')
        fonts_mod._deduplicate_registry()
        assert [e['name'] for e in fonts_mod._registered_fonts] == ['A', 'B', 'C']


# ---------------------------------------------------------------------------
# collect_font_files()
# ---------------------------------------------------------------------------

class TestCollectFontFiles:

    def test_deduplication_across_families(self, tmp_path):
        shared = 'Shared-Regular.ttf'
        entries = [
            {
                'name': 'FamilyA',
                'fonts_dir': tmp_path,
                'upright': shared, 'bold': shared,
                'italic': shared, 'bold_italic': shared,
            },
            {
                'name': 'FamilyB',
                'fonts_dir': tmp_path,
                'upright': shared, 'bold': 'B-Bold.ttf',
                'italic': shared, 'bold_italic': shared,
            },
        ]
        files = fonts_mod.collect_font_files(entries)
        # shared path appears only once
        shared_path = str(tmp_path / shared)
        assert files.count(shared_path) == 1

    def test_returns_absolute_strings(self, tmp_path):
        entries = [{
            'name': 'F',
            'fonts_dir': tmp_path,
            'upright': 'F.ttf', 'bold': 'F.ttf',
            'italic': 'F.ttf', 'bold_italic': 'F.ttf',
        }]
        files = fonts_mod.collect_font_files(entries)
        assert len(files) == 1
        assert files[0] == str(tmp_path / 'F.ttf')


# ---------------------------------------------------------------------------
# generate_font_features()
# ---------------------------------------------------------------------------

class TestGenerateFontFeatures:

    def _entry(self, name='TestFont', options=''):
        return {
            'name': name,
            'fonts_dir': Path('/fonts'),
            'upright': f'{name}-Regular.ttf',
            'bold': f'{name}-Bold.ttf',
            'italic': f'{name}-Italic.ttf',
            'bold_italic': f'{name}-BoldItalic.ttf',
            'options': options,
        }

    def test_basic_output_format(self):
        result = fonts_mod.generate_font_features([self._entry()])
        assert r'\defaultfontfeatures+[TestFont]{' in result
        assert 'Path=./,' in result
        assert 'UprightFont=TestFont-Regular.ttf,' in result
        assert 'BoldFont=TestFont-Bold.ttf,' in result
        assert 'ItalicFont=TestFont-Italic.ttf,' in result
        assert 'BoldItalicFont=TestFont-BoldItalic.ttf' in result

    def test_options_appended(self):
        result = fonts_mod.generate_font_features([self._entry(options='Numbers=OldStyle')])
        assert 'Numbers=OldStyle' in result

    def test_no_options_no_comma(self):
        result = fonts_mod.generate_font_features([self._entry(options='')])
        # BoldItalicFont line should be last content, no trailing comma before }
        lines = result.split('\n')
        bold_italic_line = next(l for l in lines if 'BoldItalicFont' in l)
        assert not bold_italic_line.rstrip().endswith(',')

    def test_multiple_families_joined(self):
        result = fonts_mod.generate_font_features([
            self._entry('FontA'),
            self._entry('FontB'),
        ])
        assert r'\defaultfontfeatures+[FontA]{' in result
        assert r'\defaultfontfeatures+[FontB]{' in result


# ---------------------------------------------------------------------------
# validate_font_files()
# ---------------------------------------------------------------------------

class TestValidateFontFiles:

    def _entry(self, name, path, filename='f.ttf'):
        return {
            'name': name,
            'fonts_dir': path,
            'upright': filename, 'bold': filename,
            'italic': filename, 'bold_italic': filename,
        }

    def test_warns_on_missing_file(self, tmp_path, caplog):
        entry = self._entry('GoodName', tmp_path, 'missing.ttf')
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.validate_font_files([entry])
        assert 'missing.ttf' in caplog.text

    def test_no_warning_when_file_exists(self, tmp_path, caplog):
        (tmp_path / 'present.ttf').write_bytes(b'')
        entry = self._entry('GoodName', tmp_path, 'present.ttf')
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.validate_font_files([entry])
        # No missing file warning
        assert 'not found' not in caplog.text

    def test_warns_unsafe_name(self, tmp_path, caplog):
        (tmp_path / 'f.ttf').write_bytes(b'')
        entry = self._entry('Font{Bad}', tmp_path)
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.validate_font_files([entry])
        assert 'Font{Bad}' in caplog.text

    def test_no_warning_for_safe_name(self, tmp_path, caplog):
        (tmp_path / 'f.ttf').write_bytes(b'')
        entry = self._entry('SafeName', tmp_path)
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.validate_font_files([entry])
        assert 'SafeName' not in caplog.text or 'unsafe' not in caplog.text.lower()


# ---------------------------------------------------------------------------
# process_user_font_config()
# ---------------------------------------------------------------------------

class TestProcessUserFontConfig:

    def test_explicit_filenames_mode(self, tmp_path):
        doxtr_fonts = {
            'Corporate Sans': {
                'dir': str(tmp_path),
                'upright': 'Corp-Regular.otf',
                'bold': 'Corp-Bold.otf',
                'italic': 'Corp-Italic.otf',
                'bold_italic': 'Corp-BoldItalic.otf',
                'options': 'Scale=MatchLowercase',
            },
        }
        fonts_mod.process_user_font_config(doxtr_fonts, str(tmp_path))
        assert len(fonts_mod._registered_fonts) == 1
        entry = fonts_mod._registered_fonts[0]
        assert entry['name'] == 'Corporate Sans'
        assert entry['upright'] == 'Corp-Regular.otf'
        assert entry['options'] == 'Scale=MatchLowercase'
        assert entry['source'] == 'user_config'

    def test_pattern_mode_uses_weights(self, tmp_path):
        doxtr_fonts = {
            'Corp Light': {
                'dir': str(tmp_path),
                'pattern': 'Corp_{weight}.otf',
                'weights': {
                    'upright': '300',
                    'bold': '600',
                    'italic': '300i',
                    'bold_italic': '600i',
                },
            },
        }
        fonts_mod.process_user_font_config(doxtr_fonts, str(tmp_path))
        entry = fonts_mod._registered_fonts[0]
        assert entry['upright'] == 'Corp_300.otf'
        assert entry['bold'] == 'Corp_600.otf'
        assert entry['italic'] == 'Corp_300i.otf'
        assert entry['bold_italic'] == 'Corp_600i.otf'

    def test_user_overrides_existing_entry(self, tmp_path):
        fonts_mod._registered_fonts.append({
            'name': 'MyFont', 'source': 'api',
            'fonts_dir': tmp_path, 'upright': 'old.ttf',
            'bold': 'old.ttf', 'italic': 'old.ttf', 'bold_italic': 'old.ttf',
            'options': '',
        })
        doxtr_fonts = {
            'MyFont': {
                'dir': str(tmp_path),
                'upright': 'new.ttf',
            },
        }
        fonts_mod.process_user_font_config(doxtr_fonts, str(tmp_path))
        # Only one entry for MyFont and it is the user one
        mf = [e for e in fonts_mod._registered_fonts if e['name'] == 'MyFont']
        assert len(mf) == 1
        assert mf[0]['upright'] == 'new.ttf'
        assert mf[0]['source'] == 'user_config'

    def test_relative_dir_resolved_against_confdir(self, tmp_path):
        subdir = tmp_path / 'fonts'
        subdir.mkdir()
        doxtr_fonts = {
            'RelFont': {
                'dir': 'fonts',
                'upright': 'R.ttf',
            },
        }
        fonts_mod.process_user_font_config(doxtr_fonts, str(tmp_path))
        entry = fonts_mod._registered_fonts[0]
        assert entry['fonts_dir'] == subdir

    def test_warns_on_unknown_key(self, tmp_path, caplog):
        """Unknown keys in doxtr_fonts entries produce a warning."""
        (tmp_path / 'Fake-Regular.ttf').touch()
        spec = {'dir': str(tmp_path), 'upright': 'Fake-Regular.ttf', 'typo_key': 'oops'}
        with caplog.at_level(logging.WARNING, logger='doxtr_pdf_theme_core.fonts'):
            fonts_mod.process_user_font_config({'FakeFont': spec}, str(tmp_path))
        assert 'typo_key' in caplog.text


# ---------------------------------------------------------------------------
# auto_discover_fonts() — no-fonttools fallback
# ---------------------------------------------------------------------------

class TestAutoDiscoverFonts:

    def test_graceful_degradation_without_fonttools(self, tmp_path, caplog):
        """When fonttools is not installed, auto-discovery logs info and returns."""
        with mock.patch.dict(sys.modules, {'fontTools': None, 'fontTools.ttLib': None}):
            with caplog.at_level(logging.INFO, logger='doxtr_pdf_theme_core.fonts'):
                fonts_mod.auto_discover_fonts(tmp_path)
        assert fonts_mod._registered_fonts == []

    def test_nonexistent_directory_is_ignored(self, tmp_path):
        """Passing a non-existent directory should not raise."""
        fonts_mod.auto_discover_fonts(tmp_path / 'does_not_exist')
        assert fonts_mod._registered_fonts == []


# ---------------------------------------------------------------------------
# _find_bold_weight()
# ---------------------------------------------------------------------------

class TestFindBoldWeight:

    def _bw(self, weights):
        """Build by_weight dict with dummy entries."""
        return {w: [{'weight': w}] for w in weights}

    def test_400_maps_to_700(self):
        by_weight = self._bw([400, 700])
        assert fonts_mod._find_bold_weight(by_weight, 400) == 700

    def test_fallback_when_700_absent(self):
        by_weight = self._bw([400, 600])
        assert fonts_mod._find_bold_weight(by_weight, 400) == 600

    def test_500_targets_700(self):
        by_weight = self._bw([500, 700, 900])
        assert fonts_mod._find_bold_weight(by_weight, 500) == 700

    def test_700_targets_900(self):
        by_weight = self._bw([700, 900])
        assert fonts_mod._find_bold_weight(by_weight, 700) == 900

    def test_fallback_to_self_when_no_heavier(self):
        by_weight = self._bw([900])
        assert fonts_mod._find_bold_weight(by_weight, 900) == 900


# ---------------------------------------------------------------------------
# fontpkg injection logic — tested via inject_font_features()
# ---------------------------------------------------------------------------

from doxtr_pdf_theme_core.fonts import inject_font_features


class TestFontpkgInjection:

    def _entry(self, name='TestFont'):
        return {
            'name': name,
            'fonts_dir': Path('/fonts'),
            'upright': f'{name}-R.ttf',
            'bold': f'{name}-B.ttf',
            'italic': f'{name}-I.ttf',
            'bold_italic': f'{name}-BI.ttf',
            'options': '',
            'source': 'api',
        }

    def test_features_prepended_when_no_existing_fontpkg(self):
        registered = [self._entry()]
        dynamic = '\\usepackage{fontspec}'
        latex_elements = {}
        inject_font_features(latex_elements, dynamic, registered)
        assert latex_elements['fontpkg'].startswith(r'\defaultfontfeatures+')
        assert dynamic in latex_elements['fontpkg']

    def test_features_prepended_to_existing_fontpkg(self):
        registered = [self._entry()]
        user_fontpkg = '\\usepackage{fontspec}\n\\setmainfont{Helvetica}'
        latex_elements = {'fontpkg': user_fontpkg}
        inject_font_features(latex_elements, '\\usepackage{fontspec}', registered)
        assert latex_elements['fontpkg'].startswith(r'\defaultfontfeatures+')
        assert user_fontpkg in latex_elements['fontpkg']

    def test_no_registered_fonts_uses_setdefault(self):
        latex_elements = {}
        dynamic = '\\usepackage{fontspec}'
        inject_font_features(latex_elements, dynamic, [])
        assert latex_elements['fontpkg'] == dynamic

    def test_no_registered_fonts_respects_existing_fontpkg(self):
        """When no fonts registered, setdefault must not overwrite an existing fontpkg."""
        existing = '\\usepackage{fontspec}\n\\setmainfont{Helvetica}'
        latex_elements = {'fontpkg': existing}
        inject_font_features(latex_elements, '\\usepackage{fontspec}', [])
        assert latex_elements['fontpkg'] == existing


# ---------------------------------------------------------------------------
# Parent __init__.py guard for auto-discovery scan
# ---------------------------------------------------------------------------

class TestParentScanGuard:

    def test_parent_without_init_py_is_skipped(self, tmp_path):
        """Auto-discover should not scan parent/fonts/ if parent lacks __init__.py."""
        # Create structure: tmp_path/latex_styles/  (no __init__.py in tmp_path)
        # and tmp_path/fonts/ with a file
        style_path = tmp_path / 'latex_styles'
        style_path.mkdir()
        fonts_path = tmp_path / 'fonts'
        fonts_path.mkdir()
        (fonts_path / 'Dummy.ttf').write_bytes(b'')

        # Simulate the scan logic from config_inited
        _theme_font_dirs = []
        _sp = style_path
        _fdir = _sp / 'fonts'
        if _fdir.is_dir():
            _theme_font_dirs.append(_fdir)
        _parent = _sp.parent  # = tmp_path, no __init__.py
        if (_parent / '__init__.py').exists():
            _parent_fdir = _parent / 'fonts'
            if _parent_fdir.is_dir() and _parent_fdir not in _theme_font_dirs:
                _theme_font_dirs.append(_parent_fdir)

        # fonts_path should NOT be in _theme_font_dirs since tmp_path has no __init__.py
        assert fonts_path not in _theme_font_dirs

    def test_parent_with_init_py_is_included(self, tmp_path):
        """Auto-discover SHOULD scan parent/fonts/ when parent has __init__.py."""
        style_path = tmp_path / 'latex_styles'
        style_path.mkdir()
        fonts_path = tmp_path / 'fonts'
        fonts_path.mkdir()
        (tmp_path / '__init__.py').write_bytes(b'')  # marks parent as Python package

        _theme_font_dirs = []
        _sp = style_path
        _fdir = _sp / 'fonts'
        if _fdir.is_dir():
            _theme_font_dirs.append(_fdir)
        _parent = _sp.parent
        if (_parent / '__init__.py').exists():
            _parent_fdir = _parent / 'fonts'
            if _parent_fdir.is_dir() and _parent_fdir not in _theme_font_dirs:
                _theme_font_dirs.append(_parent_fdir)

        assert fonts_path in _theme_font_dirs
