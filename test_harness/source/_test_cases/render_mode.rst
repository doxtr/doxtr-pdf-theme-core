.. _test_render_mode:

Container Render Modes Test
===========================

This document tests the ``render_mode`` container configuration key which
controls how containers emit their LaTeX environments.

Tcolorbox Mode (Default)
-------------------------

.. stylebox:: tcolorbox-explicit
   :title: Tcolorbox Default

   This container uses the default tcolorbox render mode. The title is passed
   via tcolorbox's ``title={...}`` option.

Environment Mode
----------------

.. stylebox:: env-mode
   :title: Environment Mode Title

   This container uses environment render mode. The title is stored in
   ``\ddContainerTitle`` and ``\ddContainerIcon`` macros, not via tcolorbox's
   title option.

Environment Mode Without Title
------------------------------

.. stylebox:: env-mode
   :notitle:

   This container uses environment mode but has no title. The
   ``\ddContainerHasTitlefalse`` flag should be set.

Environment Mode Without Icon
------------------------------

.. stylebox:: env-no-icon
   :title: No Icon Title

   This container uses environment mode without an icon configured.
   The ``\ddContainerIcon`` macro should expand to empty.

Nested Environment Mode Containers
-----------------------------------

.. stylebox:: env-mode
   :title: Outer Container

   This is the outer container content.

   .. stylebox:: env-mode
      :title: Inner Container

      This is the inner container. The ``\begingroup``/``\endgroup`` scoping
      ensures this inner container's macros don't overwrite the outer.

   More outer content after the nested container.
