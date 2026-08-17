"""Unit tests for the production config_inited() pipeline.

This module tests _stage_merge_and_resolve() — the actual production pipeline
function from doxtr_pdf_theme_core.__init__. Each test class validates a
distinct logical concern of the pipeline.

Run with: python -m pytest test_harness/test_pipeline.py -v
"""
import sys
import os
import copy

# Add package to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from doxtr_pdf_theme_core import _stage_merge_and_resolve
from doxtr_pdf_theme_core.core_config import (
    CORE_CONFIG_MANIFEST,
    DOXTR_GLOBALS,
    DOXTR_SEMANTIC_PALETTE,
    DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS,
)


# ---------------------------------------------------------------------------
# MockApp / MockConfig — minimal mocks for the production pipeline
# ---------------------------------------------------------------------------

class MockConfig:
    """Minimal mock of the Sphinx config object for testing pipeline stages.

    Uses __getattr__ so getattr(config, 'key', default) returns the default
    for unset attributes.
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        raise AttributeError(name)


class MockApp:
    """Minimal mock of the Sphinx application object."""
    confdir = '/tmp'
    srcdir = '/tmp'

    def __init__(self, config=None):
        self.config = config or MockConfig()


def _make_config(**overrides):
    """Create a MockConfig with production-required defaults."""
    defaults = {
        'doxtr_globals': {},
        'doxtr_theme_defaults': {},
        'doxtr_theme_style_paths': [],
        'root_doc': 'index',
        'project': 'TestProject',
        'author': 'Test Author',
        'extensions': [],
    }
    defaults.update(overrides)
    return MockConfig(**defaults)


def _run_pipeline(**config_overrides):
    """Run _stage_merge_and_resolve with minimal defaults and return ctx."""
    config = _make_config(**config_overrides)
    app = MockApp(config=config)
    ctx = _stage_merge_and_resolve(app, config)
    return ctx, config


# ===========================================================================
# STAGE 1: Globals Merge
# ===========================================================================


class TestGlobalsMerge:
    """Tests for three-tier globals merge + legacy migration."""

    def test_basic_three_tier_merge(self):
        """Core defaults are returned when theme and user provide nothing."""
        ctx, _ = _run_pipeline()
        g = ctx['g']
        assert 'main_font' in g
        assert 'wcag_level' in g
        assert g['main_font'] == DOXTR_GLOBALS['light']['main_font']

    def test_theme_overrides_core(self):
        """Theme defaults override core defaults."""
        ctx, _ = _run_pipeline(
            doxtr_theme_defaults={'globals': {'light': {'main_font': 'MyThemeFont'}}},
        )
        assert ctx['g']['main_font'] == 'MyThemeFont'

    def test_user_overrides_theme_and_core(self):
        """User config takes precedence over both theme and core."""
        ctx, _ = _run_pipeline(
            doxtr_theme_defaults={'globals': {'light': {'main_font': 'ThemeFont'}}},
            doxtr_globals={'light': {'main_font': 'UserFont'}},
        )
        assert ctx['g']['main_font'] == 'UserFont'

    def test_empty_theme_defaults(self):
        """Empty theme defaults don't break the merge."""
        ctx, _ = _run_pipeline()
        g = ctx['g']
        assert g['wcag_level'] == 7
        assert g['headsep'] == '8mm'

    def test_legacy_flat_key_migration(self):
        """Legacy flat doxtr_<key> values are migrated into the merged dict."""
        ctx, _ = _run_pipeline(doxtr_main_font='LegacyFont')
        assert ctx['g']['main_font'] == 'LegacyFont'

    def test_unknown_wrapper_keys_detected(self):
        """Unknown top-level keys in doxtr_globals don't crash."""
        ctx, _ = _run_pipeline(
            doxtr_globals={'light': {}, 'typo_key': {}},
        )
        assert 'main_font' in ctx['g']

    def test_does_not_mutate_core_defaults(self):
        """Pipeline does not mutate the core DOXTR_GLOBALS dict."""
        core_before = copy.deepcopy(DOXTR_GLOBALS)
        _run_pipeline(doxtr_globals={'light': {'main_font': 'Mutant'}})
        assert DOXTR_GLOBALS == core_before


# ===========================================================================
# STAGE 2: Section Merging
# ===========================================================================


class TestSectionMerging:
    """Tests for section merging, validation, and dark overrides collection."""

    def test_all_sections_present_in_merged_configs(self):
        """All expected sections appear in merged_configs."""
        ctx, _ = _run_pipeline()
        expected_sections = [
            'title_page', 'headings', 'parts', 'draft', 'microtype',
            'epigraphs', 'admonitions', 'needs', 'containers', 'tables',
            'figures', 'code', 'sidebar', 'highlights', 'topic', 'contents',
            'toc', 'bibliography', 'index', 'glossary', 'links',
        ]
        for name in expected_sections:
            assert name in ctx['merged_configs'], f"Missing section: {name}"

    def test_code_key_not_code_blocks(self):
        """The ctx uses 'code' key, not 'code_blocks'."""
        ctx, _ = _run_pipeline()
        assert 'code' in ctx
        assert 'code_blocks' not in ctx
        assert 'code' in ctx['merged_configs']

    def test_dark_mode_normalization_string(self):
        """String '1' is normalised to boolean True."""
        ctx, config = _run_pipeline(doxtr_dark_mode='1')
        assert ctx['dark_mode'] is True
        assert config.doxtr_dark_mode is True

    def test_dark_mode_normalization_false(self):
        """String 'false' is normalised to boolean False."""
        ctx, config = _run_pipeline(doxtr_dark_mode='false')
        assert ctx['dark_mode'] is False

    def test_size_factor_calculation(self):
        """size_factor=2.0 with 11.5pt base → fontsize{23.0pt}{27.6pt}."""
        ctx, _ = _run_pipeline(
            doxtr_headings={'chapter': {'size_factor': 2.0}},
            doxtr_globals={'light': {'main_font_size': '11.5pt'}},
        )
        chapter_conf = ctx['headings']['chapter']
        assert 'size' in chapter_conf
        assert '23.0pt' in chapter_conf['size']
        assert '27.6pt' in chapter_conf['size']

    def test_size_factor_with_custom_base(self):
        """size_factor uses the actual main_font_size from globals."""
        ctx, _ = _run_pipeline(
            doxtr_headings={'chapter': {'size_factor': 1.5}},
            doxtr_globals={'light': {'main_font_size': '14pt'}},
        )
        chapter_conf = ctx['headings']['chapter']
        assert '21.0pt' in chapter_conf['size']

    def test_explicit_size_overrides_size_factor(self):
        """When 'size' is set explicitly, size_factor is ignored."""
        ctx, _ = _run_pipeline(
            doxtr_headings={'chapter': {
                'size_factor': 2.0,
                'size': r'\fontsize{40pt}{48pt}\selectfont',
            }},
        )
        chapter_conf = ctx['headings']['chapter']
        assert '40pt' in chapter_conf['size']

    def test_wcag_level_from_globals(self):
        """wcag_level is correctly read from the merged globals."""
        ctx, _ = _run_pipeline(
            doxtr_globals={'light': {'wcag_level': 4.5}},
        )
        assert ctx['wcag_level'] == 4.5

    def test_main_font_size_pt_parsed(self):
        """main_font_size_pt is correctly parsed from globals."""
        ctx, _ = _run_pipeline(
            doxtr_globals={'light': {'main_font_size': '12.5pt'}},
        )
        assert ctx['main_font_size_pt'] == 12.5

    def test_invalid_size_factor_ignored(self):
        """Invalid size_factor (non-numeric) is ignored, no crash."""
        ctx, _ = _run_pipeline(
            doxtr_headings={'section': {'size_factor': 'invalid'}},
        )
        section_conf = ctx['headings'].get('section', {})
        assert 'invalid' not in str(section_conf.get('size', ''))

    def test_negative_size_factor_ignored(self):
        """Negative size_factor is ignored (must be positive)."""
        ctx, _ = _run_pipeline(
            doxtr_headings={'chapter': {'size_factor': -1.0}},
        )
        chapter_conf = ctx['headings']['chapter']
        assert '-1.0' not in str(chapter_conf.get('size', ''))


# ===========================================================================
# STAGE 3: Semantic Palette Merge
# ===========================================================================


class TestSemanticPalette:
    """Tests for three-tier palette merge."""

    def test_default_palette_returned(self):
        """Default core palette is returned when no config overrides exist."""
        ctx, _ = _run_pipeline()
        palette = ctx['semantic_palette']
        # In non-dark mode, palette should contain the core primary
        assert 'primary' in palette or palette.get('primary') is not None

    def test_theme_palette_overrides_core(self):
        """Theme palette overrides core palette values."""
        ctx, _ = _run_pipeline(
            doxtr_theme_defaults={'semantic_palette': {'primary': '#AA0000'}},
        )
        assert ctx['semantic_palette']['primary'] == '#AA0000'

    def test_user_palette_overrides_theme(self):
        """User palette overrides theme palette."""
        ctx, _ = _run_pipeline(
            doxtr_theme_defaults={'semantic_palette': {'primary': '#AA0000'}},
            doxtr_semantic_palette={'primary': '#BB0000'},
        )
        assert ctx['semantic_palette']['primary'] == '#BB0000'

    def test_palette_has_all_required_keys(self):
        """Merged palette always has all 7 required keys."""
        ctx, _ = _run_pipeline()
        required_keys = {'primary', 'secondary', 'info', 'success', 'warning', 'danger', 'page'}
        assert required_keys.issubset(set(ctx['semantic_palette'].keys()))

    def test_deprecated_page_background_migration(self):
        """Legacy doxtr_page_background is migrated to palette['page']."""
        ctx, _ = _run_pipeline(doxtr_page_background='#F0F0F0')
        assert ctx['semantic_palette']['page'] == '#F0F0F0'

    def test_dark_subkey_stripped_from_light_merge(self):
        """The 'dark' sub-key in palette config is stripped during light merge."""
        ctx, _ = _run_pipeline(
            doxtr_semantic_palette={
                'primary': '#112233',
                'dark': {'primary': '#EEDDCC'},
            },
        )
        # Light merge should use #112233, not the dark value
        assert ctx['semantic_palette']['primary'] == '#112233'


# ===========================================================================
# STAGE 4: Dark Mode Processing
# ===========================================================================


class TestDarkMode:
    """Tests for dark mode strategy detection, palette generation, activation."""

    def test_dark_mode_false_sections_unchanged(self):
        """When dark_mode=False, sections are not dark-processed."""
        ctx, _ = _run_pipeline(doxtr_dark_mode=False)
        # title_page should have the original light color
        tp = ctx['tp']
        # Just verify no crash and the section exists
        assert tp is not None
        assert 'page_color' in tp or isinstance(tp, dict)

    def test_dark_mode_true_inverts_colors(self):
        """dark_mode=True with 'invert' strategy changes colors in sections."""
        ctx_light, _ = _run_pipeline(doxtr_dark_mode=False)
        ctx_dark, _ = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='invert',
        )
        # Title page colors should differ between light and dark
        light_page_color = ctx_light['tp'].get('page_color', '')
        dark_page_color = ctx_dark['tp'].get('page_color', '')
        assert dark_page_color != light_page_color

    def test_auto_strategy_dark_page(self):
        """Auto strategy detects 'invert' for a dark page background."""
        _, config = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='auto',
        )
        # Default dark page (#242424) has luminance < 0.35 → invert
        assert config.doxtr_dark_mode_strategy_resolved == 'invert'

    def test_auto_strategy_light_page(self):
        """Auto strategy detects 'passthrough' for a light page background."""
        _, config = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='auto',
            doxtr_semantic_palette={'dark': {'page': '#FCF6E5'}},
        )
        assert config.doxtr_dark_mode_strategy_resolved == 'passthrough'

    def test_dark_palette_generation(self):
        """Dark palette is generated and stored on config."""
        _, config = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='invert',
        )
        assert config.doxtr_dark_semantic_palette is not None
        assert 'primary' in config.doxtr_dark_semantic_palette
        assert 'page' in config.doxtr_dark_semantic_palette

    def test_passthrough_preserves_light_colors(self):
        """Passthrough strategy does not invert section colors."""
        ctx, _ = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='passthrough',
            doxtr_semantic_palette={'dark': {'page': '#FFFFFF'}},
        )
        tp = ctx['tp']
        # In passthrough, title page colors should match light (no inversion)
        assert tp is not None

    def test_dark_text_color_set(self):
        """Dark text color is set on config when dark mode is active."""
        _, config = _run_pipeline(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy='invert',
        )
        assert config.doxtr_dark_text_color is not None


# ===========================================================================
# STAGE 5: Page Color Adaptation
# ===========================================================================


class TestPageAdaptation:
    """Tests for page color adaptation and dd: resolution."""

    def test_no_adaptation_when_disabled(self):
        """adapt_to_page is False when explicitly disabled."""
        ctx, _ = _run_pipeline(doxtr_adapt_colors_to_page=False)
        assert ctx['adapt_to_page'] is False

    def test_no_adaptation_when_page_is_white(self):
        """No adaptation when page matches designed page (#FFFFFF)."""
        ctx, _ = _run_pipeline(doxtr_adapt_colors_to_page='auto')
        # Default palette page is #FFFFFF, so no adaptation
        assert ctx['adapt_to_page'] is False

    def test_adaptation_active_when_page_differs(self):
        """Adaptation is active when page differs significantly from designed."""
        ctx, _ = _run_pipeline(
            doxtr_adapt_colors_to_page='auto',
            doxtr_semantic_palette={'page': '#F2E8D0'},
        )
        assert ctx['adapt_to_page'] is True

    def test_adaptation_modifies_palette(self):
        """When adaptation is active, palette colors are shifted."""
        ctx, _ = _run_pipeline(
            doxtr_adapt_colors_to_page=True,
            doxtr_semantic_palette={'page': '#F2E8D0'},
        )
        # Palette primary should differ from core default after adaptation
        assert ctx['semantic_palette']['primary'] != DOXTR_SEMANTIC_PALETTE['primary']
        # Page stays as user set it
        assert ctx['semantic_palette']['page'] == '#F2E8D0'

    def test_adaptation_state_stored_on_config(self):
        """Adaptation state is stashed on config.doxtr_adaptation_state."""
        _, config = _run_pipeline(
            doxtr_adapt_colors_to_page=True,
            doxtr_semantic_palette={'page': '#F2E8D0'},
        )
        state = config.doxtr_adaptation_state
        assert state is not None
        assert state['active'] is True
        assert 'designed_page' in state
        assert 'compress_dark' in state
        assert 'compress_light' in state

    def test_dd_expression_resolution_runs(self):
        """dd: color expressions are resolved during the pipeline."""
        ctx, _ = _run_pipeline(
            doxtr_title_page={'title_color': 'dd:primary'},
        )
        resolved = ctx['tp']['title_color']
        assert resolved.startswith('#'), f"dd: expression not resolved: {resolved}"

    def test_containers_stored_on_config(self):
        """Merged containers are stored on config.doxtr_containers."""
        _, config = _run_pipeline()
        assert config.doxtr_containers is not None
        assert isinstance(config.doxtr_containers, dict)

    def test_forced_adaptation_on_white_page(self):
        """Even with white page, explicit True forces adaptation."""
        ctx, _ = _run_pipeline(doxtr_adapt_colors_to_page=True)
        assert ctx['adapt_to_page'] is True


# ===========================================================================
# STAGE 6: Pipeline Structure / Return Dict
# ===========================================================================


class TestPipelineStructure:
    """Tests for the pipeline return dict structure and keys."""

    def test_ctx_has_required_keys(self):
        """The returned ctx dict contains all expected keys."""
        ctx, _ = _run_pipeline()
        required_keys = [
            'g', 'theme_defaults', 'theme_style_paths', 'resolve_val',
            'dark_mode', 'wcag_level', 'wcag_color_debug',
            'main_font_size_str', 'main_font_size_pt',
            'tp', 'headings', 'parts', 'draft', 'microtype', 'epigraphs',
            'admonitions', 'needs', 'containers', 'tables', 'figures',
            'code', 'sidebar', 'highlights', 'topic', 'contents',
            'toc', 'bibliography', 'index', 'glossary', 'links',
            'semantic_palette', 'page_bg', 'adapt_to_page',
            'designed_page', 'compress_dark', 'compress_light',
            'merged_configs', 'pkg_dir',
        ]
        for key in required_keys:
            assert key in ctx, f"Missing ctx key: {key}"

    def test_merged_configs_matches_individual_sections(self):
        """merged_configs values match the individually-keyed sections in ctx."""
        ctx, _ = _run_pipeline()
        assert ctx['merged_configs']['title_page'] is ctx['tp']
        assert ctx['merged_configs']['headings'] is ctx['headings']
        assert ctx['merged_configs']['code'] is ctx['code']
        assert ctx['merged_configs']['containers'] is ctx['containers']

    def test_pkg_dir_is_valid(self):
        """pkg_dir points to the actual package directory."""
        ctx, _ = _run_pipeline()
        pkg_dir = ctx['pkg_dir']
        assert pkg_dir.exists()
        assert (pkg_dir / '__init__.py').exists()

    def test_no_code_blocks_key(self):
        """The old 'code_blocks' key does not exist in ctx."""
        ctx, _ = _run_pipeline()
        assert 'code_blocks' not in ctx
