.. _test_global_settings:

Global Settings Test
====================

This document tests all global settings: show_list_of_*,
appendix_chapter_numbering, geometry settings, footer logo,
and font settings.

Note
----

The global settings are applied at the document level. This section
provides content to verify the settings are active.

List of Figures Test
--------------------

This section tests the doxtr_show_list_of_figures setting. When enabled,
a List of Figures should appear in the document before the index.

.. figure:: ../_static/doxtr_icon_small.png

   Test figure for List of Figures.

.. figure:: ../_static/doxtr_icon_small.png

   Second test figure for List of Figures.

List of Tables Test
-------------------

This section tests the doxtr_show_list_of_tables setting. When enabled,
a List of Tables should appear in the document before the index.

+--------+----------+
| Col 1  | Col 2    |
+========+==========+
| A      | B        |
+--------+----------+
| C      | D        |
+--------+----------+

List of Listings Test
---------------------

This section tests the doxtr_show_list_of_listings setting. When enabled,
a List of Code Blocks (Listings) should appear in the document.

.. code-block:: python

   def test_listings():
       """Test code listings."""
       return True

Appendix Test
-------------

.. raw:: latex

   \part{Appendix Test}

This part tests the appendix_chapter_numbering setting. When enabled,
chapters in this appendix should use letter-numbered format (A.1, A.2, etc.).

Chapter in Appendix
^^^^^^^^^^^^^^^^^^^

.. raw:: latex

   \chapter{Appendix Chapter Test}

This chapter should be numbered as A.1 if appendix_chapter_numbering is
enabled and this part is the first appendix part.

Geometry Test
-------------

This section tests the headsep, footskip, headheight, and footheight
settings. The header and footer spacing should reflect the configured
values.

Footer Logo Test
----------------

This section tests the footer_logo and footer_logo_height settings.
The footer should display the configured logo at the specified height.

Font Settings Test
------------------

This section tests the main_font, sans_font, and mono_font settings.
The document should use the configured font families throughout.

.. code-block:: python

   # This monospace text tests the mono_font setting
   def test_fonts():
       """Test font settings."""
       return True
