The Damage Dispatcher
=====================

The DamageDispatcher is used to route damage events to an object interested in the damage.


Artemis Cosmos damage system
------------------------------

Artemis Cosmos calls the script function HandleDamageEvent when an item receives damage.

sbs_utils damage system
------------------------------

The DispatcherDispatcher is intended receive these and route them to callback functions.
This can further be used to direct these to classes that represent the ships enabling the handling of this code to be handled in context of the ship(s) involved.

The HandleDamage should call :py:meth:`~sbs_utils.damagedispatcher.DamageDispatcher.dispatch_damage`

.. code-block:: python

   def HandleDamageEvent(sim, damage_event):
    DamageDispatcher.dispatch_damage(sim,damage_event)


Importing the hookhandlers module it does by default.


 .. code-block:: python

      from sbs_utils.handlerhooks import *
      # no longer need to implement handlers in script.py


Being notified of damage
-------------------------



Source of damage
^^^^^^^^^^^^^^^^^


 .. code-block:: python


   class Harvester(SpaceObject, MSpawnActive):

      def spawn(self, sim, v, side):
         ship = super().spawn_v(sim,v, None, side,  "Cargo", "behav_npcship")
         DamageDispatcher.add_source(self.id, self.on_damage_source)
         return ship

      def on_damage_source(self, sim, damage_event):
         pass


Target of damage
^^^^^^^^^^^^^^^^^
   

 .. code-block:: python


   class Asteroid(SpaceObject, MSpawnActive):

      def spawn(self, sim, v, side):
         ship = super().spawn_v(sim,v, None, side,  "Asteroid 1", "behav_asteroid")
         DamageDispatcher.add_target(self.id, self.on_damage_target)
         return ship

      def on_damage_target(self, sim, damage_event):
         pass

   

 damage_amount: float, how much damage was done
 damage_type: string, tag of damage type. 'destroyed' means that this event is really a dead event, not a damage event
 event_time: long int, time this damage occured, compare to simulation.time_tick_counter
 source_id: int, ID of unit that caused the damage.  Might be zero.
 source_parent_id: int, ID of PARENT of unit that caused the damage.  Might be zero.
 target_id: int, ID of unit that suffered the damage



API: damagedispatcher module
----------------------------------

.. automodule:: sbs_utils.damagedispatcher
   :members:
   :undoc-members:
   :show-inheritance:

