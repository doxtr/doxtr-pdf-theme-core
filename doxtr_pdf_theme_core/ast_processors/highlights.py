"""AST processor for highlights directive styling.

This module handles the transformation of block_quote nodes with the
'highlights' class into custom styled LaTeX tcolorbox environments,
replacing Sphinx's default quote indentation with a fully styled box.
"""
from docutils import nodes

from ..latex_escape import esc_latex

__all__ = ['process_highlights_ast']


def process_highlights_ast(app, doctree, docname):
    """Process highlights block quotes and wrap in styled LaTeX environment.

    Transforms block_quote nodes with 'highlights' class into a custom
    tcolorbox environment (ddhighlightsbox) that can be fully styled
    via .tex_t templates and configuration.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return

    highlights_conf = getattr(app.config, 'doxtr_highlights', {})

    for node in list(doctree.traverse(nodes.block_quote)):
        if 'highlights' not in node.get('classes', []):
            continue
        if node.get('doxtr_processed'):
            continue
        node['doxtr_processed'] = True

        # Build the LaTeX wrapper using our custom environment
        wrapper = nodes.container(classes=['doxtr-highlights'])
        wrapper.append(nodes.raw('', '\n\\begin{ddhighlightsbox}\n', format='latex'))
        wrapper.extend(node.children)
        wrapper.append(nodes.raw('', '\n\\end{ddhighlightsbox}\n', format='latex'))
        node.replace_self(wrapper)
