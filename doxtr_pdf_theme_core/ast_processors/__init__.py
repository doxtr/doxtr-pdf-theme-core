"""AST processors for transforming docutils doctrees to LaTeX.

This package contains all doctree-resolved event handlers that transform
Sphinx document trees into LaTeX-compatible structures for PDF output.

Each processor handles a specific type of RST/Sphinx element:
- containers: Custom styled container boxes
- tables: Vertical mode fix for block elements after headings; reserved table hook
- codeblocks: Code block language injection
- epigraphs: Epigraph/dictum formatting
- sidebars: Sidebar boxes with text wrapping
- highlights: Highlights directive styling
- needs: sphinx-needs requirement boxes
- topics: Topic and contents directive styled boxes
- todo: sphinx.ext.todo directive styled boxes
- landscape: Forced and automatic landscape page orientation
"""
from .containers import process_containers_ast
from .tables import (process_tables_ast, fix_block_after_paragraph,
                     PARAGRAPH_FIX_PRIORITY, register_par_fix_block_type,
                     register_par_fix_skip_type,
                     register_column_width_algorithm,
                     ColumnInfo, PT_TO_MM, DEFAULT_MIN_COL_WIDTH_MM)
from .codeblocks import process_codeblocks_ast
from .epigraphs import process_epigraph_ast
from .sidebars import process_sidebar_ast, render_nodes_to_latex
from .highlights import process_highlights_ast
from .needs import process_needs_ast
from .topics import process_topics_ast
from .todo import process_todo_ast
from .landscape import (
    process_landscape_ast,
    wrap_in_landscape,
    register_landscape_wrapper,
    LANDSCAPE_CLASS,
    NO_LANDSCAPE_CLASS,
    FORCE_LANDSCAPE_CLASS,
    DEFAULT_MIN_COLUMNS,
    DEFAULT_LONGTABLE_ROW_THRESHOLD,
)
from ._helpers import make_pagegoal_cap_node


__all__ = [
    'process_containers_ast',
    'process_tables_ast',
    'fix_block_after_paragraph',
    'PARAGRAPH_FIX_PRIORITY',
    'register_par_fix_block_type',
    'register_par_fix_skip_type',
    'register_column_width_algorithm',
    'ColumnInfo',
    'PT_TO_MM',
    'DEFAULT_MIN_COL_WIDTH_MM',
    'process_codeblocks_ast',
    'process_epigraph_ast',
    'process_sidebar_ast',
    'render_nodes_to_latex',
    'process_highlights_ast',
    'process_needs_ast',
    'process_topics_ast',
    'process_todo_ast',
    'process_landscape_ast',
    'wrap_in_landscape',
    'register_landscape_wrapper',
    'LANDSCAPE_CLASS',
    'NO_LANDSCAPE_CLASS',
    'FORCE_LANDSCAPE_CLASS',
    'DEFAULT_MIN_COLUMNS',
    'DEFAULT_LONGTABLE_ROW_THRESHOLD',
    'make_pagegoal_cap_node',
]
