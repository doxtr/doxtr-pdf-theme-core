"""
conf.py overrides for testing container name mapping (doxtr_container_mapping).

Tests that:
- A mapped class name resolves to the target container's LaTeX environment
- A stylebox directive also respects the mapping
- An unmapped class that exists directly still works
- A mapping to a non-existent target falls back to 'default'
"""

doxtr_containers = {
    'default': {
        'style': 'default',
        'title_color': '#333333',
        'content_background_color': '#FFFFFF',
    },
    'business': {
        'title_font': 'Fragment Mono',
        'title_color': '#DDDDDD',
        'title_icon': r'\faIcon{gavel}',
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
}

# Mapping under test:
#   'biz-alias'        -> 'business'  (valid mapped target)
#   'typewriter-alias' -> 'typewriter' (valid mapped target via stylebox)
#   'broken-alias'     -> 'nonexistent' (invalid target — should fall back to 'default')
doxtr_container_mapping = {
    'biz-alias': 'business',
    'typewriter-alias': 'typewriter',
    'broken-alias': 'nonexistent',
}
