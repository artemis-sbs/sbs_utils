from sbs_utils.engineobject import CloseData
from sbs_utils.tickdispatcher import TickDispatcher
def get_inventory_value (so, link, default=None):
    ...
def get_open_grid_points (id_or_obj):
    ...
def grid_clear_detailed_status (id_or_obj):
    ...
def grid_clear_speech_bubble (id_or_obj):
    ...
def grid_clear_target (grid_obj_or_set):
    """Clear the target
    
    :param id: the id of the object or set
    :type id: int"""
def grid_close_list (grid_obj, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.engineobject.CloseData]:
    """Finds a list of matching objects
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str]
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func:
    :return: A list of close object
    :rtype: List[GridCloseData]"""
def grid_closest (grid_obj, roles=None, max_dist=None, filter_func=None) -> sbs_utils.engineobject.CloseData:
    """Finds the closest object matching the criteria
    
    :param roles: Roles to looks for can also be class name
    :type roles: str or List[str]
    :param max_dist: Max distance to search (faster)
    :type max_dist: float
    :param filter_func: Called to test each object to filter out non matches
    :type filter_func: function that takes ID
    :return: A list of close object
    :rtype: GridCloseData"""
def grid_detailed_status (id_or_obj, status, color=None):
    ...
def grid_objects (so_id):
    ...
def grid_objects_at (so_id, x, y):
    ...
def grid_short_status (id_or_obj, status, color=None, seconds=0, minutes=0):
    ...
def grid_speech_bubble (id_or_obj, status, color=None, seconds=0, minutes=0):
    ...
def grid_target (grid_obj_or_set, target_id: int, speed=0.01):
    """Set the item to target
    
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def grid_target_closest (grid_obj_or_set, roles=None, max_dist=None, filter_func=None):
    """Find and target the closest object matching the criteria
    
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
def grid_target_pos (grid_obj_or_set, x: float, y: float, speed=0.01):
    """Set the item to target
    
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def set_inventory_value (so, name, value):
    ...
def to_blob (id_or_obj):
    ...
def to_id (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_object_list (the_set):
    """to_object_list
    
    converts a set to a list of objects
    
    :param the_set: A set of ids
    :type the_set: set of ids
    
    :rtype: list of EngineObject"""
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_set
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
