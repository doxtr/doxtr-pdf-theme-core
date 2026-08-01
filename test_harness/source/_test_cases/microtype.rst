Microtype Test Cases
====================

This document tests the microtype package integration.
It contains content that benefits from microtype's typographic refinements:

Character Protrusion
--------------------

The following text tests hanging punctuation. When microtype's protrusion
is enabled, punctuation marks like commas, periods, and quotation marks
will protrude slightly into the margins for a cleaner right edge.

"First, we must consider the data. Second, the analysis. Third, the conclusions."

This sentence has many commas, and a period. It should look better with protrusion!

Font Expansion
--------------

The following paragraph tests font expansion. microtype slightly varies the
width of each character to eliminate uneven word spacing (the "rivers" of
white space that appear in justified text).

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
in culpa qui officia deserunt mollit anim id est laborum.

Fine Kerning
------------

The following text tests fine kerning for character pairs:

The quick brown fox jumps over the lazy dog.
WWW WWW  III  LL  TT  ff  fi  fl  ffi  ffl
AVA  TTY  OOO  111  @@  **  ##

Tables
------

+------------------+------------------+------------------+
| Column One       | Column Two       | Column Three     |
+==================+==================+==================+
| Data A1          | Data B1          | Data C1          |
+------------------+------------------+------------------+
| Data A2          | Data B2          | Data C2          |
+------------------+------------------+------------------+
| Data A3          | Data B3          | Data C3          |
+------------------+------------------+------------------+

Code Blocks
-----------

.. code-block:: python

   def test_microtype():
       """Test that microtype improves typography."""
       text = "Hello, world!"  # Commas and exclamation marks
       assert text == "Hello, world!"
       return text

Admonitions
-----------

.. note::
   This is a note that tests microtype with admonition boxes.

.. warning::
   This is a warning that tests microtype with warning boxes.

.. tip::
   This is a tip that tests microtype with tip boxes.
