"""AST processor for epigraph/dictum formatting.

This module handles the transformation of epigraph block quotes into
KOMA-Script \\dictum commands for proper chapter/section preambles.
"""
from docutils import nodes

__all__ = ['process_epigraph_ast']


def process_epigraph_ast(app, doctree, docname):
    """Process epigraph block quotes and convert to KOMA-Script dictum.

    Transforms block_quote nodes with 'epigraph' class into LaTeX \\dictum
    commands, with special handling for chapter/part preambles.

    Args:
        app: The Sphinx application object.
        doctree: The doctree to process.
        docname: The name of the document being processed.
    """
    if getattr(app.builder, 'format', '') != 'latex':
        return
    
    toplevel = getattr(app.config, 'latex_toplevel_sectioning', None)
    if not toplevel:
        docclass = app.config.latex_docclass.get('manual', 'scrbook')
        toplevel = 'chapter' if docclass in ('scrbook', 'book', 'report') else 'section'
        
    for node in list(doctree.traverse(nodes.block_quote)):
        if 'epigraph' not in node.get('classes', []):
            continue
        if node.get('doxtr_processed'):
            continue
        node['doxtr_processed'] = True
        
        # Determine section depth
        depth = 0
        ancestor = node.parent
        while ancestor is not None and isinstance(ancestor, nodes.section):
            depth += 1
            ancestor = ancestor.parent
        
        if toplevel == 'part':
            type_map = {1: 'part', 2: 'chapter', 3: 'section', 4: 'subsection', 5: 'subsubsection'}
        else:
            type_map = {1: 'chapter', 2: 'section', 3: 'subsection', 4: 'subsubsection'}
        sec_type = type_map.get(depth, 'generic')
            
        # Check if this is a preamble epigraph (right after section title)
        is_preamble = False
        idx = -1
        parent = node.parent
        if isinstance(parent, nodes.section):
            idx = parent.children.index(node)
            if idx > 0 and isinstance(parent.children[idx - 1], nodes.title):
                is_preamble = True
                
        # Extract attribution if present
        attr = next((child for child in node if isinstance(child, nodes.attribution)), None)
        
        wrapper = nodes.container(classes=['doxtr-dictum'])
        if is_preamble and sec_type in ('part', 'chapter'):
            wrapper.append(nodes.raw('', f'\\set{sec_type}preamble[u]{{\n\\begingroup\n\\setupddepigraph{{{sec_type}}}\n', format='latex'))
        else:
            wrapper.append(nodes.raw('', f'\\begingroup\n\\setupddepigraph{{{sec_type}}}\n', format='latex'))
        
        if attr:
            node.remove(attr)
            wrapper.append(nodes.raw('', '\\dictum[{', format='latex'))
            for child in attr.children:
                if isinstance(child, nodes.paragraph):
                    wrapper.extend(child.children)
                else:
                    wrapper.append(child)
            wrapper.append(nodes.raw('', '}]{', format='latex'))
        else:
            wrapper.append(nodes.raw('', '\\dictum{', format='latex'))
        
        wrapper.extend(node.children)
        wrapper.append(nodes.raw('', '}\n\\endgroup\n', format='latex'))
        
        if is_preamble and sec_type in ('part', 'chapter'):
            wrapper.append(nodes.raw('', '}\n', format='latex'))
            parent.remove(node)
            parent.insert(idx - 1, wrapper)
        else:
            node.replace_self(wrapper)
