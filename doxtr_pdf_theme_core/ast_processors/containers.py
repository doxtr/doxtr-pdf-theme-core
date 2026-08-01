"""AST processor for custom styled container boxes.

This module handles the transformation of container nodes with registered
style classes into LaTeX tcolorbox environments.
"""
import re
from docutils import nodes

from ..latex_escape import esc_latex

__all__ = ['process_containers_ast']

# Precompiled regex for performance - strips non-alpha characters for LaTeX-safe names
_RE_SAFE_NAME = re.compile(r'[^a-zA-Z]')


def process_containers_ast(app, doctree, docname):
    """Process container nodes and wrap them in styled LaTeX environments.

    Transforms container nodes that match registered container styles
    (from doxtr_containers config) into LaTeX tcolorbox environments
    with appropriate styling.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return
    containers_conf = getattr(app.config, 'doxtr_containers', {})
    if not containers_conf:
        return

    for node in list(doctree.traverse(nodes.container)):
        if node.get('doxtr_processed'):
            continue
        match_class = next((c for c in node.get('classes', []) if c in containers_conf), None)
        if not match_class:
            continue
        node['doxtr_processed'] = True

        c_conf = containers_conf.get(match_class, {})
        title_raw = c_conf.get('title_raw', False)

        # Title resolution priority:
        # 1. :notitle: sentinel — explicitly suppress title
        # 2. :title: directive option — explicit per-instance display title
        # 3. Config 'title' — static title from container configuration
        # 4. :name: directive option — legacy fallback (anchor used as display)
        # 5. Empty string — notitle
        if node.get('doxtr_stylebox_notitle', False):
            title = ""
        elif node.get('doxtr_stylebox_title', None) is not None:
            title = node['doxtr_stylebox_title']
            # SECURITY: Per-instance :title: from RST is ALWAYS escaped regardless of
            # the container's config-level title_raw flag. Only the static config 'title'
            # key respects title_raw, and only for trusted LaTeX macro strings.
            title_raw = False
        elif c_conf.get('title'):
            title = c_conf['title']
        else:
            names = node.get('names', [])
            title = names[0] if names else ""
            title_raw = False  # :name: values are always escaped

        safe_title = title if title_raw else esc_latex(title)
        safe_match_class = _RE_SAFE_NAME.sub('', match_class)
        title_str = f"ddcontainertitlestyle{safe_match_class}, title={{\\csname ddconticon{safe_match_class}\\endcsname {safe_title}}}" if safe_title else "notitle"

        wrapper = nodes.container(classes=['doxtr-flat-container'])
        wrapper.append(nodes.raw('', f'\n\\begin{{ddcontainer{safe_match_class}}}[{title_str}]\n', format='latex'))
        wrapper.extend(node.children)
        wrapper.append(nodes.raw('', f'\n\\end{{ddcontainer{safe_match_class}}}\n', format='latex'))
        node.replace_self(wrapper)
