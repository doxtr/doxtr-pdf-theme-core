"""
conf.py overrides for testing Microtype feature — enabled (no draft).
Uses core defaults: kerning=False (incompatible with LuaLaTeX).
"""

doxtr_microtype = {
    'enabled': True,
    'protrusion': True,
    'expansion': True,
    # kerning inherits core default (False) — incompatible with LuaLaTeX
    'stretch': 10,
    'shrink': 10,
}
