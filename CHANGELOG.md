# Changelog

## 1.1.0

### New Features

#### Topic & Contents Boxes (`doxtr_topic`, `doxtr_contents`)
- **New element type: `.. topic::` and `.. contents::`** styled via tcolorbox with a 45° top-right cutaway geometry (`cutaway_depth`), thick bottom frame (`bottom_frame_height`, `bottom_frame_color`), and full WCAG enforcement on title colors.
- New config sections `doxtr_topic` and `doxtr_contents` in `CORE_CONFIG_MANIFEST`.
- New `.tex_t` templates: `latex_styles/topic/default.tex_t`, `latex_styles/topic/cutaway.tex_t`, `latex_styles/contents/default.tex_t`.
- New absolute fallbacks `DEFAULT_TOPIC_STYLE` and `DEFAULT_CONTENTS_STYLE` in `core_fallbacks.py`.
- New `process_topics_ast` processor in `ast_processors/topics.py` (registered at priority 990 in `setup()`).
- New `doxtr_enable_topics_processor` flag (default `True`) to disable the processor.
- New config validation sets `VALID_TOPIC_KEYS` and `VALID_CONTENTS_KEYS` in `config.py`.

#### Draft Watermark (`doxtr_draft`)
- **New element type: draft watermarks** rendered via `latex_styles/draft/default.tex_t` using TikZ.
- New config section `DOXTR_DRAFT` in `core_config.py` with `text`, `date_format`, `timezone`, `color`, `font_size`, `font` keys.
- Supports `{date}` and `{project_version}` placeholders in draft text.
- `dd:` color expressions resolved on `doxtr_draft.color`.

#### Hyperlink Color Control (`doxtr_links`)
- **New config section `doxtr_links`** with `inner_color` and `outer_color` keys.
- Colors injected into `sphinxsetup` as `InnerLinkColor`/`OuterLinkColor` using the `{rgb}` model required by Sphinx's hyperref integration.
- Respects existing user `sphinxsetup` values (does not overwrite explicit user settings).
- New `DOXTR_LINKS` default dict in `core_config.py`.

#### Font System (`fonts.py`)
- **New dedicated `fonts.py` module** extracted from `__init__.py` containing all font registration and processing logic.
- `register_font_family(name, fonts_dir, upright, bold, italic, bold_italic, options)` — explicit filenames API.
- `register_font_families(fonts_dir, families, pattern, options)` — weight-pattern batch registration with single-pattern, dual-pattern, and literal (`pattern=None`) modes.
- `get_registered_fonts()` — read-only snapshot of the font registry (for tests and debug).
- `register_font_renderer(fn)` — replace the default `\defaultfontfeatures+` generator.
- `register_font_discoverer(fn)` — replace the built-in fontTools directory scanner.
- `inject_font_features(latex_elements, dynamic_fontpkg, registered)` — public API for injecting font blocks into `fontpkg`.
- `auto_discover_fonts(style_paths)` — scans `fonts/` siblings of theme `latex_styles/` directories (requires `fonttools>=4.0`).
- `process_user_font_config(doxtr_fonts, confdir)` — processes the new `doxtr_fonts` user config dict.
- Variable font detection: families with an `fvar` table are registered as a single base family with a log recommendation to use `register_font_family()` for full axis control.
- Parent-package scan guard: prevents double-scanning when the `fonts/` dir is a sibling of a Python package.
- `doxtr_fonts` user config dict in `conf.py` for declarative font registration without writing Python. Supports explicit filename mode and `pattern`+`weights` mode. User registrations take priority over theme API and auto-discover.
- Optional extras: `pip install doxtr-pdf-theme-core[fonts]` for auto-discovery; `pip install doxtr-pdf-theme-core[images]` for image processing.
- `pyproject.toml` updated with `[fonts]` and `[images]` optional dependency groups.

#### Image Processing (`image_processing.py`)
- **New dedicated `image_processing.py` module** extracted from `__init__.py` containing all image recolouring and adaptation logic.
- Dark mode image pipeline: grayscale recolouring, HSL lightness inversion for bright color images, `_dark` variant detection.
- Page adaptation image pipeline: edge-connected white flood-fill replacement with the target page background color.
- Shared `_iter_processable_images()` generator used by both pipelines.
- `_ALPHA_OPACITY_THRESHOLD` neutral alias (replaces `_DARK_ALPHA_THRESHOLD`).
- `no-auto-image-adapt` RST class skips all image processing (replaces deprecated `no-dark-mode-auto-invert`).

#### Dark Mode Improvements
- **`doxtr_dark_mode_strategy`** config: `'auto'` (luminance-based), `'invert'` (standard dark), `'passthrough'` (skip inversion for light-alternative pages like solarized/sepia). Default `'auto'`.
- `doxtr_dark_mode_strategy_resolved` read-only computed strategy (set by `config_inited`).
- **`doxtr_dark_text_color`** config: explicit dark mode body text color override. Auto-calculated via WCAG when not set.
- **`doxtr_dark_recolor_grayscale`** (default `True`) and **`doxtr_dark_invert_color_images`** (default `True`) fine-grained image processing controls.
- **`DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS`** in `core_config.py`: auto-generated dark semantic palette from light palette (inverted for `invert` strategy, passed through for `passthrough`).
- `hex_dark_invert(hex_color)` public utility function (exported from package `__init__`).
- `_DARK_STRATEGY_LUMINANCE_THRESHOLD` and `_VALID_DARK_STRATEGIES` exported for child theme introspection.

#### Page Color Adaptation
- **`doxtr_adapt_colors_to_page`** config: `'auto'` (default), `True`, `False`. Luminance-proportional color remapping when page background differs from the theme's designed-for background.
- `adapt_color_to_page(hex_color, designed_bg, actual_bg, compress_dark, compress_light)` public API.
- `_compute_adaptation_compression()` and `_get_luminance()` public utilities for child themes.
- `_ADAPTATION_LUMINANCE_THRESHOLD` exported constant.
- `\pagecolor` emitted in preamble when adaptation is active and page ≠ `#FFFFFF`.
- Processing order: dark mode → page adaptation → `dd:` resolution → WCAG enforcement → template rendering.

#### Extensibility API
- **`register_preamble_hook(fn, position)`** — inject LaTeX into the document preamble at one of four positions: `before_packages`, `after_packages`, `before_styles`, `after_styles`. No need to copy `preamble.tex_t`.
- **`register_config_transform(fn)`** — post-merge config transform hook. Called after three-tier merge but before template rendering. Signature: `fn(sections, palette, config) -> None`.
- **`register_style_type(name, subdir, fallback_fn, config_section_factory, color_keys, preamble_var)`** — register a fully custom element style type with template resolution, color processing, and WCAG enforcement. Collisions with built-in `preamble_var` names are rejected.
- **`register_color_operation(name, fn)`** in `utils.py` — register custom `dd:` color expression operations. Signature: `fn(hex_color, arg) -> hex_color`. Built-in operation names (`lighten`, `darken`, `contrast`) cannot be overridden.
- **`register_ast_processor(fn, doctype, priority)`** updated: `doctype` parameter added (default `None` = latex-only); `priority` parameter added (default 992). Late calls (after `builder-inited`) now emit a warning.
- `_custom_style_types`, `_preamble_hooks`, `_config_transform_hooks` runtime registries, checked via lazy import in `templates.py` to avoid circular import.

#### `doxtr_globals` Wrapper Key Support
- Config sections now support `light` / `dark` wrapper dicts in `doxtr_globals` (and all other `doxtr_*` config dicts). `_unwrap_mode()` in `config.py` extracts the correct nested values before merging.
- `validate_wrapper_keys()` in `config.py` warns on unknown top-level wrapper keys.
- `make_collect_dark_fn(config, theme_defaults)` factory in `config.py` builds the dark-mode section collector used in `_stage_merge_and_resolve`.

#### Other Config Additions
- **`doxtr_strict_mode`** (default `False`) — raise error on missing templates instead of falling back.
- **`doxtr_cache_templates`** (default `True`) — control Jinja2 template caching.
- **`doxtr_patch_admonition_translator`** (default `True`) — control patching of Sphinx's `LaTeXTranslator` for generic admonition tags. Set `False` if a child theme provides its own translator.
- **`doxtr_enable_*_processor`** flags for each AST processor (`container`, `table`, `codeblock`, `epigraph`, `sidebar`, `highlights`, `needs`, `topics`) — default `True`.
- **`main_font_size`** global: base body text font size (used as LaTeX pointsize and reference for `size_factor` calculations in headings).
- **`topic_style_path`** and **`contents_style_path`** custom resolution path globals.

#### `number_match_title_xheight` Heading Feature
- New `number_match_title_xheight` heading config key (per-level and global). When `True`, scales the chapter/section number so its cap height matches the title's x-height.
- New `tests/test_number_match_title_xheight.py` unit tests.

### Refactoring

- **`__init__.py` decomposed**: font logic extracted to `fonts.py`, image processing to `image_processing.py`. `__init__.py` reduced from ~2800 lines to the core pipeline (config, template, preamble assembly).
- **`config_inited()` split into three named stages**: `_stage_merge_and_resolve()`, `_stage_build_and_render_preamble()`, `_stage_assemble_output()` for readability and testability.
- **`_wcag_enforce_title_colors()`** and **`_process_box_section()`** extracted as internal helpers.
- **`_resolve_sty_file()`** extracted for `.sty` override path resolution.
- **`_auto_detect_dark_strategy()`** and **`_build_dark_section()`** extracted as internal helpers.
- `templates.py`: `_get_style_meta()` helper added to check built-in `STYLE_TYPES`/`STYLE_FALLBACKS` then the runtime `_custom_style_types` registry (lazy import avoids circular dependency).
- `utils.py`: `register_color_operation()` and `_custom_color_operations` registry moved here from `__init__.py`. `_RE_SAFE_NAME` precompiled regex moved here and shared with `ast_processors/containers.py`.
- `DOXTR_GLOBALS` in `core_config.py` now uses a `light`/`dark` wrapper structure.
- Legacy flat-key compatibility list `_LEGACY_GLOBAL_KEYS` maintained in `__init__.py` for one minor version.

### Tests

- **`test_harness/test_fonts.py`** (661 lines): `TestRegisterFontFamily`, `TestRegisterFontFamilies`, `TestExpandPattern`, `TestClearFontRegistry`, `TestDeduplicateRegistry`, `TestCollectFontFiles`, `TestGenerateFontFeatures`, `TestValidateFontFiles`, `TestProcessUserFontConfig`, `TestAutoDiscoverFonts`, `TestFindBoldWeight`, `TestFontpkgInjection`, `TestParentScanGuard`.
- **`test_harness/test_extensibility_phase4.py`** (400 lines): `TestRegisterColorOperation`, `TestRegisterConfigTransform`, `TestWcagPairsStyleType`.
- **`test_harness/test_ast_processors.py`** (758 lines): `TestContainersAST`, `TestTablesAST`, `TestCodeblocksAST`, `TestEpigraphsAST`, `TestHighlightsAST`, `TestTopicsAST`, `TestSidebarsAST`, `TestNeedsAST`, `TestNonLatexBuilderSkip`.
- **`test_harness/test_pipeline.py`** (480 lines): `TestGlobalsMerge`, `TestSectionMerging`, `TestSemanticPalette`, `TestDarkMode`, `TestPageAdaptation`, `TestPipelineStructure`.
- **`test_harness/test_utils.py`** extended: `_split_hex_opacity` tests, dark invert tests (`TestHexDarkInvert`), three-tier merge mutation guards, explicit-path scope enforcement tests.
- **`tests/test_number_match_title_xheight.py`**: full coverage for the `number_match_title_xheight` feature.

### Documentation

- `README.md` updated with font bundling guide (Mode 1 explicit, Mode 2 weight-pattern, Mode 3 auto-discover), `doxtr_fonts` declarative config reference, dark mode strategy docs, page color adaptation docs, extensibility API (`register_preamble_hook`, `register_config_transform`, `register_style_type`, `register_color_operation`).

### CI

- `.github/workflows/test-harness.yml`: removed redundant `pip uninstall` step and version-print debug step (now handled by the install script).
- `pyproject.toml`: added `[project.optional-dependencies]` groups `fonts` (`fonttools>=4.0`) and `images` (`numpy>=1.20`, `scipy>=1.7`, `Pillow>=9.0`); added corresponding `[project.optional-dependencies.dev]` entries.

### Breaking Changes

- **`no-dark-mode-auto-invert` RST class renamed** to `no-auto-image-adapt` (affects all `.. image::` and `.. figure::` directives using the old class). Deprecated in 1.0.42, removed in 1.1.0.
- **`doxtr_dark_image_exclude_patterns`** renamed to `doxtr_image_exclude_patterns`. Old name deprecated in 1.0.42, removed in 1.1.0.
- **`files.py` removed**: previously contained font/file utilities that are now split between `fonts.py` and `image_processing.py`.

---

## 1.0.42

### Features

- **Page-adaptive image backgrounds**: When page color adaptation is active and the page background differs from `#FFFFFF`, white image backgrounds are now automatically replaced with the page color using a flood-fill algorithm that detects edge-connected white regions while preserving internal white areas (text on colored bars, enclosed white pockets)
- **New config values**: `doxtr_adapt_image_backgrounds` (default `True`), `doxtr_adapt_image_white_fuzz` (default `5`), `doxtr_image_exclude_patterns` (replaces deprecated `doxtr_dark_image_exclude_patterns`)

### Refactoring

- **Shared image iterator**: Extracted `_iter_processable_images()` shared generator to eliminate duplication between dark mode and page adaptation image pipelines
- **Neutral alias**: Introduced `_ALPHA_OPACITY_THRESHOLD` as neutral alias for `_DARK_ALPHA_THRESHOLD`

### Breaking Changes

- **RST class renamed**: `no-dark-mode-auto-invert` → `no-auto-image-adapt`
- **Config renamed**: `doxtr_dark_image_exclude_patterns` → `doxtr_image_exclude_patterns` (old name deprecated, removed in v1.1.0)

---
