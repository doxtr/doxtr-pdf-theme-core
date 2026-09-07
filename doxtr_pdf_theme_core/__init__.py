"""Doxtr PDF Theme Core - A Sphinx extension for professional LaTeX/PDF output.

This package provides a base layer for generating professional LaTeX → PDF output.
It is designed to be inherited by child themes that customize the look and feel.
"""
import copy
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from sphinx.util import logging
from jinja2 import Environment
from sphinx.writers.latex import LaTeXTranslator
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.errors import ExtensionError

# --- Import from refactored modules ---
from .utils import (
    get_safe_filename, get_highest_contrast_color,
    deep_update, resolve_all_colors, to_bool,
    _split_hex_opacity, hex_to_rgb_floats, hex_dark_invert,
    _get_luminance, adapt_color_to_page, _adapt_colors_in_dict,
    _compute_adaptation_compression, _RE_SAFE_NAME,
    register_color_operation, _custom_color_operations,
)
from .shell_icons import make_shell_icon, micro_shell_icon, genos_shell_icon
from .core_config import CORE_CONFIG_MANIFEST, DOXTR_GLOBALS, DOXTR_SEMANTIC_PALETTE, DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS, RenderMode, validate_render_mode
from .colors import safe_cmyk
from .templates import (
    DEFAULT_STYLE_NAME,
    clear_template_cache, resolve_and_render_template,
)
from .config import (
    CORE_ADMONITION_TYPES, validate_config_keys,
    validate_container_mapping, make_resolve_val_fn, make_merge_section_fn,
    make_collect_dark_fn, warn_deprecated,
)
from .fonts import (
    register_font_family,
    register_font_families,
    get_registered_fonts,
    register_font_renderer,
    register_font_discoverer,
    inject_font_features,
    _clear_font_registry,
    _set_fonts_processed,
    _api_font_registrations,
    _registered_fonts,
    process_user_font_config,
    auto_discover_fonts,
    collect_font_files,
    validate_font_files,
    _deduplicate_registry,
)
import doxtr_pdf_theme_core.fonts as _fonts_mod

from .ast_processors import (
    process_containers_ast,
    process_tables_ast,
    fix_block_after_paragraph,
    PARAGRAPH_FIX_PRIORITY,
    register_par_fix_block_type,
    register_par_fix_skip_type,
    register_column_width_algorithm,
    ColumnInfo,
    PT_TO_MM,
    process_codeblocks_ast,
    process_epigraph_ast,
    process_sidebar_ast,
    process_highlights_ast,
    process_needs_ast,
    process_topics_ast,
    process_todo_ast,
    process_landscape_ast,
    wrap_in_landscape,
    register_landscape_wrapper,
    LANDSCAPE_CLASS,
    NO_LANDSCAPE_CLASS,
    FORCE_LANDSCAPE_CLASS,
    DEFAULT_MIN_COLUMNS,
    make_pagegoal_cap_node,
)
from .dark_file_swap import (
    swap_dark_sources,
    swap_dark_includes,
    register_dark_swap_directive,
)

logger = logging.getLogger(__name__)

__version__ = "1.1.8"

# Legacy flat-key compat list (remove in v1.1.0)
_LEGACY_GLOBAL_KEYS = [
    'show_release', 'headsep', 'footskip', 'headheight', 'footheight',
    'show_list_of_figures', 'show_list_of_tables', 'show_list_of_listings',
    'appendix_chapter_numbering', 'footer_logo', 'footer_logo_height',
    'main_font', 'main_font_options', 'main_font_size',
    'sans_font', 'sans_font_options',
    'mono_font', 'mono_font_options',
    'inherit_all', 'inherit_font', 'inherit_color', 'inherit_size',
    'wcag_level', 'wcag_color_debug',
    'container_title_style_path', 'container_style_path',
    'table_style_path', 'figure_style_path', 'code_style_path',
    'admonition_style_path', 'need_style_path',
    'title_page_template_path', 'sidebar_style_path',
    'landscape_package',
]

__all__ = [
    'setup',
    'safe_cmyk',
    'StyleBoxDirective',
    '__version__',
    'make_shell_icon',
    'micro_shell_icon',
    'genos_shell_icon',
    # Extensibility API
    'register_ast_processor',
    'register_style_type',
    'register_preamble_hook',
    'register_config_transform',
    'register_color_operation',
    # Landscape API
    'register_landscape_wrapper',
    'wrap_in_landscape',
    'LANDSCAPE_CLASS',
    'NO_LANDSCAPE_CLASS',
    'FORCE_LANDSCAPE_CLASS',
    # Table/paragraph fix API
    'fix_block_after_paragraph',
    'PARAGRAPH_FIX_PRIORITY',
    'register_par_fix_block_type',
    'register_par_fix_skip_type',
    'register_column_width_algorithm',
    'ColumnInfo',
    'PT_TO_MM',
    # Font registration API
    'register_font_family',
    'register_font_families',
    'get_registered_fonts',
    'register_font_renderer',
    'register_font_discoverer',
    'inject_font_features',
    'hex_dark_invert',
    'adapt_color_to_page',
    # Dark file swap API
    'register_dark_swap_directive',
    # Image processing API
    'register_image_processor',
    # Dark mode strategy constants (for testing and child theme introspection)
    '_DARK_STRATEGY_LUMINANCE_THRESHOLD',
    '_ADAPTATION_LUMINANCE_THRESHOLD',
    '_VALID_DARK_STRATEGIES',
]

# --- EXTENSIBLE AST PROCESSOR REGISTRY (Task 2.1) ---
# Third-party extensions may register custom doctree-resolved handlers here.
# Each entry is a tuple: (fn, doctype, priority)
#   fn       – callable with signature fn(app, doctree, docname) -> None
#   doctype  – builder format to filter on (e.g. 'latex'), or None to default to latex-only
#   priority – Sphinx event priority passed directly to app.connect()
_custom_ast_processors: list = []

# Set to True once _connect_deferred_custom_processors has run (i.e. after builder-inited).
# Used to emit a warning when register_ast_processor() is called too late.
_custom_processors_connected: bool = False

# --- EXTENSIBLE STYLE TYPE REGISTRY ---
# Theme authors may register new element style types via register_style_type().
# Each entry is a dict produced by register_style_type() and processed in
# registration order during config_inited() (after all built-in style types).
_custom_style_types: list = []

# Built-in preamble_var keys already claimed by the core processing pipeline.
# register_style_type() rejects any name whose resolved preamble_var collides
# with one of these to prevent silent overwrite of built-in rendered LaTeX.
_BUILTIN_PREAMBLE_VARS: frozenset = frozenset({
    'doxtr_rendered_code',
    'doxtr_rendered_sidebar',
    'doxtr_rendered_highlights',
    'doxtr_rendered_topic',
    'doxtr_rendered_contents',
    'doxtr_rendered_todo',
    'doxtr_rendered_containers',
    'doxtr_rendered_title_page',
    'doxtr_rendered_tables',
    'doxtr_rendered_figures',
    'doxtr_rendered_draft',
})

# --- TABULARY OVERFLOW GUARD ---
# Injected as a preamble hook so it survives child theme preamble overrides.
# Detection relies on tabulary's internal \let\equation$ during trial passes
# (same trick as Sphinx's sphinxlatexgraphics.sty).
_TABULARY_GUARD_LATEX = r"""
%% TABULARY OVERFLOW GUARD (doxtr-pdf-theme-core)
%% Prevents "Dimension too large" errors during tabulary trial passes.
%% Detection: tabulary sets \let\equation$ during trial passes,
%% so \ifx\equation$ is true only in that context (same trick as
%% Sphinx's sphinxlatexgraphics.sty). If tabulary is replaced or
%% this detection changes, disable via doxtr_tabulary_overflow_guard=False.
\makeatletter
\let\doxtr@orig@rowcolor\rowcolor
\def\rowcolor{%
  \ifx\equation$%$%
    \expandafter\doxtr@eat@rowcolor
  \else
    \expandafter\doxtr@orig@rowcolor
  \fi
}
\def\doxtr@eat@rowcolor{\@ifnextchar[\doxtr@eat@rc@opt\doxtr@eat@rc@mand}%
\def\doxtr@eat@rc@opt[#1]#2{\@ifnextchar[\doxtr@eat@rc@ovhL{}}%
\def\doxtr@eat@rc@mand#1{\@ifnextchar[\doxtr@eat@rc@ovhL{}}%
\def\doxtr@eat@rc@ovhL[#1]{\@ifnextchar[\doxtr@eat@rc@ovhR{}}%
\def\doxtr@eat@rc@ovhR[#1]{}%
%%
%% DOXTR_TABULARY_TYMAX: 2000pt supports up to 8 T-columns without
%% exceeding \maxdimen (16383pt). Formula: ceil(maxdimen / tymax) >= N columns.
%% 2000pt >> any page width so tabulary's paragraph balancing is unaffected.
\setlength{\tymax}{2000pt}
\makeatother
"""


def _inject_tabulary_guard():
    """Return tabulary guard LaTeX for preamble injection.

    This function is registered as a preamble hook when
    ``doxtr_tabulary_overflow_guard`` is True. The enable/disable
    check happens at registration time in ``config_inited()``.
    """
    return _TABULARY_GUARD_LATEX


# --- EXTENSIBLE PREAMBLE HOOK REGISTRY (Phase 2.8) ---
# Theme authors may inject LaTeX into the document preamble without copying
# the entire preamble.tex_t template.  Each entry is a tuple: (fn, position).
_VALID_PREAMBLE_POSITIONS = frozenset({
    'before_packages', 'after_packages', 'before_styles', 'after_styles',
})
_preamble_hooks: list = []


def register_preamble_hook(fn, position='after_styles'):
    """Register a hook to inject LaTeX into the document preamble.

    This allows child themes to inject \\usepackage, \\newcommand, or other
    LaTeX without copying the entire preamble.tex_t template.

    Args:
        fn: A callable that returns a LaTeX string to inject.
            Signature: fn() -> str
        position: Where to inject the result. One of:
            - 'before_packages': Before \\usepackage declarations
            - 'after_packages': After core packages, before style definitions
            - 'before_styles': Before rendered style blocks (containers, code, etc.)
            - 'after_styles': After all rendered style blocks (default)

    Raises:
        ValueError: If *position* is not one of the valid positions.
        TypeError: If *fn* is not callable.

    Example::

        from doxtr_pdf_theme_core import register_preamble_hook

        def my_packages():
            return r'\\usepackage{tikz-cd}'

        register_preamble_hook(my_packages, position='after_packages')
    """
    if not callable(fn):
        raise TypeError(f"register_preamble_hook: fn must be callable, got {type(fn).__name__}")
    if position not in _VALID_PREAMBLE_POSITIONS:
        raise ValueError(
            f"register_preamble_hook: invalid position '{position}'. "
            f"Must be one of: {sorted(_VALID_PREAMBLE_POSITIONS)}"
        )
    _preamble_hooks.append((fn, position))


# --- EXTENSIBLE CONFIG TRANSFORM HOOK REGISTRY (Phase 4.4) ---
# Theme authors may register post-merge config transforms that run after all
# three-tier merging is complete but before template rendering.  Each entry is
# a callable with signature fn(sections: dict, palette: dict, config) -> None.
_config_transform_hooks: list = []


def register_config_transform(fn) -> None:
    """Register a post-merge config transform for child themes.

    The registered function is called after all three-tier merging is complete
    but before template rendering. This allows child themes to intercept and
    modify the merged config sections programmatically.

    Args:
        fn: A callable with signature fn(sections: dict, palette: dict, config) -> None.
            ``sections`` is the dict of all merged config sections (mutate in-place).
            ``palette`` is the resolved semantic palette (mutate in-place).
            ``config`` is the Sphinx config object.

    Raises:
        TypeError: If *fn* is not callable.

    Example::

        from doxtr_pdf_theme_core import register_config_transform

        def my_transform(sections, palette, config):
            # Force all containers to use a specific font
            for name, conf in sections['containers'].items():
                conf['title_font'] = 'My Custom Font'

        register_config_transform(my_transform)
    """
    if not callable(fn):
        raise TypeError(
            f"register_config_transform: fn must be callable, got {type(fn).__name__}"
        )
    _config_transform_hooks.append(fn)


def register_ast_processor(fn, doctype=None, priority=992) -> None:
    """Register a custom doctree-resolved AST processor.

    This function allows theme authors and downstream extensions to hook into
    the AST processing pipeline without monkey-patching. Each registered
    processor is connected to the 'doctree-resolved' event at its own Sphinx
    priority, enabling precise ordering relative to core processors and other
    downstream processors.

    Core processor priorities for reference:
        999 – process_needs_ast
        998 – process_containers_ast
        997 – process_epigraph_ast
        996 – process_tables_ast
        995 – process_codeblocks_ast
        994 – process_sidebar_ast
        993 – process_highlights_ast
        992 – default for register_ast_processor (between core processors and dark/topic processing)
        991 – process_dark_images_ast
        990 – process_topics_ast
        980 – fix_block_after_paragraph
        1001 – process_landscape_ast (after tables, reads doxtr_min_table_width_mm)

    Args:
        fn:       A callable with signature fn(app, doctree, docname) -> None.
        doctype:  Builder format to restrict execution to (e.g. 'latex', 'html').
                  None (default) preserves the existing behaviour: latex-only.
        priority: Sphinx event priority passed to app.connect(). Lower numbers
                  run first. Default is 992 (after all core processors).
                  Use a value between 993–999 to interleave with core processors.

    Note:
        ``register_ast_processor()`` must be called from an extension's
        ``setup()`` function. Calls made after Sphinx has fired
        ``builder-inited`` will be logged as a warning and ignored because
        the deferred connector has already run.

    Note:
        ``register_ast_processor(fn)`` and
        ``register_ast_processor(fn, None, 992)`` are exactly equivalent —
        both append the tuple ``(fn, None, 992)`` and resolve to latex-only
        at priority 992.

    Example — run after all core processors (default behaviour, unchanged)::

        >>> register_ast_processor(my_fn)

    Example — run before process_highlights_ast (priority 993) but after
    process_codeblocks_ast (priority 995)::

        >>> register_ast_processor(my_fn, priority=994)

    Example — run for HTML builds only::

        >>> register_ast_processor(my_fn, doctype='html', priority=500)
    """
    if _custom_processors_connected:
        logger.warning(
            f"[Doxtr Core] register_ast_processor('{getattr(fn, '__name__', repr(fn))}') "
            "was called after 'builder-inited' has fired and will be ignored. "
            "Move the call into your extension's setup() function."
        )
        return
    _custom_ast_processors.append((fn, doctype, priority))


def register_style_type(
    name: str,
    subdir: str,
    fallback_fn,
    config_section_factory=None,
    color_keys: Optional[List[str]] = None,
    preamble_var: Optional[str] = None,
    wcag_pairs: Optional[List[tuple]] = None,
) -> None:
    """Register a custom style type for template resolution.

    Allows theme authors to introduce new element types (beyond the built-in
    admonition/container/table/etc. set) without patching core files.  A
    registered type participates in the full config_inited() pipeline:
    three-tier config merge, color resolution, CMYK conversion, template
    resolution, and preamble injection.

    Args:
        name: Style type name used as the STYLE_TYPES key and config section
              name (e.g. ``'callout'``).  Must consist only of ASCII letters,
              digits, and underscores.  Hyphens are not allowed because they
              produce a ``doxtr_my-type`` Sphinx config key that cannot be
              written in ``conf.py`` (Python parses it as subtraction).
        subdir: Subdirectory name under ``latex_styles/`` that holds ``.tex_t``
                files (e.g. ``'callout'``).  May differ from ``name``.
        fallback_fn: Callable ``(style_name: str) -> str`` that returns an
                     absolute LaTeX fallback string when no ``.tex_t`` file is
                     found.  A plain string is also accepted and used as a
                     constant fallback regardless of ``style_name``.
        config_section_factory: Optional ``callable() -> dict``.  Returns the
                                core-default config dict merged before theme and
                                user layers.  If ``None``, an empty dict is used.
        color_keys: Optional list of field names whose values are converted to
                    CMYK after merging (e.g. ``['border_color',
                    'content_background_color']``).  Each key ``k`` produces a
                    ``k + '_cmyk'`` field on the resolved config dict.
        preamble_var: Key under which the rendered LaTeX string is stored in
                      ``template_vars`` and later injected into the preamble.
                      Defaults to ``f'doxtr_rendered_{name}'``.
        wcag_pairs: Optional list of (foreground_key, background_key) tuples for
                    automatic WCAG contrast enforcement. Each pair specifies a
                    foreground color key that should be adjusted for readability
                    against the background color key. Example:
                    ``[('title_font_color', 'title_background_color'),
                    ('title_icon_color', 'title_background_color')]``

    Raises:
        ValueError: If ``name`` contains characters other than ASCII letters,
                    digits, or underscores, or if the resolved ``preamble_var``
                    collides with a built-in rendered key.

    Note:
        Call ``register_style_type()`` at **module level** (outside any
        ``setup()`` function) so that the core ``setup()`` loop can call
        ``app.add_config_value(f'doxtr_{name}', {}, 'env')`` automatically.
        If you must call it inside a theme ``setup()`` — which runs after
        the core ``setup()`` has already fired — you must also manually call
        ``app.add_config_value(f'doxtr_{name}', {}, 'env')`` yourself;
        otherwise Sphinx will emit an *unknown configuration value* warning
        if users set ``doxtr_{name}`` in ``conf.py``.

    Example::

        from doxtr_pdf_theme_core import register_style_type

        register_style_type(
            name='callout',
            subdir='callout',
            fallback_fn=lambda _: r'\\newenvironment{ddcallout}{}{}',
            config_section_factory=lambda: {
                'style': 'default',
                'border_color': '#FF0000',
                'content_background_color': '#FFFFFF',
                'title_font_color': '#FFFFFF',
                'title_background_color': '#FF0000',
            },
            color_keys=['border_color', 'content_background_color',
                        'title_font_color', 'title_background_color'],
            wcag_pairs=[('title_font_color', 'title_background_color')],
        )
    """
    if not name.replace('_', '').isalnum():
        raise ValueError(
            f"[Doxtr Core] register_style_type: name '{name}' must contain only "
            f"ASCII letters, digits, or underscores (hyphens are not allowed "
            f"because they produce a conf.py-inaccessible config key)."
        )
    # Guard against collision with built-in preamble_var keys to prevent silent
    # overwrite of already-rendered built-in LaTeX in template_vars.
    _pv = preamble_var or f'doxtr_rendered_{name}'
    if _pv in _BUILTIN_PREAMBLE_VARS:
        raise ValueError(
            f"[Doxtr Core] register_style_type: preamble_var '{_pv}' conflicts "
            f"with a built-in rendered key. Choose a different name or supply "
            f"an explicit preamble_var that does not match: "
            f"{sorted(_BUILTIN_PREAMBLE_VARS)}"
        )
    # Normalise string fallbacks to callables
    if isinstance(fallback_fn, str):
        _fallback_str = fallback_fn
        fallback_fn = lambda _: _fallback_str  # noqa: E731
    # Warn and replace on duplicate registration
    for _existing in list(_custom_style_types):
        if _existing['name'] == name:
            logger.warning(
                f"[Doxtr Core] register_style_type: '{name}' is already registered. "
                f"Overwriting the previous registration."
            )
            _custom_style_types.remove(_existing)
            break
    _custom_style_types.append({
        'name': name,
        'subdir': subdir,
        'fallback_fn': fallback_fn,
        'config_section_factory': config_section_factory,
        'color_keys': color_keys or [],
        'preamble_var': _pv,
        'wcag_pairs': wcag_pairs or [],
    })


def _connect_deferred_custom_processors(app):
    """Connect all registered custom AST processors to 'doctree-resolved'.

    Called on 'builder-inited', after every extension's setup() has run and
    all register_ast_processor() calls have been recorded. Each processor is
    connected at its own Sphinx priority so ordering is fully controllable.
    """
    global _custom_processors_connected
    _custom_processors_connected = True
    def _make_wrapper(fn, effective_doctype):
        def _wrapper(app, doctree, docname):
            if getattr(app.builder, 'format', '') != effective_doctype:
                return
            try:
                fn(app, doctree, docname)
            except Exception as e:
                logger.warning(
                    f"[Doxtr Core] Custom AST processor "
                    f"'{getattr(fn, '__name__', repr(fn))}' raised: {e}"
                )
        _wrapper.__name__ = getattr(fn, '__name__', 'custom_ast_processor')
        return _wrapper

    for fn, doctype, priority in _custom_ast_processors:
        effective_doctype = doctype if doctype is not None else 'latex'
        app.connect('doctree-resolved', _make_wrapper(fn, effective_doctype), priority=priority)

# --- Dark Mode Strategy Constants ---
# Luminance threshold for auto-detecting dark mode strategy.
# Pages with luminance below this value use 'invert' (color inversion).
# Pages at or above this value use 'passthrough' (no inversion).
# Covers all practical dark backgrounds while correctly identifying light themes.
_DARK_STRATEGY_LUMINANCE_THRESHOLD = 0.35

# Valid values for doxtr_dark_mode_strategy config.
_VALID_DARK_STRATEGIES = ('auto', 'invert', 'passthrough')

# Minimum number of palette keys (excluding 'page') that should be overridden
# in passthrough mode for meaningful visual differentiation from light mode.
_PASSTHROUGH_MIN_PALETTE_KEYS = 4

# Luminance difference threshold for auto-enabling page adaptation.
# Below this threshold, the page shift is imperceptible (ΔL* < 2 at high
# luminance ≈ just noticeable difference). Using 0.05 in Y-space
# correctly catches cream (#FCF6E5, ΔY=0.077) and off-white (#F2F0EF,
# ΔY=0.126) while skipping trivial shifts (#FCFCFC, ΔY=0.027).
_ADAPTATION_LUMINANCE_THRESHOLD = 0.05

# Luminance range defining "mid-grey" pages where dynamic range is limited.
# Pages in this range trigger a warning about potential color compression.
_ADAPTATION_MID_GREY_LOW = 0.25
_ADAPTATION_MID_GREY_HIGH = 0.55

# Luminance difference threshold for the proactive "adaptation available" hint.
# Must be larger than _ADAPTATION_LUMINANCE_THRESHOLD to avoid hinting when
# the difference is already caught by auto-mode.
_ADAPTATION_HINT_THRESHOLD = 0.10

# --- Precompiled regex patterns ---
# Compiled once at import time for performance (Task 4.5)
# _RE_SAFE_NAME is imported from utils.py (shared with ast_processors/containers.py)
_RE_HASH_NUM = re.compile(r'#+1')


def _nearest_valid_pointsize(size_pt: float) -> str:
    """Return the nearest valid LaTeX document class font size option.

    LaTeX document classes only accept 10pt, 11pt, or 12pt as class
    options.  This function maps an arbitrary point size to the nearest
    valid option so that no 'Unused global option' warning is emitted.

    The actual text size is controlled separately via ``\\sphinxremdimen``
    which accepts arbitrary dimensions.
    """
    # Midpoints between valid class sizes: 10pt ↔ 10.5 ↔ 11pt ↔ 11.5 ↔ 12pt
    if size_pt <= 10.5:
        return '10pt'
    elif size_pt <= 11.5:
        return '11pt'
    else:
        return '12pt'


def _dark_invert_colors_in_dict(d: dict) -> dict:
    """Return a copy of d with all hex colour values dark-inverted.

    Applies hex_dark_invert (invert(0.86) hue-rotate(180deg)) to every
    string value starting with '#'. dd: expressions pass through unchanged
    and are resolved later by resolve_all_colors against the dark palette.
    Non-colour values (fonts, sizes, booleans) are copied unchanged.
    Nested dicts are recursed into.
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _dark_invert_colors_in_dict(v)
        elif isinstance(v, str) and v.startswith('#'):
            result[k] = hex_dark_invert(v) or v
        else:
            result[k] = v
    return result


def _auto_detect_dark_strategy(page_color: str) -> tuple:
    """Auto-detect dark mode strategy from page luminance.

    Returns (strategy, luminance) tuple where strategy is 'invert' or 'passthrough'.
    Uses _DARK_STRATEGY_LUMINANCE_THRESHOLD to determine the cutoff.
    """
    lum = _get_luminance(page_color)
    strategy = 'invert' if lum < _DARK_STRATEGY_LUMINANCE_THRESHOLD else 'passthrough'
    return strategy, lum


def _build_dark_section(light_merged: dict, dark_overrides_section: dict,
                        strategy: str = 'invert') -> dict:
    """Build the dark-mode merged config for one section.

    When strategy='invert': invert all hex colors, then merge overrides.
    When strategy='passthrough': skip inversion, only merge overrides on
    top of the light values. dd: expressions resolve against the dark
    palette regardless of strategy.
    """
    if strategy == 'passthrough':
        # No inversion — light values are appropriate for a light dark-mode page.
        # Only apply user/theme dark_overrides for accent differentiation.
        return deep_update(copy.deepcopy(light_merged),
                           copy.deepcopy(dark_overrides_section))
    # Default: invert all hex colors, then merge overrides
    core_dark = _dark_invert_colors_in_dict(light_merged)
    return deep_update(copy.deepcopy(core_dark),
                       copy.deepcopy(dark_overrides_section))




class StyleBoxDirective(Directive):
    """RST directive for custom styled container boxes.

    Provides the ``.. stylebox:: <container_name>`` directive that wraps
    content in a named container node.  The container name maps to an entry
    in ``doxtr_containers`` (or via ``doxtr_container_mapping``) and is
    rendered as a styled tcolorbox in LaTeX output.

    Usage::

        .. stylebox:: my_container
           :title: Optional Title
           :class: extra-css-class

           Content goes here.

    Options:
        :title:   Override or supply the box title text.  If omitted, the
                  title defined in the container's config entry is used.
        :notitle: Suppress the title entirely, even if one is defined in
                  configuration.
        :class:   Additional CSS/LaTeX classes appended to the container
                  node (useful for per-instance overrides in RST).
        :name:    A reStructuredText reference name for cross-referencing.

    Integration:
        During the ``doctree-resolved`` phase, ``process_containers_ast``
        matches container nodes whose classes include a registered container
        name and wraps them in raw LaTeX ``\\begin{doxtrstyleboxrouter}``
        environments. The container's style and title_style ``.tex_t``
        templates control the final appearance.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'name': directives.unchanged,
        'title': directives.unchanged,
        'notitle': directives.flag,
        'class': directives.class_option
    }
    has_content = True

    def run(self):
        self.assert_has_content()
        container = nodes.container()
        if self.arguments:
            container['classes'].extend(self.arguments[0].split())
        container['classes'].extend(self.options.get('class', []))
        if 'notitle' in self.options:
            # Explicit :notitle: sentinel — suppress all title sources including config
            container['doxtr_stylebox_notitle'] = True
        else:
            raw_title = self.options.get('title')
            if raw_title:
                container['doxtr_stylebox_title'] = raw_title
        self.add_name(container)
        self.state.nested_parse(self.content, self.content_offset, container)
        return [container]

# AST processors are now imported from .ast_processors module
# The functions process_containers_ast, process_tables_ast, process_codeblocks_ast,
# process_epigraph_ast, process_sidebar_ast, process_needs_ast are all imported above.


def _resolve_sty_file(filename: str, override_paths: list, pkg_dir: Path) -> str:
    """Resolve a .sty file through override paths then the core fallback.

    Search order:
      1. Each directory in override_paths (in order) — supports absolute paths
         and paths already resolved to confdir by the caller.
      2. Core package fallback: pkg_dir / 'latex_styles' / filename

    Args:
        filename:       Bare filename, e.g. 'sphinxlatexstyleheadings.sty'
        override_paths: List of directory paths to search first.
        pkg_dir:        Resolved Path of this package (doxtr_pdf_theme_core/).

    Returns:
        Absolute path string of the first matching file found, or the core
        fallback path if none of the override paths contain the file.
    """
    for dir_str in override_paths:
        candidate = Path(dir_str) / filename
        if candidate.exists():
            return str(candidate.resolve())
    # Core fallback — always present in the installed package
    return str(pkg_dir / "latex_styles" / filename)


def _query_mono_char_width_ratio(font_path):
    """Query the advance width ratio of the '0' glyph relative to em-square.

    Uses fontTools to read the font's horizontal metrics table and compute
    the ratio of the '0' glyph's advance width to the units-per-em value.
    This ratio, multiplied by point size and 0.3528 (pt-to-mm), gives the
    physical character width in mm for monospace content.

    Args:
        font_path: Path to a .ttf or .otf font file.

    Returns:
        Float ratio (advance_width / units_per_em), or 0.6 as fallback.
    """
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(str(font_path))
        hmtx = font['hmtx']
        upm = font['head'].unitsPerEm
        cmap = font.getBestCmap()
        glyph_name = cmap.get(ord('0'))
        if glyph_name:
            width = hmtx[glyph_name][0]
            return width / upm
    except Exception as e:
        logger.debug('Could not query font metrics for %s: %s', font_path, e)
    return 0.6  # fallback: Courier default


def _resolve_table_overflow_config(app, config, ctx):
    """Resolve table overflow config values from merged tables config.

    Populates doxtr_table_nobreak_patterns, doxtr_table_break_chars,
    doxtr_table_column_width_algorithm, doxtr_table_auto_colwidths, and
    doxtr_table_char_width_mm on config when they are not explicitly set
    by the user. Values are read from the three-tier merged ``ctx`` dict
    (not raw user config) so that theme-level overrides are respected.

    Args:
        app: The Sphinx application object.
        config: The Sphinx config object (mutated).
        ctx: Pipeline context dict from _stage_merge_and_resolve().
             Expected keys: 'tables' (merged tables dict), 'g' (merged
             globals dict), 'main_font_size_pt' (float).
    """
    # --- Resolve from merged tables config (three-tier: core → theme → user) ---
    tables_merged = ctx.get('tables', {})
    generic = tables_merged.get('generic', {}) if isinstance(tables_merged, dict) else {}

    from .ast_processors.tables import DEFAULT_NOBREAK_PATTERNS, DEFAULT_BREAK_CHARS, DEFAULT_ALGORITHM

    if getattr(config, 'doxtr_table_nobreak_patterns', None) is None:
        config.doxtr_table_nobreak_patterns = generic.get('nobreak_patterns', DEFAULT_NOBREAK_PATTERNS)

    if getattr(config, 'doxtr_table_break_chars', None) is None:
        config.doxtr_table_break_chars = generic.get('break_chars', DEFAULT_BREAK_CHARS)

    if getattr(config, 'doxtr_table_column_width_algorithm', None) is None:
        config.doxtr_table_column_width_algorithm = generic.get('column_width_algorithm', DEFAULT_ALGORITHM)

    if getattr(config, 'doxtr_table_auto_colwidths', None) is None:
        config.doxtr_table_auto_colwidths = generic.get('auto_colwidths', True)

    # --- Resolve header char width factor ---
    if getattr(config, 'doxtr_table_header_char_width_factor', None) is None:
        from .ast_processors.tables import DEFAULT_HEADER_CHAR_WIDTH_FACTOR
        config.doxtr_table_header_char_width_factor = generic.get(
            'header_char_width_factor', DEFAULT_HEADER_CHAR_WIDTH_FACTOR
        )

    # --- Compute char_width_mm from mono font metrics ---
    if getattr(config, 'doxtr_table_char_width_mm', None) is None:
        g = ctx.get('g', {})
        main_font_size_pt = ctx.get('main_font_size_pt', 11.5)
        mono_font_name = g.get('mono_font', 'FiraCode Nerd Font')

        # Try to find the mono font file from the font registry
        char_width_ratio = 0.6  # fallback: Courier default
        try:
            for entry in _registered_fonts:
                if entry.get('name', '') == mono_font_name:
                    fonts_dir = entry.get('fonts_dir', '')
                    upright = entry.get('upright', '')
                    if fonts_dir and upright:
                        font_path = Path(fonts_dir) / upright
                        if font_path.exists():
                            char_width_ratio = _query_mono_char_width_ratio(font_path)
                    break
        except Exception as e:
            logger.debug('Could not resolve mono font metrics for char_width_mm: %s', e)

        from .ast_processors.tables import PT_TO_MM
        config.doxtr_table_char_width_mm = main_font_size_pt * char_width_ratio * PT_TO_MM


def config_inited(app, config):
    """Process all configuration, resolve templates, and inject LaTeX preamble.

    This is the main orchestration function that executes the configuration
    pipeline in three stages:

    1. **Merge & Resolve** (_stage_merge_and_resolve): Three-tier merge of all
       config sections, dark mode activation, page color adaptation, and dd:
       expression resolution (Pass 1).
    2. **Build & Render Preamble** (_stage_build_and_render_preamble): Build
       template variables from merged config, resolve and render all .tex_t
       style templates, and produce the final preamble LaTeX string.
    3. **Assemble Output** (_stage_assemble_output): Font processing, LaTeX
       element assembly, hyperlink colors, and final preamble injection into
       config.latex_elements.

    Called at priority 900 on the 'config-inited' event.

    Args:
        app: The Sphinx application object.
        config: The Sphinx config object. Mutated extensively — final state
                includes latex_elements, latex_additional_files, and all
                resolved doxtr_* attributes.
    """
    # Clear template cache and preamble hooks at the start of each build to avoid
    # Clear template cache at the start of each build to avoid stale templates
    # when using sphinx-autobuild or similar tools.
    clear_template_cache()
    # NOTE: _preamble_hooks, _config_transform_hooks, and _custom_color_operations
    # are NOT cleared here. They are module-level singletons registered during setup()
    # or at import time — before config_inited fires. Clearing them would make the
    # APIs non-functional. Sphinx only calls setup() once per process, so duplicates
    # cannot accumulate. (Compare: _custom_ast_processors and _custom_style_types
    # are also never cleared.)

    if config.latex_engine not in ('lualatex',):
        config.latex_engine = 'lualatex'
    if not config.latex_docclass: config.latex_docclass = {'manual': 'scrbook'}
    else: config.latex_docclass.setdefault('manual', 'scrbook')

    # Tabulary overflow guard — injected via preamble hook to survive child theme overrides.
    # Guard against duplicate registration on autobuild re-runs.
    if getattr(config, 'doxtr_tabulary_overflow_guard', True):
        if not any(fn is _inject_tabulary_guard for fn, _ in _preamble_hooks):
            register_preamble_hook(_inject_tabulary_guard, position='after_packages')

    # --- Table style: ensure colorrows is enabled ---
    # Sphinx's colorrows machinery is the only reliable way to colour longtable
    # header rows.  The manual \rowcolor injection in the AST processor works for
    # tabular/tabulary but is completely ignored for longtables (header rows are
    # assembled as strings during visit_row, before the AST processor's raw nodes
    # are read).  colorrows activates \sphinxTableRowColorHeader for all table
    # types uniformly.  We merge rather than replace so user/theme values are kept.
    # Gated by doxtr_enable_table_processor so child themes can fully opt out.
    if getattr(config, 'doxtr_enable_table_processor', True):
        _raw_table_style = getattr(config, 'latex_table_style', None)
        _user_table_style = list(_raw_table_style) if isinstance(_raw_table_style, (list, tuple)) else []
        if 'colorrows' not in _user_table_style:
            _user_table_style.append('colorrows')
        if 'booktabs' not in _user_table_style:
            _user_table_style.insert(0, 'booktabs')
        config.latex_table_style = _user_table_style

    safe_project = get_safe_filename(config.project)
    if not config.latex_documents or 'outpdfname.tex' in config.latex_documents[0][1]:
        config.latex_documents = [(config.root_doc, f"{safe_project}.tex", config.project, config.author, 'manual')]

    # --- PIPELINE STAGE 1: Merge & Resolve ---
    ctx = _stage_merge_and_resolve(app, config)

    # --- Table overflow: resolve config defaults and compute char width ---
    if getattr(config, 'doxtr_enable_table_processor', True):
        _resolve_table_overflow_config(app, config, ctx)

    # --- PIPELINE STAGE 2: Build & Render Preamble ---
    _stage_build_and_render_preamble(app, config, ctx)

    # --- PIPELINE STAGE 3: Assemble Output ---
    _stage_assemble_output(app, config, ctx)


def _stage_merge_and_resolve(app, config):
    """Pipeline Stage 1: Three-tier merge, dark mode, page adaptation, color resolution.

    Performs the following in order:
    - Three-tier globals merge + legacy flat-key migration
    - Dark mode flag normalization
    - Base font size & size_factor calculation
    - Section merging for all config sections (via merge_section)
    - Configuration validation (unknown keys, container mapping)
    - Dark overrides collection
    - Semantic palette merge (three-tier)
    - Dark mode strategy detection & palette generation
    - Dark mode activation (rebuilding all sections for dark mode)
    - Page color adaptation (luminance-proportional remapping)
    - dd: expression resolution (Pass 1)

    Args:
        app: The Sphinx application object.
        config: The Sphinx config object. Mutated: sets config.doxtr_dark_mode,
                config.doxtr_dark_mode_strategy_resolved, config.doxtr_dark_text_color,
                config.doxtr_dark_overrides, config.doxtr_adaptation_state,
                config.doxtr_containers.

    Returns:
        dict: A context dict containing all pipeline state needed by subsequent
              stages. Keys include 'g', 'theme_defaults', 'theme_style_paths',
              'resolve_val', 'dark_mode', 'wcag_level', 'wcag_color_debug',
              'main_font_size_str', 'main_font_size_pt', 'semantic_palette',
              'page_bg', 'adapt_to_page', 'designed_page', 'compress_dark',
              'compress_light', 'merged_configs', 'pkg_dir', and all individual
              section dicts (tp, headings, parts, containers, etc.).
    """
    # --- THREE-TIER MERGE ARCHITECTURE ---
    theme_defaults = getattr(config, 'doxtr_theme_defaults', {})
    theme_style_paths = getattr(config, 'doxtr_theme_style_paths', [])

    resolve_val = make_resolve_val_fn(config, theme_defaults)
    merge_section = make_merge_section_fn(config, theme_defaults)
    collect_dark = make_collect_dark_fn(config, theme_defaults)

    # --- GLOBALS MERGE (must run before palette/color resolution) ---
    _globals_core = DOXTR_GLOBALS.get('light', {})
    _globals_theme = theme_defaults.get('globals', {}).get('light', {}) if isinstance(theme_defaults.get('globals'), dict) else {}
    _globals_user = getattr(config, 'doxtr_globals', {}).get('light', {}) if isinstance(getattr(config, 'doxtr_globals', {}), dict) else {}
    g = deep_update(
        deep_update(copy.deepcopy(_globals_core), copy.deepcopy(_globals_theme)),
        copy.deepcopy(_globals_user),
    )

    # Legacy flat-key migration — inject any old doxtr_<key> = value into g.
    _any_legacy = False
    for _key in _LEGACY_GLOBAL_KEYS:
        _val = getattr(config, f'doxtr_{_key}', None)
        if _val is not None:
            _any_legacy = True
            g[_key] = _val
    if _any_legacy:
        logger.warning(
            "[Doxtr Core] One or more legacy flat globals (doxtr_main_font, "
            "doxtr_headsep, etc.) are set. These are deprecated in favour of "
            "doxtr_globals = {'light': {...}}. Support will be removed in v1.1.0."
        )

    # Validate top-level wrapper keys
    _raw_globals = getattr(config, 'doxtr_globals', {})
    if isinstance(_raw_globals, dict):
        _unknown_globals_keys = set(_raw_globals.keys()) - {'light', 'dark'}
        if _unknown_globals_keys:
            logger.warning(
                f"[Doxtr Core] Unknown top-level keys in 'doxtr_globals': "
                f"{sorted(_unknown_globals_keys)}. Valid keys are 'light' and 'dark'."
            )

    # --- DARK MODE FLAG ---
    dark_mode = to_bool(getattr(config, 'doxtr_dark_mode', False), default=False)
    config.doxtr_dark_mode = dark_mode  # normalise to bool

    # Convenience reads from globals
    wcag_level = g.get('wcag_level', 7)
    wcag_color_debug = g.get('wcag_color_debug', False)

    # Merge core configs via manifest
    tp = merge_section('title_page')
    headings = merge_section('headings')
    parts = merge_section('parts')

    # --- Base Font Size & Size Factor Calculation Engine ---
    # Resolve the base document font size through three-tier merge
    main_font_size_str = g.get('main_font_size', '11.5pt')
    # Parse the numeric pt value (e.g. '11.5pt' → 11.5)
    _mfs_match = re.match(r'(\d+(?:\.\d+)?)', str(main_font_size_str))
    try:
        main_font_size_pt = float(_mfs_match.group(1)) if _mfs_match else 11.5
    except (ValueError, TypeError):
        logger.warning("[Doxtr Core] Invalid main_font_size '%s'; falling back to 11.5pt.", main_font_size_str)
        main_font_size_pt = 11.5

    # Compute heading sizes from size_factor where applicable.
    # size_factor is a multiplier of main_font_size: e.g. size_factor=2.0 with 11.5pt → \fontsize{23.0pt}{27.6pt}\selectfont
    # If user explicitly sets 'size' on a heading level, it takes precedence over size_factor.
    # Note: 'part' is intentionally excluded — part sizes come from the separate doxtr_parts config,
    # not from headings['part']. size_factor on headings['part'] would be computed but never consumed.
    _heading_levels = ['chapter', 'section', 'subsection', 'subsubsection']
    for _hlevel in _heading_levels:
        if _hlevel in headings and isinstance(headings[_hlevel], dict):
            _hlevel_conf = headings[_hlevel]
            if 'size_factor' in _hlevel_conf and 'size' not in _hlevel_conf:
                try:
                    _factor = float(_hlevel_conf['size_factor'])
                except (ValueError, TypeError):
                    logger.warning("[Doxtr Core] Invalid size_factor '%s' in headings.%s; ignoring.",
                                   _hlevel_conf['size_factor'], _hlevel)
                    continue
                if _factor <= 0:
                    logger.warning("[Doxtr Core] size_factor must be positive in headings.%s (got %s); ignoring.",
                                   _hlevel, _factor)
                    continue
                _computed_size = main_font_size_pt * _factor
                _computed_bl = _computed_size * 1.2
                _hlevel_conf['size'] = rf'\fontsize{{{_computed_size:.1f}pt}}{{{_computed_bl:.1f}pt}}\selectfont'

    draft = merge_section('draft')
    microtype = merge_section('microtype')
    epigraphs = merge_section('epigraphs')
    admonitions = merge_section('admonitions')
    needs = merge_section('needs')
    containers = merge_section('containers')
    tables = merge_section('tables')
    figures = merge_section('figures')
    code = merge_section('code')
    sidebar = merge_section('sidebar')
    highlights = merge_section('highlights')
    topic = merge_section('topic')
    contents = merge_section('contents')
    todo = merge_section('todo')
    toc = merge_section('toc')
    bibliography = merge_section('bibliography')
    index = merge_section('index')
    glossary = merge_section('glossary')
    links = merge_section('links')

    # Collect all sections into a single dict for loop-based processing.
    # Keys are the canonical config section names.
    _sections = {
        'title_page': tp,
        'headings': headings,
        'parts': parts,
        'epigraphs': epigraphs,
        'draft': draft,
        'microtype': microtype,
        'containers': containers,
        'tables': tables,
        'figures': figures,
        'code': code,
        'admonitions': admonitions,
        'needs': needs,
        'sidebar': sidebar,
        'highlights': highlights,
        'topic': topic,
        'contents': contents,
        'todo': todo,
        'toc': toc,
        'bibliography': bibliography,
        'index': index,
        'glossary': glossary,
        'links': links,
    }

    # --- CONFIGURATION VALIDATION ---
    # Warn about unknown keys in user-provided config sections (typo detection)
    validate_config_keys(getattr(config, 'doxtr_title_page', {}), 'title_page')
    validate_config_keys(getattr(config, 'doxtr_draft', {}), 'draft')
    validate_config_keys(getattr(config, 'doxtr_epigraphs', {}), 'epigraphs')
    validate_config_keys(getattr(config, 'doxtr_headings', {}), 'headings')
    validate_config_keys(getattr(config, 'doxtr_microtype', {}), 'microtype')
    validate_config_keys(getattr(config, 'doxtr_sidebar', {}), 'sidebar')
    validate_config_keys(getattr(config, 'doxtr_highlights', {}), 'highlights')
    validate_config_keys(getattr(config, 'doxtr_topic', {}), 'topic')
    validate_config_keys(getattr(config, 'doxtr_contents', {}), 'contents')
    validate_config_keys(getattr(config, 'doxtr_todo', {}), 'todo')
    validate_config_keys(getattr(config, 'doxtr_toc', {}), 'toc')
    validate_config_keys(getattr(config, 'doxtr_bibliography', {}), 'bibliography')
    validate_config_keys(getattr(config, 'doxtr_index', {}), 'index')
    validate_config_keys(getattr(config, 'doxtr_glossary', {}), 'glossary')
    validate_config_keys(getattr(config, 'doxtr_links', {}), 'links')
    # Validate container mapping: warn about targets that don't exist in containers config.
    # Pass the already-merged containers dict so theme-defined styles don't generate
    # false-positive warnings (theme defaults are not visible in config.doxtr_containers
    # before the merge runs).
    validate_container_mapping(getattr(config, 'doxtr_container_mapping', {}), containers)
    # Validate nested dict sections only at the 'generic' level
    tables_user = getattr(config, 'doxtr_tables', {})
    if 'generic' in tables_user:
        validate_config_keys(tables_user['generic'], 'tables')
    figures_user = getattr(config, 'doxtr_figures', {})
    if 'generic' in figures_user:
        validate_config_keys(figures_user['generic'], 'figures')
    # For parts, validate the top-level non-integer keys
    parts_user = getattr(config, 'doxtr_parts', {})
    parts_top_keys = {k for k in parts_user.keys() if not isinstance(k, int)}
    validate_config_keys({k: parts_user[k] for k in parts_top_keys}, 'parts')

    # --- COLLECT DARK OVERRIDES ---
    # Store dark sub-key overrides for all sections (used in Plan 06 dark activation)
    config.doxtr_dark_overrides = {
        name: collect_dark(name)
        for name in CORE_CONFIG_MANIFEST.keys()
        if name != 'globals'  # globals dark handled separately
    }
    config.doxtr_dark_overrides['globals'] = collect_dark('globals', 'doxtr_globals')

    # --- SEMANTIC COLOR SYSTEM ---
    palette_core = DOXTR_SEMANTIC_PALETTE
    palette_theme_raw = theme_defaults.get('semantic_palette', {})
    palette_user_raw = getattr(config, 'doxtr_semantic_palette', {})

    # Strip 'dark' sub-key before light merge (Plan 05)
    palette_theme = {k: v for k, v in palette_theme_raw.items() if k != 'dark'}
    palette_user = {k: v for k, v in palette_user_raw.items() if k != 'dark'}

    # Deprecation shim: user-tier doxtr_page_background → semantic_palette['page']
    _legacy_page_bg = getattr(config, 'doxtr_page_background', None)
    if _legacy_page_bg is not None:
        warn_deprecated(config, 'doxtr_page_background',
                        "doxtr_semantic_palette['page']", 'global settings', '1.1.0')
        palette_user = dict(palette_user)
        palette_user.setdefault('page', _legacy_page_bg)

    # Deprecation shim: theme-tier doxtr_theme_defaults['page_background']
    _legacy_theme_page_bg = theme_defaults.get('page_background')
    if _legacy_theme_page_bg is not None:
        logger.warning(
            "[Doxtr Core] 'page_background' in doxtr_theme_defaults is deprecated "
            "and will be removed in v1.1.0. "
            "Use doxtr_theme_defaults['semantic_palette']['page'] instead."
        )
        palette_theme = dict(palette_theme)
        palette_theme.setdefault('page', _legacy_theme_page_bg)

    # Deprecation shim: doxtr_dark_image_exclude_patterns → doxtr_image_exclude_patterns
    _legacy_exclude = getattr(config, 'doxtr_dark_image_exclude_patterns', None)
    if _legacy_exclude:
        warn_deprecated(config, 'doxtr_dark_image_exclude_patterns',
                        'doxtr_image_exclude_patterns', 'image processing', '1.1.0')
        # Merge into the new key if user hasn't set it directly
        _new_exclude = getattr(config, 'doxtr_image_exclude_patterns', None)
        if not _new_exclude:
            config.doxtr_image_exclude_patterns = list(_legacy_exclude)

    # Three-tier merge: core → theme → user
    semantic_palette = deep_update(
        deep_update(copy.deepcopy(palette_core), copy.deepcopy(palette_theme)),
        copy.deepcopy(palette_user),
    )

    # page_bg is sourced exclusively from the merged palette
    page_bg = semantic_palette.get('page', '#FFFFFF')

    # --- DARK SEMANTIC PALETTE ---
    # Extract dark sub-key overrides from theme and user palette dicts
    dark_palette_theme = palette_theme_raw.get('dark', {}) if isinstance(palette_theme_raw, dict) else {}
    dark_palette_user = palette_user_raw.get('dark', {}) if isinstance(palette_user_raw, dict) else {}

    # --- Resolve dark mode strategy EARLY (before palette generation) ---
    # The strategy determines whether to invert palette colors or pass them
    # through. We need the dark page color to auto-detect, but the full dark
    # palette hasn't been computed yet. The page color comes exclusively from
    # user-dark → theme-dark → core-default (never auto-generated).
    _dark_page_early = (
        dark_palette_user.get('page') or
        dark_palette_theme.get('page') or
        DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page']
    )

    # Guard: if the page color is a dd: expression or non-hex value,
    # it cannot be resolved until palette merge completes. Fall back to
    # the core default so auto-detection can proceed safely.
    if not isinstance(_dark_page_early, str) or not _dark_page_early.startswith('#'):
        logger.info(
            f'[Doxtr Core] Dark page color \'{_dark_page_early}\' is not a hex value '
            f'(possibly a dd: expression). Using core default for strategy detection.'
        )
        _dark_page_early = DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page']

    # Resolve strategy from page luminance or explicit user setting.
    # 'auto' (default): detects page luminance and uses _DARK_STRATEGY_LUMINANCE_THRESHOLD.
    # 'invert': forces hex_dark_invert on all colors (current behavior).
    # 'passthrough': skips inversion — only dd: expressions and dark_overrides
    # provide differentiation, suitable for solarized/sepia/cream alternative themes.
    _strategy_raw = getattr(config, 'doxtr_dark_mode_strategy', 'auto')
    if _strategy_raw == 'auto':
        dark_strategy, _page_lum = _auto_detect_dark_strategy(_dark_page_early)
        logger.info(
            f'[Doxtr Core] Dark mode strategy auto-detected: \'{dark_strategy}\' '
            f'(page={_dark_page_early}, luminance={_page_lum:.3f}, '
            f'threshold={_DARK_STRATEGY_LUMINANCE_THRESHOLD})'
        )
    elif _strategy_raw in _VALID_DARK_STRATEGIES:
        dark_strategy = _strategy_raw
    else:
        logger.warning(
            f"[Doxtr Core] Unknown doxtr_dark_mode_strategy '{_strategy_raw}'. "
            f"Valid values: {_VALID_DARK_STRATEGIES}. Falling back to 'auto'."
        )
        dark_strategy, _page_lum = _auto_detect_dark_strategy(_dark_page_early)

    # Store resolved strategy as a proper config value (survives pickle
    # across incremental builds and is readable by build-finished hooks).
    config.doxtr_dark_mode_strategy_resolved = dark_strategy

    # Warn if passthrough mode with incomplete palette — users should provide
    # a more complete dark palette for meaningful visual differentiation.
    if dark_strategy == 'passthrough':
        _user_dark_keys = set(dark_palette_user.keys()) - {'page'}
        _theme_dark_keys = set(dark_palette_theme.keys()) - {'page'}
        _provided_keys = _user_dark_keys | _theme_dark_keys
        if len(_provided_keys) < _PASSTHROUGH_MIN_PALETTE_KEYS:
            logger.warning(
                f'[Doxtr Core] Dark mode strategy is \'passthrough\' (light page) '
                f'but only {len(_provided_keys)} palette color(s) are overridden '
                f'in dark:{{}}. In passthrough mode, only dd: expressions and '
                f'dark_overrides provide visual differentiation from light mode. '
                f'Consider providing a complete dark palette (primary, secondary, '
                f'info, success, warning, danger) for meaningful differentiation.'
            )

    # Auto-generate dark palette with strategy awareness.
    # In 'invert' mode: invert all light palette keys (existing behavior).
    # In 'passthrough' mode: pass light palette through unchanged —
    # light palette colors are already appropriate for a light page.
    if dark_strategy == 'passthrough':
        # Light palette values are correct for light dark-mode pages.
        # dd:primary on a cream page should resolve to the original
        # dark navy (#183060) not an inverted pastel (#AABBDE).
        _dark_core = {**semantic_palette, 'page': _dark_page_early}
    else:
        # Standard: invert all light palette keys for dark page
        _auto_dark = {}
        for _key, _light_val in semantic_palette.items():
            if _key == 'page':
                continue
            if not isinstance(_light_val, str) or not _light_val.startswith('#'):
                _auto_dark[_key] = _light_val
                continue
            _inverted = hex_dark_invert(_light_val)
            _auto_dark[_key] = _inverted if _inverted else _light_val
        # Set core dark defaults: auto-generated keys + hardcoded page
        _dark_core = {**_auto_dark, 'page': DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page']}

    # Three-tier dark palette merge: core-auto → theme-dark → user-dark
    dark_semantic_palette = deep_update(
        deep_update(copy.deepcopy(_dark_core), copy.deepcopy(dark_palette_theme)),
        copy.deepcopy(dark_palette_user),
    )
    config.doxtr_dark_semantic_palette = dark_semantic_palette

    # WCAG settings already resolved from globals (g) above

    # --- DARK MODE ACTIVATION ---
    # When dark_mode is True, rebuild all section configs using soft inversion.
    if dark_mode:
        page_bg = dark_semantic_palette.get('page', DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page'])
        semantic_palette = dark_semantic_palette

        # Dark body text color: use user/theme override if set, else auto-derive
        # from the dark page background using WCAG contrast enforcement.
        # When page bg is dark (e.g. #242424), text will be light (#DBDBDB).
        # When page bg is light (e.g. #FCF6E5), text will be dark (#000000).
        _user_dark_text = getattr(config, 'doxtr_dark_text_color', None)
        if _user_dark_text:
            config.doxtr_dark_text_color = _user_dark_text
        elif dark_strategy == 'passthrough':
            # Light page: start from black and WCAG-adjust
            _candidate_text = '#000000'
            config.doxtr_dark_text_color = get_highest_contrast_color(
                _candidate_text, page_bg, target='foreground',
                wcag_level=wcag_level, color_debug=wcag_color_debug,
            ) or _candidate_text
        else:
            # Dark page: invert black → off-white, then WCAG-adjust
            _candidate_text = hex_dark_invert('#000000')  # #DBDBDB
            config.doxtr_dark_text_color = get_highest_contrast_color(
                _candidate_text, page_bg, target='foreground',
                wcag_level=wcag_level, color_debug=wcag_color_debug,
            )

        _dark_overrides = config.doxtr_dark_overrides
        for _name in list(_sections.keys()):
            _sections[_name] = _build_dark_section(
                _sections[_name], _dark_overrides.get(_name, {}), dark_strategy)

        # Dark globals overrides
        _dark_globals_overrides = _dark_overrides.get('globals', {})
        if _dark_globals_overrides:
            g = deep_update(copy.deepcopy(g), copy.deepcopy(_dark_globals_overrides))

        # Resolve _dark variants for config-level asset paths.
        # In passthrough mode (light page), keep the light assets — they are
        # already appropriate for the light dark-mode page background.
        if dark_strategy == 'invert':
            _footer = g.get('footer_logo', '')
            if _footer:
                g['footer_logo'] = _resolve_dark_asset(_footer)
            _tp_bg = _sections['title_page'].get('background_image', '')
            if _tp_bg:
                _sections['title_page']['background_image'] = _resolve_dark_asset(_tp_bg)
            for _p_num, _p_conf in _sections['parts'].items():
                if isinstance(_p_conf, dict) and _p_conf.get('image'):
                    _p_conf['image'] = _resolve_dark_asset(_p_conf['image'])

    # --- PAGE COLOR ADAPTATION ---
    # Luminance-proportional remapping: shifts all theme colors to maintain
    # their intended relationships when the page background differs from the
    # theme's designed-for background. Runs AFTER dark mode processing and
    # BEFORE dd: expression resolution.

    # Determine designed_page (context-aware: depends on dark mode state)
    if dark_mode and dark_strategy == 'invert':
        # Colors are already inverted for the canonical dark page.
        # The "designed for" reference is the dark palette's default page.
        designed_page = DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page']  # '#242424'
    else:
        # Light mode or passthrough: designed against the theme's light page
        designed_page = (
            palette_theme_raw.get('page') or
            DOXTR_SEMANTIC_PALETTE['page']  # '#FFFFFF'
        )

    # Guard: if the resolved designed_page is not a valid hex color
    # (e.g., a dd: expression that hasn't been resolved yet), fall back
    # to the appropriate default to prevent _get_luminance crashes.
    if not isinstance(designed_page, str) or not designed_page.startswith('#'):
        _fallback = (DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page']
                     if (dark_mode and dark_strategy == 'invert')
                     else '#FFFFFF')
        logger.warning(
            f"[Doxtr Core] designed_page '{designed_page}' is not a hex value. "
            f"Using fallback {_fallback} for adaptation reference."
        )
        designed_page = _fallback

    # Resolve doxtr_adapt_colors_to_page setting
    _adapt_raw = getattr(config, 'doxtr_adapt_colors_to_page', 'auto')
    # Valid explicit boolean-like values that to_bool handles correctly
    _ADAPT_BOOL_TRUE = (True, 1, 'true', '1', 'yes')
    _ADAPT_BOOL_FALSE = (False, 0, 'false', '0', 'no', 'none')

    if _adapt_raw == 'auto':
        # Auto-detect: adapt when page differs significantly from designed page
        _lum_diff = abs(_get_luminance(designed_page) - _get_luminance(page_bg))
        adapt_to_page = _lum_diff >= _ADAPTATION_LUMINANCE_THRESHOLD
        if adapt_to_page:
            logger.info(
                f'[Doxtr Core] Page adaptation auto-enabled: designed={designed_page} '
                f'\u2192 actual={page_bg} (\u0394L={_lum_diff:.4f} \u2265 {_ADAPTATION_LUMINANCE_THRESHOLD})'
            )
        else:
            logger.debug(
                f'[Doxtr Core] Page adaptation auto-skipped: designed={designed_page} '
                f'\u2192 actual={page_bg} (\u0394L={_lum_diff:.4f} < {_ADAPTATION_LUMINANCE_THRESHOLD})'
            )
    elif _adapt_raw in _ADAPT_BOOL_TRUE:
        adapt_to_page = True
    elif _adapt_raw in _ADAPT_BOOL_FALSE:
        adapt_to_page = False
    else:
        logger.warning(
            f"[Doxtr Core] Unknown doxtr_adapt_colors_to_page value '{_adapt_raw}'. "
            f"Valid: 'auto', True, False. Falling back to 'auto'."
        )
        _lum_diff = abs(_get_luminance(designed_page) - _get_luminance(page_bg))
        adapt_to_page = _lum_diff >= _ADAPTATION_LUMINANCE_THRESHOLD

    # Apply adaptation when active
    compress_dark = 1.0
    compress_light = 1.0
    if adapt_to_page:
        compress_dark, compress_light = _compute_adaptation_compression(
            _get_luminance(designed_page), _get_luminance(page_bg))

        # Adapt the semantic palette itself (so dd: expressions resolve
        # against adapted colors)
        adapted_palette = {}
        for _pk, _pv in semantic_palette.items():
            if _pk == 'page':
                adapted_palette[_pk] = page_bg  # Page stays as user set it
            elif isinstance(_pv, str) and _pv.startswith('#'):
                adapted_palette[_pk] = adapt_color_to_page(
                    _pv, designed_page, page_bg, compress_dark, compress_light)
            else:
                adapted_palette[_pk] = _pv
        semantic_palette = adapted_palette

        # Adapt all built-in section configs
        for _name in list(_sections.keys()):
            _sections[_name] = _adapt_colors_in_dict(
                _sections[_name], designed_page, page_bg, compress_dark, compress_light)

    # Mid-grey warning: limited dynamic range for decorative elements
    _actual_lum = _get_luminance(page_bg)
    if adapt_to_page and _ADAPTATION_MID_GREY_LOW <= _actual_lum <= _ADAPTATION_MID_GREY_HIGH:
        logger.warning(
            f'[Doxtr Core] Page adaptation active with a mid-grey page background '
            f'({page_bg}, luminance={_actual_lum:.3f}). Mid-grey pages have limited '
            f'dynamic range \u2014 colors will be compressed significantly. WCAG '
            f'enforcement will correct text/icon contrast, but decorative elements '
            f'may lose visual distinction. Consider providing explicit palette '
            f'overrides for best results.'
        )

    # Proactive hint when adaptation is NOT active but page differs significantly
    if not adapt_to_page and not dark_mode:
        _hint_diff = abs(_get_luminance(designed_page) - _get_luminance(page_bg))
        if _hint_diff >= _ADAPTATION_HINT_THRESHOLD:
            logger.info(
                f'[Doxtr Core] Page background ({page_bg}) differs from design '
                f'reference ({designed_page}) by \u0394L={_hint_diff:.3f}. Set '
                f'doxtr_adapt_colors_to_page=True (or "auto") to automatically '
                f'adjust theme colors for this background.'
            )

    # Stash adaptation state on config for child themes that need to
    # replace or extend adaptation logic at a lower-priority config-inited hook.
    config.doxtr_adaptation_state = {
        'active': adapt_to_page,
        'designed_page': designed_page,
        'actual_page': page_bg,
        'compress_dark': compress_dark,
        'compress_light': compress_light,
    }

    # Use the _sections dict as merged_configs for color resolution
    merged_configs = _sections

    # -----------------------------------------------------------------------
    # COLOR RESOLUTION — TWO-PASS STRATEGY
    #
    # Pass 1: Resolve dd: expressions in the raw merged config.
    #         Some values remain as dd: because they reference sibling keys
    #         that haven't been resolved yet (e.g. dd:this:title_background_color)
    # -----------------------------------------------------------------------
    for section_name, section_dict in merged_configs.items():
        resolve_all_colors(
            section_dict, semantic_palette, page_bg, section_name,
            theme_defaults, CORE_CONFIG_MANIFEST,
            getattr(config, 'doxtr_' + section_name, {}),
            root_config=merged_configs,
            wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
        )

    # -----------------------------------------------------------------------
    # COLOR RESOLUTION — PASS 2 runs after the TEXT INHERITANCE LOGIC block
    # inside `if preamble_path is not None:` below.  It resolves intra-section
    # dd:this: cross-references where key iteration order in Pass 1 left
    # sibling keys unresolved (e.g. dd:this:title_background_color iterated
    # before title_background_color was itself resolved).
    # NOTE: TEXT INHERITANCE LOGIC only reads/writes template_vars (CMYK
    # strings), never merged_configs.  Pass 2 does not benefit from
    # inheritance propagation; merged_configs is unchanged by that block.
    # -----------------------------------------------------------------------

    # Store merged containers back into config so AST walkers can access them
    config.doxtr_containers = _sections['containers']

    pkg_dir = Path(__file__).parent.resolve()

    # --- Post-merge config transform hooks ---
    # Invoke registered transforms after all merging, dark mode, page adaptation,
    # and dd: resolution (Pass 1) are complete, but before template rendering.
    for hook_fn in _config_transform_hooks:
        hook_fn(_sections, semantic_palette, config)

    # --- Return pipeline context for subsequent stages ---
    return {
        'g': g,
        'theme_defaults': theme_defaults,
        'theme_style_paths': theme_style_paths,
        'resolve_val': resolve_val,
        'dark_mode': dark_mode,
        'wcag_level': wcag_level,
        'wcag_color_debug': wcag_color_debug,
        'main_font_size_str': main_font_size_str,
        'main_font_size_pt': main_font_size_pt,
        'tp': _sections['title_page'],
        'headings': _sections['headings'],
        'parts': _sections['parts'],
        'draft': _sections['draft'],
        'microtype': _sections['microtype'],
        'epigraphs': _sections['epigraphs'],
        'admonitions': _sections['admonitions'],
        'needs': _sections['needs'],
        'containers': _sections['containers'],
        'tables': _sections['tables'],
        'figures': _sections['figures'],
        'code': _sections['code'],
        'sidebar': _sections['sidebar'],
        'highlights': _sections['highlights'],
        'topic': _sections['topic'],
        'contents': _sections['contents'],
        'todo': _sections['todo'],
        'toc': _sections['toc'],
        'bibliography': _sections['bibliography'],
        'index': _sections['index'],
        'glossary': _sections['glossary'],
        'links': _sections['links'],
        'semantic_palette': semantic_palette,
        'page_bg': page_bg,
        'adapt_to_page': adapt_to_page,
        'designed_page': designed_page,
        'compress_dark': compress_dark,
        'compress_light': compress_light,
        'merged_configs': merged_configs,
        'pkg_dir': pkg_dir,
    }


def _wcag_enforce_title_colors(conf, bg_key_or_color, wcag_level, color_debug,
                                font_key='title_font_color', icon_key='title_icon_color',
                                font_default='#FFFFFF', icon_default=None):
    """Enforce WCAG contrast for title text and icon colors against a background.

    Adjusts font and icon colors to meet the configured WCAG contrast ratio
    against the title background. Stores results as *_cmyk keys in conf.

    Args:
        conf: The section config dict. Mutated: sets '{font_key}_cmyk' and '{icon_key}_cmyk'.
        bg_key_or_color: Either a key name in conf to look up, or a direct hex color string.
        wcag_level: WCAG contrast ratio threshold.
        color_debug: Whether to log WCAG adjustments.
        font_key: Config key for the font color (default: 'title_font_color').
        icon_key: Config key for the icon color (default: 'title_icon_color').
                  Pass None to skip icon enforcement.
        font_default: Default font color if key is not set.
        icon_default: Default icon color if key is not set. None = use font_default.
    """
    if icon_default is None:
        icon_default = font_default
    # Resolve background: if bg_key_or_color starts with '#', treat as direct color;
    # otherwise look it up in conf.
    if bg_key_or_color.startswith('#'):
        bg_color = bg_key_or_color
    else:
        bg_color = conf.get(bg_key_or_color) or font_default

    # Font color enforcement
    _font = conf.get(font_key) or font_default
    _font = get_highest_contrast_color(_font, bg_color, target='foreground',
                                       wcag_level=wcag_level, color_debug=color_debug) or _font
    conf[f'{font_key}_cmyk'] = safe_cmyk(_font)

    # Icon color enforcement
    if icon_key is not None:
        _icon = conf.get(icon_key) or icon_default
        _icon = get_highest_contrast_color(_icon, bg_color, target='foreground',
                                           wcag_level=wcag_level, color_debug=color_debug) or _icon
        conf[f'{icon_key}_cmyk'] = safe_cmyk(_icon)


def _process_box_section(conf_dict, section_name, page_bg, wcag_level, color_debug,
                          default_icon='', template_type=None):
    """Process a box-style section (topic/contents): copy, WCAG enforce, set defaults.

    Args:
        conf_dict: The merged section config (topic or contents).
        section_name: Name for logging (e.g. 'topic', 'contents').
        page_bg: Current page background color.
        wcag_level: WCAG contrast ratio.
        color_debug: Whether to log adjustments.
        default_icon: Default title_icon value.
        template_type: Template type name (defaults to section_name).

    Returns:
        The processed config dict ready for template rendering.
    """
    if template_type is None:
        template_type = section_name

    box_conf = conf_dict.copy()
    _title_bg = box_conf.get('title_background_color') or '#1E3A6E'
    box_conf['title_background_color_cmyk'] = safe_cmyk(_title_bg)
    # WCAG contrast enforcement: ensure title text and icon are
    # readable against the title background.
    _wcag_enforce_title_colors(box_conf, _title_bg, wcag_level, color_debug)
    box_conf['content_background_color_cmyk'] = safe_cmyk(box_conf.get('content_background_color') or '#F0F4FA')
    box_conf['content_font_color_cmyk'] = safe_cmyk(box_conf.get('content_font_color') or '#1A1A2E')
    box_conf['border_color_cmyk'] = safe_cmyk(box_conf.get('border_color') or '#3A5A8E')
    box_conf['bottom_frame_color_cmyk'] = safe_cmyk(box_conf.get('bottom_frame_color') or _title_bg)
    box_conf['cutaway_fill_color_cmyk'] = safe_cmyk(box_conf.get('cutaway_fill_color') or page_bg)
    box_conf.setdefault('title_icon', default_icon)
    box_conf.setdefault('title_font', 'Montserrat')
    box_conf.setdefault('title_font_size', r'\large\bfseries')
    box_conf.setdefault('content_font', '')
    box_conf.setdefault('content_font_size', r'\normalsize')
    box_conf.setdefault('border_width', '0.8pt')
    box_conf.setdefault('cutaway_depth', '12pt')
    box_conf.setdefault('bottom_frame_height', '3pt')
    box_conf.setdefault('before_skip', '1.5em plus 0.5em minus 0.5em')
    box_conf.setdefault('after_skip', '1.5em plus 0.5em minus 0.5em')
    return box_conf


def _stage_build_and_render_preamble(app, config, ctx):
    """Pipeline Stage 2: Build template variables and render preamble.

    Performs the following in order:
    - Preamble template resolution (multi-tier override search)
    - Container color processing (CMYK conversion, WCAG enforcement)
    - Table color processing
    - Globals injection into template_vars
    - Dark mode template variables
    - Title page variables
    - Draft watermark variables
    - Microtype variables
    - Parts processing (background images, colors)
    - Heading provenance tracking + heading variables
    - Epigraph variables (per-level cascade)
    - Text inheritance logic (font/color/size propagation)
    - Color resolution Pass 2 (intra-section dd:this: cross-references)
    - Admonition CMYK processing + WCAG enforcement
    - Needs processing
    - Template resolution engine (all style types)
    - Custom style type registry processing
    - TOC / Bibliography / Index / Glossary injection
    - Final preamble rendering

    Args:
        app: The Sphinx application object.
        config: The Sphinx config object. Mutated: adds to latex_additional_files.
        ctx: Pipeline context dict from _stage_merge_and_resolve(). Mutated: adds
             'template_vars' and 'my_preamble' keys.

    Side effects:
        - Adds files to config.latex_additional_files
        - Adds 'template_vars' and 'my_preamble' to ctx
    """
    # Unpack context for readability
    g = ctx['g']
    theme_defaults = ctx['theme_defaults']
    theme_style_paths = ctx['theme_style_paths']
    resolve_val = ctx['resolve_val']
    dark_mode = ctx['dark_mode']
    wcag_level = ctx['wcag_level']
    wcag_color_debug = ctx['wcag_color_debug']
    main_font_size_str = ctx['main_font_size_str']
    main_font_size_pt = ctx['main_font_size_pt']
    tp = ctx['tp']
    headings = ctx['headings']
    parts = ctx['parts']
    draft = ctx['draft']
    microtype = ctx['microtype']
    epigraphs = ctx['epigraphs']
    admonitions = ctx['admonitions']
    needs = ctx['needs']
    containers = ctx['containers']
    tables = ctx['tables']
    figures = ctx['figures']
    code = ctx['code']
    sidebar = ctx['sidebar']
    highlights = ctx['highlights']
    topic = ctx['topic']
    contents = ctx['contents']
    todo = ctx['todo']
    toc = ctx['toc']
    bibliography = ctx['bibliography']
    index = ctx['index']
    glossary = ctx['glossary']
    links = ctx['links']
    semantic_palette = ctx['semantic_palette']
    page_bg = ctx['page_bg']
    adapt_to_page = ctx['adapt_to_page']
    designed_page = ctx['designed_page']
    compress_dark = ctx['compress_dark']
    compress_light = ctx['compress_light']
    merged_configs = ctx['merged_configs']
    pkg_dir = ctx['pkg_dir']

    # --- PREAMBLE RESOLUTION (multi-tier override) ---
    # Search order:
    # 1. doxtr_preamble_path — custom directory under confdir or srcdir
    # 2. theme_style_paths   — preamble/preamble.tex_t under each theme path
    # 3. Core package fallback — pkg_dir/preamble.tex_t (always present)
    # Theme authors: set doxtr_preamble_path = 'my_preamble_dir' in conf.py,
    # then place preamble.tex_t in <confdir>/my_preamble_dir/.
    _preamble_candidates = []
    _preamble_override_folder = getattr(config, 'doxtr_preamble_path', None)
    if _preamble_override_folder:
        _preamble_candidates.extend([
            Path(app.confdir) / _preamble_override_folder / "preamble.tex_t",
            Path(app.srcdir) / _preamble_override_folder / "preamble.tex_t",
        ])
    for _t_path in theme_style_paths:
        _preamble_candidates.append(Path(_t_path) / "preamble" / "preamble.tex_t")
    _preamble_candidates.append(pkg_dir / "preamble.tex_t")  # core fallback — keep in place
    preamble_path = next((p for p in _preamble_candidates if p.exists()), None)

    if preamble_path is not None:
        env = Environment(block_start_string='<%', block_end_string='%>', variable_start_string='<<', variable_end_string='>>', comment_start_string='<#', comment_end_string='#>')
        template = env.from_string(preamble_path.read_text(encoding="utf-8"))
        template_vars = {}

        # --- CONTAINERS ---
        safe_containers = {}
        requested_styles = set()
        for c_name, c_conf in containers.items():
            safe_name = _RE_SAFE_NAME.sub('', c_name)
            if not safe_name:
                logger.warning(f"[Doxtr Core] Container '{c_name}' produces empty LaTeX name after sanitization. Skipping.")
                continue
            t_color = c_conf.get('title_color', '#000000')
            c_conf['title_color_cmyk'] = safe_cmyk(t_color)
            # WCAG contrast enforcement: ensure title text and icon are readable
            # against the ACTUAL title background. For most container styles,
            # title_color IS the title background (colbacktitle in tcolorbox).
            # For folder-style containers, the actual background is
            # title_background_color (a separate key). Use the actual bg for
            # contrast checks to avoid adjusting against the wrong surface.
            _title_actual_bg = c_conf.get('title_background_color') or t_color
            # If no explicit title_font_color, auto-generate one that contrasts
            # against the title background (passing it as both fg and bg forces
            # the function to produce a contrasting foreground from scratch).
            _title_font = c_conf.get('title_font_color') or get_highest_contrast_color(_title_actual_bg, _title_actual_bg, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug)
            _title_font = get_highest_contrast_color(_title_font, _title_actual_bg, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug) or _title_font
            c_conf['title_font_color_cmyk'] = safe_cmyk(_title_font)
            _title_icon = c_conf.get('title_icon_color') or c_conf.get('title_font_color') or '#FFFFFF'
            _title_icon = get_highest_contrast_color(_title_icon, _title_actual_bg, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug) or _title_icon
            c_conf['title_icon_color_cmyk'] = safe_cmyk(_title_icon)
            c_conf['content_font_color_cmyk'] = safe_cmyk(c_conf.get('content_font_color') or '#000000')
            # Fallback to page_bg (not hardcoded #FFFFFF) so containers with
            # unset background match the document page in both light and dark mode.
            c_conf['content_background_color_cmyk'] = safe_cmyk(c_conf.get('content_background_color') or page_bg)
            # Folder-specific color fields (safe for all containers — no-ops if keys absent)
            c_conf['title_background_color_cmyk'] = safe_cmyk(c_conf.get('title_background_color') or c_conf.get('content_background_color') or page_bg)
            c_conf['shadow_color_cmyk'] = safe_cmyk(c_conf.get('shadow_color') or '#C0C0C0')
            c_conf.setdefault('show_shadow', True)
            c_conf['show_shadow'] = to_bool(c_conf.get('show_shadow'), default=True)
            c_conf.setdefault('shadow_color', '#C0C0C0')
            c_conf.setdefault('border_width', '0.4pt')
            c_conf.setdefault('before_skip', '2em plus 0.5em minus 0.5em')
            c_conf.setdefault('after_skip', '1.5em plus 0.5em minus 0.5em')
            c_conf.setdefault('title_font_size', r'\large\bfseries')
            c_conf.setdefault('title_icon_font_size', '')
            c_conf.setdefault('content_font_size', r'\normalsize')
            
            # Validate and normalize render_mode
            c_conf.setdefault('render_mode', RenderMode.TCOLORBOX)
            c_conf['render_mode'] = validate_render_mode(c_conf['render_mode'], c_name, logger)

            style_name = c_conf.get('title_style', 'classic')
            # Title styles are always loaded regardless of render_mode. Environment-mode
            # containers don't use ddcontainertitlestyle* in the AST output, but the body
            # template (e.g., default.tex_t) may still reference doxtr_style_requires_arg.
            # Loading unused styles has negligible cost and prevents KeyError crashes.
            requested_styles.add(style_name)
            c_conf['title_style'] = style_name
            
            c_conf['style'] = c_conf.get('style', 'default') # Body Style Fallback
            c_conf['container_frame'] = to_bool(c_conf.get('container_frame'), default=True)
            c_conf['match_text_width'] = to_bool(c_conf.get('match_text_width'), default=False)
            c_conf.setdefault('title_icon', '')
            c_conf.setdefault('title_font', '')
            c_conf.setdefault('content_font', '')
            c_conf.setdefault('title', '')              # Static title text shown when no :title: is given in RST
            c_conf['title_raw'] = to_bool(c_conf.get('title_raw'), default=False)
            safe_containers[safe_name] = c_conf
        template_vars['doxtr_containers'] = safe_containers

        # --- TABLES ---
        t_conf = tables.get('generic', CORE_CONFIG_MANIFEST.get('tables', {}).get('generic', {}))
        t_conf['header_background_color_cmyk'] = safe_cmyk(t_conf.get('header_background_color') or '#1E3A8A')
        t_conf['header_font_color_cmyk'] = safe_cmyk(t_conf.get('header_font_color') or '#FFFFFF')
        t_conf['row_color_odd_cmyk'] = safe_cmyk(t_conf.get('row_color_odd') or '#F8FAFC')
        t_conf['row_color_even_cmyk'] = safe_cmyk(t_conf.get('row_color_even') or '#FFFFFF')
        t_conf['title_background_color_cmyk'] = safe_cmyk(t_conf.get('title_background_color') or '#1E3A8A')
        t_conf['title_font_color_cmyk'] = safe_cmyk(t_conf.get('title_font_color') or '#FFFFFF')
        
        t_conf['title_background_fade_mask_color_cmyk'] = safe_cmyk(t_conf.get('title_background_fade_mask_color') or '#FFFFFF')
        t_conf['title_background_fade_shape'] = t_conf.get('title_background_fade_shape', 'rectangle').lower()

        t_style_name = t_conf.get('title_style', 'classic')
        requested_styles.add(t_style_name)
        template_vars['doxtr_tables'] = tables

        # --- GLOBALS ---
        template_vars['doxtr_show_release'] = g.get('show_release', True)
        template_vars['doxtr_show_list_of_figures'] = g.get('show_list_of_figures', False)
        template_vars['doxtr_show_list_of_tables'] = g.get('show_list_of_tables', False)
        template_vars['doxtr_show_list_of_listings'] = g.get('show_list_of_listings', False)
        template_vars['doxtr_appendix_chapter_numbering'] = g.get('appendix_chapter_numbering', True)
        template_vars['doxtr_headsep'] = g.get('headsep', '8mm')
        template_vars['doxtr_footskip'] = g.get('footskip', '14mm')
        template_vars['doxtr_headheight'] = g.get('headheight', '18pt')
        template_vars['doxtr_footheight'] = g.get('footheight', '30pt')
        template_vars['doxtr_main_font_size'] = main_font_size_str
        template_vars['doxtr_main_font_size_pt'] = main_font_size_pt
        template_vars['doxtr_suppress_warnings'] = getattr(config, 'doxtr_suppress_warnings', True)
        template_vars['doxtr_pagegoal_overflow_guard'] = getattr(config, 'doxtr_pagegoal_overflow_guard', True)
        template_vars['doxtr_global_overflow_guard'] = getattr(config, 'doxtr_global_overflow_guard', True)
        template_vars['doxtr_heading_needspace_guard'] = getattr(config, 'doxtr_heading_needspace_guard', True)
        template_vars['doxtr_durole_par_fix'] = getattr(config, 'doxtr_durole_par_fix', True)
        template_vars['extensions'] = getattr(config, 'extensions', [])

        # --- DARK MODE TEMPLATE VARIABLES ---
        # Pass dark mode state and colors to the preamble template for
        # page background and body text color rendering.
        template_vars['doxtr_dark_mode'] = dark_mode
        template_vars['doxtr_page_bg_cmyk'] = safe_cmyk(page_bg)
        # Always emit \pagecolor + \color for structural consistency between
        # light and dark mode builds.  Without this, the whatsit nodes from
        # \pagecolor/\color subtly affect \topskip calculations, causing
        # different page breaks (and thus different page counts) between modes.
        template_vars['doxtr_emit_pagecolor'] = True
        if dark_mode:
            # Maps config.doxtr_dark_text_color (hex) → RGB for preamble template
            _dark_text_color = getattr(config, 'doxtr_dark_text_color', '#DBDBDB')
            template_vars['doxtr_body_text_color_cmyk'] = safe_cmyk(_dark_text_color)
        else:
            template_vars['doxtr_body_text_color_cmyk'] = safe_cmyk('#000000')

        footer_logo = g.get('footer_logo', '')
        if footer_logo and isinstance(footer_logo, str):
            if footer_logo not in config.latex_additional_files: config.latex_additional_files.append(footer_logo)
            template_vars['doxtr_footer_logo'] = os.path.basename(footer_logo)
        else:
            template_vars['doxtr_footer_logo'] = None
        template_vars['doxtr_footer_logo_height'] = g.get('footer_logo_height', '1.5em')

        # --- TITLE PAGE ---
        template_vars['doxtr_subtitle'] = tp.get('subtitle', None)
        template_vars['doxtr_title_page_color'] = safe_cmyk(tp.get('page_color')) if tp.get('page_color') else ""
        template_vars['doxtr_title_page_top_line'] = tp.get('top_line', False)

        title_bg = tp.get('background_image', None)
        if title_bg and isinstance(title_bg, str):
            if title_bg not in config.latex_additional_files: config.latex_additional_files.append(title_bg)
            template_vars['doxtr_title_page_background_image'] = os.path.basename(title_bg)
        else:
            template_vars['doxtr_title_page_background_image'] = None

        bg_mode = tp.get('background_image_mode', None)
        if bg_mode is None:
            keep_aspect = to_bool(tp.get('background_image_keepaspectratio'), default=False)
            bg_mode = 'fit' if keep_aspect else 'stretch'
        template_vars['doxtr_title_page_background_image_mode'] = bg_mode.lower()
        
        template_vars['doxtr_title_page_background_image_align'] = tp.get('background_image_align', 'center').lower()

        opacity = tp.get('color_opacity', None)
        if opacity is None: opacity = '0.5' if template_vars['doxtr_title_page_background_image'] else '1.0'
        template_vars['doxtr_title_page_color_opacity'] = opacity
        
        for el in ['title', 'subtitle', 'author', 'date', 'release_version']:
            prefix = f'{el}_'
            template_vars[f'doxtr_{el}_font'] = tp.get(f'{prefix}font', None)
            template_vars[f'doxtr_{el}_size'] = tp.get(f'{prefix}size', None)
            color_val = tp.get(f'{prefix}color', None)
            template_vars[f'doxtr_{el}_color'] = safe_cmyk(color_val) if color_val else ""

        # --- DRAFT ---
        draft_text = draft.get('text', None)
        if draft_text:
            date_fmt = draft.get('date_format', '%Y-%m-%d %H:%M:%S %Z').strip()
            tz_str = draft.get('timezone', 'local')
            
            if tz_str.lower() == 'utc':
                dt_obj = datetime.now(timezone.utc)
            elif tz_str.lower() != 'local':
                try:
                    from zoneinfo import ZoneInfo
                    dt_obj = datetime.now(ZoneInfo(tz_str))
                except ImportError:
                    logger.warning("[Doxtr Core] Python 3.9+ required for specific timezones. Falling back to local time.")
                    dt_obj = datetime.now().astimezone()
                except Exception as e:
                    logger.warning(f"[Doxtr Core] Invalid timezone '{tz_str}': {e}. Falling back to local time.")
                    dt_obj = datetime.now().astimezone()
            else:
                dt_obj = datetime.now().astimezone()
                
            formatted_date = dt_obj.strftime(date_fmt).strip()
            ext_version = __version__
            proj_version = getattr(config, 'version', getattr(config, 'release', ''))
            draft_text = draft_text.replace('{date}', formatted_date).replace('{ext_version}', ext_version).replace('{project_version}', proj_version)
            template_vars['doxtr_draft_text'] = draft_text
            
            draft_color_str = draft.get('color', '#00000044')
            draft_opacity = "1.0"
            if draft_color_str:
                draft_color_str, draft_opacity = _split_hex_opacity(draft_color_str)
                template_vars['doxtr_draft_color_cmyk'] = safe_cmyk(draft_color_str)
                template_vars['doxtr_draft_opacity'] = draft_opacity

            template_vars['doxtr_draft_font'] = draft.get('font', None)
            template_vars['doxtr_draft_font_size'] = draft.get('font_size', r'\normalsize')
        else:
            template_vars['doxtr_draft_text'] = None

        # --- MICROTYPE ---
        # microtype is only enabled when draft mode is NOT active
        # Draft mode = fast iteration; microtype = typographic refinement
        draft_text_active = draft.get('text', None) is not None
        mt_enabled = microtype.get('enabled', True)
        template_vars['doxtr_microtype_enabled'] = mt_enabled and not draft_text_active
        template_vars['doxtr_microtype_protrusion'] = microtype.get('protrusion', True)
        template_vars['doxtr_microtype_expansion'] = microtype.get('expansion', True)
        # Kerning is disabled by default (incompatible with LuaLaTeX); forced off in draft mode regardless
        template_vars['doxtr_microtype_kerning'] = microtype.get('kerning', False) and not draft_text_active
        template_vars['doxtr_microtype_stretch'] = microtype.get('stretch', 10)
        template_vars['doxtr_microtype_shrink'] = microtype.get('shrink', 10)

        # --- PARTS ---
        processed_part_bgs = {}
        appendix_start_part = None
        if getattr(config, 'latex_toplevel_sectioning', '') == 'part':
            for p_num, p_conf in parts.items():
                if not isinstance(p_num, int): continue
                
                # Detect start of appendices based on user configuration
                if p_conf.get('appendix', False) and appendix_start_part is None:
                    appendix_start_part = p_num

                img = p_conf.get('image', None)
                if img:
                    if img not in config.latex_additional_files: config.latex_additional_files.append(img)
                    img = os.path.basename(img)
                color_str = p_conf.get('background_color', p_conf.get('color', None))
                cmyk = None
                opacity = "1.0"
                if color_str:
                    color_str, opacity = _split_hex_opacity(color_str)
                    cmyk = safe_cmyk(color_str)
                    
                processed_part_bgs[p_num] = {
                    'image': img, 'background_color_cmyk': cmyk, 'opacity': opacity,
                    'epigraph_color_cmyk': safe_cmyk(p_conf.get('epigraph_color')) if p_conf.get('epigraph_color') else "",
                    'epigraph_author_color_cmyk': safe_cmyk(p_conf.get('epigraph_author_color')) if p_conf.get('epigraph_author_color') else "",
                    'font_color_cmyk': safe_cmyk(p_conf.get('font_color')) if p_conf.get('font_color') else "",
                    'font': p_conf.get('font', None), 'size': p_conf.get('size', None),
                    'number_color_cmyk': safe_cmyk(p_conf.get('number_color')) if p_conf.get('number_color') else "",
                    'number_font': p_conf.get('number_font', None), 'number_size': p_conf.get('number_size', None),
                    'number_part_color_cmyk': safe_cmyk(p_conf.get('number_part_color')) if p_conf.get('number_part_color') else "",
                    'number_part_font': p_conf.get('number_part_font', None), 'number_part_size': p_conf.get('number_part_size', None),
                    'number_number_color_cmyk': safe_cmyk(p_conf.get('number_number_color')) if p_conf.get('number_number_color') else "",
                    'number_number_font': p_conf.get('number_number_font', None), 'number_number_size': p_conf.get('number_number_size', None),
                }
        template_vars['doxtr_part_backgrounds'] = processed_part_bgs
        template_vars['doxtr_appendix_start_part'] = appendix_start_part

        for el in ['part', 'part_number', 'part_number_part', 'part_number_number']:
            prefix = el.replace('part_', '') + '_' if el != 'part' else ''
            template_vars[f'doxtr_{el}_font'] = parts.get(f'{prefix}font', None)
            template_vars[f'doxtr_{el}_size'] = parts.get(f'{prefix}size', None)
            c_val = parts.get(f'{prefix}color', None)
            # WCAG contrast enforcement: ensure part text colors are readable
            # against the page background. The core default 'color' is #FFFFFF
            # (white for dark part-page backgrounds in light mode), which after
            # hex_dark_invert becomes #242424 — the same as the dark page bg,
            # making the text invisible. Auto-adjust to meet contrast threshold.
            if c_val:
                c_val = get_highest_contrast_color(c_val, page_bg, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug) or c_val
            template_vars[f'doxtr_{el}_color'] = safe_cmyk(c_val) if c_val else ""

        # --- HEADING PROVENANCE: track which per-level font/color/size/margin_space keys
        # were explicitly set by theme or user (not merely inherited from core defaults).
        # This is used by the inheritance logic to treat core-only values as inheritable.
        # We also mark keys that have a core-default value as "explicit" so that a
        # parent's core-default (e.g. part.color='#FFFFFF' for a dark background) does
        # not cascade down and overwrite a sibling core-default (e.g. chapter.color='#183060').
        # Inheritance from part→chapter is only meaningful when the theme/user explicitly
        # sets part.color — not when it's just the core default.
        _heading_explicit = set()
        _theme_headings = theme_defaults.get('headings', {})
        _user_headings  = getattr(config, 'doxtr_headings', {}) or {}
        _core_headings  = CORE_CONFIG_MANIFEST.get('headings', {})
        for _el in ['part', 'chapter', 'section', 'subsection', 'subsubsection']:
            # Mark keys that have a core-default value as protected from cascade-overwrite.
            # Only theme/user explicit values are allowed to cascade.
            _core_el = _core_headings.get(_el, {})
            for _prop in ['font', 'color', 'size']:
                if _core_el.get(_prop) is not None:
                    _heading_explicit.add(f'doxtr_{_el}_{_prop}')
                # size_factor is equivalent to an explicit size for provenance purposes
                if _prop == 'size' and _core_el.get('size_factor') is not None:
                    _heading_explicit.add(f'doxtr_{_el}_{_prop}')
                if _core_el.get(f'number_{_prop}') is not None:
                    _heading_explicit.add(f'doxtr_{_el}_number_{_prop}')
                if _core_el.get(f'line_{_prop}') is not None:
                    _heading_explicit.add(f'doxtr_{_el}_line_{_prop}')
            # Also protect margin_space from cascade when set in core defaults
            if 'margin_space' in _core_el:
                _heading_explicit.add(f'doxtr_{_el}_margin_space')
            # Theme and user overrides are also explicit (and override the core protection).
            for _tier in (_theme_headings, _user_headings):
                _el_tier = _tier.get(_el, {})
                for _prop in ['font', 'color', 'size']:
                    if _prop in _el_tier:
                        _heading_explicit.add(f'doxtr_{_el}_{_prop}')
                    # size_factor is equivalent to an explicit size for provenance purposes
                    if _prop == 'size' and 'size_factor' in _el_tier:
                        _heading_explicit.add(f'doxtr_{_el}_{_prop}')
                    # Also track number_<prop> and line_<prop> as explicit
                    if f'number_{_prop}' in _el_tier:
                        _heading_explicit.add(f'doxtr_{_el}_number_{_prop}')
                    if f'line_{_prop}' in _el_tier:
                        _heading_explicit.add(f'doxtr_{_el}_line_{_prop}')
                if 'margin_space' in _el_tier:
                    _heading_explicit.add(f'doxtr_{_el}_margin_space')

        # --- HEADINGS ---
        global_align = headings.get('align', 'alternate')
        global_margin = headings.get('numbers_in_margin', True)
        global_margin_space = headings.get('margin_space', '1.5em')
        global_number_sep = headings.get('number_sep', r'\marginparsep')
        global_xheight_match = headings.get('number_match_title_xheight', False)
        for el in ['chapter', 'section', 'subsection', 'subsubsection']:
            el_dict = headings.get(el, {})
            template_vars[f'doxtr_{el}_align'] = el_dict.get('align', global_align)
            template_vars[f'doxtr_{el}_number_margin'] = el_dict.get('number_margin', global_margin)
            template_vars[f'doxtr_{el}_number_line'] = el_dict.get('number_line', True if el == 'chapter' else False)
            template_vars[f'doxtr_{el}_line_height'] = el_dict.get('line_height', '10cm')
            template_vars[f'doxtr_{el}_margin_space'] = el_dict.get('margin_space', global_margin_space)
            template_vars[f'doxtr_{el}_number_sep'] = el_dict.get('number_sep', global_number_sep)
            template_vars[f'doxtr_{el}_font'] = el_dict.get('font', None)
            template_vars[f'doxtr_{el}_size'] = el_dict.get('size', None)
            
            hc = el_dict.get('color', None)
            if hc and isinstance(hc, str) and hc.startswith('dd:'):
                logger.warning(
                    f"[Doxtr Core] Unresolved color expression '{hc}' in "
                    f"headings.{el}.color after two-pass resolution. "
                    f"Check for circular references or invalid dd: syntax."
                )
            template_vars[f'doxtr_{el}_color'] = safe_cmyk(hc) if hc else ""
            
            template_vars[f'doxtr_{el}_number_font'] = el_dict.get('number_font', None)
            template_vars[f'doxtr_{el}_number_size'] = el_dict.get('number_size', None)
            
            hnc = el_dict.get('number_color', None)
            if hnc and isinstance(hnc, str) and hnc.startswith('dd:'):
                logger.warning(
                    f"[Doxtr Core] Unresolved color expression '{hnc}' in "
                    f"headings.{el}.number_color after two-pass resolution. "
                    f"Check for circular references or invalid dd: syntax."
                )
            template_vars[f'doxtr_{el}_number_color'] = safe_cmyk(hnc) if hnc else ""
            
            hlc = el_dict.get('line_color', None)
            if hlc and isinstance(hlc, str) and hlc.startswith('dd:'):
                logger.warning(
                    f"[Doxtr Core] Unresolved color expression '{hlc}' in "
                    f"headings.{el}.line_color after two-pass resolution. "
                    f"Check for circular references or invalid dd: syntax."
                )
            template_vars[f'doxtr_{el}_line_color'] = safe_cmyk(hlc) if hlc else ""

            # X-height scaling: per-level override or global fallback.
            # chapter is always excluded — the feature only applies to body-text sectioning levels.
            # to_bool() coerces strings ('true'/'false'/'yes'/'no'/'1'/'0') to bool so that
            # conf.py typos like number_match_title_xheight = 'false' don't silently enable the feature.
            if el != 'chapter':
                template_vars[f'doxtr_{el}_number_match_title_xheight'] = to_bool(
                    el_dict.get('number_match_title_xheight', global_xheight_match), default=False)
            # chapter: never set a template var — the preamble loop only iterates
            # section/subsection/subsubsection, so this key would be dead. Omitting it
            # avoids giving theme authors the false impression that chapter can be controlled.

        # --- EPIGRAPHS ---
        align_map = {'left': r'\raggedright', 'right': r'\raggedleft', 'center': r'\centering'}
        template_vars['doxtr_epigraph_width'] = epigraphs.get('width', '0.5\\textwidth')
        template_vars['doxtr_epigraph_format'] = _RE_HASH_NUM.sub('##1', epigraphs.get('format', '--- #1'))
        template_vars['doxtr_epigraph_align_box'] = align_map.get(epigraphs.get('align_box', 'right'), r'\raggedleft')
        template_vars['doxtr_epigraph_align_text'] = align_map.get(epigraphs.get('align_text', 'left'), r'\raggedright')
        template_vars['doxtr_epigraph_align_author'] = align_map.get(epigraphs.get('align_author', 'right'), r'\raggedleft')
        template_vars['doxtr_epigraph_font'] = epigraphs.get('font', None)
        template_vars['doxtr_epigraph_size'] = epigraphs.get('size', None)
        
        ec = epigraphs.get('color', None)
        if ec and isinstance(ec, str) and ec.startswith('dd:'):
            logger.warning(
                f"[Doxtr Core] Unresolved color expression '{ec}' in "
                f"epigraphs.color after two-pass resolution. "
                f"Check for circular references or invalid dd: syntax."
            )
        template_vars['doxtr_epigraph_color'] = safe_cmyk(ec) if ec else ""
        
        template_vars['doxtr_epigraph_author_font'] = epigraphs.get('author_font', None)
        template_vars['doxtr_epigraph_author_size'] = epigraphs.get('author_size', None)
        
        eac = epigraphs.get('author_color', None)
        if eac and isinstance(eac, str) and eac.startswith('dd:'):
            logger.warning(
                f"[Doxtr Core] Unresolved color expression '{eac}' in "
                f"epigraphs.author_color after two-pass resolution. "
                f"Check for circular references or invalid dd: syntax."
            )
        template_vars['doxtr_epigraph_author_color'] = safe_cmyk(eac) if eac else ""

        for idx, level in enumerate(['part', 'chapter', 'section', 'subsection', 'subsubsection']):
            el_dict = epigraphs.get(level, {})
            for prop in ['width', 'format']:
                val = el_dict.get(prop, template_vars.get(f'doxtr_{["epigraph", "part_epigraph", "chapter_epigraph", "section_epigraph", "subsection_epigraph"][idx]}_{prop}' if idx > 0 else f'doxtr_epigraph_{prop}'))
                if val and prop == 'format': val = _RE_HASH_NUM.sub('##1', str(val))
                template_vars[f'doxtr_{level}_epigraph_{prop}'] = val
            for prop in ['align_box', 'align_text', 'align_author']:
                val = el_dict.get(prop, None)
                val_mapped = align_map.get(val, r'\raggedleft' if prop != 'align_text' else r'\raggedright') if val else template_vars.get(f'doxtr_{["epigraph", "part_epigraph", "chapter_epigraph", "section_epigraph", "subsection_epigraph"][idx]}_{prop}' if idx > 0 else f'doxtr_epigraph_{prop}')
                template_vars[f'doxtr_{level}_epigraph_{prop}'] = val_mapped
            for prop in ['font', 'size', 'color', 'author_font', 'author_size', 'author_color']:
                val = el_dict.get(prop, template_vars.get(f'doxtr_{["epigraph", "part_epigraph", "chapter_epigraph", "section_epigraph", "subsection_epigraph"][idx]}_{prop}' if idx > 0 else f'doxtr_epigraph_{prop}'))
                if val and 'color' in prop:
                    if isinstance(val, str) and val.startswith('dd:'):
                        logger.warning(
                            f"[Doxtr Core] Unresolved color expression '{val}' in "
                            f"epigraphs.{level}.{prop} after two-pass resolution. "
                            f"Check for circular references or invalid dd: syntax."
                        )
                    val = safe_cmyk(val)
                template_vars[f'doxtr_{level}_epigraph_{prop}'] = val

        # --- TEXT INHERITANCE LOGIC ---
        if g.get('inherit_all', True):
            # NOTE: epigraph and epigraph_author hierarchies are intentionally absent here.
            # The per-level epigraph loop above implements an inline cascade via indexed
            # fallback keys (global → part → chapter → section → …), so all per-level
            # epigraph slots are already fully populated before this block runs.
            # Adding them here would be dead code: every slot is truthy, making the guard
            # `if not template_vars.get(key)` always False.
            for hierarchy in [['part', 'chapter', 'section', 'subsection', 'subsubsection'], ['part_number', 'chapter_number', 'section_number', 'subsection_number', 'subsubsection_number'], ['chapter_line', 'section_line', 'subsection_line', 'subsubsection_line']]:
                for prop, is_enabled in [('font', g.get('inherit_font', True)), ('color', g.get('inherit_color', True)), ('size', g.get('inherit_size', False))]:
                    if is_enabled:
                        current_val = template_vars.get(f'doxtr_{hierarchy[0]}_{prop}', None)
                        for i in range(1, len(hierarchy)):
                            key = f'doxtr_{hierarchy[i]}_{prop}'
                            if not template_vars.get(key) or key not in _heading_explicit:
                                template_vars[key] = current_val
                            else:
                                current_val = template_vars[key]
            # --- MARGIN SPACE INHERITANCE ---
            # Propagate margin_space down the heading hierarchy (chapter → section → subsection → subsubsection)
            margin_hierarchy = ['chapter', 'section', 'subsection', 'subsubsection']
            current_val = template_vars.get('doxtr_chapter_margin_space', None)
            for i in range(1, len(margin_hierarchy)):
                key = f'doxtr_{margin_hierarchy[i]}_margin_space'
                if not template_vars.get(key) or key not in _heading_explicit:
                    template_vars[key] = current_val
                else:
                    current_val = template_vars[key]

        for prop in ['font', 'color', 'size']:
            if not template_vars.get(f'doxtr_part_number_part_{prop}'): template_vars[f'doxtr_part_number_part_{prop}'] = template_vars.get(f'doxtr_part_number_{prop}')
            if not template_vars.get(f'doxtr_part_number_number_{prop}'): template_vars[f'doxtr_part_number_number_{prop}'] = template_vars.get(f'doxtr_part_number_{prop}')

        # -----------------------------------------------------------------------
        # COLOR RESOLUTION — PASS 2
        # Catches intra-section dd:this: cross-references where key iteration
        # order left values unresolved in Pass 1 (e.g. dd:this:title_background_color
        # iterated before title_background_color was resolved).
        # NOTE: The TEXT INHERITANCE LOGIC above operates on template_vars (CMYK
        # strings), not on merged_configs.  Pass 2 does not benefit from
        # inheritance propagation; merged_configs is unchanged by that block.
        # -----------------------------------------------------------------------
        for section_name, section_dict in merged_configs.items():
            resolve_all_colors(
                section_dict, semantic_palette, page_bg, section_name,
                theme_defaults, CORE_CONFIG_MANIFEST,
                getattr(config, 'doxtr_' + section_name, {}),
                root_config=merged_configs,
                wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
            )

        # --- ADMONITIONS ---
        admon_types = list(CORE_ADMONITION_TYPES)  # start from the canonical core list
        for k in admonitions.keys():
            if k.lower() not in admon_types:
                admon_types.append(k.lower())
        template_vars['admon_types'] = admon_types
        admon_props = ['title_icon', 'title_icon_color', 'title_icon_size', 'title_icon_padding', 'title_decoration_spacing', 'title_font', 'title_font_color', 'title_font_size', 'title_background_color', 'title_icon_box_background_color', 'content_background_color', 'content_background_color_nested', 'content_font', 'content_font_color', 'content_font_size', 'before_skip', 'after_skip']
        
        admon_styles_map = {}
        requested_admon_styles = set()
        
        for t in admon_types:
            t_dict = admonitions.get(t, {})
            gen_dict = admonitions.get('generic', CORE_CONFIG_MANIFEST.get('admonitions', {}).get('generic', {}))
            
            style_name = t_dict.get('style', gen_dict.get('style', t))
            admon_styles_map[t] = style_name
            requested_admon_styles.add(style_name)
            
            for p in admon_props:
                val = t_dict.get(p)
                if val is None:
                    val = gen_dict.get(p)
                if val is None and t != 'generic':
                    val = CORE_CONFIG_MANIFEST.get('admonitions', {}).get('generic', {}).get(p)
                
                # Check root user config override layer
                if val is None:
                    val = template_vars.get(f'doxtr_admonition_generic_{p}')
                
                if p == 'title_icon' and val and not str(val).strip().startswith('\\') and not str(val).strip().startswith('<'):
                    if val not in config.latex_additional_files: config.latex_additional_files.append(val)
                    val = f"\\includegraphics[height=1em, keepaspectratio]{{{os.path.basename(val)}}}"

                template_vars[f'doxtr_admonition_{t}_{p}'] = val or ""
                if p.endswith('_color') or p.endswith('_nested'):
                    template_vars[f'doxtr_admonition_{t}_{p}_cmyk'] = safe_cmyk(val)
        
        caution_bg = template_vars.get('doxtr_admonition_caution_title_background_color')
        caution_box_bg = template_vars.get('doxtr_admonition_caution_title_icon_box_background_color')
        if admonitions.get('caution', {}).get('title_icon_color') is None:
            safe_icon_color = get_highest_contrast_color(caution_bg, caution_box_bg, wcag_level=wcag_level, color_debug=wcag_color_debug)
            template_vars['doxtr_admonition_caution_title_icon_color'] = safe_icon_color
            template_vars['doxtr_admonition_caution_title_icon_color_cmyk'] = safe_cmyk(safe_icon_color)
        template_vars['doxtr_admon_styles_map'] = admon_styles_map

        # --- NEEDS ---
        need_types = ['generic']
        if hasattr(config, 'needs_types') and config.needs_types: need_types.extend([t.get('directive', '').lower() for t in config.needs_types if t.get('directive')])
        for k in needs.keys():
            if k.lower() not in need_types: need_types.append(k.lower())
            
        template_vars['need_types'] = need_types
        need_styles_map = {}
        requested_need_styles = set()
        
        for t in need_types:
            t_dict = needs.get(t, {})
            gen_dict = needs.get('generic', CORE_CONFIG_MANIFEST.get('needs', {}).get('generic', {}))
            style_name = t_dict.get('style', gen_dict.get('style', t))
            need_styles_map[t] = style_name
            requested_need_styles.add(style_name)
            
            for p in ['title_font', 'title_font_size', 'title_color', 'title_background_color', 'title_icon', 'title_icon_size', 'title_icon_color', 'title_icon_raise', 'title_icon_raise_offset', 'title_vertical_position', 'metadata_background_color', 'metadata_font', 'metadata_font_size', 'metadata_font_color', 'metadata_key_font', 'metadata_key_color', 'metadata_key_font_size', 'content_background_color', 'content_font', 'content_font_size', 'content_font_color', 'segmentation_style', 'segmentation_color', 'before_skip', 'after_skip']:
                
                # Bulletproof fallback chain matching Admonitions
                val = t_dict.get(p)
                if val is None: val = gen_dict.get(p)
                if val is None: val = needs.get(p)
                
                if val is None:
                    if p == 'segmentation_color':
                        val = template_vars.get(f'doxtr_need_{t}_title_background_color') or CORE_CONFIG_MANIFEST.get('needs', {}).get('generic', {}).get('title_background_color', '#0092FA')
                    else:
                        val = CORE_CONFIG_MANIFEST.get('needs', {}).get('generic', {}).get(p, '')
            
                if p == 'title_icon' and val and not str(val).strip().startswith('\\') and not str(val).strip().startswith('<'):
                    if val not in config.latex_additional_files: config.latex_additional_files.append(val)
                    val = f"\\includegraphics[height=1em, keepaspectratio]{{{os.path.basename(val)}}}"
            
                if p == 'segmentation_style':
                    val_str = str(val).lower()
                    val = r'\draw[draw=none] (segmentation.west) -- (segmentation.east);' if val_str in ['none', 'hidden', 'false', '0', '', 'empty'] else f"\\draw[{val_str}, draw=ddneed@{t}@seglinefg, line width=0.5pt] (segmentation.west) -- (segmentation.east);"

                template_vars[f'doxtr_need_{t}_{p}'] = val
                if p.endswith('_color'): 
                    template_vars[f'doxtr_need_{t}_{p}_cmyk'] = safe_cmyk(val)

            v_pos = t_dict.get('title_vertical_position', gen_dict.get('title_vertical_position', needs.get('title_vertical_position', None)))
            manual_raise = t_dict.get('title_icon_raise', gen_dict.get('title_icon_raise', needs.get('title_icon_raise', None)))
            offset = t_dict.get('title_icon_raise_offset', gen_dict.get('title_icon_raise_offset', needs.get('title_icon_raise_offset', '0pt'))) or '0pt'

            if v_pos == 'middle': raise_val = rf'\dimexpr 0.5\fontcharht\font`X - 0.5\height + {offset} \relax'
            elif v_pos == 'top': raise_val = rf'\dimexpr 0.7em - \height + {offset} \relax'
            elif v_pos == 'bottom': raise_val = offset
            else: raise_val = rf'\dimexpr {manual_raise or "0pt"} + {offset} \relax'
                
            template_vars[f'doxtr_need_{t}_icon_raise_math'] = raise_val

        template_vars['doxtr_need_styles_map'] = need_styles_map
        # Self-reference: allows templates to access all variables via v['key'] syntax.
        # This is intentional — Jinja2 templates use {{ v['some_dynamic_key'] }} when the
        # key name itself is computed or contains special characters.
        template_vars['v'] = template_vars

        # --- Strict mode and caching settings ---
        strict_mode = resolve_val('doxtr_strict_mode', 'strict_mode', False)
        use_cache = resolve_val('doxtr_cache_templates', 'cache_templates', True)

        # --- TEMPLATE RESOLUTION ENGINE ---
        # Uses the deduplicated resolve_and_render_template() helper for all style types.

        # 1. Container Title Styles
        loaded_title_styles = {}
        style_requires_arg = {}
        for style_name in requested_styles:
            rendered_content = resolve_and_render_template(
                app, env, template_vars, 'container_title', style_name,
                theme_style_paths, resolve_val, strict_mode, use_cache,
                strip_comments=True,
            )
            loaded_title_styles[style_name] = rendered_content
            style_requires_arg[style_name] = '#1' in rendered_content

        template_vars['doxtr_loaded_title_styles'] = loaded_title_styles
        template_vars['doxtr_style_requires_arg'] = style_requires_arg

        # 1.5 Container Body Resolution
        rendered_containers = []
        for c_name, c_conf in safe_containers.items():
            rendered = resolve_and_render_template(
                app, env, template_vars, 'container', c_conf['style'],
                theme_style_paths, resolve_val, strict_mode, use_cache,
                extra_ctx={'c_name': c_name, 'c_conf': c_conf},
            )
            rendered_containers.append(rendered)

        template_vars['doxtr_rendered_containers'] = rendered_containers

        # 2. Admonition Resolution
        loaded_admon_styles = {}
        for style_name in requested_admon_styles:
            template_vars['admon_style_name'] = style_name
            loaded_admon_styles[style_name] = resolve_and_render_template(
                app, env, template_vars, 'admonition', style_name,
                theme_style_paths, resolve_val, strict_mode, use_cache,
            )

        template_vars['doxtr_loaded_admon_styles'] = loaded_admon_styles

        # 3. Needs Resolution
        loaded_need_styles = {}
        for style_name in requested_need_styles:
            template_vars['need_style_name'] = style_name
            loaded_need_styles[style_name] = resolve_and_render_template(
                app, env, template_vars, 'need', style_name,
                theme_style_paths, resolve_val, strict_mode, use_cache,
            )

        template_vars['doxtr_loaded_need_styles'] = loaded_need_styles

        # 4. Title Page Resolution
        tp_style_name = tp.get('template', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_title_page'] = resolve_and_render_template(
            app, env, template_vars, 'title_page', tp_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
        )

        # 4.5 Draft Watermark Resolution
        # Rendered after all draft template_vars (doxtr_draft_text, doxtr_draft_color_cmyk,
        # doxtr_draft_opacity, doxtr_draft_font, doxtr_draft_font_size) are set above.
        # doxtr_rendered_draft is '' when no draft text is configured.
        if template_vars.get('doxtr_draft_text'):
            draft_style_name = draft.get('template', DEFAULT_STYLE_NAME)
            template_vars['doxtr_rendered_draft'] = resolve_and_render_template(
                app, env, template_vars, 'draft', draft_style_name,
                theme_style_paths, resolve_val, strict_mode, use_cache,
            )
        else:
            template_vars['doxtr_rendered_draft'] = ''

        # 5. Table Resolution
        t_style_name = t_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_tables'] = resolve_and_render_template(
            app, env, template_vars, 'table', t_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'t_conf': t_conf},
        )

        # 5.5 Figure Resolution
        f_conf = figures.get('generic', CORE_CONFIG_MANIFEST.get('figures', {}).get('generic', {}))
        f_conf['caption_background_color_cmyk'] = safe_cmyk(f_conf.get('caption_background_color') or '#FFFFFF')
        f_conf['caption_font_color_cmyk'] = safe_cmyk(f_conf.get('caption_font_color') or '#000000')

        f_style_name = f_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_figures'] = resolve_and_render_template(
            app, env, template_vars, 'figure', f_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'f_conf': f_conf},
        )

        # 6. Code Resolution
        code_conf = code
        if 'generic' not in code_conf:
            code_conf['generic'] = CORE_CONFIG_MANIFEST.get('code', {}).get('generic', {})

        for lang, conf in code_conf.items():
            gen = code_conf['generic']
            conf['title_background_color_cmyk'] = safe_cmyk(conf.get('title_background_color') or gen.get('title_background_color', '#1E3A8A'))
            conf['title_font_color_cmyk'] = safe_cmyk(conf.get('title_font_color') or gen.get('title_font_color', '#FFFFFF'))
            conf['content_background_color_cmyk'] = safe_cmyk(conf.get('content_background_color') or gen.get('content_background_color', '#F8FAFC'))
            conf['content_font_color_cmyk'] = safe_cmyk(conf.get('content_font_color') or gen.get('content_font_color', '#0F172A'))
            conf['border_color_cmyk'] = safe_cmyk(conf.get('border_color') or gen.get('border_color', '#1E3A8A'))

            conf['border_width'] = conf.get('border_width', gen.get('border_width', '1pt'))
            conf['title_font_size'] = conf.get('title_font_size', gen.get('title_font_size', r'\small\sffamily\bfseries'))
            conf['content_font_size'] = conf.get('content_font_size', gen.get('content_font_size', r'\small'))
            conf['show_mac_dots'] = conf.get('show_mac_dots', gen.get('show_mac_dots', True))
            conf['language_label'] = conf.get('language_label', gen.get('language_label', ''))
            conf['title_font'] = conf.get('title_font', gen.get('title_font', ''))
            # Per-language font override: allows different monospace fonts per language
            conf['content_font'] = conf.get('content_font', gen.get('content_font', ''))

            # Dynamic Code Icon Processing!
            conf['icon'] = conf.get('icon', gen.get('icon', ''))
            if conf['icon'] and not str(conf['icon']).strip().startswith('\\') and not str(conf['icon']).strip().startswith('<'):
                if conf['icon'] not in config.latex_additional_files:
                    config.latex_additional_files.append(conf['icon'])
                conf['icon'] = f"\\includegraphics[height=1em, keepaspectratio]{{{os.path.basename(conf['icon'])}}}"
                
            icon_color = conf.get('icon_color', gen.get('icon_color', '')) or conf.get('title_font_color', gen.get('title_font_color', '#FFFFFF'))
            # WCAG contrast enforcement: ensure code icon is readable against
            # title background. After dark inversion both colors may shift to
            # similar luminance values, making the icon invisible.
            _code_title_bg = conf.get('title_background_color', gen.get('title_background_color', '#183060'))
            icon_color = get_highest_contrast_color(icon_color, _code_title_bg, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug) or icon_color
            conf['icon_color_cmyk'] = safe_cmyk(icon_color)
            conf['icon_size'] = conf.get('icon_size', gen.get('icon_size', ''))
            conf['icon_position'] = conf.get('icon_position', gen.get('icon_position', 'after_mac_dots'))

        c_style_name = code_conf.get('generic', {}).get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_code'] = resolve_and_render_template(
            app, env, template_vars, 'code', c_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'doxtr_code': code_conf},
        )

        # 7. Sidebar Resolution
        s_conf = sidebar.copy()
        _s_title_bg = s_conf.get('title_background_color') or '#184878'
        s_conf['title_background_color_cmyk'] = safe_cmyk(_s_title_bg)
        # WCAG contrast enforcement: ensure sidebar title text and icon are
        # readable against the title background. After dark inversion, both
        # colors may shift to similar luminance, making text/icons invisible.
        _wcag_enforce_title_colors(s_conf, _s_title_bg, wcag_level, wcag_color_debug,
                                   icon_default='#78D8F0')
        s_conf['content_background_color_cmyk'] = safe_cmyk(s_conf.get('content_background_color') or '#F0F8FF')
        s_conf['content_font_color_cmyk'] = safe_cmyk(s_conf.get('content_font_color') or '#1A1A2E')
        s_conf['border_color_cmyk'] = safe_cmyk(s_conf.get('border_color') or '#184878')
        s_conf['subtitle_font_color_cmyk'] = safe_cmyk(s_conf.get('subtitle_font_color') or '#306090')
        s_conf.setdefault('border_radius', '4pt')
        s_conf.setdefault('border_width', '0.8pt')
        s_conf.setdefault('width', '')
        s_conf.setdefault('float_position', '')
        s_conf.setdefault('title_icon', '')
        s_conf.setdefault('title_font', '')
        s_conf.setdefault('title_font_size', r'\large\bfseries')
        s_conf.setdefault('subtitle_font', '')
        s_conf.setdefault('subtitle_font_size', r'\small\itshape')
        s_conf.setdefault('content_font', '')
        s_conf.setdefault('content_font_size', r'\small')
        s_conf.setdefault('before_skip', '1.5em plus 0.5em minus 0.5em')
        s_conf.setdefault('after_skip', '1.5em plus 0.5em minus 0.5em')

        s_style_name = s_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_sidebar'] = resolve_and_render_template(
            app, env, template_vars, 'sidebar', s_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'s_conf': s_conf},
        )

        # 8. Highlights Resolution
        h_conf = highlights.copy()
        h_conf['title_font_color_cmyk'] = safe_cmyk(h_conf.get('title_font_color') or '#8B6914')
        h_conf['content_background_color_cmyk'] = safe_cmyk(h_conf.get('content_background_color') or '#FFF8DC')
        h_conf['content_font_color_cmyk'] = safe_cmyk(h_conf.get('content_font_color') or '#1A1A2E')
        h_conf['border_color_cmyk'] = safe_cmyk(h_conf.get('border_color') or '#8B6914')
        h_conf.setdefault('title_text', 'Highlights')
        h_conf.setdefault('title_icon', '')
        h_conf.setdefault('title_font', 'Montserrat')
        h_conf.setdefault('title_font_size', r'\large\bfseries')
        h_conf.setdefault('border_width', '3pt')
        h_conf.setdefault('content_font', '')
        h_conf.setdefault('content_font_size', r'\normalsize')
        h_conf.setdefault('before_skip', '1.5em plus 0.5em minus 0.5em')
        h_conf.setdefault('after_skip', '1.5em plus 0.5em minus 0.5em')

        h_style_name = h_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_highlights'] = resolve_and_render_template(
            app, env, template_vars, 'highlights', h_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'h_conf': h_conf},
        )

        # 8b. Todo Resolution
        # Mirrors the Highlights block: build the CMYK color vars (the *_cmyk
        # suffixes are rgb-format strings, matching the other box types),
        # backfill non-color defaults, then resolve + render the todo template.
        td_conf = todo.copy()
        _td_title_bg = td_conf.get('title_background_color') or '#C0392B'
        td_conf['title_background_color_cmyk'] = safe_cmyk(_td_title_bg)
        # WCAG contrast enforcement: ensure the todo title text stays readable
        # against the title strip background. After dark inversion both colors
        # may shift to similar luminance, making the title invisible. Todo has
        # no title_icon_color key (the icon inherits coltitle), so skip icon
        # enforcement with icon_key=None. This sets td_conf['title_font_color_cmyk'].
        _wcag_enforce_title_colors(td_conf, _td_title_bg, wcag_level, wcag_color_debug,
                                   icon_key=None)
        td_conf['content_background_color_cmyk'] = safe_cmyk(td_conf.get('content_background_color') or '#FBE9E7')
        td_conf['content_font_color_cmyk'] = safe_cmyk(td_conf.get('content_font_color') or '#1A1A2E')
        td_conf.setdefault('title_icon', '')
        td_conf.setdefault('title_font', 'Montserrat')
        td_conf.setdefault('title_font_size', r'\large\bfseries')
        td_conf.setdefault('content_font', '')
        td_conf.setdefault('content_font_size', r'\normalsize')
        td_conf.setdefault('before_skip', '1.5em plus 0.5em minus 0.5em')
        td_conf.setdefault('after_skip', '1.5em plus 0.5em minus 0.5em')

        td_style_name = td_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_todo'] = resolve_and_render_template(
            app, env, template_vars, 'todo', td_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'td_conf': td_conf},
        )

        # 9. Topic Resolution
        topic_conf = _process_box_section(topic, 'topic', page_bg, wcag_level, wcag_color_debug,
                                          default_icon='')
        topic_style_name = topic_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_topic'] = resolve_and_render_template(
            app, env, template_vars, 'topic', topic_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'tp_conf': topic_conf},
        )

        # 10. Contents Resolution
        ct_conf = _process_box_section(contents, 'contents', page_bg, wcag_level, wcag_color_debug,
                                       default_icon=r'\faIcon{list}')
        ct_style_name = ct_conf.get('style', DEFAULT_STYLE_NAME)
        template_vars['doxtr_rendered_contents'] = resolve_and_render_template(
            app, env, template_vars, 'contents', ct_style_name,
            theme_style_paths, resolve_val, strict_mode, use_cache,
            extra_ctx={'ct_conf': ct_conf},
        )

        # --- CUSTOM STYLE TYPE REGISTRY ---
        # Process all style types registered externally via register_style_type().
        # Built-in types (sidebar, highlights, admonitions, etc.) keep their own
        # processing blocks above.  This loop handles only externally-registered types.
        # Option B (full migration of built-ins) is tracked as a follow-on refactor.
        for _st in _custom_style_types:
            _st_name = _st['name']
            _st_preamble_var = _st['preamble_var']

            # 1. Config merge: core (from factory) → theme → user
            _st_core = _st['config_section_factory']() if _st['config_section_factory'] else {}
            _st_theme = theme_defaults.get(_st_name, {})
            _st_user  = getattr(config, f'doxtr_{_st_name}', {})
            _st_conf  = deep_update(
                deep_update(copy.deepcopy(_st_core), copy.deepcopy(_st_theme)),
                copy.deepcopy(_st_user),
            )

            # 1b. Dark mode processing for custom style types.
            # Without this, custom sections would keep their light-mode hex values
            # when dark_mode is active, violating the extensibility contract.
            if dark_mode:
                _st_dark_overrides = config.doxtr_dark_overrides.get(_st_name, {})
                _st_conf = _build_dark_section(
                    _st_conf, _st_dark_overrides,
                    getattr(config, 'doxtr_dark_mode_strategy_resolved', 'invert')
                )

            # 1c. Page adaptation for custom style types.
            # Ensures registered custom element types participate in the same
            # luminance-proportional remapping as built-in sections.
            if adapt_to_page:
                _st_conf = _adapt_colors_in_dict(
                    _st_conf, designed_page, page_bg,
                    compress_dark, compress_light)

            # 2. Color resolution (dd: expressions, semantic palette)
            # NOTE: dd:core: references are not available for custom types because
            # CORE_CONFIG_MANIFEST only contains built-in sections.
            resolve_all_colors(
                _st_conf, semantic_palette, page_bg, _st_name,
                theme_defaults, CORE_CONFIG_MANIFEST,
                _st_user,
                root_config=merged_configs,
                wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
            )

            # 3. CMYK conversion for the declared color keys
            for _ck in _st['color_keys']:
                _raw = _st_conf.get(_ck)
                if _raw:
                    _st_conf[f'{_ck}_cmyk'] = safe_cmyk(_raw)

            # 3b. WCAG enforcement for registered pairs
            if _st.get('wcag_pairs'):
                for fg_key, bg_key in _st['wcag_pairs']:
                    fg_val = _st_conf.get(fg_key)
                    bg_val = _st_conf.get(bg_key)
                    if fg_val and bg_val:
                        adjusted = get_highest_contrast_color(
                            fg_val, bg_val, target='foreground',
                            wcag_level=wcag_level, color_debug=wcag_color_debug)
                        if adjusted:
                            _st_conf[fg_key] = adjusted
                            _st_conf[f'{fg_key}_cmyk'] = safe_cmyk(adjusted)

            # 4. Template resolution and rendering
            _st_style_name = _st_conf.get('style', DEFAULT_STYLE_NAME)
            template_vars[_st_preamble_var] = resolve_and_render_template(
                app, env, template_vars, _st_name, _st_style_name,
                theme_style_paths, resolve_val, strict_mode, use_cache,
                extra_ctx={f'{_st_name}_conf': _st_conf},
            )

        # --- TOC / BIBLIOGRAPHY / INDEX / GLOSSARY ---
        # These sections are flat config dicts (no .tex_t rendering).
        # The preamble template accesses individual keys directly.
        template_vars['doxtr_toc'] = toc
        template_vars['doxtr_bibliography'] = bibliography
        template_vars['doxtr_index'] = index
        template_vars['doxtr_glossary'] = glossary

        try:
            my_preamble = template.render(**template_vars)
        except Exception as e:
            logger.error(f"[Doxtr Core] Failed to render preamble.tex_t: {e}")
            raise ExtensionError(
                f"[Doxtr Core] preamble.tex_t rendering failed: {e}. "
                f"Check your doxtr_* configuration for invalid values."
            ) from e
    else:
        logger.warning("[Doxtr Core] Could not find preamble.tex_t template.")
        my_preamble = ""


    # Store results in context for Stage 3
    ctx['template_vars'] = template_vars if preamble_path is not None else {}
    ctx['my_preamble'] = my_preamble


def _stage_assemble_output(app, config, ctx):
    """Pipeline Stage 3: Font processing and final LaTeX element assembly.

    Performs the following in order:
    - Font package generation (main/sans/mono font declarations)
    - Custom font registration pipeline (API -> auto-discover -> user config -> dedup -> inject)
    - Default latex_elements setup (fncychap, papersize, pointsize, etc.)
    - sphinxsetup defaults (margins, verbatim settings)
    - Topic/Contents deprecation warnings
    - Hyperlink color processing (RGB for hyperref)
    - WCAG contrast enforcement for link colors
    - List of Figures/Tables/Listings injection
    - Final preamble injection into config.latex_elements['preamble']
    - .sty file resolution (headings, page styles)

    Args:
        app: The Sphinx application object.
        config: The Sphinx config object. Mutated: sets latex_elements,
                latex_additional_files.
        ctx: Pipeline context dict. Reads 'g', 'main_font_size_str',
             'dark_mode', 'adapt_to_page', 'wcag_level', 'wcag_color_debug',
             'page_bg', 'merged_configs', 'template_vars', 'my_preamble',
             'theme_style_paths', 'pkg_dir'.

    Side effects:
        - Builds and injects config.latex_elements['fontpkg']
        - Builds and injects config.latex_elements['preamble']
        - Adds .sty files to config.latex_additional_files
        - Sets _fonts_processed guard
    """
    # Unpack context
    g = ctx['g']
    main_font_size_str = ctx['main_font_size_str']
    main_font_size_pt = ctx['main_font_size_pt']
    dark_mode = ctx['dark_mode']
    adapt_to_page = ctx['adapt_to_page']
    wcag_level = ctx['wcag_level']
    wcag_color_debug = ctx['wcag_color_debug']
    page_bg = ctx['page_bg']
    merged_configs = ctx['merged_configs']
    template_vars = ctx['template_vars']
    my_preamble = ctx['my_preamble']
    theme_style_paths = ctx['theme_style_paths']
    pkg_dir = ctx['pkg_dir']

    # Generate font pkg
    m_font = g.get('main_font', 'Spectral')
    m_font_opt = g.get('main_font_options', '')
    s_font = g.get('sans_font', 'Montserrat')
    s_font_opt = g.get('sans_font_options', '')
    mo_font = g.get('mono_font', 'FiraCode Nerd Font')
    mo_font_opt = g.get('mono_font_options', '')
    
    # Build font option brackets — only emit [options] if non-empty
    s_font_opt_str = f"[{s_font_opt}]" if s_font_opt else ""
    mo_font_opt_str = f"[{mo_font_opt}]" if mo_font_opt else ""
    
    # SAFE PROVIDE COMMAND: Restoration of py@HeaderFamily
    dynamic_fontpkg = f"""
\\makeatletter
\\AddToHook{{package/capt-of/before}}{{\\let\\captionof\\undefined}}
\\providecommand{{\\py@HeaderFamily}}{{\\sffamily\\bfseries}}
\\makeatother
\\usepackage{{fontspec}}
\\setmainfont{{{m_font}}}[{m_font_opt}]
\\setsansfont{{{s_font}}}{s_font_opt_str}
\\setmonofont{{{mo_font}}}{mo_font_opt_str}
"""
    # --- Custom Font Registration ---
    # Processing order: API registrations → auto-discover → user config → dedup → inject

    # 0. Clear working registry for idempotent builds (test suites, sphinx-autobuild).
    #    _api_font_registrations survives — it holds theme-time register_font_family() calls.
    _clear_font_registry()

    # 1. Re-apply API registrations from theme setup() into the working list.
    _registered_fonts.extend(copy.deepcopy(_api_font_registrations))

    # 2. Auto-discover fonts from theme style paths.
    #    Scans style_path/fonts/ and (if parent is a Python package) style_path/../fonts/.
    _font_auto_discover = g.get('font_auto_discover', True)
    if _font_auto_discover:
        _theme_font_dirs: List[Path] = []
        for _style_path in (getattr(config, 'doxtr_theme_style_paths', None) or []):
            _sp = Path(_style_path)
            # Direct: style_path/fonts/
            _fdir = _sp / 'fonts'
            if _fdir.is_dir():
                _theme_font_dirs.append(_fdir)
            # Sibling: parent/fonts/ — only if parent is a Python package (safety guard)
            _parent = _sp.parent
            if (_parent / '__init__.py').exists():
                _parent_fdir = _parent / 'fonts'
                if _parent_fdir.is_dir() and _parent_fdir not in _theme_font_dirs:
                    _theme_font_dirs.append(_parent_fdir)
        for _fdir in _theme_font_dirs:
            _discoverer = _fonts_mod._font_discoverer_fn or auto_discover_fonts
            _discoverer(_fdir)

    # 3. Process user doxtr_fonts config (user wins over theme and auto-discover).
    _user_fonts = getattr(config, 'doxtr_fonts', None) or {}
    if _user_fonts:
        process_user_font_config(_user_fonts, app.confdir)

    # 4. Deduplicate: last entry per name wins (User > API > AutoDiscover).
    _deduplicate_registry()

    # 5. Validate registered fonts and 6. add files to latex_additional_files.
    _all_registered = get_registered_fonts()
    if _all_registered:
        validate_font_files(_all_registered)
        for _fpath in collect_font_files(_all_registered):
            if _fpath not in config.latex_additional_files:
                config.latex_additional_files.append(_fpath)

    # 7-8. Generate \defaultfontfeatures+ blocks and inject into fontpkg.
    #      inject_font_features() handles both the empty and non-empty cases and
    #      respects any custom renderer registered via register_font_renderer().
    inject_font_features(config.latex_elements, dynamic_fontpkg, _all_registered)

    # 8b. Inject early LuaTeX warning suppression callback into fontpkg.
    #     This must run BEFORE \usepackage{sphinx} which triggers scrlayer-scrpage's
    #     footheight check.  fontpkg is the last element Sphinx places before sphinx.sty.
    if getattr(config, 'doxtr_suppress_warnings', True):
        _early_lua_suppress = r"""
%% Early KOMA-Script footheight fix (must precede sphinx.sty loading).
%% scrlayer-scrpage checks footheight during sphinx.sty init and warns
%% if it's below the required minimum. Setting it here prevents the
%% warning from firing in the first place.
\setlength{\footheight}{30pt}
"""
        config.latex_elements['fontpkg'] = config.latex_elements.get('fontpkg', '') + _early_lua_suppress

    # 9. Set late-call guard so register_font_family() called after this point warns.
    _set_fonts_processed()

    # Use the nearest valid LaTeX class option (10pt/11pt/12pt) to avoid
    # "Unused global option" warnings.  The actual base text size is
    # controlled via \sphinxremdimen which is overridden in the preamble.
    _valid_pointsize = _nearest_valid_pointsize(main_font_size_pt)
    default_elements = {
        'fncychap': '',
        'tableofcontents': '\\tableofcontents',
        'papersize': 'a4paper',
        'pointsize': _valid_pointsize,
        'extraclassoptions': 'openright,twoside,parskip=half,numbers=noenddot',
    }
    for key, value in default_elements.items():
        if key not in config.latex_elements:
            config.latex_elements[key] = value

    user_sphinxsetup = config.latex_elements.get('sphinxsetup', '')
    setup_defaults = [
        ('hmargin', 'hmargin={2cm,3cm}'),
        ('vmargin', 'vmargin={2cm,2.5cm}'),
        ('marginpar', 'marginpar=2cm'),
        ('verbatimwithframe', 'verbatimwithframe=false'),
        ('verbatimsep', 'verbatimsep=0pt')
    ]
    missing_setups = []
    for key, default_val in setup_defaults:
        if key not in user_sphinxsetup:
            missing_setups.append(default_val)
    if missing_setups:
        if user_sphinxsetup:
            config.latex_elements['sphinxsetup'] = user_sphinxsetup.rstrip(', ') + ', ' + ', '.join(missing_setups)
        else:
            config.latex_elements['sphinxsetup'] = ', '.join(missing_setups)

    # --- Topic/Contents styling is now handled by the template system ---
    # (Previously injected div.topic_*/div.contents_* sphinxsetup keys for dark mode.
    #  Removed in v1.0.39 — see doxtr_topic and doxtr_contents config sections.)

    # --- Deprecation: div.topic_*/div.contents_* sphinxsetup keys ---
    _user_sphinxsetup = getattr(config, 'latex_elements', {}).get('sphinxsetup', '')
    if 'div.topic_' in _user_sphinxsetup or 'div.contents_' in _user_sphinxsetup:
        logger.warning(
            'doxtr-pdf-theme-core: div.topic_* and div.contents_* sphinxsetup keys '
            'are deprecated. Topic/contents styling is now managed by doxtr_topic '
            'and doxtr_contents config sections. These keys will be ignored. '
            '(Removal in 2.0.0)'
        )

    # --- Hyperlink Colors ---
    # Sphinx's InnerLinkColor/OuterLinkColor use the {rgb} color model (not CMYK)
    # because they are passed to hyperref via \spx@DeclareColorOption.
    links_conf = merged_configs.get('links', {})
    # Store resolved links config back on config for extensibility (AST processors, child themes)
    config._doxtr_resolved_links = links_conf
    inner_color_hex = links_conf.get('inner_color', '')
    outer_color_hex = links_conf.get('outer_color', '')

    # Guard against unresolved dd: expressions (e.g. broken palette reference)
    if inner_color_hex and str(inner_color_hex).startswith('dd:'):
        logger.warning(f"[Doxtr Core] links.inner_color has unresolved expression '{inner_color_hex}'. Skipping.")
        inner_color_hex = ''
    if outer_color_hex and str(outer_color_hex).startswith('dd:'):
        logger.warning(f"[Doxtr Core] links.outer_color has unresolved expression '{outer_color_hex}'. Skipping.")
        outer_color_hex = ''

    # --- WCAG contrast enforcement for link colors against page background ---
    # In dark mode or when page adaptation is active, resolved link colors may
    # not have sufficient contrast against the page background. Apply
    # get_highest_contrast_color to ensure readability.
    if (dark_mode or adapt_to_page) and inner_color_hex:
        _adjusted = get_highest_contrast_color(
            inner_color_hex, page_bg, target='foreground',
            wcag_level=wcag_level, color_debug=wcag_color_debug)
        inner_color_hex = _adjusted if _adjusted else inner_color_hex
    if (dark_mode or adapt_to_page) and outer_color_hex:
        _adjusted = get_highest_contrast_color(
            outer_color_hex, page_bg, target='foreground',
            wcag_level=wcag_level, color_debug=wcag_color_debug)
        outer_color_hex = _adjusted if _adjusted else outer_color_hex

    if inner_color_hex or outer_color_hex:
        current_sphinxsetup = config.latex_elements.get('sphinxsetup', '')
        link_setups = []
        if inner_color_hex and 'InnerLinkColor' not in current_sphinxsetup:
            _r, _g, _b = hex_to_rgb_floats(inner_color_hex)
            link_setups.append(f'InnerLinkColor={{rgb}}{{{_r:.3f},{_g:.3f},{_b:.3f}}}')
        if outer_color_hex and 'OuterLinkColor' not in current_sphinxsetup:
            _r, _g, _b = hex_to_rgb_floats(outer_color_hex)
            link_setups.append(f'OuterLinkColor={{rgb}}{{{_r:.3f},{_g:.3f},{_b:.3f}}}')
        if link_setups:
            if current_sphinxsetup:
                config.latex_elements['sphinxsetup'] = current_sphinxsetup.rstrip(', ') + ', ' + ', '.join(link_setups)
            else:
                config.latex_elements['sphinxsetup'] = ', '.join(link_setups)

    # --- Inject Lists before Index ---
    orig_printindex = config.latex_elements.get('printindex', '\\printindex')
    lists_tex = ""
    
    if template_vars.get('doxtr_show_list_of_figures', False) or template_vars.get('doxtr_show_list_of_tables', False) or template_vars.get('doxtr_show_list_of_listings', False):
        lists_tex += "\n\\makeatletter\n"
        # Natively instructs KOMA-Script to inject all Lists into the Table of Contents!
        lists_tex += "\\KOMAoptions{listof=totoc}\n"
        if template_vars.get('doxtr_show_list_of_figures', False):
            lists_tex += "  \\listoffigures\n"
        if template_vars.get('doxtr_show_list_of_tables', False):
            lists_tex += "  \\listoftables\n"
        if template_vars.get('doxtr_show_list_of_listings', False):
            lists_tex += "  \\@ifundefined{listof}{}{\\providecommand{\\lstlistlistingname}{List of Listings}\\renewcommand{\\lstlistlistingname}{List of Listings}\\listof{literalblock}{\\lstlistlistingname}}\n"
        lists_tex += "\\makeatother\n"

    config.latex_elements['printindex'] = lists_tex + orig_printindex

    # --- Inject into the final document preamble ---
    doxtr_rendered_code = template_vars.get('doxtr_rendered_code', '')
    doxtr_rendered_sidebar = template_vars.get('doxtr_rendered_sidebar', '')
    doxtr_rendered_highlights = template_vars.get('doxtr_rendered_highlights', '')
    doxtr_rendered_topic = template_vars.get('doxtr_rendered_topic', '')
    doxtr_rendered_contents = template_vars.get('doxtr_rendered_contents', '')
    doxtr_rendered_todo = template_vars.get('doxtr_rendered_todo', '')

    # Collect rendered LaTeX from all registered custom style types
    _custom_preamble_parts = []
    for _st in _custom_style_types:
        _rendered = template_vars.get(_st['preamble_var'], '')
        if _rendered:
            _custom_preamble_parts.append(_rendered)
    _custom_rendered = '\n'.join(_custom_preamble_parts)
    
    lol_tracker = r"""
% --- DOXTR LIST OF LISTINGS TRACKER ---
\makeatletter
\providecommand{\ddCurrentCodeCaption}{}
% Define the exact layout macro LaTeX needs to format the List of Listings page!
\providecommand*{\l@literalblock}{\@dottedtocline{1}{1.5em}{2.8em}}

% Create a native LaTeX counter for Code Blocks tied to the chapter
\@ifundefined{c@chapter}{
    \newcounter{ddlisting}
    \renewcommand{\theddlisting}{\arabic{ddlisting}}
}{
    \newcounter{ddlisting}[chapter]
    \renewcommand{\theddlisting}{\thechapter.\arabic{ddlisting}}
}

% Intercept Sphinx's verbatim caption macro to track the caption natively
\let\dd@orig@sphinxSetupCaptionForVerbatim\sphinxSetupCaptionForVerbatim
\renewcommand{\sphinxSetupCaptionForVerbatim}[1]{%
    \refstepcounter{ddlisting}% <--- Native increment tied to the chapter!
    \phantomsection % <--- Forces the hyperlink anchor exactly at the caption!
    \dd@orig@sphinxSetupCaptionForVerbatim{#1}%
    \gdef\ddCurrentCodeCaption{#1}%
    % Safely write to KOMA-Script's .lol (List of Listings) tracking file
    \addcontentsline{lol}{literalblock}{\protect\numberline{\theddlisting}{\ignorespaces #1}}%
}

% Clean up the caption after the environment finishes so it doesn't bleed
\xapptocmd{\endsphinxVerbatim}{\gdef\ddCurrentCodeCaption{}}{}{}
\makeatother
"""
    
    # Collect preamble hook contributions at each injection position
    _hooks_before_pkg = '\n'.join(fn() for fn, pos in _preamble_hooks if pos == 'before_packages')
    _hooks_after_pkg = '\n'.join(fn() for fn, pos in _preamble_hooks if pos == 'after_packages')
    _hooks_before_styles = '\n'.join(fn() for fn, pos in _preamble_hooks if pos == 'before_styles')
    _hooks_after_styles = '\n'.join(fn() for fn, pos in _preamble_hooks if pos == 'after_styles')

    # Assemble the final preamble with hook injection points:
    #   before_packages → my_preamble (core packages/structure) → after_packages
    #   → before_styles → rendered style blocks → after_styles → lol_tracker
    _styles_block = f"{doxtr_rendered_code}\n{doxtr_rendered_sidebar}\n{doxtr_rendered_highlights}\n{doxtr_rendered_topic}\n{doxtr_rendered_contents}\n{doxtr_rendered_todo}\n{_custom_rendered}"

    # Override \sphinxremdimen if the class option differs from the actual
    # desired base font size (e.g. class gets 11pt but we want 11.5pt).
    # _valid_pointsize was computed earlier (line ~2614) for default_elements.
    # Ensure main_font_size_str has a unit suffix for valid TeX dimension assignment.
    _size_str_for_rem = main_font_size_str if main_font_size_str.rstrip().endswith('pt') else f'{main_font_size_pt}pt'
    _remdimen_override = ''
    if _valid_pointsize != _size_str_for_rem:
        _remdimen_override = (
            f'%% Correct \\sphinxremdimen: class option is {_valid_pointsize} '
            f'but configured base size is {_size_str_for_rem}\n'
            f'\\sphinxremdimen = {_size_str_for_rem}\\relax\n'
        )

    _assembled = f"{_remdimen_override}{_hooks_before_pkg}\n{my_preamble}\n{_hooks_after_pkg}\n{_hooks_before_styles}\n{_styles_block}\n{_hooks_after_styles}\n{lol_tracker}"

    if 'preamble' in config.latex_elements: 
        config.latex_elements['preamble'] += f"\n{_assembled}"
    else: 
        config.latex_elements['preamble'] = _assembled

    if config.latex_logo and config.latex_logo not in config.latex_additional_files:
        config.latex_additional_files.append(config.latex_logo)
    
    # Resolve .sty files — theme authors and users can override via doxtr_sty_override_paths.
    # Relative paths in doxtr_sty_override_paths are resolved against confdir.
    _raw_sty_override_paths = getattr(config, 'doxtr_sty_override_paths', []) or []
    sty_override_paths = [
        str(Path(app.confdir) / p) if not Path(p).is_absolute() else p
        for p in _raw_sty_override_paths
    ]
    for _sty in ('sphinxlatexstyleheadings.sty', 'sphinxlatexstylepage.sty'):
        resolved = _resolve_sty_file(_sty, sty_override_paths, pkg_dir)
        if resolved not in config.latex_additional_files:
            config.latex_additional_files.append(resolved)


# --- Image processing (extracted to image_processing.py) ---
from .image_processing import (
    _resolve_dark_asset,
    _ADAPT_IMAGE_WHITE_FUZZ_DEFAULT,
    process_dark_images_ast,
    _recolour_dark_images,
    _adapt_image_backgrounds,
    _process_image_adapt_ast,
    register_image_processor,
    _reset_image_processor_registry,
    _get_parallel_workers,
)


def build_finished(app, exception):
    """Write XMP metadata for the built PDF document.

    Called on the Sphinx ``build-finished`` event.  When the build completes
    without error and the active builder is LaTeX, this function writes a
    ``.xmpdata`` file alongside the generated ``.tex`` output.  The file
    contains ``\\Title`` and ``\\Author`` entries consumed by the
    ``pdfx``/``hyperxmp`` LaTeX packages to embed XMP metadata in the
    final PDF.

    Args:
        app: The Sphinx application object.
        exception: If not None, the build raised an error and we skip
                   metadata generation.
    """
    if exception is not None or app.builder.name != 'latex': return
    xmp_content = f"\\Title{{{app.config.project}}}\n\\Author{{{app.config.author}}}\n"
    Path(app.builder.outdir).joinpath(f"{get_safe_filename(app.config.project)}.xmpdata").write_text(xmp_content, encoding='utf-8')

def setup(app):
    # Patch LaTeXTranslator to normalise admonition environment names.
    # WHY: Sphinx emits ``\begin{note}`` for .. note:: directives but our
    # tcolorbox-based style system defines a single ``admonition`` environment
    # for all admonition types. Without this patch, LaTeX raises "undefined
    # environment" errors for note/warning/etc. The patch is applied once
    # (guarded by _doxtr_patched) and can be disabled via
    # doxtr_patch_admonition_translator=False for themes that define per-type
    # environments themselves.
    if not getattr(LaTeXTranslator, '_doxtr_patched', False):
        _orig_visit_admonition = LaTeXTranslator.visit_admonition
        def _custom_visit_admonition(self, node):
            _orig_visit_admonition(self, node)
            # Check config flag at call time (config unavailable during setup())
            if not getattr(self.config, 'doxtr_patch_admonition_translator', True):
                return
            if self.body and '{note}' in self.body[-1]: self.body[-1] = self.body[-1].replace('{note}', '{admonition}')
        LaTeXTranslator.visit_admonition = _custom_visit_admonition
        LaTeXTranslator._doxtr_patched = True

    app.add_directive('stylebox', StyleBoxDirective)

    # Core Foundation Layers
    app.add_config_value('doxtr_theme_defaults', {}, 'env')
    app.add_config_value('doxtr_theme_style_paths', [], 'env')
    # Override directories for .sty files — theme authors and users can supply replacement
    # sphinxlatexstyleheadings.sty / sphinxlatexstylepage.sty by listing the containing
    # directory here. Paths relative to confdir are resolved automatically.
    app.add_config_value('doxtr_sty_override_paths', [], 'env')
    # Override directory for preamble.tex_t — allows theme authors and users to replace
    # the core LaTeX document structure without forking the core. Set this to a path
    # (relative to confdir or srcdir) that contains a preamble.tex_t file.
    # Themes can also place preamble/preamble.tex_t inside any doxtr_theme_style_paths entry.
    app.add_config_value('doxtr_preamble_path', None, 'env')

    # Strict mode: raises ExtensionError on missing templates instead of using fallbacks
    app.add_config_value('doxtr_strict_mode', False, 'env')
    # Template cache: caches compiled Jinja2 templates to avoid redundant parsing
    app.add_config_value('doxtr_cache_templates', True, 'env')
    # Semantic color system palette
    app.add_config_value('doxtr_semantic_palette', {}, 'env')

    # Deprecated compat: doxtr_page_background → doxtr_semantic_palette['page']
    # Remove in v1.1.0
    app.add_config_value('doxtr_page_background', None, 'env')
    
    # Automatically register ALL globals so Sphinx never throws "Unknown Config" warnings!
    app.add_config_value('doxtr_globals', {}, 'env')
    app.add_config_value('doxtr_dark_overrides', {}, 'env')
    # Dark mode: activates the parallel dark config stack.
    # Can be set at build time: sphinx-build -D doxtr_dark_mode=1 ...
    app.add_config_value('doxtr_dark_mode', False, 'env')
    # Dark mode body text color — derived from hex_dark_invert('#000000') by default.
    # Users/themes can override to control dark-mode text appearance.
    app.add_config_value('doxtr_dark_text_color', None, 'env')
    # Dark mode color strategy: 'auto' (default), 'invert', or 'passthrough'.
    # 'auto' detects page luminance and chooses 'invert' for dark pages (<0.35)
    # or 'passthrough' for light pages (≥0.35). 'invert' forces hex_dark_invert
    # on all colors (current behavior). 'passthrough' skips inversion entirely —
    # only dd: expressions and dark_overrides provide differentiation, suitable
    # for solarized/sepia/cream alternative themes with light backgrounds.
    app.add_config_value('doxtr_dark_mode_strategy', 'auto', 'env')
    # Resolved strategy (computed by config_inited from 'auto' detection or
    # explicit user value). Registered so it survives Sphinx environment pickling
    # across incremental builds. Read by build-finished hooks.
    app.add_config_value('doxtr_dark_mode_strategy_resolved', 'invert', 'env')
    # Dark palette computed by config_inited from the semantic palette and user overrides.
    # Must be registered so Sphinx serialises it into the pickled environment; without
    # registration it is lost on incremental rebuilds and _recolour_dark_images falls
    # back silently to the hardcoded page default.
    app.add_config_value('doxtr_dark_semantic_palette', {}, 'env')
    # Both are True by default; only apply when doxtr_dark_mode is True.
    # Set False to disable that processing path entirely.
    app.add_config_value('doxtr_dark_recolor_grayscale', True, 'env')
    app.add_config_value('doxtr_dark_invert_color_images', True, 'env')
    # Brightness threshold for color image lightness inversion.
    # Mean sRGB luminance (0.0–1.0). Color images above this threshold are
    # considered too bright for the dark page background and have their
    # lightness channel inverted. Default 0.65 catches white-background
    # diagrams (PlantUML, flowcharts, charts) while leaving mid-tone and
    # dark images untouched.
    app.add_config_value('doxtr_dark_image_brightness_threshold', 0.65, 'env')
    # Glob patterns matched against image filenames in outdir.
    # Matching images are excluded from all image processing (dark mode AND
    # page adaptation). Use for extension-generated images where :class: is
    # unavailable (e.g. PlantUML: ['plantuml-*.png']).
    app.add_config_value('doxtr_image_exclude_patterns', [], 'env')
    # Deprecated alias — use doxtr_image_exclude_patterns instead. Remove in v1.1.0.
    app.add_config_value('doxtr_dark_image_exclude_patterns', [], 'env')
    # Page adaptation: automatically shift all theme colors to maintain their
    # intended relationships when the page background differs from the theme's
    # designed-for background. Uses luminance-proportional remapping with
    # directional compression.
    # Values: 'auto' (adapt when page differs by >0.05 luminance),
    #          True (force adaptation), False (disable adaptation).
    # In 'auto' mode, a proactive logger.info hint is emitted when the page
    # differs significantly but adaptation is not active.
    app.add_config_value('doxtr_adapt_colors_to_page', 'auto', 'env')
    # Image background adaptation: replace white image backgrounds with the
    # page background color when page adaptation is active. Uses flood-fill
    # from image borders to detect background regions only.
    # Only active when doxtr_adapt_colors_to_page is active AND page != #FFFFFF.
    app.add_config_value('doxtr_adapt_image_backgrounds', True, 'env')
    # White detection fuzz for image background adaptation (0–255).
    # Pixels with all RGB channels >= (255 - fuzz) are considered "white".
    # Default 5 catches anti-aliased edges and minor compression artifacts.
    app.add_config_value('doxtr_adapt_image_white_fuzz', _ADAPT_IMAGE_WHITE_FUZZ_DEFAULT, 'env')
    # Number of parallel workers for image processing (dark mode + page adaptation).
    # 'auto' or 0: min(cpu_count, 8). 1: sequential (no pool overhead).
    # N > 1: use N parallel workers via ProcessPoolExecutor.
    app.add_config_value('doxtr_image_parallel_workers', 'auto', 'env')
    # Adaptation state dict set by config_inited — exposes active/designed_page/
    # compress_dark/compress_light for child themes and image processing hooks.
    app.add_config_value('doxtr_adaptation_state', {}, 'env')
    # One-version compat: register all old flat keys so Sphinx doesn't throw
    # "Unknown config value" for users/themes still using the old API.
    # Remove in v1.1.0.
    for _legacy_key in _LEGACY_GLOBAL_KEYS:
        app.add_config_value(f'doxtr_{_legacy_key}', None, 'env')
        
    # Register the nested dictionary configurations
    for conf_dict in ['title_page', 'headings', 'parts', 'epigraphs', 'draft', 'microtype', 'containers', 'tables', 'figures', 'code', 'admonitions', 'needs', 'sidebar', 'highlights', 'topic', 'contents', 'todo', 'toc', 'bibliography', 'index', 'glossary', 'links']:
        app.add_config_value(f'doxtr_{conf_dict}', {}, 'env')

    # Auto-register config values for style types already registered via
    # register_style_type() at import time (i.e. before setup() is called).
    # Theme authors who call register_style_type() inside their own setup()
    # (which runs after core setup()) must also call
    # app.add_config_value(f'doxtr_{name}', {}, 'env') themselves.
    for _st in _custom_style_types:
        _attr = f"doxtr_{_st['name']}"
        try:
            app.add_config_value(_attr, {}, 'env')
        except Exception:
            pass  # already registered (e.g. setup() called twice)

    # Container name mapping: maps RST class names to registered container styles.
    # Enables theme switching without changing source documents.
    # Example: doxtr_container_mapping = {"terminal": "lcars-terminal"}
    app.add_config_value('doxtr_container_mapping', {}, 'env')

    # Font registration: users can declaratively register custom font families.
    # See 'doxtr_fonts' in the configuration reference for the full schema.
    app.add_config_value('doxtr_fonts', {}, 'env')

    # LaTeXTranslator admonition patch: set False if your theme defines
    # per-type LaTeX environments (note, warning, etc.) and does not need
    # the normalisation to a single 'admonition' environment.
    app.add_config_value('doxtr_patch_admonition_translator', True, 'env')

    # Per-processor disable flags: set False to skip individual AST processors.
    # Useful for debugging or when a theme provides its own AST handling.
    app.add_config_value('doxtr_enable_container_processor', True, 'env')
    app.add_config_value('doxtr_enable_table_processor', True, 'env')
    app.add_config_value('doxtr_enable_codeblock_processor', True, 'env')
    app.add_config_value('doxtr_enable_epigraph_processor', True, 'env')
    app.add_config_value('doxtr_enable_sidebar_processor', True, 'env')
    app.add_config_value('doxtr_enable_highlights_processor', True, 'env')
    app.add_config_value('doxtr_enable_needs_processor', True, 'env')
    app.add_config_value('doxtr_enable_topics_processor', True, 'env')
    # Enable/disable the todo AST processor (styles the sphinx.ext.todo
    # `.. todo::` directive as a ddtodobox tcolorbox).
    app.add_config_value('doxtr_enable_todo_processor', True, 'env')
    app.add_config_value('doxtr_enable_landscape_processor', True, 'env')
    app.add_config_value('doxtr_table_auto_landscape', True, 'env')
    app.add_config_value('doxtr_landscape_min_columns', DEFAULT_MIN_COLUMNS, 'env')
    app.add_config_value('doxtr_landscape_skip_table_classes', [], 'env')
    app.add_config_value('doxtr_tabulary_overflow_guard', True, 'env')
    app.add_config_value('doxtr_pagegoal_overflow_guard', True, 'env')
    app.add_config_value('doxtr_global_overflow_guard', True, 'env')
    app.add_config_value('doxtr_heading_needspace_guard', True, 'env')
    app.add_config_value('doxtr_durole_par_fix', True, 'env')

    # Table cell overflow protection (Phase 1 + Phase 2 config)
    app.add_config_value('doxtr_table_nobreak_patterns', None, 'env')
    app.add_config_value('doxtr_table_break_chars', None, 'env')
    app.add_config_value('doxtr_table_column_width_algorithm', None, 'env')
    app.add_config_value('doxtr_table_auto_colwidths', None, 'env')
    app.add_config_value('doxtr_table_char_width_mm', None, 'env')
    app.add_config_value('doxtr_table_header_char_width_factor', None, 'env')

    # Dark file swap: intercepts RST/MyST source text before parsing to rewrite
    # directive file arguments to their _dark variants. Targets extensions that
    # consume file content at parse time (PlantUML, Mermaid, include, etc.).
    app.add_config_value('doxtr_enable_dark_file_swap', True, 'env')
    app.add_config_value('doxtr_dark_file_swap_directives', {}, 'env')
    app.add_config_value('doxtr_dark_file_swap_extensions', None, 'env')
    app.add_config_value('doxtr_dark_file_swap_extra_extensions', [], 'env')
    app.add_config_value('doxtr_dark_file_swap_exclude', [], 'env')
    app.add_config_value('doxtr_suppress_warnings', True, 'env')

    app.connect('config-inited', config_inited, priority=900)
    app.connect('build-finished', build_finished)
    app.connect('build-finished', _recolour_dark_images)
    app.connect('build-finished', _adapt_image_backgrounds)
    app.connect('doctree-resolved', process_dark_images_ast, priority=991)
    app.connect('doctree-resolved', _process_image_adapt_ast, priority=990)
    app.connect('doctree-resolved', process_containers_ast, priority=998)
    app.connect('doctree-resolved', fix_block_after_paragraph, priority=PARAGRAPH_FIX_PRIORITY)
    app.connect('doctree-resolved', process_sidebar_ast, priority=994)
    app.connect('doctree-resolved', process_highlights_ast, priority=993)
    app.connect('doctree-resolved', process_topics_ast, priority=990)
    # Todo runs at priority 992: after highlights (993), before topics (990).
    # 992 is also the default priority for user processors registered via
    # register_ast_processor. At equal priority Sphinx runs handlers in
    # connection order, and core connects todo here during setup() — before
    # any user processor — so core todo runs first.
    app.connect('doctree-resolved', process_todo_ast, priority=992)
    app.connect('doctree-resolved', process_tables_ast, priority=996)
    app.connect('doctree-resolved', process_codeblocks_ast, priority=995)
    app.connect('doctree-resolved', process_epigraph_ast, priority=997)
    app.connect('doctree-resolved', process_needs_ast, priority=999)
    # Landscape must run AFTER tables (ascending priority order in Sphinx)
    # so it can read doxtr_min_table_width_mm set by the table processor.
    app.connect('doctree-resolved', process_landscape_ast, priority=1001)
    app.connect('builder-inited', _connect_deferred_custom_processors)  # priority=500 (default): fires after all extension setup() calls

    # Dark file swap: source-read hook rewrites directive file paths to _dark
    # variants before parsing. Priority 500 (Sphinx default).
    app.connect('source-read', swap_dark_sources, priority=500)
    # include-read requires Sphinx >= 7.2.4 — guard with version check.
    import sphinx as _sphinx_mod
    if _sphinx_mod.version_info[:3] >= (7, 2, 4):
        app.connect('include-read', swap_dark_includes, priority=500)
    else:
        logger.debug(
            '[Doxtr Core] include-read event not available (Sphinx %s < 7.2.4). '
            'Included files will not have directive paths swapped to _dark variants.',
            _sphinx_mod.__version__
        )

    return {'version': __version__, 'parallel_read_safe': True, 'parallel_write_safe': True}