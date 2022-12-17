from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
from sbs_utils.engineobject import Stuff
from enum import IntEnum
class MSpawn(object):
    """class MSpawn"""
    def spawn_common (self, sim, obj, x, y, z, name, side):
        ...
class MSpawnActive(MSpawn):
    """Mixin to add Spawn as an Active"""
    def _make_new_active (self, sim, behave, data_id):
        ...
    def _spawn (self, sim, x, y, z, name, side, art_id, behave_id):
        ...
    def spawn (self, sim, x, y, z, name, side, art_id, behave_id):
        """Spawn a new active object e.g. npc, station
        
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
        :rtype: SpawnData"""
    def spawn_v (self, sim, v, name, side, art_id, behave_id):
        """Spawn a new Active Object e.g. npc, station
        
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
        :rtype: SpawnData"""
class MSpawnPassive(MSpawn):
    """Mixin to add Spawn as an Passive"""
    def _make_new_passive (self, sim, behave, data_id):
        ...
    def _spawn (self, sim, x, y, z, name, side, art_id, behave_id):
        ...
    def spawn (self, sim, x, y, z, name, side, art_id, behave_id):
        """Spawn a new passive object e.g. Asteroid, etc.
        
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
        :rtype: SpawnData"""
    def spawn_v (self, sim, v, name, side, art_id, behave_id):
        """Spawn a new passive object e.g. asteroid, etc.
        
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
        :rtype: SpawnData"""
class MSpawnPlayer(MSpawn):
    """class MSpawnPlayer"""
    def _make_new_player (self, sim, behave, data_id):
        ...
    def _spawn (self, sim, x, y, z, name, side, art_id):
        ...
    def spawn (self, sim, x, y, z, name, side, art_id):
        """Spawn a new player
        
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
        :rtype: SpawnData"""
    def spawn_v (self, sim, v, name, side, art_id):
        """Spawn a new player
        
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
        :rtype: SpawnData"""
class SpaceObject(EngineObject):
    """class SpaceObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def clear ():
        ...
    @property
    def comms_id (self: 'SpaceObject') -> 'str':
        """str, cached version of comms_id"""
    def debug_mark_loc (sim, x: 'float', y: 'float', z: 'float', name: 'str', color: 'str'):
        """Adds a nav point to the location passed if debug mode is on
        
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
        :type color: str"""
    def debug_remove_mark_loc (sim, name: 'str'):
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_engine_data (self, sim, key, index=0):
        ...
    def get_engine_data_set (self, sim):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_space_object (self, sim):
        """Gets the simulation space object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object"""
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    @property
    def is_active (self):
        ...
    @property
    def is_npc (self):
        ...
    @property
    def is_passive (self):
        ...
    @property
    def is_player (self):
        ...
    @property
    def is_terrain (self):
        ...
    def log (s: 'str'):
        ...
    @property
    def name (self: 'SpaceObject') -> 'str':
        """str, cached version of comms_id"""
    def resolve_id (other: 'EngineObject | CloseData | int'):
        ...
    def resolve_py_object (other: 'EngineObject | CloseData | int'):
        ...
    def set_engine_data (self, sim, key, value, index=0):
        ...
    def set_name (self, sim, name):
        """Get the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str"""
    def set_side (self, sim, side):
        """Get the side of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: side
        :rtype: str"""
    @property
    def side (self: 'SpaceObject') -> 'str':
        """str, cached version of comms_id"""
    def space_object (self, sim):
        """get the simulation's space object for the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object"""
    def update_comms_id (self):
        """Updates the comms ID when the name or side has changed
        :return: this is name or name(side)
        :rtype: str"""
    def update_engine_data (self, sim, data):
        ...
class TickType(IntEnum):
    """An enumeration."""
    ACTIVE : 1
    PASSIVE : 0
    PLAYER : 2
    UNKNOWN : -1
