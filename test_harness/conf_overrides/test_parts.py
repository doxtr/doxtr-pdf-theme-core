"""
conf.py overrides for testing Parts feature.
"""

doxtr_parts = {
    # Global Part Styling
    'color': '#008734',
    'font': 'Ewert',
    'size': r'\Huge',
    'number_part_color': '#00FF11',
    'number_part_font': 'Moirai One',
    'number_part_size': r'\fontsize{32pt}{36pt}\selectfont',
    'number_number_color': '#FF9D00',
    'number_number_font': 'Vast Shadow',
    'number_number_size': r'\fontsize{48pt}{36pt}\selectfont',

    # Specific Part Overrides
    1: {
        'image': '_static/wizard-of-docs.png',
        'background_color': '#00000080',
        'epigraph_color': '#FFCC00',
    },
    2: {
        'background_color': '#120C00C9',
        'number_part_font': 'Moirai One',
    },
    3: {},
    4: {},
    7: {
        'appendix': True,
    },
}
