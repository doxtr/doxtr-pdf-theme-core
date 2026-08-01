"""AST processor for sidebar boxes with text wrapping.

This module handles the transformation of sidebar nodes into LaTeX
wrapfigure environments inside tcolorbox for proper text wrapping.
"""
from docutils import nodes

from ..latex_escape import esc_latex

__all__ = ['process_sidebar_ast', 'render_nodes_to_latex']


def render_nodes_to_latex(app, nodes_list: list) -> str:
    """Render a list of docutils nodes to LaTeX, preserving inline markup.

    Walks through the node tree and converts common inline elements
    (emphasis, strong, literal, references) to their LaTeX equivalents.
    Falls back to plain text for unknown node types.

    Args:
        app: The Sphinx application object.
        nodes_list: List of docutils nodes to render.

    Returns:
        A LaTeX string with inline formatting preserved.
    """
    if not nodes_list:
        return ''

    parts = []

    def _walk(node):
        """Recursively walk a node tree and emit LaTeX."""
        if isinstance(node, nodes.Text):
            parts.append(esc_latex(node.astext()))
        elif isinstance(node, nodes.raw):
            if node.get('format', '') == 'latex':
                parts.append(node.astext())
        elif isinstance(node, nodes.emphasis):
            parts.append(r'\emph{')
            for child in node.children:
                _walk(child)
            parts.append('}')
        elif isinstance(node, nodes.strong):
            parts.append(r'\textbf{')
            for child in node.children:
                _walk(child)
            parts.append('}')
        elif isinstance(node, nodes.literal):
            parts.append(r'\sphinxcode{\sphinxupquote{')
            parts.append(esc_latex(node.astext()))
            parts.append('}}')
        elif isinstance(node, nodes.reference):
            uri = node.get('refuri', '')
            if uri:
                parts.append(f'\\href{{{uri}}}{{')
                for child in node.children:
                    _walk(child)
                parts.append('}')
            else:
                for child in node.children:
                    _walk(child)
        elif isinstance(node, nodes.paragraph):
            parts.append('\\sphinxAtStartPar\n')
            for child in node.children:
                _walk(child)
            parts.append('\n\n')
        elif isinstance(node, nodes.inline):
            for child in node.children:
                _walk(child)
        elif isinstance(node, nodes.title_reference):
            parts.append(r'\sphinxtitleref{')
            for child in node.children:
                _walk(child)
            parts.append('}')
        elif isinstance(node, nodes.superscript):
            parts.append(r'\textsuperscript{')
            for child in node.children:
                _walk(child)
            parts.append('}')
        elif isinstance(node, nodes.subscript):
            parts.append(r'\textsubscript{')
            for child in node.children:
                _walk(child)
            parts.append('}')
        elif hasattr(node, 'children'):
            # Generic container — recurse into children
            for child in node.children:
                _walk(child)
        else:
            # Leaf node with no children — extract text
            text = node.astext() if hasattr(node, 'astext') else ''
            if text:
                parts.append(esc_latex(text))

    for node in nodes_list:
        _walk(node)

    return ''.join(parts)


def process_sidebar_ast(app, doctree, docname):
    """Replace sidebar nodes and following paragraphs with raw LaTeX.

    Uses the wrapfigure-inside-tcolorbox pattern. This avoids Sphinx inserting a
    blank line between \\end{wrapfigure} and the wrapping text, which would
    break wrapfig's paragraph shaping.

    Uses Sphinx's LaTeX translator to properly render inline markup in the
    sidebar body and following paragraphs, preserving bold, code, links, etc.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return

    for node in list(doctree.traverse(nodes.sidebar)):
        if node.get('doxtr_sidebar_processed'):
            continue
        node['doxtr_sidebar_processed'] = True
        parent = node.parent
        if parent is None:
            continue
        idx = parent.index(node)

        # Collect following paragraph nodes that should wrap around the sidebar
        following_nodes = []
        for sibling in parent.children[idx + 1:]:
            if isinstance(sibling, nodes.paragraph):
                following_nodes.append(sibling)
            else:
                break  # Stop at non-paragraph (section, code block, etc.)

        # Extract sidebar title, subtitle, and body
        sidebar_title = ''
        sidebar_subtitle = ''
        sidebar_body_nodes = []
        for child in node.children:
            if isinstance(child, nodes.title):
                sidebar_title = child.astext()
            elif isinstance(child, nodes.subtitle):
                sidebar_subtitle = child.astext()
            else:
                sidebar_body_nodes.append(child)

        # Escape LaTeX special characters in title/subtitle
        safe_title = esc_latex(sidebar_title)
        safe_subtitle = esc_latex(sidebar_subtitle)

        # Mark following nodes for removal
        for para in following_nodes:
            parent.remove(para)

        # Render body nodes with proper inline formatting via LaTeX translator
        rendered_body = render_nodes_to_latex(app, sidebar_body_nodes)
        rendered_following = render_nodes_to_latex(app, following_nodes)

        # Build raw LaTeX with the working pattern:
        # \begin{tcolorbox}[blanker]
        # \begin{wrapfigure}{R}{width}%
        #   <sidebar box>
        # \end{wrapfigure}%
        # <wrapping text>   ← NO BLANK LINE
        # \end{tcolorbox}
        raw_latex = '\n\\begin{tcolorbox}[blanker, coltext=., before skip=1em, after skip=1em]%\n'
        raw_latex += '\\begin{wrapfigure}{\\ddsidebarposition}{\\ddsidebarwidth}%\n'
        raw_latex += '\\begin{ddsidebarinnerbox}%\n'
        if safe_title:
            raw_latex += f'\\sphinxstylesidebartitle{{{safe_title}}}%\n'
        if safe_subtitle:
            raw_latex += f'\\sphinxstylesidebarsubtitle{{{safe_subtitle}}}%\n'
        raw_latex += '\n'

        # Body with inline markup preserved
        if rendered_body.strip():
            raw_latex += rendered_body.strip() + '\n'

        raw_latex += '\\end{ddsidebarinnerbox}%\n'
        raw_latex += '\\end{wrapfigure}%\n'

        # Following paragraphs — directly after wrapfigure with NO blank line
        if rendered_following.strip():
            raw_latex += rendered_following.strip() + '\n'

        raw_latex += '\\end{tcolorbox}\n'

        # Replace sidebar node with raw LaTeX
        raw_node = nodes.raw('', raw_latex, format='latex')
        parent.insert(idx, raw_node)
        parent.remove(node)
