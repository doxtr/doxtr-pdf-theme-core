"""AST processor for table header styling.

This module handles the injection of row colors into table headers
for proper LaTeX table styling.
"""
from docutils import nodes

__all__ = ['process_tables_ast']


def process_tables_ast(app, doctree, docname):
    """Process table nodes and inject header row coloring.

    Adds \\rowcolor commands to table header rows for consistent
    styling across the document.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return
    
    for node in list(doctree.traverse(nodes.table)):
        if node.get('doxtr_processed_table'):
            continue
        node['doxtr_processed_table'] = True
        
        for tgroup in node.traverse(nodes.tgroup):
            for thead in tgroup.traverse(nodes.thead):
                for row in thead.traverse(nodes.row):
                    row.insert(0, nodes.raw('', r'\rowcolor{ddtableheaderbg}', format='latex'))
