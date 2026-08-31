"""
Tests for the global overflow guard blocks in the preamble.

Verifies the preamble template contains the expected emergency stretch,
tolerance, mbox override, and sphinxhref override blocks when
doxtr_global_overflow_guard is True.
"""

from pathlib import Path
import pytest

_PREAMBLE_PATH = Path(__file__).resolve().parent.parent / "doxtr_pdf_theme_core" / "preamble.tex_t"


def _read_preamble() -> str:
    return _PREAMBLE_PATH.read_text(encoding="utf-8")


class TestGlobalOverflowGuardPresent:
    """Verify the global overflow guard blocks exist in preamble.tex_t."""

    def test_jinja_conditional_guard(self):
        """The block must be gated by doxtr_global_overflow_guard conditional."""
        preamble = _read_preamble()
        assert "doxtr_global_overflow_guard" in preamble

    def test_emergencystretch_present(self):
        r"""The preamble must contain \emergencystretch=3em."""
        preamble = _read_preamble()
        assert r"\emergencystretch=3em" in preamble

    def test_tolerance_present(self):
        r"""The preamble must contain \tolerance=400."""
        preamble = _read_preamble()
        assert r"\tolerance=400" in preamble

    def test_mbox_override_present(self):
        r"""The preamble must contain the \mbox override with configurable threshold."""
        preamble = _read_preamble()
        assert r"\let\doxtr@orig@mbox\mbox" in preamble
        assert r"\renewcommand{\mbox}[1]{%" in preamble
        assert r"\doxtr@mbox@maxfrac" in preamble

    def test_mbox_threshold_configurable(self):
        r"""The \mbox threshold must use a configurable macro, not a hardcoded value."""
        preamble = _read_preamble()
        assert r"\def\doxtr@mbox@maxfrac{0.3}" in preamble
        assert r"\ifdim\wd0>\doxtr@mbox@maxfrac\linewidth" in preamble

    def test_sphinxhref_override_present(self):
        r"""The preamble must contain the \sphinxhref override."""
        preamble = _read_preamble()
        assert r"\let\doxtr@orig@sphinxhref\sphinxhref" in preamble
        assert r"\doxtr@sphinxhyphen@breakable" in preamble

    def test_comment_header_present(self):
        """The block must include the identifying comment header."""
        preamble = _read_preamble()
        assert "GLOBAL TEXT OVERFLOW SAFETY NET" in preamble

    def test_mbox_override_inside_makeatletter(self):
        r"""The \mbox override must be wrapped in \makeatletter/\makeatother."""
        preamble = _read_preamble()
        idx_mbox = preamble.index(r"\let\doxtr@orig@mbox\mbox")
        before = preamble[:idx_mbox]
        assert r"\makeatletter" in before
        # Nearest \makeatletter must not have a closing \makeatother before the \let
        last_makeatletter = before.rindex(r"\makeatletter")
        between = preamble[last_makeatletter:idx_mbox]
        assert r"\makeatother" not in between, (
            r"No \makeatother should appear between \makeatletter and \let\doxtr@orig@mbox"
        )

    def test_sphinxhref_override_inside_makeatletter(self):
        r"""The \sphinxhref override must be wrapped in \makeatletter/\makeatother."""
        preamble = _read_preamble()
        idx_href = preamble.index(r"\let\doxtr@orig@sphinxhref\sphinxhref")
        before = preamble[:idx_href]
        last_makeatletter = before.rindex(r"\makeatletter")
        between = preamble[last_makeatletter:idx_href]
        assert r"\makeatother" not in between

    def test_sphinxhyphen_breakable_defined(self):
        r"""The breakable sphinxhyphen command must be defined."""
        preamble = _read_preamble()
        assert r"\newcommand{\doxtr@sphinxhyphen@breakable}" in preamble
        # It must use penalty0 for break opportunity
        assert r"\penalty0" in preamble

    def test_block_gated_by_endif(self):
        """The global overflow guard block must be properly closed with endif."""
        preamble = _read_preamble()
        idx_guard = preamble.index("doxtr_global_overflow_guard")
        # Find the matching endif after the block
        after = preamble[idx_guard:]
        assert "<% endif %>" in after


class TestBuildpageFilterPresent:
    """Verify the LuaTeX buildpage_filter callback exists in preamble.tex_t."""

    def test_buildpage_filter_callback(self):
        """The preamble must contain the buildpage_filter LuaTeX callback."""
        preamble = _read_preamble()
        assert "buildpage_filter" in preamble
        assert "doxtr.cap_pagegoal" in preamble

    def test_gated_by_pagegoal_guard(self):
        """The buildpage_filter must be gated by doxtr_pagegoal_overflow_guard."""
        preamble = _read_preamble()
        idx_callback = preamble.index("buildpage_filter")
        before = preamble[:idx_callback]
        assert "doxtr_pagegoal_overflow_guard" in before

    def test_callback_caps_pagegoal(self):
        """The callback must enforce pagegoal <= textheight."""
        preamble = _read_preamble()
        # Find the Lua add_to_callback block (not the comment references)
        idx_start = preamble.index("luatexbase.add_to_callback('buildpage_filter'")
        block = preamble[idx_start:idx_start + 300]
        assert "tex.pagegoal" in block
        assert "tex.dimen.textheight" in block

    def test_callback_removal_documented(self):
        """Theme authors must be told how to remove the callback."""
        preamble = _read_preamble()
        assert "luatexbase.remove_from_callback" in preamble
        assert "'doxtr.cap_pagegoal'" in preamble


class TestNeedspaceGuards:
    """Verify paragraph/subparagraph needspace guards in preamble.tex_t."""

    def test_paragraph_needspace(self):
        preamble = _read_preamble()
        assert r"\xpretocmd{\paragraph}{\needspace{\doxtr@paragraph@needspace}}" in preamble

    def test_subparagraph_needspace(self):
        preamble = _read_preamble()
        assert r"\xpretocmd{\subparagraph}{\needspace{\doxtr@paragraph@needspace}}" in preamble

    def test_needspace_configurable(self):
        r"""The needspace amount must use a configurable macro."""
        preamble = _read_preamble()
        assert r"\newcommand{\doxtr@paragraph@needspace}{3\baselineskip}" in preamble

    def test_needspace_gated_by_config(self):
        """The needspace block must be gated by doxtr_heading_needspace_guard."""
        preamble = _read_preamble()
        assert "doxtr_heading_needspace_guard" in preamble
        # Verify the guard appears before the needspace commands
        idx_guard = preamble.index("doxtr_heading_needspace_guard")
        idx_needspace = preamble.index(r"\doxtr@paragraph@needspace")
        assert idx_guard < idx_needspace

    def test_needspace_comment_documents_disable(self):
        """The block must document how to disable it."""
        preamble = _read_preamble()
        assert "doxtr_heading_needspace_guard = False" in preamble


class TestBreakCharsSync:
    """Verify DEFAULT_BREAK_CHARS sources from core_config.py."""

    def test_default_break_chars_excludes_hyphen(self):
        """DEFAULT_BREAK_CHARS must not contain '-' (handled by \\sphinxhyphen)."""
        from doxtr_pdf_theme_core.ast_processors.tables import DEFAULT_BREAK_CHARS
        assert '-' not in DEFAULT_BREAK_CHARS
        assert DEFAULT_BREAK_CHARS == '/.:'

    def test_break_chars_sourced_from_core_config(self):
        """DEFAULT_BREAK_CHARS must match core_config value (DRY)."""
        from doxtr_pdf_theme_core.ast_processors.tables import DEFAULT_BREAK_CHARS
        from doxtr_pdf_theme_core.core_config import DOXTR_TABLES
        assert DEFAULT_BREAK_CHARS == DOXTR_TABLES['generic']['break_chars']


class TestLongtablePagegoalCap:
    r"""Verify longtable gets \doxtrcapbreakablepagegoal."""

    def test_longtable_has_pagegoal_cap(self):
        preamble = _read_preamble()
        assert r"\AtBeginEnvironment{longtable}{\emergencystretch=1em\doxtrcapbreakablepagegoal}" in preamble

    def test_tabulary_no_pagegoal_cap(self):
        """tabulary must NOT get the pagegoal cap (it's a trial-pass environment)."""
        preamble = _read_preamble()
        assert r"\AtBeginEnvironment{tabulary}{\emergencystretch=1em}" in preamble
        # Verify it does NOT have \doxtrcapbreakablepagegoal
        line = [l for l in preamble.splitlines() if "tabulary" in l and "emergencystretch" in l][0]
        assert "doxtrcapbreakablepagegoal" not in line

    def test_tabular_no_pagegoal_cap(self):
        """tabular must NOT get the pagegoal cap (short environment)."""
        preamble = _read_preamble()
        line = [l for l in preamble.splitlines() if "tabular}" in l and "emergencystretch" in l][0]
        assert "doxtrcapbreakablepagegoal" not in line


class TestLandscapeSaveboxOverflow:
    """Verify the preemptive page break in doxtrautolandscape."""

    def test_preemptive_pagebreak_present(self):
        """The auto-landscape environment must check remaining page space."""
        preamble = _read_preamble()
        assert r"\pagetotal+\ht\doxtr@landscapebox+\dp\doxtr@landscapebox" in preamble

    def test_newpage_on_overflow(self):
        r"""If the savebox won't fit, \newpage must be issued."""
        preamble = _read_preamble()
        idx_check = preamble.index(r"\pagetotal+\ht\doxtr@landscapebox")
        block = preamble[idx_check:idx_check + 200]
        assert r"\newpage" in block


class TestConfigRegistration:
    """Verify new config values are registered in setup()."""

    def test_global_overflow_guard_registered(self):
        """doxtr_global_overflow_guard must be registered as a config value."""
        import doxtr_pdf_theme_core as mod
        # Verify the config name appears in the source
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "doxtr_global_overflow_guard" in source
        assert "app.add_config_value('doxtr_global_overflow_guard'" in source

    def test_heading_needspace_guard_registered(self):
        """doxtr_heading_needspace_guard must be registered as a config value."""
        import doxtr_pdf_theme_core as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "app.add_config_value('doxtr_heading_needspace_guard'" in source

    def test_template_vars_populated(self):
        """Template variables must be set for all new guards."""
        import doxtr_pdf_theme_core as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "template_vars['doxtr_global_overflow_guard']" in source
        assert "template_vars['doxtr_heading_needspace_guard']" in source
