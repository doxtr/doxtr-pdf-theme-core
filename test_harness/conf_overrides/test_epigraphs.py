"""
conf.py overrides for testing Epigraphs feature.
"""

doxtr_epigraphs = {
    'width': r'0.6\textwidth',
    'format': '~ #1',
    'align_box': 'center',
    'align_text': 'left',
    'align_author': 'right',
    'font': 'Plaster',
    'color': '#FFFF00',
    'author_font': 'Luxurious Script',
    'author_color': '#FFCC00',
    # Per-level overrides
    'part': {
        'width': r'0.6\textwidth',
        'epigraph_color': '#FFCC00',
    },
    'chapter': {
        'color': '#000000',
    },
}
