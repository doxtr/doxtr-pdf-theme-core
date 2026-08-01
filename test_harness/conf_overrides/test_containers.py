"""
conf.py overrides for testing Containers / Stylebox feature.
"""

doxtr_containers = {
    'business': {
        'title_font': 'Fragment Mono',
        'title_color': '#DDDDDD',
        'title_icon': r'\faIcon{gavel}',
        'title_icon_font_size': r'\Large',
        'title_icon_color': '#FF9D00',
        'title_style': 'business',
        'content_font': 'Doto',
        'content_font_color': '#FFFFFF',
        'content_background_color': '#DD00DD',
        'container_frame': True,
    },
    'typewriter': {
        'title_font': 'Fragment Mono',
        'title_color': '#DDDDDD',
        'title_icon': r'\faIcon{newspaper}',
        'title_style': 'floating',
        'content_font': 'Special Elite',
        'content_font_color': '#FFFFFF',
        'content_background_color': '#DD00DD',
        'container_frame': False,
    },
    'typewriter-plain': {
        'title_font': 'Fragment Mono',
        'title_color': '#DDDDDD',
        'title_icon': r'\faIcon{newspaper}',
        'title_style': 'floating',
        'content_font': 'Special Elite',
        'content_font_color': '#000000',
        'content_background_color': '#FFFFFF',
        'container_frame': False,
    },
    'custom-title': {
        'title_font': 'Kablammo',
        'title_font_color': '#FFFFFF',
        'title_color': '#F4C9C9',
        'title_icon': r'\faIcon{newspaper}',
        'title_icon_color': '#CC00FF',
        'title_style': 'my_title',
        'content_font': 'Special Elite',
        'content_font_color': '#000000',
        'content_background_color': '#EBEBEB',
        'container_frame': False,
    },
    'font-simple': {
        'content_font': 'Special Elite',
        'container_frame': False,
        'match_text_width': True,
    },
    'handwritten': {
        'content_font': 'Caveat',
        'content_font_color': '#1E00FFA7',
        'container_frame': False,
        'match_text_width': True,
        'content_font_size': r'\relscale{1.25}',
    },
}
