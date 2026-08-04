.. _test_container_mapping:

Container Mapping Test
======================

This document tests the ``doxtr_container_mapping`` feature. Containers are
written with alias class names that are redirected to registered styles at
render time.

Mapped Container via ``.. container::``
---------------------------------------

The class ``biz-alias`` is mapped to the ``business`` style. The generated
LaTeX environment must be ``ddcontainerbusiness``, not ``ddcontainerbizalias``.

.. container:: biz-alias

   This container uses the ``biz-alias`` class. The mapping should redirect
   it to the ``business`` tcolorbox environment.

Mapped Container via ``.. stylebox::``
---------------------------------------

The class ``typewriter-alias`` is mapped to the ``typewriter`` style. This
verifies that the ``.. stylebox::`` directive also respects the mapping.

.. stylebox:: typewriter-alias
   :title: Mapped Stylebox

   This stylebox uses the ``typewriter-alias`` argument. The mapping should
   redirect it to the ``typewriter`` tcolorbox environment.

Direct Match (No Mapping Needed)
---------------------------------

The class ``typewriter`` exists directly in ``doxtr_containers`` and has no
mapping entry. It must continue to work without any mapping configuration.

.. container:: typewriter

   This container uses the ``typewriter`` class directly. It should resolve
   without consulting the mapping at all.

Invalid Mapping Target (Fallback)
----------------------------------

The class ``broken-alias`` maps to ``nonexistent``, which is not registered
in ``doxtr_containers``. The resolver must fall back to the ``default``
container style and emit a warning.

.. container:: broken-alias

   This container's mapping target does not exist. It should fall back to
   the ``default`` container environment.
