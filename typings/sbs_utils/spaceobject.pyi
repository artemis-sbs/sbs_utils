from sbs_utils.agent import Agent
from sbs_utils.agent import SpawnData
from sbs_utils.helpers import FrameContext
from enum import IntEnum
from sbs_utils.vec import Vec3
class MSpawn(object):
    """class MSpawn"""
    def spawn_common (self, obj, x, y, z, name, side, art_id):
        ...
class MSpawnActive(MSpawn):
    """Mixin to add Spawn as an Active"""
    def _make_new_active (self, behave, data_id):
        ...
    def _spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
    def spawn (self, x, y, z, name, side, art_id, behave_id):
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
    def _make_new_passive (self, behave, data_id):
        ...
    def _spawn (self, x, y, z, name, side, art_id, behave_id):
        ...
    def spawn (self, x, y, z, name, side, art_id, behave_id):
        """Spawn a new passive object e.g. Asteroid, etc.
        
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
    def spawn_v (self, v, name, side, art_id, behave_id):
        """Spawn a new passive object e.g. asteroid, etc.
        
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
    def _make_new_player (self, behave, data_id):
        ...
    def _spawn (self, x, y, z, name, side, art_id):
        ...
    def spawn (self, x, y, z, name, side, art_id):
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
    def spawn_v (self, v, name, side, art_id):
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
class SpaceObject(Agent):
    """class SpaceObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    @property
    def art_id (self: 'SpaceObject') -> 'str':
        """str, cached version of art_id"""
    @art_id.setter
    def art_id (self: 'SpaceObject', value: 'str'):
        """str, cached version of art_id"""
    def clear ():
        ...
    @property
    def comms_id (self: 'SpaceObject') -> 'str':
        """str, cached version of comms_id"""
    def debug_mark_loc (sim, x: 'float', y: 'float', z: 'float', name: 'str', color: 'str'):
        """Adds a nav point to the location passed if debug mode is on
        
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
    def debug_remove_mark_loc (name: 'str'):
        ...
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_engine_object (self):
        """Gets the simulation space object
        
        :return: The simulation space object
        :rtype: The simulation space_object"""
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def get_space_object (self):
        """Gets the simulation space object
        
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
    @name.setter
    def name (self: 'SpaceObject', value: 'str'):
        """str, cached version of comms_id"""
    @property
    def pos (self: 'SpaceObject') -> 'Vec3':
        """str, cached version of art_id"""
    @pos.setter
    def pos (self: 'SpaceObject', *args):
        """str, cached version of art_id"""
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def set_art_id (self, art_id):
        """Get the name of the object
        
        :return: name
        :rtype: str"""
    def set_name (self, name):
        """Get the name of the object
        :return: name
        :rtype: str"""
    def set_side (self, side):
        """Get the side of the object
        
        :return: side
        :rtype: str"""
    @property
    def side (self: 'SpaceObject') -> 'str':
        """str, cached version of comms_id"""
    @side.setter
    def side (self: 'SpaceObject', value: 'str'):
        """str, cached version of comms_id"""
    def space_object (self):
        """get the simulation's space object for the object
        
        :return: simulation space object
        :rtype: simulation space object"""
    def update_comms_id (self):
        """Updates the comms ID when the name or side has changed
        :return: this is name or name(side)
        :rtype: str"""
class TickType(IntEnum):
    """int([x]) -> integer
    int(x, base=10) -> integer
    
    Convert a number or string to an integer, or return 0 if no arguments
    are given.  If x is a number, return x.__int__().  For floating point
    numbers, this truncates towards zero.
    
    If x is not a number or if base is given, then x must be a string,
    bytes, or bytearray instance representing an integer literal in the
    given base.  The literal can be preceded by '+' or '-' and be surrounded
    by whitespace.  The base defaults to 10.  Valid bases are 0 and 2-36.
    Base 0 means to interpret the base from the string as an integer literal.
    >>> int('0b100', base=0)
    4"""
    ACTIVE : 16
    ALL : 65535
    NPC_AND_PLAYER : 48
    PASSIVE : 1
    PLAYER : 32
    UNKNOWN : 0
