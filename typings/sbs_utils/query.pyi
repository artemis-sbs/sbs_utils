from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
def add_role (set_holder, role):
    ...
def all_objects_exists (sim, the_set):
    ...
def broad_test (x1: float, z1: float, x2: float, z2: float, broad_type=-1):
    ...
def clear_target (sim, chasers: set | int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData):
    """Clear the target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation"""
def closest (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.engineobject.CloseData:
    ...
def closest_list (source: int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData | sbs_utils.engineobject.EngineObject, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.engineobject.CloseData]:
    ...
def closest_object (the_ship, the_set, max_dist=None, filter_func=None) -> sbs_utils.engineobject.EngineObject:
    ...
def get_data_set_value (data_set, key, index=0):
    ...
def get_dedicated_link (so, link):
    ...
def get_engine_data (id_or_obj, sim, key, index=0):
    ...
def get_engine_data_set (id_or_obj, sim):
    ...
def get_inventory_value (so, link):
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
def grid_target (grid_obj_or_set, sim, target_id: int):
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
def grid_target_pos (grid_obj_or_set, sim, x: float, y: float):
    """Set the item to target
    
    :param sim: The simulation
    :type sim: Artemis Cosmos simulation
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def has_inventory (role: str):
    ...
def has_link (role: str):
    ...
def has_role (so, role):
    ...
def inventory_set (link_source, link_name: str):
    ...
def inventory_value (link_source, link_name: str):
    ...
def link (set_holder, link, set_to):
    ...
def linked_to (link_source, link_name: str):
    ...
def object_exists (sim, so_id):
    ...
def random_object (the_set):
    ...
def random_object_list (the_set, count=1):
    ...
def remove_role (set_holder, role):
    ...
def role (role: str):
    ...
def set_data_set_value (data_set, key, value, index=0):
    ...
def set_dedicated_link (so, link, to):
    ...
def set_engine_data (to_update, sim, key, value, index=0):
    ...
def set_inventory_value (so, link, to):
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
    ...
def to_list (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object_list (the_set):
    ...
def to_py_object_list (the_set):
    ...
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def unlink (set_holder, link, set_to):
    ...
def update_engine_data (sim, to_update, data):
    ...
