from sbs_utils.engineobject import CloseData
from sbs_utils.engineobject import EngineObject
from sbs_utils.engineobject import SpawnData
from sbs_utils.helpers import FrameContext
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
def clear_target (chasers: set | int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData):
    """Clear the target
    
    :param the_set: A set of ids, id, CloseData, or SpawnData
    :type the_set: set of ids, id, CloseData, or SpawnData"""
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
def get_pos (id_or_obj):
    ...
def set_pos (id_or_obj, x, y, z):
    ...
def target (set_or_object, target_id, shoot: bool = True, throttle: float = 1.0):
    """Set the item to target
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def target_pos (chasers: set | int | sbs_utils.engineobject.CloseData | sbs_utils.engineobject.SpawnData, x: float, y: float, z: float, throttle: float = 1.0):
    """Set the item to target
    
    :param other_id: the id of the object to target
    :type other_id: int
    :param shoot: if the object should be shot at
    :type shoot: bool"""
def to_list (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_list
    
    converts a single object/id, set ot list of things to a list
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of things"""
def to_object (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    ...
def to_set (other: sbs_utils.engineobject.EngineObject | sbs_utils.engineobject.CloseData | int):
    """to_set
    
    converts a single object/id, set ot list of things to a set of ids
    
    :param the_set: The a set of things
    :type the_set: set, list or single item
    :rtype: list of ids"""
