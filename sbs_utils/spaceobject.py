from __future__ import annotations
from typing import Callable
import sbs
from random import randrange, choice, choices
from enum import IntEnum
from .relationship import Stuff


class TickType(IntEnum):
    PASSIVE = 0,
    TERRAIN = 0,
    ACTIVE = 1,
    NPC = 1,
    PLAYER = 2,
    UNKNOWN = -1,
    ALL = -1


class SpawnData:
    id: int
    engine_object: any
    blob: any
    py_object: SpaceObject

    def __init__(self, id, obj, blob, py_obj) -> None:
        self.id = id
        self.engine_object = obj
        self.blob = blob
        self.py_object = py_obj


class CloseData:
    id: int
    py_object: SpaceObject
    distance: float

    def __init__(self, other_id, other_obj, distance) -> None:
        self.id = other_id
        self.py_object = other_obj
        self.distance = distance


class SpaceObject:
    #ids = {'all': {}}
    roles : Stuff = Stuff()
    has_inventory : Stuff = Stuff()
    has_links : Stuff = Stuff()
    all = {}
    
    debug = True
    removing = set()

    def __init__(self):
        self._name = ""
        self._side = ""
        self.inventory = Stuff()
        self.links = Stuff()
        self.tick_type = TickType.UNKNOWN

    @classmethod
    def clear(cls):
        cls.all = {}
        cls.roles = Stuff()
        cls.has_inventory = Stuff()
        cls.has_links = Stuff()

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

    def destroyed(self):
        self.remove()

    def get_id(self):
        return self.id

    def _add(id, obj):
        SpaceObject.all[id] = obj

    def _remove(id):
        SpaceObject.all.pop(id)
        return SpaceObject.roles.remove_every_collection(id)

    def add_role(self, role: str):
        """ Add a role to the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        SpaceObject.roles.add_to_collection(role, self.id)

    def remove_role(self, role: str):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        SpaceObject.roles.remove_from_collection(role, self.id)

    def has_role(self, role):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        return SpaceObject.roles.collection_has(role, self.id)

    def get_roles(self, id):
        return SpaceObject.roles.get_collections_in(id)

    def get_objects_with_role(role):
        id_set = SpaceObject.roles.collection_set(role)
        return [SpaceObject.get(x) for x in id_set]

    def get_role_set(role):
        return  SpaceObject.roles.collection_set(role)
    ############### LINKS ############

    def add_link(self, link_name: str, other: SpaceObject | CloseData | int):
        """ Add a link to the space object. Links are uni-directional

        :param role: The role/link name to add e.g. spy, pirate etc.
        :type id: str
        """
        id = SpaceObject.resolve_id(other)
        self.links.add_to_collection(link_name,id)
        SpaceObject.has_links.add_to_collection(link_name, self.id)

    def remove_link(self, link_name: str, other: SpaceObject | CloseData | int):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        id = SpaceObject.resolve_id(other)
        the_set = self.links.remove_from_collection(link_name,id)
        if len(the_set)<1:
            SpaceObject.has_links.remove_from_collection(self.id)

    def has_link_to(self, link_name: str | list[str], other: SpaceObject | CloseData | int):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        id = SpaceObject.resolve_id(other)
        return self.links.collection_has(link_name,id)

    def _remove_every_link(self, other: SpaceObject | CloseData | int):
        id = SpaceObject.resolve_id(other)
        for role in self.links:
            self._remove_link(role, id)

    def get_in_links(self, other: SpaceObject | CloseData | int):
        id = SpaceObject.resolve_id(other)
        return self.inventory.get_collections_in(id)
        
    def get_objects_with_link(self, link_name):
        the_set =  self.links.collection_set(link_name)
        if the_set:
            # return a list so you can remove while iterating
            return [SpaceObject.get(x) for x in the_set]
        return []

    def get_link_set(self, link_name):
        return self.links.collection_set(link_name)

    def get_link_list(self, link_name):
        return self.links.collection_list(link_name)

    def has_links_set(collection_name):
        return SpaceObject.has_links.collection_set(collection_name)

    def has_links_list(collection_name):
        return SpaceObject.has_links.collection_list(collection_name)
    ####################################
    def resolve_id(other: SpaceObject | CloseData | int):
        id = other
        if isinstance(other, SpaceObject):
            id = other.id
        elif isinstance(other, CloseData):
            id = other.id
        elif isinstance(other, SpawnData):
            id = other.id
        return id

    def resolve_py_object(other: SpaceObject | CloseData | int):
        py_object = other
        if isinstance(other, SpaceObject):
            py_object = other
        elif isinstance(other, CloseData):
            py_object = other.py_object
        elif isinstance(other, SpawnData):
            py_object = other.py_object
        else:
            py_object = SpaceObject.get(other)
        return py_object

    def get_objects_from_set(the_set):
        return [SpaceObject.get(x) for x in the_set]
    ####################################

    ############### INVENTORY (Links to data) ############
    def add_inventory(self, collection_name: str, data: object):
        """ Add a link to the space object. Links are uni-directional

        :param role: The role/link name to add e.g. spy, pirate etc.
        :type id: str
        """
        self.inventory.add_to_collection(collection_name,data)
        SpaceObject.has_inventory.add_to_collection(collection_name, self.id)

    def remove_inventory(self, collection_name: str, data: object):
        """ Remove a role from the space object

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        """
        the_set = self.inventory.remove_from_collection(collection_name,data)
        if len(the_set)<1:
            SpaceObject.has_inventory.remove_from_collection(collection_name, self.id)

    def has_any_inventory(self, collection_name: str | list[str]):
        return SpaceObject.has_inventory.collection_has(collection_name,self.id)

    def has_in_inventory(self, link_name: str | list[str], data: object):
        """ check if the object has a role

        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool
        """
        return self.links.collection_has(link_name,data)

    def _remove_every_inventory(self, data: object):
        self.inventory.remove_every_collection(data)

    def get_inventory_in(self, data: object):
        return self.inventory.get_collections_in(data)
        
    def get_objects_in_inventory(self, collection_name):
        the_set =  self.inventory.collection_set(collection_name)
        if the_set:
            # return a list so you can remove while iterating
            return [SpaceObject.get(x) for x in the_set]
        return []

    def get_inventory_set(self, collection_name):
        return self.links.collection_set(collection_name)
    def get_inventory_list(self, collection_name):
        return self.links.collection_list(collection_name)

    def has_inventory_set(collection_name):
        return SpaceObject.has_inventory.collection_set(collection_name)

    def has_inventory_list(collection_name):
        return SpaceObject.has_inventory.collection_list(collection_name)
    ###########################################################


    def get(id):
        o = SpaceObject.all.get(id)
        if o is None:
            return None
        return o

    def get_as(id, cls):
        o = SpaceObject.all.get(id)
        if o is None:
            return None
        if o.__class__ != cls:
            return None
        return o

    def py_class():
        return __class__

    def add(self):
        """ Add the object to the system, called by spawn normally
        """
        SpaceObject._add(self.id, self)

    def remove(self):
        """ remove the object to the system, called by destroyed normally
        """
        SpaceObject._remove(self.id)

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

    def target_closest(self, sim, roles=None, max_dist=None, filter_func=None, shoot: bool = True, linked: bool = True):
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
        if close.id is not None:
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
            obj._side = side
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


###################
# Set functions
def role(role: str):
    return SpaceObject.get_role_set(role)


def linked_to(link_source, link_name: str):
    link_source = SpaceObject.resolve_py_object(link_source)
    return link_source.get_link_set(link_name)

# Get the set of IDS of a broad test


def broad_test(x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    obj_list = sbs.broad_test(x1, z1, x2, z2, broad_type)
    return {so.unique_ID for so in obj_list}


#######################
# Set resolvers
def closest_list(source: int | CloseData | SpawnData | SpaceObject, the_set, max_dist=None, filter_func=None) -> list[CloseData]:
    ret = []
    test = max_dist
    source_id = SpaceObject.resolve_id(source)

    for other_id in the_set:
        # if this is self skip
        if other_id == source_id:
            continue
        other_obj = SpaceObject.get(other_id)
        if filter_func is not None and not filter_func(other_obj):
            continue
        # test distance
        test = sbs.distance_id(source_id, other_id)
        if max_dist is None:
            ret.append(CloseData(other_id, other_obj, test))
            continue

        if test < max_dist:
            ret.append(CloseData(other_id, other_obj, test))

    return ret


def closest(self, the_set, max_dist=None, filter_func=None) -> CloseData:
    test = max_dist
    ret = None
    source_id = SpaceObject.resolve_id(self)

    for other_id in the_set:
        # if this is self skip
        if other_id == SpaceObject.resolve_id(self):
            continue
        other_obj = SpaceObject.get(other_id)
        if filter_func is not None and not filter_func(other_obj):
            continue

        # test distance
        test = sbs.distance_id(source_id, other_id)
        if max_dist is None:
            ret = CloseData(other_id, other_obj, test)
            max_dist = test
            continue
        elif test < max_dist:
            ret = CloseData(other_id, other_obj, test)
            continue

    return ret


def closest_object(self, sim, the_set, max_dist=None, filter_func=None) -> SpaceObject:
    ret = closest(self, sim, the_set, max_dist=None, filter_func=None)
    if ret:
        return ret.py_object


def random(the_set):
    rand_id = choice(tuple(the_set))
    return SpaceObject.get(rand_id)


def random_list(the_set, count=1):
    rand_id_list = choices(tuple(the_set), count)
    return [SpaceObject.get(x) for x in rand_id_list]


def to_py_object_list(the_set):
    return [SpaceObject.get(id) for id in the_set]


def target(sim, set_or_object, target_id, shoot: bool = True):
    """ Set the item to target
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool
    """
    SpaceObject.resolve_id(target_id)
    target = sim.get_space_object(target_id)

    if target:
        data = {
            "target_pos_x": target.pos.x,
            "target_pos_y": target.pos.y,
            "target_pos_z": target.pos.z,
            "target_id": 0
        }
        if shoot:
            data["target_id"] = target.unique_ID

    all = list(set_or_object)
    for chaser in all:
        chaser = SpaceObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)


def target_pos(sim, chasers: set | int | CloseData|SpawnData, x: float, y: float, z: float):
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
    all = list(chasers)
    for chaser in all:
        chaser = SpaceObject.resolve_py_object(chaser)
        chaser.update_engine_data(sim, data)
