"""File registration utilities for LaTeX additional files.

This module provides safe file registration helpers that validate paths
before adding them to latex_additional_files.
"""
import os
from pathlib import Path
from sphinx.util import logging

__all__ = ['register_additional_file']

logger = logging.getLogger(__name__)


def register_additional_file(
    config,
    file_path: str,
    context: str = '',
) -> bool:
    """Safely add a file to latex_additional_files.

    Warns if the path looks absolute or points outside the project.
    Always appends to the additional files list so LaTeX can find the file
    in the build output directory.

    This function implements security best practices for file handling:
    - Warns about absolute paths outside the project root
    - Prevents duplicate entries
    - Logs for debugging

    Args:
        config: The Sphinx config object.
        file_path: The path provided in doxtr config.
        context: Human-readable context for warning messages (e.g., 'footer_logo').

    Returns:
        True if registered, False if skipped (empty path or already registered).

    Example:
        >>> register_additional_file(config, 'images/logo.png', 'footer logo')
        True
    """
    if not file_path or not isinstance(file_path, str):
        return False

    p = Path(file_path)

    # Warn if absolute path outside confdir/srcdir
    if p.is_absolute():
        conf_root = Path(config.confdir).resolve()
        try:
            p.resolve().relative_to(conf_root)
        except ValueError:
            ctx_str = f" ({context})" if context else ""
            logger.warning(
                f"[Doxtr Core]{ctx_str}: file path '{file_path}' is absolute "
                f"and outside the project root. This file will be copied to the "
                f"LaTeX build output. Verify this is intentional."
            )

    if file_path not in config.latex_additional_files:
        config.latex_additional_files.append(file_path)
        return True

    return False
