"""AST processors for transforming docutils doctrees to LaTeX.

This package contains all doctree-resolved event handlers that transform
Sphinx document trees into LaTeX-compatible structures for PDF output.

Each processor handles a specific type of RST/Sphinx element:
- containers: Custom styled container boxes
- tables: Table header styling and row coloring
- codeblocks: Code block language injection
- epigraphs: Epigraph/dictum formatting
- sidebars: Sidebar boxes with text wrapping
- highlights: Highlights directive styling
- needs: sphinx-needs requirement boxes
"""
from .containers import process_containers_ast
from .tables import process_tables_ast
from .codeblocks import process_codeblocks_ast
from .epigraphs import process_epigraph_ast
from .sidebars import process_sidebar_ast, render_nodes_to_latex
from .highlights import process_highlights_ast
from .needs import process_needs_ast

__all__ = [
    'process_containers_ast',
    'process_tables_ast',
    'process_codeblocks_ast',
    'process_epigraph_ast',
    'process_sidebar_ast',
    'render_nodes_to_latex',
    'process_highlights_ast',
    'process_needs_ast',
]
