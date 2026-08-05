"""
conf.py overrides for testing Container Render Modes.

Tests that:
- A container with render_mode='tcolorbox' (default) emits standard tcolorbox title args
- A container with render_mode='environment' emits \\begingroup macros instead
- An invalid render_mode falls back to 'tcolorbox' with a warning
- Nested environment-mode containers scope macros correctly via \\begingroup
"""

doxtr_containers = {
    'default': {
        'style': 'default',
        'title_color': '#333333',
        'content_background_color': '#FFFFFF',
    },
    # Standard tcolorbox mode (explicit default)
    'tcolorbox-explicit': {
        'render_mode': 'tcolorbox',
        'title_color': '#1E3A8A',
        'title_font_color': '#FFFFFF',
        'content_background_color': '#F8FAFC',
        'container_frame': True,
    },
    # Environment mode — title via macros, not tcolorbox title= option
    'env-mode': {
        'render_mode': 'environment',
        'title_color': '#FF9900',
        'title_icon': r'\faIcon{rocket}',
        'content_background_color': '#FFF8F0',
        'container_frame': False,
    },
    # Environment mode without title icon
    'env-no-icon': {
        'render_mode': 'environment',
        'title_color': '#009900',
        'content_background_color': '#F0FFF0',
        'container_frame': False,
    },
}
