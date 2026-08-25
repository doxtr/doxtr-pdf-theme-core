"""
conf.py overrides for testing Microtype feature — explicit kerning opt-in.
This simulates a pdfTeX user explicitly enabling kerning.
NOTE: This will produce a microtype error under LuaLaTeX but we only check
the generated .tex file contains the correct option, not that it compiles.
"""

doxtr_microtype = {
    'enabled': True,
    'protrusion': True,
    'expansion': True,
    'kerning': True,  # Explicitly opt in (pdfTeX only)
    'stretch': 10,
    'shrink': 10,
}
