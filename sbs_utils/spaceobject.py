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
        """_art_id is deprecated. Use _ship_data_key instead."""
        self._ship_data_key = ""
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
        """ 
        Gets the simulation space object.

        Returns:
            SpaceObject: The simulation space object
        """

        return FrameContext.context.sim.get_space_object(self.id)

    def get_engine_object(self) -> SpaceObject:
        """ 
        Gets the simulation space object.

        Returns:
            SpaceObject: The simulation space_object
        """
        return FrameContext.context.sim.get_space_object(self.id)

    def delete_object(self):
        """
        Delete this SpaceObject.
        """
        FrameContext.context.sbs.delete_object(self.id)
        self.destroyed()

        
    
    

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
        """ 
        Adds a nav point to the location passed, if debug mode is active.

        Args:
            x (float): x location.
            y (float): y location.
            z (float): z location.
            name (str): Name of the navpoint.
            color (str): Color of the navpoint.
        Returns:
            Navpoint | None: The navpoint added, or None if debug mode is not active.
        """
        if SpaceObject.debug:
            return FrameContext.context.sim.add_navpoint(x, y, z, name, color)
        return None

    def debug_remove_mark_loc(name: str):
        """
        Delete the navpoint specified.
        Args
            name (str): The name of the navpoint to delete.
        """
        if SpaceObject.debug:
            return FrameContext.context.sim.delete_navpoint_by_name(name)
        return None

    def log(s: str) -> None:
        if SpaceObject.debug:
            print(s)

    def space_object(self) -> SpaceObject:
        """ 
        Get the simulation's space object for the object.

        Returns:
            SpaceObject: The simulation space object.
        """
        return self._engine_object
        # return FrameContext.context.sim.get_space_object(self.id)

    def set_side(self, side):
        """ 
        Get the side of the object

        Returns:
            str: The side.
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
        """ 
        Get the name of the object
        
        Returns:
            str: The name of the object.
        """
        so = self.space_object()
        self._name = name
        self.update_comms_id()
        if so is None:
            return
        blob = so.data_set
        return blob.set("name_tag", name, 0)
    
    def set_art_id(self, ship_key):
        """ 
        Deprecated. Use `SpaceObject.set_ship_data_key()` instead.

        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_key (str): The ship key.
        """
        if ship_key != self._ship_data_key:
            so = self.space_object()
            if so is not None:
                so.data_tag = ship_key
                FrameContext.context.sim.force_update_to_clients(self.id,0)
            self._ship_data_key = ship_key

    def set_ship_data_key(self, ship_data_key):
        """ 
        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.
        """
        if ship_data_key != self._ship_data_key:
            so = self.space_object()
            if so is not None:
                so.data_tag = ship_data_key
                FrameContext.context.sim.force_update_to_clients(self.id,0)
            self._ship_data_key = ship_data_key

    def update_comms_id(self):
        """ 
        Updates the comms ID when the name or side has changed.
        If the side of the object is empty, the comms ID is the name of the object.
        Otherwise, the comms ID is the name and side of the object in the format
        ```
        name (side)
        ```
        Returns:
            str: The comms ID.
        """

        if (self.side_display != ""):
            self._comms_id = f"{self.name} ({self.side_display})"
        else:
            self._comms_id = self.name

    @property
    def name(self: SpaceObject) -> str:
        """
        The name of the space object.
        Returns:
            str: The name.
        """
        return self._name

    @name.setter
    def name(self: SpaceObject, value: str) -> None:
        """
        Set the name of the space object.
        Args:
            value (str): The name to apply to the space object.
        """
        self.set_name(value)

    @property
    def side(self: SpaceObject) -> str:
        """
        Get the side of the space object.
        Returns:
            str: The side.
        """
        return self._side
    
    @side.setter
    def side(self: SpaceObject, value: str) -> None:
        """
        Set the side of the space object.
        Args:
            value (str): The side to apply to the space object.
        """
        self.set_side(value)

    @property
    def side_display(self: SpaceObject) -> str:
        """
        Get the display value for the object's side.
        Returns:
            str: The side
        """
        test = self.data_set.get("hull_side", 0)
        if test is not None and isinstance(test, str):
            return test
        return self._side
    
    @side_display.setter
    def side_display(self: SpaceObject, value: str) -> None:
        """
        Set the display value for the object's side.
        Args:
            value (str): The side.
        """
        self.data_set.set("hull_side", value, 0)


    @property
    def comms_id(self: SpaceObject) -> str:
        """
        Get the cached version of the object's comms ID.
        Returns:
            str: The comms ID.
        """
        return self._comms_id
    
    @property
    def art_id(self: SpaceObject) -> str:
        """
        Deprecated. Use `SpaceObject.ship_data_key` instead.

        Get the ship key from shipData that this space object is using.
        Returns:
            str: The ship key.
        """
        return self._ship_data_key

    @art_id.setter
    def art_id(self: SpaceObject, ship_data_key: str) -> None:
        """
        Deprecated. Use `SpaceObject.ship_data_key` instead.

        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.
        """
        self.set_ship_data_key(ship_data_key)

    @property
    def ship_data_key(self: SpaceObject) -> str:
        """
        Get the ship key from shipData that this space object is using.
        Returns:
            str: The ship key.
        """
        return self._ship_data_key
    
    @ship_data_key.setter
    def ship_data_key(self: SpaceObject, ship_data_key: str) -> None:
        """
        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.
        """
        self.set_ship_data_key(ship_data_key)

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
        """
        Get the position of the object.
        Returns:   
            Vec3: The position.
        """
        return Vec3(self._engine_object.pos)

    @pos.setter
    def pos(self: SpaceObject, *args):
        """
        Set the position of the object.
        Args:
            *args (tuple): A variable-length argument list. This should be a single Vec3, or up to three floats, representing the position of the object.
        """
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
        self._ship_data_key = art_id
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
        self._ship_data_key = art_id
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
        self._ship_data_key = art_id
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

