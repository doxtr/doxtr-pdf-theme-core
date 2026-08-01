.. _test_needs:

Sphinx Needs Test
=================

This document tests all sphinx-needs features: generic needs,
custom need types, metadata, segmentation, title icons,
and content styling.

Generic Need (DR)
-----------------

.. dr:: DR-001

   Title: Generic Decision Record
   :xlink: https://example.com
   :documentation: See the documentation
   :python-docs: Python 3.12 docs

   This is a generic decision record (DR). It tests the default
   need box rendering with the generic configuration from core_config.py.

   The metadata fields above should be rendered with the configured
   fonts and colors.

ADR Need
--------

.. adr:: ADR-001

   Title: Architecture Decision Record
   :status: proposed
   :date: 2026-01-01
   :decision-makers: Team Lead

   This is an Architecture Decision Record (ADR). It tests the
   custom need type styling from the conf.py override.

   The ADR should use the architectural blueprint theme colors
   defined in the test_needs.py override.

Need with Rich Metadata
-----------------------

.. dr:: DR-002

   Title: Need with Rich Metadata
   :priority: high
   :risk: medium
   :effort: large
   :category: architecture
   :tags: test, needs, validation

   This need has multiple metadata fields to test the metadata
   rendering, key colors, and font settings.

Need with Content Below Segmentation
------------------------------------

.. dr:: DR-003

   Title: Need with Content Below Segmentation
   :status: accepted

   This is the content section that appears below the segmentation
   line. It tests the content_background_color, content_font, and
   content_font_color settings.

   The content should be styled according to the generic need
   configuration in the conf.py override.

Need with Specific Type Override
---------------------------------

.. adr:: ADR-002

   Title: ADR with Specific Override
   :status: accepted
   :decision-makers: Architecture Board

   This ADR tests the specific 'adr' type override from
   test_needs.py. It should use the architectural blueprint
   theme with different colors than the generic need type.
