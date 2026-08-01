"""
conf.py overrides for testing Microtype feature — enabled (no draft).
Uses core defaults: kerning=False (pdftex-only in older microtype versions).
"""

doxtr_microtype = {
    'enabled': True,
    'protrusion': True,
    'expansion': True,
    # kerning inherits core default (False) — safest for compatibility
    'stretch': 10,
    'shrink': 10,
}
