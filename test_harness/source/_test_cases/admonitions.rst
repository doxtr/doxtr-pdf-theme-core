.. _test_admonitions:

Admonitions Test
================

This document tests all admonition types and their styling features.

Generic Admonition
------------------

.. admonition:: Generic Admonition Test

   This is a generic admonition box. It tests the default
   admonition rendering with the base configuration.

Note Admonition
---------------

.. note::

   This is a note admonition. It tests the note-specific
   styling from the conf.py override.

Warning Admonition
------------------

.. warning::

   This is a warning admonition. It tests the warning-specific
   red color scheme from the conf.py override.

Hint Admonition
---------------

.. hint::

   This is a hint admonition. It tests the hint styling.

Danger Admonition
-----------------

.. danger::

   This is a danger admonition. It tests the danger styling.

Error Admonition
----------------

.. error::

   This is an error admonition. It tests the error styling.

Caution Admonition
------------------

.. caution::

   This is a caution admonition. It tests the caution styling
   with dynamic contrast calculation for the icon color.

Tip Admonition
--------------

.. tip::

   This is a tip admonition. It tests the tip styling.

Important Admonition
--------------------

.. important::

   This is an important admonition. It tests the important styling.

Attention Admonition
--------------------

.. attention::

   This is an attention admonition. It tests the attention styling.

SeeAlso Admonition
------------------

.. seealso::

   This is a seealso admonition. It tests the seealso-specific
   styling with the right-side arrow decoration.

Custom Icon Admonition
----------------------

.. note::

   This note tests the custom LaTeX icon setting.
   The icon should render as a bold "i" character.

Nested Admonitions
------------------

.. note::

   Outer note with nested admonition.

   .. warning::

      This is a nested warning inside a note.
      It tests the content_background_color_nested setting.

   .. hint::

      This is a nested hint inside a note.

Spacing Test
------------

.. note::

   This note tests the before_skip and after_skip settings.

.. warning::

   This warning follows the note. The spacing between them
   should match the configured before_skip/after_skip values.

.. hint::

   This hint follows the warning. Verify the spacing is correct.
