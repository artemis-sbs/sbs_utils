from __future__ import annotations
from typing import Callable
from enum import IntEnum
from .agent import Agent, SpawnData
from .helpers import FrameContext
from .procedural import ship_data as SHIP_DATA
from .vec import Vec3
from .procedural.ship_data import get_ship_data_for


class TickType(IntEnum):
    # Engine value bit 1111
    # Passive = 0x1 = Engine 
    PASSIVE = 0x01,
    TERRAIN = 0x01,
    ACTIVE = 0x10,
    NPC = 0x10,
    PLAYER = 0x20,
    ALL = 0xffff,
    #
    #
    NPC_AND_PLAYER = 0x30,
    UNKNOWN = 0


class SpaceObject(Agent):
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
        self.spawn_pos = Vec3(0,0,0)
        self.tick_type = TickType.UNKNOWN
        self._data_set = None
        self._engine_object = None
    
    @property
    def is_player(self) -> bool:
        return self.tick_type & TickType.PLAYER

    @property
    def is_npc(self) -> bool:
        return self.tick_type & TickType.ACTIVE

    @property
    def is_terrain(self) -> bool:
        return self.tick_type & TickType.PASSIVE

    @property
    def is_active(self) -> bool:
        return self.tick_type & TickType.ACTIVE

    @property
    def is_passive(self) -> bool:
        return self.tick_type & TickType.PASSIVE


    def get_space_object(self) -> SpaceObject:
        """ Gets the simulation space object

        :return: The simulation space object
        :rtype: The simulation space_object
        """

        return FrameContext.context.sim.get_space_object(self.id)

    def get_engine_object(self) -> SpaceObject:
        """ Gets the simulation space object

        :return: The simulation space object
        :rtype: The simulation space_object
        """
        return FrameContext.context.sim.get_space_object(self.id)

    def delete_object(self):
        FrameContext.context.sbs.delete_object(self.id)
        self.destroyed()

        
    
    

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
        """ Adds a nav point to the location passed if debug mode is on

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
            return FrameContext.context.sim.add_navpoint(x, y, z, name, color)
        return None

    def debug_remove_mark_loc(name: str):
        if SpaceObject.debug:
            return FrameContext.context.sim.delete_navpoint_by_name(name)
        return None

    def log(s: str) -> None:
        if SpaceObject.debug:
            print(s)

    def space_object(self) -> SpaceObject:
        """ get the simulation's space object for the object

        :return: simulation space object
        :rtype: simulation space object
        """
        return self._engine_object
        # return FrameContext.context.sim.get_space_object(self.id)

    def set_side(self, side):
        """ Get the side of the object

        :return: side
        :rtype: str
        """
        if side != self._side:
            self.remove_role(self._side)
            self.add_role(side)
            so = self.space_object()
            self._side = side
            self.update_comms_id()
            if so is not None:
                so.side = side
                FrameContext.context.sim.force_update_to_clients(self.id,0)

    def set_name(self, name) -> str:
        """ Get the name of the object
        :return: name
        :rtype: str
        """
        so = self.space_object()
        self._name = name
        self.update_comms_id()
        if so is None:
            return
        blob = so.data_set
        return blob.set("name_tag", name, 0)
    
    def set_art_id(self, art_id):
        """ Get the name of the object

        :return: name
        :rtype: str
        """
        if art_id != self._art_id:
            so = self.space_object()
            if so is not None:
                so.data_tag = art_id
                FrameContext.context.sim.force_update_to_clients(self.id,0)
            self._art_id = art_id

    def update_comms_id(self):
        """ Updates the comms ID when the name or side has changed
        :return: this is name or name(side)
        :rtype: str
        """

        if (self.side_display != ""):
            self._comms_id = f"{self.name} ({self.side_display})"
        else:
            self._comms_id = self.name

    @property
    def name(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._name

    @name.setter
    def name(self: SpaceObject, value: str) -> None:
        self.set_name(value)

    @property
    def side(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._side
    
    @side.setter
    def side(self: SpaceObject, value: str) -> None:
        self.set_side(value)

    @property
    def side_display(self: SpaceObject) -> str:
        test = self.data_set.get("hull_side", 0)
        if test is not None:
            return test
        return self._side
    
    @side_display.setter
    def side_display(self: SpaceObject, value: str) -> None:
        self.data_set.set("hull_side", value, 0)


    @property
    def comms_id(self: SpaceObject) -> str:
        """str, cached version of comms_id"""
        return self._comms_id
    
    @property
    def art_id(self: SpaceObject) -> str:
        """str, cached version of art_id"""
        return self._art_id

    @art_id.setter
    def art_id(self: SpaceObject, value: str) -> None:
        self.set_art_id(value)


    @property
    def race(self):
        return self.origin
    
    @property
    def origin(self):
        test = self.data_set.get("hull_origin", 0)
        if test is None:
            return "no origin"
        return test.lower()
    
    @origin.setter
    def origin(self: SpaceObject, value: str) -> None:
        self.data_set.set("hull_origin", value, 0)

    @property
    def crew(self):
        return self.get_inventory_value("__CREW__", self.origin)
    
    @crew.setter
    def crew(self: SpaceObject, value: str) -> None:
        self.set_inventory_value("__CREW__", value)


    @property
    def pos(self: SpaceObject) -> Vec3:
        """str, cached version of art_id"""
        return Vec3(self._engine_object.pos)

    @pos.setter
    def pos(self: SpaceObject, *args):
        v = Vec3(*args)
        FrameContext.context.sim.reposition_space_object(self._engine_object, v.x, v.y, v.z)



class MSpawn:
    def spawn_common(self, obj, x, y, z, name, side, art_id):
        self.spawn_pos = FrameContext.context.sbs.vec3(x,y,z)
        self._engine_object = obj

        FrameContext.context.sim.reposition_space_object(obj, x, y, z)
        self.add()
        self.add_role(self.__class__.__name__)
        self.add_role("__SPACE_OBJECT__")
        #
        # Add default roles
        #
        ship_data = SHIP_DATA.get_ship_data_for(art_id)
        if ship_data:
            roles = ship_data.get("roles", None)
            if roles:
                self.add_role(roles)


        blob = obj.data_set
        self._data_set = blob

        if name is not None:
            self._name = name
            blob.set("name_tag", name, 0)

        if side is not None:
            if isinstance(side, str):
                roles = side.split(",")
            else:
                roles = side
            side = roles[0].strip().lower()
            if side != "#":
                obj.side = side
                self._side = side
            self.update_comms_id()
            for role in roles:
                self.add_role(role)
        else:
            self._comms_id = name if name is not None else f""
        
        return blob


class MSpawnPlayer(MSpawn):
    def _make_new_player(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.PLAYER)
        self.tick_type = TickType.PLAYER
        return FrameContext.context.sim.get_space_object(self.id)

    def _spawn(self, x, y, z, name, side, art_id) -> SpawnData:
        # playerID will be a NUMBER, a unique value for every space object that you create.
        ship = self._make_new_player("behav_playership", art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self.add_role("__PLAYER__")
        self.add_role("__space_spawn__")
        self._art_id = art_id
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id) -> SpawnData:
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
        return self._spawn(x, y, z, name, side, art_id)

    def spawn_v(self, v, name, side, art_id) -> SpawnData:
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
        return self.spawn(v.x, v.y, v.z, name, side, art_id)


class MSpawnActive(MSpawn):
    """
    Mixin to add Spawn as an Active
    """

    def _make_new_active(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.ACTIVE)
        self.tick_type = TickType.ACTIVE
        return self.get_space_object()

    def _spawn(self, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_active(behave_id, art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self._art_id = art_id
        self.add_role("__NPC__")
        self.add_role("__space_spawn__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
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
        return self._spawn(x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new Active Object e.g. npc, station

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
        return self._spawn( v.x, v.y, v.z, name, side, art_id, behave_id)


class MSpawnPassive(MSpawn):
    """
    Mixin to add Spawn as an Passive
    """

    def _make_new_passive(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.PASSIVE)
        self.tick_type = TickType.PASSIVE
        return self.get_space_object()

    def _spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
        ship = self._make_new_passive(behave_id, art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self._art_id = art_id
        self.add_role("__TERRAIN__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new passive object e.g. Asteroid, etc.

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
        return self._spawn(x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, v, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new passive object e.g. asteroid, etc.

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
        return self._spawn(v.x, v.y, v.z, name, side, art_id, behave_id)

