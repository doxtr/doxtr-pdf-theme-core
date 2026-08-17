"""Unit tests for Phase 4 Extensibility Enhancements (4.1, 4.4, 4.5).

Tests cover:
- 4.1: register_color_operation() — custom dd: expression operations
- 4.4: register_config_transform() — post-merge config transform hooks
- 4.5: wcag_pairs parameter on register_style_type()

Run with: python -m pytest test_harness/test_extensibility_phase4.py -v
"""
import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from doxtr_pdf_theme_core.utils import (
    register_color_operation,
    _custom_color_operations,
    _BUILTIN_COLOR_OPERATIONS,
    resolve_color,
)
from doxtr_pdf_theme_core import (
    register_config_transform,
    register_style_type,
    _config_transform_hooks,
    _custom_style_types,
    _stage_merge_and_resolve,
)
from doxtr_pdf_theme_core.core_config import (
    CORE_CONFIG_MANIFEST,
    DOXTR_GLOBALS,
    DOXTR_SEMANTIC_PALETTE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registries():
    """Ensure registries are clean before and after each test."""
    _custom_color_operations.clear()
    _config_transform_hooks.clear()
    # Save and restore _custom_style_types
    saved = _custom_style_types.copy()
    yield
    _custom_color_operations.clear()
    _config_transform_hooks.clear()
    _custom_style_types.clear()
    _custom_style_types.extend(saved)


# ---------------------------------------------------------------------------
# MockApp / MockConfig (same pattern as test_pipeline.py)
# ---------------------------------------------------------------------------

class MockConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        raise AttributeError(name)


class MockApp:
    confdir = '/tmp'
    srcdir = '/tmp'


# ===========================================================================
# Part A: register_color_operation (4.1)
# ===========================================================================

class TestRegisterColorOperation:
    """Tests for the custom color operation registry."""

    def test_register_valid_operation(self):
        """A valid operation can be registered and appears in the registry."""
        def my_op(color, arg):
            return color

        register_color_operation('my_op', my_op)
        assert 'my_op' in _custom_color_operations
        assert _custom_color_operations['my_op'] is my_op

    def test_rejects_builtin_name_lighten(self):
        """Cannot register an operation named 'lighten'."""
        with pytest.raises(ValueError, match="conflicts with a built-in"):
            register_color_operation('lighten', lambda c, a: c)

    def test_rejects_builtin_name_darken(self):
        """Cannot register an operation named 'darken'."""
        with pytest.raises(ValueError, match="conflicts with a built-in"):
            register_color_operation('darken', lambda c, a: c)

    def test_rejects_builtin_name_contrast(self):
        """Cannot register an operation named 'contrast'."""
        with pytest.raises(ValueError, match="conflicts with a built-in"):
            register_color_operation('contrast', lambda c, a: c)

    def test_rejects_non_callable(self):
        """Raises TypeError for non-callable fn."""
        with pytest.raises(TypeError, match="fn must be callable"):
            register_color_operation('my_op', 'not_a_function')

    def test_rejects_empty_name(self):
        """Raises ValueError for empty name."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_color_operation('', lambda c, a: c)

    def test_rejects_none_name(self):
        """Raises ValueError for None name."""
        with pytest.raises(ValueError, match="non-empty string"):
            register_color_operation(None, lambda c, a: c)

    def test_custom_operation_invoked_in_dd_expression(self):
        """A registered operation is invoked when resolving a dd: expression."""
        def desaturate(color, arg):
            # Simple test: return a fixed known color
            return '#AABBCC'

        register_color_operation('desaturate', desaturate)

        # Resolve a dd: expression using our custom operation
        palette = {'primary': '#FF0000'}
        result = resolve_color(
            'dd:primary:desaturate:50',
            palette=palette,
            page_bg='#FFFFFF',
            current_section='test',
            current_dict={},
            theme_defaults={},
            core_config={},
            user_config={},
        )
        assert result == '#AABBCC'

    def test_custom_operation_receives_correct_args(self):
        """The custom operation receives the resolved color and the argument string."""
        received = {}

        def capture_op(color, arg):
            received['color'] = color
            received['arg'] = arg
            return '#112233'

        register_color_operation('capture', capture_op)

        palette = {'primary': '#FF0000'}
        result = resolve_color(
            'dd:primary:capture:75',
            palette=palette,
            page_bg='#FFFFFF',
            current_section='test',
            current_dict={},
            theme_defaults={},
            core_config={},
            user_config={},
        )
        assert result == '#112233'
        assert received['color'] == '#FF0000'
        assert received['arg'] == '75'

    def test_custom_operation_error_handled_gracefully(self):
        """If a custom operation raises, it should not crash — returns error fallback."""
        def bad_op(color, arg):
            raise RuntimeError("intentional failure")

        register_color_operation('bad_op', bad_op)

        palette = {'primary': '#00FF00'}
        # Should not raise — returns the _error fallback color (#ff0000)
        result = resolve_color(
            'dd:primary:bad_op:50',
            palette=palette,
            page_bg='#FFFFFF',
            current_section='test',
            current_dict={},
            theme_defaults={},
            core_config={},
            user_config={},
        )
        # _error() returns '#ff0000' as a safe fallback and logs a warning
        assert result == '#ff0000'

    def test_custom_operation_with_no_arg(self):
        """Custom operation receives empty string when no arg provided."""
        received = {}

        def no_arg_op(color, arg):
            received['arg'] = arg
            return '#ABCDEF'

        register_color_operation('noarg', no_arg_op)

        palette = {'primary': '#FF0000'}
        result = resolve_color(
            'dd:primary:noarg',
            palette=palette,
            page_bg='#FFFFFF',
            current_section='test',
            current_dict={},
            theme_defaults={},
            core_config={},
            user_config={},
        )
        # With no :arg suffix, arg should be empty string
        assert received['arg'] == ''
        assert result == '#ABCDEF'

    def test_builtin_operations_constant_complete(self):
        """The _BUILTIN_COLOR_OPERATIONS frozenset contains expected names."""
        assert _BUILTIN_COLOR_OPERATIONS == frozenset({'lighten', 'darken', 'contrast'})


# ===========================================================================
# Part B: register_config_transform (4.4)
# ===========================================================================

class TestRegisterConfigTransform:
    """Tests for the post-merge config transform hook registry."""

    def test_register_valid_transform(self):
        """A valid transform function can be registered."""
        def my_transform(sections, palette, config):
            pass

        register_config_transform(my_transform)
        assert my_transform in _config_transform_hooks

    def test_rejects_non_callable(self):
        """Raises TypeError for non-callable."""
        with pytest.raises(TypeError, match="fn must be callable"):
            register_config_transform("not_callable")

    def test_transform_invoked_in_pipeline(self):
        """Registered transforms are called during _stage_merge_and_resolve."""
        called = {'count': 0, 'sections': None, 'palette': None}

        def my_transform(sections, palette, config):
            called['count'] += 1
            called['sections'] = sections
            called['palette'] = palette

        register_config_transform(my_transform)

        config = MockConfig(
            latex_engine='lualatex',
            latex_docclass={'manual': 'scrbook'},
            latex_documents=[],
            project='Test',
            author='Author',
            root_doc='index',
            release='1.0',
            version='1.0',
            doxtr_globals={'light': {}},
            doxtr_dark_mode=False,
            doxtr_semantic_palette={},
        )

        app = MockApp()
        _stage_merge_and_resolve(app, config)

        assert called['count'] == 1
        assert called['sections'] is not None
        assert 'containers' in called['sections']
        assert 'headings' in called['sections']
        assert called['palette'] is not None
        assert 'primary' in called['palette']

    def test_transform_can_mutate_sections(self):
        """Transforms can mutate sections in-place and the changes persist in ctx."""
        def force_font(sections, palette, config):
            sections['sidebar']['title_font'] = 'ForcedFont'

        register_config_transform(force_font)

        config = MockConfig(
            latex_engine='lualatex',
            latex_docclass={'manual': 'scrbook'},
            latex_documents=[],
            project='Test',
            author='Author',
            root_doc='index',
            release='1.0',
            version='1.0',
            doxtr_globals={'light': {}},
            doxtr_dark_mode=False,
            doxtr_semantic_palette={},
        )

        app = MockApp()
        ctx = _stage_merge_and_resolve(app, config)

        assert ctx['sidebar']['title_font'] == 'ForcedFont'

    def test_multiple_transforms_run_in_order(self):
        """Multiple transforms run in registration order."""
        order = []

        def first(sections, palette, config):
            order.append('first')
            sections['sidebar']['title_font'] = 'First'

        def second(sections, palette, config):
            order.append('second')
            # Should see 'First' from the first transform
            assert sections['sidebar']['title_font'] == 'First'
            sections['sidebar']['title_font'] = 'Second'

        register_config_transform(first)
        register_config_transform(second)

        config = MockConfig(
            latex_engine='lualatex',
            latex_docclass={'manual': 'scrbook'},
            latex_documents=[],
            project='Test',
            author='Author',
            root_doc='index',
            release='1.0',
            version='1.0',
            doxtr_globals={'light': {}},
            doxtr_dark_mode=False,
            doxtr_semantic_palette={},
        )

        app = MockApp()
        ctx = _stage_merge_and_resolve(app, config)

        assert order == ['first', 'second']
        assert ctx['sidebar']['title_font'] == 'Second'


# ===========================================================================
# Part C: wcag_pairs on register_style_type (4.5)
# ===========================================================================

class TestWcagPairsStyleType:
    """Tests for wcag_pairs parameter on register_style_type()."""

    def test_wcag_pairs_stored_in_registry(self):
        """wcag_pairs is stored in the registered style type dict."""
        register_style_type(
            name='testbox',
            subdir='testbox',
            fallback_fn=lambda _: '% empty',
            config_section_factory=lambda: {
                'style': 'default',
                'title_font_color': '#FFFFFF',
                'title_background_color': '#000000',
            },
            color_keys=['title_font_color', 'title_background_color'],
            wcag_pairs=[('title_font_color', 'title_background_color')],
        )

        registered = next(st for st in _custom_style_types if st['name'] == 'testbox')
        assert registered['wcag_pairs'] == [('title_font_color', 'title_background_color')]

    def test_wcag_pairs_defaults_to_empty_list(self):
        """When wcag_pairs is not specified, it defaults to an empty list."""
        register_style_type(
            name='testbox2',
            subdir='testbox2',
            fallback_fn=lambda _: '% empty',
        )

        registered = next(st for st in _custom_style_types if st['name'] == 'testbox2')
        assert registered['wcag_pairs'] == []

    def test_wcag_pairs_none_defaults_to_empty(self):
        """Explicit None for wcag_pairs stored as empty list."""
        register_style_type(
            name='testbox3',
            subdir='testbox3',
            fallback_fn=lambda _: '% empty',
            wcag_pairs=None,
        )

        registered = next(st for st in _custom_style_types if st['name'] == 'testbox3')
        assert registered['wcag_pairs'] == []

    def test_style_type_signature_accepts_wcag_pairs(self):
        """register_style_type accepts wcag_pairs without error."""
        # Should not raise
        register_style_type(
            name='testbox4',
            subdir='testbox4',
            fallback_fn='% empty',
            config_section_factory=lambda: {'style': 'default'},
            color_keys=[],
            preamble_var='doxtr_rendered_testbox4',
            wcag_pairs=[('a', 'b'), ('c', 'd')],
        )
        registered = next(st for st in _custom_style_types if st['name'] == 'testbox4')
        assert registered['wcag_pairs'] == [('a', 'b'), ('c', 'd')]
