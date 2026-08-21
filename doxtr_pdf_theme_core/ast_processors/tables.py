"""AST processor for table positioning and styling.

This module handles:
- Vertical mode fix for block elements after run-in paragraph headings
- Reserved extension point for future table styling hooks

Header row colouring is handled separately by Sphinx's ``colorrows`` machinery via
``\\sphinxTableRowColorHeader`` defined in the table ``.tex_t`` templates.
This works uniformly for all table types (tabular, tabulary, longtable).

The ``process_tables_ast`` function remains a reserved hook for child
themes or future extensions that need doctree-level table manipulation.  The
``doxtr_enable_table_processor`` config flag gates execution.
"""

from docutils import nodes
from sphinx.util import logging

__all__ = ['process_tables_ast', 'fix_block_after_paragraph', 'PARAGRAPH_FIX_PRIORITY',
           'register_par_fix_block_type', 'register_par_fix_skip_type']

logger = logging.getLogger(__name__)

#: Node types to skip when finding the first "real" body child of a section.
#: These are metadata/structural nodes that appear between the section title
#: and the actual content.
_SKIP_TYPES = (
    nodes.title,
    nodes.target,
    nodes.comment,
    nodes.system_message,
)

#: Block-level node types that need vertical mode when following a heading.
#: - table: csv-table, list-table, etc.
#: - figure: image with caption
#: - container: generic .. container:: directive (often wraps tables/figures
#:   from other extensions or custom directives)
_BLOCK_TYPES = (nodes.table, nodes.figure, nodes.container)

#: Event priority for the paragraph fix. Runs after the landscape processor
#: (985) — landscape-wrapped content starts on a new page and does not need
#: the \\par fix.
PARAGRAPH_FIX_PRIORITY = 980


def register_par_fix_block_type(node_type):
    """Register an additional node type that needs the vertical mode fix.

    Call at module level or inside ``setup()`` — before ``config_inited``
    fires (priority 900).

    Args:
        node_type: A docutils node class (e.g., ``nodes.admonition``).
    """
    global _BLOCK_TYPES
    if node_type not in _BLOCK_TYPES:
        _BLOCK_TYPES = _BLOCK_TYPES + (node_type,)


def register_par_fix_skip_type(node_type):
    """Register an additional node type to skip when scanning for first body child.

    Call at module level or inside ``setup()`` — before ``config_inited``
    fires (priority 900).

    Args:
        node_type: A docutils node class (e.g., ``nodes.decoration``).
    """
    global _SKIP_TYPES
    if node_type not in _SKIP_TYPES:
        _SKIP_TYPES = _SKIP_TYPES + (node_type,)


def fix_block_after_paragraph(app, doctree, docname):
    """Insert \\leavevmode\\par before block elements that follow section titles.

    In KOMA-Script, ``\\paragraph`` and ``\\subparagraph`` headings use a
    negative ``afterskip``, making them "run-in" headings where following
    content continues on the same line.  When a table, figure, or container
    is the first body element after such a heading, it renders to the side
    of the heading text instead of below it.

    This function inserts a raw ``\\leavevmode\\par`` LaTeX node before such
    block elements, forcing LaTeX back into vertical mode.  For block-level
    headings (section, subsection, etc.) that already have positive afterskip,
    ``\\par`` in vertical mode is a no-op, making this safe at all depths.

    Skipped if ``doxtr_enable_table_processor`` is False.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_table_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    for section_node in list(doctree.traverse(nodes.section)):
        if section_node.get('doxtr_par_fix_processed'):
            continue
        section_node['doxtr_par_fix_processed'] = True

        # Find first non-metadata child after the title, tracking index
        first_block = None
        first_block_idx = None
        for idx, child in enumerate(section_node.children):
            if isinstance(child, _SKIP_TYPES):
                continue
            first_block = child
            first_block_idx = idx
            break

        if first_block is None:
            continue

        if not isinstance(first_block, _BLOCK_TYPES):
            continue

        # Insert \leavevmode\par before the block element
        par_node = nodes.raw('', '\n' + r'\leavevmode\par' + '\n', format='latex')
        section_node.insert(first_block_idx, par_node)
        logger.debug(
            '[Doxtr Tables] Inserted \\par before %s in %s',
            first_block.__class__.__name__, docname,
        )


def process_tables_ast(app, doctree, docname):
    """Reserved hook for doctree-level table processing.

    Currently a no-op.  Header row background colouring is handled by
    Sphinx's ``colorrows`` machinery (``\\sphinxTableRowColorHeader``),
    which works for all table types including longtable.

    Retained as an extension point — child themes can monkey-patch this
    function or register additional processors at adjacent priorities.

    Skipped if ``doxtr_enable_table_processor`` is False.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_table_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return
