"""
conf.py overrides for testing Microtype feature — enabled (no draft).
Uses core defaults: kerning=True (requires microtype >= 2.6a for LuaTeX).
"""

doxtr_microtype = {
    'enabled': True,
    'protrusion': True,
    'expansion': True,
    # kerning inherits core default (True) — LuaTeX compatible with microtype >= 2.6a
    'stretch': 10,
    'shrink': 10,
}
