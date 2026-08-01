.. _test_tables:

Tables Test
===========

This document tests all table features: header colors, row stripes,
caption positions, title styles, and fade effects.

Basic Table
-----------

+----------+----------+----------+
| Column 1 | Column 2 | Column 3 |
+==========+==========+==========+
| A        | B        | C        |
+----------+----------+----------+
| D        | E        | F        |
+----------+----------+----------+
| G        | H        | I        |
+----------+----------+----------+

This is a basic table with the default styling. It tests the base
table configuration from core_config.py.

Table with Header Styling
-------------------------

+--------+----------+----------+
| Header | Column 2 | Column 3 |
+========+==========+==========+
| Row 1  | Data 1   | Data 2   |
+--------+----------+----------+
| Row 2  | Data 3   | Data 4   |
+--------+----------+----------+

This table tests the header_background_color and header_font_color
settings from the conf.py override.

Table with Row Striping
-----------------------

+--------+----------+
| Col A  | Col B    |
+========+==========+
| Odd    | Data 1   |
+--------+----------+
| Even   | Data 2   |
+--------+----------+
| Odd    | Data 3   |
+--------+----------+

This table tests the row_color_odd and row_color_even stripe settings.

Side Caption Table
------------------

+--------+----------+----------+
| Col 1  | Col 2    | Col 3    |
+========+==========+==========+
| A      | B        | C        |
+--------+----------+----------+
| D      | E        | F        |
+--------+----------+----------+

This table tests the caption_position='side' setting. The caption
should appear on the side of the table.

Top Caption Table
-----------------

+--------+----------+
| Col A  | Col B    |
+========+==========+
| 1      | X        |
+--------+----------+
| 2      | Y        |
+--------+----------+

This table tests the caption_position='top' setting. The caption
should appear above the table.

Bottom Caption Table
--------------------

+--------+----------+
| Col A  | Col B    |
+========+==========+
| 1      | X        |
+--------+----------+
| 2      | Y        |
+--------+----------+

This table tests the caption_position='bottom' setting. The caption
should appear below the table.

Floating Title Table
--------------------

+--------+----------+----------+
| Header | Col 2    | Col 3    |
+========+==========+==========+
| Row 1  | Data     | Data     |
+--------+----------+----------+
| Row 2  | Data     | Data     |
+--------+----------+----------+

This table tests the title_style='floating' setting for the table
caption.

Arrow Title Table
-----------------

+--------+----------+
| Header | Col B    |
+========+==========+
| Row 1  | Data     |
+--------+----------+
| Row 2  | Data     |
+--------+----------+

This table tests the title_style='arrow' setting for the table
caption.

Fade Dots Table
---------------

+--------+----------+----------+
| Header | Col 2    | Col 3    |
+========+==========+==========+
| A      | B        | C        |
+--------+----------+----------+
| D      | E        | F        |
+--------+----------+----------+

This table tests the title_fade_dots setting which adds a fade
dots effect to the table title.
