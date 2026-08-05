"""AST processor for custom styled container boxes.

This module handles the transformation of container nodes with registered
style classes into LaTeX tcolorbox environments.
"""
import re
from docutils import nodes
from sphinx.util import logging

from ..latex_escape import esc_latex
from ..core_config import VALID_RENDER_MODES, RenderMode, validate_render_mode

__all__ = ['process_containers_ast', 'resolve_container_class']

logger = logging.getLogger(__name__)

# Precompiled regex for performance - strips non-alpha characters for LaTeX-safe names
_RE_SAFE_NAME = re.compile(r'[^a-zA-Z]')


def resolve_container_class(class_name: str, mapping: dict, containers_conf: dict) -> tuple:
    """Resolve a container class through the mapping layer.

    Applies ``doxtr_container_mapping`` so that an RST class name can be
    transparently redirected to any registered container style without
    changing the source documents.

    Resolution order:
    1. Look up ``class_name`` in ``mapping`` to get ``resolved_name``
       (defaults to ``class_name`` itself when not mapped).
    2. If ``resolved_name`` exists in ``containers_conf``, return it.
    3. If the mapping redirected to a missing target:
       a. If the original ``class_name`` exists in ``containers_conf``, warn
          and return it.
       b. Otherwise warn once and fall back to ``'default'``.
    4. If there was no mapping entry and the class is not in ``containers_conf``,
       fall back to ``'default'`` with a warning.

    Args:
        class_name: The original CSS class from the RST document.
        mapping: The ``doxtr_container_mapping`` dict from ``conf.py``.
        containers_conf: The merged ``doxtr_containers`` config dict.

    Returns:
        Tuple of ``(resolved_style_name, style_config_dict)``.
    """
    resolved_name = mapping.get(class_name, class_name)

    # Step 1: resolved name exists directly
    if resolved_name in containers_conf:
        return (resolved_name, containers_conf[resolved_name])

    # Step 2: mapping pointed to an unknown target — try the original class
    if resolved_name != class_name:
        if class_name in containers_conf:
            logger.warning(
                f"[Doxtr Core] Container mapping '{class_name}' -> '{resolved_name}' "
                f"not found in doxtr_containers. Using original '{class_name}'."
            )
            return (class_name, containers_conf[class_name])
        else:
            # Both mapped target and original class are unknown — fall back to default
            # once, with a single clear message. Skip the Step 3 warning below to avoid
            # a confusing second log line that references resolved_name out of context.
            logger.warning(
                f"[Doxtr Core] Container mapping '{class_name}' -> '{resolved_name}' "
                f"not found in doxtr_containers. Falling back to 'default' style."
            )
            return ('default', containers_conf.get('default', {}))

    # Step 3: unmapped class not found in containers_conf — fall back to default
    if resolved_name != 'default':
        logger.warning(
            f"[Doxtr Core] Container '{resolved_name}' not found in doxtr_containers. "
            f"Falling back to 'default' style."
        )
    return ('default', containers_conf.get('default', {}))


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
    container_mapping = getattr(app.config, 'doxtr_container_mapping', {})
    if not containers_conf:
        return

    for node in list(doctree.traverse(nodes.container)):
        if node.get('doxtr_processed'):
            continue

        # Find the first class that either has a mapping entry or exists directly
        # in containers_conf. Mapped classes take priority so theme aliases work
        # even when the original name is not registered.
        match_class = next(
            (c for c in node.get('classes', []) if c in container_mapping or c in containers_conf),
            None,
        )
        if not match_class:
            continue
        node['doxtr_processed'] = True

        # Resolve through the mapping layer to get the final style name and config
        resolved_name, c_conf = resolve_container_class(match_class, container_mapping, containers_conf)
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
        # Use the resolved style name for the LaTeX environment so that the
        # mapped style's tcolorbox definition is used, not the original class name.
        safe_resolved_name = _RE_SAFE_NAME.sub('', resolved_name)

        render_mode = c_conf.get('render_mode', RenderMode.TCOLORBOX)

        # Defensive validation — config_inited should have already normalized this,
        # but themes may mutate config after config_inited runs.
        render_mode = validate_render_mode(render_mode, safe_resolved_name, logger)

        if render_mode == RenderMode.ENVIRONMENT:
            # Store title/icon in macros within a TeX group to prevent nested container collisions.
            # The \begingroup scopes \def so inner containers don't overwrite outer container values.
            # Emit explicit \ddContainerHasTitle boolean for robust empty-checking in templates.
            has_title_flag = '\\ddContainerHasTitletrue' if safe_title else '\\ddContainerHasTitlefalse'
            pre = (
                f'\\begingroup%\n'
                f'{has_title_flag}%\n'
                f'\\def\\ddContainerTitle{{{safe_title}}}%\n'
                f'\\def\\ddContainerIcon{{\\csname ddconticon{safe_resolved_name}\\endcsname}}%\n'
            )
            begin_args = ''
            post = '\\endgroup%\n'
        else:
            # Current tcolorbox behavior (unchanged)
            title_str = f"ddcontainertitlestyle{safe_resolved_name}, title={{\\csname ddconticon{safe_resolved_name}\\endcsname {safe_title}}}" if safe_title else "notitle"
            pre = ''
            begin_args = f'[{title_str}]'
            post = ''

        wrapper = nodes.container(classes=['doxtr-flat-container'])
        wrapper.append(nodes.raw('', f'\n{pre}\\begin{{ddcontainer{safe_resolved_name}}}{begin_args}\n', format='latex'))
        wrapper.extend(node.children)
        wrapper.append(nodes.raw('', f'\n\\end{{ddcontainer{safe_resolved_name}}}\n{post}', format='latex'))
        node.replace_self(wrapper)
