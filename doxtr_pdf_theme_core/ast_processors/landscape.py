"""AST processor for automatic and forced landscape page orientation.

This module handles:
- ``.. container:: doxtr-landscape`` — forces content into landscape pages
- Auto-landscape for tables — column-count heuristic rotates wide tables

The landscape processor runs early (priority 985) so that contained elements
(tables, code blocks, etc.) are still processed by later AST processors.
"""
from docutils import nodes
from sphinx.util import logging

__all__ = [
    'process_landscape_ast',
    'register_landscape_wrapper',
    'wrap_in_landscape',
    'LANDSCAPE_CLASS',
    'NO_LANDSCAPE_CLASS',
    'FORCE_LANDSCAPE_CLASS',
    'NEEDS_TABLE_CLASSES',
    'DEFAULT_MIN_COLUMNS',
]

logger = logging.getLogger(__name__)

#: Container class that forces landscape orientation for any content.
LANDSCAPE_CLASS = 'doxtr-landscape'

#: Class that prevents auto-landscape on a specific table.
NO_LANDSCAPE_CLASS = 'no-landscape'

#: Classes used by sphinx-needs to mark its rendering tables.
#: These are styled tcolorbox containers, not data tables, and must be
#: excluded from landscape wrapping (which uses unbreakable minipages).
#: If sphinx-needs changes these class names, update here.
NEEDS_TABLE_CLASSES = ('need', 'need_node')

#: Default minimum column count to trigger adaptive landscape.
#: Tables with >= this many columns use the doxtradaptivelandscape
#: environment (see preamble.tex_t) which selects an appropriate
#: A-series page size based on column count * minimum column width.
DEFAULT_MIN_COLUMNS = 4

#: Module-level storage for the registered landscape wrapper function.
#: None means use the built-in \begin{landscape}/\end{landscape} logic.
_landscape_wrapper_fn = None

#: Class that can be added to any container or table to force landscape.
#: Synonym for LANDSCAPE_CLASS kept for backward compatibility.
FORCE_LANDSCAPE_CLASS = 'force-landscape'


def register_landscape_wrapper(fn):
    r"""Replace the default landscape wrapping logic with a custom function.

    *fn* must accept a single ``nodes.Node`` argument and perform the
    wrapping in place (typically via ``node.replace_self(...)`` or
    ``parent.insert(...)``).  It replaces only Phase 1 (forced-landscape
    container wrapping); Phase 2 auto-landscape table wrapping is not
    delegated through this hook.

    Call this from a child theme's ``setup()`` function — before
    ``config_inited`` fires — to substitute an entirely different
    landscape environment (e.g. a custom page-size system).

    Example::

        from doxtr_pdf_theme_core import register_landscape_wrapper

        def my_wrapper(node):
            pre = nodes.raw('', r'\begin{mytheme@landscape}', format='latex')
            post = nodes.raw('', r'\end{mytheme@landscape}', format='latex')
            node.replace_self([pre] + list(node.children) + [post])

        register_landscape_wrapper(my_wrapper)
    """
    global _landscape_wrapper_fn
    _landscape_wrapper_fn = fn


def wrap_in_landscape(node):
    r"""Wrap *node* using the registered landscape wrapper.

    If no custom wrapper has been registered via
    :func:`register_landscape_wrapper`, the built-in
    ``\begin{landscape}`` / ``\end{landscape}`` wrapping is used.

    This is the public API for forced landscape.  The
    ``process_landscape_ast`` Phase 1 handler calls this function so
    that child themes which replace the wrapper via
    :func:`register_landscape_wrapper` affect forced-landscape
    containers as well as any custom code that calls this function
    directly.
    """
    if _landscape_wrapper_fn is not None:
        _landscape_wrapper_fn(node)
        return
    # Default: wrap children in pdflscape's landscape environment.
    pre = nodes.raw('', '\n\\begin{landscape}\n', format='latex')
    post = nodes.raw('', '\n\\end{landscape}\n', format='latex')
    node.replace_self([pre] + list(node.children) + [post])


def _has_ancestor_class(node, cls):
    """Check if any ancestor of *node* carries *cls* in its classes."""
    parent = node.parent
    while parent is not None:
        if cls in getattr(parent, 'attributes', {}).get('classes', []):
            return True
        parent = parent.parent
    return False


def _get_table_column_count(table_node):
    """Return the number of columns declared in a table's tgroup.

    Returns 0 if the structure cannot be determined.
    """
    for tgroup in table_node.findall(nodes.tgroup):
        cols = tgroup.get('cols', 0)
        if cols:
            return cols
        # Fallback: count colspec children
        colspecs = list(tgroup.findall(nodes.colspec))
        if colspecs:
            return len(colspecs)
    return 0


def process_landscape_ast(app, doctree, docname):
    """Wrap doxtr-landscape containers and auto-landscape wide tables.

    Phase 1 — forced landscape:
        Any ``.. container:: doxtr-landscape`` is replaced by its children
        wrapped in ``\\begin{landscape}`` / ``\\end{landscape}`` raw nodes.
        This works for tables, figures, code blocks, or arbitrary content.

    Phase 2 — auto-landscape for tables:
        When ``doxtr_table_auto_landscape`` is True (default), tables that
        are NOT already inside a forced-landscape block and do NOT carry the
        ``no-landscape`` class are evaluated for landscape rotation.

        Because Sphinx tables use relative column widths (``\\X{a}{b}``),
        they always render at exactly ``\\linewidth`` regardless of column
        count.  The ``doxtrautolandscape`` LaTeX environment therefore cannot
        detect them as "too wide" via width measurement.  Instead, tables
        with a column count >= ``doxtr_landscape_min_columns`` (default 4)
        are wrapped in ``doxtradaptivelandscape[N]`` which selects an
        appropriate A-series page size.

        Additionally, such tables receive the ``longtable`` CSS class so
        that Sphinx's LaTeX writer emits a ``longtable`` environment instead
        of the default ``tabular``.  This is critical because landscape
        pages have reduced height and an unbreakable ``tabular`` would be
        clipped if it exceeds ``\\textheight``.  The ``longtable``
        environment breaks naturally across pages.

        Tables below the threshold keep the ``doxtrautolandscape`` wrapper
        for non-Sphinx content that may benefit from width-based detection.

    Skipped entirely for non-latex builders.
    """
    if not getattr(app.config, 'doxtr_enable_landscape_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    auto_landscape = getattr(app.config, 'doxtr_table_auto_landscape', True)
    min_columns = getattr(app.config, 'doxtr_landscape_min_columns', DEFAULT_MIN_COLUMNS)

    # --- Phase 1: forced landscape containers ---
    for node in list(doctree.traverse(nodes.container)):
        if LANDSCAPE_CLASS not in node.get('classes', []):
            continue
        if node.get('doxtr_landscape_processed'):
            continue
        node['doxtr_landscape_processed'] = True

        # Delegate to the registered wrapper (or built-in default).
        # wrap_in_landscape calls node.replace_self() internally.
        wrap_in_landscape(node)

    # --- Phase 2: auto-landscape for tables ---
    if not auto_landscape:
        return

    for node in list(doctree.traverse(nodes.table)):
        if node.get('doxtr_autolandscape_processed'):
            continue
        node['doxtr_autolandscape_processed'] = True

        # Skip tables explicitly opted out
        if NO_LANDSCAPE_CLASS in node.get('classes', []):
            continue

        # Defensive: skip tables already inside a forced landscape block.
        # Phase 1 removes doxtr-landscape containers via replace_self, so
        # this guard only fires on re-entry or partial processing.
        if _has_ancestor_class(node, LANDSCAPE_CLASS):
            continue

        # Skip sphinx-needs rendering tables -- they are styled tcolorbox
        # containers, not data tables.  Wrapping them in doxtrautolandscape
        # (which uses an unbreakable minipage/lrbox) would prevent the
        # need box from breaking across pages.
        # Child themes that use different needs plugins can extend this list
        # via the doxtr_landscape_skip_table_classes config value.
        extra_skip = tuple(getattr(app.config, 'doxtr_landscape_skip_table_classes', []))
        skip_classes = NEEDS_TABLE_CLASSES + extra_skip
        if any(c in node.get('classes', []) for c in skip_classes):
            continue

        # Determine landscape wrapping strategy based on column count.
        # Sphinx tables with many columns always render at \linewidth due to
        # relative \X{a}{b} column specs, making width-based auto-detection
        # impossible.  Use column count as the heuristic instead.
        parent = node.parent
        if parent is None:
            continue
        idx = parent.index(node)

        col_count = _get_table_column_count(node)
        if col_count == 0:
            logger.warning(
                '[Doxtr Landscape] Could not determine column count for '
                'table in %s; skipping landscape wrapping.', docname,
            )
            continue
        if col_count >= min_columns:
            # Force longtable format so the table can break across pages.
            # Landscape pages have reduced height; without longtable, tables
            # with many rows would be clipped by the unbreakable tabular box.
            if 'longtable' not in node.get('classes', []):
                node['classes'].append('longtable')
            # Use adaptive landscape (doxtradaptivelandscape[N] in
            # preamble.tex_t): selects smallest A-series page size that
            # fits the table with readable column widths (default 22mm
            # per column).  Content can break across multiple pages.
            pre = nodes.raw(
                '', f'\n\\begin{{doxtradaptivelandscape}}[{col_count}]\n',
                format='latex',
            )
            post = nodes.raw(
                '', '\n\\end{doxtradaptivelandscape}\n', format='latex',
            )
        else:
            # Narrow tables: use auto-measurement (works for non-Sphinx content)
            pre = nodes.raw('', '\n\\begin{doxtrautolandscape}\n', format='latex')
            post = nodes.raw('', '\n\\end{doxtrautolandscape}\n', format='latex')

        parent.insert(idx, pre)
        # node is now at idx+1, insert post after it
        parent.insert(idx + 2, post)
