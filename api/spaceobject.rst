Space Object
==================

All objects (ships, stations, asteroids, etc) are space objects in the Artemis Cosmos simulation.

Creating space objects in Artemis Cosmos
-------------------------------------------

Creating a ship or terrain element in Cosmos takes several lines of code.

At the very least, you need to create the objects, set its side, position the object and name the object.

.. code-block:: python

   shipID = sim.make_new_active("behav_station", hull_type)
   ship = sim.get_space_object(shipID)
   ship.side = side_tag
   sim.reposition_space_object(ship, pos_x,0,pos_z)
   blob = ship.data_set
   blob.set("name_tag", station_name, 0)

Additionally, you may want to have a character face, and keep track of the ship id as part of a group.



Creating Space Objects using sbs_utils
---------------------------------------

The SBS Utils library has the :py:class:`~sbs_utils.spaceobject.SpaceObject` class to wrap things related to space objects easier to code.

Additionally, has the library has these classes to create space objects:

- :py:class:`~sbs_utils.objects.PlayerShip`
- :py:class:`~sbs_utils.objects.Npc`
- :py:class:`~sbs_utils.objects.Active`
- :py:class:`~sbs_utils.objects.Terrain`
- :py:class:`~sbs_utils.objects.Passive`

:py:class:`~sbs_utils.objects.PlayerShip` is used to create player ships.

:py:class:`~sbs_utils.objects.Npc` and :py:class:`~sbs_utils.objects.Active` are similar and are for creating non-player ships.

:py:class:`~sbs_utils.objects.Terrain` and :py:class:`~sbs_utils.objects.Passive` are similar and are for creating world item that are not ships.


Spawning SpaceObjects
---------------------------

sbs_utils Space Objects provide a single spawn function.
spawn takes a position, a Name (can be None) a side (can be None), the art id and a behavior string.

This single function does all the setup for the space object.

 .. code-block:: python
   
   Npc().spawn(sim, -500, 0, 400,
                      "DS 1", "TSN", "Starbase", "behav_station")
   PlayerShip().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")
   Terrain().spawn_v(sim, 100,0,1000, None, None, f"Asteroid 1", "behav_asteroid")

What Spawn returns
--------------------
Spawn returns a :py:class:`~sbs_utils.spaceobject.SpawnData` which provides the ships simulation id , its simulation object, and its data blob.
This allows it to be further changes as needed easily without needing to retrieve these again.

.. code-block:: python

         PlayerShip().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")
         # Super fuel
         data.blob.set("energy", 2000)
         # tons of torps
         data.blob.set("torpedo_count", 25)


Deriving a SpaceObject
----------------------
Space Object typically derives from PlayerShip, Npc, or Terrain.

 .. code-block:: python

   class Station(Npc):
      pass

Spawning a derived SpaceObject
-------------------------------
The Station can be spawned with one line of code.

.. code-block:: python
    
   Station().spawn(sim, -500, 0, 400,
                      "DS 1", "TSN", "Starbase", "behav_station")

Customizing Spawn
----------------------
Spawn can be further simplified by implementing a new spawn in the derive SpaceObject as well as do other things related to spawn.


For example, this example spawn of a station only needs the position.

.. code-block:: python

   class Station(Npc, MCommunications):
      count = 1
      def spawn(self, sim, x, y, z):
         super().spawn(sim, x,y,z,
                        f"DS{Station.count}", "TSN", "Starbase", "behav_station")
         Station.count += 1
    
    # to spawn a space station
   Station().spawn(sim, 100,0,100)


Spawn can be further simplified by implementing a new spawn in the derive SpaceObject as well as do other things related to spawn.
e.g. Enabling comms and adding a face description.

The example automatically positions the stations.

.. code-block:: python

   class Station(Npc, MCommunications):
      count = 0

      def __init__(self):
         self.num = Station.count
         Station.count += 1

      def spawn(self, sim):
         super().spawn(sim, -500, 0, self.num * 400,
                        f"DS{Station.count}", "TSN", "Starbase", "behav_station")

         face_desc = faces.random_skaraan()
         self.enable_comms(face_desc)

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
         spawn_data = super().spawn(sim,0,0,0, "Artemis", "TSN", "Battle Cruiser")
         faces.set_face(spawn_data.id, faces.Characters.URSULA)

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


The following classes are created using Mixin classes for spawning Space Objects.
They can be used to derive new Space Object classes. However, it is likely the PlayerShip, Npc, and Terrain classes should be sufficient.

- :py:class:`~sbs_utils.spaceobject.MSpawnPassive`
- :py:class:`~sbs_utils.spaceobject.MSpawnActive`
- :py:class:`~sbs_utils.spaceobject.MSpawnPlayer`

:py:class:`~sbs_utils.spaceobject.MSpawnPassive` is for Spawning passive objects e.g. asteroids

:py:class:`~sbs_utils.spaceobject.MSpawnActive` is for spawning active object, npx ships, stations etc.

:py:class:`~sbs_utils.spaceobject.MSpawnPlayer` if for spawning player ships.

Each of these add a :py:meth:`~sbs_utils.spaceobject.MSpawnPlayer.spawn` and a each add a :py:meth:`~sbs_utils.spaceobject.MSpawnPlayer.spawn_v` function. These functions allow spawning an entity with one function rather than several.
These will create a entity that has a name, a side, is positioned in space, has the define engine behavior and art work.






API: spaceobject module
-----------------------------

.. automodule:: sbs_utils.spaceobject
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: sbs_utils.objects
   :members:
   :undoc-members:
   :show-inheritance:
