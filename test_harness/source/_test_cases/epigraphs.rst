.. _test_epigraphs:

Epigraphs Test
==============

This document tests all epigraph features: width, alignment, fonts, colors,
author styling, format, and level-specific overrides.

Default Epigraph
----------------

::

   This is a default epigraph. It tests the base epigraph configuration
   from core_config.py with default width, alignment, and styling.

   -- Doc Dash

Custom Width Epigraph
---------------------

::

   This epigraph has a custom width setting. It should be narrower
   than the default width and aligned according to the configured
   align_box and align_text settings.

   -- Doc Dash

Center Aligned Epigraph
-----------------------

::

   This epigraph tests the center alignment settings. Both the box
   and the text inside should be centered on the page.

   -- Doc Dash

Left Aligned Epigraph
---------------------

::

   This epigraph tests the left alignment settings. The box and text
   should be aligned to the left margin.

   -- Doc Dash

Right Aligned Epigraph
----------------------

::

   This epigraph tests the right alignment settings. The box and text
   should be aligned to the right margin.

   -- Doc Dash

Custom Color Epigraph
---------------------

::

   This epigraph tests the custom color settings. The text should
   render in the configured yellow color from the conf.py override.

   -- Doc Dash

Custom Author Epigraph
----------------------

::

   This epigraph tests the custom author font and color settings.
   The author name should use the configured styling.

   -- Doc Dash

Custom Format Epigraph
----------------------

::

   This epigraph tests the custom format string for the author.
   The format should use the tilde prefix from the conf.py override.

   -- Doc Dash

Part-Level Epigraph Override
----------------------------

::

   This epigraph appears on a part page and tests the part-level
   epigraph width override from the conf.py override.

   -- Doc Dash

Chapter-Level Epigraph Override
-------------------------------

::

   This epigraph appears on a chapter page and tests the chapter-level
   epigraph color override from the conf.py override.

   -- Doc Dash
