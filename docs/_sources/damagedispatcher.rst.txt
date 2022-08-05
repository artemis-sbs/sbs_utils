The Damage Dispatcher
=====================

The DamageDispatcher is used to route damage events to an object interested in the damage.


Artemis Cosmos damage system
------------------------------
Artemis Cosmos calls the script function HandleDamageEvent when an item receives damage.

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




API: damagedispatcher module
----------------------------------

.. automodule:: sbs_utils.damagedispatcher
   :members:
   :undoc-members:
   :show-inheritance:

