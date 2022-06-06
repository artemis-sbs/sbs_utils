Space Object
==================

All objects (ships, stations, asteroids, etc) are space objects in the Artemis Cosmos simulation.

The SBS Utils library has the :py:class:`~sbs_utils.spaceobject.SpaceObject` class to wrap things related to space objects easier to code.

Additionally, there are Mixin classes for spawning Space Objects. 

- :py:class:`~sbs_utils.spaceobject.MSpawnPassive`
- :py:class:`~sbs_utils.spaceobject.MSpawnActive`
- :py:class:`~sbs_utils.spaceobject.MSpawnPlayer`

:py:class:`~sbs_utils.spaceobject.MSpawnPassive` is for Spawning passive objects e.g. 

:py:class:`~sbs_utils.spaceobject.MSpawnActive`is for spawning active object, npx ships, stations etc.

:py:class:`~sbs_utils.spaceobject.MSpawnPlayer` if for spawning player ships.

Each of these add a :py:meth:`~sbs_utils.spaceobject.MSpawnPlayer.spawn` and a each add a :py:meth:`~sbs_utils.spaceobject.MSpawnPlayer.spawn_v` function. These functions allow spawning an entity with one function rather than several.
These will create a entity that has a name, a side, is positioned in space, has the define engine behavior and art work.


The :py:class:`~sbs_utils.playership.PlayerShip` class is a SpaceObject used for deriving Player Objects.



Deriving a SpaceObject
----------------------
Space Object typically derives from Space Object and a spawn mixin.


 .. code-block:: python

   class Station(SpaceObject, MSpawnActive):
      pass

Spawning a SpaceObject
----------------------
Using the default mixin a Space Object can be spawned with one line of code.

.. code-block:: python
    
   Station().spawn(sim, -500, 0, 400,
                      "DS 1", "TSN", "Starbase", "behav_station")

Customizing Spawn
----------------------
Spawn can be further simplified by implementing a new spawn in the derive SpaceObject as well as do other things related to spawn.

.. code-block:: python

   class Station(SpaceObject, MSpawnActive, MCommunications):
      count = 0

      def __init__(self):
         self.num = Station.count
         Station.count += 1
         self.b = Board()

         self.face_desc = faces.random_skaraan()

      def spawn(self, sim):
         super().spawn(sim, -500, 0, self.num * 400,
                        f"DS{Station.count}", "TSN", "Starbase", "behav_station")
         self.enable_comms(self.face_desc)

   # . . . a few lines later
   def start(sim):
      Mission.player.spawn(sim)
      for s in range(4):
         station = Station()
         station.spawn(sim)

PlayerShip
-------------
The :py:class:`~sbs_utils.playership.PlayerShip` is a class for a basic player ship.
Making it simple to spawn a player.

.. code-block:: python

   PlayerShip().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")

Customizing PlayerShip
----------------------
PlayerShip serves a a base class and it can be extended to create richer classes for player ships.

.. code-block:: python

   class Player(PlayerShip):
      def spawn(self, sim):
         # playerID will be a NUMBER, a unique value for every space object that you create.
         super().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")
         self.face_desc = faces.Characters.URSULA

What Spawn returns
--------------------
Spawn returns a :py:class:`~sbs_utils.spaceobject.SpawnData` which provides the ships simulation id , its simulation object, and its data blob.
This allows it to be further changes as needed easily without needing to retrieve these again.

.. code-block:: python

   class Player(PlayerShip):
      def spawn(self, sim):
         data = super().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")
         # Super fuel
         data.blob.set("energy", 2000)
         # tons of torps
         data.blob.set("torpedo_count", 25)






API: spaceobject module
-----------------------------

.. automodule:: sbs_utils.spaceobject
   :members:
   :undoc-members:
   :show-inheritance:
