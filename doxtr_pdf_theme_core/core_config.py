"""
Doxtr Core - Default Configuration Settings
These dictionaries define the absolute base layer of the Three-Tier Merge Architecture.
Uncommented variables are the active Core Defaults. 
Commented variables show all possible options and their inheritance rules.

Never remove comments from a variable in the Core Config, as they explain the purpose and behavior of each setting. The comment can only be removed, if the variable is removed and no longer serves a purpose
in the theme.
"""

import os

from doxtr_pdf_theme_core.utils import adjust_hex_brightness, get_highest_contrast_color


def _code_bg(font_color, brand_color):
    """Calculate a WCAG AAA (7:1) contrast-safe title background from a brand color.
    
    The brand_color is used as the starting point, and is darkened/lightened
    until it achieves 7:1 contrast against the font_color. This ensures
    the language icon/text remains readable on the title bar.
    """
    return get_highest_contrast_color(font_color, brand_color, target='background', wcag_level=7)

THEME_DIR = os.path.abspath(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(THEME_DIR, 'assets')

DOXTR_GLOBALS = {
    # --- Basic PDF Geometry & Meta ---
    'show_release': True,               # Whether to show the release version on the title page
    'headsep': '8mm',                   # Space between header and text body
    'footskip': '10mm',                 # Space between text body and footer
    'headheight': '18pt',               # Height of the header line
    'footheight': '25pt',               # Height of the footer line
    
    # --- Lists & Indices ---
    'show_list_of_figures': True,       # Print List of Figures right before the Index
    'show_list_of_tables': True,        # Print List of Tables right before the Index
    'show_list_of_listings': True,      # Print List of Code Blocks right before the Index
    'appendix_chapter_numbering': True, # If True, chapters inside appendices are numbered A.1, A.2. If False, they are unnumbered.
    
    # --- Footer Logo ---
    'footer_logo': os.path.join(ASSETS_DIR, 'doxtr_icon_small.png'), # Path to an image file for the footer
    'footer_logo_height': '1.5em',                                     # Height of the footer logo
    
    # --- Global Font Families ---
    # Artful pairing: Spectral (readable serif body) + Montserrat (geometric sans) + FiraCode NF (ligature mono)
    'main_font': 'Spectral',            # Readable literary serif for body text
    'main_font_options': 'BoldFont={Spectral SemiBold}, ItalicFont={Spectral Italic}, BoldItalicFont={Spectral SemiBold Italic}',
    'sans_font': 'Montserrat',          # Clean geometric sans for UI elements
    'sans_font_options': '',             # fontspec options for sans font (e.g. 'Scale=MatchLowercase')
    'mono_font': 'FiraCode Nerd Font',  # Ligature-enabled monospace for code
    'mono_font_options': 'Scale=MatchLowercase',  # fontspec options for mono font (e.g. 'Scale=MatchLowercase')
    
    # --- Global Hierarchy Inheritance ---
    'inherit_all': True,                # If True, structural elements inherit missing styles from parent elements
    'inherit_font': True,               # E.g., chapter inherits part font, section inherits chapter font
    'inherit_color': True,              # E.g., chapter inherits part color
    'inherit_size': False,              # (False by default so sizes naturally cascade down)

    # --- Semantic Color System ---
    'page_background': '#FFFFFF',       # Page background for contrast calculations
    
    # --- WCAG Accessibility ---
    'wcag_level': 7,                  # Minimum contrast ratio (4.5 = AA, 7 = AAA). Applied to all contrast:fg/bg calculations.
    'wcag_color_debug': False,          # If True, prints input/output colors for every WCAG contrast calculation to the console during build. Useful for theme authors to verify corrections.
    
    # --- Custom File Resolution Paths (For Theme Authors) ---
    'container_title_style_path': '',   # Custom folder to search for container .tex_t templates
    'container_style_path': '',         # Custom folder for container body .tex_t templates
    'table_style_path': '',             # Custom folder for table .tex_t templates
    'figure_style_path': '',            # Custom folder for figure .tex_t templates
    'code_style_path': '',              # Custom folder for code block .tex_t templates
    'admonition_style_path': '',        # Custom folder for admonition .tex_t templates
    'need_style_path': '',              # Custom folder for sphinx-needs .tex_t templates
    'title_page_template_path': '',     # Custom folder for title page .tex_t templates
    'sidebar_style_path': '',            # Custom folder for sidebar .tex_t templates
    
    # --- Landscape Pages ---
    'landscape_package': 'pdflscape',   # Package for landscape pages: 'pdflscape', 'lscape', or '' to disable
}

DOXTR_TITLE_PAGE = {
    'template': 'default',              # Name of the .tex_t file to load for the cover
    'background_image_align': 'center', # 'center', 'top', 'bottom', 'left', 'right'
    'top_line': False,                  # Render Sphinx's default top black line
    'page_color': '#183060',            # Dark navy background from doxtr logo
    
    # --- Font Styling ---
    # Artful hierarchy: Rye (Western display) title, Comfortaa (rounded) subtitle, Josefin Sans author
    'title_font': 'Rye',               # Western display font for dramatic title
    'title_size': r'\fontsize{38pt}{44pt}\selectfont',
    'title_color': '#F0D890',           # Warm gold for high contrast on dark navy
    'subtitle_font': 'Comfortaa',       # Rounded futuristic for subtitle
    'subtitle_size': r'\fontsize{16pt}{20pt}\selectfont',
    'subtitle_color': '#78D8F0',        # Bright cyan accent
    'author_font': 'Josefin Sans',      # Modern geometric for author
    'author_size': r'\fontsize{14pt}{18pt}\selectfont',
    'author_color': '#90F0F0',          # Light cyan
    'date_font': 'Montserrat',          # Clean sans for date
    'date_size': r'\fontsize{11pt}{14pt}\selectfont',
    'date_color': '#F0D890',            # Warm gold
    'release_version_font': 'Comfortaa', # Rounded for version
    'release_version_size': r'\fontsize{11pt}{14pt}\selectfont',
    'release_version_color': '#F0C078', # Amber accent
    #
    # --- Additional options (theme authors can override) ---
    # 'title_font': '...',
    # 'title_size': '...',
    # 'title_color': '...',
    # 'subtitle_font': '...',
    # 'subtitle_size': '...',
    # 'subtitle_color': '...',
    # 'author_font': '...',
    # 'author_size': '...',
    # 'author_color': '...',
    # 'date_font': '...',
    # 'date_size': '...',
    # 'date_color': '...',
    # 'release_version_font': '...',
    # 'release_version_size': '...',
    # 'release_version_color': '...',
}

DOXTR_HEADINGS = {
    # Artful heading style: alternate alignment with margin numbers in Kranky font
    'align': 'alternate',               # Numbers alternate left/right based on page
    'numbers_in_margin': True,          # Push numbers into the margin
    'margin_space': '0em',              # No gap between title text and body edge
    
    # --- Level-Specific Overrides ---
    'part': {
        'font': 'Cinzel',               # Classical Roman capitals for parts
        'size': r'\fontsize{42pt}{48pt}\selectfont',
        'color': '#FFFFFF',             # White on dark background
        'align': 'center',              # Centered part titles
        'number_line': False,           # No decorative line on part pages
        'line_height': '10cm',          # Height of the part background block
        'background_color': '#183060',  # Deep navy from logo
        'epigraph_color': '#D8F0F0',    # Light cyan for epigraphs
        'epigraph_author_color': '#F0C078', # Warm amber for attribution
    },
    'chapter': {
        'font': 'Story Script',         # Hand-drawn script for chapter titles
        'size': r'\fontsize{26pt}{32pt}\selectfont',
        'color': '#183060',             # Deep navy
        'number_margin': True,          # Push chapter numbers into the margin
        'number_line': True,            # Render decorative structural line
        'line_height': '7cm',           # Length of the structural line
        'line_color': '#78D8F0',        # Bright cyan accent line
        'margin_space': '0.75em',       # Half spacing for chapter margin
        'number_font': 'Kranky',        # Quirky handwritten numbers
        'number_size': r'\fontsize{32pt}{38pt}\selectfont',
        'number_color': '#184878',      # Slightly lighter navy
    },
    'section': {
        'font': 'Cabin Sketch',         # Sketchy hand-drawn for sections
        'size': r'\fontsize{18pt}{22pt}\selectfont',
        'color': '#184878',             # Medium navy
        'number_margin': True,
        'number_line': False,
        'number_font': 'Kranky',        # Quirky handwritten numbers
        'number_size': r'\large\bfseries',
        'number_color': '#306090',      # Lighter blue
    },
    'subsection': {
        'font': 'Fredericka the Great', # Ornate engraved style
        'size': r'\fontsize{14pt}{18pt}\selectfont',
        'color': '#306090',             # Light blue
        'number_margin': True,
        'number_line': False,
        'number_font': 'Kranky',        # Quirky handwritten numbers
        'number_size': r'\normalsize',
        'number_color': '#306090',
    },
    'subsubsection': {
        'font': 'Montserrat',           # Clean geometric for deepest level
        'size': r'\fontsize{12pt}{16pt}\selectfont',
        'color': '#484860',             # Muted dark blue-grey
        'number_margin': True,
        'number_line': False,
        'number_font': 'Kranky',        # Quirky handwritten numbers
        'number_size': r'\normalsize\bfseries',
        'number_color': '#484860',
    },
}

DOXTR_PARTS = {
    'font': 'Cinzel',                   # Classical Roman capitals for part titles
    'size': r'\fontsize{48pt}{54pt}\selectfont',
    'color': '#FFFFFF',                 # White on dark background
    'part_number_font': 'Comfortaa',    # Rounded futuristic for "Part" prefix
    'part_number_size': r'\fontsize{24pt}{28pt}\selectfont',
    'part_number_color': '#78D8F0',     # Bright cyan
    'part_number_part_font': 'Comfortaa', # Rounded futuristic for "Part" word
    'part_number_part_size': r'\fontsize{18pt}{22pt}\selectfont',
    'part_number_part_color': '#78D8F0', # Bright cyan
    'part_number_number_font': 'Cinzel', # Classical for the number itself
    'part_number_number_size': r'\fontsize{36pt}{42pt}\selectfont',
    'part_number_number_color': '#F0D890', # Warm gold
    #
    # --- Specific Part Overrides (by index) ---
    # 1: {
    #     'appendix': True,              # If True, switches numbering from this part forward to Letters (Appendices)
    #     'image': 'wizard-of-docs.png', # Full page background image for Part 1
    #     'background_color': '#000',    # Color overlay (supports 8-digit hex for opacity like #00000088)
    #     'epigraph_color': '#FFF',      # Overrides the epigraph text color on this specific part
    #     'epigraph_author_color': '#CCC',
    #     'font': '...',                 # Overrides the global part font for Part 1
    #     'color': '...',                
    #     'size': '...',                 
    #     'number_font': '...',          # Overrides the global number font for Part 1
    #     # ... accepts all number_part and number_number overrides too
    # }
}

DOXTR_EPIGRAPHS = {
    # Artful epigraph styling with classical serif quotes and handwritten attribution
    'width': r'0.55\textwidth',
    'format': '— #1',                   # Classic em-dash attribution
    'align_box': 'right',
    'align_text': 'left',
    'align_author': 'right',
    
    # --- Styling ---
    'font': 'Cormorant Garamond',       # Classical serif for quote text
    'size': r'\itshape\large',
    'color': '#303048',                 # Dark blue-grey
    'author_font': 'Merienda',          # Whimsical script for attribution
    'author_size': r'\small',
    'author_color': '#184878',          # Medium navy
    #
    # --- Level-Specific Overrides ---
    # 'part': {
    #     'width': r'0.6\textwidth',    # Inherits from global epigraph width if not set
    #     'format': '~ #1',             # Inherits from global epigraph format if not set
    #     'align_box': 'right',         # Inherits from global epigraph align_box if not set
    #     'align_text': 'right',        # Inherits from global epigraph align_text if not set
    #     'align_author': 'right',      # Inherits from global epigraph align_author if not set
    #     'font': '...',                # Inherits from global epigraph font if not set
    #     # ... accepts all size/color/author overrides too
    # },
    # 'chapter': { ... },
    # 'section': { ... },
    # 'subsection': { ... },
    # 'subsubsection': { ... }
}

DOXTR_DRAFT = {
    'date_format': '%Y-%m-%d %H:%M:%S %Z', # Format for the {date} variable
    'timezone': 'local',                # Target timezone ('local', 'UTC', 'Europe/Berlin', etc.)
    'color': 'dd:#000000:lighten:40',   # Main text color (black) lightened 40% → gray
    'font_size': r'\normalsize',        # Same size as main body text
    'font': 'Offside',                   # Clean casual sans for watermark text
    
    # --- Activation ---
    # 'text': 'DRAFT - {date} - V: {project_version}', # Setting this activates the watermark
}

DOXTR_MICROTYPE = {
    'enabled': True,                    # Enable microtype (only active when draft mode is off)
    'protrusion': True,                 # Character protrusion (hanging punctuation)
    'expansion': True,                  # Font expansion (eliminates uneven word spacing)
    'kerning': False,                   # Fine kerning for character pairs (pdftex-only in older microtype)
    'stretch': 10,                      # Max stretch (percent)
    'shrink': 10,                       # Max shrink (percent)
    #
    # --- Compatibility note ---
    # kerning requires microtype >= 2.6a for LuaTeX support.
    # If your system has an older microtype package, leave kerning=False.
    # To enable: set 'kerning': True in your conf.py doxtr_microtype.
    #
    # --- Advanced options (theme authors can override) ---
    # 'hanging_punctuation': True,       # Hanging punctuation on both sides
    # 'finalkern': {},                   # Fine-tune character final kerning
    # 'wordkerning': True,               # Word-level kerning
}

DOXTR_CONTAINERS = {
    # --- Default Container ---
    'default': {
        'title': '',                     # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,              # If True, title is passed as raw LaTeX without escaping
        'style': 'default',
        'title_style': 'classic',
        'container_frame': True,
        'match_text_width': False,
        'title_icon': '',
        'title_font': 'Montserrat',
        'title_font_size': r'\large\bfseries',
        'title_color': 'dd:secondary',
        'title_font_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'title_icon_font_size': '',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': 'dd:secondary:contrast:fg:primary',
        'content_background_color': 'dd:secondary:lighten:85',
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    
    # --- Typewriter Container ---
    'typewriter': {
        'title': '',                     # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,              # If True, title is passed as raw LaTeX without escaping
        'style': 'default',
        'title_style': 'classic',
        'container_frame': False,
        'match_text_width': True,
        'title_icon': r'\faIcon{keyboard}',
        'title_font': 'Special Elite',
        'title_font_size': r'\normalsize\bfseries',
        'title_color': '#484848',
        'title_font_color': '#F0F0E8',
        'title_icon_color': '#F0D890',
        'title_icon_font_size': '',
        'content_font': 'Special Elite',
        'content_font_size': r'\normalsize',
        'content_font_color': '#2A2A2A',
        'content_background_color': '',
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    
    # --- Highlight Section Container ---
    'highlight-section': {
        'title': '',                     # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,              # If True, title is passed as raw LaTeX without escaping
        'style': 'default',
        'title_style': 'classic',
        'container_frame': False,
        'match_text_width': False,
        'title_icon': r'\faIcon{star}',
        'title_font': 'Montserrat',
        'title_font_size': r'\large\bfseries',
        'title_color': '#183060',
        'title_font_color': '#FFFFFF',
        'title_icon_color': '#F0D890',
        'title_icon_font_size': '',
        'content_font': 'Overlock',
        'content_font_size': r'\normalsize',
        'content_font_color': '#183060',
        'content_background_color': '#DF9568',
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    
    # --- Alice Container ---
    # A participant container with the 'Alice' font for a whimsical, storybook feel.
    # Demonstrates how to override the title font for a specific container.
    'alice': {
        'title': 'Alice',                # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,              # If True, title is passed as raw LaTeX without escaping
        'style': 'participant',          # Uses the participant.tex_t body template
        'title_style': 'classic',        # Not used by participant style (has its own title rendering)
        'container_frame': True,
        'match_text_width': False,
        'title_icon': r'\faIcon{user}',
        'title_font': 'Alice',           # Whimsical 'Alice' font for the title
        'title_font_size': r'\bfseries',
        'title_color': '#2A6B8B',        # Teal blue
        'title_font_color': '#FFFFFF',
        'title_icon_color': '#90F0F0',
        'title_icon_font_size': '',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': '#1A3A4A',
        'content_background_color': '#F0FCFF',
        'before_skip': '2mm',
        'after_skip': '2mm',
        # --- Participant style-specific options ---
        'frame_width': '0.2mm',          # Border thickness
        'frame_arc': '0mm',              # Corner radius of content box (0mm = sharp corners)
        'title_position': 'left',        # Title badge position: 'left', 'center', 'right', or a LaTeX dimension
        'title_xshift': '1cm',           # Additional horizontal offset from the base position
        'title_max_width': '-3cm',       # varwidth constraint for title pill
    },
    
    # --- Bob Container ---
    # A participant container with a Wild West theme using the 'Rye' font.
    # Demonstrates themed color overrides for a distinct visual style.
    'bob': {
        'title': 'Bob',                  # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,              # If True, title is passed as raw LaTeX without escaping
        'style': 'participant',          # Uses the participant.tex_t body template
        'title_style': 'classic',        # Not used by participant style (has its own title rendering)
        'container_frame': True,
        'match_text_width': False,
        'title_icon': r'\faIcon{hat-cowboy}',  # Cowboy hat icon for Wild West theme
        'title_font': 'Rye',             # Western-style 'Rye' font for the title
        'title_font_size': r'\bfseries',
        'title_color': '#8B4513',        # Saddle brown — classic Western leather
        'title_font_color': '#FFF8DC',   # Cornsilk — parchment/wanted poster feel
        'title_icon_color': '#DAA520',   # Goldenrod — sheriff badge gold
        'title_icon_font_size': '',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': '#3E2723',  # Dark brown — aged paper ink
        'content_background_color': '#FAEBD7',  # Antique white — weathered parchment
        'before_skip': '2mm',
        'after_skip': '2mm',
        # --- Participant style-specific options ---
        'frame_width': '0.3mm',          # Slightly thicker border for rugged look
        'frame_arc': '0mm',              # Sharp corners
        'title_position': 'right',       # Title badge position: 'left', 'center', 'right', or a LaTeX dimension
        'title_xshift': '-1cm',          # Additional horizontal offset from the base position (negative to pull inward)
        'title_max_width': '-3cm',       # varwidth constraint for title pill
    },
    
    # --- Folder Container ---
    # A folder-shaped container with a tab extending from the top-right corner.
    # The title is displayed inside the tab. Features a drop fuzzy shadow for depth.
    'folder': {
        'title': 'Background Information',  # Static title text (shown when no :title: is given in RST; empty = notitle)
        'title_raw': False,                 # If True, title is passed as raw LaTeX without escaping
        'style': 'folder',                  # Uses the folder.tex_t body template
        'title_style': 'classic',           # Not actively used (folder has its own title via tab)
        'container_frame': True,
        'match_text_width': False,
        'title_icon': '',
        'title_font': '',                   # Font for the title tab (empty = inherit sans)
        'title_font_size': r'\small\sffamily',  # Small sans-serif title in tab
        'title_color': '#808080',           # Frame/border color (gray)
        'title_font_color': '#000000',      # Title text color inside the tab
        'title_background_color': '#FFFFFF', # Tab background color
        'title_icon_color': '',
        'title_icon_font_size': '',
        'content_font': '',                 # Content font (empty = inherit)
        'content_font_size': r'\normalsize',
        'content_font_color': '#000000',    # Content text color
        'content_background_color': '#FFFFFF', # Content area background
        'border_width': '0.4pt',            # Frame line thickness
        # --- Shadow ---
        'show_shadow': True,                # Show drop fuzzy shadow
        'shadow_color': '#C0C0C0',          # Shadow color (light gray)
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
}

DOXTR_TABLES = {
    # Navy-themed tables with alternating rows
    'generic': {
        'style': 'default',
        'title_style': 'classic',
        'caption_position': 'side',
        'caption_top_offset': '-0.5ex',
        'title_padding': '1.5ex',
        'title_text_offset': '0pt',
        'title_fade_dots': False,
        'title_background_fade_mask_color': '#FFFFFF',
        'title_background_fade_length': '1.5ex',
        'title_background_fade_shape': 'rectangle',
        'header_background_color': '#183060',          # Deep navy from logo
        'header_font_color': '#FFFFFF',
        'header_font': 'Montserrat',
        'header_font_size': r'\bfseries',
        'row_color_odd': '#F8FAFF',                    # Very light blue tint
        'row_color_even': '#FFFFFF',
        'title_background_color': '#184878',           # Slightly lighter navy
        'title_font_color': '#FFFFFF',
        'title_font': 'Montserrat',
        'title_font_size': r'\bfseries',
    }
}

DOXTR_FIGURES = {
    # Light blue figure captions
    'generic': {
        'style': 'default',
        'caption_background_color': '#F0F8FF',         # Very light blue
        'caption_font_color': '#183060',               # Deep navy
        'caption_font': 'Montserrat',
        'caption_font_size': r'\small\sffamily\bfseries',
        'caption_padding': '1.5ex',
        'caption_align': 'center',
    }
}

DOXTR_CODE = {
    # Code blocks with navy title bar and per-language color overrides.
    # Icons use FontAwesome 5 brand glyphs where available, or TikZ mini-badges for others.
    # Terminal-associated languages (sh, bash, zsh, powershell) show mac dots; others do not.
    'generic': {
        'style': 'default',
        'border_width': '0.8pt',
        'show_mac_dots': False,
        'language_label': '',
        'icon': r'\faIcon{code}',
        'icon_position': 'after_mac_dots',
        'title_background_color': '#183060',
        'title_font_color': '#78D8F0',
        'title_font_size': r'\small\sffamily\bfseries',
        'title_font': 'Montserrat',
        'icon_color': '#78D8F0',
        'icon_size': '',
        'content_background_color': '#F8FAFF',
        'content_font_color': '#1A1A2E',
        'content_font_size': r'\small',
        'content_font': 'FiraCode Nerd Font',
        'border_color': '#78D8F0',
    },

    # --- Python: Official blue/gold brand ---
    'python': {
        'icon': r'\faIcon{python}',
        'title_background_color': '#306998',
        'title_font_color': '#FFD43B',
        'icon_color': '#FFD43B',
        'border_color': '#306998',
    },

    # --- Java: Steel blue/orange brand ---
    'java': {
        'icon': r'\faIcon{java}',
        'title_background_color': '#5382A1',
        'title_font_color': '#F89820',
        'icon_color': '#F89820',
        'border_color': '#5382A1',
    },

    # --- Kotlin: Purple/white brand ---
    'kotlin': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{K};}',
        'title_background_color': _code_bg('#FFFFFF', '#7F52FF'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#7F52FF',
    },

    # --- Rust: Charcoal/copper brand ---
    'rust': {
        'icon': r'\faIcon{rust}',
        'title_background_color': '#282828',
        'title_font_color': '#DEA584',
        'icon_color': '#DEA584',
        'border_color': '#CE422B',
    },

    # --- C: ISO blue brand ---
    'c': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{C};}',
        'title_background_color': _code_bg('#FFFFFF', '#004283'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#004283',
    },

    # --- C++: ISO blue brand (slightly lighter than C) ---
    'cpp': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{C\raisebox{0.3ex}{\scalebox{0.6}{++}}};}',
        'title_background_color': _code_bg('#FFFFFF', '#00599C'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#00599C',
    },

    # --- C#: Microsoft purple brand ---
    'csharp': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{C\#};}',
        'title_background_color': _code_bg('#FFFFFF', '#68217A'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#68217A',
        'language_label': r'C\#',
    },

    # --- Go: Cyan brand ---
    'go': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{Go};}',
        'title_background_color': _code_bg('#FFFFFF', '#00ADD8'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#00ADD8',
        'language_label': 'GO',
    },

    # --- reStructuredText: Sphinx green brand ---
    'rst': {
        'icon': r'\faIcon{file-code}',
        'title_background_color': '#1A5E2A',
        'title_font_color': '#FFFFFF',
        'icon_color': '#A0E8B0',
        'border_color': '#1A5E2A',
        'language_label': 'reStructuredText',
    },

    # --- Shell (sh): Terminal dark/green — mac dots enabled ---
    'sh': {
        'show_mac_dots': True,
        'icon': r'\faIcon{terminal}',
        'title_background_color': '#2E3436',
        'title_font_color': '#8AE234',
        'icon_color': '#8AE234',
        'border_color': '#555753',
    },

    # --- Bash: Terminal dark/green — mac dots enabled ---
    'bash': {
        'show_mac_dots': True,
        'icon': r'\faIcon{terminal}',
        'title_background_color': '#2E3436',
        'title_font_color': '#8AE234',
        'icon_color': '#8AE234',
        'border_color': '#555753',
        'language_label': 'Bash',
    },

    # --- Zsh: Dark/purple terminal — mac dots enabled ---
    'zsh': {
        'show_mac_dots': True,
        'icon': r'\faIcon{terminal}',
        'title_background_color': '#1A1A2E',
        'title_font_color': '#BD93F9',
        'icon_color': '#BD93F9',
        'border_color': '#44475A',
        'language_label': 'Zsh',
    },

    # --- PowerShell: Microsoft blue brand — mac dots enabled ---
    'powershell': {
        'show_mac_dots': True,
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw={rgb,255:red,83;green,145;blue,254}, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text={rgb,255:red,83;green,145;blue,254}]{PS};}',
        'title_background_color': '#012456',
        'title_font_color': '#5391FE',
        'icon_color': '#5391FE',
        'border_color': '#012456',
        'language_label': 'PowerShell',
    },

    # --- Markdown: Blue brand ---
    'markdown': {
        'icon': r'\faIcon{markdown}',
        'title_background_color': '#083FA1',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#083FA1',
    },

    # --- HTML: Orange brand ---
    'html': {
        'icon': r'\faIcon{html5}',
        'title_background_color': '#E44D26',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#E44D26',
    },

    # --- CSS: Blue brand ---
    'css': {
        'icon': r'\faIcon{css3-alt}',
        'title_background_color': '#1572B6',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#1572B6',
    },

    # --- JavaScript: Dark/yellow brand ---
    'javascript': {
        'icon': r'\faIcon{js}',
        'title_background_color': '#323330',
        'title_font_color': '#F7DF1E',
        'icon_color': '#F7DF1E',
        'border_color': '#F7DF1E',
    },

    # --- TypeScript: Blue brand ---
    'typescript': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{TS};}',
        'title_background_color': _code_bg('#FFFFFF', '#3178C6'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#3178C6',
    },

    # --- Plain text: Neutral grey ---
    'text': {
        'icon': r'\faIcon{file-alt}',
        'title_background_color': '#4A4A5A',
        'title_font_color': '#E0E0E0',
        'icon_color': '#E0E0E0',
        'border_color': '#4A4A5A',
        'language_label': 'Plain Text',
    },

    # --- JSON: Dark/gold data format ---
    'json': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw={rgb,255:red,245;green,166;blue,35}, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text={rgb,255:red,245;green,166;blue,35}]{\{\}};}',
        'title_background_color': _code_bg('#F5A623', '#292929'),
        'title_font_color': '#F5A623',
        'icon_color': '#F5A623',
        'border_color': '#292929',
    },

    # --- YAML: Purple/lavender data format ---
    'yaml': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw={rgb,255:red,232;green,208;blue,240}, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text={rgb,255:red,232;green,208;blue,240}]{yml};}',
        'title_background_color': _code_bg('#E8D0F0', '#4B3B60'),
        'title_font_color': '#E8D0F0',
        'icon_color': '#E8D0F0',
        'border_color': '#4B3B60',
    },

    # --- SQL: PostgreSQL steel-blue brand ---
    'sql': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{SQL};}',
        'title_background_color': _code_bg('#FFFFFF', '#336791'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#336791',
    },

    # --- XML: Blue/orange markup ---
    'xml': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw={rgb,255:red,247;green,147;blue,30}, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text={rgb,255:red,247;green,147;blue,30}]{</>};}',
        'title_background_color': _code_bg('#F7931E', '#0060AC'),
        'title_font_color': '#F7931E',
        'icon_color': '#F7931E',
        'border_color': '#0060AC',
    },

    # --- LaTeX/TeX: Teal typesetting brand ---
    'latex': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[fill={rgb,255:red,0;green,128;blue,128}, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{\TeX};}',
        'title_background_color': '#008080',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#008080',
        'language_label': r'\LaTeX',
    },

    # --- Dockerfile: Docker blue brand ---
    'dockerfile': {
        'icon': r'\faIcon{docker}',
        'title_background_color': '#2496ED',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#2496ED',
        'language_label': 'Dockerfile',
    },

    # --- TOML: Warm brown config format ---
    'toml': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{T};}',
        'title_background_color': _code_bg('#FFFFFF', '#9C4121'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#9C4121',
    },

    # --- INI: Neutral grey config format ---
    'ini': {
        'icon': r'\faIcon{cogs}',
        'title_background_color': '#5A5A6A',
        'title_font_color': '#E8E8F0',
        'icon_color': '#E8E8F0',
        'border_color': '#5A5A6A',
    },

    # --- Ruby: Red brand ---
    'ruby': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{rb};}',
        'title_background_color': _code_bg('#FFFFFF', '#CC342D'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#CC342D',
    },

    # --- PHP: Purple brand ---
    'php': {
        'icon': r'\faIcon{php}',
        'title_background_color': '#777BB4',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#777BB4',
    },

    # --- Lua: Navy/white brand ---
    'lua': {
        'icon': r'\tikz[baseline=-0.5ex]{\node[draw=white, line width=0.4pt, rounded corners=2pt, inner sep=1.5pt, font=\tiny\bfseries\sffamily, text=white]{Lua};}',
        'title_background_color': _code_bg('#FFFFFF', '#000080'),
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#000080',
    },

    # --- Swift: Orange brand ---
    'swift': {
        'icon': r'\faIcon{swift}',
        'title_background_color': '#F05138',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#F05138',
    },

    # --- Makefile: Build-system grey ---
    'make': {
        'icon': r'\faIcon{cogs}',
        'title_background_color': '#6D8086',
        'title_font_color': '#FFFFFF',
        'icon_color': '#FFFFFF',
        'border_color': '#6D8086',
        'language_label': 'Makefile',
    },
}

DOXTR_ADMONITIONS = {
    # Artful admonitions with distinct colors per type and explicit dark content text
    'generic': {
        'style': 'default',
        'title_icon': r'\faIcon{info-circle}',
        'title_icon_padding': '3ex',
        'title_decoration_spacing': '2mm',
        'title_background_color': '#184878',
        'title_icon_box_background_color': '#183060',
        'title_font_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'title_font_size': r'\large\bfseries',
        'title_font': 'Montserrat',
        'content_background_color': '#F0F8FF',
        'content_background_color_nested': '#FFFFFF',
        'content_font_color': '#1A1A2E',
        'content_font_size': r'\normalsize',
        'content_font': 'Spectral',
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    'note': {
        'title_icon': r'\faIcon{bookmark}',
        'title_background_color': '#2060A0',
        'title_icon_box_background_color': '#184878',
        'content_background_color': '#EEF5FC',
        'content_font_color': '#1A1A2E',
    },
    'tip': {
        'title_icon': r'\faIcon{lightbulb}',
        'title_background_color': '#2A8B5E',
        'title_icon_box_background_color': '#1E6B48',
        'content_background_color': '#EEFBF3',
        'content_font_color': '#1A1A2E',
    },
    'hint': {
        'title_icon': r'\faIcon{hand-point-right}',
        'title_background_color': '#3AAA7A',
        'title_icon_box_background_color': '#2A8B5E',
        'content_background_color': '#F0FDF6',
        'content_font_color': '#1A1A2E',
    },
    'important': {
        'title_icon': r'\faIcon{exclamation}',
        'title_background_color': '#7848A8',
        'title_icon_box_background_color': '#5C3090',
        'content_background_color': '#F8F0FF',
        'content_font_color': '#1A1A2E',
    },
    'warning': {
        'title_icon': r'\faIcon{exclamation-triangle}',
        'title_background_color': '#D48030',
        'title_icon_box_background_color': '#B06820',
        'title_font_color': '#FFFFFF',
        'content_background_color': '#FFF8F0',
        'content_font_color': '#1A1A2E',
    },
    'caution': {
        'title_icon': r'\faIcon{radiation}',
        'title_background_color': '#E09040',
        'title_icon_box_background_color': '#C07828',
        'title_font_color': '#FFFFFF',
        'content_background_color': '#FFFAF2',
        'content_font_color': '#1A1A2E',
    },
    'danger': {
        'title_icon': r'\faIcon{skull-crossbones}',
        'title_background_color': '#C83030',
        'title_icon_box_background_color': '#A02020',
        'title_font_color': '#FFFFFF',
        'title_font': 'Permanent Marker',
        'title_font_size': r'\large',
        'content_background_color': '#FFF0F0',
        'content_font_color': '#1A1A2E',
    },
    'error': {
        'title_icon': r'\faIcon{bug}',
        'title_background_color': '#D04848',
        'title_icon_box_background_color': '#B83838',
        'title_font_color': '#FFFFFF',
        'content_background_color': '#FFF2F2',
        'content_font_color': '#1A1A2E',
    },
    'attention': {
        'title_icon': r'\faIcon{bell}',
        'title_background_color': '#E8A020',
        'title_icon_box_background_color': '#C88818',
        'title_font_color': '#183060',
        'content_background_color': '#FFFCF0',
        'content_font_color': '#1A1A2E',
    },
    'seealso': {
        'title_icon': r'\faIcon{external-link-alt}',
        'title_background_color': '#4890C8',
        'title_icon_box_background_color': '#3078B0',
        'content_background_color': '#F0F8FF',
        'content_font_color': '#1A1A2E',
    },
}

DOXTR_HIGHLIGHTS = {
    # Highlights styling — used for the RST `.. highlights::` directive.
    # Highlights are rendered as accent-bordered boxes with a bold title,
    # replacing Sphinx's default quote indentation.
    'style': 'default',                     # Name of the .tex_t file to load
    'title_text': 'Highlights',             # Title text displayed at the top of the box
    'title_icon': '',                        # Optional icon before title (e.g., r'\faIcon{star}')
    'title_font': 'Montserrat',             # Title font family
    'title_font_size': r'\large\bfseries', # Title font size/weight
    'title_font_color': '#8B6914',          # Title text color (dark golden)
    'border_color': '#8B6914',              # Left border accent color (dark golden)
    'border_width': '3pt',                  # Left border width
    'content_font': '',                     # Content body font (empty = inherit)
    'content_font_size': r'\normalsize',   # Content body font size
    'content_font_color': '#1A1A2E',        # Content text color
    'content_background_color': '#FFF8DC',  # Content area background (light yellow/cream)
    'before_skip': '1.5em plus 0.5em minus 0.5em',  # Space before box
    'after_skip': '1.5em plus 0.5em minus 0.5em',   # Space after box
}

DOXTR_SIDEBAR = {
    # Sidebar styling — used for the RST `.. sidebar::` directive.
    # Sidebars are rendered as floating/inset boxes alongside main content.
    'style': 'default',                     # Name of the .tex_t file to load
    'width': r'0.4\textwidth',              # Box width (40% of text width — leaves 60% for flowing text)
    'float_position': 'R',                  # Wrapfig placement: UPPERCASE = exact placement (no float). 'I' = inner margin (left on odd, right on even), 'O' = outer, 'L' = left, 'R' = right. Lowercase allows LaTeX to reposition.
    'border_radius': '4pt',                  # Corner radius for top corners
    'border_width': '0.8pt',                 # Frame border width
    'border_color': '#184878',               # Frame border color
    'title_icon': r'\faIcon{columns}',       # Icon before sidebar title
    'title_font': 'Montserrat',              # Title font family
    'title_font_size': r'\large\bfseries',   # Title font size/weight
    'title_background_color': '#184878',     # Title bar background
    'title_font_color': '#FFFFFF',           # Title text color
    'title_icon_color': '#78D8F0',           # Title icon color
    'subtitle_font': 'Montserrat',           # Subtitle font family
    'subtitle_font_size': r'\small\itshape', # Subtitle font size/style
    'subtitle_font_color': '#306090',        # Subtitle text color
    'content_font': 'Spectral',              # Content body font
    'content_font_size': r'\small',          # Content body font size
    'content_font_color': '#1A1A2E',         # Content text color
    'content_background_color': '#F0F8FF',   # Content area background
    'before_skip': '1.5em plus 0.5em minus 0.5em',  # Space before sidebar
    'after_skip': '1.5em plus 0.5em minus 0.5em',   # Space after sidebar
}

DOXTR_NEEDS = {
    'generic': {
        'style': 'default',
        'segmentation_style': 'solid',
        'title_vertical_position': 'middle',
        'title_icon_raise': '0pt',
        'title_icon_raise_offset': '0pt',
        'title_icon': r'\faIcon{clipboard-check}',
        'title_background_color': '#184878',
        'title_font_color': '#FFFFFF',
        'title_color': '#FFFFFF',
        'title_font_size': r'\large\bfseries',
        'title_font': 'Montserrat',
        'title_icon_color': '#FFFFFF',
        'title_icon_size': '',
        'segmentation_color': '#184878',
        'metadata_background_color': '#E8F4FC',
        'metadata_key_color': '#183060',
        'metadata_key_font_size': r'\bfseries',
        'metadata_key_font': 'Montserrat',
        'metadata_font_color': '#183060',
        'metadata_font_size': r'\small',
        'metadata_font': 'Montserrat',
        'content_background_color': '#FFFFFF',
        'content_font_color': '#1A1A2E',
        'content_font_size': r'\normalsize',
        'content_font': 'Spectral',
        'before_skip': '1.5em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em'
    },
    
    # --- Custom Need Overrides (using semantic color palette) ---
    'req': {
        'title_background_color': 'dd:secondary',     # Teal blue
        'title_font_color': '#FFFFFF',                # White on teal
        'title_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'segmentation_color': 'dd:secondary',
        'metadata_background_color': 'dd:secondary:lighten:85',
        'metadata_key_color': 'dd:secondary',
        'metadata_font_color': 'dd:secondary:darken:30',
    },
    'spec': {
        'title_background_color': 'dd:info',          # Medium blue
        'title_font_color': '#FFFFFF',
        'title_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'segmentation_color': 'dd:info',
        'metadata_background_color': 'dd:info:lighten:85',
        'metadata_key_color': 'dd:info',
        'metadata_font_color': 'dd:info:darken:30',
    },
    'decision': {
        'title_background_color': 'dd:success',       # Teal-green
        'title_font_color': '#FFFFFF',
        'title_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'segmentation_color': 'dd:success',
        'metadata_background_color': 'dd:success:lighten:85',
        'metadata_key_color': 'dd:success',
        'metadata_font_color': 'dd:success:darken:30',
    },
    'risk': {
        'title_background_color': 'dd:danger',        # Muted red
        'title_font_color': '#FFFFFF',
        'title_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'segmentation_color': 'dd:danger',
        'metadata_background_color': 'dd:danger:lighten:85',
        'metadata_key_color': 'dd:danger',
        'metadata_font_color': 'dd:danger:darken:30',
    },
}

# --- Semantic Color System ---
# Define 6 key palette colors. All other colors derive from these via
# dynamic expressions (dd: prefix) in the configuration.
DOXTR_SEMANTIC_PALETTE = {
    # Semantic color palette derived from the doxtr logo (doxtr-logo-color-round.png).
    # The logo features a deep navy-to-teal gradient with bright cyan and warm amber accents.
    # All other colors in the theme derive from these 6 palette colors via dd: expressions.
    'primary':   '#183060',   # Deep navy (#183060) — structural, headings, borders
    'secondary': '#78D8F0',   # Bright cyan (#78D8F0) — accents, highlights, active states
    'info':      '#60D8F0',   # Lighter cyan (#60D8F0) — info, notes, specs
    'success':   '#66D98E',   # Fresh green (#66D98E) — hints, tips, decisions
    'warning':   '#F0A860',   # Warm amber (#F0A860) — warnings, caution
    'danger':    '#E05050',   # Clear red (#E05050) — danger, error, risk
    'page':      '#FFFFFF',   # Default page background for contrast calculations
}

# --- Table of Contents Styling ---
DOXTR_TOC = {
    # --- TOC Title ---
    'title_font': None,                  # Font for the "Contents" heading (None = inherit)
    'title_size': None,                  # Size for the "Contents" heading
    'title_color': None,                 # Color for "Contents" heading
    
    # --- Chapter-level entries ---
    'chapter_font': None,
    'chapter_size': r'\large',
    'chapter_color': None,               # dd: expressions supported
    'chapter_bold': True,
    
    # --- Section-level entries ---
    'section_font': None,
    'section_size': r'\normalsize',
    'section_color': None,
    
    # --- Subsection/subsubsection ---
    'subsection_font': None,
    'subsection_size': r'\small',
    'subsection_color': None,
    
    # --- Dot leaders ---
    'dot_leader_color': None,            # Color of ....... leaders
    'dot_leader_char': r'\normalfont.',  # Character used as leader
    
    # --- Page numbers ---
    'page_number_font': None,
    'page_number_color': None,
}

# --- Bibliography/Citation Styling ---
DOXTR_BIBLIOGRAPHY = {
    'title_font': None,
    'title_size': None,
    'title_color': None,
    'entry_font': None,
    'entry_size': None,
    'entry_color': None,
    'label_color': None,               # Color of [AuthorYear] citation labels
    'label_font': None,
}

# --- Index Styling ---
DOXTR_INDEX = {
    'title_font': None,
    'title_size': None,
    'title_color': None,
    'entry_font': None,
    'entry_size': None,
    'subentry_font': None,
    'subentry_size': None,
    'letter_group_font': None,          # The A, B, C group headers in the index
    'letter_group_color': None,
}

# --- Glossary Styling ---
DOXTR_GLOSSARY = {
    'term_font': None,
    'term_size': None,
    'term_color': None,                 # Color of glossary terms
    'definition_font': None,
    'definition_size': None,
    'definition_color': None,
    'separator': r'\quad—\quad',        # Between term and definition inline
}

# The Master Manifest used by __init__.py to cascade configurations
CORE_CONFIG_MANIFEST = {
    'title_page': DOXTR_TITLE_PAGE,
    'headings': DOXTR_HEADINGS,
    'parts': DOXTR_PARTS,
    'epigraphs': DOXTR_EPIGRAPHS,
    'draft': DOXTR_DRAFT,
    'microtype': DOXTR_MICROTYPE,
    'containers': DOXTR_CONTAINERS,
    'tables': DOXTR_TABLES,
    'figures': DOXTR_FIGURES,
    'code': DOXTR_CODE,
    'admonitions': DOXTR_ADMONITIONS,
    'needs': DOXTR_NEEDS,
    'sidebar': DOXTR_SIDEBAR,
    'highlights': DOXTR_HIGHLIGHTS,
    'toc': DOXTR_TOC,
    'bibliography': DOXTR_BIBLIOGRAPHY,
    'index': DOXTR_INDEX,
    'glossary': DOXTR_GLOSSARY,
}