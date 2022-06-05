The roles system
=====================

The SpaceObject class has methods for assigning and removing 'roles' to objects.

Roles are like sides but can be more dynamic and are not seen by the simulation.
You can have multiple roles on an object. Roles can be used in targeting etc.



**This need more documentation**
placing examples for now


Adding a role
------------------------------

.. code-block:: python

      npc.add_role('spy')


Remove a role
------------------------------

.. code-block:: python

      npc.remove_role('spy')

Check for a role
------------------------------

.. code-block:: python

      if npc.has_role('spy')
            pass

Using with targeting
------------------------------

.. code-block:: python


      close = self.find_closest(sim,'spy')
      # class names are included in roles
      close = self.find_closest(sim,'Station')
      # side is included in roles
      close = self.find_closest(sim,'tsn')
