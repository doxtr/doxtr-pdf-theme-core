.. _test_headings:

Headings Test
=============

This document tests all heading features: alignment, margin, colors,
fonts, sizes, decorative lines, and inheritance.

.. note::
   This section tests heading configuration from conf.py overrides.

Chapter Level
-------------

This is a test chapter to verify chapter-level heading
configuration.

.. raw:: latex

   \chapter{Test Chapter — Number in Margin with
   Decorative Line}

This content appears after the chapter title. The chapter
number should be rendered in the margin with a decorative
colored line, using the color and font specified in the
test_headings.py conf override.

Section Level
-------------

This is a test section to verify section-level heading
configuration.

.. raw:: latex

   \section{Test Section — Decorative Line and
   Alternate Alignment}

This content tests section-level features including
decorative lines, custom fonts, and colors. The section
should use the "Uncial Antiqua" font with the configured
colors from the conf.py override.

Subsection Level
----------------

This is a test subsection to verify subsection-level
heading configuration.

.. raw:: latex

   \subsection{Test Subsection — Custom Margin
   Space}

This content tests subsection-level features including
custom margin space and line height settings.

Subsubsection Level
-------------------

This is a test subsubsection to verify the deepest heading level.

.. raw:: latex

   \subsubsection{Test Subsubsection — Line Height}

This content tests subsubsection-level features
including line height and margin spacing.

Heading Alignment Tests
-----------------------

Left Aligned Heading
^^^^^^^^^^^^^^^^^^^^

This section tests left-aligned heading output.

.. raw:: latex

   \section{Left Aligned
   Heading Test}

Right Aligned Heading
^^^^^^^^^^^^^^^^^^^^^

This section tests right-aligned heading output.

.. raw:: latex

   \section{Right Aligned
   Heading Test}

Inheritance Tests
-----------------

Part for Inheritance
^^^^^^^^^^^^^^^^^^^^

.. raw:: latex

   \part{Inheritance Test Part}

This part establishes the parent styling that child elements should inherit.

Chapter with Parent Styling
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. raw:: latex

   \chapter{Chapter Inheriting Part Styling}

This chapter should inherit font and/or color from the parent part if
inherit_all or inherit_font/inherit_color is enabled.

Section with Inherited Styling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. raw:: latex

   \section{Section Inheriting Chapter Styling}

This section should inherit from the parent chapter if inheritance is enabled.
