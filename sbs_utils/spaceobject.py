from __future__ import annotations
from typing import Callable
import sbs
from enum import IntEnum
from .engineobject import Stuff, EngineObject, SpawnData, CloseData


class TickType(IntEnum):
    PASSIVE = 0,
    TERRAIN = 0,
    ACTIVE = 1,
    NPC = 1,
    PLAYER = 2,
    UNKNOWN = -1,
    ALL = -1


class SpaceObject(EngineObject):
    # roles : Stuff = Stuff()
    # _has_inventory : Stuff = Stuff()
    # has_links : Stuff = Stuff()
    # all = {}
    # removing = set()

    def __init__(self):
        super().__init__()
        self._name = ""
        self._side = ""
        self._art_id = ""
        self.spawn_pos = sbs.vec3(0,0,0)
        self.tick_type = TickType.UNKNOWN
    
    @property
    def is_player(self):
        return self.tick_type == TickType.PLAYER

    @property
    def is_npc(self):
        return self.tick_type == TickType.ACTIVE

    @property
    def is_terrain(self):
        return self.tick_type == TickType.PASSIVE

    @property
    def is_active(self):
        return self.tick_type == TickType.ACTIVE

    @property
    def is_passive(self):
        return self.tick_type == TickType.PASSIVE


    def get_space_object(self, sim):
        """ Gets the simulation space object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object
        """

        return sim.get_space_object(self.id)

    def get_engine_object(self, sim):
        """ Gets the simulation space object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object
        """
        return sim.get_space_object(self.id)

    
    

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
        """ Adds a nav point to the location passed if debug mode is on

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of the navpoint
        :type name: str
        :param color: color of the navpoint
        :type color: str
        """
        if SpaceObject.debug:
            return sim.add_navpoint(x, y, z, name, color)
        return None

    def debug_remove_mark_loc(sim, name: str):
        if SpaceObject.debug:
            return sim.delete_navpoint_by_name(name)
        return None

    def log(s: str):
        if SpaceObject.debug:
            print(s)

    def space_object(self, sim):
        """ get the simulation's space object for the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object
        """
        return sim.get_space_object(self.id)

    def set_side(self, sim, side):
        """ Get the side of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: side
        :rtype: str
        """
        so = self.space_object(sim)
        self.side = side
        self.update_comms_id()
        if so is not None:
            so.side = side

    def set_name(self, sim, name):
        """ Get the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str
        """
        so = self.space_object(sim)
        self.name = name
        self.update_comms_id()
        if so is None:
            return
        blob = so.data_set
        return blob.set("name_tag", name, 0)
    
    def set_art_id(self, sim, art_id):
        """ Get the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str
        """
        so = self.space_object(sim)
        so.data_tag = art_id
        self._art_id = art_id

    def update_comms_id(self):
        """ Updates the comms ID when the name or side has changed
        :return: this is name or name(side)
        :rtype: str
        """

        if (self.side != ""):
            self._comms_id = f"{self.name}({self.side})"
        else:
            self._comms_id = self.name

    @property
    def name(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._name

    @property
    def side(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._side

    @property
    def comms_id(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._comms_id
    
    @property
    def art_id(self: SpaceObject) -> str:
        """str, cached version of art_id"""
        return self._art_id


class MSpawn:
    def spawn_common(self, sim, obj, x, y, z, name, side):
        self.spawn_pos = sbs.vec3(x,y,z)
        sim.reposition_space_object(obj, x, y, z)
        self.add()
        self.add_role(self.__class__.__name__)
        self.add_role("__space_spawn__")
        self.add_role("__SPACE_OBJECT__")

        blob = obj.data_set
        if side is not None:
            if isinstance(side, str):
                roles = side.split(",")
            else:
                roles = side
            side = roles[0].strip()
            self._comms_id = f"{name}({side})" if name is not None else f"{side}{self.id}"
            obj.side = side
            self._side = side
            for role in roles:
                self.add_role(role)
        else:
            self._comms_id = name if name is not None else f""
        if name is not None:
            self._name = name
            blob.set("name_tag", name, 0)

        return blob


class MSpawnPlayer(MSpawn):
    def _make_new_player(self, sim, behave, data_id):
        self.id = sim.make_new_player(behave, data_id)
        self.tick_type = TickType.PLAYER
        return sim.get_space_object(self.id)

    def _spawn(self, sim, x, y, z, name, side, art_id):
        # playerID will be a NUMBER, a unique value for every space object that you create.
        ship = self._make_new_player(sim, "behav_playership", art_id)
        blob = self.spawn_common(sim, ship, x, y, z, name, side)
        self.add_role("__PLAYER__")
        self._art_id = art_id
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, sim, x, y, z, name, side, art_id):
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id)

    def spawn_v(self, sim, v, name, side, art_id):
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self.spawn(sim, v.x, v.y, v.z, name, side, art_id)


class MSpawnActive(MSpawn):
    """
    Mixin to add Spawn as an Active
    """

    def _make_new_active(self, sim,  behave, data_id):
        self.id = sim.make_new_active(behave, data_id)
        self.tick_type = TickType.ACTIVE
        return self.get_space_object(sim)

    def _spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_active(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x, y, z, name, side)
        self._art_id = art_id
        self.add_role("__NPC__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        """ Spawn a new active object e.g. npc, station

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        """ Spawn a new Active Object e.g. npc, station

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, v.x, v.y, v.z, name, side, art_id, behave_id)


class MSpawnPassive(MSpawn):
    """
    Mixin to add Spawn as an Passive
    """

    def _make_new_passive(self, sim, behave, data_id):
        self.id = sim.make_new_passive(behave, data_id)
        self.tick_type = TickType.PASSIVE
        return sim.get_space_object(self.id)

    def _spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_passive(sim, behave_id, art_id)
        blob = self.spawn_common(sim, ship, x, y, z, name, side)
        self._art_id = art_id
        self.add_role("__TERRAIN__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, sim, x, y, z, name, side, art_id, behave_id):
        """ Spawn a new passive object e.g. Asteroid, etc.

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id):
        """ Spawn a new passive object e.g. asteroid, etc.

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(sim, v.x, v.y, v.z, name, side, art_id, behave_id)

