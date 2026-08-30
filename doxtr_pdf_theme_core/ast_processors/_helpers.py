"""Shared utilities for AST processors.

Small helpers that multiple AST processor modules need. Lives in its own
module to avoid circular imports (the ``__init__.py`` re-exports from
submodules, so submodules cannot import back from the package root).
"""
from docutils import nodes

__all__ = ['make_pagegoal_cap_node']


def make_pagegoal_cap_node():
    """Create a raw LaTeX node that caps ``\\pagegoal`` at ``\\textheight``.

    Call this from any AST processor that emits a breakable tcolorbox
    environment and append the returned node to the wrapper **before**
    the ``\\begin{...}`` node.  The guard prevents tcolorbox's breakable
    algorithm from overestimating available vertical space when
    ``\\vsize > \\textheight`` (stale after KOMAoptions geometry changes
    or landscape-to-portrait transitions).

    The emitted command ``\\doxtrcapbreakablepagegoal`` is the public
    alias defined in ``preamble.tex_t``; it uses standard catcode so it
    works in document-body context where ``@`` is not a letter.
    """
    return nodes.raw('', '\n\\doxtrcapbreakablepagegoal%\n', format='latex')
