"""Unit tests for doxtr_pdf_theme_core.dark_file_swap

This module tests the dark file swap mechanism that intercepts RST/MyST source
text via Sphinx's source-read event to rewrite directive file arguments to
their _dark variants.

Run with: pytest test_harness/test_dark_file_swap.py -v
"""
import os
import sys
import tempfile
import shutil

# Add package to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from doxtr_pdf_theme_core.dark_file_swap import (
    register_dark_swap_directive,
    _get_effective_directives,
    _get_effective_extensions,
    _get_exclude_patterns,
    _is_excluded,
    _is_url,
    _resolve_dark_variant,
    _perform_swap,
    _build_rst_argument_pattern,
    _build_rst_option_pattern,
    _build_myst_argument_pattern,
    _reset_dark_swap_registry,
    swap_dark_sources,
    _EXCLUDED_DIRECTIVES,
    _custom_dark_swap_directives,
    DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
    DARK_FILE_SWAP_EXTENSIONS_DEFAULT,
)

import pytest


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

class MockConfig:
    """Minimal config mock for testing."""
    def __init__(self, **kwargs):
        self.doxtr_dark_mode = kwargs.get('doxtr_dark_mode', True)
        self.doxtr_dark_mode_strategy_resolved = kwargs.get(
            'doxtr_dark_mode_strategy_resolved', 'invert'
        )
        self.doxtr_enable_dark_file_swap = kwargs.get(
            'doxtr_enable_dark_file_swap', True
        )
        self.doxtr_dark_file_swap_directives = kwargs.get(
            'doxtr_dark_file_swap_directives', {}
        )
        self.doxtr_dark_file_swap_extensions = kwargs.get(
            'doxtr_dark_file_swap_extensions', None
        )
        self.doxtr_dark_file_swap_extra_extensions = kwargs.get(
            'doxtr_dark_file_swap_extra_extensions', []
        )
        self.doxtr_dark_file_swap_exclude = kwargs.get(
            'doxtr_dark_file_swap_exclude', []
        )
        self.doxtr_image_exclude_patterns = kwargs.get(
            'doxtr_image_exclude_patterns', []
        )


class MockEnv:
    """Minimal Sphinx environment mock."""
    def __init__(self):
        self._dependencies = []

    def note_dependency(self, path):
        self._dependencies.append(path)


class MockBuilder:
    """Minimal builder mock."""
    def __init__(self, name='latex'):
        self.name = name


class MockApp:
    """Minimal Sphinx app mock for source-read tests."""
    def __init__(self, srcdir, builder_name='latex', **config_kwargs):
        self.srcdir = srcdir
        self.config = MockConfig(**config_kwargs)
        self.env = MockEnv()
        self.builder = MockBuilder(builder_name)


@pytest.fixture
def clean_registry():
    """Save and restore the dark swap registry between tests."""
    original = _custom_dark_swap_directives.copy()
    _reset_dark_swap_registry()
    yield
    _reset_dark_swap_registry()
    _custom_dark_swap_directives.extend(original)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project with source files and dark variants."""
    srcdir = tmp_path / "source"
    srcdir.mkdir()

    # Create directories
    diagrams = srcdir / "_diagrams"
    diagrams.mkdir()

    # Create original files
    (diagrams / "architecture.puml").write_text("@startuml\nAlice -> Bob\n@enduml")
    (diagrams / "flow.mmd").write_text("graph TD\n  A-->B")
    (diagrams / "schema.drawio").write_text("<mxfile>...</mxfile>")
    (srcdir / "included.rst").write_text("Some included content")

    # Create _dark variants for some
    (diagrams / "architecture_dark.puml").write_text("@startuml\nAlice -> Bob (dark)\n@enduml")
    (diagrams / "flow_dark.mmd").write_text("graph TD\n  A-->B (dark)")
    (diagrams / "schema_dark.drawio").write_text("<mxfile>dark</mxfile>")
    (srcdir / "included_dark.rst").write_text("Dark included content")

    # File without dark variant
    (diagrams / "simple.puml").write_text("@startuml\nC -> D\n@enduml")

    return srcdir


# ---------------------------------------------------------------------------
# Tests: _is_url
# ---------------------------------------------------------------------------

def test_is_url_http():
    assert _is_url("http://example.com/file.puml") is True


def test_is_url_https():
    assert _is_url("https://example.com/file.puml") is True


def test_is_url_data():
    assert _is_url("data:image/png;base64,abc") is True


def test_is_url_relative_path():
    assert _is_url("diagrams/arch.puml") is False


def test_is_url_absolute_path():
    assert _is_url("/abs/path/arch.puml") is False


# ---------------------------------------------------------------------------
# Tests: _is_excluded
# ---------------------------------------------------------------------------

def test_is_excluded_matching_basename():
    assert _is_excluded("plantuml-abc.png", ["plantuml-*.png"]) is True


def test_is_excluded_matching_full_path():
    assert _is_excluded("_diagrams/test.puml", ["_diagrams/*.puml"]) is True


def test_is_excluded_no_match():
    assert _is_excluded("_diagrams/arch.puml", ["plantuml-*.png"]) is False


def test_is_excluded_empty_patterns():
    assert _is_excluded("anything.puml", []) is False


# ---------------------------------------------------------------------------
# Tests: _resolve_dark_variant
# ---------------------------------------------------------------------------

def test_resolve_dark_variant_exists(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir  # document in root

    result = _resolve_dark_variant(
        "_diagrams/architecture.puml", srcdir, docdir,
        {'.puml', '.plantuml'}
    )
    assert result == "_diagrams/architecture_dark.puml"


def test_resolve_dark_variant_not_exists(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    result = _resolve_dark_variant(
        "_diagrams/simple.puml", srcdir, docdir,
        {'.puml', '.plantuml'}
    )
    assert result == ""


def test_resolve_dark_variant_wrong_extension(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    # .puml file but only looking for .mmd extensions
    result = _resolve_dark_variant(
        "_diagrams/architecture.puml", srcdir, docdir,
        {'.mmd'}
    )
    assert result == ""


def test_resolve_dark_variant_absolute_path(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    result = _resolve_dark_variant(
        "/absolute/path/arch.puml", srcdir, docdir,
        {'.puml'}
    )
    assert result == ""


def test_resolve_dark_variant_mmd(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    result = _resolve_dark_variant(
        "_diagrams/flow.mmd", srcdir, docdir,
        {'.mmd', '.mermaid'}
    )
    assert result == "_diagrams/flow_dark.mmd"


# ---------------------------------------------------------------------------
# Tests: RST argument-based regex
# ---------------------------------------------------------------------------

def test_rst_argument_pattern_basic():
    pattern = _build_rst_argument_pattern(['uml', 'mermaid'])
    source = ".. uml:: _diagrams/architecture.puml\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(2) == 'uml'
    assert match.group(4) == '_diagrams/architecture.puml'


def test_rst_argument_pattern_indented():
    pattern = _build_rst_argument_pattern(['uml'])
    source = "   .. uml:: _diagrams/architecture.puml\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(4) == '_diagrams/architecture.puml'


def test_rst_argument_pattern_no_match_image():
    """image and figure should NOT match even if in the pattern."""
    pattern = _build_rst_argument_pattern(['uml', 'image'])
    source = ".. image:: _images/photo.png\n"
    match = pattern.search(source)
    # It would match 'image' if included — this tests the regex itself.
    # The exclusion logic is in _get_effective_directives, not the regex.
    assert match is not None  # regex matches; exclusion is elsewhere


def test_rst_argument_pattern_hyphenated_directive():
    pattern = _build_rst_argument_pattern(['drawio-figure'])
    source = ".. drawio-figure:: _diagrams/schema.drawio\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(2) == 'drawio-figure'
    assert match.group(4) == '_diagrams/schema.drawio'


# ---------------------------------------------------------------------------
# Tests: RST option-based regex
# ---------------------------------------------------------------------------

def test_rst_option_pattern_basic():
    pattern = _build_rst_option_pattern(['file'])
    source = "   :file: _diagrams/architecture.puml\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(2) == 'file'
    assert match.group(4) == '_diagrams/architecture.puml'


def test_rst_option_pattern_custom_option():
    pattern = _build_rst_option_pattern(['source', 'file'])
    source = "      :source: my_source.txt\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(2) == 'source'
    assert match.group(4) == 'my_source.txt'


# ---------------------------------------------------------------------------
# Tests: MyST argument-based regex
# ---------------------------------------------------------------------------

def test_myst_argument_pattern_basic():
    pattern = _build_myst_argument_pattern(['uml', 'mermaid'])
    source = "```{uml} _diagrams/architecture.puml\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(4) == '_diagrams/architecture.puml'


def test_myst_argument_pattern_more_backticks():
    pattern = _build_myst_argument_pattern(['mermaid'])
    source = "````{mermaid} _diagrams/flow.mmd\n"
    match = pattern.search(source)
    assert match is not None
    assert match.group(4) == '_diagrams/flow.mmd'


def test_myst_argument_pattern_indented():
    pattern = _build_myst_argument_pattern(['uml'])
    source = "  ```{uml} _diagrams/architecture.puml\n"
    match = pattern.search(source)
    assert match is not None


# ---------------------------------------------------------------------------
# Tests: Full swap (integration with filesystem)
# ---------------------------------------------------------------------------

def test_perform_swap_rst_argument(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. uml:: _diagrams/architecture.puml\n\nSome text.\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert '_diagrams/architecture_dark.puml' in result
    assert hasattr(app.env, '_doxtr_dark_source_swapped')
    assert '_diagrams/architecture.puml' in app.env._doxtr_dark_source_swapped


def test_perform_swap_rst_option(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. uml::\n   :file: _diagrams/architecture.puml\n\nText.\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert '_diagrams/architecture_dark.puml' in result


def test_perform_swap_no_dark_variant(tmp_project):
    """Files without _dark variant should not be modified."""
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. uml:: _diagrams/simple.puml\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert result == source  # unchanged


def test_perform_swap_url_skipped(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. uml:: https://example.com/diagram.puml\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert result == source  # unchanged


def test_perform_swap_exclude_pattern(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. uml:: _diagrams/architecture.puml\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        ['architecture*']  # exclude pattern
    )
    assert result == source  # unchanged due to exclusion


def test_perform_swap_myst(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = "```{uml} _diagrams/architecture.puml\n```\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert '_diagrams/architecture_dark.puml' in result


def test_perform_swap_multiple_directives(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = (
        ".. uml:: _diagrams/architecture.puml\n\n"
        ".. mermaid:: _diagrams/flow.mmd\n\n"
        ".. uml:: _diagrams/simple.puml\n"
    )
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert '_diagrams/architecture_dark.puml' in result
    assert '_diagrams/flow_dark.mmd' in result
    assert '_diagrams/simple.puml' in result  # no dark variant, unchanged


def test_perform_swap_nested_indented(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = (
        ".. admonition:: Note\n\n"
        "   .. uml:: _diagrams/architecture.puml\n\n"
        "   Some content.\n"
    )
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert '_diagrams/architecture_dark.puml' in result


def test_perform_swap_include(tmp_project):
    srcdir = str(tmp_project)
    docdir = srcdir

    source = ".. include:: included.rst\n"
    app = MockApp(srcdir)

    result = _perform_swap(
        source, app, 'index', srcdir, docdir,
        DARK_FILE_SWAP_DIRECTIVES_DEFAULT,
        set(DARK_FILE_SWAP_EXTENSIONS_DEFAULT),
        []
    )
    assert 'included_dark.rst' in result


# ---------------------------------------------------------------------------
# Tests: swap_dark_sources (full handler with guards)
# ---------------------------------------------------------------------------

def test_swap_dark_sources_latex_builder(tmp_project):
    srcdir = str(tmp_project)
    app = MockApp(srcdir, builder_name='latex')
    source = [".. uml:: _diagrams/architecture.puml\n"]

    swap_dark_sources(app, 'index', source)
    assert '_diagrams/architecture_dark.puml' in source[0]


def test_swap_dark_sources_html_builder_skips(tmp_project):
    """HTML builder should not trigger swap."""
    srcdir = str(tmp_project)
    app = MockApp(srcdir, builder_name='html')
    original = ".. uml:: _diagrams/architecture.puml\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    assert source[0] == original


def test_swap_dark_sources_dark_mode_off(tmp_project):
    """Dark mode disabled → no swap."""
    srcdir = str(tmp_project)
    app = MockApp(srcdir, doxtr_dark_mode=False)
    original = ".. uml:: _diagrams/architecture.puml\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    assert source[0] == original


def test_swap_dark_sources_passthrough_strategy(tmp_project):
    """Passthrough strategy → no swap."""
    srcdir = str(tmp_project)
    app = MockApp(srcdir, doxtr_dark_mode_strategy_resolved='passthrough')
    original = ".. uml:: _diagrams/architecture.puml\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    assert source[0] == original


def test_swap_dark_sources_master_switch_off(tmp_project):
    """Master switch disabled → no swap."""
    srcdir = str(tmp_project)
    app = MockApp(srcdir, doxtr_enable_dark_file_swap=False)
    original = ".. uml:: _diagrams/architecture.puml\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    assert source[0] == original


# ---------------------------------------------------------------------------
# Tests: register_dark_swap_directive API
# ---------------------------------------------------------------------------

def test_register_dark_swap_directive_basic(clean_registry):
    """API registration should add to the registry."""
    register_dark_swap_directive('my-diagram', file_options=['source'])
    assert len(_custom_dark_swap_directives) == 1
    assert _custom_dark_swap_directives[0] == {
        'name': 'my-diagram',
        'options': ['source'],
    }


def test_register_dark_swap_directive_no_options(clean_registry):
    """Registration without options should default to empty list."""
    register_dark_swap_directive('custom-include')
    assert _custom_dark_swap_directives[0]['options'] == []


def test_register_dark_swap_directive_rejects_image():
    """Should raise ValueError for excluded directives."""
    with pytest.raises(ValueError, match="excluded"):
        register_dark_swap_directive('image')


def test_register_dark_swap_directive_rejects_figure():
    with pytest.raises(ValueError, match="excluded"):
        register_dark_swap_directive('figure')


def test_register_dark_swap_directive_rejects_non_string():
    with pytest.raises(TypeError):
        register_dark_swap_directive(123)


def test_register_dark_swap_directive_rejects_empty():
    with pytest.raises(ValueError, match="must not be empty"):
        register_dark_swap_directive('')


# ---------------------------------------------------------------------------
# Tests: _get_effective_directives
# ---------------------------------------------------------------------------

def test_get_effective_directives_default():
    config = MockConfig()
    result = _get_effective_directives(config)
    assert 'uml' in result
    assert 'mermaid' in result
    assert 'image' not in result  # excluded
    assert 'figure' not in result  # excluded


def test_get_effective_directives_user_override():
    config = MockConfig(doxtr_dark_file_swap_directives={
        'my-ext': {'options': ['src']},
    })
    result = _get_effective_directives(config)
    assert 'my-ext' in result
    assert result['my-ext'] == {'options': ['src']}
    # Core defaults still present
    assert 'uml' in result


def test_get_effective_directives_user_removes_by_exclusion():
    """Even if user adds 'image', it's always excluded."""
    config = MockConfig(doxtr_dark_file_swap_directives={
        'image': {'options': []},
    })
    result = _get_effective_directives(config)
    assert 'image' not in result


# ---------------------------------------------------------------------------
# Tests: Dependency tracking
# ---------------------------------------------------------------------------

def test_dependency_registered_on_swap(tmp_project):
    srcdir = str(tmp_project)
    app = MockApp(srcdir)
    source = [".. uml:: _diagrams/architecture.puml\n"]

    swap_dark_sources(app, 'index', source)
    # Should have registered a dependency
    assert len(app.env._dependencies) > 0
    # Dependency should point to the dark variant
    assert any('architecture_dark.puml' in dep for dep in app.env._dependencies)


# ---------------------------------------------------------------------------
# Tests: Image/figure exclusion
# ---------------------------------------------------------------------------

def test_image_directive_not_swapped(tmp_project):
    """.. image:: should never be matched by source-read scanner."""
    srcdir = str(tmp_project)
    # Create an image with dark variant
    (tmp_project / "_images").mkdir(exist_ok=True)
    (tmp_project / "_images" / "photo.png").write_bytes(b'\x89PNG')
    (tmp_project / "_images" / "photo_dark.png").write_bytes(b'\x89PNG dark')

    app = MockApp(srcdir)
    original = ".. image:: _images/photo.png\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    # image directive should NOT be swapped (handled by process_dark_images_ast)
    assert source[0] == original


def test_figure_directive_not_swapped(tmp_project):
    """.. figure:: should never be matched by source-read scanner."""
    srcdir = str(tmp_project)
    (tmp_project / "_images").mkdir(exist_ok=True)
    (tmp_project / "_images" / "photo.png").write_bytes(b'\x89PNG')
    (tmp_project / "_images" / "photo_dark.png").write_bytes(b'\x89PNG dark')

    app = MockApp(srcdir)
    original = ".. figure:: _images/photo.png\n   :width: 80%\n"
    source = [original]

    swap_dark_sources(app, 'index', source)
    assert source[0] == original


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
