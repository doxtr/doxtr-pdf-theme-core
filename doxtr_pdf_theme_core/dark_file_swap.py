"""Dark file swap mechanism for source-read interception.

This module intercepts RST/MyST source text via Sphinx's ``source-read`` event
(and ``include-read`` for Sphinx >= 7.2.4) to rewrite directive file arguments
to their ``_dark`` variants when dark mode is active with the ``invert`` strategy.

Extensions like PlantUML and Mermaid consume file content at parse time, so the
existing doctree-resolved swap (``process_dark_images_ast``) fires too late.
This module rewrites paths in the source text *before* parsing, giving those
extensions the dark variant transparently.

Architecture::

    RST/MyST source text
        ↓ source-read hook (priority 500)
    Rewrite directive file arguments to _dark variants
        ↓ Sphinx parsing (directive run() methods consume files)
    Extension nodes already reference _dark source files
        ↓ doctree-resolved (existing, priority 991)
    process_dark_images_ast handles .. image:: / .. figure:: (unchanged)

Public API for child themes::

    from doxtr_pdf_theme_core import register_dark_swap_directive

    register_dark_swap_directive('my-diagram', file_options=['source'])

Known Limitations:

- **Context-free option matching**: The regex scanner cannot distinguish real
  directives from directive-like text inside ``.. code-block::``, ``::`` literal
  blocks, ``.. parsed-literal::`` content, or RST comments. The file-existence
  check (``<stem>_dark<ext>`` must exist on disk) makes real-world false positives
  extremely unlikely.
- **i18n interaction**: PlantUML's ``i18n.search_image_for_language()`` may modify
  paths after source-read. After rewriting ``arch.puml`` → ``arch_dark.puml``,
  i18n would look for ``arch_dark.en.puml``. PlantUML falls back gracefully.
- **MyST YAML-style options**: MyST directives with YAML front-matter options
  (e.g. ``file: path.puml`` without the colon-prefix RST syntax) are NOT matched.
  Only RST-style ``:option: value`` and argument-based references are supported.
- **Substitution definitions**: RST substitution definitions like
  ``.. |arch| uml:: diagrams/arch.puml`` use a different syntax and are not matched.
"""
import fnmatch
import os
import re
from typing import List, Optional

from sphinx.util import logging

from .utils import to_bool, deep_update

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    'register_dark_swap_directive',
    'swap_dark_sources',
    'swap_dark_includes',
    'DARK_FILE_SWAP_DIRECTIVES_DEFAULT',
    'DARK_FILE_SWAP_EXTENSIONS_DEFAULT',
]

# ---------------------------------------------------------------------------
# Default configuration constants
# ---------------------------------------------------------------------------

# Default directives to scan for file references.
# Dict format: keys are directive names; values are dicts with an 'options' key
# listing the :option: names that hold file paths. An empty 'options' list means
# only the directive argument (the text after `::`) is scanned for file paths.
DARK_FILE_SWAP_DIRECTIVES_DEFAULT = {
    'uml':            {'options': ['file']},      # sphinxcontrib-plantuml
    'mermaid':        {'options': ['file']},      # sphinxcontrib-mermaid
    'drawio':         {'options': []},            # sphinxcontrib-drawio (belt-and-suspenders)
    'drawio-figure':  {'options': []},            # sphinxcontrib-drawio
    'drawio-image':   {'options': []},            # sphinxcontrib-drawio
    'include':        {'options': []},            # docutils built-in
    'literalinclude': {'options': []},            # Sphinx built-in
    'raw':            {'options': ['file']},      # docutils built-in
}

# File extensions considered for dark variant lookup.
# These cover the most common diagram/include formats used with Sphinx extensions.
# Users can override entirely via doxtr_dark_file_swap_extensions or append via
# doxtr_dark_file_swap_extra_extensions without re-listing the defaults.
DARK_FILE_SWAP_EXTENSIONS_DEFAULT = [
    '.puml', '.plantuml', '.iuml',   # PlantUML
    '.mmd', '.mermaid',              # Mermaid
    '.drawio',                       # draw.io
    '.tex', '.sty',                  # LaTeX fragments
    '.rst', '.txt',                  # reStructuredText includes
    '.svg', '.png', '.jpg', '.pdf',  # Direct assets (catch-all)
]

# Directives excluded from source-read scanning (hardcoded).
# These are handled more precisely at doctree level by process_dark_images_ast
# which has access to Sphinx's image infrastructure (env.images, candidate
# tracking, class-based opt-out). Source-read cannot interact with that
# infrastructure since no nodes exist yet.
_EXCLUDED_DIRECTIVES = frozenset({'image', 'figure'})

# The _dark suffix is hardcoded across the codebase and not configurable.
_DARK_SUFFIX = '_dark'

# ---------------------------------------------------------------------------
# Public API registry — theme authors call register_dark_swap_directive()
# ---------------------------------------------------------------------------

# Module-level registry for directives added via the public API.
# Each entry is a dict: {'name': str, 'options': list[str]}
_custom_dark_swap_directives: list = []


def _reset_dark_swap_registry() -> None:
    """Clear all API-registered dark swap directives.

    Used in tests for state isolation between test cases.
    Not part of the public API — prefixed with underscore.
    """
    _custom_dark_swap_directives.clear()


def register_dark_swap_directive(name: str, file_options: Optional[List[str]] = None) -> None:
    """Register a custom directive for dark file swapping.

    Theme authors call this from their extension's ``setup()`` function to
    add directives that reference external files and should participate in
    dark variant swapping.

    The registered directive will be merged with the config-based
    ``doxtr_dark_file_swap_directives`` at event time. API registrations
    take precedence over config-based entries with the same name.

    Args:
        name: RST/MyST directive name (e.g. ``'my-diagram'``).
        file_options: Optional list of option names that hold file paths
                      (e.g. ``['source', 'file']``). If ``None`` or empty,
                      only the directive argument is scanned.

    Raises:
        TypeError: If *name* is not a string.
        ValueError: If *name* is empty or matches an excluded directive.

    Note:
        Must be called from an extension's ``setup()`` function before
        ``source-read`` fires. Calls after Sphinx begins reading documents
        will still work (the registry is checked at event time) but cannot
        affect documents already processed.

    Example::

        from doxtr_pdf_theme_core import register_dark_swap_directive

        # Register a directive that takes a file as its argument
        register_dark_swap_directive('my-diagram')

        # Register a directive with a :source: option
        register_dark_swap_directive('my-diagram', file_options=['source'])
    """
    if not isinstance(name, str):
        raise TypeError(
            f"register_dark_swap_directive: name must be a string, "
            f"got {type(name).__name__}"
        )
    if not name.strip():
        raise ValueError("register_dark_swap_directive: name must not be empty")
    if name in _EXCLUDED_DIRECTIVES:
        raise ValueError(
            f"register_dark_swap_directive: '{name}' is excluded from "
            f"source-read swapping (handled by process_dark_images_ast)"
        )
    _custom_dark_swap_directives.append({
        'name': name,
        'options': list(file_options) if file_options else [],
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_effective_directives(config) -> dict:
    """Merge config-based and API-registered directives into one dict.

    Three-tier merge order (same as the rest of the system):
    1. Core defaults (DARK_FILE_SWAP_DIRECTIVES_DEFAULT)
    2. Theme/user config (doxtr_dark_file_swap_directives)
    3. API registrations (register_dark_swap_directive calls)

    Returns:
        Dict of directive_name -> {'options': [...]}
    """
    # Start from core defaults
    result = dict(DARK_FILE_SWAP_DIRECTIVES_DEFAULT)
    # Merge user/theme config overrides
    user_directives = getattr(config, 'doxtr_dark_file_swap_directives', {})
    if user_directives:
        deep_update(result, user_directives)
    # Merge API registrations (highest priority)
    for entry in _custom_dark_swap_directives:
        result[entry['name']] = {'options': entry['options']}
    # Remove excluded directives (safety — never scan image/figure)
    for excl in _EXCLUDED_DIRECTIVES:
        result.pop(excl, None)
    return result


def _get_effective_extensions(config) -> set:
    """Return the set of file extensions to consider for swapping.

    If the user provides ``doxtr_dark_file_swap_extensions``, that replaces
    the defaults entirely. In addition, ``doxtr_dark_file_swap_extra_extensions``
    is always appended (additive), allowing users to add extensions like
    ``.wsd`` without re-listing all 14 defaults.
    """
    extensions = getattr(config, 'doxtr_dark_file_swap_extensions', None)
    if extensions is None:
        extensions = list(DARK_FILE_SWAP_EXTENSIONS_DEFAULT)
    else:
        extensions = list(extensions)
    # Merge additive extra extensions
    extra = getattr(config, 'doxtr_dark_file_swap_extra_extensions', None) or []
    extensions.extend(extra)
    return set(ext.lower() for ext in extensions)


def _get_exclude_patterns(config) -> list:
    """Collect exclude patterns from both dedicated and shared config."""
    patterns = list(getattr(config, 'doxtr_dark_file_swap_exclude', []) or [])
    # Also consult the shared image exclude patterns for consistency
    shared = getattr(config, 'doxtr_image_exclude_patterns', []) or []
    patterns.extend(shared)
    return patterns


def _is_excluded(filepath: str, exclude_patterns: list) -> bool:
    """Check if a file path matches any exclude glob pattern."""
    basename = os.path.basename(filepath)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(filepath, pattern):
            return True
    return False


def _is_url(path: str) -> bool:
    """Return True if path looks like a URL."""
    return '://' in path or path.startswith('data:')


def _build_rst_argument_pattern(directive_names: list) -> re.Pattern:
    """Build regex for RST directive arguments.

    Matches::

        .. uml:: path/to/file.puml
        .. mermaid:: diagrams/flow.mmd

    With arbitrary leading indentation (for nested directives).
    """
    # Escape directive names for regex safety (handles hyphens, dots, etc.)
    escaped = [re.escape(name) for name in directive_names]
    names_alternation = '|'.join(escaped)
    # Pattern: optional whitespace, .., whitespace, directive::, whitespace, path
    # The path is everything after :: and whitespace until end of line.
    return re.compile(
        r'^([ \t]*\.\.\s+)(' + names_alternation + r')(::[ \t]+)(\S.*?)[ \t]*$',
        re.MULTILINE
    )


def _build_rst_option_pattern(option_names: list) -> re.Pattern:
    """Build regex for RST directive options containing file paths.

    Matches::

        :file: path/to/file.puml
        :source: diagrams/architecture.puml

    With arbitrary leading indentation (including zero for MyST compatibility).
    """
    escaped = [re.escape(name) for name in option_names]
    names_alternation = '|'.join(escaped)
    # Use [ \t]* (not +) so MyST options with no leading indent also match.
    return re.compile(
        r'^([ \t]*:)(' + names_alternation + r')(:[ \t]+)(\S.*?)[ \t]*$',
        re.MULTILINE
    )


def _build_myst_argument_pattern(directive_names: list) -> re.Pattern:
    """Build regex for MyST directive arguments.

    Matches::

        ```{uml} path/to/file.puml
        ````{mermaid} diagrams/flow.mmd

    With arbitrary leading indentation and any number of backticks (>=3).
    """
    escaped = [re.escape(name) for name in directive_names]
    names_alternation = '|'.join(escaped)
    # Groups: (1) prefix incl backticks+'{', (2) directive name,
    #         (3) '}' + space, (4) file path
    return re.compile(
        r'^([ \t]*`{3,}\{)(' + names_alternation + r')(\}[ \t]+)(\S.*?)[ \t]*$',
        re.MULTILINE
    )


def _resolve_dark_variant(filepath: str, srcdir: str, docdir: str,
                          valid_extensions: set) -> str:
    """Check if a _dark variant exists for the given file path.

    Args:
        filepath: The file path as written in the directive (relative).
        srcdir: Sphinx source directory (absolute).
        docdir: Directory of the current document (absolute).
        valid_extensions: Set of file extensions to consider.

    Returns:
        The dark variant path (relative, same form as input) if it exists,
        or empty string if no dark variant is available.
    """
    # Check extension
    _, ext = os.path.splitext(filepath)
    if ext.lower() not in valid_extensions:
        return ''

    # Resolve the absolute path — try relative to docdir first, then srcdir
    if os.path.isabs(filepath):
        return ''  # Absolute paths are not swappable

    # Build candidate absolute path
    abs_path = os.path.normpath(os.path.join(docdir, filepath))
    if not os.path.isfile(abs_path):
        # Try relative to srcdir (some directives resolve from srcdir)
        abs_path = os.path.normpath(os.path.join(srcdir, filepath))
        if not os.path.isfile(abs_path):
            # Original file doesn't exist — can't determine dark variant
            logger.debug(
                '[Doxtr Dark Swap] Original file not found, skipping: %s', filepath
            )
            return ''

    # Build dark variant path
    base, ext = os.path.splitext(filepath)
    dark_filepath = f'{base}{_DARK_SUFFIX}{ext}'

    # Check if dark variant exists (resolve same way as original)
    dark_abs = os.path.normpath(os.path.join(docdir, dark_filepath))
    if os.path.isfile(dark_abs):
        return dark_filepath

    dark_abs = os.path.normpath(os.path.join(srcdir, dark_filepath))
    if os.path.isfile(dark_abs):
        return dark_filepath

    logger.debug(
        '[Doxtr Dark Swap] No dark variant found for: %s (checked %s)',
        filepath, dark_filepath
    )
    return ''


def _try_swap_path(filepath: str, srcdir: str, docdir: str,
                   valid_extensions: set, exclude_patterns: list,
                   app, docname: str) -> str:
    """Attempt to resolve a dark variant for a matched file path.

    Applies all guards (URL, absolute path, exclusion) and resolves the dark
    variant. If a swap is made, tracks it and registers a dependency.

    Args:
        filepath: The file path extracted from the regex match.
        srcdir: Sphinx source directory (absolute).
        docdir: Directory of the current document (absolute).
        valid_extensions: Set of file extensions to consider.
        exclude_patterns: List of exclude glob patterns.
        app: Sphinx application instance.
        docname: Current document name.

    Returns:
        The dark variant path if available, or empty string (no swap).
    """
    if _is_url(filepath):
        return ''
    if os.path.isabs(filepath):
        logger.debug('[Doxtr Dark Swap] Skipping absolute path: %s', filepath)
        return ''
    if _is_excluded(filepath, exclude_patterns):
        return ''

    dark_path = _resolve_dark_variant(filepath, srcdir, docdir, valid_extensions)
    if dark_path:
        _track_swap(app, docname, filepath, dark_path, srcdir, docdir)
        return dark_path
    return ''


def _perform_swap(source_text: str, app, docname: str, srcdir: str,
                  docdir: str, directives_config: dict,
                  valid_extensions: set, exclude_patterns: list) -> str:
    """Scan source text and rewrite file references to _dark variants.

    Args:
        source_text: The RST/MyST source text to scan.
        app: Sphinx application instance.
        docname: Current document name.
        srcdir: Sphinx source directory (absolute).
        docdir: Directory of the current document (absolute).
        directives_config: Merged directives configuration dict.
        valid_extensions: Set of valid file extensions.
        exclude_patterns: List of exclude glob patterns.

    Returns:
        The (possibly modified) source text.
    """
    if not source_text.strip():
        return source_text

    directive_names = list(directives_config.keys())
    if not directive_names:
        return source_text

    # Collect all option names across all directives
    all_option_names = set()
    for dconf in directives_config.values():
        for opt in dconf.get('options', []):
            all_option_names.add(opt)

    # --- RST argument-based pattern ---
    rst_arg_pattern = _build_rst_argument_pattern(directive_names)

    def _rst_arg_replacer(match):
        prefix = match.group(1)       # leading whitespace + ".. "
        directive = match.group(2)    # directive name
        separator = match.group(3)    # ":: " (with trailing space)
        filepath = match.group(4)     # the file path

        dark_path = _try_swap_path(
            filepath, srcdir, docdir, valid_extensions, exclude_patterns,
            app, docname
        )
        if dark_path:
            return f'{prefix}{directive}{separator}{dark_path}'
        return match.group(0)

    source_text = rst_arg_pattern.sub(_rst_arg_replacer, source_text)

    # --- RST option-based pattern ---
    if all_option_names:
        rst_opt_pattern = _build_rst_option_pattern(sorted(all_option_names))

        def _rst_opt_replacer(match):
            prefix = match.group(1)       # leading whitespace + ":"
            option_name = match.group(2)  # option name (e.g. "file")
            separator = match.group(3)    # ": " (with trailing space)
            filepath = match.group(4)     # the file path

            dark_path = _try_swap_path(
                filepath, srcdir, docdir, valid_extensions, exclude_patterns,
                app, docname
            )
            if dark_path:
                return f'{prefix}{option_name}{separator}{dark_path}'
            return match.group(0)

        source_text = rst_opt_pattern.sub(_rst_opt_replacer, source_text)

    # --- MyST argument-based pattern ---
    myst_arg_pattern = _build_myst_argument_pattern(directive_names)

    def _myst_arg_replacer(match):
        prefix = match.group(1)       # backticks + "{"
        directive = match.group(2)    # directive name
        separator = match.group(3)    # "} " (closing brace + space)
        filepath = match.group(4)     # the file path

        dark_path = _try_swap_path(
            filepath, srcdir, docdir, valid_extensions, exclude_patterns,
            app, docname
        )
        if dark_path:
            return f'{prefix}{directive}{separator}{dark_path}'
        return match.group(0)

    source_text = myst_arg_pattern.sub(_myst_arg_replacer, source_text)

    return source_text


def _track_swap(app, docname: str, original: str, dark_path: str,
                srcdir: str, docdir: str) -> None:
    """Track a successful swap and register dependency.

    Populates ``app.env._doxtr_dark_source_swapped`` — a set of original file
    paths that were swapped. This is available to downstream hooks and child
    themes for introspection (e.g. skipping already-swapped paths).

    Args:
        app: Sphinx application instance.
        docname: Current document name.
        original: Original file path (as written in source).
        dark_path: Dark variant path that replaced the original.
        srcdir: Sphinx source directory.
        docdir: Document directory.
    """
    # Track in environment for downstream hooks
    if not hasattr(app.env, '_doxtr_dark_source_swapped'):
        app.env._doxtr_dark_source_swapped = set()
    app.env._doxtr_dark_source_swapped.add(original)

    # Register dependency — ensures rebuild when _dark variant changes
    # Resolve absolute path for dependency tracking
    dark_abs = os.path.normpath(os.path.join(docdir, dark_path))
    if not os.path.isfile(dark_abs):
        dark_abs = os.path.normpath(os.path.join(srcdir, dark_path))
    app.env.note_dependency(dark_abs)

    logger.info(
        '[Doxtr Dark Swap] %s: %s → %s', docname, original, dark_path
    )


# ---------------------------------------------------------------------------
# Sphinx event handlers
# ---------------------------------------------------------------------------

def swap_dark_sources(app, docname, source):
    """Sphinx ``source-read`` handler: rewrite file paths to _dark variants.

    Connected at priority 500 (Sphinx default). Fires before directive parsing,
    allowing extensions that consume files at parse time (PlantUML, Mermaid) to
    transparently receive dark variants.

    Guards (early exit):
        - Non-latex builder
        - Dark mode not active
        - Strategy is 'passthrough'
        - Master switch disabled (doxtr_enable_dark_file_swap)

    Args:
        app: Sphinx application instance.
        docname: Document name (e.g. 'index', 'api/overview').
        source: Single-element list containing the source text (mutable).
    """
    # --- Guard: builder type ---
    if app.builder.name != 'latex':
        return

    # --- Guard: dark mode not active ---
    if not to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return

    # --- Guard: passthrough strategy (light images are appropriate) ---
    if getattr(app.config, 'doxtr_dark_mode_strategy_resolved', 'invert') == 'passthrough':
        return

    # --- Guard: master switch ---
    if not to_bool(getattr(app.config, 'doxtr_enable_dark_file_swap', True)):
        return

    srcdir = str(app.srcdir)
    # Resolve document directory from docname (e.g. 'api/overview' → '<srcdir>/api/')
    docdir = os.path.dirname(os.path.join(srcdir, docname.replace('/', os.sep)))

    directives_config = _get_effective_directives(app.config)
    valid_extensions = _get_effective_extensions(app.config)
    exclude_patterns = _get_exclude_patterns(app.config)

    # source is a single-element list; modify in-place
    source[0] = _perform_swap(
        source[0], app, docname, srcdir, docdir,
        directives_config, valid_extensions, exclude_patterns
    )


def swap_dark_includes(app, relative_path, parent_docname, source):
    """Sphinx ``include-read`` handler: rewrite file paths in included files.

    Identical logic to ``swap_dark_sources`` but connected to the
    ``include-read`` event (Sphinx >= 7.2.4). Fires for files pulled in by
    ``.. include::`` directives that themselves contain other directives
    referencing external files.

    The ``include-read`` event signature differs from ``source-read``:
    it passes the relative path of the included file and the parent docname.

    Args:
        app: Sphinx application instance.
        relative_path: Path object of the included file relative to srcdir.
        parent_docname: Document name of the including (parent) document.
        source: Single-element list containing the included source text (mutable).
    """
    # Delegate using parent_docname for path resolution context.
    swap_dark_sources(app, parent_docname, source)
