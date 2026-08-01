"""
conf.py overrides for testing Title Page feature.
"""

doxtr_title_page = {
    'page_color': '#FFFFFF',
    'background_image': '_static/wizard-of-docs-techno.png',
    'background_image_mode': 'cover_width',
    'background_image_align': 'center',
    'color_opacity': '0.2',
    'top_line': True,

    # Title styling
    'title_font': 'Almendra Display',
    'title_color': '#EE1224',
    'title_size': r'\fontsize{32pt}{8pt}\selectfont',

    # Subtitle styling
    'subtitle_font': 'Faster One',
    'subtitle_color': '#009830',
    'subtitle': 'A study on demos',
    'subtitle_size': r'\Large',

    # Author styling
    'author_font': 'Handjet',
    'author_color': '#240EE8',

    # Date styling
    'date_font': 'Ephesis',
    'date_color': '#FFBB00',

    # Release version styling
    'release_version_font': 'Handjet',
    'release_version_color': '#FFBB00',
}

# Toggle release display
doxtr_show_release = True
