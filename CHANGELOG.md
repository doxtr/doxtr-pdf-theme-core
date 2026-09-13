# Changelog

## 1.1.10

### Bug Fixes

#### Tall portrait tables overflowing into the footer

- **Fixed narrow, multi-page tables running into the footer** (and off the bottom of the page). The auto-landscape processor previously wrapped narrow Sphinx tables (below `doxtr_landscape_min_columns`) in the legacy `doxtrautolandscape` environment, which typesets content into an *unbreakable* savebox/minipage. A table taller than `\textheight` could not fit and overflowed the footer. Sphinx tables always fill `\linewidth`, so the environment's width-based rotation check could never fire for them anyway.
- Narrow Sphinx tables are no longer wrapped in `doxtrautolandscape`. Tall portrait tables are instead **promoted to `longtable`** so they break across pages with repeated headers and "continued" markers.
- New config value `doxtr_table_longtable_row_threshold` (default `12`) — minimum row count (header + body) at which a narrow portrait table is promoted to `longtable`. Set to `0` to disable promotion.
- **Defense-in-depth**: the `doxtrautolandscape` environment now detects an over-tall box (`> \textheight`) and emits a `\PackageWarning{doxtr}` diagnostic instead of silently overflowing, guiding authors to use a breakable environment.
- Hardened `doxtr_landscape_skip_table_classes` handling against a `None` config value.
- **Enable `parallel_write_safe: True`** — The extension now correctly declares itself safe for parallel writing. All `doctree-resolved` and `build-finished` handlers guard on `builder.format == 'latex'` (which is inherently serial), and all module-level state is read-only during the write phase. This eliminates the spurious Sphinx warning and unblocks parallel writing for HTML/other builders when this extension is also loaded.

### New Features

#### Modular URL Line-Break Guard

- **Added a URL line-break guard** that makes Sphinx inline links (`\url` / `\sphinxurl` / `\sphinxhref`) break-friendly, preventing long query-string-heavy URLs (UUIDs, percent-encoded parameters, base64 blobs, tokens with no hyphens or spaces) from overflowing the right margin as overfull hboxes. The guard adds inter-character stretch via `\Urlmuskip` and extends `\UrlBreaks` with structural (and optionally alphanumeric) break points.
- New config value `doxtr_url_break_guard` (default `True`) — master switch; set `False` to disable the guard entirely (e.g. when a child theme handles URL breaking differently).
- New config value `doxtr_url_break_aggressive` (default `True`) — when the guard is on, also allow breaks between plain letters and digits so unbroken alphanumeric tokens can wrap. Set `False` for a conservative structural-only break set.
- New config value `doxtr_url_break_path` — custom folder for the `url_break/default.tex_t` override (parity with the other `*_style_path`/`*_path` custom-resolution keys).
- **Fully overridable** via `latex_styles/url_break/default.tex_t`, resolved through the same hierarchical template engine as every other style type (custom path → user project → theme paths → core file → absolute fallback `DEFAULT_URL_BREAK_STYLE`). The guard is *not* inlined in `preamble.tex_t`; it is injected via `register_preamble_hook(..., position='after_packages')` so it lands after `url`/`hyperref` and survives child-theme whole-preamble overrides.
- The inter-character stretch is exposed as the redefinable macro `\doxtrurlmuskip` (assigned at `\begin{document}` so a later redefinition via `register_preamble_hook` is honoured). Extra break points can be appended with `\g@addto@macro\UrlBreaks{...}` via a preamble hook.

#### Parallel image processing

- **Parallel image processing** — Dark mode recolouring and page-adaptation background replacement now process images in parallel via `ProcessPoolExecutor`. Configurable via `doxtr_image_parallel_workers` (default: `'auto'` = `min(cpu_count, 8)`). Set to `1` for sequential processing (debugging). For projects with many images, this significantly reduces `build-finished` time.
- **`register_image_processor(fn, position)`** — New public API for child themes to completely replace the built-in dark-mode (`'dark'`) or page-adaptation (`'adapt'`) image pipeline with a custom implementation.

### Tests

- Added `TestLandscapeAutoWrap` in `test_harness/test_ast_processors.py` covering: narrow tables not wrapped, short tables kept as `tabular`, tall tables promoted to `longtable`, zero-threshold disables promotion, wide tables still wrapped in `doxtradaptivelandscape`, and `no-landscape` opt-out.
- Added over-tall-box guard assertions to `tests/test_global_overflow_preamble.py`.
- Added `tests/test_url_break_guard.py` covering config registration, `template_vars` threading, fallback rendering, aggressive/conservative branches, disabled = emit-nothing, `\providecommand` redefinability, `\AtBeginDocument` deferral, the not-inlined-in-preamble guarantee, style-type resolvability, override precedence, and `.tex_t`/`DEFAULT_URL_BREAK_STYLE` sync.

## 1.1.8

### Features

#### Styled `.. todo::` directive (sphinx.ext.todo)

- **Added a themeable `ddtodobox` tcolorbox** for the `sphinx.ext.todo` `.. todo::` directive, replacing Sphinx's default `sphinxtodo` environment. Rendered as a flat "tile" box with a coloured `flip title={sharp corners}` strip (default: strong-red strip, light-red content). Participates in the three-tier merge, dark mode, page adaptation, `dd:` resolution, WCAG title-contrast enforcement, and the pagegoal overflow guard.
- Respects `sphinx.ext.todo`'s `todo_include_todos` gate — todos hidden by Sphinx's default (`False`) are not rendered.
- New config section `doxtr_todo` (see README) with `title_*`/`content_*` keys mirroring `doxtr_highlights`.
- New `doxtr_todo_style_path` (custom `.tex_t` folder) and `doxtr_enable_todo_processor` (default `True`) config values.
- Fully overridable via `latex_styles/todo/default.tex_t`; absolute fallback `DEFAULT_TODO_STYLE` provided. No-ops gracefully when `sphinx.ext.todo` is not loaded.

### Bug Fixes

#### FontAwesome 7 Icon Name Compatibility

- **Fix: rename hardcoded FontAwesome 5 icon names to their FontAwesome 7 equivalents** — A TeX Live update (revision dated 2025-11-06) installed `fontawesome7.sty`. Sphinx auto-selects the newest available icon package, so its default `iconpackage` switched from `fontawesome5` to `fontawesome7`. Several icon names were renamed in FontAwesome 6/7, so the previously hardcoded fa5 names (e.g. `\faIcon{info-circle}`) no longer exist in fa7, producing a fatal `"Package fontawesome7 Error: The requested icon info-circle was not found."` during the LaTeX build (no PDF produced).
- Renamed the seven affected icons in the core defaults (`core_config.py`): `info-circle` → `circle-info`, `exclamation-triangle` → `triangle-exclamation`, `times-circle` → `circle-xmark`, `external-link-alt` → `up-right-from-square`, `file-alt` → `file-lines`, `cogs` → `gears`, `columns` → `table-columns`. All other icons the theme uses already have valid fontawesome7 names.
- Updated the matching icon examples in `README.md` to keep the documentation consistent with the code.
- **Note:** fontawesome5 and fontawesome7 use mutually exclusive names for these icons. This change requires fontawesome7 to be the active package. Themes or projects that pin `iconpackage=fontawesome5` in `sphinxsetup` should remove the pin (or set it to `fontawesome7`).

### Tests

- Added `tests/test_todo_style.py` (template + fallback + config-wiring markers) and `TestTodoAST` / `TestPagegoalCapInTodo` classes in `test_harness/test_ast_processors.py` (wrapping, disabled flag, non-latex skip, `todo_include_todos` gate, idempotency, title escaping, pagegoal cap ordering).
- Added `tests/test_fa7_icons.py` verifying the FontAwesome 7 icon-name migration.

## 1.1.7

### Bug Fixes

#### Sphinx \DUrole Paragraph Tolerance for sphinx-needs Multi-Value Fields

- **Fix: redefine `\DUrole` as `\long` to accept `\par` tokens** — sphinx-needs renders multi-value fields (e.g. semicolon-separated `fully_qualified_domain_names`) with blank lines between entries. In LaTeX, a blank line produces a `\par` token. Sphinx defines `\DUrole` with `\providecommand*` (short form), which rejects `\par` inside its arguments, causing a fatal `"Paragraph ended before \DUrole was complete."` error. The fix redefines `\DUrole` with `\renewcommand` (without `*`) so it becomes a `\long` command that accepts paragraph breaks. The replacement preserves the original Sphinx dispatch logic (`DUrole<role>` → `docutilsrole<role>` → passthrough).
- The redefinition is placed in the preamble after `\usepackage{sphinx}` has established the original definition, alongside other Sphinx compatibility fixes.
- Child themes can override this by providing their own `\DUrole` redefinition via `register_preamble_hook` at the `after_packages` position.
- Added `doxtr_durole_par_fix` config toggle (default `True`) to allow disabling the fix, consistent with `doxtr_tabulary_overflow_guard` and `doxtr_pagegoal_overflow_guard`.

### Tests

- Added `tests/test_durole_preamble.py` with tests verifying the `\DUrole` redefinition block: presence, no star form, `\makeatletter`/`\makeatother` wrapping, comment header, dispatch logic, placement ordering, uniqueness, fallback passthrough, and Jinja2 conditional guard.

## 1.1.4

### Bug Fixes

#### Microtype Kerning Incompatible with LuaLaTeX

- **Fix: disable microtype `kerning` by default** — The microtype package does not support the `kerning` feature with LuaLaTeX or XeLaTeX. It is explicitly rejected in `microtype-luatex.def` with a fatal error that prevents `latexmk` from completing its multi-pass cycle. Since doxtr-pdf-theme-core requires LuaLaTeX, the previous `kerning: True` default was broken out of the box for the primary use case.
- Default changed from `'kerning': True` to `'kerning': False` in `DOXTR_MICROTYPE`.
- Users on pdfTeX can still opt in via `doxtr_microtype = {'kerning': True}` in their `conf.py`.
- Child themes can override via `doxtr_theme_defaults = {'microtype': {'kerning': True}}` (three-tier merge respected).

### Migration Guide

If you were relying on the implicit `kerning: True` default and building with pdfTeX:

```python
# conf.py — explicitly opt in (pdfTeX only)
doxtr_microtype = {
    'kerning': True,
}
```

No action needed for LuaLaTeX users (the previous default was silently broken).

### Tests

- Added `microtype_kerning_optin` test — verifies explicit `kerning=True` propagates correctly.
- Added `microtype_draft_document_compiles` test — verifies document generation succeeds with draft mode active.
- Updated default microtype test to expect `kerning=false` in generated `.tex` output.

---

## 1.1.2

### Bug Fixes

#### Hyperref Undefined Warnings for Sphinx-Needs Cross-References
- **Fix: LaTeX "Hyper reference ... undefined" warnings for sphinx-needs nodes** — Sphinx's LaTeX writer qualifies all hyperref targets with the document path (e.g. `path/to/doc:NEED-ID`), but since `process_needs_ast` emits raw LaTeX labels bypassing the writer, labels were generated without the docname prefix, causing hundreds of warnings for cross-document need references.
- Retrieves the needs data dict using the sphinx-needs 8.x internal attribute (`_needs_all_needs`), falling back to the legacy public name.
- Looks up each need's docname from the stored need data.
- Prefixes every generated `\label` with `docname:` to match what `make_refnode` / `\hyperref` expects in single-file LaTeX output.

#### Tables/Figures Rendering Beside Run-In Paragraph Headings
- **Fix: block elements (tables, figures, containers) rendering beside run-in headings** — In KOMA-Script, `\paragraph` and `\subparagraph` headings use a negative `afterskip`, making them "run-in" headings. When a table, figure, or container was the first body element after such a heading, it rendered to the side of the heading text instead of below it.
- New `fix_block_after_paragraph()` AST processor at priority 980 inserts `\leavevmode\par` before block elements that immediately follow section titles, forcing LaTeX back into vertical mode.
- New public APIs `register_par_fix_block_type(node_type)` and `register_par_fix_skip_type(node_type)` for child theme extensibility.
- Exported `PARAGRAPH_FIX_PRIORITY` constant at all package levels.
- Gated by existing `doxtr_enable_table_processor` config flag.

### New Features

#### Dark File Swap (`dark_file_swap.py`)
- **New `dark_file_swap.py` module** — Source-read interception for dark mode file variant swapping.
- Intercepts RST/MyST source text via Sphinx's `source-read` event (priority 500) and rewrites directive file arguments to their `_dark` variants before parsing. This ensures extensions that consume file content at parse time (PlantUML, Mermaid, drawio, include, etc.) receive the correct dark variant.
- `swap_dark_sources(app, docname, source)` — Sphinx `source-read` handler.
- `swap_dark_includes(app, relative_path, parent_docname, source)` — Sphinx `include-read` handler (requires Sphinx ≥ 7.2.4).
- `register_dark_swap_directive(name, file_options)` — **Public API** for theme authors to register custom directives for dark file swapping.
- Default directives scanned: `uml`, `mermaid`, `drawio`, `drawio-figure`, `drawio-image`, `include`, `literalinclude`, `raw`.
- Hardcoded exclusions: `image` and `figure` (handled by `process_dark_images_ast` at doctree level).
- New config values: `doxtr_enable_dark_file_swap`, `doxtr_dark_file_swap_directives`, `doxtr_dark_file_swap_extensions`, `doxtr_dark_file_swap_extra_extensions`, `doxtr_dark_file_swap_exclude`.
- Guards: non-latex builder, dark mode not active, strategy is `passthrough`, master switch disabled.

### Tests

- **`test_harness/test_dark_file_swap.py`**: comprehensive test coverage for the dark file swap module including directive matching, extension filtering, exclusion patterns, and Sphinx version guards.

---

# 1.1.0

## New Features

### Topic & Contents Boxes (`doxtr_topic`, `doxtr_contents`)
- **New element type: `.. topic::` and `.. contents::`** styled via tcolorbox with a 45° top-right cutaway geometry (`cutaway_depth`), thick bottom frame (`bottom_frame_height`, `bottom_frame_color`), and full WCAG enforcement on title colors.
- New config sections `doxtr_topic` and `doxtr_contents` in `CORE_CONFIG_MANIFEST`.
- New `.tex_t` templates: `latex_styles/topic/default.tex_t`, `latex_styles/topic/cutaway.tex_t`, `latex_styles/contents/default.tex_t`.
- New absolute fallbacks `DEFAULT_TOPIC_STYLE` and `DEFAULT_CONTENTS_STYLE` in `core_fallbacks.py`.
- New `process_topics_ast` processor in `ast_processors/topics.py` (registered at priority 990 in `setup()`).
- New `doxtr_enable_topics_processor` flag (default `True`) to disable the processor.
- New config validation sets `VALID_TOPIC_KEYS` and `VALID_CONTENTS_KEYS` in `config.py`.

### Draft Watermark (`doxtr_draft`)
- **New element type: draft watermarks** rendered via `latex_styles/draft/default.tex_t` using TikZ.
- New config section `DOXTR_DRAFT` in `core_config.py` with `text`, `date_format`, `timezone`, `color`, `font_size`, `font` keys.
- Supports `{date}` and `{project_version}` placeholders in draft text.
- `dd:` color expressions resolved on `doxtr_draft.color`.

### Hyperlink Color Control (`doxtr_links`)
- **New config section `doxtr_links`** with `inner_color` and `outer_color` keys.
- Colors injected into `sphinxsetup` as `InnerLinkColor`/`OuterLinkColor` using the `{rgb}` model required by Sphinx's hyperref integration.
- Respects existing user `sphinxsetup` values (does not overwrite explicit user settings).
- New `DOXTR_LINKS` default dict in `core_config.py`.

### Font System (`fonts.py`)
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

### Image Processing (`image_processing.py`)
- **New dedicated `image_processing.py` module** extracted from `__init__.py` containing all image recolouring and adaptation logic.
- Dark mode image pipeline: grayscale recolouring, HSL lightness inversion for bright color images, `_dark` variant detection.
- Page adaptation image pipeline: edge-connected white flood-fill replacement with the target page background color.
- Shared `_iter_processable_images()` generator used by both pipelines.
- `_ALPHA_OPACITY_THRESHOLD` neutral alias (replaces `_DARK_ALPHA_THRESHOLD`).
- `no-auto-image-adapt` RST class skips all image processing (replaces deprecated `no-dark-mode-auto-invert`).

### Dark Mode Improvements
- **`doxtr_dark_mode_strategy`** config: `'auto'` (luminance-based), `'invert'` (standard dark), `'passthrough'` (skip inversion for light-alternative pages like solarized/sepia). Default `'auto'`.
- `doxtr_dark_mode_strategy_resolved` read-only computed strategy (set by `config_inited`).
- **`doxtr_dark_text_color`** config: explicit dark mode body text color override. Auto-calculated via WCAG when not set.
- **`doxtr_dark_recolor_grayscale`** (default `True`) and **`doxtr_dark_invert_color_images`** (default `True`) fine-grained image processing controls.
- **`DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS`** in `core_config.py`: auto-generated dark semantic palette from light palette (inverted for `invert` strategy, passed through for `passthrough`).
- `hex_dark_invert(hex_color)` public utility function (exported from package `__init__`).
- `_DARK_STRATEGY_LUMINANCE_THRESHOLD` and `_VALID_DARK_STRATEGIES` exported for child theme introspection.

### Page Color Adaptation
- **`doxtr_adapt_colors_to_page`** config: `'auto'` (default), `True`, `False`. Luminance-proportional color remapping when page background differs from the theme's designed-for background.
- `adapt_color_to_page(hex_color, designed_bg, actual_bg, compress_dark, compress_light)` public API.
- `_compute_adaptation_compression()` and `_get_luminance()` public utilities for child themes.
- `_ADAPTATION_LUMINANCE_THRESHOLD` exported constant.
- `\pagecolor` emitted in preamble when adaptation is active and page ≠ `#FFFFFF`.
- Processing order: dark mode → page adaptation → `dd:` resolution → WCAG enforcement → template rendering.

### Extensibility API
- **`register_preamble_hook(fn, position)`** — inject LaTeX into the document preamble at one of four positions: `before_packages`, `after_packages`, `before_styles`, `after_styles`. No need to copy `preamble.tex_t`.
- **`register_config_transform(fn)`** — post-merge config transform hook. Called after three-tier merge but before template rendering. Signature: `fn(sections, palette, config) -> None`.
- **`register_style_type(name, subdir, fallback_fn, config_section_factory, color_keys, preamble_var)`** — register a fully custom element style type with template resolution, color processing, and WCAG enforcement. Collisions with built-in `preamble_var` names are rejected.
- **`register_color_operation(name, fn)`** in `utils.py` — register custom `dd:` color expression operations. Signature: `fn(hex_color, arg) -> hex_color`. Built-in operation names (`lighten`, `darken`, `contrast`) cannot be overridden.
- **`register_ast_processor(fn, doctype, priority)`** updated: `doctype` parameter added (default `None` = latex-only); `priority` parameter added (default 992). Late calls (after `builder-inited`) now emit a warning.
- `_custom_style_types`, `_preamble_hooks`, `_config_transform_hooks` runtime registries, checked via lazy import in `templates.py` to avoid circular import.

### `doxtr_globals` Wrapper Key Support
- Config sections now support `light` / `dark` wrapper dicts in `doxtr_globals` (and all other `doxtr_*` config dicts). `_unwrap_mode()` in `config.py` extracts the correct nested values before merging.
- `validate_wrapper_keys()` in `config.py` warns on unknown top-level wrapper keys.
- `make_collect_dark_fn(config, theme_defaults)` factory in `config.py` builds the dark-mode section collector used in `_stage_merge_and_resolve`.

### Other Config Additions
- **`doxtr_strict_mode`** (default `False`) — raise error on missing templates instead of falling back.
- **`doxtr_cache_templates`** (default `True`) — control Jinja2 template caching.
- **`doxtr_patch_admonition_translator`** (default `True`) — control patching of Sphinx's `LaTeXTranslator` for generic admonition tags. Set `False` if a child theme provides its own translator.
- **`doxtr_enable_*_processor`** flags for each AST processor (`container`, `table`, `codeblock`, `epigraph`, `sidebar`, `highlights`, `needs`, `topics`) — default `True`.
- **`main_font_size`** global: base body text font size (used as LaTeX pointsize and reference for `size_factor` calculations in headings).
- **`topic_style_path`** and **`contents_style_path`** custom resolution path globals.

### `number_match_title_xheight` Heading Feature
- New `number_match_title_xheight` heading config key (per-level and global). When `True`, scales the chapter/section number so its cap height matches the title's x-height.
- New `tests/test_number_match_title_xheight.py` unit tests.

## Refactoring

- **`__init__.py` decomposed**: font logic extracted to `fonts.py`, image processing to `image_processing.py`. `__init__.py` reduced from ~2800 lines to the core pipeline (config, template, preamble assembly).
- **`config_inited()` split into three named stages**: `_stage_merge_and_resolve()`, `_stage_build_and_render_preamble()`, `_stage_assemble_output()` for readability and testability.
- **`_wcag_enforce_title_colors()`** and **`_process_box_section()`** extracted as internal helpers.
- **`_resolve_sty_file()`** extracted for `.sty` override path resolution.
- **`_auto_detect_dark_strategy()`** and **`_build_dark_section()`** extracted as internal helpers.
- `templates.py`: `_get_style_meta()` helper added to check built-in `STYLE_TYPES`/`STYLE_FALLBACKS` then the runtime `_custom_style_types` registry (lazy import avoids circular dependency).
- `utils.py`: `register_color_operation()` and `_custom_color_operations` registry moved here from `__init__.py`. `_RE_SAFE_NAME` precompiled regex moved here and shared with `ast_processors/containers.py`.
- `DOXTR_GLOBALS` in `core_config.py` now uses a `light`/`dark` wrapper structure.
- Legacy flat-key compatibility list `_LEGACY_GLOBAL_KEYS` maintained in `__init__.py` for one minor version.
- **LaTeX color model migrated from CMYK to RGB**: all theme colors are now emitted using the `{rgb}` model throughout (preamble, tcolorbox, TikZ). `hex_to_rgb_floats()` replaces `hex_to_cmyk_string()` as the primary color serialiser. Exception: hyperlink colors were already `{rgb}` (hyperref requirement) and are unchanged. Custom `.tex_t` files that hard-code `{cmyk}` color definitions will continue to work but should be updated to use the `{rgb}` model for consistency.

## Tests

- **`test_harness/test_fonts.py`** (661 lines): `TestRegisterFontFamily`, `TestRegisterFontFamilies`, `TestExpandPattern`, `TestClearFontRegistry`, `TestDeduplicateRegistry`, `TestCollectFontFiles`, `TestGenerateFontFeatures`, `TestValidateFontFiles`, `TestProcessUserFontConfig`, `TestAutoDiscoverFonts`, `TestFindBoldWeight`, `TestFontpkgInjection`, `TestParentScanGuard`.
- **`test_harness/test_extensibility_phase4.py`** (400 lines): `TestRegisterColorOperation`, `TestRegisterConfigTransform`, `TestWcagPairsStyleType`.
- **`test_harness/test_ast_processors.py`** (758 lines): `TestContainersAST`, `TestTablesAST`, `TestCodeblocksAST`, `TestEpigraphsAST`, `TestHighlightsAST`, `TestTopicsAST`, `TestSidebarsAST`, `TestNeedsAST`, `TestNonLatexBuilderSkip`.
- **`test_harness/test_pipeline.py`** (480 lines): `TestGlobalsMerge`, `TestSectionMerging`, `TestSemanticPalette`, `TestDarkMode`, `TestPageAdaptation`, `TestPipelineStructure`.
- **`test_harness/test_utils.py`** extended: `_split_hex_opacity` tests, dark invert tests (`TestHexDarkInvert`), three-tier merge mutation guards, explicit-path scope enforcement tests.
- **`tests/test_number_match_title_xheight.py`**: full coverage for the `number_match_title_xheight` feature.

## Documentation

- `README.md` updated with font bundling guide (Mode 1 explicit, Mode 2 weight-pattern, Mode 3 auto-discover), `doxtr_fonts` declarative config reference, dark mode strategy docs, page color adaptation docs, extensibility API (`register_preamble_hook`, `register_config_transform`, `register_style_type`, `register_color_operation`).

## CI

- `.github/workflows/test-harness.yml`: removed redundant `pip uninstall` step and version-print debug step (now handled by the install script).
- `pyproject.toml`: added `[project.optional-dependencies]` groups `fonts` (`fonttools>=4.0`) and `images` (`numpy>=1.20`, `scipy>=1.7`, `Pillow>=9.0`); added corresponding `[project.optional-dependencies.dev]` entries.

## Breaking Changes

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
