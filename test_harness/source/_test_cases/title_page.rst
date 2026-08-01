.. _test_title_page:

Title Page Test
===============

This document tests all title page features: page color, background images,
title/subtitle/author/date/release styling, show_release toggle, and more.

Note
----

The title page is generated automatically from conf.py settings.
This section exists to ensure the document has content for the build.

Document Content
----------------

This is sample content to verify the title page renders correctly.

.. code-block:: python

   def test_title_page():
       """Test that the title page renders correctly."""
       return True

.. note::
   This note tests that admonitions work alongside title page testing.

.. warning::
   This warning tests warning admonition rendering.

.. tip::
   This tip tests tip admonition rendering.

Tables for Testing
------------------

+--------+----------+
| Col 1  | Col 2    |
+========+==========+
| A      | Some     |
+--------+----------+
| B      | Content  |
+--------+----------+

Figures for Testing
-------------------

.. figure:: ../_static/doxtr_icon_small.png

   Test figure caption for title page verification.
