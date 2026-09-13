"""Image processing functions for dark mode and page adaptation.

This module handles all image manipulation for the doxtr-pdf-theme-core extension:
- Dark mode image recolouring (grayscale remap + color lightness inversion)
- Page-adaptive image background replacement (flood-fill white detection)
- Dark asset variant resolution (_dark file swap)
- Per-image opt-out collection (no-auto-image-adapt class)
- Parallel image processing via concurrent.futures (configurable)
"""
import fnmatch
import os
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed

from docutils import nodes
from sphinx.util import logging

from .core_config import DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS
from .utils import to_bool

logger = logging.getLogger(__name__)


# --- EXTENSIBLE IMAGE PROCESSOR REGISTRY ---
# Child themes may register a custom image processing function that completely
# replaces the built-in dark-mode or page-adaptation pipeline.
# Each key is a position ('dark' or 'adapt'), each value is a callable with
# signature fn(app, exception) -> None (same as the built-in handlers).
_VALID_IMAGE_PROCESSOR_POSITIONS = frozenset({'dark', 'adapt'})
_image_processor_registry: dict = {}


def register_image_processor(fn, position='dark'):
    """Register a custom image processor that replaces a built-in pipeline.

    Allows child themes to completely replace the dark-mode or page-adaptation
    image processing with their own implementation. When a custom processor is
    registered, the built-in handler for that position is skipped entirely.

    Must be called from the child theme's ``setup()`` function — before
    ``build-finished`` fires.

    Args:
        fn: A callable with signature ``fn(app, exception) -> None``.
            Receives the same arguments as Sphinx's ``build-finished`` event.
        position: Which pipeline to replace. One of:
            - ``'dark'``: Replaces ``_recolour_dark_images`` (dark mode
              grayscale recolouring and color lightness inversion).
            - ``'adapt'``: Replaces ``_adapt_image_backgrounds`` (page
              background adaptation via flood-fill).

    Raises:
        ValueError: If *position* is not one of the valid positions.
        TypeError: If *fn* is not callable.

    Example::

        from doxtr_pdf_theme_core import register_image_processor

        def my_dark_processor(app, exception):
            '''Custom dark mode image processing.'''
            # ... custom implementation ...
            pass

        # In your extension's setup():
        register_image_processor(my_dark_processor, position='dark')

    Note:
        The custom handler receives ALL ``build-finished`` calls, including
        when ``exception`` is not None (build failed), when the builder is
        not LaTeX, or when dark mode / adaptation is inactive. The handler
        must perform its own guard checks. See the example above.
    """
    if not callable(fn):
        raise TypeError(
            f"register_image_processor: fn must be callable, got {type(fn).__name__}"
        )
    if position not in _VALID_IMAGE_PROCESSOR_POSITIONS:
        raise ValueError(
            f"register_image_processor: invalid position '{position}'. "
            f"Must be one of: {sorted(_VALID_IMAGE_PROCESSOR_POSITIONS)}"
        )
    _image_processor_registry[position] = fn


def _reset_image_processor_registry():
    """Clear the image processor registry. Used for test isolation."""
    _image_processor_registry.clear()


def mark_image_dark_ready(app, filename) -> None:
    """Mark an already-dark-themed image so the dark pipeline skips it.

    Public API for extensions that GENERATE image content which is already
    correct for the dark page (e.g. doxtr-roadmap renders a PlantUML Gantt
    from a dark-themed source string). Such images must NOT be re-processed by
    the built-in dark pipeline (``_recolour_dark_images``): a dark,
    largely-achromatic diagram would be misclassified as grayscale line-art
    and remapped (black->text, white->page), inverting its already-correct
    colours.

    The ``_dark`` file-swap mechanism handles this automatically for
    *file-based* diagrams (``.. uml:: arch.puml`` with ``arch_dark.puml``), but
    inline-generated diagrams have no source file to swap, so the generating
    extension must register the final output filename explicitly.

    This records *filename* in the same set the file-swap uses
    (``app.env._doxtr_dark_substituted``); the build-finished dark and
    page-adaptation pipelines skip any output file whose basename matches.

    Only the exact basename you register is skipped, so this is safe even when
    an extension shares an output namespace with hand-authored diagrams (e.g.
    ``sphinxcontrib.plantuml`` writes every diagram as ``plantuml-<hash>.png``
    -- registering one specific hash does not affect the others).

    Call this from a directive's ``run()`` (once the final filename is known)
    or any time before ``build-finished`` fires. It is a no-op when dark mode
    is not active, so callers may register unconditionally.

    Args:
        app: The Sphinx application object.
        filename: The output image filename (basename or path; only the
            basename is matched, e.g. ``'plantuml-<hash>.png'``).

    Example (inside a directive ``run()``)::

        import hashlib
        key = hashlib.sha1()
        key.update(node['incdir'].encode()); key.update(b'\0')
        key.update(node['uml'].encode())
        try:
            from doxtr_pdf_theme_core import mark_image_dark_ready
            mark_image_dark_ready(env.app, f'plantuml-{key.hexdigest()}.png')
        except ImportError:
            pass  # core not installed -- nothing to skip
    """
    if not filename:
        return
    if not to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return
    env = getattr(app, 'env', None)
    if env is None:
        return
    if not hasattr(env, '_doxtr_dark_substituted'):
        env._doxtr_dark_substituted = set()
    env._doxtr_dark_substituted.add(os.path.basename(filename))


def _get_parallel_workers(config):
    """Determine the number of parallel workers from config.

    Reads ``doxtr_image_parallel_workers`` from the Sphinx config and returns
    the effective worker count.

    Args:
        config: Sphinx config object.

    Returns:
        int: Number of workers to use. 1 means sequential (no pool overhead).

    Rules:
        - ``'auto'`` or ``0``: ``min(os.cpu_count() or _PARALLEL_FALLBACK_CPU_COUNT, _PARALLEL_MAX_AUTO_WORKERS)``
        - ``1``: Sequential processing (no pool).
        - ``N > 1``: Use N workers (capped at no maximum — user's choice).
    """
    val = getattr(config, 'doxtr_image_parallel_workers', 'auto')
    if val == 'auto' or val == 0:
        return min(os.cpu_count() or _PARALLEL_FALLBACK_CPU_COUNT, _PARALLEL_MAX_AUTO_WORKERS)
    return max(1, int(val))


def _resolve_dark_asset(path: str) -> str:
    """Return the _dark variant of a file path if it exists, else original."""
    if not path:
        return path
    base, ext = os.path.splitext(path)
    dark_path = f'{base}_dark{ext}'
    if os.path.isfile(dark_path):
        return dark_path
    return path


# Supported image extensions for dark-mode grayscale recolouring.
# SVG, PDF, and EPS are excluded — they are not processable by Pillow.
_RECOLOUR_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')

# --- Dark image processing constants ---
# Alpha opacity threshold: pixels with alpha <= this value are treated as transparent.
# 128 = 50% opacity (half of 255). Used by both dark mode and page adaptation pipelines.
_ALPHA_OPACITY_THRESHOLD: int = 128
_DARK_ALPHA_THRESHOLD: int = _ALPHA_OPACITY_THRESHOLD  # Legacy alias for dark mode code

# Downsample target size for fast sampling in _is_grayscale_sample / _is_too_bright.
# 64×64 = 4096 pixels — large enough for statistical accuracy, fast to compute.
_DARK_SAMPLE_SIZE: int = 64

# Saturation threshold above which a pixel is considered chromatic (not grey).
# Chosen to tolerate JPEG compression artifacts (which introduce tiny false chroma).
_DARK_SAT_THRESHOLD: float = 0.15

# Maximum fraction of visible pixels that may be chromatic for an image to be
# classified as "grayscale". 5% tolerates anti-aliasing at colored borders.
_DARK_CHROMATIC_MAX_FRACTION: float = 0.05

# Near-black channel ceiling. Pixels with max channel < this are excluded from
# grayscale detection because tiny channel differences produce spurious high
# saturation ratios at near-zero values (e.g. (0,1,1) = 100% technical saturation).
_DARK_NEAR_BLACK_CEILING: int = 20

# Dampened lightness inversion coefficients for _invert_color_image_lightness.
# Formula: L_new = _DARK_INVERT_PEAK - (L * _DARK_INVERT_SLOPE)
# Derived from CSS invert(0.86): c' = 0.86 - 0.72 * c
# Output range [0.14, 0.86] — matches hex_dark_invert exactly for achromatic values.
_DARK_INVERT_PEAK: float = 0.86
_DARK_INVERT_SLOPE: float = 0.72

# Default brightness threshold (also the default for doxtr_dark_image_brightness_threshold).
# Calibrated against the simplified (non-linearised) sRGB luminance formula.
# 0.65 catches white-background diagrams (typical mean ~0.7–0.85) while leaving
# mid-tone and dark images untouched.
_DARK_BRIGHTNESS_DEFAULT: float = 0.65

# ITU-R BT.709 sRGB relative luminance coefficients (simplified — no gamma linearisation).
_DARK_LUM_R: float = 0.2126
_DARK_LUM_G: float = 0.7152
_DARK_LUM_B: float = 0.0722

# Optional dependency: Pillow (PIL) for dark-mode image processing.
# If not installed, all dark image processing is silently skipped with a warning.
try:
    from PIL import Image as _PIL_Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_Image = None  # type: ignore[assignment]
    _PIL_AVAILABLE = False

# --- Parallel processing constants ---
# Maximum number of workers when 'auto' is selected. Caps parallelism to avoid
# diminishing returns from process spawn overhead and memory pressure.
_PARALLEL_MAX_AUTO_WORKERS: int = 8

# Fallback CPU count when os.cpu_count() returns None (e.g., in containers).
_PARALLEL_FALLBACK_CPU_COUNT: int = 4

# Minimum number of work items required to justify pool overhead.
# Batches at or below this size are processed sequentially regardless of worker config.
_PARALLEL_MIN_BATCH_SIZE: int = 2


def _get_exclude_patterns(config):
    """Get the merged exclude patterns list from config.

    Reads doxtr_image_exclude_patterns (primary) with fallback to
    the deprecated doxtr_dark_image_exclude_patterns.
    """
    return list(getattr(config, 'doxtr_image_exclude_patterns', None)
                or getattr(config, 'doxtr_dark_image_exclude_patterns', []))


def _hex_to_rgb_tuple(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (R, G, B) int tuple."""
    c = hex_color.lstrip('#')
    if len(c) == 3:
        c = ''.join(x * 2 for x in c)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _sample_pixels(img) -> list:
    """Downsample img to _DARK_SAMPLE_SIZE × _DARK_SAMPLE_SIZE and return opaque pixels.

    Returns a list of (R, G, B, A) tuples where A > _DARK_ALPHA_THRESHOLD.
    Transparent pixels are excluded. Used by _is_grayscale_sample and _is_too_bright
    to share the downsample + alpha-handling logic.

    Args:
        img: PIL Image object (any mode — converted internally).

    Returns:
        List of (R, G, B, A) tuples for opaque pixels only. May be empty if the
        image is fully transparent.
    """
    size = (_DARK_SAMPLE_SIZE, _DARK_SAMPLE_SIZE)
    small = img.resize(size, _PIL_Image.LANCZOS)
    if small.mode in ('RGBA', 'LA', 'PA'):
        return [(r, g, b, a) for r, g, b, a in small.convert('RGBA').getdata()
                if a > _DARK_ALPHA_THRESHOLD]
    return [(r, g, b, 255) for r, g, b in small.convert('RGB').getdata()]


def _is_grayscale_sample(img) -> bool:
    """Return True if a downsampled version of img has no meaningful hue.

    Downsamples to _DARK_SAMPLE_SIZE × _DARK_SAMPLE_SIZE for speed. Uses a
    majority-based approach: if 95% or more of sampled pixels have saturation
    below _DARK_SAT_THRESHOLD, the image is considered grayscale. This tolerates
    anti-aliasing artifacts and PNG compression noise that produce tiny per-pixel
    color differences (e.g. (8,9,8) from sub-pixel rendering) while still
    correctly identifying full-color photographs.

    For images with alpha channels, only opaque pixels (alpha > _DARK_ALPHA_THRESHOLD)
    are tested. This prevents transparent-to-black compositing artifacts from
    producing false chromatic readings at anti-aliased edges.

    Near-black pixels (max channel value < _DARK_NEAR_BLACK_CEILING) are excluded
    because at very low channel values, even 1-unit rounding differences produce
    spuriously high saturation ratios (e.g. (0,1,1) = 100% technical saturation
    despite being perceptually black).
    """
    pixels = _sample_pixels(img)

    total = 0
    chromatic = 0
    for r, g, b, _ in pixels:
        cmax = max(r, g, b)
        # Skip near-black pixels — tiny channel differences give spurious saturation
        if cmax < _DARK_NEAR_BLACK_CEILING:
            continue
        total += 1
        if (cmax - min(r, g, b)) / cmax > _DARK_SAT_THRESHOLD:
            chromatic += 1
    if total == 0:
        return True
    # Image is grayscale if fewer than _DARK_CHROMATIC_MAX_FRACTION of visible
    # non-black pixels are chromatic
    return (chromatic / total) < _DARK_CHROMATIC_MAX_FRACTION


def _is_too_bright(img, threshold: float = _DARK_BRIGHTNESS_DEFAULT) -> bool:
    """Return True if the image's mean perceived luminance exceeds threshold.

    Downsamples to _DARK_SAMPLE_SIZE × _DARK_SAMPLE_SIZE for speed. Uses
    standard sRGB relative luminance (_DARK_LUM_R * R + _DARK_LUM_G * G +
    _DARK_LUM_B * B, ITU-R BT.709 simplified without gamma linearisation)
    for perceptual accuracy. Transparent pixels (alpha <= _DARK_ALPHA_THRESHOLD)
    are excluded from the calculation.

    Args:
        img: PIL Image object (any mode — converted internally).
        threshold: Luminance threshold in [0.0, 1.0]. Images with mean
            luminance above this value are considered "too bright" for the
            dark page background.

    Returns:
        True if mean luminance > threshold, False otherwise.
        Returns False if no opaque pixels are found (fully transparent image).
    """
    pixels = _sample_pixels(img)

    total_lum = 0.0
    count = 0
    for r, g, b, _ in pixels:
        # sRGB relative luminance (simplified — no gamma linearisation for
        # speed; acceptable for threshold comparison)
        total_lum += (_DARK_LUM_R * r + _DARK_LUM_G * g + _DARK_LUM_B * b) / 255.0
        count += 1

    if count == 0:
        return False

    return (total_lum / count) > threshold


def _invert_color_image_lightness(path: str, img=None, text_rgb: tuple = None, page_rgb: tuple = None) -> None:
    """Invert the HSL lightness of a color image in-place for dark mode.

    Applies a dampened lightness inversion that maps:
    - White backgrounds (L=1.0) → page background lightness
    - Black lines (L=0.0) → text color lightness
    - Pure saturated colors (L=0.5) → approximately unchanged

    When text_rgb and page_rgb are provided, the inversion coefficients are
    derived dynamically from the configured dark text and page background
    colors, ensuring image backgrounds match the document page color.
    When not provided, falls back to the default constants
    _DARK_INVERT_PEAK (0.86) / _DARK_INVERT_SLOPE (0.72) which match
    the standard dark defaults (#DBDBDB text, #242424 page).

    Formula: L_new = peak - (L * slope)
    Where peak = text_lightness, slope = text_lightness - page_lightness.

    Hue and saturation are preserved, so the image retains its color
    character while white backgrounds become dark. Results are consistent
    with hex_dark_invert for achromatic values (±1 rounding per channel).

    Uses numpy for vectorised processing when available; falls back to
    pure Python via colorsys. Both paths produce identical results within
    ±1 per channel due to float rounding.

    Alpha channel is preserved unchanged. Image format is preserved
    (PNG stays PNG, JPEG stays JPEG).
    Note: JPEG images are re-saved with PIL's default quality (75), introducing
    a minor quality loss. For lossless output, use PNG source images.

    Precondition: the image must be a color (non-grayscale) image. If called
    with a grayscale image, hue and saturation will be zero and only lightness
    will shift, producing a recoloured result instead of the expected
    black/white remap. Use _is_grayscale_sample() to verify before calling,
    or use _maybe_recolour_image() for grayscale images.

    Args:
        path: Path to the image file (modified in-place).
        img: Optional pre-opened PIL Image. If None, opens from path.
            Caller is responsible for ensuring this is a non-grayscale image
            (grayscale detection is the caller's responsibility).
        text_rgb: Optional (R, G, B) int tuple for the dark text color.
            Used with page_rgb to derive inversion coefficients dynamically
            so that image backgrounds match the configured page color.
            If None, uses the default _DARK_INVERT_PEAK / _DARK_INVERT_SLOPE.
        page_rgb: Optional (R, G, B) int tuple for the dark page background.
            Used with text_rgb to derive inversion coefficients. If None,
            uses the default constants.
    """
    if img is None:
        img = _PIL_Image.open(path)

    img, alpha, has_alpha, fmt = _strip_alpha(img)

    # Compute dynamic inversion coefficients from configured text/page colors.
    # The formula maps: white (L=1.0) → page bg lightness, black (L=0.0) → text lightness.
    # Linear: L_new = l_text - L * (l_text - l_page)
    # Defaults to _DARK_INVERT_PEAK / _DARK_INVERT_SLOPE when no colors are provided
    # (matching the standard dark defaults #DBDBDB text, #242424 page).
    if text_rgb is not None and page_rgb is not None:
        # Compute HSL lightness from RGB tuples (average of max and min channels)
        _t_max = max(text_rgb) / 255.0
        _t_min = min(text_rgb) / 255.0
        _p_max = max(page_rgb) / 255.0
        _p_min = min(page_rgb) / 255.0
        l_text = (_t_max + _t_min) / 2.0  # text lightness (the "bright" target for L=0)
        l_page = (_p_max + _p_min) / 2.0  # page lightness (the "dark" target for L=1)
        invert_peak = l_text  # L_new when L=0 (black → text color)
        invert_slope = l_text - l_page  # slope (L_new decreases as L increases)
    else:
        invert_peak = _DARK_INVERT_PEAK
        invert_slope = _DARK_INVERT_SLOPE

    # Vectorised path via numpy (preferred for performance)
    try:
        import numpy as np
        arr = np.array(img, dtype=np.float32) / 255.0  # (H, W, 3) in [0,1]

        # RGB → HSL (vectorised)
        cmax = arr.max(axis=2)
        cmin = arr.min(axis=2)
        delta = cmax - cmin

        # Lightness
        L = (cmax + cmin) / 2.0

        # Saturation
        S = np.zeros_like(L)
        mask = delta > 0
        low = L <= 0.5
        S[mask & low] = delta[mask & low] / (cmax[mask & low] + cmin[mask & low])
        S[mask & ~low] = delta[mask & ~low] / (2.0 - cmax[mask & ~low] - cmin[mask & ~low])

        # Hue (normalised to [0, 1])
        H = np.zeros_like(L)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        rm = mask & (cmax == r)
        H[rm] = ((g[rm] - b[rm]) / delta[rm]) % 6.0
        gm = mask & (cmax == g)
        H[gm] = ((b[gm] - r[gm]) / delta[gm]) + 2.0
        bm = mask & (cmax == b)
        H[bm] = ((r[bm] - g[bm]) / delta[bm]) + 4.0
        H = H / 6.0

        # Dampened lightness inversion using dynamic coefficients:
        #   L_new = invert_peak - (L * invert_slope)
        # With default constants, L=0.5 maps to 0.50 (pure saturated colors preserved).
        L_new = np.clip(invert_peak - (L * invert_slope), 0.0, 1.0)

        # HSL → RGB (vectorised, sector-based)
        # HSL sector: 0=[0°,60°), 1=[60°,120°), 2=[120°,180°), 3=[180°,240°), 4=[240°,300°), 5=[300°,360°)
        C = (1.0 - np.abs(2.0 * L_new - 1.0)) * S
        X = C * (1.0 - np.abs((H * 6.0) % 2.0 - 1.0))
        m = L_new - C / 2.0

        H6 = (H * 6.0).astype(np.int32) % 6
        out = np.zeros_like(arr)
        # The table encodes which of C, X, 0 maps to each RGB channel per sector.
        # None means "leave at zero" (out is already zeroed, so no assignment needed).
        # This avoids any isinstance check on the channel value.
        _hsl_sectors = [
            (C, X, None), (X, C, None), (None, C, X),
            (None, X, C), (X, None, C), (C, None, X),
        ]
        for i, (c1, c2, c3) in enumerate(_hsl_sectors):
            sector = H6 == i
            if c1 is not None:
                out[:, :, 0][sector] = c1[sector]
            if c2 is not None:
                out[:, :, 1][sector] = c2[sector]
            if c3 is not None:
                out[:, :, 2][sector] = c3[sector]

        out = np.clip((out + m[:, :, np.newaxis]) * 255.0, 0, 255).astype(np.uint8)
        result = _PIL_Image.fromarray(out, mode='RGB')

    except ImportError:
        # Pure-Python fallback using colorsys (slower, same result ±1 rounding)
        import colorsys
        new_pixels = []
        for r_val, g_val, b_val in img.getdata():
            h, l, s = colorsys.rgb_to_hls(r_val / 255.0, g_val / 255.0, b_val / 255.0)
            # Dampened inversion using dynamic coefficients
            l_new = max(0.0, min(1.0, invert_peak - (l * invert_slope)))
            nr, ng, nb = colorsys.hls_to_rgb(h, l_new, s)
            new_pixels.append((
                max(0, min(255, round(nr * 255))),
                max(0, min(255, round(ng * 255))),
                max(0, min(255, round(nb * 255))),
            ))
        result = _PIL_Image.new('RGB', img.size)
        result.putdata(new_pixels)

    _restore_alpha_and_save(result, alpha, has_alpha, path, fmt)


def _strip_alpha(img):
    """Split the alpha channel from img, return (rgb_img, alpha, has_alpha, fmt).

    Converts img to RGB (stripping alpha) and returns the alpha channel separately
    so it can be restored after processing. Counterpart: _restore_alpha_and_save.

    Args:
        img: PIL Image object (any mode).

    Returns:
        Tuple of (rgb_img, alpha_channel_or_None, has_alpha_bool, format_string).
        rgb_img is always in 'RGB' mode.
    """
    fmt = img.format or 'PNG'
    has_alpha = img.mode in ('RGBA', 'LA', 'PA')
    alpha = None
    if has_alpha:
        img = img.convert('RGBA')
        alpha = img.getchannel('A')
        img = img.convert('RGB')
    else:
        img = img.convert('RGB')
    return img, alpha, has_alpha, fmt


def _restore_alpha_and_save(result, alpha, has_alpha: bool, path: str, fmt: str) -> None:
    """Restore alpha channel (if any) and save result to path.

    Counterpart to _strip_alpha. If has_alpha is True, composites the alpha
    channel back onto result before saving.

    Args:
        result: PIL Image in 'RGB' mode (the processed image).
        alpha: Alpha channel from _strip_alpha (PIL Image or None).
        has_alpha: Whether the original image had an alpha channel.
        path: Destination file path (overwritten in-place).
        fmt: PIL format string (e.g. 'PNG', 'JPEG').
    """
    if has_alpha:
        result = result.convert('RGBA')
        result.putalpha(alpha)
    result.save(path, format=fmt)


def _maybe_recolour_image(path: str, text_rgb: tuple, page_rgb: tuple, img=None) -> None:
    """Recolour a grayscale image in-place for dark mode.

    Remaps: black (L=0) → text_rgb,  white (L=1) → page_rgb.
    Intermediate grey values are linearly interpolated.
    Alpha channel is preserved. Non-grayscale images are skipped.

    Grayscale detection runs on the original image (before alpha stripping)
    to avoid false chromatic readings from RGBA→RGB compositing artifacts.

    Image format is preserved (PNG stays PNG, JPEG stays JPEG).
    Note: JPEG images are re-saved with PIL's default quality (75), introducing
    a minor quality loss. For lossless output, use PNG source images.

    Args:
        path: Path to image file (modified in-place).
        text_rgb: (R, G, B) tuple for the dark text colour.
        page_rgb: (R, G, B) tuple for the dark page background colour.
        img: Optional pre-opened PIL Image. If provided, the internal
            grayscale check is skipped — caller is responsible for ensuring
            the image is grayscale (e.g. via _is_grayscale_sample).
            If None, opens the image from path and runs the check.
    """
    if img is None:
        img = _PIL_Image.open(path)
        # When called standalone (not from the main pipeline), verify grayscale
        if not _is_grayscale_sample(img):
            return  # Colour image — skip

    img, alpha, has_alpha, fmt = _strip_alpha(img)

    try:
        import numpy as np
        arr = np.array(img, dtype=np.float32)
        L = arr.mean(axis=2, keepdims=True) / 255.0
        t = np.array(text_rgb, dtype=np.float32)
        p = np.array(page_rgb, dtype=np.float32)
        out = np.clip(np.round(t * (1 - L) + p * L), 0, 255).astype(np.uint8)
        result = _PIL_Image.fromarray(out, mode='RGB')
    except ImportError:
        t, p = text_rgb, page_rgb
        new_pixels = []
        for r_val, g_val, b_val in img.getdata():
            L = (r_val + g_val + b_val) / (3 * 255)
            nr = max(0, min(255, round(t[0] * (1 - L) + p[0] * L)))
            ng = max(0, min(255, round(t[1] * (1 - L) + p[1] * L)))
            nb = max(0, min(255, round(t[2] * (1 - L) + p[2] * L)))
            new_pixels.append((nr, ng, nb))
        result = _PIL_Image.new('RGB', img.size)
        result.putdata(new_pixels)

    _restore_alpha_and_save(result, alpha, has_alpha, path, fmt)


# --- Page-adaptive image background replacement ---
# Default white fuzz: pixels with all RGB channels >= (255 - fuzz) are considered "white".
# 5 tolerates anti-aliasing artifacts and minor JPEG compression noise.
_ADAPT_IMAGE_WHITE_FUZZ_DEFAULT: int = 5

# Fraction of border pixels that must be transparent for the image to be
# considered "designed for transparent backgrounds" (skip processing).
_ADAPT_TRANSPARENT_BORDER_THRESHOLD: float = 0.5


def _iter_processable_images(app, exclude_patterns=None):
    """Yield (filename, dest_path, img) for each processable image in outdir.

    .. deprecated::
        Superseded by ``_iter_processable_image_paths`` for the parallel
        processing pipeline. Retained for backward compatibility with child
        themes that may import it directly. Will be removed in v2.0.0.

    Shared iteration logic for both dark-mode and page-adaptation image pipelines.
    Skips images that:
    - Have an extension not in _RECOLOUR_EXTENSIONS
    - Were substituted with a _dark variant (app.env._doxtr_dark_substituted)
    - Were opted out via no-auto-image-adapt class (app.env._doxtr_image_skip)
    - Match an exclude pattern (fnmatch glob against filename)
    - Are not regular files

    Args:
        app: Sphinx application object.
        exclude_patterns: List of glob patterns to exclude (default: empty).

    Yields:
        Tuples of (filename, dest_path, PIL.Image) for each processable image.
        The caller is responsible for closing or discarding the image object.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    dark_substituted = getattr(app.env, '_doxtr_dark_substituted', set())
    image_skip = getattr(app.env, '_doxtr_image_skip', set())

    dark_sub_basenames = {os.path.basename(uri) for uri in dark_substituted}
    skip_basenames = {os.path.basename(uri) for uri in image_skip}

    outdir = app.outdir
    try:
        outdir_files = os.listdir(outdir)
    except OSError:
        return

    for filename in outdir_files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _RECOLOUR_EXTENSIONS:
            continue

        if filename in dark_sub_basenames:
            continue

        if filename in skip_basenames:
            continue

        if any(fnmatch.fnmatch(filename, pat) for pat in exclude_patterns):
            continue

        dest_path = os.path.join(outdir, filename)
        if not os.path.isfile(dest_path):
            continue

        try:
            img = _PIL_Image.open(dest_path)
            yield filename, dest_path, img
        except Exception as e:
            logger.warning(
                f'[Doxtr Core] Failed to open image {filename}: {e}'
            )
            logger.debug('[Doxtr Core] Image open traceback:', exc_info=True)


def _has_transparent_background(img, threshold: float = _ADAPT_TRANSPARENT_BORDER_THRESHOLD) -> bool:
    """Return True if the image border is predominantly transparent.

    Samples all pixels on the 4 image borders. If more than `threshold`
    fraction have alpha < _ALPHA_OPACITY_THRESHOLD (128), the image is
    considered to be designed for compositing over any background and
    should not have its background replaced.

    Args:
        img: PIL Image object (any mode).
        threshold: Fraction of border pixels that must be transparent
            (default 0.5 = 50%).

    Returns:
        True if the image has a predominantly transparent border.
        False if the image has no alpha channel or border is mostly opaque.
    """
    if img.mode not in ('RGBA', 'LA', 'PA'):
        return False

    rgba = img.convert('RGBA')
    w, h = rgba.size
    if w < 2 or h < 2:
        return False

    try:
        import numpy as np
        arr = np.array(rgba)  # (H, W, 4)
        # Collect border alpha values efficiently
        top = arr[0, :, 3]
        bottom = arr[h - 1, :, 3]
        left = arr[1:h - 1, 0, 3]
        right = arr[1:h - 1, w - 1, 3]
        border_alphas = np.concatenate([top, bottom, left, right])
        transparent_count = int(np.sum(border_alphas < _ALPHA_OPACITY_THRESHOLD))
        total = len(border_alphas)
    except ImportError:
        # Pure-Python fallback via getpixel
        border_alphas = []
        for x in range(w):
            border_alphas.append(rgba.getpixel((x, 0))[3])
            border_alphas.append(rgba.getpixel((x, h - 1))[3])
        for y in range(1, h - 1):
            border_alphas.append(rgba.getpixel((0, y))[3])
            border_alphas.append(rgba.getpixel((w - 1, y))[3])
        transparent_count = sum(1 for a in border_alphas if a < _ALPHA_OPACITY_THRESHOLD)
        total = len(border_alphas)

    if total == 0:
        return False

    return (transparent_count / total) >= threshold


# Minimum area (in pixels) for interior white regions to be considered background.
# Regions smaller than this are assumed to be intentional (text, decorations).
# Default 64 pixels = an 8×8 area, well above any text glyph but catches
# even narrow background strips between diagram lifelines.
_ADAPT_IMAGE_MIN_INTERIOR_AREA: int = 64


def _flood_fill_background_mask(img, fuzz: int = _ADAPT_IMAGE_WHITE_FUZZ_DEFAULT):
    """Create a binary mask of white background pixels.

    Combines two strategies:

    1. **Edge-connected flood-fill**: BFS from all border pixels that match the
       white threshold. Identifies the outer background reliably.

    2. **Interior region inclusion**: White connected components NOT reached from
       the border are also included if their area exceeds
       _ADAPT_IMAGE_MIN_INTERIOR_AREA pixels. This catches enclosed background
       pockets inside diagrams (e.g. between PlantUML lifelines, inside frame
       borders) while preserving small intentional white areas (text glyphs,
       thin strokes).

    This approach correctly handles:
    - Diagrams with dashed lifelines (enclosed pockets ARE marked if large enough)
    - White text on colored bars (too small to exceed area threshold)
    - Anti-aliased edges (the fuzz tolerance handles gradient pixels at boundaries)

    Args:
        img: PIL Image in 'RGB' mode.
        fuzz: Channel tolerance (0–255). Pixel is "white" if all channels >= 255 - fuzz.

    Returns:
        numpy array (H, W) of dtype bool — True for background pixels.
        Returns None if numpy is not available (pure-Python fallback not
        provided for flood fill due to performance constraints on large images).
    """
    try:
        import numpy as np
    except ImportError:
        return None

    arr = np.array(img)  # (H, W, 3) uint8
    h, w = arr.shape[:2]

    # Binary mask: True where pixel is "white" (all channels >= threshold)
    white_threshold = 255 - fuzz
    white_mask = np.all(arr >= white_threshold, axis=2)  # (H, W) bool

    # --- Phase 1: BFS flood fill from border white pixels ---
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()

    # Top and bottom rows
    for x in range(w):
        if white_mask[0, x] and not visited[0, x]:
            visited[0, x] = True
            queue.append((0, x))
        if white_mask[h - 1, x] and not visited[h - 1, x]:
            visited[h - 1, x] = True
            queue.append((h - 1, x))
    # Left and right columns
    for y in range(h):
        if white_mask[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            queue.append((y, 0))
        if white_mask[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            queue.append((y, w - 1))

    # BFS through connected white pixels
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and white_mask[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    # --- Phase 2: Include large interior white regions ---
    # Find white pixels NOT reached from the border
    interior_white = white_mask & ~visited

    if interior_white.any():
        # Label connected components of interior white pixels.
        # Use scipy if available (fast C-level), fall back to iterative BFS.
        try:
            from scipy.ndimage import label as _scipy_label
            labeled, num_features = _scipy_label(interior_white)
            # Count pixels per label and include regions above threshold
            for lbl in range(1, num_features + 1):
                region_size = int(np.sum(labeled == lbl))
                if region_size >= _ADAPT_IMAGE_MIN_INTERIOR_AREA:
                    visited[labeled == lbl] = True
        except ImportError:
            # Fallback: BFS each unvisited interior white component
            interior_coords = list(zip(*np.where(interior_white)))
            interior_visited = np.zeros((h, w), dtype=bool)

            for start_y, start_x in interior_coords:
                if interior_visited[start_y, start_x]:
                    continue
                # BFS this component
                component = []
                comp_queue = deque()
                comp_queue.append((start_y, start_x))
                interior_visited[start_y, start_x] = True
                while comp_queue:
                    cy, cx = comp_queue.popleft()
                    component.append((cy, cx))
                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ny, nx = cy + dy, cx + dx
                        if (0 <= ny < h and 0 <= nx < w and
                                not interior_visited[ny, nx] and interior_white[ny, nx]):
                            interior_visited[ny, nx] = True
                            comp_queue.append((ny, nx))
                # Include this component if large enough
                if len(component) >= _ADAPT_IMAGE_MIN_INTERIOR_AREA:
                    for py, px in component:
                        visited[py, px] = True

    return visited


def _replace_background_with_color(path: str, page_rgb: tuple, fuzz: int, img=None) -> bool:
    """Replace edge-connected white background pixels with the page background color.

    Preserves the alpha channel if present. Only modifies pixels identified
    as "background" by flood-fill from the image borders.

    Args:
        path: Path to the image file (modified in-place).
        page_rgb: (R, G, B) tuple for the target page background color.
        fuzz: White detection tolerance (0–255).
        img: Optional pre-opened PIL Image. If None, opens from path.

    Returns:
        True if the image was modified, False if skipped (e.g. no numpy,
        no background detected, or image has transparent background).
    """
    if img is None:
        img = _PIL_Image.open(path)

    # Skip images that already have transparent backgrounds
    if _has_transparent_background(img):
        return False

    img_rgb, alpha, has_alpha, fmt = _strip_alpha(img)

    # Generate the background mask via flood fill
    mask = _flood_fill_background_mask(img_rgb, fuzz)
    if mask is None:
        # numpy not available — cannot perform flood fill
        logger.debug(
            '[Doxtr Core] numpy not available — skipping image background adaptation '
            f'for {os.path.basename(path)}'
        )
        return False

    # Check if any background pixels were found
    if not mask.any():
        return False

    # numpy is guaranteed available here — _flood_fill_background_mask
    # returned a numpy array (it returns None when numpy is missing).
    import numpy as np

    # Replace background pixels with page color
    arr = np.array(img_rgb)  # (H, W, 3) uint8
    arr[mask] = page_rgb
    result = _PIL_Image.fromarray(arr, mode='RGB')

    _restore_alpha_and_save(result, alpha, has_alpha, path, fmt)
    return True


# --- PARALLEL IMAGE PROCESSING WORKER FUNCTIONS ---
# These are top-level module functions (not closures or lambdas) so they can be
# pickled by ProcessPoolExecutor. They accept only serializable arguments —
# no `app`, no PIL Image objects. Workers open images from disk themselves.


def _process_single_dark_image(dest_path, filename, recolor_grayscale, invert_color,
                               threshold, text_rgb, page_rgb):
    """Process a single image for dark mode. Runs in a worker process.

    Determines whether the image is grayscale or color, then applies the
    appropriate dark-mode transformation:
    - Grayscale: remap black→text, white→page background
    - Color + too bright: invert HSL lightness

    Args:
        dest_path: Absolute path to the image file (modified in-place).
        filename: Basename of the image (for error reporting).
        recolor_grayscale: Whether to recolour grayscale images.
        invert_color: Whether to invert lightness of bright color images.
        threshold: Brightness threshold for color image inversion.
        text_rgb: (R, G, B) tuple for dark text colour.
        page_rgb: (R, G, B) tuple for dark page background.

    Returns:
        dict with keys:
            - 'filename': str — the image filename
            - 'success': bool — whether processing completed without error
            - 'error': str — error message (only when success=False)
    """
    try:
        from PIL import Image as _Image
        img = _Image.open(dest_path)

        if _is_grayscale_sample(img):
            if recolor_grayscale:
                _maybe_recolour_image(dest_path, text_rgb, page_rgb, img=img)
        else:
            if invert_color and _is_too_bright(img, threshold):
                _invert_color_image_lightness(dest_path, img=img,
                                             text_rgb=text_rgb, page_rgb=page_rgb)
        return {'filename': filename, 'success': True}
    except Exception as e:
        return {'filename': filename, 'success': False, 'error': str(e)}


def _process_single_adapt_image(dest_path, filename, page_rgb, fuzz):
    """Process a single image for page background adaptation. Runs in a worker process.

    Opens the image, checks for transparent backgrounds, then replaces
    edge-connected white background pixels with the page background color.

    Args:
        dest_path: Absolute path to the image file (modified in-place).
        filename: Basename of the image (for error reporting).
        page_rgb: (R, G, B) tuple for the target page background color.
        fuzz: White detection tolerance (0–255).

    Returns:
        dict with keys:
            - 'filename': str — the image filename
            - 'success': bool — whether processing completed without error
            - 'modified': bool — whether the image was actually changed
              (only present when success=True)
            - 'error': str — error message (only when success=False)
    """
    try:
        from PIL import Image as _Image
        img = _Image.open(dest_path)
        modified = _replace_background_with_color(dest_path, page_rgb, fuzz, img=img)
        return {'filename': filename, 'success': True, 'modified': modified}
    except Exception as e:
        return {'filename': filename, 'success': False, 'error': str(e)}


def _dispatch_parallel(work_items, worker_fn, worker_args_fn, workers, pipeline_name):
    """Dispatch work items to a ProcessPoolExecutor or run sequentially.

    Shared dispatch logic for both dark-mode and page-adaptation pipelines.
    Handles the decision between parallel and sequential execution, logging,
    error reporting, and result collection.

    Args:
        work_items: List of (filename, dest_path) tuples to process.
        worker_fn: The top-level worker function to call per item.
        worker_args_fn: Callable that takes (dest_path, filename) and returns
            the full args tuple to pass to worker_fn.
        workers: Number of parallel workers (1 = sequential).
        pipeline_name: Human-readable name for log messages (e.g. 'dark mode').

    Returns:
        int: Count of successfully processed images (for adapt pipeline,
             count of images that were actually modified).
    """
    if not work_items:
        return 0

    processed = 0
    errors = 0

    if workers <= 1 or len(work_items) <= _PARALLEL_MIN_BATCH_SIZE:
        # Sequential: no pool overhead for small batches or single-worker config
        for filename, dest_path in work_items:
            result = worker_fn(*worker_args_fn(dest_path, filename))
            if result['success']:
                # For adapt pipeline, count only modified images
                if 'modified' in result:
                    if result['modified']:
                        processed += 1
                else:
                    processed += 1
            else:
                logger.warning(
                    f"[Doxtr Core] {pipeline_name} image processing failed for "
                    f"{result['filename']}: {result['error']}"
                )
    else:
        logger.info(
            f'[Doxtr Core] Processing {len(work_items)} images with '
            f'{workers} parallel workers ({pipeline_name})'
        )
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(worker_fn, *worker_args_fn(dest_path, filename)): filename
                for filename, dest_path in work_items
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    # Worker process crashed (OOM, segfault, BrokenProcessPool)
                    filename = futures[future]
                    logger.warning(
                        f'[Doxtr Core] {pipeline_name} worker crashed for '
                        f'{filename}: {e}'
                    )
                    errors += 1
                    continue
                if result['success']:
                    if 'modified' in result:
                        if result['modified']:
                            processed += 1
                    else:
                        processed += 1
                else:
                    logger.warning(
                        f"[Doxtr Core] {pipeline_name} image processing failed for "
                        f"{result['filename']}: {result['error']}"
                    )

    return processed


def _iter_processable_image_paths(app, exclude_patterns=None):
    """Yield (filename, dest_path) for each processable image in outdir.

    Like _iter_processable_images but does NOT open the image file. Used by
    the parallel dispatch path where workers open images themselves in separate
    processes.

    Skips images that:
    - Have an extension not in _RECOLOUR_EXTENSIONS
    - Were substituted with a _dark variant (app.env._doxtr_dark_substituted)
    - Were opted out via no-auto-image-adapt class (app.env._doxtr_image_skip)
    - Match an exclude pattern (fnmatch glob against filename)
    - Are not regular files

    Args:
        app: Sphinx application object.
        exclude_patterns: List of glob patterns to exclude (default: empty).

    Yields:
        Tuples of (filename, dest_path) for each processable image.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    dark_substituted = getattr(app.env, '_doxtr_dark_substituted', set())
    image_skip = getattr(app.env, '_doxtr_image_skip', set())

    dark_sub_basenames = {os.path.basename(uri) for uri in dark_substituted}
    skip_basenames = {os.path.basename(uri) for uri in image_skip}

    outdir = app.outdir
    try:
        outdir_files = os.listdir(outdir)
    except OSError:
        return

    for filename in outdir_files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _RECOLOUR_EXTENSIONS:
            continue

        if filename in dark_sub_basenames:
            continue

        if filename in skip_basenames:
            continue

        if any(fnmatch.fnmatch(filename, pat) for pat in exclude_patterns):
            continue

        dest_path = os.path.join(outdir, filename)
        if not os.path.isfile(dest_path):
            continue

        yield filename, dest_path


def _adapt_image_backgrounds(app, exception):
    """Replace white image backgrounds with the page background color.

    Runs after Sphinx has copied all images to the LaTeX output directory.
    Only activates when page color adaptation is active (doxtr_adapt_colors_to_page)
    and the page background differs from white.

    Uses flood-fill from image borders to detect background regions, then
    replaces only those edge-connected white pixels with the configured page
    background color. Interior white areas (text, fills) are preserved.

    Images are skipped if:
    - The image has a predominantly transparent border (designed for compositing)
    - The image was marked with no-auto-image-adapt class
    - A _dark variant was substituted
    - The filename matches a pattern in doxtr_image_exclude_patterns
    - The extension is not in _RECOLOUR_EXTENSIONS
    - Dark mode is active (dark mode has its own image pipeline)

    Processing is parallelised via ProcessPoolExecutor when the image count
    exceeds 2 and ``doxtr_image_parallel_workers`` is not 1. Each image is
    processed independently in a worker process. Set workers to 1 to force
    sequential processing (useful for debugging).
    """
    # Allow child themes to replace the entire adapt pipeline
    if _image_processor_registry.get('adapt'):
        return _image_processor_registry['adapt'](app, exception)

    if exception:
        return
    if app.builder.name != 'latex':
        return
    # Don't run when dark mode is active — the dark pipeline handles images separately
    if to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return
    if not _PIL_AVAILABLE:
        logger.warning(
            '[Doxtr Core] Pillow (PIL) is not installed — '
            'image background adaptation is disabled. '
            'Install it with: pip install Pillow'
        )
        return

    # Check if adaptation is active
    adapt_state = getattr(app.config, 'doxtr_adaptation_state', None)
    if not adapt_state or not adapt_state.get('active', False):
        return

    # Check if image background adaptation is enabled
    if not to_bool(getattr(app.config, 'doxtr_adapt_image_backgrounds', True), default=True):
        return

    # Get the page background color
    page_bg = getattr(app.config, 'doxtr_semantic_palette', {}).get('page', '#FFFFFF')
    if not page_bg or page_bg.upper() == '#FFFFFF':
        return  # No adaptation needed — page is already white

    page_rgb = _hex_to_rgb_tuple(page_bg)
    fuzz = int(getattr(app.config, 'doxtr_adapt_image_white_fuzz', _ADAPT_IMAGE_WHITE_FUZZ_DEFAULT))

    exclude_patterns = _get_exclude_patterns(app.config)

    # Collect work items without opening images (workers do that themselves)
    work_items = list(_iter_processable_image_paths(app, exclude_patterns))

    if not work_items:
        return

    workers = _get_parallel_workers(app.config)

    def _adapt_args(dest_path, filename):
        return (dest_path, filename, page_rgb, fuzz)

    processed_count = _dispatch_parallel(
        work_items, _process_single_adapt_image, _adapt_args, workers,
        'page adaptation'
    )

    if processed_count > 0:
        logger.info(
            f'[Doxtr Core] Adapted {processed_count} image background(s) '
            f'to page color {page_bg}'
        )


def _process_image_adapt_ast(app, doctree, docname):
    """Collect per-image opt-outs for page-adaptive image processing.

    Scans for images with the 'no-auto-image-adapt' class and records
    their URIs so the build-finished hook can skip them. This runs
    independently of dark mode — it serves the page adaptation pipeline.

    Also handles the case where dark mode is NOT active but page adaptation IS,
    ensuring opt-outs are still collected.
    """
    if app.builder.name != 'latex':
        return
    # Only needed when dark mode is OFF (when dark mode is ON,
    # process_dark_images_ast already collects opt-outs into _doxtr_image_skip)
    if to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return

    for node in doctree.findall(nodes.image):
        uri = node.get('uri', '')
        if not uri or uri.startswith('data:') or '://' in uri:
            continue

        node_classes = node.get('classes', [])
        parent_classes = node.parent.get('classes', []) if node.parent is not None else []
        if ('no-auto-image-adapt' in node_classes or
                'no-auto-image-adapt' in parent_classes):
            if not hasattr(app.env, '_doxtr_image_skip'):
                app.env._doxtr_image_skip = set()
            app.env._doxtr_image_skip.add(uri)


def process_dark_images_ast(app, doctree, docname):
    """Swap image URIs to _dark variants and collect per-image opt-outs.

    Two tasks in one pass:

    1. Per-image opt-out: if an image node (or its direct parent) carries
       the class 'no-auto-image-adapt', its URI is added to
       app.env._doxtr_image_skip. These images are excluded from all
       automatic image processing (dark-mode recolouring, page-adaptation
       background replacement) in the build-finished phase.

    2. _dark variant swap: if a '<name>_dark<ext>' file exists alongside the
       source image, replace node['uri'] with the dark variant and register
       it with env.images. Swapped URIs are tracked in
       app.env._doxtr_dark_substituted so the build-finished hook skips them.

    Opt-out is checked first — an image with no-auto-image-adapt also
    skips the _dark variant lookup (the user is explicitly controlling the
    image and wants the original used).
    """
    if not to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return
    if app.builder.name != 'latex':
        return
    # In passthrough mode, don't swap to _dark image variants — light images
    # are appropriate for the light page background.
    if getattr(app.config, 'doxtr_dark_mode_strategy_resolved', 'invert') == 'passthrough':
        return

    srcdir = str(app.srcdir)

    for node in doctree.findall(nodes.image):
        uri = node.get('uri', '')
        if not uri or uri.startswith('data:') or '://' in uri:
            continue

        # --- Per-image opt-out via :class: no-auto-image-adapt ---
        # Check the image node itself and its direct parent (figures place
        # the class on the figure node, which wraps the image node).
        node_classes = node.get('classes', [])
        parent_classes = node.parent.get('classes', []) if node.parent is not None else []
        if ('no-auto-image-adapt' in node_classes or
                'no-auto-image-adapt' in parent_classes):
            if not hasattr(app.env, '_doxtr_image_skip'):
                app.env._doxtr_image_skip = set()
            app.env._doxtr_image_skip.add(uri)
            # User wants the original image — skip _dark variant lookup too
            continue

        # --- _dark variant lookup ---
        base, ext = os.path.splitext(uri)
        dark_uri = f'{base}_dark{ext}'
        dark_full = os.path.join(srcdir, dark_uri)

        if os.path.isfile(dark_full):
            node['uri'] = dark_uri
            node['candidates'] = {'*': dark_uri}
            app.env.images.add_file(docname, dark_uri)
            if not hasattr(app.env, '_doxtr_dark_substituted'):
                app.env._doxtr_dark_substituted = set()
            app.env._doxtr_dark_substituted.add(dark_uri)


def _recolour_dark_images(app, exception):
    """Process images in outdir for dark mode: grayscale recolouring and color inversion.

    Runs after Sphinx has copied all images to the LaTeX output directory.
    Scans ALL image files in outdir (not just app.builder.images) to catch
    extension-generated images such as PlantUML, draw.io, and Mermaid that
    are rendered directly to outdir during the write phase and therefore
    never appear in app.builder.images.

    Two processing paths (each independently enabled/disabled):

    1. Grayscale recolouring (doxtr_dark_recolor_grayscale, default True):
       Remaps black lines → dark text colour and white backgrounds → dark
       page colour. Targets images where <5% of visible pixels are chromatic
       (saturation > _DARK_SAT_THRESHOLD).

    2. Color image lightness inversion (doxtr_dark_invert_color_images,
       default True): For color images whose mean sRGB luminance exceeds
       doxtr_dark_image_brightness_threshold (default _DARK_BRIGHTNESS_DEFAULT),
       inverts the HSL lightness channel using L_new = _DARK_INVERT_PEAK -
       (L * _DARK_INVERT_SLOPE). Hue and saturation are preserved.

    Images are skipped if:
    - A _dark variant was substituted (app.env._doxtr_dark_substituted)
    - The image was marked with no-auto-image-adapt class
      (app.env._doxtr_image_skip)
    - The filename matches a pattern in doxtr_image_exclude_patterns
    - The extension is not in _RECOLOUR_EXTENSIONS (SVG, PDF, EPS excluded)

    Processing is parallelised via ProcessPoolExecutor when the image count
    exceeds 2 and ``doxtr_image_parallel_workers`` is not 1. Each image is
    processed independently in a worker process. Set workers to 1 to force
    sequential processing (useful for debugging).

    .. note:: Future optimisation opportunity
       This function currently processes ALL white pixels uniformly (grayscale
       remap) or ALL bright pixels (lightness inversion). A flood-fill
       background-detection approach (as used by _adapt_image_backgrounds)
       could be applied here to only modify edge-connected background pixels,
       preserving intentional white/bright fills inside diagrams. This is left
       as a future enhancement since the current approach works well for the
       full-inversion dark mode use case.
    """
    # Allow child themes to replace the entire dark pipeline
    if _image_processor_registry.get('dark'):
        return _image_processor_registry['dark'](app, exception)

    if exception:
        return
    if not to_bool(getattr(app.config, 'doxtr_dark_mode', False)):
        return
    if app.builder.name != 'latex':
        return
    # In passthrough mode (light dark-page), images are already fine — no processing
    if getattr(app.config, 'doxtr_dark_mode_strategy_resolved', 'invert') == 'passthrough':
        return
    if not _PIL_AVAILABLE:
        logger.warning(
            '[Doxtr Core] Pillow (PIL) is not installed — '
            'dark mode image processing is disabled. '
            'Install it with: pip install Pillow'
        )
        return

    recolor_grayscale = to_bool(
        getattr(app.config, 'doxtr_dark_recolor_grayscale', True), default=True)
    invert_color = to_bool(
        getattr(app.config, 'doxtr_dark_invert_color_images', True), default=True)

    # Early exit if both features are disabled — no image processing needed
    if not recolor_grayscale and not invert_color:
        return

    threshold = float(getattr(app.config, 'doxtr_dark_image_brightness_threshold', _DARK_BRIGHTNESS_DEFAULT))
    exclude_patterns = _get_exclude_patterns(app.config)

    # Guard against None: doxtr_dark_text_color is None until config_inited runs
    dark_text = getattr(app.config, 'doxtr_dark_text_color', '#DBDBDB') or '#DBDBDB'
    dark_page = getattr(app.config, 'doxtr_dark_semantic_palette', {}).get(
        'page', DOXTR_SEMANTIC_PALETTE_DARK_DEFAULTS['page'])

    text_rgb = _hex_to_rgb_tuple(dark_text)
    page_rgb = _hex_to_rgb_tuple(dark_page)

    # Collect work items without opening images (workers do that themselves)
    work_items = list(_iter_processable_image_paths(app, exclude_patterns))

    if not work_items:
        return

    workers = _get_parallel_workers(app.config)

    def _dark_args(dest_path, filename):
        return (dest_path, filename, recolor_grayscale, invert_color,
                threshold, text_rgb, page_rgb)

    _dispatch_parallel(
        work_items, _process_single_dark_image, _dark_args, workers,
        'dark mode'
    )
