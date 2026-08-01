"""Utility functions for generating TikZ shell icons for doxtr code styling."""

from .utils import hex_to_rgb

# Explicit public API - prevents accidental re-export of hex_to_rgb
__all__ = ['make_shell_icon', 'micro_shell_icon', 'genos_shell_icon']


def make_shell_icon(shell_name):
    """Generates a dynamic TikZ >_ icon with the shell name floating above the underline."""
    return (
        r"\tikz[baseline=-0.6ex]{"
        r"\node[inner sep=0pt, font=\bfseries] (gt) {\textgreater}; "
        r"\node[inner sep=0pt, anchor=south west, font=\tiny\sffamily\bfseries, yshift=1pt] "
        r"(text) at ([xshift=2pt, yshift=0.2ex]gt.south east) {" + shell_name.upper() + r"}; "
        r"\draw[line width=1pt] ([yshift=-2pt]text.south west) -- ([yshift=-2pt]text.south east);"
        r"}"
    )


def micro_shell_icon(shell_name):
    """Generates an ultra-small dynamic TikZ >_ icon with precisely shifted underline."""
    return (
        r"\tikz[baseline=-0.6ex]{"
        # The '>' character
        r"\node[inner sep=0pt, font=\selectfont\fontspec{Genos}\bfseries] (gt) {\textgreater}; "
        # The shell text: using \fontsize{4pt}{4pt} for ultra-small text
        r"\node[inner sep=0pt, anchor=south west] "
        r"(text) at ([xshift=1pt]gt.south east) "
        r"{\fontsize{4.5pt}{4.5pt}\selectfont\fontspec{Genos}\bfseries " + shell_name.upper() + r"}; "
        # The underline: pushed exactly 1.5pt below the text baseline
        r"\draw[line width=0.1pt] ([yshift=-1pt]text.south west) -- ([yshift=-1pt]text.south east);"
        r"}"
    )


def genos_shell_icon(shell_name, terminal_color='#61AFEF', shell_color='#FFFFFF'):
    """
    Generates a dynamic TikZ icon. 
    Uses native TikZ RGB formats and safely escapes LaTeX reserved characters.
    """
    tr, tg, tb = hex_to_rgb(terminal_color)
    sr, sg, sb = hex_to_rgb(shell_color)
    
    # Natively format the colors so TikZ understands them perfectly
    term_rgb = f"{{rgb,255:red,{tr};green,{tg};blue,{tb}}}"
    shell_rgb = f"{{rgb,255:red,{sr};green,{sg};blue,{sb}}}"
    
    # Safely escape LaTeX special characters in the display text!
    safe_shell = (shell_name
                  .replace('#', r'\#')
                  .replace('_', r'\_')
                  .replace('%', r'\%')
                  .replace('&', r'\&'))
    
    return (
        r"\tikz[baseline=-0.6ex]{"
        rf"\node[inner sep=0pt, font=\bfseries, text={term_rgb}] (gt) {{\textgreater}}; "
        rf"\node[inner sep=0pt, anchor=south west, text={shell_rgb}] "
        r"(text) at ([xshift=2pt, yshift=0.3ex]gt.south east) "
        r"{\fontsize{4.5pt}{4.5pt}\selectfont\fontspec{Genos}\bfseries " + safe_shell + r"}; "
        rf"\draw[line width=0.6pt, draw={term_rgb}] ([yshift=-1.5pt]text.south west) -- ([yshift=-1.5pt]text.south east);"
        r"}"
    )
