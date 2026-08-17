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

    def test_table_header_gets_rowcolor(self):
        """Table header rows get \\rowcolor markup injected."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        config = MockConfig(doxtr_enable_table_processor=True)
        app = MockApp(config=config)
        doc = self._make_table_doc()

        process_tables_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        assert len(raw_nodes) > 0
        raw_text = raw_nodes[0].astext()
        assert r'\rowcolor{ddtableheaderbg}' in raw_text

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
        """Running the processor twice doesn't double-inject rowcolor."""
        from doxtr_pdf_theme_core.ast_processors.tables import process_tables_ast

        config = MockConfig(doxtr_enable_table_processor=True)
        app = MockApp(config=config)
        doc = self._make_table_doc()

        process_tables_ast(app, doc, 'index')
        process_tables_ast(app, doc, 'index')

        raw_nodes = list(doc.traverse(nodes.raw))
        # Should only have one rowcolor per header row
        assert len(raw_nodes) == 1


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
