"""Font registration utilities for theme authors.

Provides a declarative API to register custom font families that will be:
- Copied to the LaTeX build directory (via latex_additional_files)
- Registered with \\defaultfontfeatures+ so \\fontspec{FamilyName} resolves

Public API (called from theme setup() or at module level):
- register_font_family()     -- register a single family with explicit filenames
- register_font_families()   -- batch-register multiple families (with optional pattern)
- get_registered_fonts()     -- return read-only snapshot of the working registry
- register_font_renderer()   -- replace the \\defaultfontfeatures+ generator
- register_font_discoverer() -- replace the fontTools-based directory scanner
- inject_font_features()     -- inject font feature blocks into latex_elements

Internal API (called from config_inited):
- _clear_font_registry()     -- reset working registry (idempotent builds)
- _set_fonts_processed()     -- mark processing complete (late-call guard)
- process_user_font_config() -- parse doxtr_fonts from conf.py
- auto_discover_fonts()      -- scan directory via fontTools metadata
- collect_font_files()       -- gather deduplicated file paths for latex_additional_files
- generate_font_features()   -- build \\defaultfontfeatures+ LaTeX blocks
- validate_font_files()      -- warn about missing files or unsafe names
- _deduplicate_registry()    -- keep last entry per name (User > API > AutoDiscover)

Private helpers (used internally by auto_discover_fonts):
- _get_weight_suffix()       -- map usWeightClass integer to a name suffix
- _find_bold_weight()        -- pick the appropriate bold weight for a given weight
"""
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from .config import VALID_FONT_KEYS

logger = logging.getLogger(__name__)

# Permanent list — populated by register_font_family() calls at import/setup time.
# Survives _clear_font_registry() so theme registrations persist across builds.
_api_font_registrations: List[dict] = []

# Working list — rebuilt each build from _api + auto-discover + user config.
_registered_fonts: List[dict] = []

# Late-call guard — set True after config_inited processes fonts.
_fonts_processed: bool = False

# Characters that break LaTeX \defaultfontfeatures+ syntax
_UNSAFE_LATEX_CHARS = set('[]{}#&%\\')

# Standard CSS/OpenType weight class to name suffix mapping
_WEIGHT_NAMES: Dict[int, str] = {
    100: 'Thin',
    200: 'ExtraLight',
    250: 'ExtraLight',   # Some pre-CSS3 fonts use 250/275 for ExtraLight
    275: 'ExtraLight',   # Historical OpenType weight codes
    300: 'Light',
    400: '',               # Base family — no suffix
    500: 'Medium',
    600: 'SemiBold',
    700: 'Bold',
    800: 'ExtraBold',
    900: 'Black',
}

# Internal: custom font renderer registered by theme authors.
# None = use built-in generate_font_features().
_font_renderer_fn: Optional[Callable] = None

# Internal: custom font discoverer registered by theme authors.
# None = use built-in auto_discover_fonts().
_font_discoverer_fn: Optional[Callable] = None


def register_font_family(
    name: str,
    fonts_dir: Union[str, Path],
    upright: str,
    bold: Optional[str] = None,
    italic: Optional[str] = None,
    bold_italic: Optional[str] = None,
    options: str = '',
) -> None:
    """Register a custom font family for LaTeX output.

    Called from a theme's setup() function or at module level. The font files
    will be copied to the LaTeX build directory and \\defaultfontfeatures+ will
    be generated so that \\fontspec{name} resolves correctly.

    Must be called before config_inited fires (priority 900). Calling after
    config_inited emits a warning and the registration is ignored.

    Example — explicit filenames::

        from doxtr_pdf_theme_core import register_font_family
        from pathlib import Path

        register_font_family(
            name='Raleway',
            fonts_dir=Path(__file__).parent / 'fonts',
            upright='Raleway-Regular.ttf',
            bold='Raleway-Bold.ttf',
            italic='Raleway-Italic.ttf',
            bold_italic='Raleway-BoldItalic.ttf',
            options='Numbers=OldStyle',
        )

    Args:
        name: Font family name as used in \\fontspec{Name} and config values.
        fonts_dir: Directory containing the font files (str or Path).
        upright: Filename of the regular/upright font (required).
        bold: Filename of the bold font. Defaults to upright if None.
        italic: Filename of the italic font. Defaults to upright if None.
        bold_italic: Filename of the bold-italic font. Defaults to bold if None.
        options: Extra fontspec options (e.g. 'Scale=MatchLowercase, Numbers=OldStyle').
    """
    global _fonts_processed
    if _fonts_processed:
        logger.warning(
            "[Doxtr Fonts] register_font_family('%s') called after config_inited "
            "has already processed fonts. This registration will be ignored. "
            "Ensure register_font_family() is called at module level or in setup().",
            name,
        )
        return

    entry = {
        'name': name,
        'fonts_dir': Path(fonts_dir),
        'upright': upright,
        'bold': bold or upright,
        'italic': italic or upright,
        'bold_italic': bold_italic or bold or upright,
        'options': options or '',
        'source': 'api',
    }

    # Deduplicate: remove any earlier registration with the same name (last wins)
    _api_font_registrations[:] = [f for f in _api_font_registrations if f['name'] != name]
    _api_font_registrations.append(entry)


def register_font_families(
    fonts_dir: Union[str, Path],
    families: dict,
    pattern: Optional[Union[str, dict]] = None,
    options: str = '',
) -> None:
    """Batch-register multiple font families from a single directory.

    Called from a theme's setup() function or at module level. Each family in
    the ``families`` dict is passed through ``register_font_family()`` after
    optional pattern expansion.

    Example — single pattern::

        from doxtr_pdf_theme_core import register_font_families
        from pathlib import Path

        register_font_families(
            fonts_dir=Path(__file__).parent / 'fonts',
            pattern='Raleway-{weight}.ttf',
            families={
                'Raleway Thin':  {'upright': 'Thin', 'bold': 'Regular',
                                  'italic': 'ThinItalic', 'bold_italic': 'Italic'},
                'Raleway':       {'upright': 'Regular', 'bold': 'Bold',
                                  'italic': 'Italic', 'bold_italic': 'BoldItalic'},
            },
        )

    Example — dual pattern (irregular naming)::

        register_font_families(
            fonts_dir=Path(__file__).parent / 'fonts',
            pattern={
                'upright': 'MyFontB_{weight}_.ttf',
                'italic':  'MyFontB_{weight}.ttf',
            },
            families={
                'MyFont Thin': {'upright': '200', 'bold': '400',
                                'italic': '200i', 'bold_italic': '400i'},
                'MyFont':      {'upright': '400', 'bold': '700',
                                'italic': '400i', 'bold_italic': '700i'},
            },
        )

    Example — literal filenames (no pattern)::

        register_font_families(
            fonts_dir=Path(__file__).parent / 'fonts',
            families={
                'MyFont': {
                    'upright': 'MyFont-Regular.ttf',
                    'bold': 'MyFont-Bold.ttf',
                    'italic': 'MyFont-Italic.ttf',
                    'bold_italic': 'MyFont-BoldItalic.ttf',
                },
            },
        )

    Args:
        fonts_dir: Shared directory containing all font files (str or Path).
        families: Dict mapping family name → face mapping dict.
            Each face mapping has keys: 'upright', 'bold', 'italic', 'bold_italic'.
            Values are filenames (when pattern is None) or weight identifiers
            (when pattern is provided). A per-family 'options' key overrides the
            shared ``options`` argument.
        pattern: Optional filename pattern with ``{weight}`` placeholder.
            - ``str``: single pattern for all four faces.
            - ``dict`` with keys ``'upright'``/``'italic'``: separate patterns for
              upright/bold vs italic/bold-italic faces.
            - ``None``: values in families are treated as literal filenames.
        options: Shared fontspec options applied to all families (can be
            overridden per-family via an 'options' key in the face dict).
    """
    # Validate pattern contains {weight} if provided
    if pattern is not None:
        _patterns = [pattern] if isinstance(pattern, str) else list(pattern.values())
        for p in _patterns:
            if '{weight}' not in p:
                logger.warning(
                    "[Doxtr Fonts] Pattern '%s' does not contain {weight} placeholder. "
                    "Weight values will not be substituted.",
                    p,
                )

    for name, faces in families.items():
        resolved = _expand_pattern(faces, pattern)
        register_font_family(
            name=name,
            fonts_dir=fonts_dir,
            upright=resolved['upright'],
            bold=resolved['bold'],
            italic=resolved['italic'],
            bold_italic=resolved['bold_italic'],
            options=faces.get('options', options) or '',
        )


def _expand_pattern(faces: dict, pattern: Optional[Union[str, dict]]) -> dict:
    """Expand weight identifiers through a pattern into filenames.

    Args:
        faces: Dict with 'upright', 'bold', 'italic', 'bold_italic' values.
            Note: 'upright' can also be keyed as 'regular' as a fallback alias.
        pattern: None (pass-through), str (single), or dict (dual upright/italic).

    Returns:
        Dict with resolved filenames for all four faces.
    """
    upright_val = faces.get('upright', faces.get('regular', ''))
    bold_val = faces.get('bold', upright_val)
    italic_val = faces.get('italic', upright_val)
    bold_italic_val = faces.get('bold_italic', bold_val)

    if pattern is None:
        # Literal filenames — pass through
        return {
            'upright': upright_val,
            'bold': bold_val,
            'italic': italic_val,
            'bold_italic': bold_italic_val,
        }

    if isinstance(pattern, str):
        # Single pattern for all faces
        return {
            'upright': pattern.replace('{weight}', upright_val),
            'bold': pattern.replace('{weight}', bold_val),
            'italic': pattern.replace('{weight}', italic_val),
            'bold_italic': pattern.replace('{weight}', bold_italic_val),
        }

    # Dual pattern: dict with 'upright' and 'italic' keys
    upright_pattern = pattern.get('upright', pattern.get('regular', ''))
    italic_pattern = pattern.get('italic', upright_pattern)

    return {
        'upright': upright_pattern.replace('{weight}', upright_val),
        'bold': upright_pattern.replace('{weight}', bold_val),
        'italic': italic_pattern.replace('{weight}', italic_val),
        'bold_italic': italic_pattern.replace('{weight}', bold_italic_val),
    }


def get_registered_fonts() -> List[dict]:
    """Return a read-only copy of all registered font families.

    Returns the current state of the working registry. Call after
    config_inited has processed fonts for the complete list.

    Use this in tests or debug output to inspect the final registry::

        from doxtr_pdf_theme_core import get_registered_fonts
        for entry in get_registered_fonts():
            print(entry['name'], entry['source'])

    Note: Returns a shallow copy. Do not mutate the returned dicts —
    they share Path objects with the live registry.

    Returns:
        List of font entry dicts. Each entry has keys: 'name', 'fonts_dir',
        'upright', 'bold', 'italic', 'bold_italic', 'options', 'source'.
    """
    return list(_registered_fonts)


def _clear_font_registry() -> None:
    """Reset the working font registry for a fresh build.

    Called at the start of config_inited font processing to ensure
    idempotent builds (test suites, sphinx-autobuild, multiple builds
    in the same process).

    Does NOT clear _api_font_registrations — those persist across builds
    as they are set at module/setup time.

    Also does NOT reset _font_renderer_fn or _font_discoverer_fn —
    those are set at module/setup time and must survive clearing.
    """
    global _fonts_processed
    _registered_fonts.clear()
    _fonts_processed = False


def _set_fonts_processed() -> None:
    """Mark font processing as complete. Called once from config_inited after step 8.

    This setter keeps the write path inside the module that owns the state,
    rather than using a direct module-attribute write from __init__.py.
    """
    global _fonts_processed
    _fonts_processed = True


def register_font_renderer(fn: Callable) -> None:
    r"""Register a custom font feature block generator to replace \defaultfontfeatures+.

    Allows child themes to emit different LaTeX font registration syntax (e.g.
    ``\newfontfamily``, ``\fontspec``, or a completely custom block) instead of
    the default ``\defaultfontfeatures+`` output.

    Must be called at module level or from ``setup()`` — before ``config_inited``
    fires (priority 900). ``builder-inited`` hooks fire after ``config-inited``
    and are therefore too late.

    Args:
        fn: Callable with signature ``fn(registered: List[dict]) -> str``.
            Receives the deduplicated, validated font registry and must return
            a LaTeX string to prepend to ``fontpkg``. Returning an empty string
            suppresses all font feature injection.

    Example::

        from doxtr_pdf_theme_core import register_font_renderer

        def my_renderer(registered):
            lines = []
            for entry in registered:
                lines.append(
                    r'\newfontfamily\\' + entry['name'].replace(' ', '') + 'Font'
                    '{' + entry['upright'] + '}'
                )
            return '\n'.join(lines)

        register_font_renderer(my_renderer)
    """
    global _font_renderer_fn
    if _fonts_processed:
        logger.warning(
            "[Doxtr Fonts] register_font_renderer() called after config_inited has "
            "already processed fonts. This registration will be ignored."
        )
        return
    _font_renderer_fn = fn


def register_font_discoverer(fn: Callable) -> None:
    """Register a custom font auto-discovery function to replace the built-in scanner.

    Allows child themes to implement their own font discovery logic (e.g. reading
    a manifest file, downloading from a registry, or scanning with custom rules)
    instead of the built-in ``fontTools``-based directory scanner.

    Must be called at module level or from ``setup()`` — before ``config_inited``
    fires (priority 900). ``builder-inited`` hooks fire after ``config-inited``
    and are therefore too late.

    The custom discoverer is called once per discovered ``fonts/`` directory (the
    same directories the built-in scans). It must append entries directly to
    ``_registered_fonts`` (via ``register_font_family()`` or direct append) for
    each family it finds.

    Args:
        fn: Callable with signature ``fn(fonts_dir: Path) -> None``.
            Called for each fonts directory that would normally be scanned by
            ``auto_discover_fonts()``.

    Example::

        from doxtr_pdf_theme_core import register_font_discoverer
        from doxtr_pdf_theme_core.fonts import register_font_family
        from pathlib import Path

        def my_discoverer(fonts_dir: Path) -> None:
            manifest = fonts_dir / 'fonts.json'
            if manifest.exists():
                import json
                for entry in json.loads(manifest.read_text()):
                    register_font_family(
                        name=entry['name'],
                        fonts_dir=fonts_dir,
                        upright=entry['regular'],
                    )

        register_font_discoverer(my_discoverer)
    """
    global _font_discoverer_fn
    if _fonts_processed:
        logger.warning(
            "[Doxtr Fonts] register_font_discoverer() called after config_inited has "
            "already processed fonts. This registration will be ignored."
        )
        return
    _font_discoverer_fn = fn


def _deduplicate_registry() -> None:
    """Deduplicate _registered_fonts by name, keeping the LAST entry.

    This ensures the priority hierarchy: User > API > AutoDiscover.
    Since processing appends in order (API → auto-discover → user),
    later entries win on name collision.
    """
    seen: Dict[str, int] = {}
    for i, entry in enumerate(_registered_fonts):
        seen[entry['name']] = i  # last index wins

    # Rebuild list preserving only the last entry per name, in original order
    keep_indices = set(seen.values())
    _registered_fonts[:] = [
        entry for i, entry in enumerate(_registered_fonts)
        if i in keep_indices
    ]


def _get_weight_suffix(weight_class: int) -> str:
    """Map a numeric weight class to the nearest named suffix.

    Non-standard weight values are snapped to the nearest standard weight
    by absolute distance.

    Args:
        weight_class: OpenType usWeightClass integer (100–900).

    Returns:
        Human-readable weight suffix string (e.g. 'Light', 'Bold').
        Empty string for weight 400 (base family, no suffix).
    """
    if weight_class in _WEIGHT_NAMES:
        return _WEIGHT_NAMES[weight_class]
    # Snap to nearest standard weight
    standard_weights = sorted(_WEIGHT_NAMES.keys())
    closest = min(standard_weights, key=lambda w: abs(w - weight_class))
    return _WEIGHT_NAMES[closest]


def _find_bold_weight(by_weight: dict, current_weight: int) -> int:
    """Find the appropriate bold weight for a given weight class.

    Strategy:
    - If current is 400 or below, bold target is 700 (if available) or next higher.
    - If current is 500+, bold target is current + 200 (capped at 900) or next higher.
    - Falls back to current weight if no heavier weight exists.

    Args:
        by_weight: Dict mapping weight class → list of font entries.
        current_weight: Weight class to find a bold pairing for.

    Returns:
        The weight class to use as the bold face.
    """
    if current_weight <= 400:
        target = 700
    else:
        target = min(current_weight + 200, 900)

    available = sorted(by_weight.keys())
    # Exact match
    if target in by_weight:
        return target
    # Next weight >= target
    higher = [w for w in available if w >= target]
    if higher:
        return higher[0]
    # Fallback: highest available above current
    above_current = [w for w in available if w > current_weight]
    if above_current:
        return above_current[-1]
    return current_weight


def auto_discover_fonts(fonts_dir: Union[str, Path]) -> None:
    """Scan a directory for .ttf/.otf files and register families from metadata.

    Uses fontTools to read the font's internal name table and OS/2 table to
    determine family name, weight class, and italic flag. Groups files into
    families and registers them.

    Skips families whose name is already registered (API takes priority).
    Detects variable fonts (fvar table) and registers them as a single base
    family rather than generating per-weight sub-families.

    Requires fonttools>=4.0. If not installed, logs an info message and returns
    without error. Modes 1 and 2 (explicit registration) work without fonttools.

    Args:
        fonts_dir: Path to scan for .ttf and .otf font files.
    """
    try:
        from fontTools.ttLib import TTFont  # type: ignore[import]
    except ImportError:
        logger.info(
            "[Doxtr Fonts] fonttools not installed; font auto-discovery disabled. "
            "Install with: pip install doxtr-pdf-theme-core[fonts]"
        )
        return

    fonts_dir = Path(fonts_dir)
    if not fonts_dir.is_dir():
        return

    # Collect metadata from all font files
    font_entries: List[dict] = []
    variable_fonts: List[dict] = []  # Track variable fonts separately

    for ext in ('*.ttf', '*.otf'):
        for font_path in sorted(fonts_dir.glob(ext)):
            try:
                with TTFont(font_path) as font:
                    name_table = font['name']

                    # Preferred family (nameID 16) is the canonical grouping name.
                    # Falls back to nameID 1 (family) if 16 is absent.
                    pref_family = name_table.getName(16, 3, 1, 0x0409)
                    family_rec = name_table.getName(1, 3, 1, 0x0409)
                    chosen = pref_family or family_rec
                    if not chosen:
                        continue
                    family_name = chosen.toUnicode()
                    if not family_name:
                        continue

                    # Detect variable fonts (fvar table present)
                    is_variable = 'fvar' in font

                    os2 = font.get('OS/2')
                    weight_class = os2.usWeightClass if os2 else 400
                    is_italic = bool(os2.fsSelection & 1) if os2 else False

                    entry = {
                        'path': font_path,
                        'filename': font_path.name,
                        'family': family_name,
                        'weight': weight_class,
                        'italic': is_italic,
                        'variable': is_variable,
                    }

                    if is_variable:
                        variable_fonts.append(entry)
                    else:
                        font_entries.append(entry)

            except Exception as e:
                logger.debug(
                    "[Doxtr Fonts] Could not read metadata from %s: %s",
                    font_path.name, e,
                )

    # Get already-registered names to avoid overriding API registrations
    existing_names = {f['name'] for f in _registered_fonts}

    # Register variable fonts as single base families
    for entry in variable_fonts:
        if entry['family'] in existing_names:
            continue
        logger.info(
            "[Doxtr Fonts] Variable font detected: %s (%s). "
            "Registered as base family. For full weight axis control, "
            "use register_font_family() with explicit options.",
            entry['family'], entry['filename'],
        )
        _registered_fonts.append({
            'name': entry['family'],
            'fonts_dir': fonts_dir,
            'upright': entry['filename'],
            'bold': entry['filename'],
            'italic': entry['filename'],
            'bold_italic': entry['filename'],
            'options': '',
            'source': 'auto_discover',
        })
        existing_names.add(entry['family'])

    if not font_entries:
        return

    # Group static fonts by family name
    families: Dict[str, list] = {}
    for entry in font_entries:
        families.setdefault(entry['family'], []).append(entry)

    # For each family, group by weight and register sub-families
    for family_name, entries in sorted(families.items()):
        # Group by weight class
        by_weight: Dict[int, list] = {}
        for entry in entries:
            by_weight.setdefault(entry['weight'], []).append(entry)

        for weight_class, weight_entries in sorted(by_weight.items()):
            suffix = _get_weight_suffix(weight_class)
            registered_name = f"{family_name} {suffix}".strip() if suffix else family_name

            if registered_name in existing_names:
                continue  # API registration takes priority

            # Find upright and italic for this weight
            upright_entry = next((e for e in weight_entries if not e['italic']), None)
            italic_entry = next((e for e in weight_entries if e['italic']), None)

            if not upright_entry:
                continue  # Need at least an upright face

            # Find bold: look for appropriate higher weight in same family
            bold_weight = _find_bold_weight(by_weight, weight_class)
            bold_entry = next(
                (e for e in by_weight.get(bold_weight, []) if not e['italic']), None
            )
            bold_italic_entry = next(
                (e for e in by_weight.get(bold_weight, []) if e['italic']), None
            )

            _registered_fonts.append({
                'name': registered_name,
                'fonts_dir': fonts_dir,
                'upright': upright_entry['filename'],
                'bold': bold_entry['filename'] if bold_entry else upright_entry['filename'],
                'italic': italic_entry['filename'] if italic_entry else upright_entry['filename'],
                'bold_italic': (
                    bold_italic_entry['filename'] if bold_italic_entry
                    else (bold_entry['filename'] if bold_entry else upright_entry['filename'])
                ),
                'options': '',
                'source': 'auto_discover',
            })
            existing_names.add(registered_name)


def process_user_font_config(doxtr_fonts: dict, confdir: str) -> None:
    """Parse the doxtr_fonts user config dict and register each family.

    User-registered fonts override theme fonts with the same name.
    Each entry in ``doxtr_fonts`` can use either explicit filenames or
    pattern + weights mode (see ``doxtr_fonts`` config reference).

    Args:
        doxtr_fonts: Dict from conf.py. Keys are family names, values are
            dicts with 'dir', 'upright', 'bold', 'italic', 'bold_italic',
            and optionally 'pattern', 'weights', and 'options'.
        confdir: Sphinx confdir for resolving relative 'dir' paths.
    """
    for name, spec in doxtr_fonts.items():
        # Warn about unknown keys (catches typos early)
        unknown = set(spec.keys()) - VALID_FONT_KEYS
        if unknown:
            logger.warning(
                "[Doxtr Fonts] Unknown keys in doxtr_fonts entry '%s': %s. "
                "Valid keys: %s",
                name, sorted(unknown), sorted(VALID_FONT_KEYS),
            )

        # Remove any existing registration with the same name (user wins)
        _registered_fonts[:] = [f for f in _registered_fonts if f['name'] != name]

        fonts_dir = Path(spec.get('dir', '.'))
        if not fonts_dir.is_absolute():
            fonts_dir = Path(confdir) / fonts_dir

        pattern = spec.get('pattern', None)
        options = spec.get('options', '')

        if pattern:
            # Pattern mode: weight identifiers in 'weights' sub-dict
            weights = spec.get('weights', {})
            if not weights:
                logger.warning(
                    "[Doxtr Fonts] Font '%s': 'pattern' is set but 'weights' is missing "
                    "or empty. All faces will resolve to empty filenames. Add a 'weights' "
                    "dict with 'upright', 'bold', 'italic', 'bold_italic' keys.",
                    name,
                )
            upright_w = weights.get('upright', '')
            faces = {
                'upright': upright_w,
                'bold': weights.get('bold', upright_w),
                'italic': weights.get('italic', upright_w),
                'bold_italic': weights.get('bold_italic', weights.get('bold', upright_w)),
            }
            resolved = _expand_pattern(faces, pattern)
        else:
            # Explicit filenames
            upright = spec.get('upright', '')
            resolved = {
                'upright': upright,
                'bold': spec.get('bold', upright),
                'italic': spec.get('italic', upright),
                'bold_italic': spec.get('bold_italic', spec.get('bold', upright)),
            }

        _registered_fonts.append({
            'name': name,
            'fonts_dir': fonts_dir,
            'upright': resolved['upright'],
            'bold': resolved['bold'],
            'italic': resolved['italic'],
            'bold_italic': resolved['bold_italic'],
            'options': options,
            'source': 'user_config',
        })


def collect_font_files(registered: List[dict]) -> List[str]:
    """Return deduplicated list of absolute font file paths.

    These paths are added to config.latex_additional_files so Sphinx
    copies them to the LaTeX build directory.

    Args:
        registered: List of font entry dicts from the working registry.

    Returns:
        Deduplicated list of absolute file path strings.
    """
    seen: set = set()
    files: List[str] = []
    for entry in registered:
        for key in ('upright', 'bold', 'italic', 'bold_italic'):
            filename = entry[key]
            if not filename:
                continue
            path = str(entry['fonts_dir'] / filename)
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def generate_font_features(registered: List[dict]) -> str:
    r"""Generate \\defaultfontfeatures+ blocks for all registered families.

    Assumes _deduplicate_registry() has already been called, so there are
    no duplicate names in the list.

    The generated block for each family looks like::

        \\defaultfontfeatures+[FamilyName]{
          Path=./,
          UprightFont=Family-Regular.ttf,
          BoldFont=Family-Bold.ttf,
          ItalicFont=Family-Italic.ttf,
          BoldItalicFont=Family-BoldItalic.ttf,
          Scale=MatchLowercase
        }

    Args:
        registered: List of font entry dicts from the working registry.

    Returns:
        LaTeX string containing all \\defaultfontfeatures+ blocks,
        joined by newlines. Ready to prepend to the fontpkg element.
    """
    blocks = []

    for entry in registered:
        if not entry.get('upright'):
            logger.warning(
                "[Doxtr Fonts] Skipping font family '%s' in feature generation: "
                "'upright' face filename is empty.",
                entry.get('name', '?'),
            )
            continue

        options_str = ''
        if entry['options']:
            options_str = f",\n  {entry['options']}"

        blocks.append(
            f"\\defaultfontfeatures+[{entry['name']}]{{\n"
            f"  Path=./,\n"
            f"  UprightFont={entry['upright']},\n"
            f"  BoldFont={entry['bold']},\n"
            f"  ItalicFont={entry['italic']},\n"
            f"  BoldItalicFont={entry['bold_italic']}{options_str}\n"
            f"}}"
        )
    return '\n'.join(blocks)


def validate_font_files(registered: List[dict]) -> None:
    """Warn about registered font files that don't exist on disk and
    font names containing LaTeX-unsafe characters.

    This runs during config_inited. Missing files don't abort the build
    (LuaLaTeX will produce a more specific error if the font is actually used),
    but the early warning helps theme authors catch typos quickly.

    Args:
        registered: List of font entry dicts from the working registry.
    """
    for entry in registered:
        # Check font name for LaTeX special characters
        unsafe = ''.join(c for c in entry['name'] if c in _UNSAFE_LATEX_CHARS)
        if unsafe:
            logger.warning(
                "[Doxtr Fonts] Font family name '%s' contains characters that may "
                "break LaTeX \\defaultfontfeatures+ syntax: %s",
                entry['name'],
                unsafe,
            )

        # Check font files exist
        for key in ('upright', 'bold', 'italic', 'bold_italic'):
            filename = entry[key]
            if not filename:
                continue
            path = entry['fonts_dir'] / filename
            if not path.is_file():
                logger.warning(
                    "[Doxtr Fonts] Font file not found: %s "
                    "(family '%s', face '%s', dir '%s')",
                    filename, entry['name'], key, entry['fonts_dir'],
                )


def inject_font_features(
    latex_elements: dict,
    dynamic_fontpkg: str,
    registered: List[dict],
) -> None:
    r"""Inject \defaultfontfeatures+ blocks into latex_elements['fontpkg'].

    Centralises the fontpkg injection logic so it can be tested directly
    and reused by child themes.

    Behaviour:
    - If ``registered`` is empty, falls back to
      ``latex_elements.setdefault('fontpkg', dynamic_fontpkg)``.
    - If a user-supplied ``fontpkg`` already exists in ``latex_elements``,
      font features are prepended to it.
    - Otherwise, ``fontpkg`` is built as font features + ``dynamic_fontpkg``.

    The active renderer (``_font_renderer_fn`` if registered, otherwise
    ``generate_font_features``) is used to build the feature block.

    Args:
        latex_elements: The sphinx ``config.latex_elements`` dict (mutated in place).
        dynamic_fontpkg: The core-generated fontpkg string (``\\setmainfont`` etc.).
        registered: The deduplicated font registry from ``get_registered_fonts()``.
    """
    if not registered:
        latex_elements.setdefault('fontpkg', dynamic_fontpkg)
        return
    _renderer = _font_renderer_fn or generate_font_features
    _font_features_block = _renderer(registered)
    if 'fontpkg' in latex_elements:
        # User has explicit fontpkg — prepend our \defaultfontfeatures+ blocks
        # so font resolution works regardless of user customisation.
        latex_elements['fontpkg'] = _font_features_block + '\n' + latex_elements['fontpkg']
    else:
        # Normal path: build full fontpkg with features prepended.
        latex_elements['fontpkg'] = _font_features_block + '\n' + dynamic_fontpkg
