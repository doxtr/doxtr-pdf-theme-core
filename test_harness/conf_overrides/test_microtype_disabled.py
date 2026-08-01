"""
conf.py overrides for testing Microtype feature — with draft mode ON.
When draft mode is active, microtype should NOT be loaded.
"""

# Explicitly disable microtype (simulating what happens when draft is on)
doxtr_microtype = {
    'enabled': False,
    'protrusion': True,
    'expansion': True,
    'kerning': True,
    'stretch': 10,
    'shrink': 10,
}

# Also set draft mode to verify the draft watermark is rendered
doxtr_draft = {
    'text': "DRAFT - {date}",
    'color': '#D3D3D3BA',
    'date_format': '%Y-%m-%d',
    'timezone': 'UTC',
    'font_size': r'\fontsize{9pt}{9pt}\selectfont',
    'font': 'Lato',
}
