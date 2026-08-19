"""AST processor for table styling (reserved extension point).

Header row colouring is handled by Sphinx's ``colorrows`` machinery via
``\\sphinxTableRowColorHeader`` defined in the table ``.tex_t`` templates.
This works uniformly for all table types (tabular, tabulary, longtable).

This module is retained as a reserved hook for child themes or future
extensions that need doctree-level table manipulation.  The
``doxtr_enable_table_processor`` config flag gates execution.
"""

__all__ = ['process_tables_ast']


def process_tables_ast(app, doctree, docname):
    """Reserved hook for doctree-level table processing.

    Currently a no-op.  Header row background colouring is handled by
    Sphinx's ``colorrows`` machinery (``\\sphinxTableRowColorHeader``),
    which works for all table types including longtable.

    Retained as an extension point — child themes can monkey-patch this
    function or register additional processors at adjacent priorities.

    Skipped if ``doxtr_enable_table_processor`` is False.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_table_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return
