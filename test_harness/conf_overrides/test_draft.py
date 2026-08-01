"""
conf.py overrides for testing Draft Watermark feature.
"""

doxtr_draft = {
    'text': "DRAFT - {date} - Theme: {ext_version} - Proj: {project_version}",
    'color': '#D3D3D3BA',
    'date_format': '%Y-%m-%d %H:%M:%S %Z',
    'timezone': 'UTC',
    'font_size': r'\fontsize{9pt}{9pt}\selectfont',
    'font': 'Lato',
}
