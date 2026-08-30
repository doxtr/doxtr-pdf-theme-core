"""Unit tests for doxtr_pdf_theme_core.ast_processors

This module tests the AST processor functions that transform docutils
doctree nodes for LaTeX output.

Run with: pytest test_harness/test_ast_processors.py -v
"""
import sys
import os

# Add package to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from docutils import nodes
from docutils.utils import new_document
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser


# ---------------------------------------------------------------------------
# Test helpers / mocks
# ---------------------------------------------------------------------------

def _make_document():
    """Create a minimal docutils document for testing."""
    settings = get_default_settings(Parser)
    return new_document('<test>', settings)


class MockConfig:
    """Mock Sphinx config that returns None for missing attributes."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        # Return None for any attribute not explicitly set
        return None


class MockBuilder:
    """Mock Sphinx builder with latex format."""
    name = 'latex'
    format = 'latex'


class MockApp:
    """Mock Sphinx application."""

    def __init__(self, config=None, builder=None):
        self.config = config or MockConfig()
        self.builder = builder or MockBuilder()


# ---------------------------------------------------------------------------
# Tests: containers.py
# ---------------------------------------------------------------------------

class TestContainersAST:
    """Tests for process_containers_ast."""

    def test_container_with_registered_class_gets_wrapped(self):
        """A container node with a class in doxtr_containers gets LaTeX wrapping."""
        from doxtr_pdf_theme_core.ast_processors.containers import process_containers_ast

        config = MockConfig(
            doxtr_enable_container_processor=True,
            doxtr_containers={
                'mybox': {
                    'title': 'My Box',
                    'title_raw': False,
                    'render_mode': 'tcolorbox',
                },
            },
            doxtr_container_mapping={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        container = nodes.container(classes=['mybox'])
        container += nodes.paragraph(text='Hello world')
        doc += container

        process_containers_ast(app, doc, 'index')

        # The original container should be replaced by a wrapper
        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) >= 2, "Expected begin/end raw LaTeX nodes"
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\begin{ddcontainermybox}' in raw_text
        assert r'\end{ddcontainermybox}' in raw_text

    def test_container_without_registered_class_ignored(self):
        """A container without a matching class in doxtr_containers is left alone."""
        from doxtr_pdf_theme_core.ast_processors.containers import process_containers_ast

        config = MockConfig(
            doxtr_enable_container_processor=True,
            doxtr_containers={'mybox': {'title': '', 'render_mode': 'tcolorbox'}},
            doxtr_container_mapping={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        container = nodes.container(classes=['unregistered'])
        container += nodes.paragraph(text='Untouched')
        doc += container

        process_containers_ast(app, doc, 'index')

        # No raw LaTeX should be injected
        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_container_disabled_flag(self):
        """When doxtr_enable_container_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.containers import process_containers_ast

        config = MockConfig(
            doxtr_enable_container_processor=False,
            doxtr_containers={'mybox': {'title': 'Box', 'render_mode': 'tcolorbox'}},
            doxtr_container_mapping={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        container = nodes.container(classes=['mybox'])
        container += nodes.paragraph(text='Should not be processed')
        doc += container

        process_containers_ast(app, doc, 'index')

        # No raw LaTeX nodes — processor was skipped
        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_container_mapping_resolves(self):
        """A mapped class resolves to the target container style."""
        from doxtr_pdf_theme_core.ast_processors.containers import process_containers_ast

        config = MockConfig(
            doxtr_enable_container_processor=True,
            doxtr_containers={
                'target_style': {
                    'title': 'Mapped',
                    'title_raw': False,
                    'render_mode': 'tcolorbox',
                },
            },
            doxtr_container_mapping={'alias': 'target_style'},
        )
        app = MockApp(config=config)
        doc = _make_document()

        container = nodes.container(classes=['alias'])
        container += nodes.paragraph(text='Mapped content')
        doc += container

        process_containers_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        # Should use the resolved target style name, not the alias
        assert r'\begin{ddcontainertargetstyle}' in raw_text


# ---------------------------------------------------------------------------
# Tests: tables.py
# ---------------------------------------------------------------------------

class TestTablesAST:
    """Tests for process_tables_ast."""

    def _make_table_doc(self):
        """Create a doc with a simple table containing a header row."""
        doc = _make_document()
        table = nodes.table()
        tgroup = nodes.tgroup(cols=2)
        thead = nodes.thead()
        row = nodes.row()
        entry1 = nodes.entry()
        entry1 += nodes.paragraph(text='Col A')
        entry2 = nodes.entry()
        entry2 += nodes.paragraph(text='Col B')
        row += entry1
        row += entry2
        thead += row
        tgroup += thead
        table += tgroup
        doc += table
        return doc

    def test_table_gets_processed_flag(self):
        """Table gets marked as processed after running the AST processor."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        config = MockConfig(
            doxtr_enable_table_processor=True,
            doxtr_table_nobreak_patterns=[],
            doxtr_table_break_chars='',
            doxtr_table_auto_colwidths=False,
        )
        app = MockApp(config=config)
        doc = self._make_table_doc()

        process_tables_ast(app, doc, 'index')

        table = list(doc.findall(nodes.table))[0]
        assert table.get('doxtr_table_overflow_processed') is True

    def test_table_disabled_flag(self):
        """When doxtr_enable_table_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        config = MockConfig(doxtr_enable_table_processor=False)
        app = MockApp(config=config)
        doc = self._make_table_doc()

        process_tables_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_table_not_processed_twice(self):
        """Running the processor twice doesn't double-process the table."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        config = MockConfig(
            doxtr_enable_table_processor=True,
            doxtr_table_nobreak_patterns=[],
            doxtr_table_break_chars='',
            doxtr_table_auto_colwidths=False,
        )
        app = MockApp(config=config)
        doc = self._make_table_doc()

        process_tables_ast(app, doc, 'index')
        process_tables_ast(app, doc, 'index')

        # Guard flag should still be set; processor skips on second pass.
        table = list(doc.findall(nodes.table))[0]
        assert table.get('doxtr_table_overflow_processed') is True


# ---------------------------------------------------------------------------
# Tests: codeblocks.py
# ---------------------------------------------------------------------------

class TestCodeblocksAST:
    """Tests for process_codeblocks_ast."""

    def test_literal_block_gets_language_macro(self):
        """A literal_block node gets \\def\\ddCurrentCodeLang injected before it."""
        from doxtr_pdf_theme_core.ast_processors.codeblocks import process_codeblocks_ast

        config = MockConfig(doxtr_enable_codeblock_processor=True)
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        code = nodes.literal_block(text='print("hello")')
        code['language'] = 'python'
        section += code
        doc += section

        process_codeblocks_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 1
        assert r'\def\ddCurrentCodeLang{python}' in raw_nodes[0].astext()

    def test_codeblock_disabled_flag(self):
        """When doxtr_enable_codeblock_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.codeblocks import process_codeblocks_ast

        config = MockConfig(doxtr_enable_codeblock_processor=False)
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        code = nodes.literal_block(text='x = 1')
        code['language'] = 'python'
        section += code
        doc += section

        process_codeblocks_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_codeblock_special_chars_sanitized(self):
        """Language names with special chars are sanitized for LaTeX safety."""
        from doxtr_pdf_theme_core.ast_processors.codeblocks import process_codeblocks_ast

        config = MockConfig(doxtr_enable_codeblock_processor=True)
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        code = nodes.literal_block(text='#include <stdio.h>')
        code['language'] = 'c++'
        section += code
        doc += section

        process_codeblocks_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 1
        # c++ should become 'c' (non-alphanumeric stripped)
        assert r'\def\ddCurrentCodeLang{c}' in raw_nodes[0].astext()


# ---------------------------------------------------------------------------
# Tests: epigraphs.py
# ---------------------------------------------------------------------------

class TestEpigraphsAST:
    """Tests for process_epigraph_ast."""

    def test_epigraph_block_quote_gets_dictum(self):
        """A block_quote with 'epigraph' class gets wrapped in \\dictum."""
        from doxtr_pdf_theme_core.ast_processors.epigraphs import process_epigraph_ast

        config = MockConfig(
            doxtr_enable_epigraph_processor=True,
            latex_toplevel_sectioning='chapter',
            latex_docclass={'manual': 'scrbook'},
        )
        app = MockApp(config=config)
        doc = _make_document()

        # Put epigraph inside a section (non-preamble position)
        section = nodes.section()
        section += nodes.title(text='Test Section')
        section += nodes.paragraph(text='Intro paragraph')

        bq = nodes.block_quote(classes=['epigraph'])
        bq += nodes.paragraph(text='To be or not to be.')
        section += bq
        doc += section

        process_epigraph_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\dictum{' in raw_text
        assert r'\setupddepigraph{' in raw_text

    def test_epigraph_disabled_flag(self):
        """When doxtr_enable_epigraph_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.epigraphs import process_epigraph_ast

        config = MockConfig(
            doxtr_enable_epigraph_processor=False,
            latex_toplevel_sectioning='chapter',
            latex_docclass={'manual': 'scrbook'},
        )
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        section += nodes.title(text='Test')
        bq = nodes.block_quote(classes=['epigraph'])
        bq += nodes.paragraph(text='Quote text')
        section += bq
        doc += section

        process_epigraph_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_epigraph_with_attribution(self):
        """An epigraph with attribution renders \\dictum[author]{...}."""
        from doxtr_pdf_theme_core.ast_processors.epigraphs import process_epigraph_ast

        config = MockConfig(
            doxtr_enable_epigraph_processor=True,
            latex_toplevel_sectioning='chapter',
            latex_docclass={'manual': 'scrbook'},
        )
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        section += nodes.title(text='Chapter')
        section += nodes.paragraph(text='Some text before')

        bq = nodes.block_quote(classes=['epigraph'])
        bq += nodes.paragraph(text='The unexamined life...')
        attr = nodes.attribution()
        attr += nodes.Text('Socrates')
        bq += attr
        section += bq
        doc += section

        process_epigraph_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\dictum[{' in raw_text


# ---------------------------------------------------------------------------
# Tests: highlights.py
# ---------------------------------------------------------------------------

class TestHighlightsAST:
    """Tests for process_highlights_ast."""

    def test_highlights_block_quote_gets_wrapped(self):
        """A block_quote with 'highlights' class gets ddhighlightsbox wrapping."""
        from doxtr_pdf_theme_core.ast_processors.highlights import process_highlights_ast

        config = MockConfig(
            doxtr_enable_highlights_processor=True,
            doxtr_highlights={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        bq = nodes.block_quote(classes=['highlights'])
        bq += nodes.paragraph(text='Key point 1')
        bq += nodes.paragraph(text='Key point 2')
        doc += bq

        process_highlights_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\begin{ddhighlightsbox}' in raw_text
        assert r'\end{ddhighlightsbox}' in raw_text

    def test_highlights_disabled_flag(self):
        """When doxtr_enable_highlights_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.highlights import process_highlights_ast

        config = MockConfig(
            doxtr_enable_highlights_processor=False,
            doxtr_highlights={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        bq = nodes.block_quote(classes=['highlights'])
        bq += nodes.paragraph(text='Should not be processed')
        doc += bq

        process_highlights_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_highlights_non_highlights_block_quote_ignored(self):
        """A block_quote without 'highlights' class is not processed."""
        from doxtr_pdf_theme_core.ast_processors.highlights import process_highlights_ast

        config = MockConfig(
            doxtr_enable_highlights_processor=True,
            doxtr_highlights={},
        )
        app = MockApp(config=config)
        doc = _make_document()

        bq = nodes.block_quote(classes=['other-class'])
        bq += nodes.paragraph(text='Normal quote')
        doc += bq

        process_highlights_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0


# ---------------------------------------------------------------------------
# Tests: topics.py
# ---------------------------------------------------------------------------

class TestTopicsAST:
    """Tests for process_topics_ast."""

    def test_topic_node_gets_wrapped(self):
        """A topic node gets wrapped in doxtrtopic environment."""
        from doxtr_pdf_theme_core.ast_processors.topics import process_topics_ast

        config = MockConfig(
            doxtr_enable_topics_processor=True,
            doxtr_topic={'enabled': True},
            doxtr_contents={'enabled': True},
        )
        app = MockApp(config=config)
        doc = _make_document()

        topic = nodes.topic()
        topic += nodes.title(text='My Topic')
        topic += nodes.paragraph(text='Topic body content')
        doc += topic

        process_topics_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\begin{doxtrtopic}{My Topic}' in raw_text
        assert r'\end{doxtrtopic}' in raw_text

    def test_contents_node_gets_wrapped(self):
        """A topic node with 'contents' class uses doxtrcontents environment."""
        from doxtr_pdf_theme_core.ast_processors.topics import process_topics_ast

        config = MockConfig(
            doxtr_enable_topics_processor=True,
            doxtr_topic={'enabled': True},
            doxtr_contents={'enabled': True},
        )
        app = MockApp(config=config)
        doc = _make_document()

        topic = nodes.topic(classes=['contents'])
        topic += nodes.title(text='Table of Contents')
        topic += nodes.paragraph(text='Contents go here')
        doc += topic

        process_topics_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\begin{doxtrcontents}{Table of Contents}' in raw_text
        assert r'\end{doxtrcontents}' in raw_text

    def test_topics_disabled_flag(self):
        """When doxtr_enable_topics_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.topics import process_topics_ast

        config = MockConfig(
            doxtr_enable_topics_processor=False,
            doxtr_topic={'enabled': True},
            doxtr_contents={'enabled': True},
        )
        app = MockApp(config=config)
        doc = _make_document()

        topic = nodes.topic()
        topic += nodes.title(text='Ignored Topic')
        topic += nodes.paragraph(text='Body')
        doc += topic

        process_topics_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_topic_per_type_enabled_false(self):
        """When doxtr_topic['enabled']=False, topic nodes are skipped."""
        from doxtr_pdf_theme_core.ast_processors.topics import process_topics_ast

        config = MockConfig(
            doxtr_enable_topics_processor=True,
            doxtr_topic={'enabled': False},
            doxtr_contents={'enabled': True},
        )
        app = MockApp(config=config)
        doc = _make_document()

        topic = nodes.topic()
        topic += nodes.title(text='Disabled Topic')
        topic += nodes.paragraph(text='Body')
        doc += topic

        process_topics_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0


# ---------------------------------------------------------------------------
# Tests: sidebars.py
# ---------------------------------------------------------------------------

class TestSidebarsAST:
    """Tests for process_sidebar_ast."""

    def test_sidebar_gets_wrapped(self):
        """A sidebar node gets wrapped in wrapfigure/tcolorbox LaTeX."""
        from doxtr_pdf_theme_core.ast_processors.sidebars import process_sidebar_ast

        config = MockConfig(doxtr_enable_sidebar_processor=True)
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        sidebar = nodes.sidebar()
        sidebar += nodes.title(text='Sidebar Title')
        sidebar += nodes.paragraph(text='Sidebar body content')
        section += sidebar
        doc += section

        process_sidebar_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) > 0
        raw_text = raw_nodes[0].astext()
        assert r'\begin{wrapfigure}' in raw_text
        assert r'\begin{ddsidebarinnerbox}' in raw_text
        assert 'Sidebar Title' in raw_text

    def test_sidebar_disabled_flag(self):
        """When doxtr_enable_sidebar_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.sidebars import process_sidebar_ast

        config = MockConfig(doxtr_enable_sidebar_processor=False)
        app = MockApp(config=config)
        doc = _make_document()

        section = nodes.section()
        sidebar = nodes.sidebar()
        sidebar += nodes.title(text='Sidebar')
        sidebar += nodes.paragraph(text='Body')
        section += sidebar
        doc += section

        process_sidebar_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0


# ---------------------------------------------------------------------------
# Tests: needs.py
# ---------------------------------------------------------------------------

class TestNeedsAST:
    """Tests for process_needs_ast."""

    def test_needs_disabled_flag(self):
        """When doxtr_enable_needs_processor=False, no processing happens."""
        from doxtr_pdf_theme_core.ast_processors.needs import process_needs_ast

        config = MockConfig(doxtr_enable_needs_processor=False)
        app = MockApp(config=config)
        doc = _make_document()

        # Create a node that looks like a need
        container = nodes.container(classes=['need'])
        container['ids'] = ['REQ-001']
        container += nodes.paragraph(text='Requirement text')
        doc += container

        process_needs_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_needs_node_with_id_gets_wrapped(self):
        """A node with 'need' class and an ID gets doxtrneedboxrouter wrapping."""
        from doxtr_pdf_theme_core.ast_processors.needs import process_needs_ast

        config = MockConfig(doxtr_enable_needs_processor=True)
        app = MockApp(config=config)
        # Add minimal env with needs_all_needs
        app.env = type('MockEnv', (), {
            'needs_all_needs': {
                'REQ-001': {'title': 'First Requirement', 'type': 'req'}
            }
        })()
        doc = _make_document()

        # Create a container that simulates a sphinx-needs node
        container = nodes.container(classes=['need'])
        container['ids'] = ['REQ-001']
        # Add a table with metadata (typical needs structure)
        table = nodes.table()
        tgroup = nodes.tgroup(cols=2)
        # Header row
        thead = nodes.thead()
        hrow = nodes.row()
        he1 = nodes.entry()
        he1 += nodes.paragraph(text='Key')
        he2 = nodes.entry()
        he2 += nodes.paragraph(text='Value')
        hrow += he1
        hrow += he2
        thead += hrow
        tgroup += thead
        # Content row
        tbody = nodes.tbody()
        crow = nodes.row()
        ce1 = nodes.entry()
        ce1 += nodes.paragraph(text='Description')
        crow += ce1
        tbody += crow
        tgroup += tbody
        table += tgroup
        container += table
        doc += container

        process_needs_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        raw_text = ''.join(r.astext() for r in raw_nodes)
        assert r'\begin{doxtrneedboxrouter}' in raw_text
        assert r'\end{doxtrneedboxrouter}' in raw_text
        assert 'REQ-001' in raw_text


# ---------------------------------------------------------------------------
# Tests: non-latex builder skip
# ---------------------------------------------------------------------------

class TestNonLatexBuilderSkip:
    """All processors should skip when builder format is not 'latex'."""

    def test_containers_skips_html_builder(self):
        """Container processor skips when builder format is html."""
        from doxtr_pdf_theme_core.ast_processors.containers import process_containers_ast

        class HtmlBuilder:
            name = 'html'
            format = 'html'

        config = MockConfig(
            doxtr_enable_container_processor=True,
            doxtr_containers={'mybox': {'title': 'Box', 'render_mode': 'tcolorbox'}},
            doxtr_container_mapping={},
        )
        app = MockApp(config=config, builder=HtmlBuilder())
        doc = _make_document()

        container = nodes.container(classes=['mybox'])
        container += nodes.paragraph(text='Not for HTML')
        doc += container

        process_containers_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0

    def test_tables_skips_html_builder(self):
        """Table processor skips when builder format is html."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        class HtmlBuilder:
            name = 'html'
            format = 'html'

        config = MockConfig(doxtr_enable_table_processor=True)
        app = MockApp(config=config, builder=HtmlBuilder())
        doc = _make_document()

        table = nodes.table()
        tgroup = nodes.tgroup(cols=1)
        thead = nodes.thead()
        row = nodes.row()
        entry = nodes.entry()
        entry += nodes.paragraph(text='Header')
        row += entry
        thead += row
        tgroup += thead
        table += tgroup
        doc += table

        process_tables_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) == 0


# ---------------------------------------------------------------------------
# Tests: tables.py — Phase 2 column width helpers (patch: table-column-width-fix)
# ---------------------------------------------------------------------------

class TestIsPredominantlyUppercase:
    """Tests for _is_predominantly_uppercase helper."""

    def test_all_uppercase(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        assert _is_predominantly_uppercase('SAST') is True

    def test_all_lowercase(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        assert _is_predominantly_uppercase('hello') is False

    def test_mixed_majority_upper(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        # 2/3 upper => True
        assert _is_predominantly_uppercase('ABc') is True

    def test_mixed_majority_lower(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        # 1/3 upper => False
        assert _is_predominantly_uppercase('abC') is False

    def test_exactly_half(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        # 50% is NOT >50%, so False
        assert _is_predominantly_uppercase('Ab') is False

    def test_no_alpha_chars(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        assert _is_predominantly_uppercase('123-!@') is False

    def test_empty_string(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        assert _is_predominantly_uppercase('') is False

    def test_digits_ignored_for_ratio(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _is_predominantly_uppercase
        # 'A1B2' => alpha chars are A, B => both upper => True
        assert _is_predominantly_uppercase('A1B2') is True


class TestEffectiveWordWidthChars:
    """Tests for _effective_word_width_chars helper."""

    def test_lowercase_word_returns_length(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _effective_word_width_chars
        assert _effective_word_width_chars('hello') == 5.0

    def test_uppercase_word_returns_scaled_length(self):
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _effective_word_width_chars, DEFAULT_UPPERCASE_WIDTH_FACTOR,
        )
        result = _effective_word_width_chars('SAST')
        assert result == len('SAST') * DEFAULT_UPPERCASE_WIDTH_FACTOR

    def test_custom_uppercase_factor(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _effective_word_width_chars
        result = _effective_word_width_chars('SAST', uppercase_factor=1.5)
        assert result == 4 * 1.5

    def test_empty_word_returns_zero(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _effective_word_width_chars
        assert _effective_word_width_chars('') == 0.0

    def test_mixed_case_not_scaled(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _effective_word_width_chars
        # 'Hello' => 1/5 upper => not predominantly uppercase
        assert _effective_word_width_chars('Hello') == 5.0


class TestGetLongestUnbreakableWordUpdated:
    """Tests for _get_longest_unbreakable_word with the updated Phase 2 logic.

    Key behavior changes:
    - Short tokens (<= MIN_TOKEN_LENGTH_FOR_BREAKS) are NOT split on break_chars.
    - Long tokens (> MIN_TOKEN_LENGTH_FOR_BREAKS) ARE split on break_chars.
    - Uppercase words get the uppercase width factor applied.
    """

    def test_short_token_not_split_on_break_chars(self):
        """Tokens <= 15 chars should NOT be split at break_chars."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _get_longest_unbreakable_word, MIN_TOKEN_LENGTH_FOR_BREAKS,
        )
        # 'ADR-0001' is 8 chars (< 15), break_chars includes '-'
        # Should return the full token width, NOT split at '-'
        result = _get_longest_unbreakable_word('ADR-0001', None, '-')
        assert result == 10  # 'ADR-0001': uppercase (A,D,R all upper) => 8 * 1.2 = 9.6 => 10

    def test_long_token_split_on_break_chars(self):
        """Tokens > 15 chars should be split at break_chars."""
        from doxtr_pdf_theme_core.ast_processors.tables import _get_longest_unbreakable_word
        # 'abcdefghij-klmnopqrst' is 21 chars, break_chars includes '-'
        # Should split into 'abcdefghij' (10) and 'klmnopqrst' (10)
        result = _get_longest_unbreakable_word('abcdefghij-klmnopqrst', None, '-')
        assert result == 10  # Longest segment after splitting at '-'

    def test_empty_text_returns_zero(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _get_longest_unbreakable_word
        assert _get_longest_unbreakable_word('', None, '-') == 0

    def test_uppercase_word_gets_factor(self):
        """Uppercase words in nobreak segments get the uppercase width factor."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _get_longest_unbreakable_word, DEFAULT_UPPERCASE_WIDTH_FACTOR,
        )
        # 'SAST' is 4 chars, short token, uppercase => 4 * 1.2 = 4.8 => round to 5
        result = _get_longest_unbreakable_word('SAST', None, '-')
        expected = int(round(len('SAST') * DEFAULT_UPPERCASE_WIDTH_FACTOR))
        assert result == expected

    def test_whitespace_splits_tokens(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _get_longest_unbreakable_word
        # 'hello world' => two short tokens of 5 each
        result = _get_longest_unbreakable_word('hello world', None, '-')
        assert result == 5


class TestGetEntryMinWidth:
    """Tests for _get_entry_min_width — structure-aware entry measurement."""

    def test_plain_text_entry(self):
        """Plain text entry should match _get_longest_unbreakable_word."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _get_entry_min_width, _get_longest_unbreakable_word,
        )
        doc = _make_document()
        entry = nodes.entry()
        para = nodes.paragraph(text='hello world')
        entry += para
        doc += entry

        result = _get_entry_min_width(entry, None, '-')
        expected = _get_longest_unbreakable_word('hello world', None, '-')
        assert result == expected

    def test_reference_text_not_split_on_break_chars(self):
        """Text inside a reference node should not be split on break_chars."""
        from doxtr_pdf_theme_core.ast_processors.tables import _get_entry_min_width
        doc = _make_document()
        entry = nodes.entry()
        para = nodes.paragraph()
        # Simulate a hyperlink with hyphenated ID: 'ADR-0001'
        ref = nodes.reference('', 'ADR-0001', refuri='#adr-0001')
        para += ref
        entry += para
        doc += entry

        # break_chars='-', but inside a reference, '-' should NOT break
        result = _get_entry_min_width(entry, None, '-')
        assert result == 10  # 'ADR-0001': uppercase => 8 * 1.2 = 9.6 => 10

    def test_reference_with_long_hyphenated_id(self):
        """Long hyphenated IDs in references stay unbroken per word."""
        from doxtr_pdf_theme_core.ast_processors.tables import _get_entry_min_width
        doc = _make_document()
        entry = nodes.entry()
        para = nodes.paragraph()
        ref = nodes.reference('', 'ORCA-CRE-241', refuri='#orca-cre-241')
        para += ref
        entry += para
        doc += entry

        # 'ORCA-CRE-241' inside ref — words split on whitespace only, not '-'
        # Whole string is one "word" (no spaces) => full width with uppercase scaling
        result = _get_entry_min_width(entry, None, '-')
        assert result == 14  # 'ORCA-CRE-241': uppercase => 12 * 1.2 = 14.4 => 14

    def test_mixed_reference_and_text(self):
        """Entry with both reference and plain text picks the longest."""
        from doxtr_pdf_theme_core.ast_processors.tables import _get_entry_min_width
        doc = _make_document()
        entry = nodes.entry()
        para = nodes.paragraph()
        ref = nodes.reference('', 'ID-001', refuri='#id-001')
        para += ref
        para += nodes.Text(' some short text')
        entry += para
        doc += entry

        result = _get_entry_min_width(entry, None, '-')
        # 'ID-001' as reference (6 chars, not split at '-') vs 'some' (4), 'short' (5), 'text' (4)
        assert result == 7  # 'ID-001': uppercase (I,D both upper) => 6 * 1.2 = 7.2 => 7


class TestColumnInfoNewFields:
    """Tests for ColumnInfo dataclass new fields."""

    def test_new_fields_have_defaults(self):
        from doxtr_pdf_theme_core.ast_processors.tables import ColumnInfo
        ci = ColumnInfo()
        assert ci.min_width_chars == 0
        assert ci.raw_body_min_chars == 0
        assert ci.raw_header_min_chars == 0
        assert ci.avg_content_chars == 0.0
        assert ci.header_text == ''

    def test_new_fields_can_be_set(self):
        from doxtr_pdf_theme_core.ast_processors.tables import ColumnInfo
        ci = ColumnInfo(
            min_width_chars=10,
            raw_body_min_chars=8,
            raw_header_min_chars=6,
            avg_content_chars=15.5,
            header_text='ID',
        )
        assert ci.raw_body_min_chars == 8
        assert ci.raw_header_min_chars == 6


class TestNewConstants:
    """Tests that new constants exist and have expected values."""

    def test_a4_portrait_textwidth(self):
        from doxtr_pdf_theme_core.ast_processors.tables import A4_PORTRAIT_TEXTWIDTH_MM
        assert A4_PORTRAIT_TEXTWIDTH_MM == 160.0

    def test_header_char_width_factor(self):
        from doxtr_pdf_theme_core.ast_processors.tables import DEFAULT_HEADER_CHAR_WIDTH_FACTOR
        assert DEFAULT_HEADER_CHAR_WIDTH_FACTOR == 1.35

    def test_uppercase_width_factor(self):
        from doxtr_pdf_theme_core.ast_processors.tables import DEFAULT_UPPERCASE_WIDTH_FACTOR
        assert DEFAULT_UPPERCASE_WIDTH_FACTOR == 1.2

    def test_tabcolsep_overhead(self):
        from doxtr_pdf_theme_core.ast_processors.tables import TABCOLSEP_OVERHEAD_MM
        assert TABCOLSEP_OVERHEAD_MM == 4.37

    def test_min_width_padding_chars(self):
        from doxtr_pdf_theme_core.ast_processors.tables import MIN_WIDTH_PADDING_CHARS
        assert MIN_WIDTH_PADDING_CHARS == 1

    def test_landscape_textwidths_list(self):
        from doxtr_pdf_theme_core.ast_processors.tables import _LANDSCAPE_TEXTWIDTHS_MM
        assert isinstance(_LANDSCAPE_TEXTWIDTHS_MM, list)
        assert len(_LANDSCAPE_TEXTWIDTHS_MM) == 7
        # Must be sorted ascending
        assert _LANDSCAPE_TEXTWIDTHS_MM == sorted(_LANDSCAPE_TEXTWIDTHS_MM)
        # First entry is A4 landscape
        assert _LANDSCAPE_TEXTWIDTHS_MM[0] == 267.0


class TestComputeColumnMetricsUpdated:
    """Tests for _compute_column_metrics with header font scaling."""

    def _make_table_with_header(self, headers, body_rows):
        """Build a docutils table node with a header row and body rows.

        Args:
            headers: List of header text strings.
            body_rows: List of lists of cell text strings.
        Returns:
            (document, table_node)
        """
        doc = _make_document()
        table = nodes.table()
        tgroup = nodes.tgroup(cols=len(headers))
        for _ in headers:
            tgroup += nodes.colspec(colwidth=1)
        # Header
        thead = nodes.thead()
        header_row = nodes.row()
        for h in headers:
            entry = nodes.entry()
            entry += nodes.paragraph(text=h)
            header_row += entry
        thead += header_row
        tgroup += thead
        # Body
        tbody = nodes.tbody()
        for row_texts in body_rows:
            row = nodes.row()
            for cell_text in row_texts:
                entry = nodes.entry()
                entry += nodes.paragraph(text=cell_text)
                row += entry
            tbody += row
        tgroup += tbody
        table += tgroup
        doc += table
        return doc, table

    def test_raw_header_and_body_min_populated(self):
        """raw_header_min_chars and raw_body_min_chars should be populated."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_column_metrics
        _, table = self._make_table_with_header(
            ['ID', 'Description'],
            [['12345', 'Short text'], ['67890', 'Another entry']],
        )
        columns = _compute_column_metrics(table, None, '-')
        assert len(columns) == 2
        # raw_header_min_chars for col 0 should be based on 'ID'
        assert columns[0].raw_header_min_chars == 2
        # raw_body_min_chars for col 0 should be based on '12345' or '67890'
        assert columns[0].raw_body_min_chars == 5

    def test_min_width_includes_padding_and_overhead(self):
        """min_width_chars should exceed raw values due to padding and overhead."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _compute_column_metrics, TABCOLSEP_OVERHEAD_MM,
            FALLBACK_CHAR_WIDTH_MM, MIN_WIDTH_PADDING_CHARS,
        )
        _, table = self._make_table_with_header(
            ['Name'],
            [['Alice'], ['Bob']],
        )
        columns = _compute_column_metrics(table, None, '-')
        assert len(columns) == 1
        tabcolsep_chars = int(round(TABCOLSEP_OVERHEAD_MM / FALLBACK_CHAR_WIDTH_MM))
        raw_max = max(columns[0].raw_body_min_chars, columns[0].raw_header_min_chars)
        # min_width must be at least raw + overhead + padding
        assert columns[0].min_width_chars >= raw_max + tabcolsep_chars + MIN_WIDTH_PADDING_CHARS

    def test_header_scaling_applied(self):
        """Header min width should be scaled by header_char_width_factor."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_column_metrics
        _, table = self._make_table_with_header(
            ['Description'],  # 11 chars
            [['tiny']],        # 4 chars
        )
        # With default factor 1.35, header 'Description' (11) => 11*1.35=14.85 => 15
        # Body 'tiny' (4) << header, so header should dominate
        columns = _compute_column_metrics(table, None, '-')
        assert columns[0].raw_header_min_chars >= 11
        # The effective min should reflect the scaled header, not the body
        assert columns[0].min_width_chars > columns[0].raw_body_min_chars


class TestColwidthsAutoPromotion:
    """Tests for colwidths-auto → colwidths-given promotion in Phase 2."""

    def _make_auto_table(self, num_cols=3, table_class='colwidths-auto'):
        """Build a table with the given class for Phase 2 testing."""
        doc = _make_document()
        table = nodes.table()
        if table_class:
            table['classes'] = [table_class]
        tgroup = nodes.tgroup(cols=num_cols)
        for _ in range(num_cols):
            tgroup += nodes.colspec(colwidth=1)
        thead = nodes.thead()
        header_row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'Header{i}')
            header_row += entry
        thead += header_row
        tgroup += thead
        tbody = nodes.tbody()
        body_row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'Cell content {i}')
            body_row += entry
        tbody += body_row
        tgroup += tbody
        table += tgroup
        section = nodes.section()
        section += table
        doc += section
        return doc, table

    def test_colwidths_auto_promoted_to_given(self):
        """Tables with colwidths-auto should be promoted to colwidths-given."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_auto_table(num_cols=3, table_class='colwidths-auto')
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        classes = table.get('classes', [])
        assert 'colwidths-given' in classes
        assert 'colwidths-auto' not in classes

    def test_colwidths_given_stays_given(self):
        """Tables with colwidths-given should remain colwidths-given."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_auto_table(num_cols=3, table_class='colwidths-given')
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        classes = table.get('classes', [])
        assert 'colwidths-given' in classes
        # Should only appear once
        assert classes.count('colwidths-given') == 1

    def test_no_class_table_promoted_to_given(self):
        """Tables with no colwidths class should be promoted to colwidths-given."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_auto_table(num_cols=3, table_class=None)
        table['classes'] = []  # No colwidths class at all
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        classes = table.get('classes', [])
        assert 'colwidths-given' in classes

    def test_auto_colwidths_disabled_skips_processing(self):
        """When auto_colwidths=False, no processing should happen."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_auto_table(num_cols=3, table_class='colwidths-auto')
        config = MockConfig(
            doxtr_table_auto_colwidths=False,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        # Should NOT be promoted since processing was disabled
        classes = table.get('classes', [])
        assert 'colwidths-auto' in classes
        assert 'colwidths-given' not in classes

    def test_min_table_width_stored(self):
        """Phase 2 should store doxtr_min_table_width_mm on the table node."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_auto_table(num_cols=3)
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        assert 'doxtr_min_table_width_mm' in table.attributes
        assert table['doxtr_min_table_width_mm'] > 0


class TestPortraitVsLandscapeTextwidth:
    """Tests for portrait vs landscape textwidth selection based on column count."""

    def _make_wide_table(self, num_cols):
        doc = _make_document()
        table = nodes.table()
        table['classes'] = ['colwidths-auto']
        tgroup = nodes.tgroup(cols=num_cols)
        for _ in range(num_cols):
            tgroup += nodes.colspec(colwidth=1)
        thead = nodes.thead()
        header_row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'H{i}')
            header_row += entry
        thead += header_row
        tgroup += thead
        tbody = nodes.tbody()
        row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'data{i}')
            row += entry
        tbody += row
        tgroup += tbody
        table += tgroup
        section = nodes.section()
        section += table
        doc += section
        return doc, table

    def test_few_columns_uses_portrait_width(self):
        """Tables below landscape threshold should use portrait textwidth."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _compute_and_apply_widths, A4_PORTRAIT_TEXTWIDTH_MM,
        )
        _, table = self._make_wide_table(num_cols=3)
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        # With 3 cols and min_columns=4, should use portrait width
        min_mm = table.get('doxtr_min_table_width_mm', 0)
        assert min_mm > 0
        assert min_mm < A4_PORTRAIT_TEXTWIDTH_MM * 2  # sanity check

    def test_many_columns_uses_landscape_width(self):
        """Tables at or above landscape threshold should use landscape textwidth."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_wide_table(num_cols=8)
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        # Should still succeed and store min width
        min_mm = table.get('doxtr_min_table_width_mm', 0)
        assert min_mm > 0


class TestDefaultMinColWidthConstant:
    """Test that the shared DEFAULT_MIN_COL_WIDTH_MM constant exists."""

    def test_constant_value(self):
        from doxtr_pdf_theme_core.ast_processors.tables import DEFAULT_MIN_COL_WIDTH_MM
        assert DEFAULT_MIN_COL_WIDTH_MM == 22.0

    def test_importable_from_package(self):
        from doxtr_pdf_theme_core.ast_processors import DEFAULT_MIN_COL_WIDTH_MM
        assert DEFAULT_MIN_COL_WIDTH_MM == 22.0


class TestAutoLandscapeRespected:
    """Test that Phase 2 respects doxtr_table_auto_landscape and no-landscape class."""

    def _make_wide_table(self, num_cols, extra_classes=None):
        doc = _make_document()
        table = nodes.table()
        classes = ['colwidths-auto']
        if extra_classes:
            classes.extend(extra_classes)
        table['classes'] = classes
        tgroup = nodes.tgroup(cols=num_cols)
        for _ in range(num_cols):
            tgroup += nodes.colspec(colwidth=1)
        thead = nodes.thead()
        header_row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'Header{i}')
            header_row += entry
        thead += header_row
        tgroup += thead
        tbody = nodes.tbody()
        row = nodes.row()
        for i in range(num_cols):
            entry = nodes.entry()
            entry += nodes.paragraph(text=f'Cell {i}')
            row += entry
        tbody += row
        tgroup += tbody
        table += tgroup
        section = nodes.section()
        section += table
        doc += section
        return doc, table

    def test_auto_landscape_false_uses_portrait(self):
        """When auto_landscape=False, wide tables should use portrait textwidth."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _compute_and_apply_widths, A4_PORTRAIT_TEXTWIDTH_MM,
        )
        _, table = self._make_wide_table(num_cols=8)
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
            doxtr_table_auto_landscape=False,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        min_mm = table.get('doxtr_min_table_width_mm', 0)
        assert min_mm > 0

    def test_no_landscape_class_uses_portrait(self):
        """Tables with no-landscape class should use portrait textwidth."""
        from doxtr_pdf_theme_core.ast_processors.tables import (
            _compute_and_apply_widths, A4_PORTRAIT_TEXTWIDTH_MM,
        )
        _, table = self._make_wide_table(num_cols=8, extra_classes=['no-landscape'])
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=2.43,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
            doxtr_table_auto_landscape=True,
        )
        app = MockApp(config=config)
        _compute_and_apply_widths(table, None, '-', app)
        min_mm = table.get('doxtr_min_table_width_mm', 0)
        assert min_mm > 0


class TestCharWidthZeroGuard:
    """Test that char_width_mm=0 doesn't cause division by zero."""

    def _make_simple_table(self):
        doc = _make_document()
        table = nodes.table()
        table['classes'] = ['colwidths-auto']
        tgroup = nodes.tgroup(cols=2)
        for _ in range(2):
            tgroup += nodes.colspec(colwidth=1)
        thead = nodes.thead()
        row = nodes.row()
        for t in ['A', 'B']:
            entry = nodes.entry()
            entry += nodes.paragraph(text=t)
            row += entry
        thead += row
        tgroup += thead
        tbody = nodes.tbody()
        row = nodes.row()
        for t in ['x', 'y']:
            entry = nodes.entry()
            entry += nodes.paragraph(text=t)
            row += entry
        tbody += row
        tgroup += tbody
        table += tgroup
        section = nodes.section()
        section += table
        doc += section
        return doc, table

    def test_zero_char_width_falls_back(self):
        """char_width_mm=0 should fall back to FALLBACK_CHAR_WIDTH_MM."""
        from doxtr_pdf_theme_core.ast_processors.tables import _compute_and_apply_widths
        _, table = self._make_simple_table()
        config = MockConfig(
            doxtr_table_auto_colwidths=True,
            doxtr_table_column_width_algorithm='minfloor',
            doxtr_table_char_width_mm=0,
            doxtr_table_header_char_width_factor=1.35,
            doxtr_landscape_min_columns=4,
        )
        app = MockApp(config=config)
        # Should not raise ZeroDivisionError
        _compute_and_apply_widths(table, None, '-', app)
        assert table.get('doxtr_min_table_width_mm', 0) > 0
