# Doxtr PDF Theme Core

The core PDF layout engine for the Doxtr document authoring system. It provides a professional LaTeX/PDF output pipeline utilizing KOMA classes and LuaLaTeX, designed to be inherited by child themes that customize the look and feel.

## Installation

```bash
pip install doxtr-pdf-theme-core
```

**Note on LaTeX Engine:** This core relies on `fontspec` and KOMA classes, which require LuaLaTeX. The core will automatically set `latex_engine = 'lualatex'` if you haven't explicitly configured an engine.

## Quick Start — Using a Child Theme

The easiest way to use the core is through a child theme (e.g., `doxtr-pdf-theme-aubergine`):

```python
# conf.py
extensions = [
    'doxtr_pdf_theme_aubergine',
]
```

To use the core directly without a child theme:

```python
# conf.py
extensions = [
    'doxtr_pdf_theme_core',
]
```

---

## Create a Child Theme — Walkthrough

This section explains how to build your own child theme on top of the core engine.
A reference implementation is available at [doxtr-pdf-theme-aubergine](https://github.com/doxtr/doxtr-pdf-theme-aubergine).

### Project Structure

The minimum viable theme is 3 files:

```
my_company_theme/
├── pyproject.toml                   # Package metadata
├── README.md                        # Usage documentation
└── my_company_theme/
    └── __init__.py                  # Theme logic (colors, fonts, defaults)
```

For themes with custom LaTeX templates:

```
my_company_theme/
├── pyproject.toml
├── README.md
└── my_company_theme/
    ├── __init__.py
    └── latex_styles/                # Optional: override visual templates
        ├── admonition/
        │   └── rounded.tex_t       # Custom admonition rendering
        ├── container/
        │   └── default.tex_t       # Custom container body
        ├── container_title_style/
        │   └── minimal.tex_t       # Custom container title geometry
        ├── code/
        │   └── default.tex_t       # Custom code block rendering
        ├── draft/
        │   └── default.tex_t       # Custom draft watermark rendering
        ├── figure/
        │   └── default.tex_t       # Custom figure captions
        ├── highlights/
        │   └── default.tex_t       # Custom highlights rendering
        ├── need/
        │   └── default.tex_t       # Custom sphinx-needs boxes
        ├── sidebar/
        │   └── default.tex_t       # Custom sidebar rendering
        ├── table/
        │   └── default.tex_t       # Custom table captions
        └── title_page/
            └── my_cover.tex_t      # Custom title page layout
```

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-company-theme"
version = "0.1.0"
description = "My company's PDF theme for Doxtr."
requires-python = ">=3.8"
dependencies = [
    "doxtr-pdf-theme-core>=0.1.10",
]

[tool.setuptools.packages.find]
include = ["my_company_theme*"]

[tool.setuptools]
include-package-data = true

[tool.setuptools.package-data]
my_company_theme = [
    "*.tex_t",
    "latex_styles/**/*.tex_t",
    "assets/*.png",
]
```

### The Simplest Theme (Palette + Fonts Only)

A 20-line theme that recolors the entire document:

```python
# my_company_theme/__init__.py
from doxtr_pdf_theme_core import setup as core_setup

__version__ = "0.1.0"

def setup(app):
    # 1. Initialize the core engine first — this registers all config values
    core_setup(app)

    # 2. Set semantic colors — the entire document derives from these
    #    (The 7th key, 'page', defaults to '#FFFFFF' and rarely needs changing)
    app.config.doxtr_semantic_palette = {
        'primary':   '#1B4F72',   # Deep blue — headings, borders, table headers
        'secondary': '#F39C12',   # Gold — accents, highlights, decorative lines
        'info':      '#2E86C1',   # Info blue — notes, specs
        'success':   '#28B463',   # Green — tips, hints, decisions
        'warning':   '#E67E22',   # Orange — warnings, caution
        'danger':    '#E74C3C',   # Red — errors, danger
    }

    # 3. Set fonts (must be installed on the build system)
    app.config.doxtr_main_font = 'Noto Serif'
    app.config.doxtr_sans_font = 'Noto Sans'
    app.config.doxtr_mono_font = 'Noto Sans Mono'

    # Return value is required by Sphinx
    return {'version': __version__, 'parallel_read_safe': True}
```

This produces a fully styled PDF with blue headings, gold accent lines, blue table headers, automatic WCAG-compliant contrast on all text, and full inheritance down the heading hierarchy.

### Adding Element-Specific Overrides

For more control, set `doxtr_theme_defaults` — a dictionary that overrides specific elements. You only set the keys you want to change; unset config keys fall back to core defaults.

```python
def setup(app):
    core_setup(app)

    app.config.doxtr_semantic_palette = { ... }
    app.config.doxtr_main_font = 'Noto Serif'
    app.config.doxtr_sans_font = 'Noto Sans'
    app.config.doxtr_mono_font = 'Noto Sans Mono'

    # 4. Set theme defaults — the "middle layer" between Core and User
    app.config.doxtr_theme_defaults = {
        # Dark blue title page
        'title_page': {
            'page_color': '#1B2631',
            'title_font': 'Noto Sans',
            'title_size': r'\fontsize{34pt}{40pt}\selectfont',
            'title_color': '#FFFFFF',
            'subtitle_color': '#F39C12',
        },

        # Alternating headings with decorative chapter line
        'headings': {
            'align': 'alternate',
            'numbers_in_margin': True,
            'chapter': {
                'font': 'Noto Sans',
                'color': '#1B4F72',
                'number_line': True,
                'line_color': '#F39C12',
            },
        },

        # Custom admonition styling
        'admonitions': {
            'generic': {
                'title_font': 'Noto Sans',
                'title_background_color': '#1B4F72',
                'title_icon_box_background_color': '#0E3352',
                'content_background_color': '#EBF5FB',
            },
            'warning': {
                'title_background_color': '#E67E22',
                'content_background_color': '#FEF5E7',
            },
        },

        # Table styling
        'tables': {
            'generic': {
                'header_background_color': '#1B4F72',
                'header_font_color': '#FFFFFF',
                'row_color_odd': '#EBF5FB',
            },
        },
    }

    return {'version': __version__, 'parallel_read_safe': True}
```

### Overriding Visual Templates (Advanced)

For advanced visual changes (e.g., redesigning how admonition boxes are drawn), provide custom `.tex_t` template files and register their path.

`doxtr_theme_style_paths` is a **list** of directories searched in order. Use it for broad overrides spanning multiple style types. The per-type single-path variables (`doxtr_<type>_style_path`) take precedence over `doxtr_theme_style_paths` for their specific type.

```python
import os
from pathlib import Path

def setup(app):
    core_setup(app)

    # Tell the core where to find your .tex_t overrides
    pkg_dir = Path(__file__).parent.resolve()
    app.config.doxtr_theme_style_paths = [
        str(pkg_dir / 'latex_styles'),
    ]

    # Reference your custom style by name
    app.config.doxtr_theme_defaults = {
        'admonitions': {
            'generic': {
                'style': 'rounded',          # loads admonition/rounded.tex_t
            },
        },
        'containers': {
            'default': {
                'title_style': 'minimal',    # loads container_title_style/minimal.tex_t
            },
        },
    }

    return {'version': __version__, 'parallel_read_safe': True}
```

**Template resolution order:**
1. Per-type custom path (`doxtr_<type>_style_path`)
2. User project's `latex_styles/<type>/` folder
3. Theme's `doxtr_theme_style_paths` list (searched in order)
4. Core's `latex_styles/<type>/`
5. Absolute fallback (hardcoded in `core_fallbacks.py`)

### Bundling Custom Fonts with Your Theme

By default, Sphinx uses whatever fonts are installed on the build system. If your theme ships its own font files (`.ttf` or `.otf`), the core's font registration facility handles everything — copying files to the LaTeX build directory and generating `\defaultfontfeatures+` blocks so `\fontspec{FamilyName}` resolves correctly.

> **Optional dependency:** Auto-discovery (Mode 3 below) requires `fonttools>=4.0`. Explicit registration (Modes 1 and 2) works without it. Install with `pip install doxtr-pdf-theme-core[fonts]`.

#### Mode 1 — Explicit filenames

Call `register_font_family()` at module level (outside `setup()`). The registration happens at import time, before Sphinx fires any events.

```python
# my_theme/__init__.py
from pathlib import Path
from doxtr_pdf_theme_core import setup as core_setup, register_font_family

_FONTS_DIR = Path(__file__).parent / 'fonts'

register_font_family(
    name='Corporate Sans',
    fonts_dir=_FONTS_DIR,
    upright='CorpSans-Regular.otf',
    bold='CorpSans-Bold.otf',
    italic='CorpSans-Italic.otf',
    bold_italic='CorpSans-BoldItalic.otf',
    options='Numbers=OldStyle',          # any fontspec feature string
)

def setup(app):
    core_setup(app)
    app.config.doxtr_main_font = 'Corporate Sans'
    # No latex_additional_files manipulation, no config-inited hook needed.
```

The font files must live under `my_theme/fonts/` and be included in your package's `MANIFEST.in` / `pyproject.toml` package-data.

#### Mode 2 — Weight-pattern batch registration

For families with a consistent naming scheme, use `register_font_families()` with a `pattern` and a per-family `weights` map:

```python
from doxtr_pdf_theme_core import setup as core_setup, register_font_families

_FONTS_DIR = Path(__file__).parent / 'fonts'

# Single pattern — one template for all four faces
register_font_families(
    fonts_dir=_FONTS_DIR,
    pattern='Raleway-{weight}.ttf',
    families={
        'Raleway Thin':     {'upright': 'Thin',     'bold': 'Regular',   'italic': 'ThinItalic',     'bold_italic': 'Italic'},
        'Raleway Light':    {'upright': 'Light',    'bold': 'SemiBold',  'italic': 'LightItalic',    'bold_italic': 'SemiBoldItalic'},
        'Raleway':          {'upright': 'Regular',  'bold': 'Bold',      'italic': 'Italic',         'bold_italic': 'BoldItalic'},
        'Raleway SemiBold': {'upright': 'SemiBold', 'bold': 'ExtraBold', 'italic': 'SemiBoldItalic', 'bold_italic': 'ExtraBoldItalic'},
    },
)
```

For families where upright and italic files use different naming conventions, pass a `dict` as the pattern:

```python
# Dual pattern — upright/bold use one template, italic/bold-italic use another
register_font_families(
    fonts_dir=_FONTS_DIR,
    pattern={
        'upright': 'MyFont_{weight}_.ttf',   # trailing underscore on uprights
        'italic':  'MyFont_{weight}.ttf',    # no trailing underscore on italics
    },
    families={
        'MyFont Thin':  {'upright': '200', 'bold': '400', 'italic': '200i', 'bold_italic': '400i'},
        'MyFont':       {'upright': '400', 'bold': '700', 'italic': '400i', 'bold_italic': '700i'},
        'MyFont Bold':  {'upright': '700', 'bold': '900', 'italic': '700i', 'bold_italic': '900i'},
    },
)
```

For a batch of families with fully explicit filenames (no pattern), omit `pattern` or pass `pattern=None`:

```python
# Literal filenames batch mode
register_font_families(
    fonts_dir=_FONTS_DIR,
    families={
        'Raleway':       {'upright': 'Raleway-Regular.ttf',  'bold': 'Raleway-Bold.ttf',
                          'italic':  'Raleway-Italic.ttf',   'bold_italic': 'Raleway-BoldItalic.ttf'},
        'Raleway Light': {'upright': 'Raleway-Light.ttf',    'bold': 'Raleway-Regular.ttf',
                          'italic':  'Raleway-LightItalic.ttf', 'bold_italic': 'Raleway-Italic.ttf'},
    },
)
```

#### Mode 3 — Zero-code auto-discovery

Place font files in a `fonts/` directory alongside your `latex_styles/` directory. The core scans it automatically using `fonttools` to read family names, weight classes, and italic flags directly from the font metadata.

```
my_theme/
├── __init__.py
├── fonts/                ← auto-discovered (sibling to latex_styles)
│   ├── Raleway-Regular.ttf
│   ├── Raleway-Bold.ttf
│   ├── Raleway-Italic.ttf
│   └── Raleway-BoldItalic.ttf
└── latex_styles/         ← registered in doxtr_theme_style_paths
```

```python
# my_theme/__init__.py — zero font code needed
from doxtr_pdf_theme_core import setup as core_setup

def setup(app):
    core_setup(app)
    app.config.doxtr_theme_style_paths = [str(Path(__file__).parent / 'latex_styles')]
    # Auto-discovery finds my_theme/fonts/ because the parent directory
    # (my_theme/) contains __init__.py — confirming it is a Python package.
    app.config.doxtr_main_font = 'Raleway'
    app.config.doxtr_sans_font = 'Raleway Bold'
```

Auto-discovery groups files into sub-families based on `OS/2.usWeightClass`. Weight 400 registers as `FamilyName`, weight 300 as `FamilyName Light`, weight 700 as `FamilyName Bold`, and so on. Variable fonts (those with an `fvar` table) are registered as a single base family; a log message recommends using `register_font_family()` for full axis control.

Disable auto-discovery for a theme:

```python
doxtr_globals = {'light': {'font_auto_discover': False}}
```

#### Advanced — replacing the LaTeX renderer

Child themes that need a different LaTeX font registration syntax (e.g. `\newfontfamily` instead of `\defaultfontfeatures+`) can register a custom renderer:

```python
from doxtr_pdf_theme_core import register_font_renderer

def my_renderer(registered):
    """registered is the deduplicated list of font dicts."""
    lines = []
    for entry in registered:
        macro = ''.join(w.capitalize() for w in entry['name'].split())
        lines.append(
            f"\\newfontfamily\\{macro}Font[Path=./,"
            f" BoldFont={entry['bold']},"
            f" ItalicFont={entry['italic']},"
            f" BoldItalicFont={entry['bold_italic']}]"
            f"{{{entry['upright']}}}"
        )
    return '\n'.join(lines)

register_font_renderer(my_renderer)
```

To replace the discovery step with a manifest-based scanner:

```python
from doxtr_pdf_theme_core import register_font_discoverer
from doxtr_pdf_theme_core.fonts import register_font_family
import json

def manifest_discoverer(fonts_dir):
    manifest = fonts_dir / 'fonts.json'
    if not manifest.exists():
        return
    for entry in json.loads(manifest.read_text()):
        register_font_family(
            name=entry['name'],
            fonts_dir=fonts_dir,
            upright=entry['regular'],
            bold=entry.get('bold', entry['regular']),
        )

register_font_discoverer(manifest_discoverer)
```

### Font Weight Mapping

If your chosen font has non-standard weight variants (e.g., "Light" as the regular weight), use the `_options` variables to prevent LaTeX "Font shape undefined" warnings:

```python
app.config.doxtr_main_font = 'Roboto'
app.config.doxtr_main_font_options = (
    'UprightFont={Roboto Light}, '
    'BoldFont={Roboto Medium}, '
    'ItalicFont={Roboto Light Italic}, '
    'BoldItalicFont={Roboto Medium Italic}'
)

app.config.doxtr_sans_font = 'Source Sans Pro'
app.config.doxtr_sans_font_options = 'Scale=MatchLowercase'

app.config.doxtr_mono_font = 'JetBrains Mono'
app.config.doxtr_mono_font_options = 'Scale=MatchLowercase'
```

### Using the Semantic Color System

The `dd:` expression system lets you derive colors dynamically from the palette. All color fields in every config section accept `dd:` expressions.

```python
app.config.doxtr_theme_defaults = {
    'headings': {
        'chapter': {
            'color': 'dd:primary',                    # Palette's primary color
            'line_color': 'dd:secondary',             # Palette's secondary
        },
    },
    'admonitions': {
        'generic': {
            'title_background_color': 'dd:primary',
            'content_background_color': 'dd:primary:lighten:85',   # 85% lighter
            'content_font_color': 'dd:primary:darken:30',          # 30% darker
        },
    },
    'tables': {
        'generic': {
            'header_background_color': 'dd:primary',
            'header_font_color': 'dd:primary:contrast:fg:primary', # Auto WCAG contrast
        },
    },
}
```

**Available expressions:**

| Expression | Result |
|---|---|
| `dd:primary` | Palette color directly |
| `dd:page` | Page background color |
| `dd:primary:lighten:80` | 80% lighter |
| `dd:primary:darken:30` | 30% darker |
| `dd:primary:contrast:fg:primary` | Foreground adjusted for WCAG contrast |
| `dd:page:contrast:bg:primary` | Background adjusted for contrast |
| `dd:this:title_background_color` | Another key in the same merged section |
| `dd:theme:title_background_color` | Value from the theme's current section |
| `dd:core:title_background_color` | Value from the core's current section |
| `dd:#FFCC0025:lighten:80` | Inline hex literal with operation |
| `dd:admonitions.warning[theme]:title_background_color` | Explicit cross-section path |

**Shorthand collision:** `dd:warning:` is ambiguous — it could mean the palette key or the admonition type. Use `dd:admonitions.warning:title_background_color` for the admonition, or `dd:warning` alone for the palette.

**WCAG override suffix:**

```python
'color': 'dd:primary:contrast:fg:primary:aaa'    # Force AAA (7:1)
'color': 'dd:primary:contrast:fg:primary:aa'     # Force AA (4.5:1)
'color': 'dd:primary:contrast:fg:primary:7'      # Explicit ratio
```

**Resolution rules:**
- Core configs cannot reference theme configs. Theme configs cannot reference user configs.
- Two-pass resolution: values are resolved before inheritance, then re-resolved after.
- Static hex values (no `dd:` prefix) pass through unchanged.

### Registering Custom AST Processors

Theme authors and downstream extensions can hook into the AST processing pipeline without monkey-patching, using `register_ast_processor()`. Registered processors run at priority 992, after all core processors.

```python
from doxtr_pdf_theme_core import register_ast_processor
from docutils import nodes

def my_processor(app, doctree, docname):
    """Called for every resolved doctree during a latex build."""
    for node in doctree.traverse(nodes.paragraph):
        # Custom processing here
        pass

register_ast_processor(my_processor)
```

The function signature must be `fn(app, doctree, docname) -> None`. Processors are called in registration order and errors are caught and logged as warnings without aborting the build.

### Install and Test

```bash
# Install in development mode
pip install -e /path/to/my_company_theme

# Add to your Sphinx conf.py
# extensions = ['my_company_theme']

# Build PDF
sphinx-build -b latex source/ build/latex/
cd build/latex && latexmk -pdf -lualatex *.tex
```

### Package and Distribute

```bash
# Build the wheel
python -m build

# Publish to PyPI (or private registry)
twine upload dist/*
```

---

## Architecture

### Three-Tier Merge

All configuration flows through a three-layer cascade:

```
┌─────────────────────────────────────────────────┐
│  User conf.py                                   │  ← Highest priority
│  (doxtr_headings = {'chapter': {'color': ...}}) │
├─────────────────────────────────────────────────┤
│  Theme Defaults                                 │  ← Middle layer
│  (app.config.doxtr_theme_defaults = {...})      │
├─────────────────────────────────────────────────┤
│  Core Defaults                                  │  ← Lowest priority
│  (core_config.py CORE_CONFIG_MANIFEST)          │
└─────────────────────────────────────────────────┘
```

Each layer only specifies the keys it wants to override. The `deep_update()` function recursively merges nested dictionaries, so setting one key inside `headings.chapter` doesn't wipe out the other keys in that section.

### Semantic Color Palette

Control the entire document's look by setting 7 palette colors:

```python
doxtr_semantic_palette = {
    'primary':   '#183060',   # Deep navy — structural, headings, borders
    'secondary': '#78D8F0',   # Bright cyan — accents, highlights, active states
    'info':      '#60D8F0',   # Lighter cyan — info, notes, specs
    'success':   '#66D98E',   # Fresh green — hints, tips, decisions
    'warning':   '#F0A860',   # Warm amber — warnings, caution
    'danger':    '#E05050',   # Clear red — danger, error, risk
    'page':      '#FFFFFF',   # Page background for contrast calculations
}
```

All other colors derive from these via `dd:` expressions in the configuration.

---

## Features & Customization

### Structural Layout Settings

By default, the theme pushes chapter and section numbers into the page margins and *alternates* their placement based on the page number.

```python
doxtr_headings = {
    'align': 'alternate',         # 'alternate', 'left', 'right', 'center'
    'numbers_in_margin': True,    # Push numbers into the margin
    'margin_space': '1.5em',      # Gap between number and title text

    'chapter': {
        'align': 'right',         # Override just for chapters
        'number_margin': True,
        'number_line': True,      # Decorative colored bar
        'line_height': '10cm',
        'line_color': '#FF0000',
        'margin_space': '0.75em',
    },
    'section': {
        'number_margin': False,
        'number_line': False,
    },
}
```

### Document Inheritance Hierarchy

Font, color, and size properties cascade top-down through the heading hierarchy (`part` → `chapter` → `section` → `subsection` → `subsubsection`). Each level inherits from the nearest ancestor that was explicitly set by the theme or user — not necessarily the core. For example, if a theme sets only `chapter.font = 'Inter'` and leaves lower levels unset, `section`, `subsection`, and `subsubsection` all inherit `'Inter'`, not the core's per-level defaults.

```python
doxtr_inherit_all = True    # Global kill-switch for all style cascading
doxtr_inherit_font = True   # Cascade font families downward
doxtr_inherit_color = True  # Cascade colors downward
doxtr_inherit_size = False  # Let KOMA handle font scaling by default
```

### Core Fonts

```python
doxtr_main_font = 'Spectral'
doxtr_main_font_options = 'BoldFont={Spectral SemiBold}, ItalicFont={Spectral Italic}, BoldItalicFont={Spectral SemiBold Italic}'
doxtr_sans_font = 'Montserrat'
doxtr_sans_font_options = ''                        # fontspec options for sans font
doxtr_mono_font = 'FiraCode Nerd Font'
doxtr_mono_font_options = 'Scale=MatchLowercase'    # fontspec options for mono font
```

These variables select fonts already installed on the build system. To bundle custom font files with your project or theme, use the `doxtr_fonts` config variable (end users) or `register_font_family()` / `register_font_families()` (theme authors). See [Bundling Custom Fonts with Your Theme](#bundling-custom-fonts-with-your-theme) and [`doxtr_fonts`](#doxtr_fonts) below.

### Sizes & Spacing

The base document font size is controlled by:

```python
doxtr_main_font_size = '11.5pt'  # Default; accepts '10pt', '11pt', '11.5pt', '12pt', etc.
```

Heading sizes can be defined in two ways:

**1. Relative (recommended for themes)** — scales with `doxtr_main_font_size`:

```python
doxtr_headings = {
    'chapter': {
        'size_factor': 2.0,   # 2× base size (11.5pt × 2.0 = 23.0pt)
    },
    'section': {
        'size_factor': 1.5,   # 1.5× base size (11.5pt × 1.5 = 17.2pt)
    },
}
```

**2. Absolute** — fixed LaTeX font command (use Python raw strings):

```python
doxtr_headings = {
    'chapter': {
        'size': r'\fontsize{32pt}{36pt}\selectfont',
    },
}
```

The `\fontsize{}{}\selectfont` command takes:
1. **Font size** (e.g., `32pt`) — character height
2. **Baselineskip** (e.g., `36pt`) — line-to-line distance

When using `size_factor`, the baselineskip is automatically calculated as `size × 1.2`.

**Precedence:** If both `size` and `size_factor` are present in the merged config for a heading level, `size` wins (explicit user override takes precedence over computed value).

### Building in Dark Mode

Because the entire document derives from the semantic color palette, switching to dark mode only requires overriding `doxtr_semantic_palette` and `doxtr_page_background` at build time — no source document changes are needed.

**Option 1 — Sphinx tags (recommended)**

Add a conditional block to `conf.py` once, then pass `-t dark` on every dark-mode build:

```python
# conf.py
if tags.has('dark'):
    doxtr_semantic_palette = {
        'primary':   '#E8E8E8',   # Light grey — headings, borders
        'secondary': '#B388FF',   # Soft violet — accents, highlights
        'info':      '#4FC3F7',   # Sky blue — info, notes
        'success':   '#81C784',   # Muted green — hints, tips
        'warning':   '#FFB74D',   # Warm amber — warnings
        'danger':    '#EF5350',   # Red — errors, danger
        'page':      '#1A1A2E',   # Dark page background
    }
    doxtr_page_background = '#1A1A2E'
```

```bash
sphinx-build -b latex -t dark source/ build/latex_dark/
cd build/latex_dark && latexmk -pdf -lualatex *.tex
```

**Option 2 — Environment variable**

Read an environment variable in `conf.py`:

```python
# conf.py
import os
if os.environ.get('DOXTR_DARK_MODE'):
    doxtr_semantic_palette = {
        'primary':   '#E8E8E8',
        'secondary': '#B388FF',
        'info':      '#4FC3F7',
        'success':   '#81C784',
        'warning':   '#FFB74D',
        'danger':    '#EF5350',
        'page':      '#1A1A2E',
    }
    doxtr_page_background = '#1A1A2E'
```

```bash
DOXTR_DARK_MODE=1 sphinx-build -b latex source/ build/latex_dark/
cd build/latex_dark && latexmk -pdf -lualatex *.tex
```

On Windows:

```bat
set DOXTR_DARK_MODE=1
sphinx-build -b latex source/ build\latex_dark\
```

**Option 3 — Separate config directory**

No `conf.py` modifications needed. Create a `dark/conf.py` that imports your existing config and overrides the colors:

```python
# dark/conf.py
import os, sys

_here = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(_here, '..', 'conf.py')).read())

doxtr_semantic_palette = {
    'primary':   '#E8E8E8',
    'secondary': '#B388FF',
    'info':      '#4FC3F7',
    'success':   '#81C784',
    'warning':   '#FFB74D',
    'danger':    '#EF5350',
    'page':      '#1A1A2E',
}
doxtr_page_background = '#1A1A2E'
```

Point Sphinx at the override directory with `-c`:

```bash
sphinx-build -b latex -c dark/ source/ build/latex_dark/
cd build/latex_dark && latexmk -pdf -lualatex *.tex
```

This approach keeps `conf.py` untouched and is useful in CI pipelines where you want a strict separation between light and dark builds.

---

### Page Color Adaptation

When the page background differs from the theme's designed-for background (typically `#FFFFFF`), the core automatically adapts all theme colors to maintain their intended visual relationships. This includes image backgrounds.

```python
# conf.py — warm cream page
doxtr_semantic_palette = {'page': '#FCF6E5'}
```

With just that one change:
- All theme colors shift proportionally to maintain contrast and visual hierarchy
- White image backgrounds (PlantUML, flowcharts, diagrams) are replaced with the page color
- Images with transparent backgrounds are left untouched

**Image background detection** uses flood-fill from image borders — only edge-connected white regions are replaced. Interior white areas (text on colored bars, enclosed pockets between crossing lines) are preserved.

Per-image opt-out:

```rst
.. image:: my-special-diagram.png
   :class: no-auto-image-adapt
```

Configuration:

```python
# conf.py
doxtr_adapt_colors_to_page = 'auto'       # 'auto', True, or False
doxtr_adapt_image_backgrounds = True       # Toggle image adaptation separately
doxtr_adapt_image_white_fuzz = 5           # Channel tolerance (0–255)
doxtr_image_exclude_patterns = ['logo-*.png']  # Skip specific images
```

---

## Configuration Reference

### Config Sections

Each section can be set via `doxtr_theme_defaults` (in a theme) or directly in `conf.py`:

| Section | `conf.py` variable | Controls |
|---|---|---|
| `title_page` | `doxtr_title_page` | Cover page colors, fonts, background image |
| `headings` | `doxtr_headings` | Chapter/section/subsection styling |
| `parts` | `doxtr_parts` | Part page styling and numbering |
| `epigraphs` | `doxtr_epigraphs` | Quote block styling |
| `draft` | `doxtr_draft` | Watermark text and styling |
| `microtype` | `doxtr_microtype` | Typographic refinement settings |
| `admonitions` | `doxtr_admonitions` | Note/warning/tip/etc. boxes |
| `tables` | `doxtr_tables` | Table header, row, and caption colors |
| `figures` | `doxtr_figures` | Figure caption styling |
| `code` | `doxtr_code` | Code block per-language styling |
| `containers` | `doxtr_containers` | Custom stylebox containers |
| `needs` | `doxtr_needs` | sphinx-needs box styling |
| `sidebar` | `doxtr_sidebar` | RST `.. sidebar::` directive styling |
| `highlights` | `doxtr_highlights` | RST `.. highlights::` directive styling |
| `toc` | `doxtr_toc` | Table of Contents entry styling |
| `bibliography` | `doxtr_bibliography` | Bibliography/citation entry styling |
| `index` | `doxtr_index` | Back-of-book index styling |
| `glossary` | `doxtr_glossary` | Glossary term/definition styling |
| `links` | `doxtr_links` | Hyperlink colors (internal/external) |

### Global Variables

| Variable | Default | Purpose |
|---|---|---|
| `doxtr_main_font` | `'Spectral'` | Body text font |
| `doxtr_main_font_options` | *(Spectral weight mapping)* | fontspec options for main font weight mapping |
| `doxtr_sans_font` | `'Montserrat'` | Sans-serif font |
| `doxtr_sans_font_options` | `''` | fontspec options for sans font (e.g. `Scale=MatchLowercase`) |
| `doxtr_mono_font` | `'FiraCode Nerd Font'` | Monospace font |
| `doxtr_mono_font_options` | `'Scale=MatchLowercase'` | fontspec options for mono font |
| `doxtr_main_font_size` | `'11.5pt'` | Base body text font size. Used as LaTeX document class pointsize and as reference for heading `size_factor` calculations |
| `doxtr_semantic_palette` | *(6 colors)* | Semantic color palette |
| `doxtr_page_background` | `'#FFFFFF'` | Page background used in contrast calculations |
| `doxtr_wcag_level` | `7` | Minimum contrast ratio for `contrast:` ops (4.5=AA, 7=AAA) |
| `doxtr_wcag_color_debug` | `False` | Log every WCAG contrast adjustment during build |
| `doxtr_inherit_all` | `True` | Master switch for style inheritance |
| `doxtr_inherit_font` | `True` | Inherit fonts down the heading hierarchy |
| `doxtr_inherit_color` | `True` | Inherit colors down the heading hierarchy |
| `doxtr_inherit_size` | `False` | Inherit sizes down the heading hierarchy |
| `doxtr_show_release` | `True` | Show release version on the title page |
| `doxtr_show_list_of_figures` | `False` | Print List of Figures before Index |
| `doxtr_show_list_of_tables` | `False` | Print List of Tables before Index |
| `doxtr_show_list_of_listings` | `False` | Print List of Code Blocks before Index |
| `doxtr_appendix_chapter_numbering` | `True` | Number appendix chapters as A.1, A.2, etc. |
| `doxtr_headsep` | `'8mm'` | Space between header and text body |
| `doxtr_footskip` | `'10mm'` | Space between text body and footer |
| `doxtr_headheight` | `'18pt'` | Height of the header line |
| `doxtr_footheight` | `'25pt'` | Height of the footer |
| `doxtr_footer_logo` | *(doxtr icon)* | Path to footer logo image |
| `doxtr_footer_logo_height` | `'1.5em'` | Height of the footer logo |
| `doxtr_landscape_package` | `'pdflscape'` | Package for landscape pages: `'pdflscape'`, `'lscape'`, or `''` to disable |
| `doxtr_strict_mode` | `False` | Raise an error on missing templates instead of falling back |
| `doxtr_cache_templates` | `True` | Cache compiled Jinja2 templates across pages |
| `doxtr_adapt_colors_to_page` | `'auto'` | Page color adaptation: `'auto'` (adapt when page differs by >0.05 luminance), `True` (force), `False` (disable) |
| `doxtr_adapt_image_backgrounds` | `True` | Replace white image backgrounds with page color when adaptation is active |
| `doxtr_adapt_image_white_fuzz` | `5` | Channel tolerance (0–255) for white detection in image background adaptation |
| `doxtr_image_exclude_patterns` | `[]` | Glob patterns to exclude images from all processing (dark mode AND page adaptation) |
| `doxtr_fonts` | `{}` | Declarative font registration for end users — see [`doxtr_fonts`](#doxtr_fonts) |
| `doxtr_globals['light']['font_auto_discover']` | `True` | Scan theme `fonts/` directories and register families from metadata (requires `fonttools`) |

### `doxtr_fonts`

End users can bundle and register custom fonts declaratively in `conf.py` without writing Python code. The core copies the files to the LaTeX build directory and generates the necessary `\defaultfontfeatures+` blocks automatically.

```python
# conf.py
doxtr_fonts = {
    # Explicit filenames — four faces named directly
    'Corporate Sans': {
        'dir': '_fonts',                        # relative to conf.py directory
        'upright':    'CorpSans-Regular.otf',
        'bold':       'CorpSans-Bold.otf',
        'italic':     'CorpSans-Italic.otf',
        'bold_italic':'CorpSans-BoldItalic.otf',
        'options':    'Scale=MatchLowercase',    # any fontspec feature string
    },
    # Pattern mode — weight identifiers expanded into filenames
    'Corporate Sans Light': {
        'dir':     '_fonts',
        'pattern': 'CorpSans_{weight}.otf',
        'weights': {
            'upright':    '300',
            'bold':       '600',
            'italic':     '300i',
            'bold_italic':'600i',
        },
    },
}

# Then reference the registered families in your config:
doxtr_main_font = 'Corporate Sans'
doxtr_sans_font = 'Corporate Sans Light'
```

**`dir`** is resolved relative to `confdir` (the directory containing `conf.py`) when not absolute. If only `upright` is provided, the other three faces default to it. User-registered fonts override any same-name registrations from the active theme.

Valid keys per entry: `dir`, `upright`, `bold`, `italic`, `bold_italic`, `options`, `pattern`, `weights`. Unknown keys produce a warning.

---

### Custom Resolution Paths (for Theme Authors)

`doxtr_theme_style_paths` is a **list** of directories searched for all style types. The per-type variables are single **strings** pointing to a specific folder and take precedence over `doxtr_theme_style_paths` for their type.

| Variable | Type | Purpose |
|---|---|---|
| `doxtr_theme_style_paths` | list | Ordered list of directories to search for any `.tex_t` file |
| `doxtr_preamble_path` | string | Override directory containing `preamble.tex_t` (replaces core LaTeX structure) |
| `doxtr_sty_override_paths` | list | Override directories for `.sty` files (e.g. `sphinxlatexstyleheadings.sty`) |
| `doxtr_container_title_style_path` | string | Container title `.tex_t` files |
| `doxtr_container_style_path` | string | Container body `.tex_t` files |
| `doxtr_table_style_path` | string | Table `.tex_t` files |
| `doxtr_figure_style_path` | string | Figure `.tex_t` files |
| `doxtr_code_style_path` | string | Code block `.tex_t` files |
| `doxtr_admonition_style_path` | string | Admonition `.tex_t` files |
| `doxtr_need_style_path` | string | sphinx-needs `.tex_t` files |
| `doxtr_sidebar_style_path` | string | Sidebar `.tex_t` files |
| `doxtr_topic_style_path` | string | Topic `.tex_t` files |
| `doxtr_contents_style_path` | string | Contents `.tex_t` files |
| `doxtr_title_page_template_path` | string | Title page `.tex_t` files |

---

### `doxtr_title_page`

```python
doxtr_title_page = {
    'template': 'default',              # Name of the .tex_t file to load for the cover
    'page_color': '#183060',            # Solid background color
    'background_image': 'bg.png',       # Path to background image (added to latex_additional_files)
    'background_image_mode': 'fit',     # 'fit', 'stretch', or 'tile'
    'background_image_align': 'center', # 'center', 'top', 'bottom', 'left', 'right'
    'color_opacity': '0.5',             # Opacity of the page_color overlay (0.0–1.0 as string)
    'top_line': False,                  # Render Sphinx's default top black line
    'subtitle': 'My Subtitle',          # Custom subtitle text

    # Font styling per element (title, subtitle, author, date, release_version):
    'title_font': 'Rye',
    'title_size': r'\fontsize{38pt}{44pt}\selectfont',
    'title_color': '#F0D890',
    'subtitle_font': 'Comfortaa',
    'subtitle_size': r'\fontsize{16pt}{20pt}\selectfont',
    'subtitle_color': '#78D8F0',
    'author_font': 'Josefin Sans',
    'author_size': r'\fontsize{14pt}{18pt}\selectfont',
    'author_color': '#90F0F0',
    'date_font': 'Montserrat',
    'date_size': r'\fontsize{11pt}{14pt}\selectfont',
    'date_color': '#F0D890',
    'release_version_font': 'Comfortaa',
    'release_version_size': r'\fontsize{11pt}{14pt}\selectfont',
    'release_version_color': '#F0C078',
}
```

`background_image_mode` controls how the image fills the page:
- `'fit'` — scale to fit while preserving aspect ratio
- `'stretch'` — scale to fill the entire page, ignoring aspect ratio
- `'tile'` — tile the image across the page

### `doxtr_headings`

```python
doxtr_headings = {
    # Global defaults applied to all levels unless overridden per-level:
    'align': 'alternate',           # 'alternate', 'left', 'right', 'center'
    'numbers_in_margin': True,      # Push numbers into the page margin
    'margin_space': '0em',          # Gap between number and title text
    'number_sep': r'\marginparsep', # Space between text block edge and number in margin
    'number_match_title_xheight': True,  # Scale number cap height to match title x-height

    # Per-level overrides — all keys below are accepted by every level:
    'part': {
        'font': 'Cinzel',
        'size': r'\fontsize{42pt}{48pt}\selectfont',
        'color': '#FFFFFF',
        'align': 'center',
        'number_line': False,        # Decorative colored structural bar
        'line_height': '10cm',       # Length of the structural line
        'line_color': '#78D8F0',
        'margin_space': '0.75em',
        'number_font': 'Kranky',
        'number_size': r'\fontsize{32pt}{38pt}\selectfont',
        'number_color': '#184878',
        'background_color': '#183060',      # Part page background color
        'epigraph_color': '#D8F0F0',        # Epigraph text color on part pages
        'epigraph_author_color': '#F0C078', # Epigraph attribution color on part pages
    },
    'chapter': {
        'font': 'Story Script',
        'size_factor': 2.0,          # 2× doxtr_main_font_size (or use absolute 'size' instead)
        'color': '#183060',
        'number_margin': True,       # Push chapter number into margin
        'number_line': True,
        'line_height': '7cm',
        'line_color': '#78D8F0',
        'margin_space': '0.75em',
        'number_font': 'Kranky',
        'number_size': r'\fontsize{32pt}{38pt}\selectfont',
        'number_color': '#184878',
    },
    # 'section': { ... },      # Same keys as chapter, number_line defaults to False
    # 'subsection': { ... },
    # 'subsubsection': { ... },
}
```

### `doxtr_parts`

Parts are numbered pages that divide the book into major sections. Global keys set defaults for all parts; integer keys override individual parts by number.

```python
doxtr_parts = {
    # Global defaults for all part pages:
    'font': 'Cinzel',
    'size': r'\fontsize{48pt}{54pt}\selectfont',
    'color': '#FFFFFF',
    'part_number_font': 'Comfortaa',           # Font for the "Part" prefix label
    'part_number_size': r'\fontsize{24pt}{28pt}\selectfont',
    'part_number_color': '#78D8F0',
    'part_number_part_font': 'Comfortaa',       # Font for the word "Part"
    'part_number_part_size': r'\fontsize{18pt}{22pt}\selectfont',
    'part_number_part_color': '#78D8F0',
    'part_number_number_font': 'Cinzel',        # Font for the numeral itself
    'part_number_number_size': r'\fontsize{36pt}{42pt}\selectfont',
    'part_number_number_color': '#F0D890',

    # Per-part overrides (integer key = part number):
    1: {
        'appendix': True,                       # Switch to letter numbering from this part
        'image': 'wizard-of-docs.png',          # Full-page background image
        'background_color': '#00000088',        # 8-digit hex: last 2 digits = opacity
        'epigraph_color': '#FFF',
        'epigraph_author_color': '#CCC',
        'font': 'Cinzel',
        'color': '#FFFFFF',
        'size': r'\fontsize{48pt}{54pt}\selectfont',
        'number_font': 'Comfortaa',
        'number_color': '#78D8F0',
        'number_part_font': 'Comfortaa',
        'number_part_color': '#78D8F0',
        'number_number_font': 'Cinzel',
        'number_number_color': '#F0D890',
    },
}
```

### `doxtr_epigraphs`

```python
doxtr_epigraphs = {
    'width': r'0.55\textwidth',
    'format': '— #1',               # #1 is replaced by the attribution text
    'align_box': 'right',           # 'left', 'center', 'right'
    'align_text': 'left',
    'align_author': 'right',
    'font': 'Cormorant Garamond',
    'size': r'\itshape\large',
    'color': '#303048',
    'author_font': 'Merienda',
    'author_size': r'\small',
    'author_color': '#184878',

    # Per-level overrides (inherit from global when not set):
    # 'part': { 'width': r'0.6\textwidth', 'color': '#FFFFFF', ... },
    # 'chapter': { ... },
    # 'section': { ... },
    # 'subsection': { ... },
    # 'subsubsection': { ... },
}
```

### `doxtr_draft`

The watermark is **activated by setting `'text'`**. Without it, no watermark is rendered.

```python
doxtr_draft = {
    'text': 'DRAFT - {date} - V: {project_version}',  # Activates the watermark
    # Placeholders: {date}, {project_version}, {ext_version}
    'date_format': '%Y-%m-%d %H:%M:%S %Z',
    'timezone': 'local',            # 'local', 'UTC', or any IANA zone e.g. 'Europe/Berlin'
    'color': '#00000044',           # 8-digit hex — last 2 digits control opacity
    'font_size': r'\normalsize',
    'font': 'Offside',
}
```

Watermark is automatically disabled when `microtype` is active (draft mode implies fast iteration; microtype is for final output). Microtype is re-enabled when `'text'` is removed.

### `doxtr_microtype`

Microtype is active by default when no draft watermark is set.

```python
doxtr_microtype = {
    'enabled': True,        # Master switch (also disabled automatically in draft mode)
    'protrusion': True,     # Hanging punctuation — characters protrude slightly into margin
    'expansion': True,      # Font expansion — eliminates uneven word spacing
    'kerning': False,       # Fine character-pair kerning (requires microtype >= 2.6a for LuaTeX)
    'stretch': 10,          # Maximum stretch percentage
    'shrink': 10,           # Maximum shrink percentage
}
```

---

### `doxtr_admonitions`

All admonition types inherit from `'generic'`. Override only the keys you want to change for a specific type.

**Built-in types:** `generic`, `admonition`, `note`, `tip`, `hint`, `important`, `warning`, `caution`, `danger`, `error`, `attention`, `seealso`

```python
doxtr_admonitions = {
    'generic': {
        'style': 'default',                         # Name of the .tex_t template to use
        'title_icon': r'\faIcon{info-circle}',       # LaTeX command or image path
        'title_icon_color': '#FFFFFF',
        'title_icon_size': '',                       # LaTeX size command (empty = inherit)
        'title_icon_padding': '3ex',
        'title_decoration_spacing': '2mm',
        'title_font': 'Montserrat',
        'title_font_size': r'\large\bfseries',
        'title_font_color': '#FFFFFF',
        'title_background_color': '#184878',
        'title_icon_box_background_color': '#183060',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': '#1A1A2E',
        'content_background_color': '#F0F8FF',
        'content_background_color_nested': '#FFFFFF', # Background when admonition is nested
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    # Per-type overrides (merge on top of generic):
    'note': {
        'title_icon': r'\faIcon{bookmark}',
        'title_background_color': '#2060A0',
        'title_icon_box_background_color': '#184878',
        'content_background_color': '#EEF5FC',
    },
    'warning': {
        'title_icon': r'\faIcon{exclamation-triangle}',
        'title_background_color': '#D48030',
        'content_background_color': '#FFF8F0',
    },
    # 'tip', 'hint', 'important', 'caution', 'danger', 'error', 'attention', 'seealso'
    # all accept the same keys as 'generic'
}
```

If `title_icon` is a file path (not a LaTeX command starting with `\`), it is automatically included as `\includegraphics[height=1em, keepaspectratio]{file}`.

### `doxtr_needs`

Controls [sphinx-needs](https://sphinx-needs.readthedocs.io/) box styling. Types beyond `generic` are auto-detected from `needs_types` in your `conf.py`.

**Built-in type overrides:** `generic`, `req`, `spec`, `decision`, `risk`

```python
doxtr_needs = {
    'generic': {
        'style': 'default',
        'title_font': 'Montserrat',
        'title_font_size': r'\large\bfseries',
        'title_color': '#FFFFFF',
        'title_background_color': '#184878',
        'title_icon': r'\faIcon{clipboard-check}',
        'title_icon_color': '#FFFFFF',
        'title_icon_size': '',
        'title_icon_raise': '0pt',                  # Manual vertical adjustment for icon
        'title_icon_raise_offset': '0pt',            # Additional offset added to raise
        'title_vertical_position': 'middle',         # 'top', 'middle', 'bottom', or manual
        'segmentation_style': 'solid',               # 'solid', 'dashed', 'dotted', 'dashdotted', 'none'
        'segmentation_color': '#184878',
        'metadata_background_color': '#E8F4FC',
        'metadata_font': 'Montserrat',
        'metadata_font_size': r'\small',
        'metadata_font_color': '#183060',
        'metadata_key_font': 'Montserrat',
        'metadata_key_font_size': r'\bfseries',
        'metadata_key_color': '#183060',
        'content_background_color': '#FFFFFF',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': '#1A1A2E',
        'before_skip': '1.5em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },
    # Per-type overrides:
    'req': {
        'title_background_color': 'dd:secondary',
        'segmentation_color': 'dd:secondary',
        'metadata_background_color': 'dd:secondary:lighten:85',
    },
    # 'spec', 'decision', 'risk' follow the same pattern
}
```

`title_vertical_position` values:
- `'middle'` — vertically centered (uses `\dimexpr 0.5\fontcharht...`)
- `'top'` — aligned to cap height
- `'bottom'` — baseline aligned
- Any other string — treated as a raw LaTeX raise dimension

### `doxtr_tables`

```python
doxtr_tables = {
    'generic': {
        'style': 'default',
        'title_style': 'classic',
        'caption_position': 'side',               # 'side', 'top', or 'bottom'
        'caption_top_offset': '-0.5ex',
        'title_padding': '1.5ex',
        'title_text_offset': '0pt',               # Horizontal offset of caption text
        'title_fade_dots': False,                  # Fade dot leaders in caption
        'title_background_fade_mask_color': '#FFFFFF',
        'title_background_fade_length': '1.5ex',
        'title_background_fade_shape': 'rectangle', # 'rectangle' or 'triangle'
        'header_background_color': '#183060',
        'header_font_color': '#FFFFFF',
        'header_font': 'Montserrat',
        'header_font_size': r'\bfseries',
        'row_color_odd': '#F8FAFF',
        'row_color_even': '#FFFFFF',
        'title_background_color': '#184878',
        'title_font_color': '#FFFFFF',
        'title_font': 'Montserrat',
        'title_font_size': r'\bfseries',
        # --- Content-Aware Column Widths ---
        'column_width_algorithm': 'minfloor',      # 'minfloor' or 'maxcontent'
        'header_char_width_factor': 1.35,          # Bold header font width relative to body
        'auto_colwidths': True,                    # Enable/disable Phase 2 column widths
    }
}
```

### `doxtr_figures`

```python
doxtr_figures = {
    'generic': {
        'style': 'default',
        'caption_background_color': '#F0F8FF',
        'caption_font_color': '#183060',
        'caption_font': 'Montserrat',
        'caption_font_size': r'\small\sffamily\bfseries',
        'caption_padding': '1.5ex',
        'caption_align': 'center',              # 'left', 'center', 'right'
    }
}
```

---

### `doxtr_code`

Code blocks are styled per language. All language entries inherit from `'generic'` for any key not explicitly set.

**Built-in language overrides:** `python`, `java`, `kotlin`, `rust`, `c`, `cpp`, `csharp`, `go`, `rst`, `sh`, `bash`, `zsh`, `powershell`, `markdown`, `html`, `css`, `javascript`, `typescript`, `text`, `json`, `yaml`, `sql`, `xml`, `latex`, `dockerfile`, `toml`, `ini`, `ruby`, `php`, `lua`, `swift`, `make`

```python
doxtr_code = {
    'generic': {
        'style': 'default',
        'border_width': '0.8pt',
        'show_mac_dots': False,          # Red/yellow/green terminal dots (auto-enabled for shell languages)
        'language_label': '',            # Override the auto-detected language name in the title bar
        'icon': r'\faIcon{code}',        # LaTeX command or image path
        'icon_color': '#78D8F0',
        'icon_size': '',                 # LaTeX size command (empty = inherit)
        'icon_position': 'after_mac_dots', # 'before_mac_dots' or 'after_mac_dots'
        'title_background_color': '#183060',
        'title_font_color': '#78D8F0',
        'title_font': 'Montserrat',
        'title_font_size': r'\small\sffamily\bfseries',
        'content_background_color': '#F8FAFF',
        'content_font_color': '#1A1A2E',
        'content_font': 'FiraCode Nerd Font',  # Per-language monospace font override
        'content_font_size': r'\small',
        'border_color': '#78D8F0',
    },
    # Per-language overrides (any key from generic is accepted):
    'python': {
        'icon': r'\faIcon{python}',
        'title_background_color': '#306998',
        'title_font_color': '#FFD43B',
        'icon_color': '#FFD43B',
        'border_color': '#306998',
    },
    # Add your own language override:
    # 'mylang': {
    #     'title_background_color': '#123456',
    #     'title_font_color': '#FFFFFF',
    #     'icon': r'\faIcon{file-code}',
    #     'language_label': 'My Language',
    # },
}
```

Terminal/shell languages (`sh`, `bash`, `zsh`, `powershell`) have `show_mac_dots: True` by default. For all others it defaults to `False`.

If `icon` is a file path (not a LaTeX command), it is included as `\includegraphics[height=1em, keepaspectratio]{file}`.

### `doxtr_containers`

Containers are custom styled boxes created with the `.. stylebox::` RST directive. The core ships several built-in containers that you can use directly or use as examples for your own.

**Built-in container types:** `default`, `typewriter`, `highlight-section`, `alice`, `bob`, `folder`

#### RST Usage

```rst
.. stylebox:: my_container
   :title: My Title

   Content goes here.

.. stylebox:: my_container
   :notitle:

   No title shown (suppresses even a static title configured in the theme).
```

Options for the `.. stylebox::` directive:

| Option | Purpose |
|---|---|
| *(first argument)* | Container type name — must match a key in `doxtr_containers` |
| `:title: Text` | Override the title for this instance |
| `:notitle:` | Suppress all title sources, including a static `title` from config |
| `:name: anchor` | RST cross-reference anchor |
| `:class: css-class` | Additional docutils class |

#### Container Configuration

```python
doxtr_containers = {
    'my_container': {
        'style': 'default',              # Body .tex_t template name
        'title_style': 'classic',        # Title geometry .tex_t template name
        'render_mode': 'tcolorbox',      # 'tcolorbox' (title via option) or 'environment' (full control)
        'title': '',                     # Static title shown when no :title: in RST (empty = no title)
        'title_raw': False,              # Pass title as raw LaTeX without escaping
        'container_frame': True,         # Draw an outer border
        'match_text_width': False,       # Align box width to body text column
        'title_icon': r'\faIcon{info}',
        'title_font': 'Montserrat',
        'title_font_size': r'\large\bfseries',
        'title_color': '#1E3A8A',        # Title bar background color
        'title_font_color': '#FFFFFF',
        'title_icon_color': '#FFFFFF',
        'title_icon_font_size': '',
        'content_font': 'Spectral',
        'content_font_size': r'\normalsize',
        'content_font_color': '#000000',
        'content_background_color': '#F8FAFC',
        'before_skip': '2em plus 0.5em minus 0.5em',
        'after_skip': '1.5em plus 0.5em minus 0.5em',
    },

    # Folder style adds shadow and tab title:
    'folder': {
        'style': 'folder',
        'title': 'Background Information',
        'title_color': '#808080',              # Frame/border color
        'title_font_color': '#000000',
        'title_background_color': '#FFFFFF',   # Tab background
        'content_background_color': '#FFFFFF',
        'border_width': '0.4pt',
        'show_shadow': True,
        'shadow_color': '#C0C0C0',
    },

    # Participant style (alice/bob) adds a floating name badge:
    'alice': {
        'style': 'participant',
        'title': 'Alice',
        'frame_width': '0.2mm',        # Border thickness
        'frame_arc': '0mm',            # Corner radius (0mm = sharp)
        'title_position': 'left',      # Badge position: 'left', 'center', 'right', or LaTeX dim
        'title_xshift': '1cm',         # Additional horizontal offset
        'title_max_width': '-3cm',     # varwidth constraint for title pill
    },
}
```

### `doxtr_container_mapping`

Maps RST container class names to registered `doxtr_containers` style names. This lets you switch themes or rename container styles without touching your source documents.

```python
doxtr_container_mapping = {
    "terminal": "lcars-terminal",    # RST class -> theme container style
    "code-output": "lcars-terminal",  # Multiple classes can point to the same style
    "my-callout": "note",            # Fall back to any registered container
}
```

#### Resolution Order

When a container node is processed, the class name is resolved in this order:

1. **Mapping hit** — if the class is in `doxtr_container_mapping`, the target style name is used.
2. **Direct match** — if the class exists directly in `doxtr_containers`, it is used as-is (no mapping needed).
3. **Mapping fallback** — if the mapped target doesn't exist in `doxtr_containers`, the original class is tried.
4. **Default style** — if nothing matches, the `'default'` container style is used and a warning is emitted.

#### Build-time Validation

During the Sphinx build, if a mapping target doesn't exist in `doxtr_containers`, a warning is emitted:

```
WARNING: [Doxtr Core] Container mapping 'terminal' -> 'lcars-terminal': target style
'lcars-terminal' is not defined in doxtr_containers. Will fall back to 'default' at render time.
```

#### Theme Switching Example

A user writes documentation with `.. container:: terminal` (or `.. stylebox:: terminal`). To switch to an LCARS theme that calls the same style `lcars-terminal`, add to `conf.py`:

```python
doxtr_container_mapping = {
    "terminal": "lcars-terminal",
}
```

No RST files need to change. The mapping is applied at render time.

---

### `doxtr_sidebar`

Controls the RST `.. sidebar::` directive. Sidebars float alongside the main text using `wrapfig`.

```rst
.. sidebar:: My Sidebar Title
   :subtitle: Optional Subtitle

   Sidebar content here.
```

```python
doxtr_sidebar = {
    'style': 'default',
    'width': r'0.4\textwidth',
    'float_position': 'R',              # 'R'=right exact, 'L'=left exact, 'O'=outer, 'I'=inner
                                        # Lowercase (r/l/o/i) allows LaTeX to reposition
    'border_radius': '4pt',
    'border_width': '0.8pt',
    'border_color': '#184878',
    'title_icon': r'\faIcon{columns}',
    'title_font': 'Montserrat',
    'title_font_size': r'\large\bfseries',
    'title_background_color': '#184878',
    'title_font_color': '#FFFFFF',
    'title_icon_color': '#78D8F0',
    'subtitle_font': 'Montserrat',
    'subtitle_font_size': r'\small\itshape',
    'subtitle_font_color': '#306090',
    'content_font': 'Spectral',
    'content_font_size': r'\small',
    'content_font_color': '#1A1A2E',
    'content_background_color': '#F0F8FF',
    'before_skip': '1.5em plus 0.5em minus 0.5em',
    'after_skip': '1.5em plus 0.5em minus 0.5em',
}
```

### `doxtr_highlights`

Controls the RST `.. highlights::` directive, rendered as an accent-bordered summary box.

```rst
.. highlights::

   Key takeaway content here.
```

```python
doxtr_highlights = {
    'style': 'default',
    'title_text': 'Highlights',          # Text shown at top of box
    'title_icon': '',                     # Optional icon (e.g. r'\faIcon{star}')
    'title_font': 'Montserrat',
    'title_font_size': r'\large\bfseries',
    'title_font_color': '#8B6914',
    'border_color': '#8B6914',
    'border_width': '3pt',
    'content_font': '',                  # Empty = inherit body font
    'content_font_size': r'\normalsize',
    'content_font_color': '#1A1A2E',
    'content_background_color': '#FFF8DC',
    'before_skip': '1.5em plus 0.5em minus 0.5em',
    'after_skip': '1.5em plus 0.5em minus 0.5em',
}
```

### `doxtr_toc`

Controls Table of Contents entry fonts, sizes, and colors.

```python
doxtr_toc = {
    'title_font': None,           # Font for the "Contents" heading (None = inherit)
    'title_size': None,
    'title_color': None,

    'chapter_font': None,
    'chapter_size': r'\large',
    'chapter_color': None,        # dd: expressions supported
    'chapter_bold': True,

    'section_font': None,
    'section_size': r'\normalsize',
    'section_color': None,

    'subsection_font': None,
    'subsection_size': r'\small',
    'subsection_color': None,

    'dot_leader_color': None,     # Color of dot leaders (……)
    'dot_leader_char': r'\normalfont.',

    'page_number_font': None,
    'page_number_color': None,
}
```

### `doxtr_bibliography`

```python
doxtr_bibliography = {
    'title_font': None,
    'title_size': None,
    'title_color': None,
    'entry_font': None,
    'entry_size': None,
    'entry_color': None,
    'label_color': None,          # Color of [AuthorYear] citation labels
    'label_font': None,
}
```

### `doxtr_index`

```python
doxtr_index = {
    'title_font': None,
    'title_size': None,
    'title_color': None,
    'entry_font': None,
    'entry_size': None,
    'subentry_font': None,
    'subentry_size': None,
    'letter_group_font': None,    # The A, B, C group headers
    'letter_group_color': None,
}
```

### `doxtr_glossary`

```python
doxtr_glossary = {
    'term_font': None,
    'term_size': None,
    'term_color': None,
    'definition_font': None,
    'definition_size': None,
    'definition_color': None,
    'separator': r'\quad—\quad',  # Between term and definition
}
```

### `doxtr_links`

Controls hyperlink colors in the PDF output. These are injected into Sphinx's `sphinxsetup` as `InnerLinkColor` and `OuterLinkColor` (using the `{rgb}` color model required by hyperref).

```python
doxtr_links = {
    'inner_color': 'dd:info:darken:40',    # Internal cross-references (linkcolor, citecolor)
    'outer_color': 'dd:warning:darken:40', # External URLs (urlcolor, filecolor, menucolor)
}
```

Colors accept any `dd:` expression or static hex value. To disable automatic link coloring entirely, set both to empty strings:

```python
doxtr_links = {
    'inner_color': '',
    'outer_color': '',
}
```

If you set `InnerLinkColor` or `OuterLinkColor` directly in `latex_elements['sphinxsetup']`, the doxtr system will not overwrite your explicit values.

---

```bash
export VERSION=v1.0.42 && git tag $VERSION && git push origin $VERSION
```

GitHub Actions will publish to PyPI automatically on release.

## License

MIT
