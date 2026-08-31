The targeting system
=====================
The SpaceObject class has methods for targeting other objects to navigate to or to attack.


**This need more documentation**
placing examples for now

Find closest
------------------------------

.. code-block:: python

      close = self.find_closest(sim,'Station')
      # close.id        = object id
      # close.obj       = the python SpaceObject of the other entity
      # close.distance  = the distance 


targeting closest
------------------------------

.. code-block:: python

      def find_target(self, sim):
            self.target_closest(sim,'Station')

targeting closest limit distance
---------------------------------

.. code-block:: python

      def find_target(self, sim):
            self.target_closest(sim,'Station', 10000)


Advanced Filtering 
------------------------------


.. code-block:: python

      def filter_res(self, other):
        if not isinstance(other[1], ResourceAsteroid):
            return False
        if other[1].amount <= 0:
            return False
        return other[1].resource_type == self.resource_type

      def find_target(self, sim):
        if self.state == HarvesterState.HARVESTING:
            self.target_closest(sim,'ResourceAsteroid', filter_func=self.filter_res)

Clearing target
------------------------------

.. code-block:: python

        elif self.state == HarvesterState.FULL_WAITING:
            self.clear_target(sim)



Find a list of close things
------------------------------

.. code-block:: python

      if self.state == HarvesterState.FULL_WAITING:
            for base in self.find_close_list(sim, 'Spacedock'):
                sbs.send_comms_button_info(player_id, "yellow", f"Head to {base.obj.comms_id}", f"{base.obj.id}"

