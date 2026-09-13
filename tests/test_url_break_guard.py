"""
Tests for the modular URL line-break guard.

The guard is intentionally NOT inlined in preamble.tex_t. Instead it is a fully
overridable .tex_t fragment (latex_styles/url_break/default.tex_t) resolved
through the same hierarchical template engine as every other style type, with a
core absolute fallback (DEFAULT_URL_BREAK_STYLE) and two config flags:

    doxtr_url_break_guard       — master enable/disable (default True)
    doxtr_url_break_aggressive  — aggressive alphanumeric break set (default True)

These tests verify config registration, template_vars threading, the rendered
LaTeX content, aggressive vs conservative behaviour, disable-emits-nothing, and
that the fragment is resolvable/overridable through the template engine.
"""

from pathlib import Path

from jinja2 import Environment

from doxtr_pdf_theme_core.core_fallbacks import DEFAULT_URL_BREAK_STYLE
from doxtr_pdf_theme_core.templates import (
    STYLE_TYPES, STYLE_FALLBACKS, render_template, LATEX_STYLES_DIR,
)

_PKG_DIR = Path(__file__).resolve().parent.parent / "doxtr_pdf_theme_core"
_INIT_PATH = _PKG_DIR / "__init__.py"
_PREAMBLE_PATH = _PKG_DIR / "preamble.tex_t"
_FRAGMENT_PATH = _PKG_DIR / LATEX_STYLES_DIR / "url_break" / "default.tex_t"


def _make_env() -> Environment:
    """Build a Jinja2 environment with the core's custom LaTeX delimiters."""
    return Environment(
        block_start_string='<%', block_end_string='%>',
        variable_start_string='<<', variable_end_string='>>',
        comment_start_string='<#', comment_end_string='#>',
    )


def _render(aggressive: bool) -> str:
    return render_template(
        _make_env(), DEFAULT_URL_BREAK_STYLE,
        {'doxtr_url_break_aggressive': aggressive},
    )


class TestConfigRegistration:
    """New config values must be registered in setup()."""

    def test_url_break_guard_registered(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert "app.add_config_value('doxtr_url_break_guard', True, 'env')" in source

    def test_url_break_aggressive_registered(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert "app.add_config_value('doxtr_url_break_aggressive', True, 'env')" in source


class TestTemplateVarsThreading:
    """Both flags must be threaded into template_vars in config_inited."""

    def test_guard_var_populated(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert "template_vars['doxtr_url_break_guard']" in source

    def test_aggressive_var_populated(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert "template_vars['doxtr_url_break_aggressive']" in source


class TestNotInlinedInPreamble:
    """Requirement #5: the guard must NOT be hardcoded inline in preamble.tex_t."""

    def test_preamble_has_no_url_break_guard(self):
        preamble = _PREAMBLE_PATH.read_text(encoding="utf-8")
        assert "doxtr_url_break_guard" not in preamble
        assert "URL LINE-BREAK GUARD" not in preamble
        assert r"\Urlmuskip" not in preamble


class TestStyleTypeRegistration:
    """url_break must be a resolvable, overridable style type."""

    def test_style_type_registered(self):
        assert STYLE_TYPES.get('url_break') == 'url_break'

    def test_style_fallback_registered(self):
        assert 'url_break' in STYLE_FALLBACKS

    def test_fallback_matches_constant(self):
        assert STYLE_FALLBACKS['url_break']('default') == DEFAULT_URL_BREAK_STYLE

    def test_core_fragment_ships_on_disk(self):
        """A child theme overrides by dropping its own file at this path."""
        assert _FRAGMENT_PATH.exists()

    def test_fragment_functional_lines_match_fallback(self):
        """The shipped .tex_t fragment and the absolute fallback must stay in sync."""
        def key_lines(s):
            return [l for l in s.splitlines() if l.strip().startswith('\\')]
        frag = _FRAGMENT_PATH.read_text(encoding="utf-8")
        assert key_lines(frag) == key_lines(DEFAULT_URL_BREAK_STYLE)


class TestRenderedContent:
    """The rendered LaTeX must be functionally equivalent to the original patch."""

    def test_urlmuskip_present(self):
        r"""The register read must be DEFERRED to \AtBeginDocument.

        Assigning \Urlmuskip immediately would freeze the register at the
        default before a child-theme redefinition of \doxtrurlmuskip could
        take effect. The deferred form is what makes the documented
        \doxtrurlmuskip override actually work.
        """
        out = _render(aggressive=True)
        assert r"\AtBeginDocument{\Urlmuskip=\doxtrurlmuskip\relax}" in out

    def test_muskip_uses_providecommand_not_newcommand(self):
        r"""\doxtrurlmuskip must be redefinable, so it must use \providecommand.

        \newcommand would make it an error for a child theme to redefine it
        with \providecommand of its own, and would also error if the macro
        was already defined upstream. \providecommand keeps the override
        contract intact.
        """
        out = _render(aggressive=True)
        assert r"\providecommand{\doxtrurlmuskip}" in out
        assert r"\newcommand{\doxtrurlmuskip}" not in out

    def test_configurable_muskip_default(self):
        r"""\doxtrurlmuskip must be a redefinable macro with the documented default."""
        out = _render(aggressive=True)
        assert r"\providecommand{\doxtrurlmuskip}{0mu plus 1mu}" in out

    def test_urlbreaks_extended(self):
        out = _render(aggressive=True)
        assert r"\g@addto@macro\UrlBreaks{\UrlOrds}" in out
        assert r"\g@addto@macro\UrlBreaks{%" in out

    def test_structural_break_chars_present(self):
        r"""Structural URL break chars must always be added (both modes)."""
        for aggressive in (True, False):
            out = _render(aggressive=aggressive)
            assert r"\do\." in out
            assert r"\do\/" in out
            assert r"\do\?" in out
            assert r"\do\=" in out
            assert r"\do\&" in out

    def test_url_package_guard(self):
        out = _render(aggressive=True)
        assert r"\@ifpackageloaded{url}{}{\usepackage{url}}" in out

    def test_makeatletter_wrapped(self):
        out = _render(aggressive=True)
        assert r"\makeatletter" in out
        assert r"\makeatother" in out

    def test_comment_header_preserved(self):
        """Explanatory comments are documentation and must be preserved."""
        assert "URL LINE-BREAK GUARD" in DEFAULT_URL_BREAK_STYLE


class TestAggressiveMode:
    """Aggressive mode adds alphanumeric breaks; conservative omits them."""

    def test_aggressive_adds_letters(self):
        out = _render(aggressive=True)
        assert r"\do\a" in out
        assert r"\do\z" in out
        assert r"\do\A" in out
        assert r"\do\Z" in out

    def test_aggressive_adds_digits(self):
        out = _render(aggressive=True)
        assert r"\do\0" in out
        assert r"\do\9" in out

    def test_conservative_omits_letters(self):
        out = _render(aggressive=False)
        assert r"\do\a" not in out
        assert r"\do\z" not in out

    def test_conservative_omits_digits(self):
        out = _render(aggressive=False)
        assert r"\do\9" not in out

    def test_conservative_keeps_structural(self):
        """Conservative mode must still add structural break chars."""
        out = _render(aggressive=False)
        assert r"\do\." in out
        assert r"\do\:" in out


class TestDisableEmitsNothing:
    """When the guard is disabled, no LaTeX is injected."""

    def test_hook_holder_empty_when_disabled(self):
        """The preamble-hook holder must return '' when nothing was rendered."""
        import doxtr_pdf_theme_core as mod
        # Simulate the disabled path: render stage skips and resets the holder.
        original = mod._rendered_url_break_guard
        try:
            mod._rendered_url_break_guard = ''
            assert mod._inject_url_break_guard() == ''
        finally:
            mod._rendered_url_break_guard = original

    def test_hook_returns_rendered_when_enabled(self):
        """The hook returns the stashed rendered LaTeX when enabled."""
        import doxtr_pdf_theme_core as mod
        original = mod._rendered_url_break_guard
        try:
            mod._rendered_url_break_guard = _render(aggressive=True)
            assert r"\Urlmuskip" in mod._inject_url_break_guard()
        finally:
            mod._rendered_url_break_guard = original


class TestPreambleHookWiring:
    """The guard must be injected via an after_packages preamble hook."""

    def test_hook_function_exists(self):
        import doxtr_pdf_theme_core as mod
        assert callable(mod._inject_url_break_guard)

    def test_hook_registered_after_packages(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert (
            "register_preamble_hook(_inject_url_break_guard, position='after_packages')"
            in source
        )

    def test_hook_gated_by_config(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        idx_reg = source.index("register_preamble_hook(_inject_url_break_guard")
        before = source[:idx_reg]
        assert "getattr(config, 'doxtr_url_break_guard', True)" in before


class TestRenderStageGating:
    """The render stage must skip rendering when the guard is disabled."""

    def test_render_gated_by_guard_flag(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        # The url_break template is resolved under the guard flag. Anchor on the
        # render call's own token (`template_vars, 'url_break'`) rather than the
        # exact full argument list, so benign reflows of the following args
        # (e.g. DEFAULT_STYLE_NAME on its own line) don't break this test.
        assert "'url_break'" in source
        idx = source.index("template_vars, 'url_break'")
        before = source[:idx]
        assert "getattr(config, 'doxtr_url_break_guard', True)" in before


class TestBehavioralRender:
    """End-to-end render through the real template engine.

    These complement the source-string structural guards above by proving
    that the ``doxtr_url_break_aggressive`` template var actually reaches the
    fragment and toggles the aggressive break set, using the same
    ``resolve_and_render_template`` path config_inited uses.
    """

    def _resolve_val(self, conf_attr, theme_key, fallback=None, section=None):
        """Minimal 3-tier resolver stub: always returns the fallback.

        Mirrors the real resolve_val for a config where no custom
        ``doxtr_url_break_path`` is set, so resolution falls through to the
        core fragment / absolute fallback.
        """
        return fallback

    def _fake_app(self, tmp_path):
        """A stand-in Sphinx app exposing only confdir/srcdir for resolution."""
        class _App:
            confdir = str(tmp_path)
            srcdir = str(tmp_path)
        return _App()

    def test_aggressive_true_threads_to_fragment(self, tmp_path):
        from doxtr_pdf_theme_core.templates import (
            resolve_and_render_template, DEFAULT_STYLE_NAME,
        )
        out = resolve_and_render_template(
            self._fake_app(tmp_path), _make_env(),
            {'doxtr_url_break_aggressive': True},
            'url_break', DEFAULT_STYLE_NAME, [], self._resolve_val,
        )
        assert r"\do\a" in out and r"\do\Z" in out
        assert r"\AtBeginDocument{\Urlmuskip=\doxtrurlmuskip\relax}" in out

    def test_aggressive_false_threads_to_fragment(self, tmp_path):
        from doxtr_pdf_theme_core.templates import (
            resolve_and_render_template, DEFAULT_STYLE_NAME,
        )
        out = resolve_and_render_template(
            self._fake_app(tmp_path), _make_env(),
            {'doxtr_url_break_aggressive': False},
            'url_break', DEFAULT_STYLE_NAME, [], self._resolve_val,
        )
        # Structural breaks remain; alphanumeric breaks are gated out.
        assert r"\do\." in out
        assert r"\do\a" not in out
        assert r"\do\9" not in out


class TestOverridePrecedence:
    """A child theme / user override must win over the core fragment.

    Drives the real resolve_template hierarchy: a .tex_t dropped in a theme
    style path is returned instead of the core url_break fragment, proving
    url_break is overridable exactly like every other style type.
    """

    def _fake_app(self, tmp_path):
        class _App:
            confdir = str(tmp_path)
            srcdir = str(tmp_path)
        return _App()

    def test_theme_path_override_wins(self, tmp_path):
        from doxtr_pdf_theme_core.templates import (
            resolve_and_render_template, DEFAULT_STYLE_NAME,
        )

        def resolve_val(conf_attr, theme_key, fallback=None, section=None):
            return fallback

        # Drop an override at <theme_path>/url_break/default.tex_t
        theme_path = tmp_path / "mytheme_styles"
        override_dir = theme_path / "url_break"
        override_dir.mkdir(parents=True)
        sentinel = r"\newcommand{\mythemeurlbreakoverride}{}"
        (override_dir / f"{DEFAULT_STYLE_NAME}.tex_t").write_text(
            sentinel + "\n", encoding="utf-8",
        )
        out = resolve_and_render_template(
            self._fake_app(tmp_path), _make_env(),
            {'doxtr_url_break_aggressive': True},
            'url_break', DEFAULT_STYLE_NAME, [str(theme_path)], resolve_val,
        )
        # The override replaced the core fragment entirely.
        assert sentinel in out
        assert r"\Urlmuskip" not in out

    def test_custom_path_config_key_is_url_break_path(self, tmp_path):
        r"""The tier-1 custom folder must be consulted via doxtr_url_break_path.

        The resolution engine derives the custom-path config key from the
        style_dir (f'doxtr_{style_dir}_path'). For url_break that is
        ``doxtr_url_break_path``; this proves a folder supplied through that
        key is honoured (parity with the other style types' tier-1 folder).
        """
        from doxtr_pdf_theme_core.templates import (
            resolve_and_render_template, DEFAULT_STYLE_NAME,
        )
        custom = tmp_path / "custom_url_break"
        custom.mkdir()
        sentinel = r"\newcommand{\customurlbreak}{}"
        (custom / f"{DEFAULT_STYLE_NAME}.tex_t").write_text(
            sentinel + "\n", encoding="utf-8",
        )

        def resolve_val(conf_attr, theme_key, fallback=None, section=None):
            # Honour only the derived custom-path key.
            if conf_attr == 'doxtr_url_break_path' or theme_key == 'url_break_path':
                return 'custom_url_break'
            return fallback

        out = resolve_and_render_template(
            self._fake_app(tmp_path), _make_env(),
            {'doxtr_url_break_aggressive': True},
            'url_break', DEFAULT_STYLE_NAME, [], resolve_val,
        )
        assert sentinel in out
        assert r"\Urlmuskip" not in out


class TestCustomPathRegistration:
    """doxtr_url_break_path must be a registered config value (parity)."""

    def test_url_break_path_registered(self):
        source = _INIT_PATH.read_text(encoding="utf-8")
        assert "app.add_config_value('doxtr_url_break_path', '', 'env')" in source

    def test_url_break_path_in_globals(self):
        from doxtr_pdf_theme_core.core_config import DOXTR_GLOBALS
        assert 'url_break_path' in DOXTR_GLOBALS['light']
