"""LaTeX string escaping utilities.

This module provides functions for escaping strings for safe inclusion
in LaTeX output, handling all special characters that have meaning in LaTeX.
"""
from typing import Optional

__all__ = ['esc_latex', 'LATEX_ESCAPE_MAP']

# Constant mapping of LaTeX special characters to their escaped equivalents.
# Defined at module level to avoid rebuilding on every call.
LATEX_ESCAPE_MAP = {
    '\\': r'\textbackslash{}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    '_': r'\_',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '&': r'\&',
    '{': r'\{',
    '}': r'\}',
}


def esc_latex(s: Optional[str]) -> str:
    """Escape a string for safe inclusion in LaTeX output.

    Handles all LaTeX special characters including ~, ^, and backslash
    which were previously missing from the inline esc() closures.

    Args:
        s: The string to escape. Returns '' if None or empty.

    Returns:
        A LaTeX-safe string.
    """
    if not s:
        return ''
    # Use character-by-character replacement to avoid interference between
    # replacements that introduce LaTeX special characters (e.g., \textasciitilde{})
    result = []
    for ch in str(s):
        if ch == '\n':
            result.append(' ')
        elif ch in LATEX_ESCAPE_MAP:
            result.append(LATEX_ESCAPE_MAP[ch])
        else:
            result.append(ch)
    return ''.join(result).strip()
