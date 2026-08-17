"""AST processor for topic and contents directive styling.

This module handles the transformation of topic nodes (both ``.. topic::``
and ``.. contents::`` directives) into custom styled LaTeX tcolorbox
environments, replacing Sphinx's default sphinxShadowBox rendering with
fully themed boxes that participate in the three-tier merge, dark mode,
page adaptation, and dd: expression resolution.

Uses the highlights/containers wrapping pattern: extracts the title, wraps
remaining body children between raw \\begin{env}/\\end{env} markers inside
a container node. Body children remain in the doctree for Sphinx's full
LaTeX writer to handle (bullet lists, cross-references, math, figures, etc.).
"""
from docutils import nodes

from ..latex_escape import esc_latex

__all__ = ['process_topics_ast']


def process_topics_ast(app, doctree, docname):
    """Replace topic and contents nodes with styled tcolorbox LaTeX.

    Transforms topic nodes into custom tcolorbox environments (doxtrtopic
    or doxtrcontents) that can be fully styled via .tex_t templates and
    configuration. The ``.. contents::`` directive creates a topic node
    with classes=['contents'], which is detected and handled separately.

    Uses the highlights/containers wrapping pattern: extracts the title,
    wraps remaining body children between raw \\begin{env}/\\end{env}
    markers inside a container node. Body children remain in the doctree
    for Sphinx's LaTeX writer to handle (bullet lists, cross-references,
    math, figures, etc.).

    Skipped if ``doxtr_enable_topics_processor`` is False.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_topics_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    conf = app.config

    # Get per-type configurations for opt-out checking
    topic_conf = getattr(conf, 'doxtr_topic', {})
    contents_conf = getattr(conf, 'doxtr_contents', {})

    for node in list(doctree.traverse(nodes.topic)):
        if node.get('doxtr_topic_processed'):
            continue
        node['doxtr_topic_processed'] = True

        # Determine if this is a 'contents' directive or a 'topic'.
        # The contents directive creates a topic node with classes=['contents']
        is_contents = 'contents' in node.get('classes', [])
        env_name = 'doxtrcontents' if is_contents else 'doxtrtopic'

        # Check per-type enabled flag
        section_conf = contents_conf if is_contents else topic_conf
        if not section_conf.get('enabled', True):
            continue

        # Extract and remove the title node
        title_text = ''
        title_node = None
        for child in node.children:
            if isinstance(child, nodes.title):
                title_text = child.astext()
                title_node = child
                break

        # Collect body children (everything except the title)
        body_children = [c for c in node.children if c is not title_node]
        safe_title = esc_latex(title_text)

        # Wrapping pattern: keep children in doctree for Sphinx's LaTeX writer
        wrapper = nodes.container(classes=[f'doxtr-{env_name}'])
        wrapper.append(nodes.raw(
            '', f'\n\\begin{{{env_name}}}{{{safe_title}}}\n', format='latex'
        ))
        wrapper.extend(body_children)
        wrapper.append(nodes.raw(
            '', f'\n\\end{{{env_name}}}\n', format='latex'
        ))
        node.replace_self(wrapper)
