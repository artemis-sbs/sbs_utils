class CloseData(object):
    """class CloseData"""
    def __init__ (self, other_id, other_obj, distance) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
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
class SpaceObject(object):
    """class SpaceObject"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _add (id, obj):
        ...
    def _add_role (role, id, obj):
        ...
    def _remove (id):
        ...
    def _remove_every_role (id):
        ...
    def _remove_role (role, id):
        ...
    def add (self):
        """Add the object to the system, called by spawn normally
                """
    def add_role (self, role: str):
        """Add a role to the space object
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str"""
    def clear_target (self, sim):
        """Clear the target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation"""
    def comms_id (self, sim):
        """Get the text to use in the comms messages
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: this is name or name(side)
        :rtype: str"""
    def debug_mark_loc (sim, x: float, y: float, z: float, name: str, color: str):
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
    def debug_remove_mark_loc (sim, name: str):
        ...
    def destroyed (self):
        ...
    def find_close_list (self, sim, roles=None, max_dist=None, filter_func=None) -> list:
        """Finds a list of matching objects
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func:
        :return: A list of close object
        :rtype: List[CloseData]"""
    def find_closest (self, sim, roles=None, max_dist=None, filter_func=None) -> sbs_utils.spaceobject.CloseData:
        """Finds the closest object matching the criteria
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type roles: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: CloseData"""
    def find_closest_nav (self, sim, nav=None, max_dist=None, filter_func=None) -> sbs_utils.spaceobject.CloseData:
        """Finds the closest object matching the criteria
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param roles: Roles to looks for can also be class name
        :type nav: str or List[str]
        :param max_dist: Max distance to search (faster)
        :type max_dist: float
        :param filter_func: Called to test each object to filter out non matches
        :type filter_func: function that takes ID
        :return: A list of close object
        :rtype: CloseData"""
    def get (id):
        ...
    def get_as (id, cls):
        ...
    def get_engine_data (self, sim, key, index=0):
        ...
    def get_engine_data_set (self, sim):
        ...
    def get_id (self):
        ...
    def get_objects_with_role (role):
        ...
    def get_roles (self, id):
        ...
    def get_space_object (self, sim):
        """Gets the simulation space object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object"""
    def has_role (self, role):
        """check if the object has a role
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str
        :return: If the object has the role
        :rtype: bool"""
    def log (s: str):
        ...
    def name (self, sim):
        """Get the name of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: name
        :rtype: str"""
    def py_class ():
        ...
    def remove (self):
        """remove the object to the system, called by destroyed normally
                """
    def remove_role (self, role: str):
        """Remove a role from the space object
        
        :param role: The role to add e.g. spy, pirate etc.
        :type id: str"""
    def set_engine_data (self, sim, key, value, index=0):
        ...
    def side (self, sim):
        """Get the side of the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: side
        :rtype: str"""
    def space_object (self, sim):
        """get the simulation's space object for the object
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object"""
    def target (self, sim, other_id: int, shoot: bool = True):
        """Set the item to target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool"""
    def target_closest (self, sim, roles=None, max_dist=None, filter_func=None, shoot: bool = True):
        """Find and target the closest object matching the criteria
        
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
        :rtype: CloseData"""
    def target_closest_nav (self, sim, nav=None, max_dist=None, filter_func=None, shoot: bool = True):
        ...
    def target_pos (self, sim, x: float, y: float, z: float):
        """Set the item to target
        
        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param other_id: the id of the object to target
        :type other_id: int
        :param shoot: if the object should be shot at
        :type shoot: bool"""
    def update_engine_data (self, sim, data):
        ...
class SpawnData(object):
    """class SpawnData"""
    def __init__ (self, id, obj, blob, py_obj) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
