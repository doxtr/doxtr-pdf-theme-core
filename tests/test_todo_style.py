"""
Tests for the ``.. todo::`` directive styling (the ``ddtodobox`` tcolorbox).

The core styles ``sphinx.ext.todo`` output via a dedicated tcolorbox
environment (``ddtodobox``) modelled on the classic tcolorbox "flip title"
tile pattern. These tests verify the style template, the absolute fallback,
and the config wiring — none of which require a full Sphinx/LaTeX build.
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "doxtr_pdf_theme_core"
    / "latex_styles"
    / "todo"
    / "default.tex_t"
)


def _read_template() -> str:
    """Return the full text of the todo default.tex_t template."""
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: style template
# ---------------------------------------------------------------------------


class TestTodoTemplate:
    """Verify the todo default.tex_t template structure."""

    def test_defines_ddtodobox(self):
        """The template must define the ddtodobox environment."""
        assert r"\newtcolorbox{ddtodobox}" in _read_template()

    def test_uses_tile_style(self):
        """The template must use the flat 'tile' style."""
        assert "tile," in _read_template()

    def test_uses_flip_title_sharp_corners(self):
        """The template must use flip title with sharp corners."""
        assert "flip title={sharp corners}" in _read_template()

    def test_defines_all_cmyk_color_vars(self):
        """The template must reference all four *_cmyk context variables."""
        tpl = _read_template()
        for var in (
            "title_font_color_cmyk",
            "title_background_color_cmyk",
            "content_background_color_cmyk",
            "content_font_color_cmyk",
        ):
            assert var in tpl, f"Expected {var} in todo template"


# ---------------------------------------------------------------------------
# Tests: absolute fallback
# ---------------------------------------------------------------------------


class TestTodoFallback:
    """Verify the DEFAULT_TODO_STYLE absolute fallback string."""

    def test_fallback_defines_ddtodobox_with_arg(self):
        """The fallback must define ddtodobox taking one argument."""
        from doxtr_pdf_theme_core.core_fallbacks import DEFAULT_TODO_STYLE

        assert r"\newtcolorbox{ddtodobox}[1]" in DEFAULT_TODO_STYLE

    def test_fallback_uses_tile_and_flip_title(self):
        """The fallback must mirror the template's tile + flip title style."""
        from doxtr_pdf_theme_core.core_fallbacks import DEFAULT_TODO_STYLE

        assert "tile," in DEFAULT_TODO_STYLE
        assert "flip title={sharp corners}" in DEFAULT_TODO_STYLE

    def test_fallback_sets_fontupper(self):
        """The fallback must set fontupper for parity with the template."""
        from doxtr_pdf_theme_core.core_fallbacks import DEFAULT_TODO_STYLE

        assert "fontupper" in DEFAULT_TODO_STYLE


# ---------------------------------------------------------------------------
# Tests: config wiring
# ---------------------------------------------------------------------------


class TestTodoConfigWiring:
    """Verify the todo section is registered in the config machinery."""

    def test_todo_in_valid_keys(self):
        """The 'todo' section must be present in VALID_KEYS."""
        from doxtr_pdf_theme_core.config import VALID_KEYS

        assert "todo" in VALID_KEYS

    def test_todo_in_config_manifest(self):
        """The 'todo' section must be present in CORE_CONFIG_MANIFEST."""
        from doxtr_pdf_theme_core.core_config import CORE_CONFIG_MANIFEST

        assert "todo" in CORE_CONFIG_MANIFEST
