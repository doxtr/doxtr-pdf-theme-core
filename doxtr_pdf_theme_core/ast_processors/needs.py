"""AST processor for sphinx-needs requirement boxes.

This module handles the transformation of sphinx-needs nodes into
styled LaTeX tcolorbox environments with metadata rendering.
"""
from docutils import nodes

from ..latex_escape import esc_latex

__all__ = ['process_needs_ast']


def _make_need_label(docname, label_id):
    """Build a single \\phantomsection\\label for a need ID.

    Uses \\detokenize to safely handle special LaTeX characters in
    docnames and IDs without requiring manual escaping.
    """
    qualified = f"{docname}:{label_id}" if docname else label_id
    return f"\\phantomsection\\label{{\\detokenize{{{qualified}}}}}"


def process_needs_ast(app, doctree, docname):
    """Process sphinx-needs nodes and wrap them in styled LaTeX environments.

    Transforms nodes with 'need' or 'need_node' classes into LaTeX
    doxtrneedboxrouter environments with proper metadata and content
    separation.  Emits docname-qualified ``\\label`` commands so that
    cross-document hyperref references resolve correctly.

    Skipped if ``doxtr_enable_needs_processor`` is False.

    Compatible with sphinx-needs 1.x through 8.x (reads ``_needs_all_needs``
    with fallback to the legacy ``needs_all_needs`` attribute).

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if not getattr(app.config, 'doxtr_enable_needs_processor', True):
        return
    if getattr(app.builder, 'format', '') != 'latex':
        return

    # Get the needs data dictionary (sphinx-needs 8.x uses _needs_all_needs)
    needs_data = getattr(app.env, '_needs_all_needs', None) or getattr(app.env, 'needs_all_needs', None) or {}

    for node in list(doctree.traverse(nodes.Element)):
        classes = node.get('classes', [])
        if 'need' not in classes and 'need_node' not in classes and node.tagname != 'need':
            continue
        if node.get('doxtr_processed'):
            continue
        for child in node.traverse(nodes.Element):
            child['doxtr_processed'] = True

        # Extract need ID
        node_ids = node.attributes.get('ids', [])
        nid = node_ids[0] if node_ids else None
        if not nid:
            for child in node.traverse(nodes.target):
                if child.get('ids'):
                    nid = child['ids'][0]
                    break
        if not nid:
            continue

        # Collect all IDs for label generation
        all_ids = []
        for n in node.traverse(nodes.Element):
            if 'ids' in n.attributes:
                all_ids.extend(n.attributes['ids'])
        unique_ids = list(dict.fromkeys(all_ids))
        if nid and f"needs:{nid}" not in unique_ids:
            unique_ids.append(f"needs:{nid}")

        # Determine need type
        need_type = 'generic'
        for c in node.get('classes', []):
            if c.startswith('needs_type_'):
                need_type = c[len('needs_type_'):].lower()
                break

        # Look up need metadata once for title, type, and docname
        need_info = needs_data.get(nid, {})
        title = need_info.get('title', '')
        if need_type == 'generic':
            need_type = need_info.get('type', 'generic').lower()

        safe_type = esc_latex(need_type)

        # Determine the docname for this need to generate properly qualified
        # LaTeX labels.  Sphinx's LaTeX writer prefixes all labels with
        # "docname:" via its curfilestack mechanism, but since we emit raw
        # LaTeX here we must do it ourselves.
        need_docname = need_info.get('docname', '') or ''  # guard against None stored as value
        labels_tex = "".join(
            _make_need_label(need_docname, i) for i in unique_ids
        )

        wrapper = nodes.container(classes=['doxtr-flat-need'])
        wrapper.append(nodes.raw('', f'\n{labels_tex}\n\\begin{{doxtrneedboxrouter}}{{{safe_type}}}{{{esc_latex(nid)}: {esc_latex(title)}}}\n', format='latex'))

        # Process metadata table
        metadata_table = next(iter(node.traverse(nodes.table)), None)
        if metadata_table:
            rows = list(metadata_table.traverse(nodes.row))
            if len(rows) > 0:
                meta_rows = rows[1:-1] if len(rows) > 2 else []
                content_row = rows[-1] if len(rows) > 1 else None
                
                for row in meta_rows:
                    entries = list(row.traverse(nodes.entry))
                    if len(entries) >= 2:
                        p = nodes.paragraph()
                        p.append(nodes.raw('', r'\needsmetakey{', format='latex'))
                        p.extend(entries[0].children)
                        p.append(nodes.raw('', r'} ', format='latex'))
                        p.extend(entries[1].children)
                        wrapper.append(p)
                    else:
                        for entry in entries:
                            for inline_node in list(entry.traverse(nodes.inline)):
                                if 'needs_label' in inline_node.get('classes', []):
                                    wrap = nodes.inline()
                                    wrap.append(nodes.raw('', r'\needsmetakey{', format='latex'))
                                    wrap.extend(inline_node.children)
                                    wrap.append(nodes.raw('', r'}', format='latex'))
                                    inline_node.replace_self(wrap)
                            p = nodes.paragraph()
                            p.extend(entry.children)
                            wrapper.append(p)
                
                if content_row:
                    wrapper.append(nodes.raw('', '\n\\doxtrneedcontentsep\n', format='latex'))
                    for entry in content_row.traverse(nodes.entry):
                        wrapper.extend(entry.children)

        wrapper.append(nodes.raw('', '\n\\end{doxtrneedboxrouter}\n', format='latex'))
        node.replace_self(wrapper)
