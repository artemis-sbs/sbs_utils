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
    roles : Stuff = Stuff()
    _has_inventory : Stuff = Stuff()
    has_links : Stuff = Stuff()
    all = {}
    removing = set()

    def __init__(self):
        super().__init__()
        self._name = ""
        self._side = ""
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

    def all_roles(roles: str, linked_object: SpaceObject | None = None, filter_func=None):
        
        roles = roles.split(",\*")
        ret = set()
        if linked_object:
            for role in roles:
                objects = linked_object.get_objects_with_link(role)
                ret |= set(objects)
        else:
            for role in roles:
                objects = SpaceObject.get_objects_with_role(role)
                ret |= set(objects)
        
        items = list(ret)
        if filter_func is not None:
            items = filter(filter_func, items)
            

        return items

    def find_close_list(self, sim, roles=None, max_dist=None, filter_func=None, linked=False) -> list[CloseData]:
        """ Finds a list of matching objects 

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str] 
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: 
        :return: A list of close object
        :rtype: List[CloseData]
        """
        items = SpaceObject.all_roles(roles, self if linked else None, filter_func)
        return self.find_close_filtered_list(sim, items, max_dist)

    def find_close_filtered_list(self, sim, items, max_dist=None) -> list[CloseData]:
        ret = []
        test = max_dist

        for other_obj in items:
            # if this is self skip
            if other_obj.id == self.id:
                continue

            # test distance
            test = sbs.distance_id(self.id, other_obj.id)
            if max_dist is None:
                ret.append(CloseData(other_obj.id, other_obj, test))
                continue

            if test < max_dist:
                ret.append(CloseData(other_obj.id, other_obj, test))

        return ret

    def find_closest(self, sim, roles=None, max_dist=None, filter_func=None, linked: bool = False) -> CloseData:
        """ Finds the closest object matching the criteria

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str] 
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: CloseData
        """
        dist = None
        close_obj = None
        # list of close objects
        items = self.find_close_list(sim, roles, max_dist, filter_func, linked)
        # Slightly inefficient
        # Maybe this should be a filter function?
        for other in items:
            test = sbs.distance_id(self.id, other.id)
            if dist is None:
                close_obj = other
                dist = test
            elif test < dist:
                close_obj = other
                dist = test
        return close_obj

    def target_closest(self, sim, roles=None, max_dist=None, filter_func=None, shoot: bool = True, linked: bool = False):
        """ Find and target the closest object matching the criteria

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str] 
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function
        :param shoot: if the target should be shot at
        :type shoot: bool
        :return: A list of close object
        :rtype: CloseData
        """
        close = self.find_closest(sim, roles, max_dist, filter_func, linked)
        if close is not None and close.id is not None:
            self.target(sim, close.id, shoot)
        return close

    def target(self, sim, other_id: int, shoot: bool = True):
        """ Set the item to target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool
        """
        SpaceObject.resolve_id(other_id)
        other = sim.get_space_object(other_id)

        if other:
            data = {
                "target_pos_x": other.pos.x,
                "target_pos_y": other.pos.y,
                "target_pos_z": other.pos.z,
                "target_id": 0
            }
            if shoot:
                data["target_id"] = other.unique_ID
            self.update_engine_data(sim, data)

    def target_pos(self, sim, x: float, y: float, z: float):
        """ Set the item to target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool
        """
        data = {
            "target_pos_x": x,
            "target_pos_y": y,
            "target_pos_z": z,
            "target_id": 0
        }
        self.update_engine_data(sim, data)

    def find_closest_nav(self, sim, nav=None, max_dist=None, filter_func=None) -> CloseData:
        """ Finds the closest object matching the criteria

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type nav: str or List[str] 
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: CloseData
        """
        close_id = None
        close_obj = None
        dist = max_dist

        # TODO USe boardtest if max_dist used

        items = []
        if type(nav) == str:
            items.append(nav)
        else:
            items.extend(nav)

        if filter_func is not None:
            items = filter(filter_func, items)

        for nav in items:

            test = sbs.distance_to_navpoint(self.id, nav)
            if dist is None:
                close_id = nav
                close_obj = nav
                dist = test
            elif test < dist:
                close_id = nav
                close_obj = nav
                dist = test

        return CloseData(close_id, close_obj, dist)

    def target_closest_nav(self, sim, nav=None, max_dist=None, filter_func=None, shoot: bool = True):
        found = self.find_closest_nav(sim, nav, max_dist, filter_func)
        if found.id is not None:
            nav_object = sim.get_navpoint_by_name(found.id)
            self.target_pos(nav_object.pos.x,
                            nav_object.pos.y, nav_object.pos.z)
        return found

    def update_engine_data(self, sim, data):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        for (key, value) in data.items():
            if type(value) is tuple:
                blob.set(key, value[0], value[1])
            else:
                blob.set(key, value)

    def get_engine_data(self, sim, key, index=0):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        return blob.get(key, index)

    def set_engine_data(self, sim, key, value, index=0):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return
        blob = this.data_set
        blob.set(key, value, index)

    def get_engine_data_set(self, sim):
        this = sim.get_space_object(self.id)
        if this is None:
            # Object is destroyed
            return None
        return this.data_set

    def clear_target(self, sim):
        """ Clear the target

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        """
        this = sim.get_space_object(self.id)
        self.update_engine_data(sim, {
            "target_pos_x": this.pos.x,
            "target_pos_y": this.pos.y,
            "target_pos_z": this.pos.z,
            "target_id": 0
        })

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


class MSpawn:
    def spawn_common(self, sim, obj, x, y, z, name, side):
        sim.reposition_space_object(obj, x, y, z)
        self.add()
        self.add_role(self.__class__.__name__)
        blob = obj.data_set
        if side is not None:
            self._comms_id = f"{name}({side})" if name is not None else f"{side}{self.id}"
            obj.side = side
            self.add_role(side)
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


