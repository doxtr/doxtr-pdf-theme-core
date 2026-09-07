"""AST processor for the ``.. todo::`` directive styling.

This module handles the transformation of ``todo_node`` elements emitted by
the ``sphinx.ext.todo`` extension into a custom, fully-themed LaTeX tcolorbox
environment (``ddtodobox``), replacing Sphinx's default ``sphinxtodo``
environment with a box that participates in the three-tier merge, dark mode,
page adaptation, and ``dd:`` expression resolution.

A ``todo_node`` is a subclass of ``docutils.nodes.Admonition`` whose first
child is a ``nodes.title`` node. We extract the title, then wrap the remaining
body children between raw ``\\begin{ddtodobox}{<title>}`` /
``\\end{ddtodobox}`` markers inside a container node — the same wrapping
pattern used by the topics and highlights processors. Body children remain in
the doctree so Sphinx's LaTeX writer handles them normally (paragraphs,
lists, cross-references, math, figures, etc.).

The rendered box is completely replaceable by child themes: drop a
``latex_styles/todo/default.tex_t`` file into a ``doxtr_theme_style_paths``
entry (or the user project), or override the ``ddtodobox`` environment via
``register_preamble_hook(..., position='after_styles')``. See
``core_fallbacks.DEFAULT_TODO_STYLE`` for the absolute fallback.
"""
from docutils import nodes

from ..latex_escape import esc_latex
from ._helpers import make_pagegoal_cap_node

# ``sphinx.ext.todo`` may not be loaded (the extension is optional). Import the
# node type defensively so this processor degrades to a no-op when the todo
# extension is absent, rather than raising at import time.
try:
    from sphinx.ext.todo import todo_node
except Exception:  # pragma: no cover - defensive: ext may be unavailable
    todo_node = None

__all__ = ['process_todo_ast']


def process_todo_ast(app, doctree, docname):
    """Replace ``todo_node`` elements with a styled tcolorbox LaTeX environment.

    Transforms ``sphinx.ext.todo`` ``todo_node`` elements into a custom
    tcolorbox environment (``ddtodobox``) that can be fully styled via
    ``.tex_t`` templates and configuration.

    Uses the highlights/topics wrapping pattern: extracts the title, wraps
    the remaining body children between raw ``\\begin{ddtodobox}{<title>}``
    / ``\\end{ddtodobox}`` markers inside a container node. Body children
    remain in the doctree for Sphinx's LaTeX writer to handle.

    No-ops when the ``sphinx.ext.todo`` extension is not loaded
    (``todo_node is None``), when ``doxtr_enable_todo_processor`` is False,
    or for non-latex builders.

    Respects ``sphinx.ext.todo``'s own ``todo_include_todos`` visibility
    gate: when it is False (Sphinx's default), todos are hidden from output,
    so the ``todo_node`` elements are removed and no ``ddtodobox`` is
    emitted.

    Skips ``todo_node`` elements whose immediate parent is the document
    root. Sphinx's ``TodoListProcessor`` (``.. todolist::``) deep-copies
    each todo into a transient ``new_document('')`` and calls
    ``env.resolve_references`` on it, which re-emits ``doctree-resolved``;
    replacing that transient copy would break its subsequent
    ``document.remove(todo)`` call. Real ``.. todo::`` content is always
    nested inside a section/body, so this guard only skips the transient
    copies while still styling real todos and final todolist expansions.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    # The todo extension is optional — skip entirely when its node type is
    # unavailable.
    if todo_node is None:
        return
    if not getattr(app.config, 'doxtr_enable_todo_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    # Respect sphinx.ext.todo's own visibility gate. When todo_include_todos
    # is False (Sphinx's default), todos are hidden from output — do not
    # render them into styled boxes either. Remove the todo_node here so the
    # default sphinxtodo path also produces nothing.
    if not getattr(app.config, 'todo_include_todos', False):
        for node in list(doctree.traverse(todo_node)):
            if node.parent is not None:
                node.parent.remove(node)
        return

    for node in list(doctree.traverse(todo_node)):
        # Skip todo_nodes that sit directly under a document root. Sphinx's
        # TodoListProcessor (`.. todolist::`) deep-copies each todo into a
        # transient `new_document('')` and calls env.resolve_references on it,
        # which re-emits 'doctree-resolved'. If we replace_self on that
        # transient copy, TodoListProcessor's subsequent `document.remove(todo)`
        # raises "list.remove(x): x not in list". Real `.. todo::` content is
        # always nested inside a section/body, never a direct document child,
        # so this guard only skips the transient copies. Checked before
        # marking doxtr_todo_processed so a legitimately nested reappearance
        # can still be processed.
        if isinstance(node.parent, nodes.document):
            continue
        if node.get('doxtr_todo_processed'):
            continue
        node['doxtr_todo_processed'] = True

        # Extract and remove the title node (todo_node's first child).
        title_text = ''
        title_node = None
        for child in node.children:
            if isinstance(child, nodes.title):
                title_text = child.astext()
                title_node = child
                break

        # Collect body children (everything except the title).
        body_children = [c for c in node.children if c is not title_node]
        safe_title = esc_latex(title_text)

        # Wrapping pattern: keep children in the doctree for Sphinx's LaTeX
        # writer; only wrap them in our tcolorbox environment.
        wrapper = nodes.container(classes=['doxtr-todo'])
        # Defense-in-depth: cap \pagegoal before the breakable tcolorbox opens.
        if getattr(app.config, 'doxtr_pagegoal_overflow_guard', True) is not False:
            wrapper.append(make_pagegoal_cap_node())
        wrapper.append(nodes.raw(
            '', f'\n\\begin{{ddtodobox}}{{{safe_title}}}\n', format='latex'
        ))
        wrapper.extend(body_children)
        wrapper.append(nodes.raw(
            '', '\n\\end{ddtodobox}\n', format='latex'
        ))
        node.replace_self(wrapper)
