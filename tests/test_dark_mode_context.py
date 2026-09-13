"""
Tests for the public dark-mode context API used by inline content-generating
extensions (e.g. doxtr-roadmap).

These helpers expose the dark-mode state that ``config_inited`` computes so
that extensions which generate diagram source *inline* (with no source file on
disk, hence no ``_dark`` file swap available) can emit dark-appropriate source
directly instead of relying on the lossy per-pixel image fallback.

The helpers are pure, read-only accessors over the Sphinx config object, so
they can be tested with a lightweight stand-in config — no Sphinx/LaTeX build
required.
"""

import doxtr_pdf_theme_core as core


class _FakeConfig:
    """Minimal stand-in for a Sphinx ``config`` object.

    Only the attributes the helpers read are set; missing attributes exercise
    the ``getattr(..., default)`` fallbacks the same way a real config with
    unresolved values would.
    """

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


# ---------------------------------------------------------------------------
# is_dark_mode_active
# ---------------------------------------------------------------------------


class TestIsDarkModeActive:
    def test_false_when_dark_mode_off(self):
        cfg = _FakeConfig(doxtr_dark_mode=False)
        assert core.is_dark_mode_active(cfg) is False

    def test_false_when_attr_missing(self):
        # No doxtr_dark_mode attribute at all → treated as off.
        cfg = _FakeConfig()
        assert core.is_dark_mode_active(cfg) is False

    def test_true_when_dark_and_invert(self):
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="invert",
        )
        assert core.is_dark_mode_active(cfg) is True

    def test_false_when_passthrough(self):
        # Passthrough = light dark-mode page → light source is appropriate.
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="passthrough",
        )
        assert core.is_dark_mode_active(cfg) is False

    def test_defaults_to_invert_when_strategy_missing(self):
        # dark on, strategy attribute absent → default 'invert' → active.
        cfg = _FakeConfig(doxtr_dark_mode=True)
        assert core.is_dark_mode_active(cfg) is True

    def test_respects_bool_coercion(self):
        # to_bool handles truthy strings like '1'/'true'.
        cfg = _FakeConfig(
            doxtr_dark_mode="1",
            doxtr_dark_mode_strategy_resolved="invert",
        )
        assert core.is_dark_mode_active(cfg) is True


# ---------------------------------------------------------------------------
# get_dark_palette
# ---------------------------------------------------------------------------


class TestGetDarkPalette:
    def test_none_when_inactive(self):
        cfg = _FakeConfig(doxtr_dark_mode=False)
        assert core.get_dark_palette(cfg) is None

    def test_none_when_passthrough(self):
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="passthrough",
            doxtr_dark_semantic_palette={"primary": "#E8E8E8", "page": "#242424"},
        )
        assert core.get_dark_palette(cfg) is None

    def test_returns_palette_when_active(self):
        palette = {"primary": "#E8E8E8", "page": "#242424"}
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="invert",
            doxtr_dark_semantic_palette=palette,
        )
        result = core.get_dark_palette(cfg)
        assert result == palette

    def test_returns_copy_not_reference(self):
        palette = {"primary": "#E8E8E8", "page": "#242424"}
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="invert",
            doxtr_dark_semantic_palette=palette,
        )
        result = core.get_dark_palette(cfg)
        result["primary"] = "#000000"
        # Mutating the returned dict must not affect the config.
        assert palette["primary"] == "#E8E8E8"

    def test_none_when_palette_empty(self):
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="invert",
            doxtr_dark_semantic_palette={},
        )
        assert core.get_dark_palette(cfg) is None


# ---------------------------------------------------------------------------
# get_dark_mode_context
# ---------------------------------------------------------------------------


class TestGetDarkModeContext:
    _KEYS = {"active", "strategy", "palette", "text_color", "page_color", "invert_color"}

    def test_inactive_shape(self):
        cfg = _FakeConfig(doxtr_dark_mode=False)
        ctx = core.get_dark_mode_context(cfg)
        assert set(ctx.keys()) == self._KEYS
        assert ctx["active"] is False
        assert ctx["palette"] is None
        assert ctx["text_color"] is None
        assert ctx["page_color"] is None
        assert callable(ctx["invert_color"])

    def test_active_shape(self):
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="invert",
            doxtr_dark_semantic_palette={"primary": "#E8E8E8", "page": "#242424"},
            doxtr_dark_text_color="#DBDBDB",
        )
        ctx = core.get_dark_mode_context(cfg)
        assert set(ctx.keys()) == self._KEYS
        assert ctx["active"] is True
        assert ctx["strategy"] == "invert"
        assert ctx["palette"] == {"primary": "#E8E8E8", "page": "#242424"}
        assert ctx["text_color"] == "#DBDBDB"
        assert ctx["page_color"] == "#242424"

    def test_invert_color_is_hex_dark_invert(self):
        cfg = _FakeConfig(doxtr_dark_mode=False)
        ctx = core.get_dark_mode_context(cfg)
        # White soft-inverts to the canonical near-black dark page.
        assert ctx["invert_color"]("#FFFFFF") == "#242424"

    def test_passthrough_reports_inactive(self):
        cfg = _FakeConfig(
            doxtr_dark_mode=True,
            doxtr_dark_mode_strategy_resolved="passthrough",
            doxtr_dark_semantic_palette={"primary": "#E8E8E8", "page": "#FCF6E5"},
        )
        ctx = core.get_dark_mode_context(cfg)
        assert ctx["active"] is False
        assert ctx["strategy"] == "passthrough"
        assert ctx["palette"] is None


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------


def test_functions_exported():
    for name in ("is_dark_mode_active", "get_dark_palette", "get_dark_mode_context"):
        assert name in core.__all__
        assert callable(getattr(core, name))


# ---------------------------------------------------------------------------
# mark_image_dark_ready
# ---------------------------------------------------------------------------


class _FakeEnv:
    pass


class _FakeApp:
    def __init__(self, dark_mode=True):
        self.env = _FakeEnv()
        self.config = _FakeConfig(doxtr_dark_mode=dark_mode)


class TestMarkImageDarkReady:
    def test_registers_basename_when_dark(self):
        app = _FakeApp(dark_mode=True)
        core.mark_image_dark_ready(app, "plantuml-abc123.png")
        assert "plantuml-abc123.png" in app.env._doxtr_dark_substituted

    def test_strips_path_to_basename(self):
        app = _FakeApp(dark_mode=True)
        core.mark_image_dark_ready(app, "/some/out/dir/plantuml-def.png")
        assert app.env._doxtr_dark_substituted == {"plantuml-def.png"}

    def test_noop_when_dark_off(self):
        app = _FakeApp(dark_mode=False)
        core.mark_image_dark_ready(app, "plantuml-abc.png")
        assert not hasattr(app.env, "_doxtr_dark_substituted")

    def test_noop_on_empty_filename(self):
        app = _FakeApp(dark_mode=True)
        core.mark_image_dark_ready(app, "")
        assert not hasattr(app.env, "_doxtr_dark_substituted")

    def test_appends_to_existing_set(self):
        app = _FakeApp(dark_mode=True)
        app.env._doxtr_dark_substituted = {"existing.png"}
        core.mark_image_dark_ready(app, "plantuml-new.png")
        assert app.env._doxtr_dark_substituted == {"existing.png", "plantuml-new.png"}

    def test_exported(self):
        assert "mark_image_dark_ready" in core.__all__
        assert callable(core.mark_image_dark_ready)
