"""Configuration validation and merging utilities.

This module provides the three-tier merge architecture for combining
core defaults, theme overrides, and user configuration. It also provides
validation to warn users about unknown configuration keys.
"""
import copy
import time
from contextlib import contextmanager
from typing import Optional, Dict, Set, Any

from sphinx.util import logging

from .utils import deep_update
from .core_config import CORE_CONFIG_MANIFEST, DOXTR_GLOBALS

__all__ = [
    'VALID_KEYS',
    'CORE_ADMONITION_TYPES',
    'VALID_CONTAINER_KEYS',
    'VALID_ADMONITION_KEYS',
    'VALID_CODE_KEYS',
    'VALID_NEEDS_KEYS',
    'validate_config_keys',
    'validate_typed_section',
    'validate_container_mapping',
    'make_resolve_val_fn',
    'make_merge_section_fn',
    'warn_deprecated',
    'debug_timer',
]

logger = logging.getLogger(__name__)

# --- CORE ADMONITION TYPES ---
# The canonical list of admonition types supported by the theme.
# Used in config_inited() to iterate over all admonition configurations.
CORE_ADMONITION_TYPES = [
    'generic', 'admonition', 'note', 'warning', 'hint', 'danger',
    'error', 'caution', 'tip', 'important', 'attention', 'seealso',
]

# --- CONFIGURATION VALIDATION ---
# Valid keys for each config section, used to warn on typos / unknown keys.
VALID_KEYS: Dict[str, Set[str]] = {
    'title_page': {
        'template', 'page_color', 'background_image', 'background_image_mode',
        'background_image_align', 'background_image_keepaspectratio', 'color_opacity',
        'subtitle', 'top_line',
        'title_font', 'title_size', 'title_color',
        'subtitle_font', 'subtitle_size', 'subtitle_color',
        'author_font', 'author_size', 'author_color',
        'date_font', 'date_size', 'date_color',
        'release_version_font', 'release_version_size', 'release_version_color',
    },
    'draft': {
        'text', 'date_format', 'timezone', 'color', 'font_size', 'font',
    },
    'epigraphs': {
        'width', 'format', 'align_box', 'align_text', 'align_author',
        'font', 'size', 'color', 'author_font', 'author_size', 'author_color',
        'part', 'chapter', 'section', 'subsection', 'subsubsection',
    },
    'headings': {
        'align', 'numbers_in_margin', 'margin_space',
        'chapter', 'section', 'subsection', 'subsubsection',
    },
    'microtype': {
        'enabled', 'protrusion', 'expansion', 'kerning', 'stretch', 'shrink',
    },
    'parts': {
        'font', 'size', 'color',
        'part_number_font', 'part_number_size', 'part_number_color',
        'part_number_part_font', 'part_number_part_size', 'part_number_part_color',
        'part_number_number_font', 'part_number_number_size', 'part_number_number_color',
    },
    'sidebar': {
        'style', 'width', 'float_position', 'border_radius', 'border_width', 'border_color',
        'title_icon', 'title_font', 'title_font_size', 'title_background_color', 'title_font_color', 'title_icon_color',
        'subtitle_font', 'subtitle_font_size', 'subtitle_font_color',
        'content_font', 'content_font_size', 'content_font_color', 'content_background_color',
        'before_skip', 'after_skip',
    },
    'highlights': {
        'style', 'title_text', 'title_icon', 'title_font', 'title_font_size', 'title_font_color',
        'border_color', 'border_width',
        'content_font', 'content_font_size', 'content_font_color', 'content_background_color',
        'before_skip', 'after_skip',
    },
    'tables': {
        'style', 'title_style', 'caption_position', 'caption_top_offset',
        'title_padding', 'title_text_offset', 'title_fade_dots',
        'title_background_fade_mask_color', 'title_background_fade_length', 'title_background_fade_shape',
        'header_background_color', 'header_font_color', 'header_font', 'header_font_size',
        'row_color_odd', 'row_color_even',
        'title_background_color', 'title_font_color', 'title_font', 'title_font_size',
    },
    'figures': {
        'style', 'caption_background_color', 'caption_font_color',
        'caption_font', 'caption_font_size', 'caption_padding', 'caption_align',
    },
}

# --- Valid keys for typed sections (Task 2.3) ---
# These validate per-entry configs within containers, admonitions, code, etc.

VALID_CONTAINER_KEYS: set = {
    'title', 'title_raw', 'style', 'title_style', 'container_frame',
    'match_text_width', 'title_icon', 'title_font', 'title_font_size',
    'title_color', 'title_font_color', 'title_icon_color', 'title_icon_font_size',
    'content_font', 'content_font_size', 'content_font_color',
    'content_background_color', 'before_skip', 'after_skip',
    # participant-specific
    'frame_width', 'frame_arc', 'title_position', 'title_xshift', 'title_max_width',
    # folder-specific
    'border_width', 'show_shadow', 'shadow_color', 'title_background_color',
}

VALID_ADMONITION_KEYS: set = {
    'style', 'title_icon', 'title_icon_padding', 'title_decoration_spacing',
    'title_background_color', 'title_icon_box_background_color',
    'title_font_color', 'title_icon_color', 'title_font_size', 'title_font',
    'content_background_color', 'content_background_color_nested',
    'content_font_color', 'content_font_size', 'content_font',
    'before_skip', 'after_skip', 'title_icon_size',
}

VALID_CODE_KEYS: set = {
    'style', 'border_width', 'show_mac_dots', 'language_label', 'icon',
    'icon_position', 'icon_color', 'icon_size',
    'title_background_color', 'title_font_color', 'title_font_size', 'title_font',
    'content_background_color', 'content_font_color', 'content_font_size',
    'content_font', 'border_color',
}

VALID_NEEDS_KEYS: set = {
    'style', 'segmentation_style', 'title_vertical_position',
    'title_icon', 'title_icon_size', 'title_icon_color', 'title_icon_raise', 'title_icon_raise_offset',
    'title_background_color', 'title_font_color', 'title_color',
    'title_font_size', 'title_font',
    'segmentation_color',
    'metadata_background_color', 'metadata_key_color', 'metadata_key_font_size',
    'metadata_key_font', 'metadata_font_color', 'metadata_font_size', 'metadata_font',
    'content_background_color', 'content_font_color', 'content_font_size', 'content_font',
    'before_skip', 'after_skip',
}


def validate_container_mapping(mapping: dict, containers_conf: dict) -> None:
    """Warn about container mappings whose targets are not defined in doxtr_containers.

    Called during ``config_inited()`` so misconfigurations are surfaced at
    build time rather than silently falling back to 'default' at render time.

    Args:
        mapping: The ``doxtr_container_mapping`` dict from ``conf.py``.
        containers_conf: The *user-supplied* ``doxtr_containers`` dict
            (pre-merge is fine here — we just want early feedback).
    """
    for source, target in mapping.items():
        if target not in containers_conf:
            logger.warning(
                f"[Doxtr Core] Container mapping '{source}' -> '{target}': "
                f"target style '{target}' is not defined in doxtr_containers. "
                f"Will fall back to 'default' at render time."
            )


def validate_typed_section(
    section_dict: dict,
    section_name: str,
    valid_keys: set,
) -> None:
    """Validate each named entry in a typed section (containers, admonitions, etc.).

    This function checks each entry in a section like 'containers' or 'admonitions'
    and warns about any unknown keys. This catches typos that would otherwise be
    silently ignored.

    Args:
        section_dict: The merged config dictionary for the section.
        section_name: The name of the section (e.g., 'containers').
        valid_keys: Set of valid key names for entries in this section.
    """
    for entry_name, entry_conf in section_dict.items():
        if not isinstance(entry_conf, dict):
            continue
        unknown = set(entry_conf.keys()) - valid_keys
        if unknown:
            logger.warning(
                f"[Doxtr Core] Unknown keys in '{section_name}.{entry_name}': "
                f"{sorted(unknown)}. These will be ignored."
            )


def validate_config_keys(config_dict: dict, section_name: str) -> None:
    """Warn about unknown keys in a configuration section.

    Only validates sections that have a known schema in VALID_KEYS.
    Sub-dictionaries (e.g., per-type overrides) are skipped since they
    use dynamic keys (container names, admonition types, etc.).

    Args:
        config_dict: The merged config dictionary for a section.
        section_name: The name of the section (e.g., 'title_page').
    """
    valid = VALID_KEYS.get(section_name)
    if valid is None:
        return  # No schema defined for this section — skip validation
    unknown = set(config_dict.keys()) - valid
    # Filter out integer keys (used for per-part overrides) and sub-dicts
    unknown = {k for k in unknown if not isinstance(k, int) and not isinstance(config_dict.get(k), dict)}
    if unknown:
        logger.warning(
            f"[Doxtr Core] Unknown keys in '{section_name}': {sorted(unknown)}. "
            f"These will be ignored. Valid keys: {sorted(valid)}"
        )


def make_resolve_val_fn(config, theme_defaults: dict):
    """Create a resolve_val function bound to specific config and theme_defaults.

    The returned function implements the three-tier resolution:
    1. User config (Sphinx conf.py)
    2. Theme defaults (doxtr_theme_defaults)
    3. Core config manifest or globals

    Args:
        config: The Sphinx config object.
        theme_defaults: The theme-level defaults dictionary.

    Returns:
        A resolve_val function with signature:
        resolve_val(conf_attr, theme_key, fallback=None, section=None) -> Any
    """
    def resolve_val(conf_attr: str, theme_key: str, fallback: Any = None, section: Optional[str] = None) -> Any:
        """Resolve a config value through the three-tier hierarchy.

        Args:
            conf_attr: The Sphinx config attribute name (e.g., 'doxtr_show_release').
            theme_key: The key to look up in theme_defaults.
            fallback: Default value if not found anywhere.
            section: Optional section name for CORE_CONFIG_MANIFEST lookup.

        Returns:
            The resolved value from the first tier where it's found.
        """
        val = getattr(config, conf_attr, None)
        if val is not None:
            return val
        if theme_key in theme_defaults:
            return theme_defaults[theme_key]
        if section:
            section_conf = CORE_CONFIG_MANIFEST.get(section, {})
            if isinstance(section_conf, dict):
                val = section_conf.get(theme_key, fallback)
            else:
                val = section_conf if section_conf is not None else fallback
            if val is not None:
                return val
        return DOXTR_GLOBALS.get(theme_key, fallback)

    return resolve_val


def make_merge_section_fn(config, theme_defaults: dict):
    """Create a merge_section function bound to specific config and theme_defaults.

    The returned function implements the three-tier merge:
    core → theme → user for a config section.

    Args:
        config: The Sphinx config object.
        theme_defaults: The theme-level defaults dictionary.

    Returns:
        A merge_section function with signature:
        merge_section(name, config_attr=None) -> dict
    """
    def merge_section(name: str, config_attr: Optional[str] = None) -> dict:
        """Three-tier merge: core → theme → user for a config section.

        Args:
            name: The section name in CORE_CONFIG_MANIFEST.
            config_attr: Optional override for the Sphinx config attribute name.
                        Defaults to 'doxtr_{name}'.

        Returns:
            The merged configuration dictionary.
        """
        attr = config_attr or f'doxtr_{name}'
        section_core = CORE_CONFIG_MANIFEST.get(name, {})
        section_theme = theme_defaults.get(name, {})
        section_user = getattr(config, attr, {})
        return deep_update(deep_update(copy.deepcopy(section_core), section_theme), section_user)

    return merge_section


def warn_deprecated(
    config,
    old_key: str,
    new_key: str,
    section: str,
    removed_in: str,
) -> None:
    """Emit a deprecation warning if an old config key is present.

    This function is part of the versioned deprecation warning infrastructure.
    Call it in config_inited() for any config key that has been renamed or
    will be removed in a future version.

    Args:
        config: The Sphinx config object.
        old_key: The deprecated config attribute name (e.g., 'doxtr_old_key').
        new_key: The replacement key (e.g., 'doxtr_new_key').
        section: Human-readable section for context (e.g., 'containers').
        removed_in: Version string when the key will be removed (e.g., '0.3.0').

    Example:
        >>> warn_deprecated(config, 'doxtr_old_setting', 'doxtr_new_setting',
        ...                 'global settings', '0.3.0')
        # If config.doxtr_old_setting is set, emits:
        # WARNING: 'doxtr_old_setting' in global settings is deprecated...
    """
    if getattr(config, old_key, None) is not None:
        logger.warning(
            f"[Doxtr Core] '{old_key}' in {section} is deprecated and will be "
            f"removed in v{removed_in}. Use '{new_key}' instead."
        )


@contextmanager
def debug_timer(label: str, enabled: bool = False):
    """Context manager for debug timing of config processing stages.

    Use this to measure the time spent in critical sections of config_inited()
    or template rendering. Times are only logged when enabled is True.

    Args:
        label: Human-readable label for the timing output.
        enabled: Whether to actually time and log (default: False).

    Example:
        >>> debug_enabled = getattr(config, 'doxtr_debug_timing', False)
        >>> with debug_timer('Color resolution pass 1', debug_enabled):
        ...     resolve_all_colors(...)
        # If enabled: [Doxtr Timing] Color resolution pass 1: 0.042s

    Yields:
        None.
    """
    if not enabled:
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"[Doxtr Timing] {label}: {elapsed:.3f}s")
