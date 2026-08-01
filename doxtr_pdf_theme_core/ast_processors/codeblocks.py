"""AST processor for code block language injection.

This module handles the injection of language macros before code blocks
for per-language styling in LaTeX output.
"""
import re
from docutils import nodes

__all__ = ['process_codeblocks_ast']

# Precompiled regex for performance - strips non-alphanumeric characters for LaTeX-safe language names
_RE_SAFE_LANG = re.compile(r'[^a-zA-Z0-9]')


def process_codeblocks_ast(app, doctree, docname):
    """Process literal blocks and inject language macros.

    Adds a \\def\\ddCurrentCodeLang{<lang>} macro before each code block
    so the LaTeX preamble can apply per-language styling.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return
    
    for node in list(doctree.traverse(nodes.literal_block)):
        lang = node.get('language', 'default') or 'default'
        safe_lang = _RE_SAFE_LANG.sub('', lang).lower()
        raw_node = nodes.raw('', f'\n\\def\\ddCurrentCodeLang{{{safe_lang}}}\n', format='latex')
        idx = node.parent.index(node)
        node.parent.insert(idx, raw_node)
