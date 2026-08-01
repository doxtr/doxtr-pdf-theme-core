"""
Doxtr Test Harness — Base Sphinx Configuration

This is the BASE configuration for the test harness. Per-feature overrides
in conf_overrides/ are merged on top of this at build time.

To add a new feature test:
    1. Add a FeatureSubTest to features.py
    2. Create the conf.py override in conf_overrides/
    3. Create the RST file in source/_test_cases/ (optional)

To override a setting for ALL tests, edit this file directly.
To override for a specific feature, create a new file in conf_overrides/.
"""

# -- Project information -----------------------------------------------------
project = "Doxtr Test Harness"
copyright = "2026, Doc Dash"
author = "Doc Dash"
version = "0.0.1"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_needs",
]

# Always use LaTeX builder for the test harness
master_doc = "index"
exclude_patterns = ["_build", "_extensions", "conf_overrides", "features.py", "test_runner.py", "*.md"]

# -- Options for LaTeX output ------------------------------------------------
latex_engine = "lualatex"
latex_toplevel_sectioning = "part"
latex_show_pagerefs = True
latex_logo = "_static/doxtr_icon_small.png"
latex_documents = [
    (master_doc, "doxtr-test-harness.tex", project, author, "manual"),
]

# -- Doxtr Core Configuration (base defaults) -----------------------------
# These are the DEFAULTS. Per-feature overrides in conf_overrides/ will merge on top.

# Enable core (not a child theme — this IS the core)
extensions.append("doxtr_pdf_theme_core")

# Show lists
doxtr_show_release = True
doxtr_show_list_of_figures = False   # Each feature test toggles this individually
doxtr_show_list_of_tables = False
doxtr_show_list_of_listings = False
doxtr_appendix_chapter_numbering = True

# Global geometry
doxtr_headsep = "8mm"
doxtr_footskip = "10mm"
doxtr_headheight = "18pt"
doxtr_footheight = "25pt"

# Fonts
doxtr_main_font = "Lato Light"
doxtr_sans_font = "Exo 2"
doxtr_mono_font = "IosevkaTerm NF"

# Inheritance
doxtr_inherit_all = True
doxtr_inherit_font = True
doxtr_inherit_color = True
doxtr_inherit_size = False

# -- sphinx-needs configuration ----------------------------------------------
needs_build_json = True
needs_types = [
    {
        "directive": "dr",
        "title": "Decision Record",
        "prefix": "_DR",
        "style": "rectangle",
        "color": "#BFD8D2",
    },
    {
        "directive": "adr",
        "title": "Architecture Decision Record",
        "prefix": "_ADR",
        "style": "rectangle",
        "color": "#FFCC14",
    },
]
needs_id_regex = r'^[a-zA-Z0-9_-]+$'
needs_fields = {
    "xlink": {
        "description": "Documentation link",
        "schema": {"type": "string"},
        "nullable": True,
    },
}

# -- HTML output (for test report) -------------------------------------------
html_theme = "basic"
html_static_path = ["_static"]

# -- Paths -------------------------------------------------------------------
templates_path = ["_templates"]
