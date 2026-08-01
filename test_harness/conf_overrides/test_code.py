"""
conf.py overrides for testing Code Blocks feature.

This file demonstrates the power of DYNAMIC ICON GENERATION using Python
functions in conf.py. Theme authors and users can create custom TikZ icons
that are generated at build time — no external image files needed!
"""

import os

# =============================================================================
# DYNAMIC TIKZ ICON GENERATORS
# =============================================================================
# These functions generate LaTeX/TikZ code at build time. They showcase:
# 1. Parametric color customization via hex values
# 2. LaTeX special character escaping
# 3. Inline TikZ graphics that render perfectly in PDF
# 4. Dynamic text labels derived from language names
# =============================================================================

def hex_to_rgb(hex_color):
    """Convert a hex color string to an (r, g, b) tuple (0-255)."""
    h = hex_color.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def tikz_rgb(hex_color):
    """Convert hex to native TikZ RGB color format with outer braces."""
    r, g, b = hex_to_rgb(hex_color)
    return f"{{rgb,255:red,{r};green,{g};blue,{b}}}"


def genos_shell_icon(shell_name, terminal_color='#61AFEF', shell_color='#FFFFFF'):
    """
    Generates a dynamic TikZ terminal prompt icon.
    
    Renders a bold '>' character followed by a tiny shell name with an underline,
    mimicking a shell prompt. Uses the Genos font for a technical look.
    
    Args:
        shell_name: Text to display (e.g., '#!/bin/bash', 'ZSH', 'PS1')
        terminal_color: Hex color for the '>' and underline
        shell_color: Hex color for the shell name text
    """
    term_rgb = tikz_rgb(terminal_color)
    shell_rgb = tikz_rgb(shell_color)
    
    # Safely escape LaTeX special characters in the display text
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


def language_badge_icon(text, bg_color='#306998', text_color='#FFFFFF', font='Montserrat'):
    """
    Generates a rounded-rectangle badge icon with custom text.
    
    Creates a small pill-shaped badge commonly used for language identifiers.
    Perfect for languages without a FontAwesome icon.
    
    Args:
        text: Short text label (e.g., 'Go', 'K', 'C++')
        bg_color: Background color of the badge
        text_color: Text color inside the badge
        font: Font family for the badge text
    """
    bg_rgb = tikz_rgb(bg_color)
    txt_rgb = tikz_rgb(text_color)
    
    # Escape LaTeX specials
    safe_text = (text
                 .replace('#', r'\#')
                 .replace('_', r'\_')
                 .replace('%', r'\%')
                 .replace('&', r'\&'))
    
    return (
        r"\tikz[baseline=-0.5ex]{"
        rf"\node[fill={bg_rgb}, rounded corners=2pt, inner sep=2pt, "
        rf"font=\fontsize{{5pt}}{{5pt}}\selectfont\fontspec{{{font}}}\bfseries, "
        rf"text={txt_rgb}]{{{safe_text}}};"
        r"}"
    )


def circle_icon(letter, bg_color='#306998', text_color='#FFFFFF'):
    """
    Generates a circular icon with a single character.
    
    Creates a small filled circle with a centered letter — similar to
    how many IDEs display file type indicators.
    
    Args:
        letter: Single character to display
        bg_color: Circle fill color
        text_color: Letter color
    """
    bg_rgb = tikz_rgb(bg_color)
    txt_rgb = tikz_rgb(text_color)
    
    return (
        r"\tikz[baseline=-0.5ex]{"
        rf"\node[circle, fill={bg_rgb}, inner sep=1.5pt, "
        rf"font=\fontsize{{5pt}}{{5pt}}\selectfont\bfseries\sffamily, "
        rf"text={txt_rgb}]{{{letter}}};"
        r"}"
    )


def gradient_badge_icon(text, left_color='#E44857', right_color='#7F52FF', text_color='#FFFFFF'):
    """
    Generates a badge with a horizontal gradient background.
    
    Uses TikZ shading for a modern gradient effect — perfect for
    languages with gradient branding (like Kotlin, Swift).
    
    Args:
        text: Short label text
        left_color: Left side of gradient
        right_color: Right side of gradient  
        text_color: Text color
    """
    left_rgb = tikz_rgb(left_color)
    right_rgb = tikz_rgb(right_color)
    txt_rgb = tikz_rgb(text_color)
    
    return (
        r"\tikz[baseline=-0.5ex]{"
        rf"\node[rounded corners=2pt, inner sep=2pt, "
        rf"left color={left_rgb}, right color={right_rgb}, "
        rf"font=\fontsize{{5pt}}{{5pt}}\selectfont\bfseries\sffamily, "
        rf"text={txt_rgb}]{{{text}}};"
        r"}"
    )


def powershell_icon(bg_color='#012456', chevron_color='#5391FE'):
    """
    Generates a PowerShell-style icon with a '>' chevron and underline.
    
    Mimics the official PowerShell logo shape: a right-pointing angle
    bracket above a horizontal baseline, all in Microsoft's blue palette.
    """
    bg_rgb = tikz_rgb(bg_color)
    chev_rgb = tikz_rgb(chevron_color)
    
    return (
        r"\tikz[baseline=-0.5ex]{"
        rf"\node[fill={bg_rgb}, rounded corners=2pt, inner sep=2pt, minimum width=1.2em, minimum height=1em] (box) {{}}; "
        rf"\draw[{chev_rgb}, line width=0.8pt] ([xshift=-1.5pt, yshift=1.5pt]box.center) -- ([xshift=1.5pt]box.center) -- ([xshift=-1.5pt, yshift=-1.5pt]box.center); "
        rf"\draw[{chev_rgb}, line width=0.6pt] ([xshift=2pt, yshift=-2pt]box.center) -- ([xshift=4pt, yshift=-2pt]box.center);"
        r"}"
    )


# =============================================================================
# CODE BLOCK CONFIGURATION
# =============================================================================
# This showcases how dynamic functions can generate per-language styling.
# The core provides sensible defaults; here we override with custom icons
# generated by the TikZ functions above.
# =============================================================================

doxtr_code = {
    'generic': {
        'border_width': '2pt',
        'show_mac_dots': False,
        'icon': r'\faIcon{code}',
        'icon_position': 'after_mac_dots',
        'title_background_color': '#183060',
        'title_font_color': '#78D8F0',
        'content_background_color': '#F8FAFF',
        'content_font_color': '#1A1A2E',
        'content_font': 'Iosevka',
        'border_color': '#78D8F0',
    },

    # --- Terminal Languages (mac dots enabled) ---

    'bash': {
        'show_mac_dots': True,
        'icon': genos_shell_icon('#!/bin/bash', terminal_color='#8AE234', shell_color='#D3D7CF'),
        'icon_position': 'before_mac_dots',
        'language_label': 'Bourne Again SHell',
        'title_background_color': '#2E3436',
        'title_font_color': '#8AE234',
        'border_color': '#555753',
    },

    'zsh': {
        'show_mac_dots': True,
        'icon': genos_shell_icon('ZSH', terminal_color='#BD93F9', shell_color='#F8F8F2'),
        'icon_position': 'before_mac_dots',
        'language_label': 'Zsh',
        'title_background_color': '#1A1A2E',
        'title_font_color': '#BD93F9',
        'border_color': '#44475A',
    },

    'sh': {
        'show_mac_dots': True,
        'icon': genos_shell_icon('sh', terminal_color='#8AE234', shell_color='#D3D7CF'),
        'icon_position': 'before_mac_dots',
        'title_background_color': '#2E3436',
        'title_font_color': '#8AE234',
        'border_color': '#555753',
    },

    'powershell': {
        'show_mac_dots': True,
        'icon': powershell_icon(bg_color='#012456', chevron_color='#5391FE'),
        'icon_position': 'before_mac_dots',
        'language_label': 'PowerShell',
        'title_background_color': '#012456',
        'title_font_color': '#5391FE',
        'border_color': '#012456',
    },

    # --- Programming Languages (custom dynamic icons) ---

    'python': {
        'icon': r'\faIcon{python}',
        'title_background_color': '#306998',
        'title_font_color': '#FFD43B',
        'icon_color': '#FFD43B',
        'border_color': '#306998',
    },

    'java': {
        'icon': r'\faIcon{java}',
        'title_background_color': '#5382A1',
        'title_font_color': '#F89820',
        'icon_color': '#F89820',
        'border_color': '#5382A1',
    },

    'kotlin': {
        'icon': gradient_badge_icon('K', left_color='#E44857', right_color='#7F52FF'),
        'title_background_color': '#7F52FF',
        'title_font_color': '#FFFFFF',
        'border_color': '#7F52FF',
    },

    'rust': {
        'icon': r'\faIcon{rust}',
        'title_background_color': '#282828',
        'title_font_color': '#DEA584',
        'icon_color': '#DEA584',
        'border_color': '#CE422B',
    },

    'c': {
        'icon': circle_icon('C', bg_color='#004283'),
        'title_background_color': '#004283',
        'title_font_color': '#FFFFFF',
        'border_color': '#004283',
    },

    'cpp': {
        'icon': language_badge_icon('C++', bg_color='#00599C'),
        'title_background_color': '#00599C',
        'title_font_color': '#FFFFFF',
        'border_color': '#00599C',
    },

    'csharp': {
        'icon': language_badge_icon('C#', bg_color='#68217A'),
        'title_background_color': '#68217A',
        'title_font_color': '#FFFFFF',
        'border_color': '#68217A',
        'language_label': r'C\#',
    },

    'go': {
        'icon': language_badge_icon('Go', bg_color='#00ADD8'),
        'title_background_color': '#00ADD8',
        'title_font_color': '#FFFFFF',
        'border_color': '#00ADD8',
        'language_label': 'GO',
    },

    # --- Web Languages ---

    'javascript': {
        'icon': r'\faIcon{js}',
        'title_background_color': '#323330',
        'title_font_color': '#F7DF1E',
        'icon_color': '#F7DF1E',
        'border_color': '#F7DF1E',
    },

    'typescript': {
        'icon': language_badge_icon('TS', bg_color='#3178C6'),
        'title_background_color': '#3178C6',
        'title_font_color': '#FFFFFF',
        'border_color': '#3178C6',
    },

    'html': {
        'icon': r'\faIcon{html5}',
        'title_background_color': '#E44D26',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#E44D26',
    },

    'css': {
        'icon': r'\faIcon{css3-alt}',
        'title_background_color': '#1572B6',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#1572B6',
    },

    # --- Data & Config Formats ---

    'json': {
        'icon': language_badge_icon('{}', bg_color='#292929', text_color='#F5A623'),
        'title_background_color': '#292929',
        'title_font_color': '#F5A623',
        'border_color': '#292929',
    },

    'yaml': {
        'icon': language_badge_icon('yml', bg_color='#4B3B60', text_color='#E8D0F0'),
        'title_background_color': '#4B3B60',
        'title_font_color': '#E8D0F0',
        'border_color': '#4B3B60',
    },

    'toml': {
        'icon': language_badge_icon('T', bg_color='#9C4121'),
        'title_background_color': '#9C4121',
        'title_font_color': '#FFFFFF',
        'border_color': '#9C4121',
    },

    'xml': {
        'icon': language_badge_icon('</>', bg_color='#0060AC', text_color='#F7931E'),
        'title_background_color': '#0060AC',
        'title_font_color': '#F7931E',
        'border_color': '#0060AC',
    },

    # --- Markup & Documentation ---

    'markdown': {
        'icon': r'\faIcon{markdown}',
        'title_background_color': '#083FA1',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#083FA1',
    },

    'rst': {
        'icon': r'\faIcon{file-code}',
        'title_background_color': '#1A5E2A',
        'title_font_color': '#FFFFFF',
        'icon_color': '#A0E8B0',
        'border_color': '#1A5E2A',
        'language_label': 'reStructuredText',
    },

    'latex': {
        'icon': language_badge_icon('TeX', bg_color='#008080'),
        'title_background_color': '#008080',
        'title_font_color': '#FFFFFF',
        'border_color': '#008080',
        'language_label': r'\LaTeX',
    },

    # --- Other ---

    'sql': {
        'icon': language_badge_icon('SQL', bg_color='#336791'),
        'title_background_color': '#336791',
        'title_font_color': '#FFFFFF',
        'border_color': '#336791',
    },

    'dockerfile': {
        'icon': r'\faIcon{docker}',
        'title_background_color': '#2496ED',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#2496ED',
        'language_label': 'Dockerfile',
    },

    'ruby': {
        'icon': circle_icon('R', bg_color='#CC342D'),
        'title_background_color': '#CC342D',
        'title_font_color': '#FFFFFF',
        'border_color': '#CC342D',
    },

    'php': {
        'icon': r'\faIcon{php}',
        'title_background_color': '#777BB4',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#777BB4',
    },

    'text': {
        'icon': r'\faIcon{file-alt}',
        'title_background_color': '#4A4A5A',
        'title_font_color': '#E0E0E0',
        'icon_color': '#E0E0E0',
        'border_color': '#4A4A5A',
        'language_label': 'Plain Text',
    },
}
