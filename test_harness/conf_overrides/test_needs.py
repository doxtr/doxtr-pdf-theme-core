"""
conf.py overrides for testing Sphinx Needs feature.
"""

# Configure the specific ADR directive
doxtr_needs = {
    # The master fallback for all standard needs
    'generic': {
        'metadata_background_color': '#D3FBFF',
        'content_background_color': '#BA0202F4',
        'title_background_color': '#7484FF',
        'metadata_font_color': '#FF9D00',
        'metadata_key_color': '#00FF0D',
        'title_font_size': r'\fontsize{16pt}{16pt}\selectfont',
        'title_color': '#DD53BBA7',
        'title_icon': r'\faIcon{gavel}',
        'title_icon_size': r'\fontsize{30pt}{30pt}\selectfont',
        'title_icon_color': '#005EFF',
        'title_vertical_position': 'middle',
        'title_icon_raise_offset': '2pt',
        'segmentation_style': 'dashdotted',
        'segmentation_color': '#9900FF',
        'content_font': 'Stardos Stencil',
        'content_font_size': r'\fontsize{9pt}{9pt}\selectfont',
        'content_font_color': '#FFFFFF',
    },

    # The specific override for Architecture Decision Records
    'adr': {
        'style': 'adr',

        # Colors: Architectural Blueprint Theme
        'title_background_color': '#0F4C81',
        'title_color': '#FFBB00',
        'title_icon_color': '#FFFFFF',

        'metadata_background_color': '#F8FAFC',
        'metadata_font_color': '#334155',
        'metadata_key_color': '#0F4C81',
        'content_background_color': '#FFFFFF',
        'content_font_color': '#334155',
        'segmentation_color': '#94A3B8',

        # Fonts & Typography
        'title_font': 'Montserrat',
        'title_font_size': r'\Large\bfseries',
        'metadata_font': 'JetBrains Mono',
        'metadata_font_size': r'\small',
        'content_font': 'Lato',

        # Icons
        'title_icon': r'\faIcon{sitemap}',
        'title_icon_size': r'\Large',
        'title_vertical_position': 'middle',
    },
}
