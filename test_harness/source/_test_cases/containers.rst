.. _test_containers:

Containers / Stylebox Test
==========================

This document tests all container/stylebox features: frame, match_text_width,
title styles, fonts, colors, and icons.

Basic Container
---------------

.. stylebox:: Basic Container

   This is a basic stylebox container. It tests the default container
   rendering with the basic configuration.

Container with Title
--------------------

.. stylebox:: Container with Title

   This container has a custom title. It tests the title rendering
   with the classic title style geometry.

Framed Container
----------------

.. stylebox:: Framed Container
   :class: framed-box

   This container has a visible frame. It tests the container_frame=True
   setting which draws an outer border around the container.

Unframed Container
------------------

.. stylebox:: Unframed Container
   :class: unframed-box

   This container has no frame. It tests the container_frame=False
   setting which removes the outer border.

Match Text Width Container
--------------------------

.. stylebox:: Match Text Width Container
   :class: match-width-box

   This container matches the text width. It tests the match_text_width=True
   setting which pushes padding out so text aligns with body text.

Classic Title Style Container
-----------------------------

.. stylebox:: Classic Title Container
   :class: classic-title-box

   This container uses the classic title style. It tests the
   title_style='classic' setting.

Floating Title Style Container
------------------------------

.. stylebox:: Floating Title Container
   :class: floating-title-box

   This container uses the floating title style. It tests the
   title_style='floating' setting with the diamond-shaped title.

Ribbon Title Style Container
----------------------------

.. stylebox:: Ribbon Title Container
   :class: ribbon-title-box

   This container uses the ribbon title style. It tests the
   title_style='ribbon' setting with the curved ribbon decoration.

Container with Custom Font
--------------------------

.. stylebox:: Custom Font Container
   :class: custom-font-box

   This container tests the content_font setting. The content
   should use the configured font family.

Container with Custom Colors
----------------------------

.. stylebox:: Custom Colors Container
   :class: custom-colors-box

   This container tests the content_font_color and
   content_background_color settings.

Container with Title Icon
-------------------------

.. stylebox:: Title Icon Container
   :class: icon-title-box

   This container tests the title_icon setting. The icon
   should be rendered before the title text.

Container with Custom Title Font
--------------------------------

.. stylebox:: Custom Title Font Container
   :class: custom-title-font-box

   This container tests the title_font setting. The title
   should use the configured font family.
