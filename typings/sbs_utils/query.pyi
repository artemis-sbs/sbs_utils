from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
def add_role (set_holder, role):
    ...
def all_objects_exists (sim, the_set):
    ...
def broad_test (x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    """broad_test
    
    returns a set of ids that are in the target rect
    
    :param x1: x location (left)
    :type x1: float
    :param z1: z location (top)
    :type z1: float
    :param x2: x location (right)
    :type x2: float
    :param z2: z location (bottom)
    :type z2: float
    
    :param broad type:  -1=All, 0=player, 1=Active, 2=Passive
    :type broad_type: int
    :rtype: set of ids"""
def clear_target (sim, chasers: set | int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData):
    """Clear the target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation"""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.engineobject.CloseData:
    """closest
    
    get the  close data that matches the test set, max_dist and optional filter function
    
    :param source: The id object to check
    :type source: int / id
    :param the_set: a set of ids to check against
    :type the_set: set of ids
    :param max_dist: The maximum distance to include
    :type link_name: float
    :param filter_func: A function to filter the set
    :type filter_func: func
    :rtype: CloseData"""
def closest_list (source: int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData | sbs_utils.engineobject.EngineObject, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.engineobject.CloseData]:
    """close_list
    
    get the list of close data that matches the test set, max_dist and optional filter function
    
    :param source: The id object to check
    :type source: int / id
    :param the_set: a set of ids to check against
    :type the_set: set of ids
    :param max_dist: The maximum distance to include
    :type link_name: float
    :param filter_func: A function to filter the set
    :type filter_func: func
    :rtype: list of CloseData"""
def closest_object (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.engineobject.EngineObject:
    """closest_object
    
    get the object that matches the test set, max_dist and optional filter function
    
    :param source: The id object to check
    :type source: int / id
    :param the_set: a set of ids to check against
    :type the_set: set of ids
    :param max_dist: The maximum distance to include
    :type link_name: float
    :param filter_func: A function to filter the set
    :type filter_func: func
    :rtype: EngineObject"""
def get_data_set_value (data_set, key, index=0):
    ...
def get_dedicated_link (so, link):
    ...
def get_engine_data (id_or_obj, sim, key, index=0):
    ...
def get_engine_data_set (sim, id_or_obj):
    ...
def get_inventory_value (so, link):
    ...
def get_open_grid_points (sim, id_or_obj):
    ...
def get_pos (sim, id_or_obj):
    ...
def grid_clear_target (grid_obj_or_set, sim):
    """Clear the target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation"""
def grid_close_list (grid_obj, sim, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.engineobject.CloseData]:
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
    :rtype: List[GridCloseData]"""
def grid_closest (grid_obj, sim, roles=None, max_dist=None, filter_func=None) -> sbs_utils.engineobject.CloseData:
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
    :rtype: GridCloseData"""
def grid_objects (sim, so_id):
    ...
def grid_target (grid_obj_or_set, sim, target_id: int, speed=0.01):
    """Set the item to target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def grid_target_closest (grid_obj_or_set, sim, roles=None, max_dist=None, filter_func=None):
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
    :rtype: GridCloseData"""
def grid_target_pos (grid_obj_or_set, sim, x: float, y: float, speed=0.01):
    """Set the item to target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def has_inventory (key: str):
    """has_inventory
    
    get the object that have a inventory item with the given key
    
    :param key: The key/name of the inventory item
    :type key: str
    :rtype: set of ids"""
def has_link (key: str):
    """has_link
    
    get the object that have a link item with the given key
    
    :param key: The key/name of the inventory item
    :type key: str
    :rtype: set of ids"""
def has_role (so, role):
    ...
def has_roles (so, roles):
    ...
def inventory_set (link_source, link_name: str):
    """inventory_set
    
    get the set that inventory items with the given key the the link source has
    this is the way to create a collection in inventory
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: set of data"""
def inventory_value (link_source, link_name: str):
    """inventory_value
    
    get the value that inventory items with the given key the the link source has
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: data"""
def is_client_id (id):
    ...
def is_grid_object_id (id):
    ...
def is_space_object_id (id):
    ...
def link (set_holder, link, set_to):
    ...
def linked_to (link_source, link_name: str):
    """linked_to
    
    get the set that inventor the source is linked to for the given key
    
    :param link_source: The id object to check
    :type link_source: int / id
    :param link_name: The key/name of the inventory item
    :type link_name: str
    :rtype: set of ids"""
def object_exists (sim, so_id):
    ...
def random_object (the_set):
    """random_object
    
    get the object from the set provide
    
    :rtype: EngineObject"""
def random_object_list (the_set, count=1):
    """random_object_list
    
    get a list of objects selected randomly from the set provided
    
    :param the_set: Set of Ids
    :type the_set: set of ids
    :param count: The number of objects to pick
    :type count: int
    :rtype: list of EngineObject"""
def remove_role (set_holder, role):
    ...
def role (role: str):
    """role
    
    returns a set of all the engine objects with a given role.
    
    :param role: the role
    :type role: str
    
    :rtype: set of ids """
def set_data_set_value (data_set, key, value, index=0):
    ...
def set_dedicated_link (so, link, to):
    ...
def set_engine_data (to_update, sim, key, value, index=0):
    ...
def set_inventory_value (so, link, to):
    ...
def set_pos (sim, id_or_obj, x, y, z):
    ...
def target (sim, set_or_object, target_id, shoot: bool = True):
    """Set the item to target
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def target_pos (sim, chasers: set | int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData, x: float, y: float, z: float):
    """Set the item to target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def to_id (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_id_list (the_set):
    """to_id_list
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
def to_list (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_list
    
    converts a single object/id, set ot list of things to a list
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of things"""
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object_list (the_set):
    """to_object_list
    
    converts a set to a list of objects
    
    :param the_set: A set of ids
    :type the_set: set of ids
    
    :rtype: list of EngineObject"""
def to_py_object_list (the_set):
    """to_py_object_list
    
    converts a set of ids to a set of objects
    
    :rtype: list EngineObject"""
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_set
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
def unlink (set_holder, link, set_to):
    ...
def update_engine_data (sim, to_update, data):
    ...
