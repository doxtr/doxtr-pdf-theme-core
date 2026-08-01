"""Doxtr PDF Theme Core - A Sphinx extension for professional LaTeX/PDF output.

This package provides a base layer for generating professional LaTeX → PDF output.
It is designed to be inherited by child themes that customize the look and feel.
"""
import copy
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from sphinx.util import logging
from jinja2 import Environment
from sphinx.writers.latex import LaTeXTranslator
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.errors import ExtensionError

# --- Import from refactored modules ---
from .utils import (
    get_safe_filename, get_highest_contrast_color,
    hex_to_cmyk_string, deep_update,
    resolve_all_colors, to_bool,
)
from .shell_icons import make_shell_icon, micro_shell_icon, genos_shell_icon
from .core_fallbacks import (
    DEFAULT_TITLE_STYLES, DEFAULT_ADMONITION_STYLE, DEFAULT_NEED_STYLE,
    DEFAULT_CONTAINER_STYLE, DEFAULT_TABLE_STYLE, DEFAULT_FIGURE_STYLE,
    DEFAULT_CODE_STYLE, DEFAULT_SIDEBAR_STYLE, DEFAULT_HIGHLIGHTS_STYLE
)
from .core_config import CORE_CONFIG_MANIFEST, DOXTR_GLOBALS, DOXTR_SEMANTIC_PALETTE

# Import from new refactored modules (Plan 03)
from .latex_escape import esc_latex, LATEX_ESCAPE_MAP
from .colors import safe_cmyk, prepare_cmyk_colors, CONTAINER_COLOR_KEYS, TABLE_COLOR_KEYS
from .templates import (
    LATEX_STYLES_DIR, DEFAULT_STYLE_NAME, CLASSIC_STYLE_NAME, GENERIC_TYPE_NAME,
    STYLE_TYPES, STYLE_FALLBACKS,
    clear_template_cache, get_template, resolve_template,
    render_template, resolve_and_render_template,
)
from .config import (
    VALID_KEYS, CORE_ADMONITION_TYPES, validate_config_keys,
    make_resolve_val_fn, make_merge_section_fn,
)
from .ast_processors import (
    process_containers_ast,
    process_tables_ast,
    process_codeblocks_ast,
    process_epigraph_ast,
    process_sidebar_ast,
    process_highlights_ast,
    process_needs_ast,
    render_nodes_to_latex,
)

logger = logging.getLogger(__name__)

__version__ = "1.0.1"

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
]

# --- EXTENSIBLE AST PROCESSOR REGISTRY (Task 2.1) ---
# Third-party extensions may register custom doctree-resolved handlers here.
# Each entry is a callable: fn(app, doctree, docname) -> None
# They are invoked in registration order at priority 993 (after all core processors).
_custom_ast_processors: list = []


def register_ast_processor(fn) -> None:
    """Register a custom doctree-resolved AST processor.

    This function allows theme authors and downstream extensions to hook into
    the AST processing pipeline without monkey-patching. Registered processors
    are called in registration order at priority 993, after all core processors
    but before the document is written.

    Args:
        fn: A callable with signature fn(app, doctree, docname).
            Called for every resolved doctree, latex builder only.

    Example:
        >>> from doxtr_pdf_theme_core import register_ast_processor
        >>> def my_processor(app, doctree, docname):
        ...     for node in doctree.traverse(nodes.paragraph):
        ...         # Custom processing
        ...         pass
        >>> register_ast_processor(my_processor)
    """
    _custom_ast_processors.append(fn)


def _dispatch_custom_ast_processors(app, doctree, docname):
    """Invoke all registered custom AST processors.

    This function is connected to the 'doctree-resolved' event at priority 993,
    after all core processors have run.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return
    for fn in _custom_ast_processors:
        try:
            fn(app, doctree, docname)
        except Exception as e:
            logger.warning(
                f"[Doxtr Core] Custom AST processor '{fn.__name__}' raised: {e}"
            )

# --- Precompiled regex patterns ---
# Compiled once at import time for performance (Task 4.5)
_RE_SAFE_NAME = re.compile(r'[^a-zA-Z]')
_RE_HASH_NUM = re.compile(r'#+1')




class StyleBoxDirective(Directive):
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

def config_inited(app, config):
    # Clear template cache at the start of each build to avoid stale templates
    # when using sphinx-autobuild or similar tools.
    clear_template_cache()

    if config.latex_engine not in ('lualatex',):
        config.latex_engine = 'lualatex'
    if not config.latex_docclass: config.latex_docclass = {'manual': 'scrbook'}
    else: config.latex_docclass.setdefault('manual', 'scrbook')

    safe_project = get_safe_filename(config.project)
    if not config.latex_documents or 'outpdfname.tex' in config.latex_documents[0][1]:
        config.latex_documents = [(config.root_doc, f"{safe_project}.tex", config.project, config.author, 'manual')]

    # --- THREE-TIER MERGE ARCHITECTURE ---
    theme_defaults = getattr(config, 'doxtr_theme_defaults', {})
    theme_style_paths = getattr(config, 'doxtr_theme_style_paths', [])

    def resolve_val(conf_attr, theme_key, fallback=None, section=None):
        val = getattr(config, conf_attr, None)
        if val is not None: return val
        if theme_key in theme_defaults: return theme_defaults[theme_key]
        if section:
            section_conf = CORE_CONFIG_MANIFEST.get(section, {})
            if isinstance(section_conf, dict):
                val = section_conf.get(theme_key, fallback)
            else:
                val = section_conf if section_conf is not None else fallback
            if val is not None: return val
        return DOXTR_GLOBALS.get(theme_key, fallback)

    def merge_section(name, config_attr=None):
        """Three-tier merge: core → theme → user for a config section."""
        attr = config_attr or f'doxtr_{name}'
        section_core = CORE_CONFIG_MANIFEST.get(name, {})
        section_theme = theme_defaults.get(name, {})
        section_user = getattr(config, attr, {})
        return deep_update(deep_update(copy.deepcopy(section_core), section_theme), section_user)

    # Merge core configs via manifest
    tp = merge_section('title_page')
    headings = merge_section('headings')
    parts = merge_section('parts')
    draft = merge_section('draft')
    microtype = merge_section('microtype')
    epigraphs = merge_section('epigraphs')
    admonitions = merge_section('admonitions')
    needs = merge_section('needs')
    containers = merge_section('containers')
    tables = merge_section('tables')
    figures = merge_section('figures')
    code_blocks = merge_section('code')
    sidebar = merge_section('sidebar')
    highlights = merge_section('highlights')

    # --- CONFIGURATION VALIDATION ---
    # Warn about unknown keys in user-provided config sections (typo detection)
    validate_config_keys(getattr(config, 'doxtr_title_page', {}), 'title_page')
    validate_config_keys(getattr(config, 'doxtr_draft', {}), 'draft')
    validate_config_keys(getattr(config, 'doxtr_epigraphs', {}), 'epigraphs')
    validate_config_keys(getattr(config, 'doxtr_headings', {}), 'headings')
    validate_config_keys(getattr(config, 'doxtr_microtype', {}), 'microtype')
    validate_config_keys(getattr(config, 'doxtr_sidebar', {}), 'sidebar')
    validate_config_keys(getattr(config, 'doxtr_highlights', {}), 'highlights')
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

    # --- SEMANTIC COLOR SYSTEM ---
    # Merge palette: core → theme → user
    palette_core = DOXTR_SEMANTIC_PALETTE
    palette_theme = theme_defaults.get('semantic_palette', {})
    palette_user = getattr(config, 'doxtr_semantic_palette', {})
    semantic_palette = deep_update(deep_update(copy.deepcopy(palette_core), palette_theme), palette_user)

    # Get page background
    page_bg = resolve_val('doxtr_page_background', 'page_background', '#FFFFFF')

    # Get WCAG settings
    wcag_level = resolve_val('doxtr_wcag_level', 'wcag_level', 4.5)
    wcag_color_debug = resolve_val('doxtr_wcag_color_debug', 'wcag_color_debug', False)

    # Collect all merged config sections for resolution
    merged_configs = {
        'admonitions': admonitions,
        'needs': needs,
        'containers': containers,
        'tables': tables,
        'figures': figures,
        'code': code_blocks,
        'headings': headings,
        'parts': parts,
        'title_page': tp,
        'draft': draft,
        'microtype': microtype,
        'epigraphs': epigraphs,
        'sidebar': sidebar,
        'highlights': highlights,
    }

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
    # INHERITANCE
    # Copy font/color/size down the heading/epigraph hierarchy.
    # After this pass, inherited values may be dd: expressions from a parent
    # level that were not present in the child's original dict.
    # -----------------------------------------------------------------------
    # (inheritance logic follows in the existing code below)

    # -----------------------------------------------------------------------
    # COLOR RESOLUTION — PASS 2
    # Re-resolve dd: expressions that appeared via inheritance.
    # -----------------------------------------------------------------------
    for section_name, section_dict in merged_configs.items():
        resolve_all_colors(
            section_dict, semantic_palette, page_bg, section_name,
            theme_defaults, CORE_CONFIG_MANIFEST,
            getattr(config, 'doxtr_' + section_name, {}),
            root_config=merged_configs,
            wcag_level=wcag_level, wcag_color_debug=wcag_color_debug,
        )

    # Store merged containers back into config so AST walkers can access them
    config.doxtr_containers = containers

    pkg_dir = Path(__file__).parent.resolve()
    preamble_path = pkg_dir / "preamble.tex_t"
    
    if preamble_path.exists():
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
            c_conf['title_font_color_cmyk'] = safe_cmyk(c_conf.get('title_font_color') or get_highest_contrast_color(t_color, t_color, target='foreground', wcag_level=wcag_level, color_debug=wcag_color_debug))
            c_conf['title_icon_color_cmyk'] = safe_cmyk(c_conf.get('title_icon_color') or c_conf.get('title_font_color') or '#FFFFFF')
            c_conf['content_font_color_cmyk'] = safe_cmyk(c_conf.get('content_font_color') or '#000000')
            c_conf['content_background_color_cmyk'] = safe_cmyk(c_conf.get('content_background_color') or '#FFFFFF')
            # Folder-specific color fields (safe for all containers — no-ops if keys absent)
            c_conf['title_background_color_cmyk'] = safe_cmyk(c_conf.get('title_background_color') or c_conf.get('content_background_color') or '#FFFFFF')
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
            
            style_name = c_conf.get('title_style', 'classic')
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
        template_vars['doxtr_show_release'] = resolve_val('doxtr_show_release', 'show_release', True)
        template_vars['doxtr_show_list_of_figures'] = resolve_val('doxtr_show_list_of_figures', 'show_list_of_figures', False)
        template_vars['doxtr_show_list_of_tables'] = resolve_val('doxtr_show_list_of_tables', 'show_list_of_tables', False)
        template_vars['doxtr_show_list_of_listings'] = resolve_val('doxtr_show_list_of_listings', 'show_list_of_listings', False)
        template_vars['doxtr_appendix_chapter_numbering'] = resolve_val('doxtr_appendix_chapter_numbering', 'appendix_chapter_numbering', True)
        template_vars['doxtr_headsep'] = resolve_val('doxtr_headsep', 'headsep', '8mm')
        template_vars['doxtr_footskip'] = resolve_val('doxtr_footskip', 'footskip', '10mm')
        template_vars['doxtr_headheight'] = resolve_val('doxtr_headheight', 'headheight', '18pt')
        template_vars['doxtr_footheight'] = resolve_val('doxtr_footheight', 'footheight', '25pt')
        template_vars['extensions'] = getattr(config, 'extensions', [])

        footer_logo = resolve_val('doxtr_footer_logo', 'footer_logo', None)
        if footer_logo and isinstance(footer_logo, str):
            if footer_logo not in config.latex_additional_files: config.latex_additional_files.append(footer_logo)
            template_vars['doxtr_footer_logo'] = os.path.basename(footer_logo)
        else:
            template_vars['doxtr_footer_logo'] = None
        template_vars['doxtr_footer_logo_height'] = resolve_val('doxtr_footer_logo_height', 'footer_logo_height', '1.5em')

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
                clean_hex = draft_color_str.lstrip('#')
                if len(clean_hex) == 8:
                    draft_opacity = str(round(int(clean_hex[6:8], 16) / 255.0, 2))
                    draft_color_str = f"#{clean_hex[:6]}"
                elif len(clean_hex) == 4:
                    draft_opacity = str(round(int(clean_hex[3] * 2, 16) / 255.0, 2))
                    draft_color_str = f"#{clean_hex[:3]}"
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
        template_vars['doxtr_microtype_kerning'] = microtype.get('kerning', True)
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
                    clean_hex = color_str.lstrip('#')
                    if len(clean_hex) == 8:
                        opacity = str(round(int(clean_hex[6:8], 16) / 255.0, 2))
                        color_str = f"#{clean_hex[:6]}"
                    elif len(clean_hex) == 4:
                        opacity = str(round(int(clean_hex[3] * 2, 16) / 255.0, 2))
                        color_str = f"#{clean_hex[:3]}"
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
            template_vars[f'doxtr_{el}_color'] = safe_cmyk(c_val) if c_val else ""

        # --- HEADINGS ---
        global_align = headings.get('align', 'alternate')
        global_margin = headings.get('numbers_in_margin', True)
        global_margin_space = headings.get('margin_space', '1.5em')
        for el in ['chapter', 'section', 'subsection', 'subsubsection']:
            el_dict = headings.get(el, {})
            template_vars[f'doxtr_{el}_align'] = el_dict.get('align', global_align)
            template_vars[f'doxtr_{el}_number_margin'] = el_dict.get('number_margin', global_margin)
            template_vars[f'doxtr_{el}_number_line'] = el_dict.get('number_line', True if el == 'chapter' else False)
            template_vars[f'doxtr_{el}_line_height'] = el_dict.get('line_height', '10cm')
            template_vars[f'doxtr_{el}_margin_space'] = el_dict.get('margin_space', global_margin_space)
            template_vars[f'doxtr_{el}_font'] = el_dict.get('font', None)
            template_vars[f'doxtr_{el}_size'] = el_dict.get('size', None)
            
            hc = el_dict.get('color', None)
            template_vars[f'doxtr_{el}_color'] = safe_cmyk(hc) if hc else ""
            
            template_vars[f'doxtr_{el}_number_font'] = el_dict.get('number_font', None)
            template_vars[f'doxtr_{el}_number_size'] = el_dict.get('number_size', None)
            
            hnc = el_dict.get('number_color', None)
            template_vars[f'doxtr_{el}_number_color'] = safe_cmyk(hnc) if hnc else ""
            
            hlc = el_dict.get('line_color', None)
            template_vars[f'doxtr_{el}_line_color'] = safe_cmyk(hlc) if hlc else ""

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
        template_vars['doxtr_epigraph_color'] = safe_cmyk(ec) if ec else ""
        
        template_vars['doxtr_epigraph_author_font'] = epigraphs.get('author_font', None)
        template_vars['doxtr_epigraph_author_size'] = epigraphs.get('author_size', None)
        
        eac = epigraphs.get('author_color', None)
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
                if val and 'color' in prop: val = safe_cmyk(val)
                template_vars[f'doxtr_{level}_epigraph_{prop}'] = val

        # --- TEXT INHERITANCE LOGIC ---
        if resolve_val('doxtr_inherit_all', 'inherit_all', True):
            for hierarchy in [['part', 'chapter', 'section', 'subsection', 'subsubsection'], ['part_number', 'chapter_number', 'section_number', 'subsection_number', 'subsubsection_number'], ['chapter_line', 'section_line', 'subsection_line', 'subsubsection_line'], ['epigraph', 'part_epigraph', 'chapter_epigraph', 'section_epigraph', 'subsection_epigraph', 'subsubsection_epigraph'], ['epigraph_author', 'part_epigraph_author', 'chapter_epigraph_author', 'section_epigraph_author', 'subsection_epigraph_author', 'subsubsection_epigraph_author']]:
                for prop, is_enabled in [('font', resolve_val('doxtr_inherit_font', 'inherit_font', True)), ('color', resolve_val('doxtr_inherit_color', 'inherit_color', True)), ('size', resolve_val('doxtr_inherit_size', 'inherit_size', False))]:
                    if is_enabled:
                        current_val = template_vars.get(f'doxtr_{hierarchy[0]}_{prop}', None)
                        for i in range(1, len(hierarchy)):
                            key = f'doxtr_{hierarchy[i]}_{prop}'
                            if not template_vars.get(key): template_vars[key] = current_val
                            else: current_val = template_vars[key]
            # --- MARGIN SPACE INHERITANCE ---
            # Propagate margin_space down the heading hierarchy (chapter → section → subsection → subsubsection)
            margin_hierarchy = ['chapter', 'section', 'subsection', 'subsubsection']
            current_val = template_vars.get('doxtr_chapter_margin_space', None)
            for i in range(1, len(margin_hierarchy)):
                key = f'doxtr_{margin_hierarchy[i]}_margin_space'
                if not template_vars.get(key):
                    template_vars[key] = current_val
                else:
                    current_val = template_vars[key]

        for prop in ['font', 'color', 'size']:
            if not template_vars.get(f'doxtr_part_number_part_{prop}'): template_vars[f'doxtr_part_number_part_{prop}'] = template_vars.get(f'doxtr_part_number_{prop}')
            if not template_vars.get(f'doxtr_part_number_number_{prop}'): template_vars[f'doxtr_part_number_number_{prop}'] = template_vars.get(f'doxtr_part_number_{prop}')

        # --- ADMONITIONS ---
        admon_types = ['generic', 'admonition', 'note', 'warning', 'hint', 'danger', 'error', 'caution', 'tip', 'important', 'attention', 'seealso']
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
                if not val and val != False:
                    val = gen_dict.get(p)
                if not val and val != False:
                    val = CORE_CONFIG_MANIFEST.get('admonitions', {}).get('generic', {}).get(p) if t != 'generic' else CORE_CONFIG_MANIFEST.get('admonitions', {}).get('generic', {}).get(p)
                
                # Check root user config override layer
                if not val and val != False:
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
                if not val and val != False: val = gen_dict.get(p)
                if not val and val != False: val = needs.get(p)
                
                if not val and val != False:
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
        code_conf = code_blocks
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
        s_conf['title_background_color_cmyk'] = safe_cmyk(s_conf.get('title_background_color') or '#184878')
        s_conf['title_font_color_cmyk'] = safe_cmyk(s_conf.get('title_font_color') or '#FFFFFF')
        s_conf['title_icon_color_cmyk'] = safe_cmyk(s_conf.get('title_icon_color') or '#78D8F0')
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

    # Generate font pkg
    m_font = resolve_val('doxtr_main_font', 'main_font', 'Lato Light')
    m_font_opt = resolve_val('doxtr_main_font_options', 'main_font_options', '')
    s_font = resolve_val('doxtr_sans_font', 'sans_font', 'Exo 2')
    s_font_opt = resolve_val('doxtr_sans_font_options', 'sans_font_options', '')
    mo_font = resolve_val('doxtr_mono_font', 'mono_font', 'IosevkaTerm NF')
    mo_font_opt = resolve_val('doxtr_mono_font_options', 'mono_font_options', '')
    
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
    config.latex_elements.setdefault('fontpkg', dynamic_fontpkg)
    
    default_elements = {
        'fncychap': '',
        'tableofcontents': '\\tableofcontents',
        'papersize': 'a4paper',
        'pointsize': '11pt',
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
    
    if 'preamble' in config.latex_elements: 
        config.latex_elements['preamble'] += f"\n{my_preamble}\n{doxtr_rendered_code}\n{doxtr_rendered_sidebar}\n{doxtr_rendered_highlights}\n{lol_tracker}"
    else: 
        config.latex_elements['preamble'] = f"{my_preamble}\n{doxtr_rendered_code}\n{doxtr_rendered_sidebar}\n{doxtr_rendered_highlights}\n{lol_tracker}"

    if config.latex_logo and config.latex_logo not in config.latex_additional_files:
        config.latex_additional_files.append(config.latex_logo)
    
    config.latex_additional_files.extend([
        str(pkg_dir / "latex_styles" / "sphinxlatexstyleheadings.sty"),
        str(pkg_dir / "latex_styles" / "sphinxlatexstylepage.sty")
    ])

def build_finished(app, exception):
    if exception is not None or app.builder.name != 'latex': return
    xmp_content = f"\\Title{{{app.config.project}}}\n\\Author{{{app.config.author}}}\n"
    Path(app.builder.outdir).joinpath(f"{get_safe_filename(app.config.project)}.xmpdata").write_text(xmp_content, encoding='utf-8')

def setup(app):
    if not getattr(LaTeXTranslator, '_doxtr_patched', False):
        _orig_visit_admonition = LaTeXTranslator.visit_admonition
        def _custom_visit_admonition(self, node):
            _orig_visit_admonition(self, node)
            if self.body and '{note}' in self.body[-1]: self.body[-1] = self.body[-1].replace('{note}', '{admonition}')
        LaTeXTranslator.visit_admonition = _custom_visit_admonition
        LaTeXTranslator._doxtr_patched = True

    app.add_directive('stylebox', StyleBoxDirective)

    # Core Foundation Layers
    app.add_config_value('doxtr_theme_defaults', {}, 'env')
    app.add_config_value('doxtr_theme_style_paths', [], 'env')
    
    # Strict mode: raises ExtensionError on missing templates instead of using fallbacks
    app.add_config_value('doxtr_strict_mode', False, 'env')
    # Template cache: caches compiled Jinja2 templates to avoid redundant parsing
    app.add_config_value('doxtr_cache_templates', True, 'env')
    # Semantic color system palette
    app.add_config_value('doxtr_semantic_palette', {}, 'env')
    
    # Automatically register ALL globals so Sphinx never throws "Unknown Config" warnings!
    for key in DOXTR_GLOBALS.keys():
        app.add_config_value(f'doxtr_{key}', None, 'env')
        
    # Register the nested dictionary configurations
    for conf_dict in ['title_page', 'headings', 'parts', 'epigraphs', 'draft', 'microtype', 'containers', 'tables', 'figures', 'code', 'admonitions', 'needs', 'sidebar', 'highlights', 'toc', 'bibliography', 'index', 'glossary']:
        app.add_config_value(f'doxtr_{conf_dict}', {}, 'env')

    app.connect('config-inited', config_inited, priority=900)
    app.connect('build-finished', build_finished)
    app.connect('doctree-resolved', process_containers_ast, priority=998)
    app.connect('doctree-resolved', process_sidebar_ast, priority=994)
    app.connect('doctree-resolved', process_highlights_ast, priority=993)
    app.connect('doctree-resolved', process_tables_ast, priority=996) 
    app.connect('doctree-resolved', process_codeblocks_ast, priority=995)
    app.connect('doctree-resolved', process_epigraph_ast, priority=997)
    app.connect('doctree-resolved', process_needs_ast, priority=999)
    app.connect('doctree-resolved', _dispatch_custom_ast_processors, priority=992)
    
    return {'version': __version__, 'parallel_read_safe': True, 'parallel_write_safe': False}