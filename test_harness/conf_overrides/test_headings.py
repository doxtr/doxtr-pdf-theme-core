"""
conf.py overrides for testing Headings feature.
"""

doxtr_headings = {
    'numbers_in_margin': True,
    'margin_space': '1.5em',
    'align': 'alternate',
    'chapter': {
        'number_margin': True,
        'align': 'right',
        'color': '#FF00D9',
        'number_color': '#0092FA',
        'number_size': r'\fontsize{30pt}{30pt}\selectfont',
        'number_line': True,
        'line_height': '10cm',
        'line_color': '#CCCCCC',
    },
    'section': {
        'number_margin': True,
        'margin_space': '.5em',
        'align': 'alternate',
        'number_line': True,
        'line_height': '3em',
        'font': 'Uncial Antiqua',
        'color': '#2FFF00',
        'number_color': '#55FFF4',
        'number_font': 'Mr Dafoe',
    },
    'subsection': {
        'number_margin': True,
        'margin_space': '5.5em',
        'align': 'alternate',
        'number_line': True,
        'line_height': '1.8em',
    },
    'subsubsection': {
        'number_margin': True,
        'margin_space': '3em',
        'align': 'alternate',
        'number_line': False,
    },
}

# Global inheritance settings
doxtr_inherit_all = True
doxtr_inherit_font = True
doxtr_inherit_color = True
doxtr_inherit_size = False

# Parts config for inheritance testing
doxtr_parts = {
    'font': 'Ewert',
    'color': '#008734',
    'size': r'\Huge',
}
