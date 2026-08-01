.. _test_parts:

Parts Test
==========

This document tests all part features: global styling, number splitting,
background colors/images, appendix switch, and epigraph colors.

Part with Global Styling
------------------------

.. raw:: latex

   \part{Global Part Styling Test}

This part tests the global part font, color, and size settings from the
conf.py override.

Part with Number Splitting
--------------------------

.. raw:: latex

   \part{Split Number Part Test}

This part tests the number_part_font and number_number_font settings
that split "Part 1" into separate styled components.

Part with Background Color
--------------------------

.. raw:: latex

   \part{Background Color Part Test}

This part tests the background_color setting with 8-digit hex opacity.
The part page should have a dark overlay with the configured opacity.

Part with Background Image
--------------------------

.. raw:: latex

   \part{Background Image Part Test}

This part tests the image setting for a full-page background image.
The image should cover the entire part page.

Part with Appendix Switch
-------------------------

.. raw:: latex

   \part{Appendix Part Test}

This part tests the appendix switch. Chapters after this part should
use letter-based numbering (A.1, A.2, etc.) instead of numeric.

Part with Epigraph Color
------------------------

.. raw:: latex

   \part{Epigraph Color Part Test}

This part tests the epigraph_color setting for custom epigraph text
color on this specific part page.

Part Number Styling
-------------------

.. raw:: latex

   \part{Number Part Color Test}

This part tests the number_part_color and number_number_color settings
for the "Part" word and the number separately.

Part Epigraph
-------------

A test epigraph to verify epigraph rendering on part pages.

::

   This is a test epigraph for the part page.
   It should use the configured color settings.

   -- Doc Dash
