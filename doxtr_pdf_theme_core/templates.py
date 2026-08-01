"""Template resolution and rendering engine for LaTeX style files.

This module implements the multi-tier template resolution strategy that allows
theme authors to override any .tex_t template file at multiple levels:
1. Custom folder (if doxtr_<type>_style_path is set)
2. User project's latex_styles/<type>/ folder
3. User project root for .tex_t files
4. Theme's doxtr_theme_style_paths
5. Core fallback (doxtr_pdf_theme_core/latex_styles/<type>/)
6. Absolute fallback (string from core_fallbacks.py)
"""
import re
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

from jinja2 import Environment
from sphinx.util import logging
from sphinx.errors import ExtensionError

from .core_fallbacks import (
    DEFAULT_TITLE_STYLES, DEFAULT_ADMONITION_STYLE, DEFAULT_NEED_STYLE,
    DEFAULT_CONTAINER_STYLE, DEFAULT_TABLE_STYLE, DEFAULT_FIGURE_STYLE,
    DEFAULT_CODE_STYLE, DEFAULT_SIDEBAR_STYLE, DEFAULT_HIGHLIGHTS_STYLE
)

__all__ = [
    'LATEX_STYLES_DIR',
    'DEFAULT_STYLE_NAME',
    'CLASSIC_STYLE_NAME',
    'GENERIC_TYPE_NAME',
    'STYLE_TYPES',
    'STYLE_FALLBACKS',
    'get_template_cache',
    'clear_template_cache',
    'get_template',
    'resolve_template',
    'render_template',
    'resolve_and_render_template',
]

logger = logging.getLogger(__name__)

# --- CONSTANTS ---
# Canonical directory and style names used throughout the template resolution engine.
# Centralizes magic strings to prevent typos and ease future refactoring.
LATEX_STYLES_DIR = 'latex_styles'
DEFAULT_STYLE_NAME = 'default'
CLASSIC_STYLE_NAME = 'classic'
GENERIC_TYPE_NAME = 'generic'
GENERIC_TYPE_NAME = 'generic'

# Mapping from style type to the subdirectory name in latex_styles/
STYLE_TYPES: Dict[str, str] = {
    'container_title': 'container_title_style',
    'container': 'container',
    'admonition': 'admonition',
    'need': 'need',
    'title_page': 'title_page',
    'table': 'table',
    'figure': 'figure',
    'code': 'code',
    'sidebar': 'sidebar',
    'highlights': 'highlights',
}

# Mapping from style type to the corresponding absolute fallback constant.
# These are used as last-resort fallbacks when no .tex_t file can be found.
STYLE_FALLBACKS: Dict[str, Callable[[str], str]] = {
    'container_title': lambda name: DEFAULT_TITLE_STYLES.get(name, DEFAULT_TITLE_STYLES[CLASSIC_STYLE_NAME]),
    'container': lambda _: DEFAULT_CONTAINER_STYLE,
    'admonition': lambda _: DEFAULT_ADMONITION_STYLE,
    'need': lambda _: DEFAULT_NEED_STYLE,
    'title_page': lambda _: '',
    'table': lambda _: DEFAULT_TABLE_STYLE,
    'figure': lambda _: DEFAULT_FIGURE_STYLE,
    'code': lambda _: DEFAULT_CODE_STYLE,
    'sidebar': lambda _: DEFAULT_SIDEBAR_STYLE,
    'highlights': lambda _: DEFAULT_HIGHLIGHTS_STYLE,
}

# --- TEMPLATE CACHE ---
# Caches compiled Jinja2 template objects to avoid redundant parsing.
# Keyed by template content string. Enabled via doxtr_cache_templates config.
_template_cache: Dict[str, Any] = {}


def get_template_cache() -> Dict[str, Any]:
    """Get the global template cache dictionary.

    Returns:
        The module-level template cache dict.
    """
    return _template_cache


def clear_template_cache() -> None:
    """Clear the global template cache.

    Should be called at the start of each build to avoid stale templates
    when using sphinx-autobuild or similar tools.
    """
    _template_cache.clear()


def get_template(env: Environment, content: str, use_cache: bool = True) -> Any:
    """Get a compiled Jinja2 template, optionally from cache.

    Args:
        env: The Jinja2 Environment instance.
        content: The raw template string.
        use_cache: Whether to use the template cache.

    Returns:
        A compiled Jinja2 Template object.
    """
    if not use_cache:
        return env.from_string(content)
    if content not in _template_cache:
        _template_cache[content] = env.from_string(content)
    return _template_cache[content]


def resolve_template(
    app,
    env: Environment,
    style_type: str,
    style_name: str,
    theme_style_paths: List[str],
    resolve_val_fn: Callable,
    strict_mode: bool = False,
    use_cache: bool = True,
) -> Optional[str]:
    """Resolve a .tex_t template file through the hierarchical search path.

    Implements the multi-tier template resolution strategy:
    1. Custom folder (if doxtr_<type>_style_path is set)
    2. User project's latex_styles/<type>/ folder
    3. User project root for .tex_t files
    4. Theme's doxtr_theme_style_paths
    5. Core fallback (doxtr_pdf_theme_core/latex_styles/<type>/)
    6. Absolute fallback (string from core_fallbacks.py)

    Args:
        app: The Sphinx application object.
        env: The Jinja2 Environment for template compilation.
        style_type: The type of style (key in STYLE_TYPES, e.g. 'admonition').
        style_name: The specific style name (e.g. 'default', 'note').
        theme_style_paths: List of theme-provided style directories.
        resolve_val_fn: Function to resolve config values (3-tier).
        strict_mode: If True, raise ExtensionError on missing templates.
        use_cache: Whether to use the template cache.

    Returns:
        The raw template content string, or None if not found (with fallback applied).

    Raises:
        ExtensionError: If strict_mode is True and the template cannot be found.
    """
    pkg_dir = Path(__file__).parent.resolve()
    style_dir = STYLE_TYPES.get(style_type, style_type)
    config_path_key = f'doxtr_{style_dir}_path'
    theme_key = f'{style_dir}_path'

    paths_to_check: List[Path] = []

    # 1. Custom folder from config
    custom_folder = resolve_val_fn(config_path_key, theme_key, '')
    if custom_folder:
        paths_to_check.extend([
            Path(app.confdir) / custom_folder / f"{style_name}.tex_t",
            Path(app.srcdir) / custom_folder / f"{style_name}.tex_t",
        ])

    # 2. User project's latex_styles/<type>/ folder
    paths_to_check.extend([
        Path(app.confdir) / LATEX_STYLES_DIR / style_dir / f"{style_name}.tex_t",
        Path(app.srcdir) / LATEX_STYLES_DIR / style_dir / f"{style_name}.tex_t",
        Path(app.confdir) / f"{style_name}.tex_t",
        Path(app.srcdir) / f"{style_name}.tex_t",
    ])

    # 3. Theme style paths
    for t_path in theme_style_paths:
        paths_to_check.append(Path(t_path) / style_dir / f"{style_name}.tex_t")

    # 4. Core fallback
    paths_to_check.append(pkg_dir / LATEX_STYLES_DIR / style_dir / f"{style_name}.tex_t")

    # Search for the file
    raw_content = None
    for p in paths_to_check:
        if p.exists():
            raw_content = p.read_text(encoding='utf-8')
            break

    if raw_content is not None:
        return raw_content

    # 5. Try the default fallback file name
    fallback_name = CLASSIC_STYLE_NAME if style_type == 'container_title' else DEFAULT_STYLE_NAME
    default_content = None

    for t_path in theme_style_paths:
        def_path = Path(t_path) / style_dir / f"{fallback_name}.tex_t"
        if def_path.exists():
            default_content = def_path.read_text(encoding='utf-8')
            break

    if default_content is None:
        core_def_path = pkg_dir / LATEX_STYLES_DIR / style_dir / f"{fallback_name}.tex_t"
        if core_def_path.exists():
            default_content = core_def_path.read_text(encoding='utf-8')

    if default_content:
        logger.warning(
            f"[Doxtr Core] {style_type} style '{style_name}' not found. "
            f"Falling back to {fallback_name}.tex_t."
        )
        return default_content

    # 6. Absolute fallback from core_fallbacks.py
    if strict_mode:
        raise ExtensionError(
            f"[Doxtr Core] {style_type} style '{style_name}' not found and "
            f"strict mode is enabled. No fallback available."
        )

    fallback_fn = STYLE_FALLBACKS.get(style_type)
    if fallback_fn:
        logger.warning(
            f"[Doxtr Core] {style_type} style '{style_name}' not found. "
            f"Injecting Core Absolute Fallback."
        )
        return fallback_fn(style_name)

    return ''


def render_template(
    env: Environment,
    raw_content: str,
    template_vars: dict,
    use_cache: bool = True,
    strip_comments: bool = False,
) -> str:
    """Render a Jinja2 template string with the given variables.

    Args:
        env: The Jinja2 Environment instance.
        raw_content: The raw template string.
        template_vars: Variables to pass to the template.
        use_cache: Whether to use template caching.
        strip_comments: If True, strip LaTeX comments and join lines.

    Returns:
        The rendered template output.
    """
    if not raw_content:
        return ''
    tmpl = get_template(env, raw_content, use_cache)
    rendered = tmpl.render(**template_vars)
    if strip_comments:
        clean_lines = [
            re.sub(r'(?<!\\)%.*', '', line).strip()
            for line in rendered.splitlines()
            if re.sub(r'(?<!\\)%.*', '', line).strip()
        ]
        return ' '.join(clean_lines)
    return '\n'.join(line for line in rendered.splitlines() if line.strip())


def resolve_and_render_template(
    app,
    env: Environment,
    template_vars: dict,
    style_type: str,
    style_name: str,
    theme_style_paths: List[str],
    resolve_val_fn: Callable,
    strict_mode: bool = False,
    use_cache: bool = True,
    strip_comments: bool = False,
    extra_ctx: Optional[dict] = None,
) -> str:
    """Resolve and render a template in one step.

    Combines resolve_template() and render_template() for the common case.

    Args:
        app: The Sphinx application object.
        env: The Jinja2 Environment instance.
        template_vars: Base template variables.
        style_type: The type of style (key in STYLE_TYPES).
        style_name: The specific style name.
        theme_style_paths: List of theme-provided style directories.
        resolve_val_fn: Function to resolve config values.
        strict_mode: If True, raise ExtensionError on missing templates.
        use_cache: Whether to use template caching.
        strip_comments: If True, strip LaTeX comments from output.
        extra_ctx: Extra context variables merged into template_vars for rendering.

    Returns:
        The rendered template output string.
    """
    raw_content = resolve_template(
        app, env, style_type, style_name,
        theme_style_paths, resolve_val_fn, strict_mode, use_cache,
    )
    render_ctx = template_vars
    if extra_ctx:
        render_ctx = template_vars.copy()
        render_ctx.update(extra_ctx)
    return render_template(env, raw_content, render_ctx, use_cache, strip_comments)
