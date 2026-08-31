"""
Tests for the \\DUrole paragraph tolerance fix in the preamble.

The core redefines \\DUrole as a \\long command (without the * short-form
flag) so that \\par tokens from sphinx-needs multi-value fields do not
cause a fatal "Paragraph ended before \\DUrole was complete." LaTeX error.

These tests verify the preamble template contains the expected redefinition
block with the correct structure and comments.
"""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PREAMBLE_PATH = Path(__file__).resolve().parent.parent / "doxtr_pdf_theme_core" / "preamble.tex_t"


def _read_preamble() -> str:
    """Return the full text of preamble.tex_t."""
    return _PREAMBLE_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDUroleRedefinitionPresent:
    """Verify the \\DUrole redefinition block exists in preamble.tex_t."""

    def test_renewcommand_durole_present(self):
        """The preamble must contain \\renewcommand{\\DUrole}[2] (long form)."""
        preamble = _read_preamble()
        assert r"\renewcommand{\DUrole}[2]" in preamble

    def test_no_star_form(self):
        r"""The redefinition must NOT use the * short form (\\renewcommand*)."""
        preamble = _read_preamble()
        # Ensure there is no \renewcommand*{\DUrole} — that would reintroduce
        # the bug by making it a short command again.
        assert r"\renewcommand*{\DUrole}" not in preamble

    def test_makeatletter_makeatother_wrapping(self):
        """The \\DUrole block must be wrapped in \\makeatletter / \\makeatother."""
        preamble = _read_preamble()
        # Find the DUrole renewcommand and verify it sits between
        # \makeatletter and \makeatother.
        idx_renew = preamble.index(r"\renewcommand{\DUrole}[2]")
        # Search backwards for the nearest \makeatletter
        before = preamble[:idx_renew]
        assert r"\makeatletter" in before, (
            r"\makeatletter must appear before the \DUrole redefinition"
        )
        last_makeatletter = before.rindex(r"\makeatletter")
        # There must not be a \makeatother between \makeatletter and \renewcommand
        between = preamble[last_makeatletter:idx_renew]
        assert r"\makeatother" not in between, (
            r"No \makeatother should appear between \makeatletter and \renewcommand{\DUrole}"
        )
        # Search forwards for the nearest \makeatother
        after = preamble[idx_renew:]
        assert r"\makeatother" in after, (
            r"\makeatother must appear after the \DUrole redefinition"
        )

    def test_comment_header_present(self):
        """The block must include the identifying comment header."""
        preamble = _read_preamble()
        assert r"FIX: SPHINX \DUrole PARAGRAPH TOLERANCE" in preamble

    def test_detokenize_dispatch_logic(self):
        """The redefinition must use \\detokenize and the two-tier dispatch."""
        preamble = _read_preamble()
        # Verify the DUrole<role> dispatch
        assert r"DUrole\detokenize{#1}" in preamble
        # Verify the docutilsrole<role> fallback
        assert r"docutilsrole\detokenize{#1}" in preamble

    def test_block_before_komafix(self):
        """The \\DUrole block must appear before the KOMA-Script conflict section."""
        preamble = _read_preamble()
        idx_durole = preamble.index(r"FIX: SPHINX \DUrole PARAGRAPH TOLERANCE")
        idx_koma = preamble.index("RESOLVE SPHINX vs KOMA-SCRIPT CONFLICT")
        assert idx_durole < idx_koma, (
            "The \\DUrole fix must be placed before the KOMA-Script conflict section"
        )

    def test_single_occurrence(self):
        """The \\renewcommand{\\DUrole} block must appear exactly once."""
        preamble = _read_preamble()
        assert preamble.count(r"\renewcommand{\DUrole}[2]") == 1

    def test_fallback_passthrough(self):
        """The bare #2 passthrough must exist as the final fallback branch."""
        preamble = _read_preamble()
        # Find the DUrole block and verify the passthrough is present
        idx_renew = preamble.index(r"\renewcommand{\DUrole}[2]")
        # The passthrough should be within the next 300 characters
        block = preamble[idx_renew:idx_renew + 300]
        assert "#2%" in block, (
            "The bare #2% passthrough must exist as the fallback "
            "when neither DUrole<role> nor docutilsrole<role> is defined"
        )

    def test_no_providecommand_star(self):
        r"""The preamble must NOT contain \providecommand*{\DUrole} (the buggy form)."""
        preamble = _read_preamble()
        assert r"\providecommand*{\DUrole}" not in preamble

    def test_jinja_conditional_guard(self):
        """The \\DUrole block must be wrapped in a doxtr_durole_par_fix conditional."""
        preamble = _read_preamble()
        idx_durole = preamble.index(r"FIX: SPHINX \DUrole PARAGRAPH TOLERANCE")
        # Search backwards for the nearest Jinja2 if
        before = preamble[:idx_durole]
        assert "doxtr_durole_par_fix" in before, (
            "The \\DUrole block must be gated by a doxtr_durole_par_fix conditional"
        )
